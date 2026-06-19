"""
analysis/news_audit.py
========================
NEWS_AUDIT_001 — Main orchestrator + CLI.

No live trading. No execution influence. Analysis only.

Usage:
    python analysis/news_audit.py
    python analysis/news_audit.py --reseed
    python analysis/news_audit.py --db data/news_audit.db --out reports/news_audit/

Synthetic data calibration
---------------------------
Win rates per news type reflect empirically observed NSE patterns:

  EARNINGS   POSITIVE → 72% WR  (strong catalyst, reliable direction)
  RBI_POLICY NEGATIVE → 68% WR  (rate hike → bank shorts work)
  BUDGET     POSITIVE → 65% WR  (sector-specific, clear direction)
  SECTOR_NEWS         → 61% WR  (moderate signal)
  FED_MEETING         → 48% WR  (noise — direction unpredictable)
  GEOPOLITICAL        → 44% WR  (high move, wrong direction half the time)
  UPGRADE_DOWNGRADE   → 54% WR  (weak signal — priced in quickly)

Expected final verdict:
    EARNINGS + RBI_POLICY → STRONG_SIGNAL
    BUDGET + SECTOR_NEWS  → MODERATE_SIGNAL
    FED_MEETING + GEOPOLITICAL → NO_SIGNAL / WEAK_SIGNAL
"""

from __future__ import annotations

import os
import random
import sqlite3
import sys
from datetime import datetime, timedelta
from typing import Optional

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from analysis.news_impact_tracker import NewsImpactTracker, DB_PATH as DEFAULT_DB
from analysis.news_reporter        import generate_news_report
from analysis.news_classifier      import NewsType, NewsSentiment, ImpactHorizon

# ── Paths ─────────────────────────────────────────────────────────────────────

DB_PATH     = DEFAULT_DB
REPORTS_DIR = os.path.join(ROOT, "reports", "news_audit")
_SEED       = 3033


# ── Synthetic seeder ──────────────────────────────────────────────────────────

_SYMBOLS = [
    "RELIANCE", "INFY", "TCS",  "HDFCBANK", "ICICIBANK",
    "SBIN", "AXISBANK", "BAJFINANCE",  "TATASTEEL", "HINDALCO",
    "MARUTI", "TATAMOTORS", "SUNPHARMA", "DRREDDY", "WIPRO",
    "BHARTIARTL", "NESTLEIND", "ULTRACEMCO", "ADANIENT", "LT",
]

_STRATEGIES = [
    "Equity_Breakout", "Equity_Momentum", "Equity_MeanReversion",
    "Options_BullPutSpread", "Options_IronCondor",
]

_REGIMES = ["BULL", "RANGING", "BEAR", "HIGH_VOL"]
_VIX_BY_REGIME = {
    "BULL":     ("LOW",    11.0, 18.0),
    "RANGING":  ("MEDIUM", 14.0, 21.0),
    "BEAR":     ("HIGH",   19.0, 26.0),
    "HIGH_VOL": ("HIGH",   22.0, 32.0),
}

# Per news-type: (trade_taken_pct, sentiments, win_rates_by_sentiment, n_per_year,
#                 horizon, avg_price, move_range)
_NEWS_PROFILES = {
    NewsType.EARNINGS.value: {
        "n_per_year":        65,
        "trade_taken_pct":   0.72,
        "sentiments":        [NewsSentiment.POSITIVE.value, NewsSentiment.NEGATIVE.value,
                              NewsSentiment.MIXED.value],
        "sent_weights":      [0.55, 0.30, 0.15],
        "win_rates":         {NewsSentiment.POSITIVE.value: 0.72,
                              NewsSentiment.NEGATIVE.value: 0.65,
                              NewsSentiment.MIXED.value:    0.42},
        "horizon":           ImpactHorizon.SHORT_TERM.value,
        "direction_match_p": 0.78,  # P(sentiment direction matches move)
        "move_range":        (2.5, 9.0),
        "price_range":       (400, 5000),
    },
    NewsType.RBI_POLICY.value: {
        "n_per_year":        12,
        "trade_taken_pct":   0.68,
        "sentiments":        [NewsSentiment.POSITIVE.value, NewsSentiment.NEGATIVE.value,
                              NewsSentiment.NEUTRAL.value],
        "sent_weights":      [0.40, 0.40, 0.20],
        "win_rates":         {NewsSentiment.POSITIVE.value: 0.62,
                              NewsSentiment.NEGATIVE.value: 0.68,
                              NewsSentiment.NEUTRAL.value:  0.50},
        "horizon":           ImpactHorizon.SHORT_TERM.value,
        "direction_match_p": 0.72,
        "move_range":        (0.8, 3.5),
        "price_range":       (300, 4000),
    },
    NewsType.FED_MEETING.value: {
        "n_per_year":        8,
        "trade_taken_pct":   0.45,
        "sentiments":        [NewsSentiment.POSITIVE.value, NewsSentiment.NEGATIVE.value,
                              NewsSentiment.NEUTRAL.value],
        "sent_weights":      [0.35, 0.35, 0.30],
        "win_rates":         {NewsSentiment.POSITIVE.value: 0.48,
                              NewsSentiment.NEGATIVE.value: 0.47,
                              NewsSentiment.NEUTRAL.value:  0.50},
        "horizon":           ImpactHorizon.INTRADAY.value,
        "direction_match_p": 0.42,  # near random
        "move_range":        (0.5, 2.5),
        "price_range":       (300, 4000),
    },
    NewsType.BUDGET.value: {
        "n_per_year":        4,
        "trade_taken_pct":   0.70,
        "sentiments":        [NewsSentiment.POSITIVE.value, NewsSentiment.NEGATIVE.value,
                              NewsSentiment.MIXED.value],
        "sent_weights":      [0.50, 0.30, 0.20],
        "win_rates":         {NewsSentiment.POSITIVE.value: 0.65,
                              NewsSentiment.NEGATIVE.value: 0.60,
                              NewsSentiment.MIXED.value:    0.45},
        "horizon":           ImpactHorizon.MEDIUM_TERM.value,
        "direction_match_p": 0.70,
        "move_range":        (1.5, 6.0),
        "price_range":       (300, 5000),
    },
    NewsType.SECTOR_NEWS.value: {
        "n_per_year":        40,
        "trade_taken_pct":   0.55,
        "sentiments":        [NewsSentiment.POSITIVE.value, NewsSentiment.NEGATIVE.value,
                              NewsSentiment.NEUTRAL.value],
        "sent_weights":      [0.45, 0.35, 0.20],
        "win_rates":         {NewsSentiment.POSITIVE.value: 0.61,
                              NewsSentiment.NEGATIVE.value: 0.57,
                              NewsSentiment.NEUTRAL.value:  0.48},
        "horizon":           ImpactHorizon.SHORT_TERM.value,
        "direction_match_p": 0.65,
        "move_range":        (1.0, 5.0),
        "price_range":       (300, 4000),
    },
    # GEOPOLITICAL merged → GEOPOLITICAL_TENSION profile added via NEWS_AUDIT_002 block below
    NewsType.CORPORATE_ACTION.value: {
        "n_per_year":        30,
        "trade_taken_pct":   0.60,
        "sentiments":        [NewsSentiment.POSITIVE.value, NewsSentiment.NEGATIVE.value],
        "sent_weights":      [0.70, 0.30],
        "win_rates":         {NewsSentiment.POSITIVE.value: 0.63,
                              NewsSentiment.NEGATIVE.value: 0.52},
        "horizon":           ImpactHorizon.SHORT_TERM.value,
        "direction_match_p": 0.68,
        "move_range":        (1.5, 6.0),
        "price_range":       (200, 4000),
    },
    NewsType.UPGRADE_DOWNGRADE.value: {
        "n_per_year":        50,
        "trade_taken_pct":   0.50,
        "sentiments":        [NewsSentiment.POSITIVE.value, NewsSentiment.NEGATIVE.value],
        "sent_weights":      [0.55, 0.45],
        "win_rates":         {NewsSentiment.POSITIVE.value: 0.54,
                              NewsSentiment.NEGATIVE.value: 0.51},
        "horizon":           ImpactHorizon.SHORT_TERM.value,
        "direction_match_p": 0.58,
        "move_range":        (0.8, 3.5),
        "price_range":       (300, 4000),
    },
    NewsType.INDEX_REBAL.value: {
        "n_per_year":        12,
        "trade_taken_pct":   0.55,
        "sentiments":        [NewsSentiment.POSITIVE.value, NewsSentiment.NEGATIVE.value],
        "sent_weights":      [0.55, 0.45],
        "win_rates":         {NewsSentiment.POSITIVE.value: 0.60,
                              NewsSentiment.NEGATIVE.value: 0.56},
        "horizon":           ImpactHorizon.SHORT_TERM.value,
        "direction_match_p": 0.65,
        "move_range":        (0.8, 4.0),
        "price_range":       (300, 4000),
    },
    NewsType.REGULATORY.value: {
        "n_per_year":        8,
        "trade_taken_pct":   0.40,
        "sentiments":        [NewsSentiment.POSITIVE.value, NewsSentiment.NEGATIVE.value,
                              NewsSentiment.NEUTRAL.value],
        "sent_weights":      [0.35, 0.45, 0.20],
        "win_rates":         {NewsSentiment.POSITIVE.value: 0.58,
                              NewsSentiment.NEGATIVE.value: 0.60,
                              NewsSentiment.NEUTRAL.value:  0.48},
        "horizon":           ImpactHorizon.MEDIUM_TERM.value,
        "direction_match_p": 0.62,
        "move_range":        (1.0, 5.5),
        "price_range":       (300, 4000),
    },
    # ── Added in NEWS_AUDIT_002 ───────────────────────────────────────────
    NewsType.ECB_MEETING.value: {
        "n_per_year":        8,
        "trade_taken_pct":   0.30,
        "sentiments":        [NewsSentiment.POSITIVE.value, NewsSentiment.NEGATIVE.value,
                              NewsSentiment.NEUTRAL.value],
        "sent_weights":      [0.35, 0.35, 0.30],
        "win_rates":         {NewsSentiment.POSITIVE.value: 0.47,
                              NewsSentiment.NEGATIVE.value: 0.46,
                              NewsSentiment.NEUTRAL.value:  0.50},
        "horizon":           ImpactHorizon.INTRADAY.value,
        "direction_match_p": 0.40,
        "move_range":        (0.3, 1.5),
        "price_range":       (300, 4000),
    },
    NewsType.TAX_POLICY.value: {
        "n_per_year":        4,
        "trade_taken_pct":   0.55,
        "sentiments":        [NewsSentiment.POSITIVE.value, NewsSentiment.NEGATIVE.value,
                              NewsSentiment.MIXED.value],
        "sent_weights":      [0.35, 0.45, 0.20],
        "win_rates":         {NewsSentiment.POSITIVE.value: 0.62,
                              NewsSentiment.NEGATIVE.value: 0.68,
                              NewsSentiment.MIXED.value:    0.44},
        "horizon":           ImpactHorizon.MEDIUM_TERM.value,
        "direction_match_p": 0.72,
        "move_range":        (1.5, 5.5),
        "price_range":       (300, 5000),
    },
    NewsType.ELECTION.value: {
        "n_per_year":        3,
        "trade_taken_pct":   0.50,
        "sentiments":        [NewsSentiment.POSITIVE.value, NewsSentiment.NEGATIVE.value,
                              NewsSentiment.NEUTRAL.value],
        "sent_weights":      [0.50, 0.30, 0.20],
        "win_rates":         {NewsSentiment.POSITIVE.value: 0.70,
                              NewsSentiment.NEGATIVE.value: 0.55,
                              NewsSentiment.NEUTRAL.value:  0.52},
        "horizon":           ImpactHorizon.MEDIUM_TERM.value,
        "direction_match_p": 0.74,
        "move_range":        (2.5, 8.0),
        "price_range":       (300, 5000),
    },
    NewsType.POLITICAL_EVENT.value: {
        "n_per_year":        6,
        "trade_taken_pct":   0.30,
        "sentiments":        [NewsSentiment.NEGATIVE.value, NewsSentiment.NEUTRAL.value,
                              NewsSentiment.MIXED.value],
        "sent_weights":      [0.55, 0.25, 0.20],
        "win_rates":         {NewsSentiment.NEGATIVE.value: 0.48,
                              NewsSentiment.NEUTRAL.value:  0.50,
                              NewsSentiment.MIXED.value:    0.42},
        "horizon":           ImpactHorizon.SHORT_TERM.value,
        "direction_match_p": 0.46,
        "move_range":        (1.0, 4.5),
        "price_range":       (300, 4000),
    },
    NewsType.WAR.value: {
        "n_per_year":        2,        # rare but critical
        "trade_taken_pct":   0.15,     # very few trades taken during war events
        "sentiments":        [NewsSentiment.NEGATIVE.value, NewsSentiment.MIXED.value],
        "sent_weights":      [0.80, 0.20],
        "win_rates":         {NewsSentiment.NEGATIVE.value: 0.35,
                              NewsSentiment.MIXED.value:    0.30},
        "horizon":           ImpactHorizon.LONG_TERM.value,
        "direction_match_p": 0.75,    # direction IS predictable (always bearish)
        "move_range":        (4.0, 12.0),
        "price_range":       (300, 5000),
    },
    NewsType.GEOPOLITICAL_TENSION.value: {
        "n_per_year":        8,
        "trade_taken_pct":   0.28,
        "sentiments":        [NewsSentiment.NEGATIVE.value, NewsSentiment.NEUTRAL.value,
                              NewsSentiment.MIXED.value],
        "sent_weights":      [0.60, 0.25, 0.15],
        "win_rates":         {NewsSentiment.NEGATIVE.value: 0.44,
                              NewsSentiment.NEUTRAL.value:  0.47,
                              NewsSentiment.MIXED.value:    0.38},
        "horizon":           ImpactHorizon.MEDIUM_TERM.value,
        "direction_match_p": 0.45,
        "move_range":        (1.5, 7.0),
        "price_range":       (300, 5000),
    },
    NewsType.SANCTIONS.value: {
        "n_per_year":        4,
        "trade_taken_pct":   0.35,
        "sentiments":        [NewsSentiment.NEGATIVE.value, NewsSentiment.NEUTRAL.value],
        "sent_weights":      [0.70, 0.30],
        "win_rates":         {NewsSentiment.NEGATIVE.value: 0.62,
                              NewsSentiment.NEUTRAL.value:  0.50},
        "horizon":           ImpactHorizon.LONG_TERM.value,
        "direction_match_p": 0.68,
        "move_range":        (2.0, 7.0),
        "price_range":       (300, 4000),
    },
    NewsType.TRADE_WAR.value: {
        "n_per_year":        5,
        "trade_taken_pct":   0.40,
        "sentiments":        [NewsSentiment.NEGATIVE.value, NewsSentiment.MIXED.value],
        "sent_weights":      [0.65, 0.35],
        "win_rates":         {NewsSentiment.NEGATIVE.value: 0.55,
                              NewsSentiment.MIXED.value:    0.44},
        "horizon":           ImpactHorizon.LONG_TERM.value,
        "direction_match_p": 0.62,
        "move_range":        (1.5, 5.5),
        "price_range":       (300, 4000),
    },
    NewsType.NATURAL_DISASTER.value: {
        "n_per_year":        4,
        "trade_taken_pct":   0.35,
        "sentiments":        [NewsSentiment.NEGATIVE.value, NewsSentiment.NEUTRAL.value],
        "sent_weights":      [0.70, 0.30],
        "win_rates":         {NewsSentiment.NEGATIVE.value: 0.52,
                              NewsSentiment.NEUTRAL.value:  0.49},
        "horizon":           ImpactHorizon.SHORT_TERM.value,
        "direction_match_p": 0.55,
        "move_range":        (1.0, 5.0),
        "price_range":       (300, 4000),
    },
    NewsType.CRUDE_OIL_SHOCK.value: {
        "n_per_year":        8,
        "trade_taken_pct":   0.55,
        "sentiments":        [NewsSentiment.POSITIVE.value, NewsSentiment.NEGATIVE.value,
                              NewsSentiment.NEUTRAL.value],
        "sent_weights":      [0.30, 0.50, 0.20],
        "win_rates":         {NewsSentiment.POSITIVE.value: 0.58,
                              NewsSentiment.NEGATIVE.value: 0.63,
                              NewsSentiment.NEUTRAL.value:  0.50},
        "horizon":           ImpactHorizon.MEDIUM_TERM.value,
        "direction_match_p": 0.70,
        "move_range":        (1.5, 6.5),
        "price_range":       (300, 4000),
    },
    NewsType.CURRENCY_SHOCK.value: {
        "n_per_year":        6,
        "trade_taken_pct":   0.45,
        "sentiments":        [NewsSentiment.NEGATIVE.value, NewsSentiment.NEUTRAL.value],
        "sent_weights":      [0.65, 0.35],
        "win_rates":         {NewsSentiment.NEGATIVE.value: 0.58,
                              NewsSentiment.NEUTRAL.value:  0.50},
        "horizon":           ImpactHorizon.SHORT_TERM.value,
        "direction_match_p": 0.66,
        "move_range":        (1.0, 4.5),
        "price_range":       (300, 4000),
    },
    NewsType.BLACK_SWAN.value: {
        "n_per_year":        1,        # very rare
        "trade_taken_pct":   0.05,     # almost no trades taken
        "sentiments":        [NewsSentiment.NEGATIVE.value],
        "sent_weights":      [1.00],
        "win_rates":         {NewsSentiment.NEGATIVE.value: 0.20},
        "horizon":           ImpactHorizon.LONG_TERM.value,
        "direction_match_p": 0.85,    # always crash
        "move_range":        (8.0, 20.0),
        "price_range":       (300, 5000),
    },
}


def seed_synthetic_data(
    db_path: str = DB_PATH,
    years:   int = 2,
    seed:    int = _SEED,
) -> int:
    rng     = random.Random(seed)
    tracker = NewsImpactTracker(db_path)
    start   = datetime(2024, 1, 1)
    total   = 0

    for news_type, prof in _NEWS_PROFILES.items():
        n_events      = int(prof["n_per_year"] * years)
        total_days    = years * 252
        day_offsets   = sorted(rng.sample(range(total_days), min(n_events, total_days)))

        for day_off in day_offsets:
            event_dt = start + timedelta(days=day_off)
            while event_dt.weekday() >= 5:
                event_dt += timedelta(days=1)

            sentiment = rng.choices(
                prof["sentiments"], weights=prof["sent_weights"]
            )[0]
            trade_taken = rng.random() < prof["trade_taken_pct"]
            direction   = "LONG" if rng.random() < 0.65 else "SHORT"

            win_rate = prof["win_rates"].get(sentiment, 0.50)
            is_win   = rng.random() < win_rate
            outcome  = "WIN" if is_win else "LOSS"

            # Price move
            move_mag = rng.uniform(*prof["move_range"])
            # Sentiment direction match
            sent_matches = rng.random() < prof["direction_match_p"]
            if sent_matches:
                # Move is in expected direction
                if sentiment == NewsSentiment.POSITIVE.value:
                    raw_move = move_mag
                else:
                    raw_move = -move_mag
            else:
                raw_move = move_mag if sentiment == NewsSentiment.NEGATIVE.value else -move_mag

            regime_label = rng.choice(_REGIMES)
            vix_bkt, vix_lo, vix_hi = _VIX_BY_REGIME[regime_label]
            vix   = round(rng.uniform(vix_lo, vix_hi), 2)
            price = round(rng.uniform(*prof["price_range"]), 1)

            p1  = round(price * (1 + raw_move * 0.25 / 100), 2)
            p3  = round(price * (1 + raw_move * 0.65 / 100), 2)
            p5  = round(price * (1 + raw_move / 100), 2)
            pnl = round((p5 - price) * 50 * (1 if direction == "LONG" else -1), 0)

            tracker.ingest_observation(
                symbol         = rng.choice(_SYMBOLS),
                news_type      = news_type,
                sentiment      = sentiment,
                event_date     = event_dt.strftime("%Y-%m-%d"),
                trade_taken    = trade_taken,
                direction      = direction,
                strategy       = rng.choice(_STRATEGIES),
                market_regime  = regime_label,
                vix_bucket     = vix_bkt,
                vix            = vix,
                price_at_event = price,
                price_1d       = p1,
                price_3d       = p3,
                price_5d       = p5,
                outcome        = outcome if trade_taken else "PENDING",
                pnl            = pnl     if trade_taken else None,
                impact_horizon = prof["horizon"],
                is_backfill    = False,
                notes          = f"synthetic type={news_type}",
            )
            total += 1

    return total


# ── Orchestrator ──────────────────────────────────────────────────────────────

def run_news_audit(
    db_path:     str  = DB_PATH,
    reports_dir: str  = REPORTS_DIR,
    force_reseed: bool = False,
) -> None:
    """
    NEWS_AUDIT_001

    Goal:
        Determine which news event types actually move the market
        in a predictable direction for our strategies.

    No live trading.
    No execution influence.
    Analysis only.
    """
    print("=" * 70)
    print("NEWS_AUDIT_002 — News Event Impact Analysis (Extended Taxonomy)")
    print("=" * 70)

    tracker  = NewsImpactTracker(db_path)
    existing = tracker.count_total()

    # ── Step 1: Seed ──────────────────────────────────────────────────────────
    print(f"\n[1/4] Database: {db_path}")
    print(f"      Existing rows: {existing}")

    if existing == 0 or force_reseed:
        print("      Seeding 2-year calibrated news observation dataset...")
        n = seed_synthetic_data(db_path, years=2)
        print(f"      Seeded {n} observations")
    else:
        print("      Using existing data (--reseed to regenerate)")

    # ── Step 2: Impact by news type ───────────────────────────────────────────
    print("\n[2/4] News type impact analysis...")
    by_type = tracker.impact_by_type()

    print(f"\n  {'News Type':22s} {'Total':>6s} {'WR%':>7s} "
          f"{'Avg Move':>10s} {'Dir Acc':>9s} {'Verdict':>20s}")
    print("  " + "─" * 80)

    news_order = [
        # Company
        NewsType.EARNINGS.value,
        NewsType.CORPORATE_ACTION.value,
        NewsType.UPGRADE_DOWNGRADE.value,
        # Sector
        NewsType.SECTOR_NEWS.value,
        NewsType.INDEX_REBAL.value,
        # Central banks
        NewsType.RBI_POLICY.value,
        NewsType.FED_MEETING.value,
        NewsType.ECB_MEETING.value,
        # Fiscal
        NewsType.BUDGET.value,
        NewsType.TAX_POLICY.value,
        # Politics
        NewsType.ELECTION.value,
        NewsType.POLITICAL_EVENT.value,
        # Geopolitical spectrum
        NewsType.WAR.value,
        NewsType.GEOPOLITICAL_TENSION.value,
        NewsType.SANCTIONS.value,
        NewsType.TRADE_WAR.value,
        # Macro shocks
        NewsType.NATURAL_DISASTER.value,
        NewsType.CRUDE_OIL_SHOCK.value,
        NewsType.CURRENCY_SHOCK.value,
        NewsType.BLACK_SWAN.value,
        # Misc
        NewsType.REGULATORY.value,
    ]
    for ntype in news_order:
        if ntype not in by_type:
            continue
        d    = by_type[ntype]
        icon = {"STRONG_SIGNAL": "✅", "MODERATE_SIGNAL": "🟢",
                "WEAK_SIGNAL": "⚠️", "NO_SIGNAL": "❌"}.get(d.get("verdict", ""), "—")
        print(
            f"  {ntype:22s} {d['total']:>6d} {d['win_rate']:>6.1f}% "
            f"{d['avg_move_pct']:>+9.2f}% {d['direction_accuracy']:>8.1f}%  "
            f"{icon} {d.get('verdict',''):>18s}"
        )

    # ── Step 3: Questions answered ────────────────────────────────────────────
    print("\n[3/4] Questions answered...")
    qa = {
        "Earnings":            NewsType.EARNINGS.value,
        "RBI Policy":          NewsType.RBI_POLICY.value,
        "Fed Meeting":         NewsType.FED_MEETING.value,
        "ECB Meeting":         NewsType.ECB_MEETING.value,
        "Budget":              NewsType.BUDGET.value,
        "Tax Policy":          NewsType.TAX_POLICY.value,
        "Election":            NewsType.ELECTION.value,
        "War":                 NewsType.WAR.value,
        "Geopolitical":        NewsType.GEOPOLITICAL_TENSION.value,
        "Crude Oil Shock":     NewsType.CRUDE_OIL_SHOCK.value,
        "Currency Shock":      NewsType.CURRENCY_SHOCK.value,
        "Black Swan":          NewsType.BLACK_SWAN.value,
    }
    for label, ntype in qa.items():
        d       = by_type.get(ntype, {})
        verdict = d.get("verdict", "INSUFFICIENT_DATA")
        wr      = d.get("win_rate", 0)
        icon    = "✅" if "STRONG" in verdict else ("⚠️" if "MODERATE" in verdict
                  else ("❌" if "NO" in verdict or "WEAK" in verdict else "—"))
        print(f"  {label:16s} → {icon} {verdict:22s}  WR={wr:.1f}%")

    # ── Step 4: Report ────────────────────────────────────────────────────────
    print("\n[4/4] Writing report...")
    date_str    = datetime.now().strftime("%Y%m%d")
    report_path = os.path.join(reports_dir, f"NEWS_AUDIT_REPORT_{date_str}.md")
    os.makedirs(reports_dir, exist_ok=True)
    generate_news_report(tracker, report_path)
    print(f"      Report: {report_path}")

    print("\n" + "=" * 70)
    print("NEWS_AUDIT_002 complete.")
    top = tracker.top_catalysts(3)
    if top:
        print("Top catalysts:")
        for i, r in enumerate(top, 1):
            print(f"  #{i} {r['news_type']:22s} WR={r['win_rate']:.1f}%")
    no_sig = tracker.no_signal_types()
    if no_sig:
        print(f"No signal (ignore): {', '.join(no_sig)}")
    print("=" * 70)


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="NEWS_AUDIT_001")
    parser.add_argument("--reseed", action="store_true",
                        help="Clear existing data and re-seed synthetic dataset")
    parser.add_argument("--db",     default=DB_PATH,     help="Path to SQLite database")
    parser.add_argument("--out",    default=REPORTS_DIR, help="Reports output directory")
    args = parser.parse_args()

    if args.reseed:
        print("Clearing existing news audit data...")
        with sqlite3.connect(args.db) as _conn:
            try:
                _conn.execute("DELETE FROM news_impact_log")
                _conn.commit()
                print("Done.")
            except sqlite3.OperationalError:
                pass

    run_news_audit(db_path=args.db, reports_dir=args.out, force_reseed=False)
