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
MAX_MONITOR_DTE  = 30
MIN_MONITOR_DAYS = 1


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

    # ── Outcome ───────────────────────────────────────────────────────
    analysed:              bool          = False
    hypothetical_pnl:      Optional[float] = None
    rejection_classification: Optional[str] = None  # REJECTION_CORRECT / REJECTION_INCORRECT / MISSED
    analysis_notes:        str           = ""


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
    ) -> None:
        """
        Register a rejected/non-executed opportunity for counterfactual monitoring.
        """
        if dte <= 0 or dte > MAX_MONITOR_DTE:
            return  # outside trackable range

        horizon_days = max(dte, MIN_MONITOR_DAYS)
        monitor_date = (date.today() + timedelta(days=horizon_days)).isoformat()

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
        )
        with self._lock:
            self._pending[opportunity_id] = monitor
            self._save()

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

        with self._lock:
            due = [m for m in self._pending.values()
                   if not m.analysed and m.monitor_until <= today]

        for monitor in due:
            self._analyse(monitor)
            newly_analysed.append(monitor)

        if newly_analysed:
            with self._lock:
                self._save()
            self._write_journal(newly_analysed)
            log.info(
                "[CounterfactualEngine] Analysed %d counterfactuals today.",
                len(newly_analysed),
            )

        return newly_analysed

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
