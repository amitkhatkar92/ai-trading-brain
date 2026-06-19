"""
analysis/real_options_reporter.py
======================================
REAL_OPTIONS_AUDIT_002 — Markdown report generator.

Reads from RealOptionsTracker, compares against synthetic OPTIONS_AUDIT_001
findings, and produces a dated report.

Output: reports/real_options/REAL_OPTIONS_AUDIT_002_YYYYMMDD.md
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Dict, List, Optional

from analysis.real_options_tracker import RealOptionsTracker
from analysis.options_backtester import SYNTHETIC_BENCHMARK, ALL_STRATEGIES

_ROOT    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR  = os.path.join(_ROOT, "reports", "real_options")


# ── Verdict helpers ───────────────────────────────────────────────────────────

def _verdict(real_wr: float, syn_wr: float, n: int) -> str:
    if n < 20:
        return "⚪ INSUFFICIENT"
    diff = real_wr - syn_wr
    if abs(diff) <= 10:
        return "✅ CONFIRMED"
    if diff < -10:
        return f"🔴 OVERSTATED (+{abs(diff):.1f}pp gap)"
    return f"🟢 UNDERSTATED (real beats by {diff:.1f}pp)"


def _pf_verdict(real_pf: float, syn_pf: Optional[float]) -> str:
    if syn_pf is None:
        return "—"
    diff = real_pf - syn_pf
    if abs(diff) <= 0.3:
        return "✅ MATCH"
    if diff < -0.3:
        return f"🔴 WEAKER (−{abs(diff):.2f})"
    return f"🟢 STRONGER (+{diff:.2f})"


def _best_regime(rows_by_regime: List[dict], strategy: str) -> str:
    strat_rows = [r for r in rows_by_regime if r["strategy"] == strategy and r["n"] >= 10]
    if not strat_rows:
        return "—"
    best = max(strat_rows, key=lambda r: r["win_rate"])
    return f"{best['regime']} ({best['win_rate']:.1f}%, n={best['n']})"


# ── Main report generator ─────────────────────────────────────────────────────

def generate_real_options_report(
    tracker:  RealOptionsTracker,
    run_id:   str,
    period:   str = "2y",
    out_dir:  str = OUT_DIR,
) -> str:
    """Write markdown report and return path."""
    os.makedirs(out_dir, exist_ok=True)
    date_str  = datetime.now(timezone.utc).strftime("%Y%m%d")
    out_path  = os.path.join(out_dir, f"REAL_OPTIONS_AUDIT_002_{date_str}.md")
    now_str   = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    date_from, date_to = tracker.date_range(run_id)
    total     = tracker.total_records(run_id)

    by_strategy        = tracker.stats_by_strategy(run_id)
    by_strategy_regime = tracker.stats_by_strategy_regime(run_id)
    by_vix             = tracker.stats_by_vix_bucket(run_id)
    by_underlying      = tracker.underlying_summary(run_id)

    # Index by strategy for quick lookup
    strat_map: Dict[str, dict] = {r["strategy"]: r for r in by_strategy}

    md = []

    # ── Header ────────────────────────────────────────────────────────────────
    md += ["# REAL_OPTIONS_AUDIT_002 — Real Market Validation", ""]
    md += [f"**Run ID:** `{run_id}`  "]
    md += [f"**Generated:** {now_str}  "]
    md += [f"**Data period:** {date_from} → {date_to} ({period})  "]
    md += [f"**Total records:** {total:,}  "]
    md += [f"**Instruments:** NIFTY + BANKNIFTY  "]
    md += [""]
    md += ["> This audit validates synthetic OPTIONS_AUDIT_001 findings against"]
    md += ["> real NIFTY/BANKNIFTY price history and India VIX data."]
    md += ["> No live trading code was modified."]
    md += [""]

    # ── Executive Summary ─────────────────────────────────────────────────────
    md += ["---", "## Executive Summary", ""]
    confirmed    = sum(1 for r in by_strategy if r["n"] >= 20
                       and abs(r["win_rate"] - SYNTHETIC_BENCHMARK.get(r["strategy"], {}).get("win_rate", r["win_rate"])) <= 10)
    overstated   = sum(1 for r in by_strategy if r["n"] >= 20
                       and r["win_rate"] < SYNTHETIC_BENCHMARK.get(r["strategy"], {}).get("win_rate", r["win_rate"]) - 10)
    understated  = sum(1 for r in by_strategy if r["n"] >= 20
                       and r["win_rate"] > SYNTHETIC_BENCHMARK.get(r["strategy"], {}).get("win_rate", r["win_rate"]) + 10)

    md += ["| Finding | Count |"]
    md += ["|---------|-------|"]
    md += [f"| ✅ Synthetic findings CONFIRMED | {confirmed} |"]
    md += [f"| 🔴 Synthetic findings OVERSTATED | {overstated} |"]
    md += [f"| 🟢 Real outperforms synthetic | {understated} |"]
    md += [f"| ⚪ Insufficient real data | {len(by_strategy) - confirmed - overstated - understated} |"]
    md += [""]

    # ── Strategy-by-Strategy Comparison ──────────────────────────────────────
    md += ["---", "## Strategy Validation vs OPTIONS_AUDIT_001 Synthetic", ""]
    md += ["| Strategy | Real WR% | Real PF | Synthetic WR% | Synthetic PF | WR Verdict | PF Verdict | Best Regime (Real) |"]
    md += ["|----------|----------|---------|---------------|--------------|------------|------------|--------------------|"]

    for strat in ALL_STRATEGIES:
        real = strat_map.get(strat)
        syn  = SYNTHETIC_BENCHMARK.get(strat, {})
        if real is None:
            md += [f"| `{strat}` | — | — | {syn.get('win_rate','—')}% | {syn.get('profit_factor','—')} | ⚪ NO DATA | — | — |"]
            continue
        wr_v = _verdict(real["win_rate"], syn.get("win_rate", real["win_rate"]), real["n"])
        pf_v = _pf_verdict(real["profit_factor"], syn.get("profit_factor"))
        br   = _best_regime(by_strategy_regime, strat)
        md += [
            f"| `{strat}` | **{real['win_rate']:.1f}%** (n={real['n']}) "
            f"| {real['profit_factor']:.2f} "
            f"| {syn.get('win_rate','—')}% "
            f"| {syn.get('profit_factor','—')} "
            f"| {wr_v} | {pf_v} | {br} |"
        ]
    md += [""]

    # ── Regime Breakdown ──────────────────────────────────────────────────────
    md += ["---", "## Win Rate by Strategy × Regime", ""]
    md += ["| Strategy | HIGH_VOL | RANGING | TRENDING |"]
    md += ["|----------|----------|---------|----------|"]

    regime_data: Dict[str, Dict[str, dict]] = {}
    for r in by_strategy_regime:
        regime_data.setdefault(r["strategy"], {})[r["regime"]] = r

    for strat in ALL_STRATEGIES:
        rd = regime_data.get(strat, {})
        def _wr(regime: str) -> str:
            r = rd.get(regime)
            if r is None or r["n"] < 5:
                return "—"
            return f"{r['win_rate']:.1f}% (n={r['n']})"

        syn_best = SYNTHETIC_BENCHMARK.get(strat, {}).get("best_regime", "")
        md += [
            f"| `{strat}` ({'⭐ best=' + syn_best if syn_best else ''}) "
            f"| {_wr('HIGH_VOL')} | {_wr('RANGING')} | {_wr('TRENDING')} |"
        ]
    md += [""]

    # ── VIX Bucket Breakdown ──────────────────────────────────────────────────
    md += ["---", "## Win Rate by VIX Bucket", ""]
    md += ["LOW VIX < 14 | MEDIUM 14–22 | HIGH > 22", ""]
    md += ["| Strategy | LOW VIX | MEDIUM VIX | HIGH VIX |"]
    md += ["|----------|---------|------------|----------|"]

    vix_data: Dict[str, Dict[str, dict]] = {}
    for r in by_vix:
        vix_data.setdefault(r["strategy"], {})[r["vix_bucket"]] = r

    for strat in ALL_STRATEGIES:
        vd = vix_data.get(strat, {})
        def _vwr(bucket: str) -> str:
            r = vd.get(bucket)
            if r is None or r["n"] < 5:
                return "—"
            return f"{r['win_rate']:.1f}% (n={r['n']})"

        md += [f"| `{strat}` | {_vwr('LOW')} | {_vwr('MEDIUM')} | {_vwr('HIGH')} |"]
    md += [""]

    # ── NIFTY vs BANKNIFTY ────────────────────────────────────────────────────
    md += ["---", "## NIFTY vs BANKNIFTY Comparison", ""]
    md += ["| Strategy | NIFTY WR% | BANKNIFTY WR% | Delta |"]
    md += ["|----------|-----------|---------------|-------|"]

    ul_data: Dict[str, Dict[str, dict]] = {}
    for r in by_underlying:
        ul_data.setdefault(r["strategy"], {})[r["underlying"]] = r

    for strat in ALL_STRATEGIES:
        ud = ul_data.get(strat, {})
        n_row = ud.get("NIFTY")
        b_row = ud.get("BANKNIFTY")
        n_wr  = f"{n_row['win_rate']:.1f}% (n={n_row['n']})" if n_row else "—"
        b_wr  = f"{b_row['win_rate']:.1f}% (n={b_row['n']})" if b_row else "—"
        delta = "—"
        if n_row and b_row:
            d     = b_row["win_rate"] - n_row["win_rate"]
            delta = f"{d:+.1f}pp"
        md += [f"| `{strat}` | {n_wr} | {b_wr} | {delta} |"]
    md += [""]

    # ── Key Findings ──────────────────────────────────────────────────────────
    md += ["---", "## Key Findings & Production Readiness", ""]

    # Top 3 strategies by real profit factor
    sorted_strats = sorted(
        [r for r in by_strategy if r["n"] >= 20],
        key=lambda r: -r["profit_factor"]
    )
    if sorted_strats:
        md += ["**Top strategies by real profit factor:**", ""]
        for i, r in enumerate(sorted_strats[:3], 1):
            syn = SYNTHETIC_BENCHMARK.get(r["strategy"], {})
            v   = _verdict(r["win_rate"], syn.get("win_rate", r["win_rate"]), r["n"])
            md += [f"{i}. `{r['strategy']}` — PF={r['profit_factor']:.2f}, "
                   f"WR={r['win_rate']:.1f}% — {v}"]
        md += [""]

    md += ["**Production readiness verdict:**", ""]
    md += ["| Strategy | Confirmed by Real Data | Safe to Promote? |"]
    md += ["|----------|------------------------|------------------|"]
    for strat in ALL_STRATEGIES:
        real = strat_map.get(strat)
        syn  = SYNTHETIC_BENCHMARK.get(strat, {})
        if real is None or real["n"] < 20:
            md += [f"| `{strat}` | ⚪ Insufficient data | ❌ Do not promote yet |"]
            continue
        diff = real["win_rate"] - syn.get("win_rate", real["win_rate"])
        pf   = real["profit_factor"]
        ok   = abs(diff) <= 15 and pf >= 1.2 and real["n"] >= 30
        md += [
            f"| `{strat}` | {'✅ Yes' if abs(diff) <= 10 else '⚠️ Partial'} "
            f"| {'✅ Promote to paper' if ok else '⚠️ Watch — needs more data'} |"
        ]
    md += [""]

    # ── Footer ────────────────────────────────────────────────────────────────
    md += ["---"]
    md += ["*Generated by REAL_OPTIONS_AUDIT_002.*  "]
    md += ["*No live trading code was modified.*"]

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md))

    return out_path
