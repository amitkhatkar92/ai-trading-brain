"""iios/investment/company/opportunity/ranking_statistics.py
Pure ranking computation helpers — no side-effects, no external state.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple


def rank_tickers(
    scores: Dict[str, float],
    reverse: bool = True,
) -> Dict[str, int]:
    """
    Assign 1-based integer ranks to tickers by score.
    *reverse=True* → highest score = rank 1.
    Ties receive the same rank (dense ranking).
    """
    if not scores:
        return {}
    sorted_tickers = sorted(scores, key=lambda t: scores[t], reverse=reverse)
    ranks: Dict[str, int] = {}
    current_rank = 1
    for i, t in enumerate(sorted_tickers):
        if i > 0 and scores[t] != scores[sorted_tickers[i - 1]]:
            current_rank = i + 1
        ranks[t] = current_rank
    return ranks


def top_n_tickers(
    scores: Dict[str, float],
    n: int,
    reverse: bool = True,
) -> List[str]:
    """Return the top-*n* tickers sorted by score."""
    return sorted(scores, key=lambda t: scores[t], reverse=reverse)[:n]


def compute_score_percentile(score: float, population: List[float]) -> float:
    """
    Return 0-100 percentile rank (100 = best).
    Uses interpolation for tie-breaking.
    """
    if not population:
        return 50.0
    below = sum(1 for s in population if s < score)
    equal = sum(1 for s in population if s == score)
    # Mid-point among equals
    pct = (below + 0.5 * equal) / len(population) * 100.0
    return max(0.0, min(100.0, pct))


def score_momentum(
    current: float,
    history: List[float],
    *,
    lookback: int = 3,
) -> float:
    """
    Compare current score to recent average.
    Returns positive if improving, negative if deteriorating.
    """
    if not history:
        return 0.0
    window = history[-lookback:] if len(history) >= lookback else history
    avg = sum(window) / len(window)
    return current - avg


def normalise_scores(scores: Dict[str, float]) -> Dict[str, float]:
    """
    Min-max normalise scores to [0, 100].
    Returns the input dict unchanged if all scores are identical.
    """
    if not scores:
        return {}
    lo = min(scores.values())
    hi = max(scores.values())
    if hi == lo:
        return {t: 50.0 for t in scores}
    return {t: (s - lo) / (hi - lo) * 100.0 for t, s in scores.items()}


def sector_relative_score(
    ticker: str,
    sector_scores: Dict[str, float],
) -> Optional[float]:
    """
    Score of *ticker* relative to its sector peers (0-100).
    100 = top of sector. Returns None if ticker not in dict.
    """
    if ticker not in sector_scores:
        return None
    population = list(sector_scores.values())
    return compute_score_percentile(sector_scores[ticker], population)


def score_distribution_summary(scores: Dict[str, float]) -> Dict[str, float]:
    """Return basic statistics for a score distribution."""
    if not scores:
        return {}
    vals = list(scores.values())
    n = len(vals)
    avg = sum(vals) / n
    sorted_vals = sorted(vals)
    median = (
        sorted_vals[n // 2]
        if n % 2
        else (sorted_vals[n // 2 - 1] + sorted_vals[n // 2]) / 2
    )
    return {
        "count":  n,
        "min":    sorted_vals[0],
        "max":    sorted_vals[-1],
        "mean":   round(avg, 2),
        "median": round(median, 2),
    }
