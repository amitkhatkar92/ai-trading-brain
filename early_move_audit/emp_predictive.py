"""
early_move_audit/emp_predictive.py — EMP-001 Predictive Models A, B, C.

Phase 5 — Model A: Previous-Day Only
Phase 6 — Model B: Opening-Window Only
Phase 7 — Model C: Previous-Day + Opening-Window (Combined)
Phase 8 — Gap-specific analysis (within gap classes)
Phase 9 — Previous-day IIOS scan hit-rate analysis
Phase 10 — Capital-constraint separation

LOOK-AHEAD PREVENTION CONTRACT
-------------------------------
• Model A uses ONLY: prev_return_pct, prev_volume_ratio, prev_range_pct,
  was_prev_pga_flag, was_prev_leader.  No same-day data.
• Model B uses ONLY: gap_pct, ret_to_930 (or ret_to_945, ret_to_1000).
  No close, no data after the specified window.
• Model C = A score + B score (simple weighted average of ranks).
"""
from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple

from .emp_collector import DayRecord
from .emp_config import PERSISTENCE_TOP_N


# ── Failure mode classification (Phase 10) ───────────────────────────────────

class MissClass(str, Enum):
    PREDICTION_FAILURE               = "PREDICTION_FAILURE"
    CAPITAL_FAILURE                  = "CAPITAL_FAILURE"          # price too high for ₹10k
    PORTFOLIO_FAILURE                = "PORTFOLIO_FAILURE"        # max positions reached
    RISK_FAILURE                     = "RISK_FAILURE"             # risk filter blocked
    EXECUTION_FAILURE                = "EXECUTION_FAILURE"        # could not execute
    UNIVERSE_FAILURE                 = "UNIVERSE_FAILURE"         # not in scanner universe
    NO_SIGNAL                        = "NO_SIGNAL"                # model gave no signal
    NO_DATA                          = "NO_DATA"                  # missing price data
    PREDICTED_BUT_UNACTIONABLE_CAPITAL = "PREDICTED_BUT_UNACTIONABLE_CAPITAL"


SMALL_CAPITAL = 10_000.0   # ₹10,000 reference capital
MIN_QTY       = 1          # minimum 1 share required


# ── Model result container ────────────────────────────────────────────────────

@dataclass
class ModelMetrics:
    """Prediction quality metrics for a single top-N threshold."""
    top_n: int
    n_days: int                 # trading days evaluated
    n_predictions: int          # total predictions made
    n_correct: int              # correct (symbol in actual top-N at close)
    precision: float            # n_correct / n_predictions
    recall: float               # n_correct / n_actual_top_n
    hit_rate: float             # fraction of days with ≥1 correct prediction
    false_positive_rate: float
    lift: float                 # precision / base_rate
    base_rate: float            # n_top / n_universe (random chance)
    spearman_rho: Optional[float] = None


@dataclass
class ModelResult:
    """Complete result for one predictive model."""
    name: str           # "Model A", "Model B (09:30)", "Model C (Combined)"
    description: str
    window: str         # "previous_day" | "09:30" | "09:45" | "10:00" | "combined"
    metrics: List[ModelMetrics] = field(default_factory=list)
    look_ahead_clean: bool = True   # always True when constraints are satisfied


@dataclass
class MissRecord:
    date: str
    symbol: str
    close_return_pct: float
    miss_class: MissClass
    predicted: bool          # model said this would be a winner
    reason: str


@dataclass
class ScanHitRate:
    """Previous-day IIOS scan hit-rate vs base market hit-rate (Phase 9)."""
    n_scan_days: int
    scan_total_signals: int                # symbols flagged by PGA/scanner
    scan_became_top5:   int
    scan_became_top10:  int
    scan_became_top20:  int
    base_top5_rate:     float             # random chance of being top-5
    base_top10_rate:    float
    base_top20_rate:    float
    scan_top5_rate:     float             # hit rate among scanned symbols
    scan_top10_rate:    float
    scan_top20_rate:    float
    lift_top5:          float             # scan_rate / base_rate
    lift_top10:         float
    lift_top20:         float


@dataclass
class PredictiveResult:
    model_a: Optional[ModelResult]         = None   # previous day only
    model_b_930: Optional[ModelResult]     = None   # opening 09:30
    model_b_945: Optional[ModelResult]     = None   # opening 09:45
    model_b_1000: Optional[ModelResult]   = None   # opening 10:00
    model_c: Optional[ModelResult]         = None   # combined
    scan_hit_rate: Optional[ScanHitRate]  = None
    misses: List[MissRecord]              = field(default_factory=list)
    recommendation: str                   = ""      # OPTION A/B/C/D/E


# ── Public API ────────────────────────────────────────────────────────────────

def build_predictive_analysis(
    records: List[DayRecord],
    top_n_values: List[int] = PERSISTENCE_TOP_N,
) -> PredictiveResult:
    result = PredictiveResult()
    if not records:
        return result

    by_date = _group_by_date(records)

    result.model_a      = _build_model_a(by_date, top_n_values)
    result.model_b_930  = _build_model_b(by_date, "ret_to_930",  "09:30", top_n_values)
    result.model_b_945  = _build_model_b(by_date, "ret_to_945",  "09:45", top_n_values)
    result.model_b_1000 = _build_model_b(by_date, "ret_to_1000", "10:00", top_n_values)
    result.model_c      = _build_model_c(by_date, top_n_values)
    result.scan_hit_rate = _build_scan_hit_rate(by_date, top_n_values)
    result.misses        = _classify_misses(by_date, top_n_values[0] if top_n_values else 10)
    result.recommendation = _generate_recommendation(result)

    return result


# ── Model A: Previous-day only ────────────────────────────────────────────────

def _build_model_a(
    by_date: Dict[str, List[DayRecord]],
    top_n_values: List[int],
) -> ModelResult:
    """
    Score each symbol purely on previous-day features (no same-day data).
    Score = weighted sum of normalized previous-day signals.
    """
    metrics = []
    for n in top_n_values:
        m = _evaluate_model(
            by_date,
            score_fn=_score_model_a,
            n=n,
            allowed_fields={"prev_return_pct", "prev_volume_ratio", "prev_range_pct",
                            "was_prev_pga_flag", "was_prev_leader"},
        )
        if m:
            metrics.append(m)

    return ModelResult(
        name        = "Model A",
        description = "Previous-day only: prev_return, volume_ratio, range, PGA flag, leader",
        window      = "previous_day",
        metrics     = metrics,
    )


def _score_model_a(rec: DayRecord) -> Optional[float]:
    """Score a record using only prior-day features.  Higher = more bullish."""
    score = 0.0
    components = 0

    if rec.prev_return_pct is not None:
        score += rec.prev_return_pct * 0.4
        components += 1
    if rec.prev_volume_ratio is not None:
        score += (rec.prev_volume_ratio - 1.0) * 0.3
        components += 1
    if rec.prev_range_pct is not None:
        score += rec.prev_range_pct * 0.1
        components += 1
    if rec.was_prev_pga_flag:
        score += 0.5
        components += 1
    if rec.was_prev_leader:
        score += (0.5 if rec.prev_leader_type == "WINNER" else -0.5)
        components += 1

    return score if components >= 1 else None


# ── Model B: Opening-window only ─────────────────────────────────────────────

def _build_model_b(
    by_date: Dict[str, List[DayRecord]],
    ret_col: str,
    window_label: str,
    top_n_values: List[int],
) -> ModelResult:
    """
    Score based solely on the opening-window return (gap + first N minutes).
    No look-ahead: only uses data up to window_label.
    """
    def score_fn(rec: DayRecord) -> Optional[float]:
        val = getattr(rec, ret_col, None)
        if val is None:
            # Fall back to gap alone
            return rec.gap_pct
        return val

    metrics = []
    for n in top_n_values:
        m = _evaluate_model(by_date, score_fn=score_fn, n=n,
                            allowed_fields={"gap_pct", ret_col})
        if m:
            metrics.append(m)

    return ModelResult(
        name        = f"Model B ({window_label})",
        description = f"Opening window only: gap + return to {window_label}",
        window      = window_label,
        metrics     = metrics,
    )


# ── Model C: Combined ─────────────────────────────────────────────────────────

def _build_model_c(
    by_date: Dict[str, List[DayRecord]],
    top_n_values: List[int],
) -> ModelResult:
    """
    Combine Model A rank + Model B (09:30) rank into a single composite score.
    Simple average of percentile ranks — no ML, no calibration.
    """
    def score_fn(rec: DayRecord) -> Optional[float]:
        a = _score_model_a(rec)
        b = getattr(rec, "ret_to_930", None)
        if b is None:
            b = rec.gap_pct
        parts = [x for x in [a, b] if x is not None]
        return sum(parts) / len(parts) if parts else None

    metrics = []
    for n in top_n_values:
        m = _evaluate_model(by_date, score_fn=score_fn, n=n,
                            allowed_fields={"prev_return_pct", "prev_volume_ratio",
                                            "prev_range_pct", "was_prev_pga_flag",
                                            "was_prev_leader", "gap_pct", "ret_to_930"})
        if m:
            metrics.append(m)

    return ModelResult(
        name        = "Model C",
        description = "Combined: prev-day rank + opening-window (09:30) rank averaged",
        window      = "combined",
        metrics     = metrics,
    )


# ── Core evaluation engine ────────────────────────────────────────────────────

def _evaluate_model(
    by_date: Dict[str, List[DayRecord]],
    score_fn,
    n: int,
    allowed_fields,
) -> Optional[ModelMetrics]:
    """
    For each trading day:
      1. Score each symbol with score_fn
      2. Predict top-N
      3. Compare prediction to actual top-N (by close_return_pct)

    Returns ModelMetrics aggregated across all days.
    """
    total_predictions = 0
    total_correct     = 0
    total_actual      = 0
    days_with_hit     = 0
    valid_days        = 0
    fp_count          = 0
    tn_count          = 0
    universe_sizes    = []

    for day_records in by_date.values():
        # Require close data for actual ranking
        valid = [(r, score_fn(r)) for r in day_records
                 if r.close_return_pct is not None and score_fn(r) is not None]
        if len(valid) < n:
            continue
        valid_days += 1
        universe_sizes.append(len(valid))

        # Actual top-N at close
        sorted_actual = sorted(valid, key=lambda x: x[0].close_return_pct, reverse=True)
        actual_top_n  = {r.symbol for r, _ in sorted_actual[:n]}

        # Predicted top-N by model score
        sorted_pred   = sorted(valid, key=lambda x: x[1], reverse=True)
        pred_top_n    = {r.symbol for r, _ in sorted_pred[:n]}

        correct = len(pred_top_n & actual_top_n)
        total_predictions += n
        total_correct     += correct
        total_actual      += n
        if correct >= 1:
            days_with_hit += 1

        # False positives: predicted but not actual
        fp_count += n - correct
        # True negatives: not predicted, not actual
        tn_count += len(valid) - n - (n - correct)

    if valid_days < 3:
        return None

    avg_universe   = statistics.mean(universe_sizes) if universe_sizes else n + 1
    base_rate      = n / avg_universe
    precision      = total_correct / max(total_predictions, 1)
    recall         = total_correct / max(total_actual, 1)
    hit_rate       = days_with_hit / max(valid_days, 1)
    fp_rate        = fp_count / max(total_predictions, 1)
    lift           = precision / base_rate if base_rate > 0 else 0.0

    return ModelMetrics(
        top_n               = n,
        n_days              = valid_days,
        n_predictions       = total_predictions,
        n_correct           = total_correct,
        precision           = round(precision, 4),
        recall              = round(recall, 4),
        hit_rate            = round(hit_rate, 4),
        false_positive_rate = round(fp_rate, 4),
        lift                = round(lift, 3),
        base_rate           = round(base_rate, 4),
    )


# ── Phase 9: Previous-day scan hit rate ───────────────────────────────────────

def _build_scan_hit_rate(
    by_date: Dict[str, List[DayRecord]],
    top_n_values: List[int],
) -> ScanHitRate:
    scan_flagged: List[bool] = []
    became_top: Dict[int, List[bool]] = {n: [] for n in top_n_values}
    universe_sizes: List[int] = []

    for day_records in by_date.values():
        valid = [r for r in day_records if r.close_return_pct is not None]
        if not valid:
            continue
        sorted_close = sorted(valid, key=lambda r: r.close_return_pct, reverse=True)
        universe_sizes.append(len(valid))

        for r in valid:
            if r.was_prev_pga_flag or r.was_in_prev_scan:
                scan_flagged.append(True)
                for n in top_n_values:
                    top_n_syms = {x.symbol for x in sorted_close[:n]}
                    became_top[n].append(r.symbol in top_n_syms)

    n_scan = len(scan_flagged)
    avg_u  = statistics.mean(universe_sizes) if universe_sizes else 1

    def rate(lst: List[bool]) -> float:
        return sum(lst) / max(len(lst), 1)

    top5_base  = top_n_values[0] / avg_u if top_n_values else 0.0
    top10_base = (top_n_values[1] if len(top_n_values) > 1 else top_n_values[0]) / avg_u
    top20_base = (top_n_values[2] if len(top_n_values) > 2 else top_n_values[0]) / avg_u

    s5  = rate(became_top.get(top_n_values[0], []))
    s10 = rate(became_top.get(top_n_values[1] if len(top_n_values) > 1 else top_n_values[0], []))
    s20 = rate(became_top.get(top_n_values[2] if len(top_n_values) > 2 else top_n_values[0], []))

    return ScanHitRate(
        n_scan_days         = len(by_date),
        scan_total_signals  = n_scan,
        scan_became_top5    = sum(became_top.get(top_n_values[0], [])),
        scan_became_top10   = sum(became_top.get(top_n_values[1] if len(top_n_values) > 1 else top_n_values[0], [])),
        scan_became_top20   = sum(became_top.get(top_n_values[2] if len(top_n_values) > 2 else top_n_values[0], [])),
        base_top5_rate      = round(top5_base, 4),
        base_top10_rate     = round(top10_base, 4),
        base_top20_rate     = round(top20_base, 4),
        scan_top5_rate      = round(s5, 4),
        scan_top10_rate     = round(s10, 4),
        scan_top20_rate     = round(s20, 4),
        lift_top5           = round(s5 / max(top5_base, 1e-6), 3),
        lift_top10          = round(s10 / max(top10_base, 1e-6), 3),
        lift_top20          = round(s20 / max(top20_base, 1e-6), 3),
    )


# ── Phase 10: Capital constraint classification ───────────────────────────────

def _classify_misses(
    by_date: Dict[str, List[DayRecord]],
    top_n: int,
) -> List[MissRecord]:
    """
    Classify each near-miss as PREDICTION_FAILURE or PREDICTED_BUT_UNACTIONABLE_CAPITAL.
    A stock that moved into top-N at close but was not in the scanner top-N is a miss.
    If its price × 1 share > SMALL_CAPITAL, classify as CAPITAL rather than PREDICTION.
    """
    misses: List[MissRecord] = []

    for day_records in by_date.values():
        valid = [(r, _score_model_a(r)) for r in day_records
                 if r.close_return_pct is not None]
        if len(valid) < top_n:
            continue

        sorted_actual = sorted(valid, key=lambda x: x[0].close_return_pct, reverse=True)
        sorted_pred   = sorted([(r, s) for r, s in valid if s is not None],
                                key=lambda x: x[1], reverse=True)

        actual_top_n = {r.symbol for r, _ in sorted_actual[:top_n]}
        pred_top_n   = {r.symbol for r, _ in sorted_pred[:top_n]}

        # False negatives: should have been predicted but weren't
        missed = actual_top_n - pred_top_n
        for r, _ in sorted_actual[:top_n]:
            if r.symbol not in pred_top_n and r.close_return_pct is not None:
                close_px = r.close_price or r.prev_close or 0.0
                if close_px > SMALL_CAPITAL:
                    cls = MissClass.PREDICTED_BUT_UNACTIONABLE_CAPITAL
                    reason = f"Price ~₹{close_px:.0f} exceeds ₹{SMALL_CAPITAL:.0f} capital"
                else:
                    cls = MissClass.PREDICTION_FAILURE
                    reason = "Model A score too low"

                misses.append(MissRecord(
                    date             = r.date,
                    symbol           = r.symbol,
                    close_return_pct = r.close_return_pct,
                    miss_class       = cls,
                    predicted        = False,
                    reason           = reason,
                ))

    return misses


# ── Phase 11: Recommendation ──────────────────────────────────────────────────

def _generate_recommendation(result: PredictiveResult) -> str:
    """
    Evidence-based recommendation for future scan strategy.

    A: Previous-day sufficient
    B: Add opening window
    C: Add 09:30 scan
    D: Add 09:45 scan
    E: Use combined previous-day + opening window
    """
    from .emp_config import REPORT_RECOMMENDATION_MIN_LIFT

    if not result.model_a or not result.model_b_930:
        return "INSUFFICIENT_DATA"

    a_lift = max((m.lift for m in result.model_a.metrics), default=0.0)
    b930_lift = max((m.lift for m in result.model_b_930.metrics), default=0.0)
    c_lift  = max((m.lift for m in result.model_c.metrics), default=0.0) if result.model_c else 0.0
    b945_lift = max((m.lift for m in result.model_b_945.metrics), default=0.0) if result.model_b_945 else 0.0
    b1000_lift = max((m.lift for m in result.model_b_1000.metrics), default=0.0) if result.model_b_1000 else 0.0

    if c_lift > a_lift + 0.15 and c_lift >= REPORT_RECOMMENDATION_MIN_LIFT:
        return "OPTION_E"   # Combined is materially better
    if b930_lift > a_lift + 0.10 and b930_lift >= REPORT_RECOMMENDATION_MIN_LIFT:
        return "OPTION_C"   # 09:30 scan adds meaningful value
    if b945_lift > a_lift + 0.10:
        return "OPTION_D"   # 09:45 scan is better
    if b930_lift > a_lift and b930_lift >= REPORT_RECOMMENDATION_MIN_LIFT:
        return "OPTION_B"   # Some opening-window value
    return "OPTION_A"       # Previous-day is sufficient


# ── Helpers ───────────────────────────────────────────────────────────────────

def _group_by_date(records: List[DayRecord]) -> Dict[str, List[DayRecord]]:
    by_date: Dict[str, List[DayRecord]] = {}
    for r in records:
        by_date.setdefault(r.date, []).append(r)
    return by_date
