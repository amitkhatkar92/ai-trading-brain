"""
early_move_audit/emp_reporter.py — Report generation for EMP-001.

Produces:
  data/early_move_audit/YYYY-MM-DD/
    EMP_DAILY_REPORT_YYYY-MM-DD.md
    EMP_PERSISTENCE_ANALYSIS.md
    EMP_PREDICTIVE_COMPARISON.md
    EMP_DATA_QUALITY.md
    EMP_FINDINGS.json

All output is READ-ONLY observational content.
No live trading data is modified.
"""
from __future__ import annotations

import json
import logging
import statistics
from datetime import date as date_cls
from pathlib import Path
from typing import Any, Dict, List, Optional

from .emp_analyzer import EMPResult
from .emp_config import REPORT_RECOMMENDATION_MIN_LIFT
from .emp_predictive import MissClass

log = logging.getLogger(__name__)

OPTION_LABELS = {
    "OPTION_A": "Keep existing previous-day scan — sufficient predictive value.",
    "OPTION_B": "Add an opening-window scan — opening provides incremental value.",
    "OPTION_C": "Add a 09:30 scan — 09:30 return materially improves prediction.",
    "OPTION_D": "Add a 09:45 scan — first 30 minutes is the optimal window.",
    "OPTION_E": "Use previous-day + opening-window combined — combination is best.",
    "INSUFFICIENT_DATA": "Insufficient data to make a recommendation.",
}


def generate_reports(result: EMPResult) -> Dict[str, Path]:
    """
    Write all EMP-001 reports for the given result.

    Returns dict of {report_name -> path} for all files written.
    """
    from .emp_config import REPORT_DIR
    out_dir = REPORT_DIR / result.run_date
    out_dir.mkdir(parents=True, exist_ok=True)

    paths: Dict[str, Path] = {}

    paths["daily"]       = _write_daily_report(result, out_dir)
    paths["persistence"] = _write_persistence(result, out_dir)
    paths["predictive"]  = _write_predictive(result, out_dir)
    paths["quality"]     = _write_quality(result, out_dir)
    paths["findings"]    = _write_findings_json(result, out_dir)

    log.info("[EmpReporter] Reports written to %s", out_dir)
    return paths


# ── Daily report ──────────────────────────────────────────────────────────────

def _write_daily_report(result: EMPResult, out_dir: Path) -> Path:
    path = out_dir / f"EMP_DAILY_REPORT_{result.run_date}.md"

    pers = result.persistence
    pred = result.predictive
    rec  = pred.recommendation
    rec_text = OPTION_LABELS.get(rec, rec)

    # Morning persistence headline
    best_interval = None
    best_overlap  = 0.0
    for iv in pers.interval_stats:
        ov = iv.overlap.get(10, 0.0)
        if ov > best_overlap:
            best_overlap = ov
            best_interval = iv

    # Lift comparison across models
    a_lift  = _max_lift(pred.model_a)
    b_lift  = _max_lift(pred.model_b_930)
    c_lift  = _max_lift(pred.model_c)

    lines = [
        f"# EMP-001 Daily Report — {result.run_date}",
        "",
        "**Early-Move Persistence & Previous-Day Predictive Value Audit**",
        f"**Analysis period:** {result.persistence.n_trading_days} trading days",
        f"**Universe:** {result.persistence.n_symbols} symbols",
        f"**Records:** {len(result.records)} symbol-days",
        "",
        "---",
        "",
        "## 1. Executive Summary",
        "",
    ]

    # Morning persistence verdict
    if best_interval:
        cont = best_interval.continuation_rate
        rev  = best_interval.reversal_rate
        lines += [
            f"**Morning persistence ({best_interval.label}):**",
            f"- Top-10 overlap: **{best_overlap:.1f}%**",
            f"- Direction continuation: **{cont:.1f}%**  | Reversal: **{rev:.1f}%**",
            f"- Morning gainers → positive close: "
            f"**{best_interval.gainer_stays_positive:.1f}%**",
            f"- Avg final return of top-5 morning leaders: "
            f"**{best_interval.avg_final_return_top5 or 'N/A'}%**",
            "",
        ]

    # Predictive power verdict
    lines += [
        "**Predictive model comparison (Top-10 precision lift over random):**",
        f"- Model A (previous day only):          lift = **{a_lift:.2f}x**",
        f"- Model B (opening window, 09:30):       lift = **{b_lift:.2f}x**",
        f"- Model C (combined):                    lift = **{c_lift:.2f}x**",
        "",
        f"**Recommendation: {rec}** — {rec_text}",
        "",
    ]

    # Leader persistence
    lp = pers.leader_persistence
    if lp:
        lines += [
            "## 2. Morning Leader Persistence (09:30 → Close)",
            "",
            "| Leader Type | Top-5 remains Top-5 | Top-10 | Top-20 |",
            "|---|---|---|---|",
        ]
        for side in ("WINNER", "LOSER"):
            d = lp.get(side, {})
            p5  = d.get(5,  "N/A")
            p10 = d.get(10, "N/A")
            p20 = d.get(20, "N/A")
            lines.append(
                f"| {side} | {p5}% | {p10}% | {p20}% |"
            )
        lines.append("")

    # Gap analysis
    if pers.gap_stats:
        lines += [
            "## 3. Gap Analysis",
            "",
            "| Gap Class | N | Continuation% | Avg Close Return | Avg MFE | Avg MAE |",
            "|---|---|---|---|---|---|",
        ]
        for g in sorted(pers.gap_stats, key=lambda x: x.gap_class):
            lines.append(
                f"| {g.gap_class} | {g.n} | {g.continuation_pct:.1f}% | "
                f"{g.avg_close_return:+.2f}% | {g.avg_mfe:.2f}% | {g.avg_mae:.2f}% |"
            )
        lines.append("")

    # Scan hit rate
    shr = pred.scan_hit_rate
    if shr and shr.scan_total_signals > 0:
        lines += [
            "## 4. Previous-Day IIOS Scan Performance",
            "",
            f"Scanned signals: **{shr.scan_total_signals}** across {shr.n_scan_days} days",
            "",
            "| Metric | Top-5 | Top-10 | Top-20 |",
            "|---|---|---|---|",
            f"| System hit rate | {shr.scan_top5_rate:.1%} | {shr.scan_top10_rate:.1%} | {shr.scan_top20_rate:.1%} |",
            f"| Base market rate | {shr.base_top5_rate:.1%} | {shr.base_top10_rate:.1%} | {shr.base_top20_rate:.1%} |",
            f"| Lift | **{shr.lift_top5:.2f}x** | **{shr.lift_top10:.2f}x** | **{shr.lift_top20:.2f}x** |",
            "",
        ]

    # Capital-only misses
    cap_misses = [m for m in pred.misses
                  if m.miss_class == MissClass.PREDICTED_BUT_UNACTIONABLE_CAPITAL]
    if cap_misses:
        lines += [
            "## 5. Capital-Only Misses",
            "",
            f"**{len(cap_misses)} instances** where correct prediction was blocked by capital (₹10,000).",
            "",
            "| Date | Symbol | Close Return | Price Note |",
            "|---|---|---|---|",
        ]
        for m in cap_misses[:10]:
            lines.append(f"| {m.date} | {m.symbol} | {m.close_return_pct:+.2f}% | {m.reason} |")
        lines.append("")

    # Final answer to Phase Final Question
    lines += [
        "## 6. Final Research Question Answer",
        "",
        "**Does IIOS gain meaningful predictive information from:**",
        "",
    ]
    _append_window_verdict(lines, "the previous trading day", pred.model_a, a_lift)
    _append_window_verdict(lines, "the first 15 minutes (09:30)", pred.model_b_930, b_lift)
    _append_window_verdict(lines, "the first 30 minutes (09:45)",
                           pred.model_b_945, _max_lift(pred.model_b_945))
    _append_window_verdict(lines, "the first 45 minutes (10:00)",
                           pred.model_b_1000, _max_lift(pred.model_b_1000))

    # Morning winner persistence answer
    winner_10 = lp.get("WINNER", {}).get(10, None) if lp else None
    if winner_10 is not None:
        if winner_10 >= 50:
            verdict = f"YES — **{winner_10:.1f}%** of morning Top-10 gainers remain top gainers at close."
        else:
            verdict = f"MIXED — only **{winner_10:.1f}%** of morning Top-10 gainers remain top at close."
        lines += [
            "",
            f"**Does a morning winner usually remain a winner?** {verdict}",
            "",
        ]

    lines += [
        f"**Scheduling recommendation:** {rec} — {rec_text}",
        "",
        "---",
        f"*Generated {result.run_date} | EMP-001 | Read-only observational research*",
    ]

    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def _append_window_verdict(lines: list, label: str, model, lift: float) -> None:
    if model is None:
        lines.append(f"- **{label}:** N/A (no intraday data)")
        return
    top10m = next((m for m in model.metrics if m.top_n == 10), None)
    if top10m:
        lines.append(
            f"- **{label}:** lift={lift:.2f}x | precision={top10m.precision:.1%} | "
            f"recall={top10m.recall:.1%}"
            + (" ✅ meaningful" if lift >= REPORT_RECOMMENDATION_MIN_LIFT else " — marginal")
        )
    else:
        lines.append(f"- **{label}:** insufficient data")


# ── Persistence analysis report ───────────────────────────────────────────────

def _write_persistence(result: EMPResult, out_dir: Path) -> Path:
    path = out_dir / "EMP_PERSISTENCE_ANALYSIS.md"
    pers = result.persistence
    lines = [
        f"# EMP-001 Persistence Analysis — {result.run_date}",
        "",
        f"Trading days: {pers.n_trading_days} | Symbols: {pers.n_symbols}",
        "",
        "## Interval Persistence",
        "",
        "| Interval | Days | Top-5 Overlap | Top-10 Overlap | Top-20 Overlap | "
        "Continuation% | Reversal% | Spearman ρ | Avg Top-5 Return |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for iv in pers.interval_stats:
        lines.append(
            f"| {iv.label} | {iv.n_days} | "
            f"{iv.overlap.get(5,'N/A')}% | {iv.overlap.get(10,'N/A')}% | "
            f"{iv.overlap.get(20,'N/A')}% | {iv.continuation_rate:.1f}% | "
            f"{iv.reversal_rate:.1f}% | "
            f"{iv.spearman_rho if iv.spearman_rho is not None else 'N/A'} | "
            f"{iv.avg_final_return_top5 or 'N/A'}% |"
        )

    lines += [
        "",
        "## Morning Leader Persistence (09:30 → Close)",
        "",
        "| Side | Top-5 % | Top-10 % | Top-20 % |",
        "|---|---|---|---|",
    ]
    for side in ("WINNER", "LOSER"):
        d = pers.leader_persistence.get(side, {})
        lines.append(
            f"| {side} | {d.get(5,'N/A')}% | {d.get(10,'N/A')}% | {d.get(20,'N/A')}% |"
        )

    lines += [
        "",
        "## Gap Analysis",
        "",
        "| Gap Class | N | Cont% | Rev% | Avg Return | Median Return | "
        "P(top5 at close) | P(top10 at close) | Avg MFE | Avg MAE |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for g in sorted(pers.gap_stats, key=lambda x: x.gap_class):
        lines.append(
            f"| {g.gap_class} | {g.n} | {g.continuation_pct:.1f}% | "
            f"{g.reversal_pct:.1f}% | {g.avg_close_return:+.2f}% | "
            f"{g.median_close_return:+.2f}% | {g.prob_top5_at_close:.1%} | "
            f"{g.prob_top10_at_close:.1%} | {g.avg_mfe:.2f}% | {g.avg_mae:.2f}% |"
        )

    path.write_text("\n".join(lines), encoding="utf-8")
    return path


# ── Predictive comparison report ──────────────────────────────────────────────

def _write_predictive(result: EMPResult, out_dir: Path) -> Path:
    path = out_dir / "EMP_PREDICTIVE_COMPARISON.md"
    pred = result.predictive
    rec  = pred.recommendation
    rec_text = OPTION_LABELS.get(rec, rec)

    lines = [
        f"# EMP-001 Predictive Comparison — {result.run_date}",
        "",
        "## Model A vs Model B vs Model C",
        "",
    ]

    for model in [pred.model_a, pred.model_b_930, pred.model_b_945, pred.model_b_1000, pred.model_c]:
        if not model:
            continue
        lines += [f"### {model.name}", f"*{model.description}*", ""]
        if model.metrics:
            lines += [
                "| Top-N | Days | Precision | Recall | Hit Rate | FPR | Lift | Base Rate |",
                "|---|---|---|---|---|---|---|---|",
            ]
            for m in model.metrics:
                lines.append(
                    f"| {m.top_n} | {m.n_days} | {m.precision:.1%} | {m.recall:.1%} | "
                    f"{m.hit_rate:.1%} | {m.false_positive_rate:.1%} | "
                    f"**{m.lift:.2f}x** | {m.base_rate:.1%} |"
                )
        else:
            lines.append("*No metrics computed (insufficient data).*")
        lines.append("")

    if pred.scan_hit_rate:
        shr = pred.scan_hit_rate
        lines += [
            "## Previous-Day IIOS Scan Hit Rate",
            "",
            f"Scanned signals: {shr.scan_total_signals} over {shr.n_scan_days} days",
            "",
            "| Metric | Top-5 | Top-10 | Top-20 |",
            "|---|---|---|---|",
            f"| Scan hit rate | {shr.scan_top5_rate:.1%} | {shr.scan_top10_rate:.1%} | {shr.scan_top20_rate:.1%} |",
            f"| Base rate     | {shr.base_top5_rate:.1%} | {shr.base_top10_rate:.1%} | {shr.base_top20_rate:.1%} |",
            f"| Lift          | {shr.lift_top5:.2f}x | {shr.lift_top10:.2f}x | {shr.lift_top20:.2f}x |",
            "",
        ]

    # Miss classification summary
    miss_counts: Dict[str, int] = {}
    for m in pred.misses:
        miss_counts[m.miss_class.value] = miss_counts.get(m.miss_class.value, 0) + 1
    if miss_counts:
        lines += [
            "## Miss Classification Summary",
            "",
            "| Class | Count |",
            "|---|---|",
        ]
        for cls, cnt in sorted(miss_counts.items(), key=lambda x: -x[1]):
            lines.append(f"| {cls} | {cnt} |")
        lines.append("")

    lines += [
        "## Recommendation",
        "",
        f"**{rec}** — {rec_text}",
        "",
        "### Option Details",
        "",
    ]
    for opt, desc in OPTION_LABELS.items():
        prefix = "✅ **RECOMMENDED**" if opt == rec else "—"
        lines.append(f"- {prefix} **{opt}**: {desc}")

    path.write_text("\n".join(lines), encoding="utf-8")
    return path


# ── Data quality report ───────────────────────────────────────────────────────

def _write_quality(result: EMPResult, out_dir: Path) -> Path:
    path = out_dir / "EMP_DATA_QUALITY.md"
    q = result.quality

    lines = [
        f"# EMP-001 Data Quality Report — {result.run_date}",
        "",
        f"| Metric | Value |",
        "|---|---|",
        f"| Total symbol-days | {q.total_symbol_days} |",
        f"| With daily OHLCV | {q.with_daily} ({q.with_daily / max(q.total_symbol_days,1):.1%}) |",
        f"| With intraday 5m | {q.with_intraday} ({q.with_intraday / max(q.total_symbol_days,1):.1%}) |",
        f"| With prev scan context | {q.with_prev_context} ({q.with_prev_context / max(q.total_symbol_days,1):.1%}) |",
        f"| yfinance available | {q.yf_available} |",
        "",
        "## Snapshot Coverage",
        "",
        "| Snapshot | Coverage% |",
        "|---|---|",
    ]
    for snap, pct in q.snapshot_coverage.items():
        lines.append(f"| {snap} | {pct}% |")

    if q.notes:
        lines += ["", "## Notes", ""]
        for n in q.notes:
            lines.append(f"- {n}")

    if result.warnings:
        lines += ["", "## Warnings", ""]
        for w in result.warnings:
            lines.append(f"- {w}")

    if result.look_ahead_violations:
        lines += ["", "## ⚠ Look-Ahead Violation Alerts", ""]
        for v in result.look_ahead_violations:
            lines.append(f"- **{v}**")

    lines += [
        "",
        "## Statistical Limitations",
        "",
        "- **Intraday data**: yfinance provides 5m bars for up to 60 calendar days.",
        "  Older trading days in the lookback window may lack intraday snapshots.",
        "- **Survivorship bias**: Only symbols currently in the scanner watchlist are",
        "  analysed. Delisted or removed symbols are excluded.",
        "- **Universe size**: Analysis uses ~40–50 symbols. With N=5 or N=10 rankings,",
        "  base rates are relatively high. Results for N=20 are more robust.",
        "- **Market regime**: All trading days are pooled. Persistence may differ",
        "  across bull/bear regimes (not segmented in this version).",
        "- **yfinance intraday granularity**: 5m bars — price is the 5-minute close.",
        "  True intraday lows/highs between bar boundaries are not captured.",
    ]

    path.write_text("\n".join(lines), encoding="utf-8")
    return path


# ── Findings JSON ─────────────────────────────────────────────────────────────

def _write_findings_json(result: EMPResult, out_dir: Path) -> Path:
    path = out_dir / "EMP_FINDINGS.json"
    pers = result.persistence
    pred = result.predictive

    findings: Dict[str, Any] = {
        "run_date":            result.run_date,
        "n_trading_days":      pers.n_trading_days,
        "n_symbols":           pers.n_symbols,
        "n_records":           len(result.records),
        "recommendation":      pred.recommendation,
        "recommendation_text": OPTION_LABELS.get(pred.recommendation, ""),
        "look_ahead_clean":    len(result.look_ahead_violations) == 0,
        "data_quality": {
            "total_symbol_days": result.quality.total_symbol_days,
            "with_daily_pct":    result.quality.with_daily / max(result.quality.total_symbol_days, 1),
            "with_intraday_pct": result.quality.with_intraday / max(result.quality.total_symbol_days, 1),
            "snapshot_coverage": result.quality.snapshot_coverage,
        },
        "persistence": {
            "intervals": [
                {
                    "label":                  iv.label,
                    "n_days":                 iv.n_days,
                    "overlap_top5":           iv.overlap.get(5),
                    "overlap_top10":          iv.overlap.get(10),
                    "overlap_top20":          iv.overlap.get(20),
                    "continuation_rate":      iv.continuation_rate,
                    "reversal_rate":          iv.reversal_rate,
                    "gainer_stays_positive":  iv.gainer_stays_positive,
                    "loser_stays_negative":   iv.loser_stays_negative,
                    "avg_top5_return":        iv.avg_final_return_top5,
                    "spearman_rho":           iv.spearman_rho,
                }
                for iv in pers.interval_stats
            ],
            "leader_persistence": pers.leader_persistence,
            "gap_stats": [
                {
                    "gap_class":        g.gap_class,
                    "n":                g.n,
                    "continuation_pct": g.continuation_pct,
                    "reversal_pct":     g.reversal_pct,
                    "avg_close_return": g.avg_close_return,
                    "prob_top5":        g.prob_top5_at_close,
                    "prob_top10":       g.prob_top10_at_close,
                    "avg_mfe":          g.avg_mfe,
                    "avg_mae":          g.avg_mae,
                }
                for g in pers.gap_stats
            ],
        },
        "predictive": {
            "model_a":       _model_to_dict(pred.model_a),
            "model_b_930":   _model_to_dict(pred.model_b_930),
            "model_b_945":   _model_to_dict(pred.model_b_945),
            "model_b_1000":  _model_to_dict(pred.model_b_1000),
            "model_c":       _model_to_dict(pred.model_c),
            "scan_hit_rate": _shr_to_dict(pred.scan_hit_rate),
            "miss_summary": {
                m.miss_class.value: sum(
                    1 for x in pred.misses if x.miss_class == m.miss_class
                )
                for m in pred.misses
            } if pred.misses else {},
        },
        "warnings":                result.warnings,
        "look_ahead_violations":   result.look_ahead_violations,
    }

    path.write_text(
        json.dumps(findings, indent=2, default=str),
        encoding="utf-8",
    )
    return path


# ── Helpers ───────────────────────────────────────────────────────────────────

def _max_lift(model) -> float:
    if not model or not model.metrics:
        return 0.0
    return max(m.lift for m in model.metrics)


def _model_to_dict(model) -> Optional[Dict]:
    if not model:
        return None
    return {
        "name":        model.name,
        "description": model.description,
        "window":      model.window,
        "metrics": [
            {
                "top_n":               m.top_n,
                "n_days":              m.n_days,
                "precision":           m.precision,
                "recall":              m.recall,
                "hit_rate":            m.hit_rate,
                "false_positive_rate": m.false_positive_rate,
                "lift":                m.lift,
                "base_rate":           m.base_rate,
            }
            for m in model.metrics
        ],
    }


def _shr_to_dict(shr) -> Optional[Dict]:
    if not shr:
        return None
    return {
        "scan_total_signals": shr.scan_total_signals,
        "scan_became_top5":   shr.scan_became_top5,
        "scan_became_top10":  shr.scan_became_top10,
        "scan_became_top20":  shr.scan_became_top20,
        "lift_top5":          shr.lift_top5,
        "lift_top10":         shr.lift_top10,
        "lift_top20":         shr.lift_top20,
    }
