"""
analysis/edge_detector.py
============================
LEARNING_ENGINE_001 — Filter strength ranking and edge detection.

No database writes. No IO. Pure analytics.

An "edge" is any filter, signal, or criterion whose accuracy deviates
meaningfully from the 50% baseline (coin flip).

Edge strength = (accuracy − 50%) × sqrt(n)
    — proportional to a one-sample z-score (H0: accuracy = 0.50)
    — safe to compute without scipy; directionally correct

Edge direction:
    POSITIVE  : filter correctly blocks bad trades (accuracy > 50%)
    NEGATIVE  : filter is blocking good trades   (accuracy < 50%)
    NEUTRAL   : within ±NEUTRAL_BAND of 50%

The system NEVER directly modifies execution or risk modules.
It only produces ranked evidence for human review.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional


# ── Config ────────────────────────────────────────────────────────────────────

BASELINE          = 0.50      # null hypothesis accuracy
NEUTRAL_BAND      = 0.05      # ±5pp from baseline = neutral
MIN_OBS_FOR_EDGE  = 10        # fewer observations = COLLECTING, no edge claim
STRONG_THRESHOLD  = 0.70      # >= 70% → STRONG edge
MODERATE_THRESHOLD= 0.55      # >= 55% → MODERATE


# ── Data classes ──────────────────────────────────────────────────────────────

class EdgeDirection:
    POSITIVE  = "POSITIVE"   # filter is working
    NEGATIVE  = "NEGATIVE"   # filter is hurting
    NEUTRAL   = "NEUTRAL"    # no signal
    COLLECTING= "COLLECTING" # not enough data


class EdgeStrength:
    STRONG    = "STRONG"
    MODERATE  = "MODERATE"
    WEAK      = "WEAK"
    NONE      = "NONE"
    COLLECTING= "COLLECTING"


@dataclass
class Edge:
    """One filter or signal with its computed edge metrics."""
    name:        str
    category:    str           # REJECTION_FILTER / QUALITY_TIER / NEWS_SIGNAL / OPTIONS
    accuracy:    float         # 0.0–1.0
    n_obs:       int
    edge_score:  float         # (accuracy − 0.50) × sqrt(n)
    direction:   str           # EdgeDirection
    strength:    str           # EdgeStrength
    action:      str           # concise governance action


@dataclass
class EdgeReport:
    edges:       List[Edge]  = field(default_factory=list)
    generated_at: str         = ""

    def by_direction(self, direction: str) -> List[Edge]:
        return [e for e in self.edges if e.direction == direction]

    def strong_positive(self) -> List[Edge]:
        return [e for e in self.edges
                if e.direction == EdgeDirection.POSITIVE
                and e.strength == EdgeStrength.STRONG]

    def negative_edges(self) -> List[Edge]:
        return [e for e in self.edges if e.direction == EdgeDirection.NEGATIVE]

    def ranked(self) -> List[Edge]:
        """All edges sorted by absolute edge_score descending."""
        return sorted(self.edges, key=lambda e: -abs(e.edge_score))


# ── Core scoring ──────────────────────────────────────────────────────────────

def compute_edge(
    name:     str,
    category: str,
    accuracy: float,          # raw accuracy fraction 0.0–1.0
    n_obs:    int,
) -> Edge:
    """Compute edge metrics for a single filter/signal."""
    if n_obs < MIN_OBS_FOR_EDGE:
        return Edge(
            name       = name,
            category   = category,
            accuracy   = accuracy,
            n_obs      = n_obs,
            edge_score = 0.0,
            direction  = EdgeDirection.COLLECTING,
            strength   = EdgeStrength.COLLECTING,
            action     = f"Collect {MIN_OBS_FOR_EDGE - n_obs} more observations",
        )

    score = (accuracy - BASELINE) * math.sqrt(n_obs)

    if accuracy >= STRONG_THRESHOLD:
        direction = EdgeDirection.POSITIVE
        strength  = EdgeStrength.STRONG
        action    = "Keep — strong signal"
    elif accuracy >= BASELINE + NEUTRAL_BAND:
        direction = EdgeDirection.POSITIVE
        strength  = (EdgeStrength.MODERATE if accuracy >= MODERATE_THRESHOLD
                     else EdgeStrength.WEAK)
        action    = "Watch — moderate signal" if accuracy >= MODERATE_THRESHOLD else "Watch — weak"
    elif accuracy >= BASELINE - NEUTRAL_BAND:
        direction = EdgeDirection.NEUTRAL
        strength  = EdgeStrength.NONE
        action    = "Neutral — no action"
    else:
        direction = EdgeDirection.NEGATIVE
        strength  = (EdgeStrength.STRONG   if accuracy < BASELINE - 0.20
                     else EdgeStrength.MODERATE)
        action    = "Review — possible false rejections"

    return Edge(
        name       = name,
        category   = category,
        accuracy   = round(accuracy, 4),
        n_obs      = n_obs,
        edge_score = round(score, 3),
        direction  = direction,
        strength   = strength,
        action     = action,
    )


# ── Batch computation from audit data dicts ──────────────────────────────────

def detect_rejection_edges(by_reason: Dict[str, dict]) -> List[Edge]:
    """
    Compute edges for each rejection reason.

    Args:
        by_reason: dict from RejectionTracker.accuracy_by_reason()
    """
    edges = []
    for reason, stats in by_reason.items():
        n   = stats.get("classified", 0)
        acc = stats.get("accuracy_pct", 0.0) / 100
        edges.append(compute_edge(reason, "REJECTION_FILTER", acc, n))
    return edges


def detect_quality_tier_edges(tier_stats: Dict[str, dict]) -> List[Edge]:
    """
    Compute edges for each quality tier.

    Note: for quality tiers the "accuracy" is the win rate.
    Tiers with VERY LOW win rate (LOW/MEDIUM) are NEGATIVE edges
    — their presence as approved trades is the problem.
    """
    edges = []
    for tier, stats in tier_stats.items():
        n   = stats.get("closed", 0)
        wr  = stats.get("win_rate", 0.0) / 100
        edges.append(compute_edge(f"TIER_{tier}", "QUALITY_TIER", wr, n))
    return edges


def detect_news_signal_edges(by_type: Dict[str, dict]) -> List[Edge]:
    """
    Compute edges for each news signal type.

    Args:
        by_type: dict from NewsImpactTracker.impact_by_type()
    """
    edges = []
    for ntype, data in by_type.items():
        n   = data.get("closed", 0)
        wr  = data.get("win_rate", 0.0) / 100
        edges.append(compute_edge(f"NEWS_{ntype}", "NEWS_SIGNAL", wr, n))
    return edges


def detect_options_strategy_edges(overall: Dict[str, object]) -> List[Edge]:
    """
    Compute edges for each options strategy.

    Args:
        overall: dict from StrategyEvaluator.evaluate_all()
                 values are StrategyMetrics with .win_rate, .trades
    """
    edges = []
    for strategy, m in overall.items():
        n  = getattr(m, "trades", 0)
        wr = getattr(m, "win_rate", 0.0) / 100
        edges.append(compute_edge(f"OPT_{strategy}", "OPTIONS_STRATEGY", wr, n))
    return edges


# ── Edge summary ──────────────────────────────────────────────────────────────

def summarise_edges(all_edges: List[Edge]) -> dict:
    """High-level counts across all detected edges."""
    positive  = [e for e in all_edges if e.direction == EdgeDirection.POSITIVE]
    negative  = [e for e in all_edges if e.direction == EdgeDirection.NEGATIVE]
    collecting= [e for e in all_edges if e.direction == EdgeDirection.COLLECTING]
    strong_pos= [e for e in positive  if e.strength  == EdgeStrength.STRONG]

    return {
        "total":          len(all_edges),
        "positive":       len(positive),
        "negative":       len(negative),
        "neutral":        len(all_edges) - len(positive) - len(negative) - len(collecting),
        "collecting":     len(collecting),
        "strong_positive":len(strong_pos),
        "top_edge":       max(all_edges, key=lambda e: e.edge_score, default=None),
        "worst_edge":     min(all_edges, key=lambda e: e.edge_score, default=None),
    }
