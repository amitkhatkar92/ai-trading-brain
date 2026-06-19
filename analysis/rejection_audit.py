"""
analysis/rejection_audit.py
==============================
REJECTION_AUDIT_001 — Main orchestrator + CLI.

No live trading. No execution influence. Analysis only.

Usage:
    python analysis/rejection_audit.py
    python analysis/rejection_audit.py --reseed
    python analysis/rejection_audit.py --db data/rejection_audit.db --out reports/rejection_audit/

Synthetic data calibration
---------------------------
Rejection accuracy is deliberately set per reason to expose the core finding:

  LOW_SFT             → 78% accuracy (strongest signal — use it)
  HIGH_VOL_REGIME     → 73% accuracy (regime filter is reliable)
  LOW_DECISION_SCORE  → 62% accuracy (works but has room to improve)
  LOW_QUALITY_SCORE   → 63% accuracy
  LOW_CONVICTION      → 59% accuracy
  CORRELATED_POSITION → 55% accuracy
  MAX_POSITIONS       → 48% accuracy  ← broken — capacity limit is rejecting winners
  DAILY_LOSS_LIMIT    → 49% accuracy  ← below chance — stop-out limit cuts off recovery

Overall expected: ~64% accuracy (clear signal: system is working)
False negative rate: ~36% (captures "we rejected 36% winners")

Hypothetical PnL:
    Correct rejections save losses → large negative contribution
    False rejections miss winners  → positive contribution
    Net result: significantly negative → system is saving more than it's missing
"""

from __future__ import annotations

import os
import random
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from typing import Optional

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from analysis.rejection_tracker  import RejectionTracker, DB_PATH as DEFAULT_DB
from analysis.rejection_reporter import generate_rejection_report
from analysis.rejection_classifier import RejectionReason


# ── Paths ─────────────────────────────────────────────────────────────────────

DB_PATH     = DEFAULT_DB
REPORTS_DIR = os.path.join(ROOT, "reports", "rejection_audit")

_SEED = 2025


# ── Synthetic seeder ──────────────────────────────────────────────────────────

_SYMBOLS = [
    "RELIANCE", "INFY", "TCS",   "HINDALCO", "AXISBANK",
    "TATASTEEL", "HDFCBANK",     "ICICIBANK", "SBIN", "WIPRO",
    "BHARTIARTL", "BAJFINANCE",  "DRREDDY", "MARUTI", "SUNPHARMA",
    "ULTRACEMCO", "TATAMOTORS",  "NESTLEIND", "ADANIENT", "KOTAKBANK",
]

_STRATEGIES = [
    "Equity_Breakout", "Equity_Momentum",
    "Equity_MeanReversion", "Options_BullPutSpread", "Options_IronCondor",
]

_REGIMES = ["BULL", "RANGING", "BEAR", "HIGH_VOL"]
_VIX_BY_REGIME = {
    "BULL":     ("LOW",    11.0, 18.0),
    "RANGING":  ("MEDIUM", 14.0, 21.0),
    "BEAR":     ("HIGH",   19.0, 26.0),
    "HIGH_VOL": ("HIGH",   22.0, 32.0),
}

# Per-rejection-reason:
# (accuracy, trades_per_year, avg_quality_of_rejected, avg_price, avg_price_move_if_correct)
# accuracy = P(CORRECT_REJECTION)
# avg_quality_of_rejected = what quality tier did these rejected trades have?
_REASON_PROFILES = {
    RejectionReason.LOW_SFT.value: {
        "accuracy":    0.78,
        "n_per_year":  35,
        "avg_quality": 6.1,
        "quality_tier": "MEDIUM",
        "avg_price":   1_500,
        "price_range": (500, 4_000),
        "move_range":  (1.0, 12.0),   # move magnitude when correct
    },
    RejectionReason.HIGH_VOL_REGIME.value: {
        "accuracy":    0.73,
        "n_per_year":  28,
        "avg_quality": 6.4,
        "quality_tier": "MEDIUM",
        "avg_price":   1_200,
        "price_range": (300, 3_000),
        "move_range":  (1.5, 15.0),
    },
    RejectionReason.LOW_DECISION_SCORE.value: {
        "accuracy":    0.62,
        "n_per_year":  55,
        "avg_quality": 6.3,
        "quality_tier": "MEDIUM",
        "avg_price":   1_800,
        "price_range": (400, 5_000),
        "move_range":  (0.5, 10.0),
    },
    RejectionReason.LOW_QUALITY_SCORE.value: {
        "accuracy":    0.63,
        "n_per_year":  42,
        "avg_quality": 5.9,
        "quality_tier": "LOW",
        "avg_price":   1_600,
        "price_range": (400, 4_000),
        "move_range":  (0.5, 9.0),
    },
    RejectionReason.LOW_CONVICTION.value: {
        "accuracy":    0.59,
        "n_per_year":  30,
        "avg_quality": 6.9,      # these were decent-quality trades
        "quality_tier": "HIGH",
        "avg_price":   2_000,
        "price_range": (600, 5_000),
        "move_range":  (0.5, 8.0),
    },
    RejectionReason.CORRELATED_POSITION.value: {
        "accuracy":    0.55,
        "n_per_year":  22,
        "avg_quality": 7.1,      # often good trades — capacity constraint
        "quality_tier": "HIGH",
        "avg_price":   2_200,
        "price_range": (800, 6_000),
        "move_range":  (0.5, 7.0),
    },
    RejectionReason.MAX_POSITIONS.value: {
        "accuracy":    0.48,     # ← worse than chance — problem area
        "n_per_year":  18,
        "avg_quality": 7.4,      # we're rejecting HIGH quality trades due to capacity
        "quality_tier": "HIGH",
        "avg_price":   2_500,
        "price_range": (1_000, 7_000),
        "move_range":  (1.0, 10.0),
    },
    RejectionReason.DAILY_LOSS_LIMIT.value: {
        "accuracy":    0.49,     # ← also broken: cutting off recovery trades
        "n_per_year":  14,
        "avg_quality": 6.5,
        "quality_tier": "MEDIUM",
        "avg_price":   1_400,
        "price_range": (400, 3_500),
        "move_range":  (0.5, 8.0),
    },
    RejectionReason.MANUAL_OVERRIDE.value: {
        "accuracy":    0.56,
        "n_per_year":  8,
        "avg_quality": 6.8,
        "quality_tier": "HIGH",
        "avg_price":   1_800,
        "price_range": (500, 5_000),
        "move_range":  (0.5, 9.0),
    },
}


def seed_synthetic_data(
    db_path:  str = DB_PATH,
    years:    int = 2,
    seed:     int = _SEED,
) -> int:
    """Seed calibrated synthetic rejection data. Returns number of records inserted."""
    rng     = random.Random(seed)
    tracker = RejectionTracker(db_path)
    start   = datetime(2024, 1, 1)
    total   = 0

    for reason, prof in _REASON_PROFILES.items():
        n_trades      = int(prof["n_per_year"] * years)
        total_days    = years * 252
        day_offsets   = sorted(rng.sample(range(total_days), min(n_trades, total_days)))

        for day_off in day_offsets:
            trade_dt = start + timedelta(days=day_off)
            while trade_dt.weekday() >= 5:
                trade_dt += timedelta(days=1)

            regime_label = rng.choice(_REGIMES)
            vix_bkt, vix_lo, vix_hi = _VIX_BY_REGIME[regime_label]
            vix = round(rng.uniform(vix_lo, vix_hi), 2)

            # Quality scores for rejected trades (slightly below threshold)
            qbase     = prof["avg_quality"]
            quality   = round(rng.gauss(qbase, 0.6), 2)
            quality   = max(4.0, min(9.5, quality))
            decision  = round(rng.gauss(qbase - 0.1, 0.5), 2)
            decision  = max(3.5, min(9.5, decision))
            threshold = round(rng.uniform(6.3, 7.0), 2)

            # Price at rejection
            price_ref = round(rng.uniform(*prof["price_range"]), 1)

            # Price follow-through: determine outcome by accuracy param
            is_correct = rng.random() < prof["accuracy"]
            direction  = "LONG" if rng.random() < 0.65 else "SHORT"
            move_mag   = rng.uniform(*prof["move_range"])   # % move

            if is_correct:
                # Correct: price moves adversely
                raw_move = -move_mag if direction == "LONG" else move_mag
            else:
                # False: price moves favourably
                raw_move = move_mag if direction == "LONG" else -move_mag

            # Smaller moves at 1d/3d, full at 5d
            p1 = round(price_ref * (1 + raw_move * 0.30 / 100), 2)
            p3 = round(price_ref * (1 + raw_move * 0.65 / 100), 2)
            p5 = round(price_ref * (1 + raw_move / 100), 2)

            sft_options = ["HIGH", "MEDIUM", "LOW"]
            sft_weights = (
                [0.15, 0.50, 0.35] if reason == RejectionReason.LOW_SFT.value
                else [0.40, 0.40, 0.20]
            )
            sft_class = rng.choices(sft_options, weights=sft_weights)[0]

            tracker.ingest_rejection(
                symbol                 = rng.choice(_SYMBOLS),
                strategy               = rng.choice(_STRATEGIES),
                trade_date             = trade_dt.strftime("%Y-%m-%d"),
                decision_score         = decision,
                quality_score          = quality,
                quality_tier           = prof["quality_tier"],
                rejected_reason        = reason,
                price_at_rejection     = price_ref,
                direction              = direction,
                sft_class              = sft_class,
                market_regime          = regime_label,
                vix_bucket             = vix_bkt,
                vix                    = vix,
                rejected_at_threshold  = threshold,
                price_1d               = p1,
                price_3d               = p3,
                price_5d               = p5,
                is_backfill            = False,
                notes                  = f"synthetic reason={reason}",
            )
            total += 1

    return total


# ── Orchestrator ──────────────────────────────────────────────────────────────

def run_rejection_audit(
    db_path:      str  = DB_PATH,
    reports_dir:  str  = REPORTS_DIR,
    force_reseed: bool = False,
) -> None:
    """
    REJECTION_AUDIT_001

    Goal:
        Determine whether the rejection system is correctly filtering out
        bad trades, or whether it is incorrectly blocking winners.

    No live trading.
    No execution influence.
    Analysis only.
    """
    print("=" * 70)
    print("REJECTION_AUDIT_001 — Rejection System Analysis")
    print("=" * 70)

    tracker  = RejectionTracker(db_path)
    existing = tracker.count_total()

    # ── Step 1: Seed / Init ───────────────────────────────────────────────────
    print(f"\n[1/5] Database: {db_path}")
    print(f"      Existing rows: {existing}")

    if existing == 0 or force_reseed:
        print("      Seeding 2-year calibrated rejection dataset...")
        n = seed_synthetic_data(db_path, years=2)
        print(f"      Seeded {n} rejection records")
    else:
        print("      Using existing data (--reseed to regenerate)")

    # ── Step 2: Overall accuracy ──────────────────────────────────────────────
    print("\n[2/5] Overall rejection accuracy...")
    overall = tracker.overall_accuracy()
    print(f"\n  Total rejections:   {overall['total']}")
    print(f"  Classified:         {overall['classified']}")
    print(f"  Correct rejections: {overall['correct']}  "
          f"(saved from losses)")
    print(f"  False rejections:   {overall['false_rejections']}  "
          f"(missed winners)")
    print(f"  Neutral:            {overall['neutral']}  "
          f"(move too small)")
    print(f"\n  Rejection Accuracy: {overall['accuracy_pct']:.1f}%")

    # ── Step 3: Per-reason breakdown ──────────────────────────────────────────
    print("\n[3/5] Accuracy by rejection reason...")
    by_reason = tracker.accuracy_by_reason()
    print(f"\n  {'Reason':28s} {'Total':>6s} {'Correct':>8s} {'False':>6s} "
          f"{'Accuracy':>10s} {'Verdict':>20s}")
    print("  " + "─" * 82)

    reason_order = [
        "LOW_SFT", "HIGH_VOL_REGIME", "LOW_DECISION_SCORE",
        "LOW_QUALITY_SCORE", "LOW_CONVICTION", "CORRELATED_POSITION",
        "MAX_POSITIONS", "DAILY_LOSS_LIMIT", "MANUAL_OVERRIDE",
    ]
    for reason in reason_order:
        if reason not in by_reason:
            continue
        s = by_reason[reason]
        if s.get("classified", 0) == 0:
            continue
        icon = "✅" if s["accuracy_pct"] >= 65 else ("⚠️" if s["accuracy_pct"] >= 55 else "❌")
        print(
            f"  {reason:28s} {s['classified']:>6d} {s['correct']:>8d} "
            f"{s['false_rejections']:>6d} "
            f"  {s['accuracy_pct']:>5.1f}%  {icon}  "
            f"{s.get('verdict',''):>18s}"
        )

    # ── Step 4: Missed winner analysis ────────────────────────────────────────
    print("\n[4/5] Missed winner (false rejection) analysis...")
    missed  = tracker.missed_winner_analysis()
    hyp_pnl = tracker.hypothetical_total_pnl()
    if missed.get("count", 0) > 0:
        print(f"  Missed winners:     {missed['count']}")
        print(f"  Avg quality score:  {missed.get('avg_quality', 0):.2f}")
        print(f"  Avg 5d move:        {missed.get('avg_move_pct', 0):+.2f}%")
        print(f"  Best missed move:   {missed.get('max_move_pct', 0):+.2f}%")
        print(f"  Hypothetical PnL:   ₹{hyp_pnl:,.0f}  "
              f"({'saved' if hyp_pnl < 0 else 'missed'})")
        by_r = missed.get("by_reason", {})
        if by_r:
            top = sorted(by_r.items(), key=lambda x: -x[1])[:3]
            print(f"  Top reasons missed: {', '.join(f'{r}({n})' for r, n in top)}")

    # ── Step 5: Write report ──────────────────────────────────────────────────
    print("\n[5/5] Writing report...")
    date_str    = datetime.now().strftime("%Y%m%d")
    report_path = os.path.join(reports_dir, f"REJECTION_AUDIT_REPORT_{date_str}.md")
    os.makedirs(reports_dir, exist_ok=True)
    generate_rejection_report(tracker, report_path)
    print(f"      Report: {report_path}")

    print("\n" + "=" * 70)
    print("REJECTION_AUDIT_001 complete.")
    acc = overall["accuracy_pct"]
    if acc >= 70:
        verdict = "✅ REJECTION SYSTEM IS WORKING"
    elif acc >= 55:
        verdict = "⚠️  MARGINAL — REVIEW BROKEN REASONS"
    else:
        verdict = "❌ SYSTEM REJECTING TOO MANY WINNERS"
    print(f"Verdict: {verdict}  (accuracy={acc:.1f}%)")

    # Flag broken reasons
    broken = [
        r for r, s in by_reason.items()
        if s.get("verdict") in ("BROKEN", "UNDERPERFORMING")
        and s.get("classified", 0) >= 5
    ]
    if broken:
        print(f"Action:  Review these rejection criteria → {', '.join(broken)}")
    print("=" * 70)


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="REJECTION_AUDIT_001")
    parser.add_argument("--reseed", action="store_true",
                        help="Clear existing data and re-seed synthetic dataset")
    parser.add_argument("--db",     default=DB_PATH,     help="Path to SQLite database")
    parser.add_argument("--out",    default=REPORTS_DIR, help="Reports output directory")
    args = parser.parse_args()

    if args.reseed:
        print("Clearing existing rejection data...")
        with sqlite3.connect(args.db) as _conn:
            try:
                _conn.execute("DELETE FROM rejection_log")
                _conn.commit()
                print("Done.")
            except sqlite3.OperationalError:
                pass

    run_rejection_audit(
        db_path      = args.db,
        reports_dir  = args.out,
        force_reseed = False,
    )
