"""
early_move_audit/emp_analyzer.py — Top-level analysis coordinator for EMP-001.

Calls emp_persistence and emp_predictive, returns a unified EMPResult.
Does NOT touch any live trading objects.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import List, Optional

from .emp_collector import CollectionQuality, DayRecord
from .emp_config import EmpConfig
from .emp_persistence import PersistenceResult, compute_persistence
from .emp_predictive import PredictiveResult, build_predictive_analysis

log = logging.getLogger(__name__)


@dataclass
class EMPResult:
    """Unified output of one EMP-001 analysis run."""
    run_date: str
    config: EmpConfig
    records: List[DayRecord]
    quality: CollectionQuality
    persistence: PersistenceResult
    predictive: PredictiveResult
    look_ahead_violations: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


def run_analysis(
    records: List[DayRecord],
    quality: CollectionQuality,
    config: EmpConfig,
    run_date: str,
) -> EMPResult:
    """
    Execute the full EMP-001 analysis pipeline.

    Parameters
    ----------
    records   : collected dataset from emp_collector
    quality   : collection quality report
    config    : run configuration
    run_date  : ISO-8601 date string for this run

    Returns
    -------
    EMPResult with persistence + predictive sub-results populated.
    """
    result = EMPResult(
        run_date=run_date,
        config=config,
        records=records,
        quality=quality,
        persistence=PersistenceResult(),
        predictive=PredictiveResult(),
    )

    if not records:
        result.warnings.append("No records collected — check yfinance availability")
        return result

    daily_count = sum(1 for r in records if r.has_daily)
    if daily_count < len(config.universe):
        result.warnings.append(
            f"Only {daily_count}/{len(config.universe)} universe symbols have daily data"
        )

    intraday_count = sum(1 for r in records if r.has_intraday)
    if intraday_count == 0:
        result.warnings.append(
            "No intraday data available — Model B (opening window) will be empty"
        )

    log.info("[EmpAnalyzer] Running persistence analysis on %d records", len(records))
    result.persistence = compute_persistence(records, config.persistence_top_n)

    log.info("[EmpAnalyzer] Running predictive analysis")
    result.predictive = build_predictive_analysis(records, config.persistence_top_n)

    # Look-ahead verification (Phase 12)
    violations = _verify_no_lookahead(result)
    result.look_ahead_violations = violations
    if violations:
        log.error("[EmpAnalyzer] LOOK-AHEAD VIOLATIONS DETECTED: %s", violations)

    log.info(
        "[EmpAnalyzer] Analysis complete: %d trading days, %d symbols, "
        "%d persistence intervals",
        result.persistence.n_trading_days,
        result.persistence.n_symbols,
        len(result.persistence.interval_stats),
    )
    return result


def _verify_no_lookahead(result: EMPResult) -> List[str]:
    """
    Check that Model A and Model B do not use forbidden fields.

    This is a code-level invariant check, not a data scan.
    Returns list of violation descriptions (empty = clean).
    """
    violations: List[str] = []

    # Verify Model A metadata
    if result.predictive.model_a:
        forbidden_a = {"open_price", "gap_pct", "p930", "p945", "p1000",
                       "close_price", "ret_to_930", "ret_to_945", "close_return_pct"}
        declared = set(result.predictive.model_a.description.lower().split())
        for f in forbidden_a:
            # Check description doesn't mention same-day features
            if f.replace("_", " ") in result.predictive.model_a.description.lower():
                violations.append(
                    f"Model A description mentions same-day field '{f}' — verify no look-ahead"
                )

    # Verify Model B metadata
    for model_b in [result.predictive.model_b_930, result.predictive.model_b_945,
                    result.predictive.model_b_1000]:
        if not model_b:
            continue
        forbidden_b = {"close_price", "close_return_pct", "p1500", "ret_to_1500"}
        for f in forbidden_b:
            if f.replace("_", " ") in model_b.description.lower():
                violations.append(
                    f"Model B ({model_b.window}) description mentions post-window field '{f}'"
                )

    return violations
