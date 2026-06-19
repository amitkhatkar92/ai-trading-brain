"""
analysis/pattern_miner.py
============================
LEARNING_ENGINE_001 — Multi-factor pattern discovery.

No database writes. No IO. Pure analytics.

Discovers recurring multi-factor patterns across the audit layer:

    PREMIUM + HIGH_SFT + EARNINGS       → WR = 74%
    LOW + LOW_SFT + HIGH_VOL_REGIME     → WR = 8%
    HIGH_VOL + SHORT_STRANGLE           → PF = 0.099

A pattern is only reported when:
    - At least MIN_PATTERN_OBS observations
    - Win rate OR profit factor deviates > SIGNIFICANCE_GAP from baseline

Patterns are ranked by strength = |win_rate − baseline| * sqrt(n)
(approximates the z-score direction without requiring scipy)
"""

from __future__ import annotations

import math
import statistics
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


# ── Config ────────────────────────────────────────────────────────────────────

MIN_PATTERN_OBS   = 5      # minimum observations to report a pattern
SIGNIFICANCE_GAP  = 0.10   # WR must differ from baseline by >= 10pp to matter
BASELINE_WIN_RATE = 0.50   # null hypothesis: coin flip


# ── Data classes ──────────────────────────────────────────────────────────────

@dataclass
class Pattern:
    """A discovered multi-factor pattern with statistical strength."""
    factors:       Tuple[str, ...]   # e.g. ("PREMIUM", "HIGH_SFT", "EARNINGS")
    n:             int
    win_rate:      float             # 0.0–1.0
    avg_pnl:       float
    baseline_wr:   float
    wr_edge:       float             # win_rate − baseline_wr (signed)
    strength:      float             # |wr_edge| * sqrt(n)  — sort key
    direction:     str               # "POSITIVE" / "NEGATIVE"
    description:   str               # human-readable label
    source:        str               # which DB this came from


@dataclass
class PatternMineResult:
    patterns:  List[Pattern] = field(default_factory=list)
    baseline:  float         = BASELINE_WIN_RATE
    n_total:   int           = 0

    def top(self, n: int = 10) -> List[Pattern]:
        return sorted(self.patterns, key=lambda p: -p.strength)[:n]

    def positive(self, n: int = 10) -> List[Pattern]:
        return sorted(
            [p for p in self.patterns if p.direction == "POSITIVE"],
            key=lambda p: -p.strength
        )[:n]

    def negative(self, n: int = 10) -> List[Pattern]:
        return sorted(
            [p for p in self.patterns if p.direction == "NEGATIVE"],
            key=lambda p: -p.strength
        )[:n]


# ── Pattern extraction from trade_quality records ─────────────────────────────

def mine_quality_patterns(records: List[dict]) -> PatternMineResult:
    """
    Discover patterns from trade_quality_log records.

    Factors explored:
        quality_tier × sft_class
        quality_tier × market_regime
        quality_tier × sft_class × market_regime
        is_high_conviction × market_regime
    """
    result  = PatternMineResult(n_total=len(records))
    closed  = [r for r in records if r.get("outcome") in ("WIN", "LOSS", "BREAKEVEN")]
    if not closed:
        return result

    baseline = sum(1 for r in closed if r.get("outcome") == "WIN") / len(closed)
    result.baseline = baseline

    def _bucket(recs: list, factors: tuple, source: str) -> Optional[Pattern]:
        if len(recs) < MIN_PATTERN_OBS:
            return None
        wins   = [r for r in recs if r.get("outcome") == "WIN"]
        pnls   = [r["pnl"] for r in recs if r.get("pnl") is not None]
        wr     = len(wins) / len(recs)
        edge   = wr - baseline
        if abs(edge) < SIGNIFICANCE_GAP:
            return None
        return Pattern(
            factors     = factors,
            n           = len(recs),
            win_rate    = round(wr, 3),
            avg_pnl     = round(statistics.mean(pnls), 0) if pnls else 0.0,
            baseline_wr = round(baseline, 3),
            wr_edge     = round(edge, 3),
            strength    = round(abs(edge) * math.sqrt(len(recs)), 3),
            direction   = "POSITIVE" if edge > 0 else "NEGATIVE",
            description = " + ".join(factors),
            source      = source,
        )

    # quality_tier × sft_class
    buckets: Dict[tuple, list] = defaultdict(list)
    for r in closed:
        key = (r.get("quality_tier", "?"), r.get("sft_class", "?"))
        buckets[key].append(r)
    for key, recs in buckets.items():
        p = _bucket(recs, key, "trade_quality")
        if p:
            result.patterns.append(p)

    # quality_tier × market_regime
    buckets2: Dict[tuple, list] = defaultdict(list)
    for r in closed:
        key = (r.get("quality_tier", "?"), r.get("market_regime", "?"))
        buckets2[key].append(r)
    for key, recs in buckets2.items():
        p = _bucket(recs, key, "trade_quality")
        if p:
            result.patterns.append(p)

    # quality_tier × sft_class × market_regime (3-way)
    buckets3: Dict[tuple, list] = defaultdict(list)
    for r in closed:
        key = (
            r.get("quality_tier", "?"),
            r.get("sft_class", "?"),
            r.get("market_regime", "?"),
        )
        buckets3[key].append(r)
    for key, recs in buckets3.items():
        p = _bucket(recs, key, "trade_quality")
        if p:
            result.patterns.append(p)

    # is_high_conviction × market_regime
    buckets4: Dict[tuple, list] = defaultdict(list)
    for r in closed:
        hc  = "HIGH_CONVICTION" if r.get("is_high_conviction") else "NORMAL"
        key = (hc, r.get("market_regime", "?"))
        buckets4[key].append(r)
    for key, recs in buckets4.items():
        p = _bucket(recs, key, "trade_quality")
        if p:
            result.patterns.append(p)

    return result


# ── Pattern extraction from news_impact records ───────────────────────────────

def mine_news_patterns(records: List[dict]) -> PatternMineResult:
    """
    Discover patterns from news_impact_log records.

    Factors: news_type × sentiment × market_regime
    """
    result  = PatternMineResult(n_total=len(records))
    closed  = [r for r in records if r.get("outcome") in ("WIN", "LOSS", "BREAKEVEN")]
    if not closed:
        return result

    baseline       = sum(1 for r in closed if r.get("outcome") == "WIN") / len(closed)
    result.baseline = baseline

    def _bucket(recs: list, factors: tuple) -> Optional[Pattern]:
        if len(recs) < MIN_PATTERN_OBS:
            return None
        wins = [r for r in recs if r.get("outcome") == "WIN"]
        pnls = [r["pnl"] for r in recs if r.get("pnl") is not None]
        wr   = len(wins) / len(recs)
        edge = wr - baseline
        if abs(edge) < SIGNIFICANCE_GAP:
            return None
        return Pattern(
            factors     = factors,
            n           = len(recs),
            win_rate    = round(wr, 3),
            avg_pnl     = round(statistics.mean(pnls), 0) if pnls else 0.0,
            baseline_wr = round(baseline, 3),
            wr_edge     = round(edge, 3),
            strength    = round(abs(edge) * math.sqrt(len(recs)), 3),
            direction   = "POSITIVE" if edge > 0 else "NEGATIVE",
            description = " + ".join(factors),
            source      = "news_audit",
        )

    # news_type × sentiment
    b1: Dict[tuple, list] = defaultdict(list)
    for r in closed:
        b1[(r.get("news_type", "?"), r.get("sentiment", "?"))].append(r)
    for key, recs in b1.items():
        p = _bucket(recs, key)
        if p:
            result.patterns.append(p)

    # news_type × market_regime
    b2: Dict[tuple, list] = defaultdict(list)
    for r in closed:
        b2[(r.get("news_type", "?"), r.get("market_regime", "?"))].append(r)
    for key, recs in b2.items():
        p = _bucket(recs, key)
        if p:
            result.patterns.append(p)

    return result


# ── Pattern extraction from rejection records ─────────────────────────────────

def mine_rejection_patterns(records: List[dict]) -> PatternMineResult:
    """
    Discover patterns in which rejections are most / least accurate.

    Factors: rejected_reason × quality_tier
             rejected_reason × market_regime
    """
    result   = PatternMineResult(n_total=len(records))
    classified = [
        r for r in records
        if r.get("rejection_outcome") in ("CORRECT_REJECTION", "FALSE_REJECTION")
    ]
    if not classified:
        return result

    baseline       = (
        sum(1 for r in classified if r.get("rejection_outcome") == "CORRECT_REJECTION")
        / len(classified)
    )
    result.baseline = baseline

    def _bucket(recs: list, factors: tuple) -> Optional[Pattern]:
        if len(recs) < MIN_PATTERN_OBS:
            return None
        correct = [r for r in recs if r.get("rejection_outcome") == "CORRECT_REJECTION"]
        wr      = len(correct) / len(recs)    # "win" = correct rejection
        edge    = wr - baseline
        if abs(edge) < SIGNIFICANCE_GAP:
            return None
        moves = [r.get("move_5d_pct") or 0.0 for r in recs]
        return Pattern(
            factors     = factors,
            n           = len(recs),
            win_rate    = round(wr, 3),
            avg_pnl     = round(statistics.mean(moves), 2),  # avg price move used
            baseline_wr = round(baseline, 3),
            wr_edge     = round(edge, 3),
            strength    = round(abs(edge) * math.sqrt(len(recs)), 3),
            direction   = "POSITIVE" if edge > 0 else "NEGATIVE",
            description = " + ".join(factors),
            source      = "rejection_audit",
        )

    b1: Dict[tuple, list] = defaultdict(list)
    for r in classified:
        b1[(r.get("rejected_reason", "?"), r.get("quality_tier", "?"))].append(r)
    for key, recs in b1.items():
        p = _bucket(recs, key)
        if p:
            result.patterns.append(p)

    b2: Dict[tuple, list] = defaultdict(list)
    for r in classified:
        b2[(r.get("rejected_reason", "?"), r.get("market_regime", "?"))].append(r)
    for key, recs in b2.items():
        p = _bucket(recs, key)
        if p:
            result.patterns.append(p)

    return result


# ── Options pattern mining ────────────────────────────────────────────────────

def mine_options_patterns(records: List[dict]) -> PatternMineResult:
    """
    Discover patterns from option_trade_audit records.

    Factors: strategy × market_regime
             strategy × vix_bucket
    """
    result  = PatternMineResult(n_total=len(records))
    closed  = [r for r in records if r.get("win_loss") in ("WIN", "LOSS")]
    if not closed:
        return result

    baseline       = sum(1 for r in closed if r.get("win_loss") == "WIN") / len(closed)
    result.baseline = baseline

    def _bucket(recs: list, factors: tuple) -> Optional[Pattern]:
        if len(recs) < MIN_PATTERN_OBS:
            return None
        wins = [r for r in recs if r.get("win_loss") == "WIN"]
        pnls = [r["pnl"] for r in recs if r.get("pnl") is not None]
        wr   = len(wins) / len(recs)
        edge = wr - baseline
        if abs(edge) < SIGNIFICANCE_GAP:
            return None
        return Pattern(
            factors     = factors,
            n           = len(recs),
            win_rate    = round(wr, 3),
            avg_pnl     = round(statistics.mean(pnls), 0) if pnls else 0.0,
            baseline_wr = round(baseline, 3),
            wr_edge     = round(edge, 3),
            strength    = round(abs(edge) * math.sqrt(len(recs)), 3),
            direction   = "POSITIVE" if edge > 0 else "NEGATIVE",
            description = " + ".join(factors),
            source      = "options_audit",
        )

    b1: Dict[tuple, list] = defaultdict(list)
    for r in closed:
        b1[(r.get("strategy", "?"), r.get("market_regime", "?"))].append(r)
    for key, recs in b1.items():
        p = _bucket(recs, key)
        if p:
            result.patterns.append(p)

    b2: Dict[tuple, list] = defaultdict(list)
    for r in closed:
        b2[(r.get("strategy", "?"), r.get("vix_bucket", "?"))].append(r)
    for key, recs in b2.items():
        p = _bucket(recs, key)
        if p:
            result.patterns.append(p)

    return result
