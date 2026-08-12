"""
early_move_audit/emp_persistence.py — Morning rank persistence analysis.

Phases 3 & 4 of EMP-001:

Phase 3 — For each interval pair (e.g. 09:30 → CLOSE), compute:
  • Top-N overlap %
  • Spearman rank correlation
  • Direction persistence rate (gainer stays gainer)
  • Average / median final return

Phase 4 — Morning leader persistence:
  • Top-5/10/20 morning gainer → still top-N at close?
  • Gap-up continuation vs reversal
  • Intraday breakout vs reversal

All computation uses only data available BEFORE the end time of each
interval — no look-ahead.  (Close price is the "result", not an input.)
"""
from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .emp_collector import DayRecord
from .emp_config import PERSISTENCE_TOP_N

# Pairs to evaluate: (source_col, result_col, label)
INTERVAL_PAIRS: List[Tuple[str, str, str]] = [
    ("ret_to_930",  "close_return_pct", "09:30 → CLOSE"),
    ("ret_to_945",  "close_return_pct", "09:45 → CLOSE"),
    ("ret_to_1000", "close_return_pct", "10:00 → CLOSE"),
    ("ret_to_1100", "close_return_pct", "11:00 → CLOSE"),
    ("ret_to_1300", "close_return_pct", "13:00 → CLOSE"),
    ("ret_to_1500", "close_return_pct", "15:00 → CLOSE"),
    ("ret_to_930",  "ret_to_1500",      "09:30 → 15:00"),
    ("ret_to_945",  "ret_to_1500",      "09:45 → 15:00"),
]


@dataclass
class IntervalStats:
    label: str
    n_days: int
    # Per top-N bucket
    overlap: Dict[int, float] = field(default_factory=dict)   # top-N → mean overlap %
    # Direction persistence
    gainer_stays_positive: float = 0.0   # % of morning gainers that close positive
    loser_stays_negative:  float = 0.0   # % of morning losers that close negative
    continuation_rate:     float = 0.0   # overall direction persistence
    reversal_rate:         float = 0.0   # morning dir → opposite at result time
    # Returns
    avg_final_return_top5:    Optional[float] = None
    median_final_return_top5: Optional[float] = None
    # Rank correlation
    spearman_rho: Optional[float] = None


@dataclass
class GapStats:
    gap_class: str
    n: int
    continuation_pct: float  # gap direction == close direction
    reversal_pct:     float
    avg_close_return: float
    median_close_return: float
    prob_top5_at_close: float   # P(in top-5 at close | gap class)
    prob_top10_at_close: float
    avg_mfe: float   # mean max favourable excursion from open (intraday)
    avg_mae: float   # mean max adverse excursion from open (intraday)


@dataclass
class PersistenceResult:
    interval_stats: List[IntervalStats] = field(default_factory=list)
    gap_stats: List[GapStats] = field(default_factory=list)
    leader_persistence: Dict[str, Dict[int, float]] = field(default_factory=dict)
    # leader_persistence["WINNER"][5] = P(top-5 morning gainer stays top-5 at close)
    # leader_persistence["LOSER"][5]  = P(top-5 morning loser stays top-5 at close)
    n_trading_days: int = 0
    n_symbols: int = 0


def compute_persistence(records: List[DayRecord], top_n_values: List[int] = PERSISTENCE_TOP_N) -> PersistenceResult:
    """Compute all persistence metrics from the collected dataset."""
    result = PersistenceResult()
    if not records:
        return result

    result.n_symbols = len({r.symbol for r in records})

    # Group by date
    by_date: Dict[str, List[DayRecord]] = {}
    for r in records:
        by_date.setdefault(r.date, []).append(r)

    result.n_trading_days = len(by_date)

    # Compute interval stats
    for src_col, res_col, label in INTERVAL_PAIRS:
        stats = _compute_interval_stats(by_date, src_col, res_col, label, top_n_values)
        if stats:
            result.interval_stats.append(stats)

    # Gap stats
    result.gap_stats = _compute_gap_stats(records)

    # Leader persistence (09:30 → close)
    result.leader_persistence = _compute_leader_persistence(by_date, top_n_values)

    return result


def _compute_interval_stats(
    by_date: Dict[str, List[DayRecord]],
    src_col: str,
    res_col: str,
    label: str,
    top_n_values: List[int],
) -> Optional[IntervalStats]:
    stats = IntervalStats(label=label, n_days=0)
    overlap_acc: Dict[int, List[float]] = {n: [] for n in top_n_values}
    gainer_positive: List[bool] = []
    loser_negative:  List[bool] = []
    direction_match: List[bool] = []
    top5_final_returns: List[float] = []
    src_ranks_all: List[float] = []
    res_ranks_all: List[float] = []

    for day_records in by_date.values():
        # Collect valid pairs
        pairs = [
            (r, getattr(r, src_col), getattr(r, res_col))
            for r in day_records
            if getattr(r, src_col) is not None and getattr(r, res_col) is not None
        ]
        if len(pairs) < 3:
            continue
        stats.n_days += 1

        # Sort by source return (descending = gainer rank)
        pairs_sorted_src = sorted(pairs, key=lambda x: x[1], reverse=True)
        pairs_sorted_res = sorted(pairs, key=lambda x: x[2], reverse=True)

        src_syms_ranked = [r.symbol for r, _, _ in pairs_sorted_src]
        res_syms_ranked = [r.symbol for r, _, _ in pairs_sorted_res]

        # Top-N overlap
        for n in top_n_values:
            top_src = set(src_syms_ranked[:n])
            top_res = set(res_syms_ranked[:n])
            overlap = len(top_src & top_res) / max(n, 1) * 100.0
            overlap_acc[n].append(overlap)

        # Direction persistence
        for r, src_ret, res_ret in pairs:
            if src_ret > 0:
                gainer_positive.append(res_ret > 0)
                direction_match.append((src_ret > 0) == (res_ret > 0))
            elif src_ret < 0:
                loser_negative.append(res_ret < 0)
                direction_match.append((src_ret < 0) == (res_ret < 0))

        # Top-5 final returns
        for _, _, res_ret in pairs_sorted_src[:5]:
            top5_final_returns.append(res_ret)

        # For Spearman correlation
        src_positions = {r.symbol: i for i, (r, _, _) in enumerate(pairs_sorted_src)}
        res_positions = {r.symbol: i for i, (r, _, _) in enumerate(pairs_sorted_res)}
        for sym in src_positions:
            if sym in res_positions:
                src_ranks_all.append(src_positions[sym])
                res_ranks_all.append(res_positions[sym])

    # Aggregate
    for n in top_n_values:
        if overlap_acc[n]:
            stats.overlap[n] = round(statistics.mean(overlap_acc[n]), 1)

    if gainer_positive:
        stats.gainer_stays_positive = sum(gainer_positive) / len(gainer_positive) * 100.0
    if loser_negative:
        stats.loser_stays_negative = sum(loser_negative) / len(loser_negative) * 100.0
    if direction_match:
        stats.continuation_rate = sum(direction_match) / len(direction_match) * 100.0
        stats.reversal_rate     = 100.0 - stats.continuation_rate

    if top5_final_returns:
        stats.avg_final_return_top5    = round(statistics.mean(top5_final_returns), 3)
        stats.median_final_return_top5 = round(statistics.median(top5_final_returns), 3)

    if len(src_ranks_all) >= 10:
        stats.spearman_rho = _spearman(src_ranks_all, res_ranks_all)

    return stats if stats.n_days > 0 else None


def _compute_gap_stats(records: List[DayRecord]) -> List[GapStats]:
    """Compute per-gap-class continuation and excursion statistics."""
    from collections import defaultdict
    buckets: Dict[str, List[DayRecord]] = defaultdict(list)
    for r in records:
        if r.gap_class and r.gap_class != "UNKNOWN":
            buckets[r.gap_class].append(r)

    result = []
    for gap_class, recs in sorted(buckets.items()):
        close_rets   = [r.close_return_pct for r in recs if r.close_return_pct is not None]
        if not close_rets:
            continue

        gap_positive  = [r.gap_pct > 0 for r in recs if r.gap_pct is not None]
        cont_count = sum(
            1 for r in recs
            if r.gap_pct is not None and r.close_return_pct is not None
            and (r.gap_pct > 0) == (r.close_return_pct > 0)
        )
        valid = sum(
            1 for r in recs
            if r.gap_pct is not None and r.close_return_pct is not None
        )

        # Max favourable / adverse excursion from open
        mfe_list: List[float] = []
        mae_list: List[float] = []
        for r in recs:
            if r.open_price and r.day_high and r.day_low and r.open_price > 0:
                mfe = (r.day_high - r.open_price) / r.open_price * 100.0
                mae = (r.open_price - r.day_low)  / r.open_price * 100.0
                mfe_list.append(max(mfe, 0.0))
                mae_list.append(max(mae, 0.0))

        # Top-5 and Top-10 by close return
        close_sorted = sorted(recs, key=lambda r: r.close_return_pct or -999, reverse=True)
        all_count = len(recs)
        top5  = set(r.symbol for r in close_sorted[:5])
        top10 = set(r.symbol for r in close_sorted[:10])

        p_top5  = len(top5)  / max(all_count, 1)
        p_top10 = len(top10) / max(all_count, 1)

        result.append(GapStats(
            gap_class          = gap_class,
            n                  = len(recs),
            continuation_pct   = cont_count / max(valid, 1) * 100.0 if valid else 0.0,
            reversal_pct       = (valid - cont_count) / max(valid, 1) * 100.0 if valid else 0.0,
            avg_close_return   = round(statistics.mean(close_rets), 3),
            median_close_return= round(statistics.median(close_rets), 3),
            prob_top5_at_close = round(p_top5, 3),
            prob_top10_at_close= round(p_top10, 3),
            avg_mfe            = round(statistics.mean(mfe_list), 3) if mfe_list else 0.0,
            avg_mae            = round(statistics.mean(mae_list), 3) if mae_list else 0.0,
        ))
    return result


def _compute_leader_persistence(
    by_date: Dict[str, List[DayRecord]],
    top_n_values: List[int],
) -> Dict[str, Dict[int, float]]:
    """
    P(morning top-N gainer stays top-N at close).

    Morning = ranked by ret_to_930 (09:30 return from open).
    Result  = ranked by close_return_pct.
    """
    result: Dict[str, Dict[int, float]] = {
        "WINNER": {n: [] for n in top_n_values},  # type: ignore
        "LOSER":  {n: [] for n in top_n_values},  # type: ignore
    }
    counts: Dict[str, Dict[int, List[bool]]] = {
        "WINNER": {n: [] for n in top_n_values},
        "LOSER":  {n: [] for n in top_n_values},
    }

    for day_records in by_date.values():
        valid = [(r, r.ret_to_930, r.close_return_pct)
                 for r in day_records
                 if r.ret_to_930 is not None and r.close_return_pct is not None]
        if len(valid) < max(top_n_values, default=5):
            continue

        sorted_930  = sorted(valid, key=lambda x: x[1], reverse=True)
        sorted_close = sorted(valid, key=lambda x: x[2], reverse=True)

        top_close_syms     = {r.symbol for r, _, _ in sorted_close}
        bottom_close_syms  = set()

        for n in top_n_values:
            top_morning_winner = {r.symbol for r, _, _ in sorted_930[:n]}
            top_morning_loser  = {r.symbol for r, _, _ in sorted_930[-n:]}
            top_close_n        = {r.symbol for r, _, _ in sorted_close[:n]}
            bottom_close_n     = {r.symbol for r, _, _ in sorted_close[-n:]}

            for sym in top_morning_winner:
                counts["WINNER"][n].append(sym in top_close_n)
            for sym in top_morning_loser:
                counts["LOSER"][n].append(sym in bottom_close_n)

    # Compute mean persistence rates
    out: Dict[str, Dict[int, float]] = {}
    for side in ("WINNER", "LOSER"):
        out[side] = {}
        for n in top_n_values:
            bools = counts[side][n]
            out[side][n] = round(sum(bools) / max(len(bools), 1) * 100.0, 1) if bools else 0.0

    return out


# ── Spearman rank correlation (no scipy dependency) ───────────────────────────

def _spearman(x: List[float], y: List[float]) -> float:
    """Compute Spearman rank correlation between two lists of equal length."""
    n = len(x)
    if n < 3:
        return float("nan")
    rx = _ranks(x)
    ry = _ranks(y)
    d2 = sum((a - b) ** 2 for a, b in zip(rx, ry))
    rho = 1.0 - 6.0 * d2 / (n * (n * n - 1))
    return round(rho, 4)


def _ranks(vals: List[float]) -> List[float]:
    """Convert a list of values to their rank positions (1-indexed, average for ties)."""
    indexed = sorted(enumerate(vals), key=lambda x: x[1])
    ranks = [0.0] * len(vals)
    i = 0
    while i < len(indexed):
        j = i
        while j < len(indexed) - 1 and indexed[j + 1][1] == indexed[i][1]:
            j += 1
        avg_rank = (i + j) / 2.0 + 1.0
        for k in range(i, j + 1):
            ranks[indexed[k][0]] = avg_rank
        i = j + 1
    return ranks
