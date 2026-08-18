"""
scripts/knowledge_system/knowledge_pattern_miner_001.py
========================================================
Stage 2 — Pattern Miner (KSL-001).

Reads data/shadow_evidence_ledger.jsonl and detects statistically
meaningful patterns across C2 ranking, strategy, direction, and regime.

Pattern strength is NOT determined by raw count alone.
Uses effect size, consistency, and comparison against baseline.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from .ksl_models import (
    Classification,
    EvidenceRecord,
    MissReason,
    PatternRecord,
    PatternType,
    ResearchArea,
)

ROOT = Path(__file__).resolve().parent.parent.parent
LEDGER_PATH = ROOT / "data" / "shadow_evidence_ledger.jsonl"

# Minimum sample sizes before a pattern is considered real
MIN_SAMPLE_PATTERN       = 10   # minimum n to detect any pattern
MIN_SAMPLE_STRONG        = 20   # minimum n for strong pattern
MIN_STRENGTH_FOR_QUESTION = 0.35  # strength threshold to generate a research question

# Effect size thresholds
MIN_MISS_RATE_EFFECT   = 0.05   # miss_rate must be >5pp above naive expectation
MIN_FALSE_REJECT_EFFECT = 0.05
MIN_DIRECTION_DIFF     = 0.06   # dir_acc difference between UP and DOWN
MIN_REGIME_DIFF        = 0.10   # regime underperformance threshold
MISS_REASON_UNIFORM    = 1.0 / 3  # uniform baseline: 3 miss reason categories


# ─────────────────────────────────────────────────────────────────────────────
# Load evidence ledger
# ─────────────────────────────────────────────────────────────────────────────


def load_evidence(ledger_path: Path = LEDGER_PATH) -> List[Dict]:
    if not ledger_path.exists():
        return []
    records = []
    with open(ledger_path) as f:
        for line in f:
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return records


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────


def _safe_rate(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator > 0 else 0.0


def _strength(effect: float, n: int, consistency: float = 1.0) -> float:
    """Composite pattern strength [0,1]. Caps at 1.0."""
    effect_score = min(abs(effect) / 0.20, 1.0)     # effect / reference (20pp = max)
    sample_score = min(n / MIN_SAMPLE_STRONG, 1.0)   # sample coverage
    return min(effect_score * 0.5 + sample_score * 0.3 + consistency * 0.2, 1.0)


# ─────────────────────────────────────────────────────────────────────────────
# Individual pattern detectors
# ─────────────────────────────────────────────────────────────────────────────


def _detect_ranking_miss_rate(records: List[Dict], direction: str, regime: str) -> Optional[PatternRecord]:
    """Detect HIGH_RANKING_MISS_RATE: fraction of ≥2% movers that were RANKING_MISS."""
    subset = [r for r in records
              if r.get("direction") == direction
              and (regime == "ALL" or r.get("regime") == regime)
              and r.get("classification") in (Classification.RANKING_MISS.value,
                                               Classification.CORRECT_SELECT.value)]
    if len(subset) < MIN_SAMPLE_PATTERN:
        return None

    ge2_movers = [r for r in subset if r.get("ge2") is True]
    if not ge2_movers:
        return None

    total_ge2 = len(ge2_movers)
    missed_ge2 = sum(1 for r in ge2_movers if r.get("classification") == Classification.RANKING_MISS.value)
    miss_rate = _safe_rate(missed_ge2, total_ge2)

    # Baseline: random 5-from-20 capture = 25%
    baseline = 0.75  # 75% miss rate is expected baseline (15/20 not selected)
    effect = miss_rate - baseline  # positive means worse than expected — but this is expected

    # Better measure: what fraction of ≥2% movers did we MISS vs CATCH
    # If miss_rate > 55% (i.e., more than 55% of big movers missed), flag
    effect = miss_rate - 0.55
    n = total_ge2
    s = _strength(effect, n)

    if n < MIN_SAMPLE_PATTERN or effect < MIN_MISS_RATE_EFFECT:  # only flag HIGH miss rate
        return None

    # Characterize miss reasons
    reasons: Dict[str, int] = {}
    for r in ge2_movers:
        if r.get("classification") == Classification.RANKING_MISS.value:
            rr = r.get("miss_reason", "UNKNOWN")
            reasons[rr] = reasons.get(rr, 0) + 1
    top_reason = max(reasons, key=reasons.get) if reasons else "UNKNOWN"

    return PatternRecord(
        pattern_id=str(uuid.uuid4()),
        pattern_type=PatternType.HIGH_RANKING_MISS_RATE,
        area=ResearchArea.C2_RANKING,
        direction=direction,
        regime=regime,
        description=(
            f"{direction} {regime}: {missed_ge2}/{total_ge2} ({miss_rate:.1%}) ≥2% movers missed. "
            f"Top reason: {top_reason}"
        ),
        sample_size=n,
        effect_size=round(effect, 4),
        baseline=0.55,
        observed=round(miss_rate, 4),
        strength=round(s, 4),
        data={
            "total_ge2_movers": total_ge2,
            "ranking_miss_count": missed_ge2,
            "miss_rate": round(miss_rate, 4),
            "miss_reasons": reasons,
            "top_reason": top_reason,
        },
    )


def _detect_direction_asymmetry(records: List[Dict]) -> Optional[PatternRecord]:
    """Detect significant UP vs DOWN performance difference in top-5 selection."""
    def dir_acc(recs: List[Dict], direction: str) -> tuple:
        sel = [r for r in recs
               if r.get("direction") == direction
               and r.get("classification") == Classification.CORRECT_SELECT.value
               and r.get("ge2") is not None]
        if not sel:
            return 0.0, 0
        correct = sum(1 for r in sel if r.get("ge2") is True)
        return _safe_rate(correct, len(sel)), len(sel)

    up_acc, up_n = dir_acc(records, "UP")
    dn_acc, dn_n = dir_acc(records, "DOWN")

    if min(up_n, dn_n) < MIN_SAMPLE_PATTERN:
        return None

    diff = abs(up_acc - dn_acc)
    if diff < MIN_DIRECTION_DIFF:
        return None

    better = "UP" if up_acc > dn_acc else "DOWN"
    s = _strength(diff, min(up_n, dn_n))

    return PatternRecord(
        pattern_id=str(uuid.uuid4()),
        pattern_type=PatternType.DIRECTION_ASYMMETRY,
        area=ResearchArea.DIRECTION,
        direction="BOTH",
        regime="ALL",
        description=(
            f"Direction asymmetry: UP ge2={up_acc:.3f} (n={up_n}) vs "
            f"DOWN ge2={dn_acc:.3f} (n={dn_n}). {better} is significantly better."
        ),
        sample_size=up_n + dn_n,
        effect_size=round(diff, 4),
        baseline=min(up_acc, dn_acc),
        observed=max(up_acc, dn_acc),
        strength=round(s, 4),
        data={"up_ge2": round(up_acc, 4), "up_n": up_n, "dn_ge2": round(dn_acc, 4), "dn_n": dn_n},
    )


def _detect_false_reject_rate(records: List[Dict], direction: str) -> Optional[PatternRecord]:
    """Detect HIGH FALSE_REJECT_RATE: fraction of strategy-rejected that would have qualified."""
    rejected = [r for r in records
                if r.get("direction") == direction
                and r.get("classification") in (Classification.FALSE_REJECT.value,
                                                 Classification.CORRECT_REJECT.value)]
    if len(rejected) < MIN_SAMPLE_PATTERN:
        return None

    false_r = sum(1 for r in rejected if r.get("classification") == Classification.FALSE_REJECT.value)
    rate = _safe_rate(false_r, len(rejected))
    effect = rate - 0.10  # baseline: 10% false-reject expected

    if abs(effect) < MIN_FALSE_REJECT_EFFECT:
        return None

    s = _strength(effect, len(rejected))

    return PatternRecord(
        pattern_id=str(uuid.uuid4()),
        pattern_type=PatternType.FALSE_REJECT_RATE,
        area=ResearchArea.STRATEGY,
        direction=direction,
        regime="ALL",
        description=(
            f"{direction}: {false_r}/{len(rejected)} ({rate:.1%}) strategy-rejected candidates "
            f"were false rejections (would have been ≥2% movers)."
        ),
        sample_size=len(rejected),
        effect_size=round(effect, 4),
        baseline=0.10,
        observed=round(rate, 4),
        strength=round(s, 4),
        data={"false_rejections": false_r, "total_rejections": len(rejected), "rate": round(rate, 4)},
    )


def _detect_regime_underperformance(records: List[Dict], direction: str, regime: str) -> Optional[PatternRecord]:
    """Detect significant underperformance of a specific regime+direction combination."""
    overall = [r for r in records
               if r.get("direction") == direction
               and r.get("classification") == Classification.CORRECT_SELECT.value
               and r.get("ge2") is not None]
    in_regime = [r for r in overall if r.get("regime") == regime]

    if len(overall) < MIN_SAMPLE_PATTERN or len(in_regime) < 5:
        return None

    overall_ge2 = _safe_rate(sum(1 for r in overall if r.get("ge2")), len(overall))
    regime_ge2  = _safe_rate(sum(1 for r in in_regime if r.get("ge2")), len(in_regime))
    diff = overall_ge2 - regime_ge2  # positive means regime underperforms

    if diff < MIN_REGIME_DIFF:
        return None

    s = _strength(diff, len(in_regime))

    return PatternRecord(
        pattern_id=str(uuid.uuid4()),
        pattern_type=PatternType.REGIME_UNDERPERFORMANCE,
        area=ResearchArea.REGIME,
        direction=direction,
        regime=regime,
        description=(
            f"Regime underperformance: {direction}+{regime} ge2={regime_ge2:.3f} (n={len(in_regime)}) "
            f"vs overall ge2={overall_ge2:.3f} (n={len(overall)}). "
            f"Deficit: {diff:.3f}"
        ),
        sample_size=len(in_regime),
        effect_size=round(diff, 4),
        baseline=round(overall_ge2, 4),
        observed=round(regime_ge2, 4),
        strength=round(s, 4),
        data={"regime_ge2": round(regime_ge2, 4), "overall_ge2": round(overall_ge2, 4),
              "n_regime": len(in_regime), "n_overall": len(overall)},
    )


def _detect_miss_reason_concentration(records: List[Dict], direction: str) -> Optional[PatternRecord]:
    """Detect when OUTRANKED_BY_STRONGER_OPENERS is the dominant miss reason."""
    misses = [r for r in records
              if r.get("direction") == direction
              and r.get("classification") == Classification.RANKING_MISS.value]
    if len(misses) < MIN_SAMPLE_PATTERN:
        return None

    reason_counts: Dict[str, int] = {}
    for r in misses:
        rr = r.get("miss_reason", "UNKNOWN")
        reason_counts[rr] = reason_counts.get(rr, 0) + 1

    outranked = reason_counts.get(MissReason.OUTRANKED_BY_STRONGER_OPENERS.value, 0)
    rate = _safe_rate(outranked, len(misses))
    effect = rate - MISS_REASON_UNIFORM  # vs uniform baseline (1/3)

    if outranked < 5 or abs(effect) < MIN_MISS_RATE_EFFECT:
        return None

    s = _strength(effect, len(misses))

    return PatternRecord(
        pattern_id=str(uuid.uuid4()),
        pattern_type=PatternType.HIGH_RANKING_MISS_RATE,
        area=ResearchArea.C2_RANKING,
        direction=direction,
        regime="ALL",
        description=(
            f"{direction}: {outranked}/{len(misses)} ({rate:.1%}) ranking misses are "
            f"OUTRANKED_BY_STRONGER_OPENERS. This is {effect:+.1%} vs uniform baseline. "
            f"Suggests competition from higher-opening peers affects selection quality."
        ),
        sample_size=len(misses),
        effect_size=round(effect, 4),
        baseline=round(MISS_REASON_UNIFORM, 4),
        observed=round(rate, 4),
        strength=round(s, 4),
        data={
            "outranked_count": outranked,
            "total_misses": len(misses),
            "rate": round(rate, 4),
            "all_reasons": reason_counts,
            "top_reason": MissReason.OUTRANKED_BY_STRONGER_OPENERS.value,
            "miss_rate": round(rate, 4),
            "total_ge2_movers": len(misses),
        },
    )


def _detect_adverse_gap_dominance(records: List[Dict], direction: str) -> Optional[PatternRecord]:
    """Detect when ADVERSE_OPEN_GAP is the dominant miss reason."""
    misses = [r for r in records
              if r.get("direction") == direction
              and r.get("classification") == Classification.RANKING_MISS.value]
    if len(misses) < MIN_SAMPLE_PATTERN:
        return None

    adverse = sum(1 for r in misses if r.get("miss_reason") == MissReason.ADVERSE_OPEN_GAP.value)
    rate = _safe_rate(adverse, len(misses))
    effect = rate - 0.25  # baseline expectation

    if adverse < 5 or abs(effect) < MIN_MISS_RATE_EFFECT:
        return None

    s = _strength(effect, len(misses))

    return PatternRecord(
        pattern_id=str(uuid.uuid4()),
        pattern_type=PatternType.ADVERSE_GAP_DOMINATES,
        area=ResearchArea.C2_RANKING,
        direction=direction,
        regime="ALL",
        description=(
            f"{direction}: {adverse}/{len(misses)} ({rate:.1%}) ranking misses are ADVERSE_OPEN_GAP. "
            f"These candidates gapped against direction but still moved favorably."
        ),
        sample_size=len(misses),
        effect_size=round(effect, 4),
        baseline=0.25,
        observed=round(rate, 4),
        strength=round(s, 4),
        data={"adverse_gap_misses": adverse, "total_misses": len(misses), "rate": round(rate, 4)},
    )


# ─────────────────────────────────────────────────────────────────────────────
# Main miner
# ─────────────────────────────────────────────────────────────────────────────


def mine_patterns(ledger_path: Path = LEDGER_PATH) -> List[PatternRecord]:
    """
    Run all pattern detectors against the evidence ledger.
    Returns patterns above the strength threshold.
    """
    records = load_evidence(ledger_path)
    if not records:
        return []

    patterns: List[PatternRecord] = []

    for direction in ["UP", "DOWN"]:
        # Ranking miss rate (all regimes combined)
        p = _detect_ranking_miss_rate(records, direction, "ALL")
        if p and p.strength >= MIN_STRENGTH_FOR_QUESTION:
            patterns.append(p)

        # Miss rate by regime
        for regime in ["BULL", "BEAR", "RANGE"]:
            p = _detect_ranking_miss_rate(records, direction, regime)
            if p and p.strength >= MIN_STRENGTH_FOR_QUESTION:
                patterns.append(p)

        # Miss reason concentration (OUTRANKED_BY_STRONGER_OPENERS)
        p = _detect_miss_reason_concentration(records, direction)
        if p and p.strength >= MIN_STRENGTH_FOR_QUESTION:
            patterns.append(p)

        # False reject rate
        p = _detect_false_reject_rate(records, direction)
        if p and p.strength >= MIN_STRENGTH_FOR_QUESTION:
            patterns.append(p)

        # Adverse gap dominance
        p = _detect_adverse_gap_dominance(records, direction)
        if p and p.strength >= MIN_STRENGTH_FOR_QUESTION:
            patterns.append(p)

        # Regime underperformance
        for regime in ["BULL", "BEAR", "RANGE"]:
            p = _detect_regime_underperformance(records, direction, regime)
            if p and p.strength >= MIN_STRENGTH_FOR_QUESTION:
                patterns.append(p)

    # Direction asymmetry (both directions combined)
    p = _detect_direction_asymmetry(records)
    if p and p.strength >= MIN_STRENGTH_FOR_QUESTION:
        patterns.append(p)

    # Sort by strength descending
    patterns.sort(key=lambda x: x.strength, reverse=True)
    return patterns
