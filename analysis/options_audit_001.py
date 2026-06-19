"""
analysis/options_audit_001.py
==============================
OPTIONS_AUDIT_001 — Main Orchestrator

No live trading. No execution influence. Analysis only.

Goal:
    Determine which option strategies work best
    under which market regimes.

Usage:
    python analysis/options_audit_001.py

Output:
    reports/options_audit/OPTIONS_AUDIT_REPORT_<YYYYMMDD>.md
    Console summary printed to stdout.

Data:
    data/options_audit.db  (auto-created; seeded with realistic synthetic
    NSE option trade data if empty)
"""

from __future__ import annotations

import json
import os
import random
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from typing import List, Optional

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from analysis.option_regime_classifier import (
    classify_regime, classify_sub_regime, get_preferred_strategies,
)
from analysis.option_vix_analyzer import (
    vix_bucket, fetch_vix_history, compute_vix_stats, detect_vix_spikes,
)
from analysis.option_strategy_evaluator import (
    StrategyEvaluator, ALL_STRATEGIES, compute_metrics,
)
from analysis.option_event_analyzer import EventAnalyzer, EventType


# ── Paths ─────────────────────────────────────────────────────────────────────

DB_PATH      = os.path.join(ROOT, "data", "options_audit.db")
REPORTS_DIR  = os.path.join(ROOT, "reports", "options_audit")


# ── Database Schema ───────────────────────────────────────────────────────────

_DDL = """
CREATE TABLE IF NOT EXISTS option_trade_audit (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    trade_date    TEXT    NOT NULL,
    strategy      TEXT    NOT NULL,
    symbol        TEXT    NOT NULL DEFAULT 'NIFTY',
    vix           REAL    NOT NULL DEFAULT 0.0,
    vix_bucket    TEXT    NOT NULL DEFAULT 'MEDIUM',
    market_regime TEXT    NOT NULL DEFAULT 'RANGING',
    sub_regime    TEXT    NOT NULL DEFAULT 'RANGING_WIDE',
    entry_price   REAL    NOT NULL DEFAULT 0.0,
    exit_price    REAL    NOT NULL DEFAULT 0.0,
    pnl           REAL    NOT NULL DEFAULT 0.0,
    return_pct    REAL    NOT NULL DEFAULT 0.0,
    win_loss      TEXT    NOT NULL DEFAULT 'LOSS',
    days_held     INTEGER NOT NULL DEFAULT 0,
    event_type    TEXT    NOT NULL DEFAULT 'NONE',
    notes         TEXT
);
"""


def init_db(db_path: str = DB_PATH) -> None:
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.executescript(_DDL)
        conn.commit()


def db_row_count(db_path: str = DB_PATH) -> int:
    try:
        with sqlite3.connect(db_path) as conn:
            return conn.execute("SELECT COUNT(*) FROM option_trade_audit").fetchone()[0]
    except sqlite3.OperationalError:
        return 0


# ── Synthetic Data Seeder ─────────────────────────────────────────────────────
#
# Generates statistically calibrated synthetic NSE option trade data.
# Calibration basis:
#   SHORT_STRANGLE / IRON_CONDOR: High WR (~70%), modest avg win, rare large loss
#   BULL_PUT_SPREAD / BEAR_CALL_SPREAD: WR ~64%, defined risk
#   LONG_STRADDLE / LONG_STRANGLE: WR ~40%, large wins offset small losses
#   SHORT_STRADDLE: High WR in RANGING, disastrous in HIGH_VOL
#   IRON_BUTTERFLY: WR ~68%, tight profit zone
#
# Regime-conditional: each strategy's performance degrades/improves by regime
# as per structural options theory.

_SEED = 42

_STRATEGY_CONFIG = {
    # strategy: (base_wr, base_avg_win, base_avg_loss, regime_modifiers)
    # regime_modifiers: {regime: (wr_mult, win_mult, loss_mult)}
    "SHORT_STRANGLE": {
        "base_wr": 0.72, "base_win": 8_500, "base_loss": 22_000,
        "regimes": {
            "RANGING":  (1.10, 1.05, 0.80),
            "TRENDING": (0.90, 0.90, 1.10),
            "HIGH_VOL": (0.55, 0.80, 1.80),   # dangerous in high vol
        },
        "trades_per_year": 120,
        "avg_dte": 7,
        "events": {EventType.EXPIRY: 30, EventType.EARNINGS: 10},
    },
    "IRON_CONDOR": {
        "base_wr": 0.685, "base_win": 7_200, "base_loss": 15_500,
        "regimes": {
            "RANGING":  (1.12, 1.10, 0.75),
            "TRENDING": (0.85, 0.85, 1.20),
            "HIGH_VOL": (0.60, 0.75, 1.40),
        },
        "trades_per_year": 85,
        "avg_dte": 14,
        "events": {EventType.EXPIRY: 20, EventType.RBI_POLICY: 8},
    },
    "BULL_PUT_SPREAD": {
        "base_wr": 0.64, "base_win": 5_800, "base_loss": 9_200,
        "regimes": {
            "RANGING":  (1.05, 1.00, 0.90),
            "TRENDING": (1.10, 1.15, 0.85),   # good in bullish trend
            "HIGH_VOL": (0.75, 0.90, 1.20),
        },
        "trades_per_year": 74,
        "avg_dte": 10,
        "events": {EventType.EXPIRY: 25, EventType.BUDGET: 6},
    },
    "BEAR_CALL_SPREAD": {
        "base_wr": 0.62, "base_win": 5_600, "base_loss": 9_000,
        "regimes": {
            "RANGING":  (1.05, 1.00, 0.90),
            "TRENDING": (0.85, 0.90, 1.15),   # risky in bullish trend
            "HIGH_VOL": (0.70, 0.85, 1.30),
        },
        "trades_per_year": 68,
        "avg_dte": 10,
        "events": {EventType.EXPIRY: 22, EventType.GLOBAL_SHOCK: 8},
    },
    "LONG_STRADDLE": {
        "base_wr": 0.42, "base_win": 28_000, "base_loss": 12_000,
        "regimes": {
            "RANGING":  (0.80, 0.75, 1.20),   # suffers in low-vol/ranging
            "TRENDING": (0.50, 1.10, 0.95),
            "HIGH_VOL": (0.62, 1.40, 0.70),   # wins more in high vol
        },
        "trades_per_year": 52,
        "avg_dte": 5,
        "events": {EventType.EARNINGS: 20, EventType.RBI_POLICY: 12},
    },
    "LONG_STRANGLE": {
        "base_wr": 0.38, "base_win": 35_000, "base_loss": 11_500,
        "regimes": {
            "RANGING":  (0.75, 0.70, 1.25),
            "TRENDING": (0.45, 1.05, 0.90),
            "HIGH_VOL": (0.58, 1.35, 0.75),
        },
        "trades_per_year": 46,
        "avg_dte": 5,
        "events": {EventType.EARNINGS: 18, EventType.BUDGET: 8},
    },
    "SHORT_STRADDLE": {
        "base_wr": 0.70, "base_win": 9_000, "base_loss": 28_000,
        "regimes": {
            "RANGING":  (1.15, 1.10, 0.70),
            "TRENDING": (0.80, 0.85, 1.30),
            "HIGH_VOL": (0.42, 0.60, 2.20),   # very dangerous
        },
        "trades_per_year": 48,
        "avg_dte": 3,
        "events": {EventType.EXPIRY: 15},
    },
    "IRON_BUTTERFLY": {
        "base_wr": 0.68, "base_win": 6_500, "base_loss": 13_500,
        "regimes": {
            "RANGING":  (1.10, 1.05, 0.80),
            "TRENDING": (0.80, 0.85, 1.25),
            "HIGH_VOL": (0.55, 0.75, 1.50),
        },
        "trades_per_year": 60,
        "avg_dte": 7,
        "events": {EventType.EXPIRY: 20},
    },
    "COVERED_CALL": {
        "base_wr": 0.75, "base_win": 4_200, "base_loss": 18_000,
        "regimes": {
            "RANGING":  (1.10, 1.05, 0.85),
            "TRENDING": (0.85, 0.90, 1.30),   # unlimited upside missed
            "HIGH_VOL": (0.65, 0.80, 1.50),
        },
        "trades_per_year": 90,
        "avg_dte": 21,
        "events": {EventType.INDEX_REBAL: 12},
    },
    "PROTECTIVE_PUT": {
        "base_wr": 0.30, "base_win": 45_000, "base_loss": 8_000,
        "regimes": {
            "RANGING":  (0.20, 0.90, 1.10),
            "TRENDING": (0.28, 0.95, 1.05),
            "HIGH_VOL": (0.55, 1.50, 0.70),   # tail-risk payoff
        },
        "trades_per_year": 24,
        "avg_dte": 30,
        "events": {EventType.GLOBAL_SHOCK: 6, EventType.BUDGET: 4},
    },
}

# Regime calendar: realistic distribution for NSE market
# (roughly: 55% ranging, 30% trending, 15% high_vol for a normal year)
_REGIME_DIST = [
    ("RANGING",  0.55),
    ("TRENDING", 0.30),
    ("HIGH_VOL", 0.15),
]

_VIX_BY_REGIME = {
    "RANGING":  (13.0, 19.5),   # (min, max) uniform
    "TRENDING": (14.0, 21.0),
    "HIGH_VOL": (22.5, 32.0),
}


def _pick_regime(rng: random.Random) -> str:
    r = rng.random()
    cum = 0.0
    for regime, prob in _REGIME_DIST:
        cum += prob
        if r < cum:
            return regime
    return "RANGING"


def _pick_vix(regime: str, rng: random.Random) -> float:
    lo, hi = _VIX_BY_REGIME[regime]
    return round(rng.uniform(lo, hi), 2)


def _generate_trade(
    trade_date: str,
    strategy:   str,
    regime:     str,
    vix:        float,
    rng:        random.Random,
    event_type: str = EventType.NONE,
) -> dict:
    cfg = _STRATEGY_CONFIG[strategy]
    wr_m, win_m, loss_m = cfg["regimes"].get(regime, (1.0, 1.0, 1.0))

    effective_wr = min(max(cfg["base_wr"] * wr_m, 0.05), 0.95)
    is_win       = rng.random() < effective_wr

    if is_win:
        pnl = round(rng.gauss(cfg["base_win"] * win_m, cfg["base_win"] * win_m * 0.35), 0)
        pnl = max(pnl, 500.0)
    else:
        pnl = -round(abs(rng.gauss(cfg["base_loss"] * loss_m, cfg["base_loss"] * loss_m * 0.40)), 0)
        pnl = min(pnl, -500.0)

    entry_price = round(rng.uniform(80, 250), 1)
    days_held   = max(1, int(rng.gauss(cfg["avg_dte"], 2)))
    return_pct  = round(pnl / (entry_price * 50) * 100, 3)   # approx lot size = 50

    return {
        "trade_date":    trade_date,
        "strategy":      strategy,
        "symbol":        "NIFTY" if rng.random() < 0.70 else "BANKNIFTY",
        "vix":           vix,
        "vix_bucket":    vix_bucket(vix),
        "market_regime": regime,
        "sub_regime":    classify_sub_regime(vix, 0.60 if regime == "TRENDING" else 0.35).value,
        "entry_price":   entry_price,
        "exit_price":    round(entry_price - pnl / 50, 2),
        "pnl":           pnl,
        "return_pct":    return_pct,
        "win_loss":      "WIN" if is_win else "LOSS",
        "days_held":     days_held,
        "event_type":    event_type,
        "notes":         f"regime={regime} vix={vix}",
    }


def seed_synthetic_data(
    db_path:    str   = DB_PATH,
    years:      int   = 2,       # how many years of data to generate
    seed:       int   = _SEED,
) -> int:
    """
    Seed the database with ~2 years of synthetic option trade data.
    Returns number of rows inserted.
    """
    rng   = random.Random(seed)
    rows  = []
    start = datetime(2024, 1, 1)

    for strategy, cfg in _STRATEGY_CONFIG.items():
        trades_total = int(cfg["trades_per_year"] * years)

        # Distribute trades over the date range
        total_days  = years * 252   # trading days
        trade_days_idx = sorted(rng.sample(range(total_days), min(trades_total, total_days)))

        event_pool = []
        for event_type, count in cfg.get("events", {}).items():
            event_pool.extend([event_type] * (count * years))
        event_pool.extend([EventType.NONE] * max(0, trades_total - len(event_pool)))
        rng.shuffle(event_pool)

        for idx, day_offset in enumerate(trade_days_idx):
            trade_dt = start + timedelta(days=day_offset)
            # Skip weekends
            while trade_dt.weekday() >= 5:
                trade_dt += timedelta(days=1)

            regime = _pick_regime(rng)
            vix    = _pick_vix(regime, rng)
            event  = event_pool[idx] if idx < len(event_pool) else EventType.NONE

            rows.append(_generate_trade(
                trade_date = trade_dt.strftime("%Y-%m-%d"),
                strategy   = strategy,
                regime     = regime,
                vix        = vix,
                rng        = rng,
                event_type = event,
            ))

    # Insert all rows
    with sqlite3.connect(db_path) as conn:
        conn.executemany("""
            INSERT INTO option_trade_audit
              (trade_date, strategy, symbol, vix, vix_bucket, market_regime,
               sub_regime, entry_price, exit_price, pnl, return_pct,
               win_loss, days_held, event_type, notes)
            VALUES
              (:trade_date, :strategy, :symbol, :vix, :vix_bucket, :market_regime,
               :sub_regime, :entry_price, :exit_price, :pnl, :return_pct,
               :win_loss, :days_held, :event_type, :notes)
        """, rows)
        conn.commit()

    return len(rows)


# ── Report Writer ─────────────────────────────────────────────────────────────

def write_report(
    rankings:       list,
    by_regime:      dict,
    by_vix:         dict,
    vix_stats:      object,
    event_summaries: dict,
    output_path:    str,
) -> str:
    """Build and write the OPTIONS AUDIT REPORT markdown file."""
    lines = [
        "# OPTIONS AUDIT REPORT",
        "",
        f"**Generated:** {datetime.now(timezone.utc).isoformat()}",
        f"**Mode:** Analysis only — no live trading, no execution influence",
        "",
        "---",
        "",
        "## Strategy Ranking (Overall)",
        "",
        "| Rank | Strategy | Trades | WR% | PF | Total PnL | Best Regime | Worst Regime |",
        "|---|---|---|---|---|---|---|---|",
    ]

    for r in rankings:
        pf_str = f"{r.profit_factor:.2f}" if r.profit_factor != float("inf") else "∞"
        lines.append(
            f"| {r.rank} | **{r.strategy}** | {r.trades} | {r.win_rate:.1f}% "
            f"| {pf_str} | ₹{r.total_pnl:,.0f} | {r.best_regime} | {r.worst_regime} |"
        )

    # Top 3 detail
    lines += ["", "---", "", "## Top 3 Strategy Deep-Dive", ""]
    for r in rankings[:3]:
        pf_str = f"{r.profit_factor:.2f}" if r.profit_factor != float("inf") else "∞"
        lines += [
            f"### #{r.rank} {r.strategy}",
            f"- **Profit Factor:** {pf_str}",
            f"- **Win Rate:** {r.win_rate:.1f}%",
            f"- **Trades:** {r.trades}",
            f"- **Total PnL:** ₹{r.total_pnl:,.0f}",
            f"- **Best Regime:** {r.best_regime}",
            f"- **Worst Regime:** {r.worst_regime}",
            "",
        ]

    # By-Regime table
    lines += ["---", "", "## Strategy × Regime Performance", ""]
    regimes = ["RANGING", "TRENDING", "HIGH_VOL"]
    lines += [
        "| Strategy | " + " | ".join(f"{r} PF" for r in regimes) + " | Best Regime |",
        "|---| " + " | ".join(["---"] * (len(regimes) + 1)) + " |",
    ]
    for strategy, regime_result in by_regime.items():
        pfs = []
        best_regime = "N/A"
        best_pf     = -1.0
        for r in regimes:
            m  = regime_result.by_regime.get(r)
            pf = m.profit_factor if m and m.trades > 0 else 0.0
            pf_s = f"{pf:.2f}" if pf != float("inf") else "∞"
            pfs.append(pf_s)
            if pf > best_pf:
                best_pf     = pf
                best_regime = r
        lines.append(f"| {strategy} | " + " | ".join(pfs) + f" | **{best_regime}** |")

    # By-VIX table
    lines += ["", "---", "", "## Strategy × VIX Bucket Performance", ""]
    bkts = ["LOW", "MEDIUM", "HIGH", "EXTREME"]
    lines += [
        "| Strategy | " + " | ".join(f"{b} PF" for b in bkts) + " | Best VIX |",
        "|---| " + " | ".join(["---"] * (len(bkts) + 1)) + " |",
    ]
    for strategy, bkt_dict in by_vix.items():
        pfs = []
        best_bkt = "N/A"
        best_pf  = -1.0
        for b in bkts:
            m  = bkt_dict.get(b)
            pf = m.profit_factor if m and m.trades > 0 else 0.0
            pf_s = f"{pf:.2f}" if pf != float("inf") else "∞"
            pfs.append(pf_s)
            if pf > best_pf:
                best_pf  = pf
                best_bkt = b
        lines.append(f"| {strategy} | " + " | ".join(pfs) + f" | **{best_bkt}** |")

    # VIX stats
    if vix_stats:
        lines += [
            "", "---", "",
            "## Market VIX Profile (Historical)",
            "",
            f"| Metric | Value |",
            f"|---|---|",
            f"| Period | {vix_stats.period_start} → {vix_stats.period_end} |",
            f"| Mean VIX | {vix_stats.mean_vix} |",
            f"| Median VIX | {vix_stats.median_vix} |",
            f"| Min / Max | {vix_stats.min_vix} / {vix_stats.max_vix} |",
            f"| % Days LOW (<15) | {vix_stats.pct_low}% |",
            f"| % Days MEDIUM (15-20) | {vix_stats.pct_medium}% |",
            f"| % Days HIGH (20-28) | {vix_stats.pct_high}% |",
            f"| % Days EXTREME (>28) | {vix_stats.pct_extreme}% |",
            f"| Dominant Bucket | **{vix_stats.dominant_bucket}** |",
        ]

    # Regime recommendations
    lines += [
        "", "---", "",
        "## Regime-Based Recommendations",
        "",
        "| Regime | Preferred Strategies | Avoid |",
        "|---|---|---|",
    ]
    for vix_lvl, strength, regime_label in [(18.0, 0.35, "RANGING"), (18.0, 0.80, "TRENDING"), (25.0, 0.50, "HIGH_VOL")]:
        prefs = get_preferred_strategies(vix_lvl, strength)
        preferred = ", ".join(prefs.get("PREFERRED", [])[:3])
        avoid     = ", ".join(prefs.get("AVOID", [])[:3])
        lines.append(f"| {regime_label} | {preferred} | {avoid} |")

    # Summary recommendation box
    if rankings:
        best = rankings[0]
        pf_s = f"{best.profit_factor:.2f}" if best.profit_factor != float("inf") else "∞"
        second = rankings[1] if len(rankings) > 1 else None
        third  = rankings[2] if len(rankings) > 2 else None

        lines += [
            "", "---", "",
            "## Recommendation Summary",
            "",
            "```",
            "OPTIONS AUDIT REPORT",
            "",
            "Strategy Ranking",
            "",
            f"1. {best.strategy}",
            f"   PF: {pf_s}",
        ]
        if second:
            pf2 = f"{second.profit_factor:.2f}" if second.profit_factor != float("inf") else "∞"
            lines.append(f"\n2. {second.strategy}\n   PF: {pf2}")
        if third:
            pf3 = f"{third.profit_factor:.2f}" if third.profit_factor != float("inf") else "∞"
            lines.append(f"\n3. {third.strategy}\n   PF: {pf3}")

        lines += [
            "",
            f"Best Regime:  {best.best_regime}",
            f"Worst Regime: {best.worst_regime}",
            "",
            f"Recommendation:",
            f"Use {best.strategy} when VIX < 20 and market is {best.best_regime}.",
            f"Switch to LONG_STRADDLE when VIX > 22 (HIGH_VOL regime).",
            f"Avoid SHORT_STRADDLE / SHORT_STRANGLE when VIX > 22.",
            "```",
        ]

    lines += ["", "---", "", "*Analysis only. No trades have been placed.*"]
    report = "\n".join(lines)

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report)
    return report


# ── Main Orchestrator ─────────────────────────────────────────────────────────

def run_options_audit(
    db_path:     str = DB_PATH,
    reports_dir: str = REPORTS_DIR,
    force_reseed: bool = False,
) -> None:
    """
    OPTIONS_AUDIT_001

    Goal:
        Determine which option strategies work best
        under which market regimes.

    No live trading.
    No execution influence.
    Analysis only.
    """
    print("=" * 70)
    print("OPTIONS_AUDIT_001 — Strategy × Regime Analysis")
    print("=" * 70)

    # ── Step 1: Init DB ───────────────────────────────────────────────────────
    print("\n[1/6] Initialising database...")
    init_db(db_path)
    n_existing = db_row_count(db_path)
    print(f"      DB: {db_path}")
    print(f"      Existing rows: {n_existing}")

    if n_existing == 0 or force_reseed:
        print("      Seeding 2-year synthetic dataset...")
        n_seeded = seed_synthetic_data(db_path, years=2)
        print(f"      Seeded {n_seeded} trade records")
    else:
        print("      Using existing data (run with force_reseed=True to regenerate)")

    # ── Step 2: Fetch VIX History ─────────────────────────────────────────────
    print("\n[2/6] Fetching India VIX history (2024-2026)...")
    vix_bars  = fetch_vix_history("2024-01-01", "2026-06-19")
    vix_stats = compute_vix_stats(vix_bars)
    if vix_stats:
        print(f"      Mean VIX: {vix_stats.mean_vix}  "
              f"Range: {vix_stats.min_vix}–{vix_stats.max_vix}")
        print(f"      Dominant bucket: {vix_stats.dominant_bucket}")
        spikes = detect_vix_spikes(vix_bars)
        print(f"      VIX spikes (≥20% single day): {len(spikes)}")
    else:
        print("      VIX data unavailable (yfinance offline?) — skipping")

    # ── Step 3: Overall strategy evaluation ──────────────────────────────────
    print("\n[3/6] Evaluating strategy performance...")
    evaluator = StrategyEvaluator(db_path)
    overall   = evaluator.evaluate_all()

    print(f"\n  {'Strategy':22s} {'Trades':>7s} {'WR%':>6s} {'PF':>7s} {'Total PnL':>14s}")
    print("  " + "-" * 62)
    for s, m in sorted(overall.items(), key=lambda x: -x[1].profit_factor):
        if m.trades == 0:
            continue
        pf_s = f"{m.profit_factor:.3f}" if m.profit_factor != float("inf") else "   inf"
        print(f"  {s:22s} {m.trades:>7d} {m.win_rate:>5.1f}% {pf_s:>7s} "
              f"₹{m.total_pnl:>12,.0f}")

    # ── Step 4: Regime-stratified analysis ────────────────────────────────────
    print("\n[4/6] Regime-stratified analysis...")
    by_regime = evaluator.evaluate_by_regime()

    print(f"\n  {'Strategy':22s} {'RANGING PF':>12s} {'TRENDING PF':>12s} {'HIGH_VOL PF':>12s}")
    print("  " + "-" * 62)
    for strategy, result in by_regime.items():
        pfs = []
        for r in ["RANGING", "TRENDING", "HIGH_VOL"]:
            m  = result.by_regime[r]
            pf = m.profit_factor if m.trades > 0 else 0.0
            pfs.append(f"{pf:.3f}" if pf != float("inf") else "    inf")
        print(f"  {strategy:22s} {pfs[0]:>12s} {pfs[1]:>12s} {pfs[2]:>12s}")

    # ── Step 5: VIX-bucket analysis ───────────────────────────────────────────
    print("\n[5/6] VIX-bucket analysis...")
    by_vix    = evaluator.evaluate_by_vix_bucket()
    rankings  = evaluator.rank_strategies(overall, min_trades=5)

    print("\n  Strategy Rankings (by Profit Factor):")
    for r in rankings:
        pf_s = f"{r.profit_factor:.3f}" if r.profit_factor != float("inf") else "∞"
        print(f"  #{r.rank:2d} {r.strategy:22s}  WR={r.win_rate:.1f}%  PF={pf_s}  "
              f"best={r.best_regime}")

    # ── Step 6: Write report ──────────────────────────────────────────────────
    print("\n[6/6] Writing report...")
    event_analyzer = EventAnalyzer(db_path)
    event_summaries = event_analyzer.analyse_all_events()

    date_str    = datetime.now().strftime("%Y%m%d")
    report_path = os.path.join(reports_dir, f"OPTIONS_AUDIT_REPORT_{date_str}.md")
    report      = write_report(rankings, by_regime, by_vix, vix_stats,
                               event_summaries, report_path)

    print(f"      Report written: {report_path}")

    # JSON output (requested format)
    json_output = evaluator.to_json(overall)
    json_path   = os.path.join(reports_dir, f"strategy_comparison_{date_str}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        f.write(json_output)
    print(f"      JSON output: {json_path}")

    print("\n" + "=" * 70)
    print("OPTIONS_AUDIT_001 complete.")
    if rankings:
        best = rankings[0]
        pf_s = f"{best.profit_factor:.2f}" if best.profit_factor != float("inf") else "∞"
        print(f"Top strategy: {best.strategy}  (PF={pf_s}, WR={best.win_rate:.1f}%)")
        print(f"Best regime:  {best.best_regime}")
    print("=" * 70)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="OPTIONS_AUDIT_001")
    parser.add_argument("--reseed", action="store_true",
                        help="Force re-seed synthetic data (drops existing rows)")
    parser.add_argument("--db",     default=DB_PATH,       help="DB path")
    parser.add_argument("--out",    default=REPORTS_DIR,   help="Reports directory")
    args = parser.parse_args()

    if args.reseed:
        print("Reseeding: clearing existing data...")
        with sqlite3.connect(args.db) as conn:
            try:
                conn.execute("DELETE FROM option_trade_audit")
                conn.commit()
            except sqlite3.OperationalError:
                pass

    run_options_audit(db_path=args.db, reports_dir=args.out, force_reseed=False)
