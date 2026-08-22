"""
knowledge_authority/kda_comparative.py
========================================
KDA-002 — Three-way comparison: KDA vs StrategyLab vs Scanner-only baseline.

Comparison types:
  BOTH_AGREE             — KDA directional AND StrategyLab PASS
  BOTH_REJECT            — KDA WAIT/HOLD AND StrategyLab REJECT
  KDA_OVERRULES_STRATEGY — KDA directional, StrategyLab REJECT
  STRATEGY_OVERRULES_KDA — KDA WAIT/HOLD, StrategyLab PASS
  KDA_ONLY               — no StrategyLab context available
  STRATEGY_ONLY          — KDA has no evidence, StrategyLab has view

Overrule outcomes:
  KNOWLEDGE_SUCCESSFUL_OVERRULE — KDA overruled + direction was correct
  KNOWLEDGE_FALSE_OVERRULE      — KDA overruled + direction was wrong
  FALSE_KNOWLEDGE_REJECTION     — KDA rejected + meaningful move happened
  FALSE_KNOWLEDGE_SELECTION     — KDA selected + move failed

Scanner baseline:
  scanner_confidence >= SCANNER_APPROVAL_THRESHOLD → scanner approves signal
  Direction = observation direction (BUY/SELL from scanner)

Safety contract:
  broker_calls = 0, orders = 0, no_lookahead = True, PAPER_TRADING unchanged
"""
from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional, Tuple

from .kda_models import KDADecision, KDADecisionRecord
from .kda_outcome_models import (
    ComparisonType,
    KDAComparisonRecord,
    OutcomeClass,
    OverruleResult,
)

# Scanner approves when confidence >= this threshold
_SCANNER_APPROVAL_THRESHOLD = 6.0

# Meaningful move threshold for missed-opportunity / false-selection detection
_MEANINGFUL_MOVE_PCT = 2.0

_DIRECTIONAL_DECISIONS = {
    KDADecision.KNOWLEDGE_BUY.value,
    KDADecision.KNOWLEDGE_SELL.value,
}
_NON_DIRECTIONAL_DECISIONS = {
    KDADecision.KNOWLEDGE_WAIT.value,
    KDADecision.KNOWLEDGE_HOLD.value,
    KDADecision.KNOWLEDGE_EXIT.value,
}


class KDAComparativeAnalyzer:
    """
    Produces KDAComparisonRecord for each opportunity where KDA data is available,
    benchmarked against StrategyLab and a naive scanner-only baseline.
    Stateless — all computation is per-call.
    """

    def compare(
        self,
        kda_record:       KDADecisionRecord,
        strategy_status:  Optional[str],     # "PASS" / "REJECT" / "UNKNOWN" / None
        outcome:          Optional[Dict[str, Any]] = None,  # KDAOutcomeRecord.as_dict()
        trading_date:     Optional[str] = None,
    ) -> KDAComparisonRecord:
        """
        Build a comparison record.
        outcome is the KDAOutcomeRecord.as_dict() for the same decision (may be None).
        """
        kda_decision = kda_record.decision.value
        is_kda_directional = kda_decision in _DIRECTIONAL_DECISIONS

        # Scanner baseline: approve if scanner_confidence >= threshold
        scanner_conf = kda_record.knowledge_score
        scanner_approves = (scanner_conf is not None and scanner_conf >= _SCANNER_APPROVAL_THRESHOLD)
        scanner_signal = kda_record.direction if scanner_approves else "HOLD"

        strat_upper = (strategy_status or "UNKNOWN").upper()
        strat_passes = strat_upper == "PASS"

        # Comparison type
        if strategy_status is None:
            comp_type = ComparisonType.KDA_ONLY
        elif is_kda_directional and strat_passes:
            comp_type = ComparisonType.BOTH_AGREE
        elif is_kda_directional and not strat_passes:
            comp_type = ComparisonType.KDA_OVERRULES_STRATEGY
        elif not is_kda_directional and strat_passes:
            comp_type = ComparisonType.STRATEGY_OVERRULES_KDA
        else:
            comp_type = ComparisonType.BOTH_REJECT

        # Extract outcome fields
        out_class      = outcome.get("outcome_class")  if outcome else None
        return_t5      = outcome.get("return_t5")      if outcome else None
        dir_correct    = outcome.get("direction_correct") if outcome else None
        target_hit     = outcome.get("target_hit")     if outcome else None
        stop_hit       = outcome.get("stop_hit")       if outcome else None

        kda_correct      = _is_decision_correct(out_class, is_kda_directional, dir_correct)
        strategy_correct = _strat_correct(strat_passes, dir_correct, return_t5)
        scanner_correct  = _scanner_correct(scanner_approves, dir_correct, return_t5)

        # Overrule analysis
        overrule_result = _classify_overrule(
            comp_type, is_kda_directional, kda_correct, dir_correct,
            return_t5, out_class,
        )

        td = trading_date or kda_record.timestamp[:10]

        return KDAComparisonRecord(
            comparison_id     = str(uuid.uuid4()),
            decision_id       = kda_record.decision_id,
            symbol            = kda_record.symbol,
            trading_date      = td,
            kda_decision      = kda_decision,
            strategy_decision = strat_upper if strategy_status else None,
            scanner_signal    = scanner_signal,
            comparison_type   = comp_type.value,
            overrule_result   = overrule_result,
            outcome_class     = out_class,
            return_t5         = return_t5,
            direction_correct = dir_correct,
            target_hit        = target_hit,
            stop_hit          = stop_hit,
            kda_correct       = kda_correct,
            strategy_correct  = strategy_correct,
            scanner_correct   = scanner_correct,
            no_lookahead      = True,
            broker_calls      = 0,
            orders            = 0,
        )

    # ── aggregate helpers ─────────────────────────────────────────────────

    @staticmethod
    def summarize(records: List[KDAComparisonRecord]) -> Dict[str, Any]:
        """
        Compute summary metrics for a list of comparison records.
        Does NOT use future data — all records must already have outcome set.
        """
        if not records:
            return {"n": 0, "status": "INSUFFICIENT_SAMPLE"}

        kda_correct   = [r for r in records if r.kda_correct is True]
        strat_correct = [r for r in records if r.strategy_correct is True]
        scan_correct  = [r for r in records if r.scanner_correct is True]

        def _acc(correct_list: list, total: list) -> Optional[float]:
            complete = [r for r in total if r.direction_correct is not None]
            if not complete:
                return None
            return sum(1 for r in complete if r.kda_correct is True) / len(complete) if correct_list is kda_correct else \
                   sum(1 for r in complete if r.strategy_correct is True) / len(complete) if correct_list is strat_correct else \
                   sum(1 for r in complete if r.scanner_correct is True) / len(complete)

        kda_acc  = _safe_rate([r.kda_correct      for r in records])
        strat_acc = _safe_rate([r.strategy_correct for r in records])
        scan_acc  = _safe_rate([r.scanner_correct  for r in records])

        overrule_recs = [r for r in records if r.comparison_type == ComparisonType.KDA_OVERRULES_STRATEGY.value]
        successful_overrules = sum(1 for r in overrule_recs
                                   if r.overrule_result == OverruleResult.KNOWLEDGE_SUCCESSFUL_OVERRULE.value)
        false_overrules      = sum(1 for r in overrule_recs
                                   if r.overrule_result == OverruleResult.KNOWLEDGE_FALSE_OVERRULE.value)

        missed = sum(1 for r in records if r.overrule_result == OverruleResult.FALSE_KNOWLEDGE_REJECTION.value)
        false_sel = sum(1 for r in records if r.overrule_result == OverruleResult.FALSE_KNOWLEDGE_SELECTION.value)

        return {
            "n": len(records),
            "kda_direction_accuracy":      kda_acc,
            "strategy_direction_accuracy": strat_acc,
            "scanner_direction_accuracy":  scan_acc,
            "overrule_count":              len(overrule_recs),
            "successful_overrules":        successful_overrules,
            "false_overrules":             false_overrules,
            "missed_opportunities":        missed,
            "false_selections":            false_sel,
            "comparison_type_counts": {
                ct.value: sum(1 for r in records if r.comparison_type == ct.value)
                for ct in ComparisonType
            },
        }


# ─────────────────────────────────────────────────────────────────────────────
# Pure helper functions
# ─────────────────────────────────────────────────────────────────────────────

def _is_decision_correct(
    out_class: Optional[str],
    is_directional: bool,
    dir_correct: Optional[bool],
) -> Optional[bool]:
    if out_class is None:
        return None
    correct = {"CORRECT_BUY", "CORRECT_SELL", "CORRECT_WAIT", "CORRECT_HOLD", "CORRECT_EXIT"}
    if out_class in correct:
        return True
    if out_class == "UNRESOLVED":
        return None
    return False


def _strat_correct(
    strat_passes: bool,
    dir_correct: Optional[bool],
    return_t5: Optional[float],
) -> Optional[bool]:
    if dir_correct is None:
        return None
    if strat_passes:
        return dir_correct  # strategy said trade → correct if direction was right
    else:
        # Strategy said no-trade → correct if there was no meaningful move
        if return_t5 is not None:
            return abs(return_t5) < _MEANINGFUL_MOVE_PCT
        return None


def _scanner_correct(
    scanner_approves: bool,
    dir_correct: Optional[bool],
    return_t5: Optional[float],
) -> Optional[bool]:
    if scanner_approves:
        return dir_correct
    else:
        if return_t5 is not None:
            return abs(return_t5) < _MEANINGFUL_MOVE_PCT
        return None


def _classify_overrule(
    comp_type:       ComparisonType,
    is_kda_dir:      bool,
    kda_correct:     Optional[bool],
    dir_correct:     Optional[bool],
    return_t5:       Optional[float],
    out_class:       Optional[str],
) -> Optional[str]:
    if comp_type == ComparisonType.KDA_OVERRULES_STRATEGY:
        if kda_correct is True:
            return OverruleResult.KNOWLEDGE_SUCCESSFUL_OVERRULE.value
        if kda_correct is False:
            return OverruleResult.KNOWLEDGE_FALSE_OVERRULE.value
        return None

    if comp_type in (ComparisonType.BOTH_REJECT, ComparisonType.STRATEGY_OVERRULES_KDA):
        # KDA WAIT → check for missed opportunity
        if return_t5 is not None and abs(return_t5) >= _MEANINGFUL_MOVE_PCT:
            return OverruleResult.FALSE_KNOWLEDGE_REJECTION.value
        return None

    if comp_type in (ComparisonType.BOTH_AGREE, ComparisonType.KDA_ONLY):
        # KDA selected but wrong direction
        if is_kda_dir and dir_correct is False:
            return OverruleResult.FALSE_KNOWLEDGE_SELECTION.value
        return None

    return None


def _safe_rate(values: List[Optional[bool]]) -> Optional[float]:
    decided = [v for v in values if v is not None]
    if not decided:
        return None
    return sum(1 for v in decided if v) / len(decided)
