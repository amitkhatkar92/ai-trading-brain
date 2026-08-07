"""predictive_gap/pga_root_cause.py — Root cause analysis for PGA-001 misses."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import List

from .pga_analyzer import (
    StockAnalysis,
    MISS_CORRECT, MISS_MISSED_WINNER, MISS_MISSED_LOSER,
    MISS_WRONG_DIRECTION, MISS_NO_DATA,
    PRED_NO, PRED_PART, PRED_YES,
    WP_NO, WP_PARTIALLY, WP_YES,
)
from .pga_collector import DailyData
from .pga_config import PGAConfig, ROOT_CAUSES

log = logging.getLogger(__name__)


@dataclass
class RootCause:
    symbol: str
    miss_type: str
    primary_cause: str             # one of ROOT_CAUSES
    secondary_cause: str           # supporting factor
    can_improve: bool              # can IIOS improve this?
    reason_not_improvable: str     # why not, if applicable
    improvement_category: str      # "A"–"G" or ""
    explanation: str               # human-readable explanation
    evidence: List[str] = field(default_factory=list)  # data points supporting this


def _classify_root_cause(analysis: StockAnalysis, data: DailyData, cfg: PGAConfig) -> RootCause:
    """
    Determine the primary root cause for a miss or wrong prediction.

    Decision tree:
    1. CORRECT → no root cause
    2. Not in universe → Scanner gap
    3. In universe, not scanned → PMCI or MissingFeature
    4. Scanned but no decision → CDS (below threshold or portfolio constraint)
    5. Decision approved, wrong direction → WrongThreshold or DNA
    6. Decision rejected → depends on rejection reason
    7. Not predictable + large move → ExternalEvent or MissingHistoricalPattern
    """
    sym   = analysis.symbol
    move  = analysis.stock_move
    dec   = analysis.iios_decision
    sig   = analysis.iios_signal
    mt    = analysis.miss_type
    wp    = analysis.was_predicted
    pred  = analysis.was_predictable
    dna   = analysis.dna_coverage
    edges = analysis.edge_coverage
    in_universe = sym in data.universe_symbols
    evidence: List[str] = []

    # ── CASE 0: Correct prediction ───────────────────────────────────
    if mt == MISS_CORRECT:
        return RootCause(
            symbol=sym, miss_type=mt,
            primary_cause="None", secondary_cause="",
            can_improve=False, reason_not_improvable="Prediction was correct",
            improvement_category="", explanation="No miss — IIOS predicted correctly",
        )

    # ── CASE 1: No data (stock barely moved) ─────────────────────────
    if mt == MISS_NO_DATA:
        return RootCause(
            symbol=sym, miss_type=mt,
            primary_cause="None", secondary_cause="",
            can_improve=False, reason_not_improvable="Insufficient price movement",
            improvement_category="", explanation="Stock moved < threshold — not a miss",
        )

    # ── CASE 2: Not in universe ───────────────────────────────────────
    if not in_universe and sig is None and dec is None:
        if pred == PRED_NO and abs(move.daily_return_pct) > 8.0:
            evidence.append(f"Move: {move.daily_return_pct:+.1f}% — likely external event")
            return RootCause(
                symbol=sym, miss_type=mt,
                primary_cause="ExternalEvent", secondary_cause="Scanner",
                can_improve=False,
                reason_not_improvable="External catalyst (earnings/news) — not predictable from OHLCV",
                improvement_category="",
                explanation=f"{sym} moved {move.daily_return_pct:+.1f}% on likely external event",
                evidence=evidence,
            )
        evidence.append(f"Not in universe of {len(data.universe_symbols)} symbols")
        evidence.append(f"DNA coverage: {dna}")
        return RootCause(
            symbol=sym, miss_type=mt,
            primary_cause="Scanner", secondary_cause="MissingData",
            can_improve=True, reason_not_improvable="",
            improvement_category="E" if dna == 0 else "A",
            explanation=f"{sym} not in IIOS universe — scanner coverage gap",
            evidence=evidence,
        )

    # ── CASE 3: In universe, not scanned ──────────────────────────────
    if in_universe and sig is None and dec is None:
        if dna == 0:
            evidence.append(f"In universe, zero DNA patterns for {sym}")
            return RootCause(
                symbol=sym, miss_type=mt,
                primary_cause="DNA", secondary_cause="PMCI",
                can_improve=True, reason_not_improvable="",
                improvement_category="E",
                explanation=f"{sym} in universe but no DNA — DNA gap; PMCI couldn't generate signal",
                evidence=evidence,
            )
        else:
            evidence.append(f"DNA coverage: {dna} patterns, edges: {edges}")
            evidence.append("PMCI scan ran but didn't generate signal for this symbol")
            return RootCause(
                symbol=sym, miss_type=mt,
                primary_cause="PMCI", secondary_cause="DNA",
                can_improve=True, reason_not_improvable="",
                improvement_category="A" if dna >= cfg.dna_coverage_min else "B",
                explanation=f"{sym} in universe with DNA={dna} but scanner didn't select it "
                           f"— PMCI threshold or feature weighting issue",
                evidence=evidence,
            )

    # ── CASE 4: Decision approved, wrong direction ───────────────────
    if mt == MISS_WRONG_DIRECTION and dec is not None and dec.approved:
        evidence.append(f"Decision: {dec.direction} conf={dec.confidence:.1f}")
        evidence.append(f"Actual move: {move.actual_direction} ({move.daily_return_pct:+.1f}%)")
        if dna > 0:
            evidence.append(f"DNA coverage: {dna} — pattern misread direction")
            return RootCause(
                symbol=sym, miss_type=mt,
                primary_cause="DNA", secondary_cause="WrongThreshold",
                can_improve=True, reason_not_improvable="",
                improvement_category="B",
                explanation=f"{sym} approved {dec.direction} but moved opposite — "
                           f"DNA directional bias incorrect",
                evidence=evidence,
            )
        else:
            return RootCause(
                symbol=sym, miss_type=mt,
                primary_cause="WrongThreshold", secondary_cause="MissingHistoricalPattern",
                can_improve=True, reason_not_improvable="",
                improvement_category="F",
                explanation=f"{sym} approved {dec.direction} but moved opposite — "
                           f"insufficient historical context for directional bias",
                evidence=evidence,
            )

    # ── CASE 5: Rejected decision ─────────────────────────────────────
    if dec is not None and not dec.approved:
        rej_reason = dec.rejection_reason.upper()
        evidence.append(f"Rejection reason: {dec.rejection_reason or 'below threshold'}")
        evidence.append(f"Confidence: {dec.confidence:.1f}, threshold: {cfg.predicted_threshold}")

        if "HEAT" in rej_reason or "PORTFOLIO" in rej_reason or "POSITION_LIMIT" in rej_reason:
            return RootCause(
                symbol=sym, miss_type=mt,
                primary_cause="PortfolioConstraint", secondary_cause="RiskFilter",
                can_improve=False,
                reason_not_improvable="Portfolio was at capacity — this is intended behavior",
                improvement_category="",
                explanation=f"{sym} rejected due to portfolio heat/capacity constraint "
                           f"— correct risk management, not an error",
                evidence=evidence,
            )

        if "RR" in rej_reason or "RISK" in rej_reason:
            return RootCause(
                symbol=sym, miss_type=mt,
                primary_cause="RiskFilter", secondary_cause="CDS",
                can_improve=True, reason_not_improvable="",
                improvement_category="A",
                explanation=f"{sym} rejected by risk filter — R:R threshold calibration",
                evidence=evidence,
            )

        # Below confidence threshold
        if dec.confidence < cfg.predicted_threshold:
            if dna < cfg.dna_coverage_min:
                cat = "E"
                primary = "DNA"
                explanation = (f"{sym} conf={dec.confidence:.1f} below threshold {cfg.predicted_threshold} "
                               f"— insufficient DNA to build strong signal")
            else:
                cat = "B"
                primary = "Knowledge"
                explanation = (f"{sym} conf={dec.confidence:.1f} below threshold {cfg.predicted_threshold} "
                               f"— knowledge exists but insufficient confidence")
            return RootCause(
                symbol=sym, miss_type=mt,
                primary_cause=primary, secondary_cause="CDS",
                can_improve=True, reason_not_improvable="",
                improvement_category=cat,
                explanation=explanation,
                evidence=evidence,
            )

        # Generic CDS rejection
        return RootCause(
            symbol=sym, miss_type=mt,
            primary_cause="CDS", secondary_cause="Knowledge",
            can_improve=True, reason_not_improvable="",
            improvement_category="B",
            explanation=f"{sym} rejected by CDS scoring — knowledge gap or calibration issue",
            evidence=evidence,
        )

    # ── CASE 6: Missed winner/loser with no signal at all ────────────
    if pred == PRED_NO:
        evidence.append(f"Not predictable: DNA={dna}, in_universe={in_universe}")
        evidence.append(f"Move: {move.daily_return_pct:+.1f}% ({move.move_type})")
        if abs(move.daily_return_pct) > 8.0:
            return RootCause(
                symbol=sym, miss_type=mt,
                primary_cause="ExternalEvent", secondary_cause="MissingData",
                can_improve=False,
                reason_not_improvable="Likely external catalyst — not derivable from available data",
                improvement_category="",
                explanation=f"{sym} {move.daily_return_pct:+.1f}% — likely external event",
                evidence=evidence,
            )
        return RootCause(
            symbol=sym, miss_type=mt,
            primary_cause="MissingHistoricalPattern", secondary_cause="Research",
            can_improve=True, reason_not_improvable="",
            improvement_category="F",
            explanation=f"{sym} missed — no historical patterns available for this setup",
            evidence=evidence,
        )

    if dna == 0:
        evidence.append("Zero DNA coverage")
        return RootCause(
            symbol=sym, miss_type=mt,
            primary_cause="DNA", secondary_cause="Research",
            can_improve=True, reason_not_improvable="",
            improvement_category="E",
            explanation=f"{sym} missed — DNA gap, no institutional patterns for this symbol",
            evidence=evidence,
        )

    if edges == 0:
        evidence.append("No active edges")
        return RootCause(
            symbol=sym, miss_type=mt,
            primary_cause="Knowledge", secondary_cause="Research",
            can_improve=True, reason_not_improvable="",
            improvement_category="G",
            explanation=f"{sym} missed — no discovered edges fire for this symbol/context",
            evidence=evidence,
        )

    # Generic research gap
    return RootCause(
        symbol=sym, miss_type=mt,
        primary_cause="Research", secondary_cause="Knowledge",
        can_improve=True, reason_not_improvable="",
        improvement_category="D",
        explanation=f"{sym} missed — needs dedicated research study to understand pattern",
        evidence=evidence,
    )


def analyze_misses(
    analyses: List[StockAnalysis],
    data: DailyData,
    cfg: PGAConfig,
) -> List[RootCause]:
    """
    Produce one RootCause record per analysed stock.
    Skips CORRECT and NO_DATA stocks from the verbose report,
    but still includes them for completeness.
    """
    causes: List[RootCause] = []
    for analysis in analyses:
        cause = _classify_root_cause(analysis, data, cfg)
        causes.append(cause)

    improvable = [c for c in causes if c.can_improve and c.miss_type not in (MISS_CORRECT, MISS_NO_DATA)]
    log.info(
        "[PGA] Root cause analysis: total=%d improvable=%d "
        "categories=%s",
        len(causes),
        len(improvable),
        dict.fromkeys(c.improvement_category for c in improvable if c.improvement_category),
    )

    return causes
