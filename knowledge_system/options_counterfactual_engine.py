"""
Options Counterfactual Engine
==============================

Background monitoring of rejected and non-executed options opportunities.

Purpose
-------
For every options opportunity that was REJECTED or NOT_EXECUTED, the engine:

  1. Records the rejection and expected move horizon (= DTE at rejection time).
  2. After the horizon has passed, estimates the hypothetical P&L that would
     have been realised had the signal been executed.
  3. Classifies the rejection outcome:
       REJECTION_CORRECT    → rejection was right (hypothetical P&L ≤ 0)
       REJECTION_INCORRECT  → rejection was wrong (hypothetical P&L > 0)
       MISSED_OPPORTUNITY   → system never generated the signal; large profitable
                               move happened that matched the strategy's profile

  4. Records all findings back to the observation journal and to the
     knowledge store so the pattern engine can learn from false rejections.

Monitoring interval: every 30 minutes (triggered by research pipeline).
Horizon: = DTE at rejection time (options expire, so post-DTE is the right horizon).
         Min horizon: 1 day.  Max horizon: 30 days.

P&L estimation (after DTE)
--------------------------
At analysis time we cannot roll back the options chain.  We use:
  - The underlying spot change over the horizon period
  - The original expected_entry_price from the signal
  - Black-Scholes intrinsic + time-value decay model to estimate exit premium
  - This is explicitly labelled as ESTIMATED — not as actual P&L

Persistence: monitors written to observation journal (JSONL).
             pending monitors held in data/options_cf_pending.json.
"""

from __future__ import annotations

import json
import os
import threading
from dataclasses import dataclass, field, asdict
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional

from utils import get_logger

log = get_logger(__name__)

_CF_PENDING_PATH = "data/options_cf_pending.json"

# Maximum DTE horizon to track (beyond this, monitoring expires)
MAX_MONITOR_DTE  = 60
MIN_MONITOR_DAYS = 1

# DTA-OPTIONS-CREDIT-CLASSIFICATION-001: mirrors the authoritative
# _CREDIT_OPTION_TYPES fix in execution_engine/options_order_manager.py.
# monitor.strategy_name holds the human-readable label (e.g. "Iron_Condor_Range",
# "Hedging_Model", "Bear_Put_Spread") -- NOT the option_type/strategy_type
# code -- so the token set is matched against that naming convention instead.
# Deliberately does NOT fall back to `direction == "SELL"`: that field is the
# signal's directional VIEW, not its credit/debit nature (Bear_Put_Spread is a
# DEBIT spread with a bearish view, hence direction=SELL -- the prior fallback
# misclassified it as credit, inverting its hypothetical P&L sign).
_CREDIT_STRATEGY_NAME_TOKENS = ("IRON_CONDOR", "HEDGING_MODEL")


@dataclass
class CounterfactualMonitor:
    """Pending counterfactual monitoring record."""
    opportunity_id:    str
    symbol:            str
    strategy_name:     str
    direction:         str
    rejection_reason:  str
    expected_pnl:      float
    expected_entry_price: float
    dte_at_rejection:  int
    monitor_until:     str    # ISO date — when to run analysis
    recorded_at:       str    # ISO datetime — when rejected

    # ── Context for retrospective analysis ────────────────────────────
    spot_at_rejection: float = 0.0
    iv_at_rejection:   float = 0.0
    regime_at_rejection: str = ""
    confidence:        float = 0.0
    iv_rank_at_rejection: float = 0.0

    # Real-quote virtual position, used only when every entry leg has a live
    # executable bid/ask. Existing records without these fields remain readable.
    entry_legs:        List[dict] = field(default_factory=list)
    lots:              int = 1
    lot_size:          int = 1
    expiry_date:       str = ""
    stop_premium:      float = 0.0
    target_premium:    float = 0.0
    entry_quote_source: str = ""
    pnl_method:        str = "UNDERLYING_DIRECTIONAL_ESTIMATE"
    last_mark_pnl:     Optional[float] = None
    last_mark_at:      str = ""
    gross_hypothetical_pnl: Optional[float] = None
    estimated_transaction_cost: float = 0.0
    decision_grade:    Optional[str] = None

    # ── Outcome ───────────────────────────────────────────────────────
    analysed:              bool = False
    hypothetical_pnl:      Optional[float] = None
    rejection_classification: Optional[str] = None
    analysis_notes:        str = ""


def _normalize_live_entry_legs(legs: Optional[List[dict]]) -> List[dict]:
    """Keep a quote-backed virtual entry only when every leg is executable."""
    if not isinstance(legs, list) or not legs:
        return []
    normalized: List[dict] = []
    for leg in legs:
        if not isinstance(leg, dict):
            return []
        direction = str(leg.get("direction", "")).upper()
        option_type = str(leg.get("type", leg.get("option_type", ""))).upper()
        try:
            strike = float(leg.get("strike", 0.0))
            bid = float(leg.get("bid", 0.0) or 0.0)
            ask = float(leg.get("ask", 0.0) or 0.0)
        except (TypeError, ValueError):
            return []
        if direction not in ("BUY", "SELL") or option_type not in ("CE", "PE"):
            return []
        if strike <= 0 or bid <= 0 or ask < bid:
            return []
        normalized.append({
            "strike": strike,
            "type": option_type,
            "direction": direction,
            "entry_bid": bid,
            "entry_ask": ask,
            "entry_price": ask if direction == "BUY" else bid,
        })
    return normalized if len(normalized) == len(legs) else []


class OptionsCounterfactualEngine:
    """
    Tracks and analyses counterfactual outcomes for rejected/missed opportunities.

    Thread-safe.  Called periodically by the research pipeline.
    """

    def __init__(self) -> None:
        self._lock    = threading.RLock()
        self._pending: Dict[str, CounterfactualMonitor] = {}  # opportunity_id → monitor
        os.makedirs(os.path.dirname(_CF_PENDING_PATH), exist_ok=True)
        self._load()

    # ── Public API ─────────────────────────────────────────────────────────

    def register_rejection(
        self,
        opportunity_id:       str,
        symbol:               str,
        strategy_name:        str,
        direction:            str,
        rejection_reason:     str,
        expected_pnl:         float,
        expected_entry_price: float,
        dte:                  int,
        spot:                 float,
        iv:                   float,
        regime:               str,
        confidence:           float,
        iv_rank:              float = 0.0,
        legs:                 Optional[List[dict]] = None,
        lots:                 int = 1,
        lot_size:             int = 1,
        expiry_date:          str = "",
        stop_premium:         float = 0.0,
        target_premium:       float = 0.0,
        entry_quotes_live:    bool = False,
        entry_quote_source:   str = "",
    ) -> None:
        """
        Register a rejected/non-executed opportunity for counterfactual monitoring.
        """
        if dte <= 0 or dte > MAX_MONITOR_DTE:
            return  # outside trackable range

        horizon_days = max(dte, MIN_MONITOR_DAYS)
        monitor_date = (date.today() + timedelta(days=horizon_days)).isoformat()

        normalized_legs = _normalize_live_entry_legs(legs) if entry_quotes_live else []
        pnl_method = (
            "LIVE_OPTION_QUOTES_PENDING"
            if normalized_legs and expiry_date
            else "UNDERLYING_DIRECTIONAL_ESTIMATE"
        )
        with self._lock:
            existing = self._pending.get(opportunity_id)
            if existing and not existing.analysed:
                if normalized_legs and not existing.entry_legs and expiry_date:
                    existing.entry_legs = normalized_legs
                    existing.lots = max(1, int(lots or 1))
                    existing.lot_size = max(1, int(lot_size or 1))
                    existing.expiry_date = expiry_date
                    existing.stop_premium = float(stop_premium or 0.0)
                    existing.target_premium = float(target_premium or 0.0)
                    existing.entry_quote_source = entry_quote_source
                    existing.pnl_method = "LIVE_OPTION_QUOTES_PENDING"
                if rejection_reason and rejection_reason not in existing.rejection_reason:
                    existing.rejection_reason = (
                        f"{existing.rejection_reason}|{rejection_reason}"
                    )
                self._save()
                return

            if normalized_legs and expiry_date:
                signature = tuple(sorted(
                    (
                        float(leg["strike"]),
                        str(leg["type"]),
                        str(leg["direction"]),
                    )
                    for leg in normalized_legs
                ))
                today = date.today().isoformat()
                duplicate = any(
                    prior.recorded_at[:10] == today
                    and prior.expiry_date == expiry_date
                    and prior.symbol == symbol
                    and prior.strategy_name == strategy_name
                    and tuple(sorted(
                        (
                            float(leg["strike"]),
                            str(leg["type"]),
                            str(leg["direction"]),
                        )
                        for leg in prior.entry_legs
                    )) == signature
                    for prior in self._pending.values()
                    if prior.entry_legs
                )
                if duplicate:
                    log.info(
                        "[CounterfactualEngine] Deduplicated same-day shadow structure "
                        "%s %s %s; decision remains in observation journal.",
                        symbol, strategy_name, expiry_date,
                    )
                    return

        monitor = CounterfactualMonitor(
            opportunity_id       = opportunity_id,
            symbol               = symbol,
            strategy_name        = strategy_name,
            direction            = direction,
            rejection_reason     = rejection_reason,
            expected_pnl         = expected_pnl,
            expected_entry_price = expected_entry_price,
            dte_at_rejection     = dte,
            monitor_until        = monitor_date,
            recorded_at          = datetime.now().isoformat(),
            spot_at_rejection    = spot,
            iv_at_rejection      = iv,
            regime_at_rejection  = regime,
            confidence           = confidence,
            iv_rank_at_rejection = iv_rank,
            entry_legs           = normalized_legs,
            lots                 = max(1, int(lots or 1)),
            lot_size             = max(1, int(lot_size or 1)),
            expiry_date          = expiry_date,
            stop_premium         = float(stop_premium or 0.0),
            target_premium       = float(target_premium or 0.0),
            entry_quote_source   = entry_quote_source,
            pnl_method           = pnl_method,
        )
        with self._lock:
            self._pending[opportunity_id] = monitor
            self._save()

        self._write_monitoring_state(monitor)

        log.debug(
            "[CounterfactualEngine] Registered monitor for %s (%s %s), "
            "horizon=%d days, monitor_until=%s",
            opportunity_id, strategy_name, symbol, horizon_days, monitor_date,
        )

    def run_analysis(self) -> List[CounterfactualMonitor]:
        """
        Analyse all monitors whose monitoring window has passed.
        Returns the list of newly analysed monitors.
        """
        today  = date.today().isoformat()
        newly_analysed: List[CounterfactualMonitor] = []
        changed = False

        with self._lock:
            quote_backed = [
                m for m in self._pending.values()
                if not m.analysed and m.pnl_method == "LIVE_OPTION_QUOTES_PENDING"
            ]

        for monitor in quote_backed:
            updated, completed = self._refresh_live_quote_monitor(monitor)
            changed = changed or updated
            if completed:
                newly_analysed.append(monitor)

        with self._lock:
            due = [m for m in self._pending.values()
                   if not m.analysed
                   and m.pnl_method == "UNDERLYING_DIRECTIONAL_ESTIMATE"
                   and m.monitor_until <= today]

        for monitor in due:
            self._analyse(monitor)
            newly_analysed.append(monitor)

        if newly_analysed or changed:
            with self._lock:
                self._save()
        if newly_analysed:
            self._write_journal(newly_analysed)
            log.info(
                "[CounterfactualEngine] Analysed %d counterfactuals today.",
                len(newly_analysed),
            )

        return newly_analysed

    def _write_monitoring_state(self, monitor: CounterfactualMonitor) -> None:
        """Append the start of shadow monitoring to the options journal."""
        try:
            from execution_engine.options_observation_journal import (
                get_options_observation_journal,
                OptionsOpportunityObservation,
                OBS_COUNTERFACTUAL_MONITORING,
            )
            journal = get_options_observation_journal()
            journal.record(OptionsOpportunityObservation(
                obs_id=journal.make_obs_id(monitor.symbol, monitor.strategy_name),
                symbol=monitor.symbol,
                strategy_name=monitor.strategy_name,
                observed_at=datetime.now().isoformat(),
                state=OBS_COUNTERFACTUAL_MONITORING,
                opportunity_id=monitor.opportunity_id,
                confidence=monitor.confidence,
                direction=monitor.direction,
                dte=monitor.dte_at_rejection,
                iv_rank=monitor.iv_rank_at_rejection,
                regime=monitor.regime_at_rejection,
                data_source=monitor.entry_quote_source,
                expected_pnl=monitor.expected_pnl,
                expected_entry_price=monitor.expected_entry_price,
                counterfactual_horizon_days=monitor.dte_at_rejection,
                counterfactual_notes=(
                    f"reason={monitor.rejection_reason};pnl_method={monitor.pnl_method}"
                ),
            ))
        except Exception as exc:
            log.debug("[CounterfactualEngine] Monitoring journal write failed: %s", exc)

    def _refresh_live_quote_monitor(
        self,
        monitor: CounterfactualMonitor,
    ) -> tuple[bool, bool]:
        """Mark a virtual spread from live bid/ask quotes and close by rule."""
        try:
            from data_feeds.options_feed import get_options_feed
            from execution_engine.options_order_manager import DTE_EXIT_DAYS

            expiry_date = date.fromisoformat(monitor.expiry_date)
            remaining_dte = max((expiry_date - date.today()).days, 0)
            chain = get_options_feed().get_chain(
                monitor.symbol, dte_target=max(1, remaining_dte)
            )
            if (
                chain is None
                or not chain.is_live
                or chain.expiry != expiry_date
                or (datetime.now() - chain.fetched_at).total_seconds() > 600
            ):
                if date.today().isoformat() >= monitor.monitor_until:
                    monitor.analysed = True
                    monitor.pnl_method = "LIVE_OPTION_QUOTES_UNAVAILABLE"
                    monitor.analysis_notes = "live_chain_or_exact_expiry_unavailable_at_horizon"
                    return True, True
                return False, False

            gross_pnl_per_unit = 0.0
            quantity = max(1, monitor.lots) * max(1, monitor.lot_size)
            current_net = 0.0
            from models.transaction_costs import (
                InstrumentType,
                get_cost_model,
            )
            cost_model = get_cost_model()
            estimated_cost = 0.0
            for leg in monitor.entry_legs:
                contracts = chain.calls if leg["type"] == "CE" else chain.puts
                contract = next(
                    (c for c in contracts if abs(float(c.strike) - leg["strike"]) < 0.01),
                    None,
                )
                if contract is None or contract.bid <= 0 or contract.ask < contract.bid:
                    if date.today().isoformat() >= monitor.monitor_until:
                        monitor.analysed = True
                        monitor.pnl_method = "LIVE_OPTION_QUOTES_UNAVAILABLE"
                        monitor.analysis_notes = "entry_contract_quote_unavailable_at_horizon"
                        return True, True
                    return False, False

                direction = leg["direction"]
                exit_price = float(contract.bid if direction == "BUY" else contract.ask)
                entry_price = float(leg["entry_price"])
                pnl_per_unit = (
                    exit_price - entry_price
                    if direction == "BUY"
                    else entry_price - exit_price
                )
                gross_pnl_per_unit += pnl_per_unit
                if direction == "BUY":
                    cost_entry_price, cost_exit_price = entry_price, exit_price
                else:
                    cost_entry_price, cost_exit_price = exit_price, entry_price
                cost_breakdown = cost_model.compute(
                    symbol=f"{monitor.symbol} {leg['type']} {leg['strike']}",
                    quantity=quantity,
                    entry_price=cost_entry_price,
                    exit_price=cost_exit_price,
                    instrument_type=InstrumentType.OPTIONS,
                )
                estimated_cost += cost_breakdown.total_cost
                current_net += exit_price if direction == "BUY" else -exit_price

            gross_pnl = round(gross_pnl_per_unit * quantity, 2)
            mark_pnl = round(gross_pnl - estimated_cost, 2)
            monitor.last_mark_pnl = mark_pnl
            monitor.last_mark_at = datetime.now().isoformat()

            net_premium = abs(current_net)
            is_credit = any(
                token in monitor.strategy_name.upper()
                for token in _CREDIT_STRATEGY_NAME_TOKENS
            )
            close_reason = ""
            if is_credit:
                if monitor.stop_premium > 0 and net_premium >= monitor.stop_premium:
                    close_reason = "STOP_LOSS"
                elif monitor.target_premium > 0 and net_premium <= monitor.target_premium:
                    close_reason = "TARGET_HIT"
            else:
                if monitor.stop_premium > 0 and net_premium <= monitor.stop_premium:
                    close_reason = "STOP_LOSS"
                elif monitor.target_premium > 0 and net_premium >= monitor.target_premium:
                    close_reason = "TARGET_HIT"
            if not close_reason and remaining_dte <= DTE_EXIT_DAYS:
                close_reason = "DTE_EXIT"

            if not close_reason:
                return True, False

            monitor.hypothetical_pnl = mark_pnl
            monitor.gross_hypothetical_pnl = gross_pnl
            monitor.estimated_transaction_cost = round(estimated_cost, 2)
            monitor.decision_grade = (
                "GOOD" if mark_pnl > 0
                else "AVERAGE" if gross_pnl > 0
                else "BAD"
            )
            monitor.rejection_classification = (
                "REJECTION_INCORRECT" if mark_pnl > 0 else "REJECTION_CORRECT"
            )
            monitor.analysed = True
            monitor.pnl_method = "LIVE_OPTION_QUOTES_NET_ESTIMATED_COSTS"
            monitor.analysis_notes = (
                f"method={monitor.pnl_method}; close_reason={close_reason}; "
                f"remaining_dte={remaining_dte}; net_premium={net_premium:.2f}; "
                f"gross_pnl={gross_pnl:.2f}; estimated_cost={estimated_cost:.2f}; "
                f"decision_grade={monitor.decision_grade}; executable-side bid/ask"
            )
            return True, True
        except Exception as exc:
            log.debug(
                "[CounterfactualEngine] Live quote mark failed for %s: %s",
                monitor.opportunity_id, exc,
            )
            return False, False

    def pending_count(self) -> int:
        with self._lock:
            return sum(1 for m in self._pending.values() if not m.analysed)

    def get_false_rejections(self) -> List[CounterfactualMonitor]:
        """Return all analysed monitors classified as false rejections."""
        with self._lock:
            return [m for m in self._pending.values()
                    if m.rejection_classification == "REJECTION_INCORRECT"]

    # ── Private ────────────────────────────────────────────────────────────

    def _analyse(self, monitor: CounterfactualMonitor) -> None:
        """
        Estimate hypothetical P&L for a past rejection.

        Uses the current spot price vs spot at rejection time to estimate
        whether the underlying moved in the predicted direction.
        """
        try:
            current_spot = self._get_current_spot(monitor.symbol)
            if current_spot <= 0 or monitor.spot_at_rejection <= 0:
                monitor.analysed = True
                monitor.analysis_notes = "spot_unavailable"
                return

            spot_change_pct = (current_spot - monitor.spot_at_rejection) / monitor.spot_at_rejection
            direction = monitor.direction.upper()

            # Simple directional estimate for the hypothetical P&L
            # For spreads, profit is bounded by max_profit (expected_pnl)
            # This is approximate — we use a sign-based estimate
            if direction in ("BULLISH", "UP"):
                directional_match = spot_change_pct > 0.005   # +0.5% move
            elif direction in ("BEARISH", "DOWN"):
                directional_match = spot_change_pct < -0.005
            else:  # neutral (IC, straddle) — wins if low move
                directional_match = abs(spot_change_pct) < 0.02

            # Scale hypothetical P&L by directional confidence
            if directional_match:
                # Directional signal was right: estimate ~50% of expected_pnl
                hypo_pnl = monitor.expected_pnl * 0.5
                classification = "REJECTION_INCORRECT"
            else:
                # Directional signal was wrong
                hypo_pnl = -(monitor.expected_entry_price * 0.3)  # rough loss estimate
                classification = "REJECTION_CORRECT"

            monitor.hypothetical_pnl          = round(hypo_pnl, 2)
            monitor.rejection_classification  = classification
            monitor.analysed                   = True
            monitor.analysis_notes = (
                f"spot_at_rejection={monitor.spot_at_rejection:.0f} "
                f"current_spot={current_spot:.0f} "
                f"spot_change={spot_change_pct:.2%} "
                f"directional_match={directional_match} "
                f"method=DIRECTIONAL_ESTIMATE"
            )

        except Exception as exc:
            monitor.analysed = True
            monitor.analysis_notes = f"error: {exc}"

    def _get_current_spot(self, symbol: str) -> float:
        """Get current spot price for the symbol, non-raising."""
        try:
            from data_feeds.data_feed_manager import get_feed_manager
            fm  = get_feed_manager()
            quote = fm.get_quote(symbol)
            if quote and hasattr(quote, "ltp"):
                return float(quote.ltp)
            if quote and hasattr(quote, "close"):
                return float(quote.close)
        except Exception:
            pass
        return 0.0

    def _write_journal(self, monitors: List[CounterfactualMonitor]) -> None:
        """Write counterfactual outcomes back to the observation journal."""
        try:
            from execution_engine.options_observation_journal import (
                get_options_observation_journal,
                OptionsOpportunityObservation,
                OBS_COUNTERFACTUAL_MONITORING,
                OBS_COUNTERFACTUAL_OUTCOME,
                OBS_REJECTION_CORRECT,
                OBS_REJECTION_INCORRECT,
            )
            journal = get_options_observation_journal()
            for m in monitors:
                state_map = {
                    "REJECTION_CORRECT":   OBS_REJECTION_CORRECT,
                    "REJECTION_INCORRECT": OBS_REJECTION_INCORRECT,
                }
                state = state_map.get(
                    m.rejection_classification or "", OBS_COUNTERFACTUAL_OUTCOME
                )
                obs = OptionsOpportunityObservation(
                    obs_id         = journal.make_obs_id(m.symbol, m.strategy_name),
                    symbol         = m.symbol,
                    strategy_name  = m.strategy_name,
                    observed_at    = datetime.now().isoformat(),
                    state          = state,
                    opportunity_id = m.opportunity_id,
                    confidence     = m.confidence,
                    direction      = m.direction,
                    regime         = m.regime_at_rejection,
                    counterfactual_checked = True,
                    counterfactual_notes   = m.analysis_notes,
                    counterfactual_pnl     = m.hypothetical_pnl,
                    counterfactual_horizon_days = m.dte_at_rejection,
                )
                journal.record(obs)
        except Exception as exc:
            log.debug("[CounterfactualEngine] Journal write failed: %s", exc)

    def _save(self) -> None:
        try:
            data = {
                "saved_at": datetime.now().isoformat(),
                "pending":  {k: asdict(v) for k, v in self._pending.items()},
            }
            tmp = _CF_PENDING_PATH + ".tmp"
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump(data, fh, indent=2, default=str)
            os.replace(tmp, _CF_PENDING_PATH)
        except Exception as exc:
            log.debug("[CounterfactualEngine] Save failed: %s", exc)

    def _load(self) -> None:
        if not os.path.exists(_CF_PENDING_PATH):
            return
        try:
            with open(_CF_PENDING_PATH, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            for oid, raw in data.get("pending", {}).items():
                try:
                    m = CounterfactualMonitor(**{
                        k: v for k, v in raw.items()
                        if k in CounterfactualMonitor.__dataclass_fields__
                    })
                    self._pending[oid] = m
                except Exception:
                    pass
            log.info(
                "[CounterfactualEngine] Loaded %d pending monitors.",
                len(self._pending),
            )
        except Exception as exc:
            log.debug("[CounterfactualEngine] Load failed: %s", exc)


# ── Singleton ──────────────────────────────────────────────────────────────

_CF_INSTANCE: Optional[OptionsCounterfactualEngine] = None
_CF_LOCK      = threading.Lock()


def get_options_counterfactual_engine() -> OptionsCounterfactualEngine:
    global _CF_INSTANCE
    with _CF_LOCK:
        if _CF_INSTANCE is None:
            _CF_INSTANCE = OptionsCounterfactualEngine()
    return _CF_INSTANCE
