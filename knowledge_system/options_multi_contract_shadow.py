"""
Options Multi-Contract Shadow Tracker
=======================================
DTA-001 Phase 5: "Which option would have been best?"

When an underlying opportunity is identified and ONE option contract is executed,
this tracker shadows the outcomes of ALL other candidate contracts that were
considered or could have been selected.

This answers the critical learning question (spec §6):
    "Given this underlying move, which option contract historically
     captured the move most efficiently?"

Architecture:
    For each EXECUTED opportunity, the scanner records:
        - The EXECUTED contract (from the live position)
        - Shadow contracts: ATM, OTM+1, OTM+2, ITM+1, ITM+2 (all CE/PE variants)
          at the same underlying state as at entry time

    When the position EXITS, all shadow contracts are re-priced
    (via current chain data or yfinance fallback) and hypothetical P&L computed.

    Results are stored per context, stratified by:
        (regime, ivr_band, dte_band, underlying_move_band)

    Eventually answers:
        "In BULL regime + IVR_HIGH + DTE_WEEKLY, the ATM call typically
         captures 3.2× the underlying move, while the OTM+1 call captures 5.1×
         (but only 40% of the time)."

Failure classification (spec §6, §27):
    CORRECT_SELECTION       — selected contract outperformed alternatives
    OPTION_SELECTION_FAILURE — a better contract was available and not selected
    MISSED_UNDERLYING        — no option was selected despite the underlying moving well

Persistence: data/options_multi_contract_shadow.json (atomic write)
Singleton: get_options_multi_contract_shadow()
"""

from __future__ import annotations

import json
import os
import threading
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from utils import get_logger

log = get_logger(__name__)

_PERSIST_PATH = "data/options_multi_contract_shadow.json"
_INSTANCE: Optional["OptionsMultiContractShadow"] = None
_INSTANCE_LOCK = threading.Lock()

# ── Moneyness categories ───────────────────────────────────────────────────
MON_DEEP_OTM = "DEEP_OTM"    # delta < 0.15
MON_OTM      = "OTM"         # delta 0.15–0.35
MON_ATM      = "ATM"         # delta 0.35–0.65
MON_ITM      = "ITM"         # delta 0.65–0.80
MON_DEEP_ITM = "DEEP_ITM"    # delta > 0.80

# ── Selection outcome labels ───────────────────────────────────────────────
SEL_CORRECT   = "CORRECT_SELECTION"
SEL_FAILURE   = "OPTION_SELECTION_FAILURE"
SEL_NEUTRAL   = "NEUTRAL"           # differences below threshold
SEL_MISSED    = "MISSED_UNDERLYING" # no option selected despite underlying moving

# Threshold: selected contract must return within X% of best to be "correct"
SELECTION_CORRECTNESS_THRESHOLD = 0.80  # 80% of best alternative


def _moneyness(delta: float) -> str:
    d = abs(delta)
    if d < 0.15:
        return MON_DEEP_OTM
    if d < 0.35:
        return MON_OTM
    if d < 0.65:
        return MON_ATM
    if d < 0.80:
        return MON_ITM
    return MON_DEEP_ITM


def get_options_multi_contract_shadow() -> "OptionsMultiContractShadow":
    global _INSTANCE
    with _INSTANCE_LOCK:
        if _INSTANCE is None:
            _INSTANCE = OptionsMultiContractShadow()
    return _INSTANCE


@dataclass
class ShadowContractRecord:
    """One shadow contract for a specific opportunity."""
    opportunity_id:     str
    is_executed:        bool        # True = this was the actual trade
    option_type:        str         # CE / PE
    strike:             float
    moneyness:          str
    delta_at_entry:     float
    entry_premium:      float
    exit_premium:       Optional[float]         # filled when position exits
    hypothetical_pnl:   Optional[float]
    pct_return:         Optional[float]
    outcome_recorded:   bool = False
    iv_at_entry:        float = 0.0


@dataclass
class MultiContractOutcome:
    """
    Summary of executed vs best available contract for one opportunity.

    Created when the position exits and all shadow contracts are re-priced.
    """
    opportunity_id:     str
    symbol:             str
    strategy_name:      str
    direction:          str
    regime:             str
    ivr_band:           str
    dte_band:           str
    underlying_pct_move: float
    observed_at:        str

    executed_contract:  str         # "CE|ATM|delta=0.52"
    executed_pnl:       float
    executed_pct_return: float

    best_contract:      str         # which contract would have performed best
    best_pnl:           float
    best_pct_return:    float

    selection_outcome:  str         # SEL_CORRECT / SEL_FAILURE / SEL_NEUTRAL
    improvement_possible: float     # best_pnl - executed_pnl (0 if correct)


class OptionsMultiContractShadow:
    """
    Tracks shadow outcomes for alternative option contracts.

    For each EXECUTED opportunity, records entry prices for shadow contracts.
    On exit, re-prices all contracts and classifies the selection quality.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._pending: Dict[str, List[ShadowContractRecord]] = {}  # opp_id → contracts
        self._outcomes: List[MultiContractOutcome] = []
        os.makedirs("data", exist_ok=True)
        self._load()

    # ── Public API ─────────────────────────────────────────────────────────

    def register_opportunity(
        self,
        opportunity_id:   str,
        executed_strike:  float,
        executed_type:    str,    # CE / PE
        executed_premium: float,
        executed_delta:   float,
        candidates: List[dict],   # [{"strike": X, "type": "CE", "premium": Y, "delta": Z, "iv": W}]
    ) -> None:
        """
        Register an executed opportunity and its candidate contracts.

        Call this at EXECUTION time to record entry prices for all shadow contracts.
        """
        records: List[ShadowContractRecord] = []
        executed_mon = _moneyness(executed_delta)

        # The executed contract
        records.append(ShadowContractRecord(
            opportunity_id=opportunity_id,
            is_executed=True,
            option_type=executed_type,
            strike=executed_strike,
            moneyness=executed_mon,
            delta_at_entry=executed_delta,
            entry_premium=executed_premium,
            exit_premium=None,
            hypothetical_pnl=None,
            pct_return=None,
        ))

        # Shadow contracts (candidates that were not selected)
        for c in candidates:
            if abs(c.get("strike", 0) - executed_strike) < 0.01 and c.get("type", "") == executed_type:
                continue  # skip the executed contract
            cand_delta = c.get("delta", 0.0)
            records.append(ShadowContractRecord(
                opportunity_id=opportunity_id,
                is_executed=False,
                option_type=c.get("type", "CE"),
                strike=c.get("strike", 0.0),
                moneyness=_moneyness(cand_delta),
                delta_at_entry=cand_delta,
                entry_premium=c.get("premium", 0.0),
                exit_premium=None,
                hypothetical_pnl=None,
                pct_return=None,
                iv_at_entry=c.get("iv", 0.0),
            ))

        with self._lock:
            self._pending[opportunity_id] = records
            self._save_locked()

        log.debug(
            "[MultiContractShadow] Registered %s: 1 executed + %d shadow contracts.",
            opportunity_id, len(records) - 1,
        )

    def record_exit(
        self,
        opportunity_id:     str,
        exit_premiums:      Dict[str, float],   # key: "CE|22500" → exit premium
        symbol:             str,
        strategy_name:      str,
        direction:          str,
        regime:             str,
        ivr_band:           str,
        dte_band:           str,
        underlying_pct_move: float,
        observed_at:        Optional[str] = None,
    ) -> Optional[MultiContractOutcome]:
        """
        Record exit prices for all shadow contracts and compute selection quality.

        Parameters
        ----------
        exit_premiums : map of "CE|22500" → exit_premium
                        Supply what you know; unmapped contracts are skipped.
        """
        now = observed_at or datetime.now().isoformat()
        with self._lock:
            if opportunity_id not in self._pending:
                return None

            records = self._pending[opportunity_id]

            # Fill exit premiums
            for rec in records:
                key = f"{rec.option_type}|{int(rec.strike)}"
                if key in exit_premiums and rec.entry_premium > 0:
                    rec.exit_premium = exit_premiums[key]
                    rec.hypothetical_pnl = (rec.exit_premium - rec.entry_premium)
                    rec.pct_return = (rec.hypothetical_pnl / rec.entry_premium * 100.0)
                    rec.outcome_recorded = True

            # Evaluate selection quality
            executed = next((r for r in records if r.is_executed), None)
            shadows  = [r for r in records if not r.is_executed and r.outcome_recorded]

            if not executed or not executed.outcome_recorded:
                return None

            exec_pnl     = executed.hypothetical_pnl or 0.0
            exec_pct     = executed.pct_return or 0.0
            exec_label   = f"{executed.option_type}|{executed.moneyness}|delta={executed.delta_at_entry:.2f}"

            if not shadows:
                # Only executed contract — can't compare
                best_pnl    = exec_pnl
                best_pct    = exec_pct
                best_label  = exec_label
                selection   = SEL_NEUTRAL
                improvement = 0.0
            else:
                all_pnls = [(r.hypothetical_pnl or 0.0, r.pct_return or 0.0,
                             f"{r.option_type}|{r.moneyness}|delta={r.delta_at_entry:.2f}")
                            for r in shadows]
                best_pnl, best_pct, best_label = max(all_pnls, key=lambda x: x[0])

                if best_pnl <= 0:
                    selection   = SEL_NEUTRAL
                    improvement = 0.0
                elif exec_pnl >= best_pnl * SELECTION_CORRECTNESS_THRESHOLD:
                    selection   = SEL_CORRECT
                    improvement = 0.0
                else:
                    selection   = SEL_FAILURE
                    improvement = best_pnl - exec_pnl

            outcome = MultiContractOutcome(
                opportunity_id=opportunity_id,
                symbol=symbol,
                strategy_name=strategy_name,
                direction=direction,
                regime=regime,
                ivr_band=ivr_band,
                dte_band=dte_band,
                underlying_pct_move=underlying_pct_move,
                observed_at=now,
                executed_contract=exec_label,
                executed_pnl=exec_pnl,
                executed_pct_return=exec_pct,
                best_contract=best_label,
                best_pnl=best_pnl,
                best_pct_return=best_pct,
                selection_outcome=selection,
                improvement_possible=improvement,
            )

            self._outcomes.append(outcome)
            del self._pending[opportunity_id]
            self._save_locked()

            log.info(
                "[MultiContractShadow] %s %s: %s exec_pnl=%.0f best_pnl=%.0f improvement=%.0f",
                symbol, strategy_name, selection, exec_pnl, best_pnl, improvement,
            )
            return outcome

    def get_selection_quality_summary(self) -> Dict:
        """Overall selection quality statistics."""
        with self._lock:
            total = len(self._outcomes)
            correct = sum(1 for o in self._outcomes if o.selection_outcome == SEL_CORRECT)
            failure = sum(1 for o in self._outcomes if o.selection_outcome == SEL_FAILURE)
            improvements = [o.improvement_possible for o in self._outcomes if o.selection_outcome == SEL_FAILURE]
            return {
                "total": total,
                "correct_rate": correct / total if total else 0.0,
                "failure_rate": failure / total if total else 0.0,
                "avg_improvement_when_wrong": sum(improvements) / len(improvements) if improvements else 0.0,
                "failures": [vars(o) for o in self._outcomes if o.selection_outcome == SEL_FAILURE][-5:],
            }

    def get_outcomes(self) -> List[MultiContractOutcome]:
        with self._lock:
            return list(self._outcomes)

    # ── Persistence ────────────────────────────────────────────────────────

    def _save_locked(self) -> None:
        try:
            data = {
                "pending": {
                    opp: [vars(r) for r in recs]
                    for opp, recs in self._pending.items()
                },
                "outcomes": [vars(o) for o in self._outcomes],
                "saved_at": datetime.now().isoformat(),
            }
            tmp = _PERSIST_PATH + ".tmp"
            with open(tmp, "w") as f:
                json.dump(data, f, default=str, indent=2)
            os.replace(tmp, _PERSIST_PATH)
        except Exception as exc:
            log.debug("[MultiContractShadow] Save error: %s", exc)

    def _load(self) -> None:
        try:
            if not os.path.exists(_PERSIST_PATH):
                return
            with open(_PERSIST_PATH) as f:
                data = json.load(f)
            for opp_id, recs in data.get("pending", {}).items():
                self._pending[opp_id] = [ShadowContractRecord(**r) for r in recs]
            for o in data.get("outcomes", []):
                self._outcomes.append(MultiContractOutcome(**o))
            log.info(
                "[MultiContractShadow] Loaded %d pending, %d outcomes.",
                len(self._pending), len(self._outcomes),
            )
        except Exception as exc:
            log.debug("[MultiContractShadow] Load error: %s", exc)
            self._pending = {}
            self._outcomes = []
