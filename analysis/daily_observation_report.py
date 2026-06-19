"""
analysis/daily_observation_report.py
=============================================
LIVE_OBSERVATION_DAILY_REPORT — Evening research newspaper.

Aggregates all analysis layers into one dated daily briefing.

Usage
-----
    python analysis/daily_observation_report.py

    # Specify a date (default: today)
    python analysis/daily_observation_report.py --date 2026-06-19

    # Custom output dir
    python analysis/daily_observation_report.py --out reports/daily/

    # Print to stdout as well
    python analysis/daily_observation_report.py --print

Output
------
    reports/daily/DAILY_OBSERVATION_REPORT_YYYYMMDD.md

Sections
--------
1. Regime Snapshot         — current regime + transition probability
2. Today's Observations    — new trades added today
3. Symbol Performance      — most improved / worst performing
4. SFT Leaderboard         — highest / lowest signal follow-through
5. Evidence Scoreboard     — recommendation validation progress
6. Top Validated Rec       — closest to approval-ready
7. Running Totals          — cumulative stats since system start
"""

from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)

# Internal modules
from analysis.live_observation_tracker import get_live_tracker, DB_PATH as LIVE_DB
from analysis.recommendation_tracker   import get_recommendation_tracker, DB_PATH as REC_DB
from analysis.regime_transition_engine import analyse_regime_transition, RegimeTransitionReport

REAL_OPTIONS_DB = os.path.join(_ROOT, "data", "real_options_audit.db")
SFT_DB          = os.path.join(_ROOT, "data", "phase_d_sft.db")
OUT_DIR         = os.path.join(_ROOT, "reports", "daily")

BASELINE = 0.50


# ── Data helpers ──────────────────────────────────────────────────────────────

def _rows(db_path: str, sql: str, params: tuple = ()) -> List[dict]:
    if not os.path.exists(db_path):
        return []
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        return [dict(r) for r in conn.execute(sql, params).fetchall()]


def _scalar(db_path: str, sql: str, params: tuple = (), default=0):
    if not os.path.exists(db_path):
        return default
    with sqlite3.connect(db_path) as conn:
        row = conn.execute(sql, params).fetchone()
    return row[0] if row and row[0] is not None else default


# ── Section builders ──────────────────────────────────────────────────────────

def _section_regime(reports: List[RegimeTransitionReport]) -> List[str]:
    _ICON = {"STABLE": "🟢", "WATCH": "🟡", "ALERT": "🟠", "IMMINENT": "🔴"}
    lines = ["## 1. Regime Snapshot", ""]
    lines += ["| Underlying | Regime | VIX | VIX %ile (60d) | Transition Prob | Alert |"]
    lines += ["|------------|--------|-----|----------------|-----------------|-------|"]
    for r in reports:
        icon = _ICON.get(r.alert_level, "⚪")
        lines.append(
            f"| **{r.underlying}** | {r.current_regime} "
            f"| {r.current_vix:.1f} | {r.vix_percentile_60d:.0f}th "
            f"| **{r.transition_probability:.0f}%** "
            f"| {icon} **{r.alert_level}** |"
        )
    lines += [""]

    # Dominant regime signal
    if reports:
        r = reports[0]
        top_signal = max(r.signals, key=lambda s: s.score)
        lines += [
            f"> **Dominant signal:** {top_signal.name} (score {top_signal.score:.0f}/100) — "
            f"{top_signal.description}",
            "",
            f"> **Strategy implication:** {r.strategy_implication}",
            "",
        ]
    return lines


def _section_todays_observations(live_db: str, date_str: str) -> List[str]:
    lines  = ["## 2. Today's Observations", ""]
    today_rows = _rows(
        live_db,
        "SELECT * FROM live_observations WHERE trade_date=? ORDER BY observed_at DESC",
        (date_str,),
    )
    new_today = len(today_rows)

    if new_today == 0:
        lines += [f"_No new observations recorded on {date_str}._", ""]
        lines += ["> Run `python analysis/live_observation_audit.py` after market close.", ""]
        return lines

    lines += [f"**{new_today} new observation(s) recorded today.**", ""]
    lines += ["| Symbol | Strategy | Tier | Regime | Outcome | PnL |"]
    lines += ["|--------|----------|------|--------|---------|-----|"]
    for r in today_rows[:10]:
        pnl_str = f"₹{r['pnl']:+.0f}" if r.get("pnl") else "—"
        lines.append(
            f"| {r['symbol']} | {r['strategy']} "
            f"| {r['quality_tier'] or '—'} "
            f"| {r['market_regime'] or '—'} "
            f"| {r['outcome']} "
            f"| {pnl_str} |"
        )
    if new_today > 10:
        lines += [f"_...and {new_today - 10} more._"]
    lines += [""]
    return lines


def _section_symbol_performance(live_db: str) -> List[str]:
    lines = ["## 3. Symbol Performance", ""]

    # By symbol: total PnL and win rate (closed trades only)
    sym_rows = _rows(
        live_db,
        """SELECT symbol,
                  COUNT(*) AS n,
                  SUM(CASE WHEN outcome='WIN' THEN 1 ELSE 0 END) AS wins,
                  COALESCE(SUM(pnl), 0) AS total_pnl
           FROM live_observations
           WHERE outcome IN ('WIN','LOSS')
           GROUP BY symbol
           HAVING n >= 3
           ORDER BY total_pnl DESC""",
    )
    if not sym_rows:
        lines += ["_Insufficient closed trades for symbol ranking (need ≥ 3 per symbol)._", ""]
        return lines

    best  = sym_rows[0] if sym_rows else None
    worst = sym_rows[-1] if len(sym_rows) > 1 else None

    if best:
        wr_best = round(best["wins"] / best["n"] * 100, 1)
        lines += [
            f"**Most improved:** `{best['symbol']}` — "
            f"PnL ₹{best['total_pnl']:+,.0f}, WR {wr_best}% (n={best['n']})"
        ]
    if worst and worst["symbol"] != (best["symbol"] if best else ""):
        wr_worst = round(worst["wins"] / worst["n"] * 100, 1)
        lines += [
            f"**Worst performing:** `{worst['symbol']}` — "
            f"PnL ₹{worst['total_pnl']:+,.0f}, WR {wr_worst}% (n={worst['n']})"
        ]
    lines += [""]

    if len(sym_rows) >= 3:
        lines += ["**Full symbol ranking:**", ""]
        lines += ["| Symbol | Closed n | WR% | Total PnL |"]
        lines += ["|--------|----------|-----|-----------|"]
        for r in sym_rows[:10]:
            wr = round(r["wins"] / r["n"] * 100, 1) if r["n"] else 0
            lines.append(
                f"| `{r['symbol']}` | {r['n']} | {wr}% | ₹{r['total_pnl']:+,.0f} |"
            )
        lines += [""]
    return lines


def _section_sft_leaderboard(sft_db: str) -> List[str]:
    lines = ["## 4. SFT Leaderboard", ""]
    if not os.path.exists(sft_db):
        lines += ["_SFT database not found. Run `phase_d_sft_recommendation.py` first._", ""]
        return lines

    try:
        top_rows = _rows(
            sft_db,
            """SELECT symbol, sft_class, sft_score, recorded_at
               FROM sft_records
               WHERE sft_score IS NOT NULL
               ORDER BY sft_score DESC
               LIMIT 5""",
        )
        bot_rows = _rows(
            sft_db,
            """SELECT symbol, sft_class, sft_score, recorded_at
               FROM sft_records
               WHERE sft_score IS NOT NULL
               ORDER BY sft_score ASC
               LIMIT 5""",
        )
    except Exception:
        lines += ["_SFT table schema mismatch — update phase_d_sft_recommendation.py._", ""]
        return lines

    if not top_rows:
        lines += ["_No SFT records found._", ""]
        return lines

    lines += ["**Highest signal follow-through (prime candidates):**", ""]
    lines += ["| Symbol | SFT Class | Score | Last Updated |"]
    lines += ["|--------|-----------|-------|--------------|"]
    for r in top_rows:
        date_str = str(r.get("recorded_at", ""))[:10]
        lines.append(f"| `{r['symbol']}` | {r['sft_class']} | {r.get('sft_score', 0):.3f} | {date_str} |")
    lines += [""]

    if bot_rows:
        lines += ["**Lowest signal follow-through (approach with caution):**", ""]
        lines += ["| Symbol | SFT Class | Score | Last Updated |"]
        lines += ["|--------|-----------|-------|--------------|"]
        for r in bot_rows:
            date_str = str(r.get("recorded_at", ""))[:10]
            lines.append(f"| `{r['symbol']}` | {r['sft_class']} | {r.get('sft_score', 0):.3f} | {date_str} |")
        lines += [""]
    return lines


def _section_evidence_scoreboard(rec_db: str, live_db: str) -> List[str]:
    lines = ["## 5. Recommendation Evidence Scoreboard", ""]

    total_recs  = _scalar(rec_db,  "SELECT COUNT(*) FROM recommendations")
    pending     = _scalar(rec_db,  "SELECT COUNT(*) FROM recommendations WHERE status='PENDING'")
    approved    = _scalar(rec_db,  "SELECT COUNT(*) FROM recommendations WHERE status='APPROVED'")
    implemented = _scalar(rec_db,  "SELECT COUNT(*) FROM recommendations WHERE status='IMPLEMENTED'")
    total_live  = _scalar(live_db, "SELECT COUNT(*) FROM live_observations WHERE outcome IN ('WIN','LOSS')")

    lines += ["| Metric | Value |"]
    lines += ["|--------|-------|"]
    lines += [f"| Total recommendations | {total_recs} |"]
    lines += [f"| PENDING (awaiting evidence) | {pending} |"]
    lines += [f"| APPROVED (ready to implement) | {approved} |"]
    lines += [f"| IMPLEMENTED | {implemented} |"]
    lines += [f"| Live closed trades (evidence) | {total_live} |"]

    needed = max(0, 30 - total_live)
    pct    = min(100, int(total_live / 30 * 100))
    bar    = "█" * (pct // 5) + "░" * (20 - pct // 5)
    lines += [f"| Evidence progress to READY | `[{bar}]` {pct}% |"]
    lines += [""]

    if total_live < 10:
        lines += [f"> ⏳ **{needed} more closed trades** needed before any recommendation can be validated.", ""]
    elif total_live < 30:
        lines += [f"> 🔵 **Emerging evidence.** {needed} more trades to reach the READY threshold.", ""]
    else:
        lines += [f"> 🟡 **Validation-ready.** Run `recommendation_scorecard.py` for detailed analysis.", ""]

    return lines


def _section_top_recommendation(rec_db: str, live_db: str) -> List[str]:
    lines = ["## 6. Top Validation Candidate", ""]

    # Find the P1/P2 rec with highest live match count
    recs = _rows(rec_db,
        "SELECT * FROM recommendations WHERE status='PENDING' AND priority <= 2 ORDER BY priority"
    )
    if not recs:
        lines += ["_No pending P1/P2 recommendations._", ""]
        return lines

    # Simple: pick the first P1 with the most specific target
    best_rec = recs[0]
    lines += [
        f"**Rec ID:** `{best_rec['rec_id']}`  ",
        f"**Type:** {best_rec['rec_type']}  ",
        f"**Target:** `{best_rec['target']}`  ",
        f"**Confidence:** {best_rec['confidence']}  ",
        f"**Suggestion:** {best_rec['suggestion']}  ",
        "",
        f"**Rationale:** {best_rec['rationale']}  ",
        "",
        "> Status: **PENDING** — requires live evidence before human review.",
        "",
    ]
    return lines


def _section_running_totals(live_db: str) -> List[str]:
    lines = ["## 7. Running Totals (Since System Start)", ""]

    total   = _scalar(live_db, "SELECT COUNT(*) FROM live_observations")
    open_   = _scalar(live_db, "SELECT COUNT(*) FROM live_observations WHERE outcome='OPEN'")
    wins    = _scalar(live_db, "SELECT COUNT(*) FROM live_observations WHERE outcome='WIN'")
    losses  = _scalar(live_db, "SELECT COUNT(*) FROM live_observations WHERE outcome='LOSS'")
    closed  = wins + losses
    wr      = round(wins / closed * 100, 1) if closed else 0.0
    tot_pnl = _scalar(live_db, "SELECT COALESCE(SUM(pnl),0) FROM live_observations WHERE outcome IN ('WIN','LOSS')", default=0.0)

    lines += ["| Metric | Value |"]
    lines += ["|--------|-------|"]
    lines += [f"| Total observations | {total} |"]
    lines += [f"| Open (pending close) | {open_} |"]
    lines += [f"| Closed wins | {wins} |"]
    lines += [f"| Closed losses | {losses} |"]
    lines += [f"| Win rate (closed) | {wr:.1f}% |"]
    lines += [f"| Total PnL (closed) | ₹{tot_pnl:+,.0f} |"]
    lines += [""]

    # Tier win rates
    tier_rows = _rows(
        live_db,
        """SELECT quality_tier,
                  COUNT(*) AS n,
                  SUM(CASE WHEN outcome='WIN' THEN 1 ELSE 0 END) AS wins
           FROM live_observations
           WHERE outcome IN ('WIN','LOSS')
           GROUP BY quality_tier""",
    )
    if tier_rows:
        lines += ["**Win rate by quality tier:**", ""]
        lines += ["| Tier | n | WR% | Baseline gap |"]
        lines += ["|------|---|-----|--------------|"]
        for r in sorted(tier_rows, key=lambda x: -x.get("wins", 0) / max(x["n"], 1)):
            n  = r["n"]
            wr = round(r["wins"] / n * 100, 1) if n else 0.0
            gap = f"{wr - 50.0:+.1f}pp"
            lines.append(f"| {r['quality_tier']} | {n} | {wr}% | {gap} |")
        lines += [""]

    # Strategy win rates
    strat_rows = _rows(
        live_db,
        """SELECT strategy,
                  COUNT(*) AS n,
                  SUM(CASE WHEN outcome='WIN' THEN 1 ELSE 0 END) AS wins
           FROM live_observations
           WHERE outcome IN ('WIN','LOSS')
           GROUP BY strategy
           HAVING COUNT(*) >= 3
           ORDER BY SUM(CASE WHEN outcome='WIN' THEN 1 ELSE 0 END) * 1.0 / COUNT(*) DESC""",
    )
    if strat_rows:
        lines += ["**Win rate by strategy (≥3 trades):**", ""]
        lines += ["| Strategy | n | WR% |"]
        lines += ["|----------|---|-----|"]
        for r in strat_rows[:8]:
            wr = round(r["wins"] / r["n"] * 100, 1)
            lines.append(f"| {r['strategy']} | {r['n']} | {wr}% |")
        lines += [""]

    return lines


# ── Master report generator ───────────────────────────────────────────────────

def generate_daily_report(
    date_str:   str  = "",
    out_dir:    str  = OUT_DIR,
    live_db:    str  = LIVE_DB,
    rec_db:     str  = REC_DB,
    print_to_stdout: bool = False,
) -> str:
    date_str  = date_str or datetime.now().strftime("%Y-%m-%d")
    now_str   = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    os.makedirs(out_dir, exist_ok=True)
    out_path  = os.path.join(out_dir, f"DAILY_OBSERVATION_REPORT_{date_str.replace('-','')}.md")

    # ── Fetch regime data (live download) ─────────────────────────────────────
    print("  Fetching regime data...", end=" ", flush=True)
    regime_reports = []
    for underlying in ["NIFTY", "BANKNIFTY"]:
        try:
            r = analyse_regime_transition(underlying, period="3mo", use_cache=True)
            regime_reports.append(r)
        except Exception as e:
            print(f"(skipped {underlying}: {e})", end=" ")
    print("done")

    # ── Build report ──────────────────────────────────────────────────────────
    md = []
    md += [f"# Daily Observation Report — {date_str}", ""]
    md += [f"**Generated:** {now_str}  "]
    md += [f"**System:** AI Trading Brain — Research Layer  "]
    md += [""]
    md += [
        "> This report is your daily evidence checkpoint. It does not approve",
        "> recommendations or trigger trades. All decisions require human review.",
        "",
    ]

    md += ["---"]
    md += _section_regime(regime_reports)
    md += ["---"]
    md += _section_todays_observations(live_db, date_str)
    md += ["---"]
    md += _section_symbol_performance(live_db)
    md += ["---"]
    md += _section_sft_leaderboard(SFT_DB)
    md += ["---"]
    md += _section_evidence_scoreboard(rec_db, live_db)
    md += ["---"]
    md += _section_top_recommendation(rec_db, live_db)
    md += ["---"]
    md += _section_running_totals(live_db)
    md += ["---"]
    md += [
        "*Generated by LIVE_OBSERVATION_DAILY_REPORT.*  ",
        "*No live trading code was modified.*",
    ]

    content = "\n".join(md)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(content)

    if print_to_stdout:
        print("\n" + content)

    return out_path


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> None:
    p = argparse.ArgumentParser(
        description="LIVE_OBSERVATION_DAILY_REPORT — evening research newspaper"
    )
    p.add_argument("--date",     default="",       help="Date YYYY-MM-DD (default: today)")
    p.add_argument("--out",      default=OUT_DIR,  help="Output directory")
    p.add_argument("--live-db",  default=LIVE_DB,  help="live_observations.db path")
    p.add_argument("--rec-db",   default=REC_DB,   help="recommendations.db path")
    p.add_argument("--print",    action="store_true", dest="print_stdout",
                   help="Also print report to stdout")
    args = p.parse_args()

    print(f"\nLIVE_OBSERVATION_DAILY_REPORT\n")
    path = generate_daily_report(
        date_str         = args.date,
        out_dir          = args.out,
        live_db          = args.live_db,
        rec_db           = args.rec_db,
        print_to_stdout  = args.print_stdout,
    )
    print(f"\nReport: {path}")


if __name__ == "__main__":
    main()
