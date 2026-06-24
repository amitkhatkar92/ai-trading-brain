"""
OIOS Control Pipeline Backfill — run after deploying the daily wiring fix.

Fills market_research_controls and feature_differentials for any dates that
are in market_leaders_daily but NOT yet in market_research_controls.

Safe to re-run: build_controls_for_date uses INSERT OR IGNORE,
compute_differentials uses INSERT OR REPLACE.
"""
import sys, logging
sys.path.insert(0, "/app")
logging.basicConfig(level=logging.WARNING)

from oios.db.connection import get_connection
from oios.phase_f.control_population import build_controls_for_date
from oios.phase_f.differential_engine import compute_differentials

print("=" * 60)
print("OIOS Control Pipeline Backfill")
print("=" * 60)

with get_connection() as conn:

    # Find the latest OHLCV date (as-of date for outcome lookups)
    as_of = conn.execute("SELECT MAX(trade_date) FROM ohlcv_daily").fetchone()[0]
    print(f"OHLCV max date : {as_of}")

    # Find dates that have leaders but no controls yet
    missing = [r[0] for r in conn.execute("""
        SELECT DISTINCT ld.trade_date
        FROM market_leaders_daily ld
        LEFT JOIN market_research_controls mc ON ld.trade_date = mc.trade_date
        WHERE mc.trade_date IS NULL
        ORDER BY ld.trade_date
    """).fetchall()]

    if not missing:
        print("No missing dates — checking differentials...")
        # Also check for dates with controls but no differentials
        missing = [r[0] for r in conn.execute("""
            SELECT DISTINCT mc.trade_date
            FROM market_research_controls mc
            LEFT JOIN feature_differentials fd ON mc.trade_date = fd.trade_date
            WHERE fd.trade_date IS NULL
            ORDER BY mc.trade_date
        """).fetchall()]
        if not missing:
            print("All dates already have controls and differentials.")
        else:
            print(f"Dates with controls but missing differentials: {missing}")
    else:
        print(f"Dates missing controls: {missing}")

    # Current state before
    ctrl_max  = conn.execute("SELECT MAX(trade_date) FROM market_research_controls").fetchone()[0]
    ctrl_cnt  = conn.execute("SELECT COUNT(*) FROM market_research_controls").fetchone()[0]
    diff_max  = conn.execute("SELECT MAX(trade_date) FROM feature_differentials").fetchone()[0]
    diff_cnt  = conn.execute("SELECT COUNT(*) FROM feature_differentials").fetchone()[0]
    print(f"\nBEFORE:")
    print(f"  market_research_controls: max={ctrl_max}  count={ctrl_cnt}")
    print(f"  feature_differentials:    max={diff_max}  count={diff_cnt}")

    # Run for all dates that need it
    all_dates = sorted(set(missing))
    if not all_dates:
        # Fallback: run for all dates that have leaders (idempotent)
        all_dates = [r[0] for r in conn.execute(
            "SELECT DISTINCT trade_date FROM market_leaders_daily ORDER BY trade_date"
        ).fetchall()]
        print(f"\nRunning idempotent refresh for all {len(all_dates)} leader dates...")
    else:
        print(f"\nRunning for {len(all_dates)} missing date(s): {all_dates}")

    total_ctrl = 0
    total_diff = 0
    for td in all_dates:
        n_ctrl = build_controls_for_date(td, conn)
        n_diff = compute_differentials(td, conn)
        total_ctrl += n_ctrl
        total_diff += n_diff
        print(f"  {td}: controls={n_ctrl}  differentials={n_diff}")

    # State after
    ctrl_max2 = conn.execute("SELECT MAX(trade_date) FROM market_research_controls").fetchone()[0]
    ctrl_cnt2 = conn.execute("SELECT COUNT(*) FROM market_research_controls").fetchone()[0]
    diff_max2 = conn.execute("SELECT MAX(trade_date) FROM feature_differentials").fetchone()[0]
    diff_cnt2 = conn.execute("SELECT COUNT(*) FROM feature_differentials").fetchone()[0]
    print(f"\nAFTER:")
    print(f"  market_research_controls: max={ctrl_max2}  count={ctrl_cnt2}")
    print(f"  feature_differentials:    max={diff_max2}  count={diff_cnt2}")

    # Verification queries
    print(f"\nVERIFICATION:")
    print(f"  SELECT MAX(trade_date) FROM market_research_controls; → {ctrl_max2}")
    print(f"  SELECT MAX(trade_date) FROM feature_differentials;    → {diff_max2}")

    # Verdict
    leaders_max = conn.execute(
        "SELECT MAX(trade_date) FROM market_leaders_daily"
    ).fetchone()[0]
    if ctrl_max2 == leaders_max and diff_max2 == leaders_max:
        verdict = "BUG_FIXED_AND_VERIFIED"
    elif ctrl_max2 and ctrl_max2 >= (ctrl_max or ""):
        verdict = "PARTIAL_FIX"
    else:
        verdict = "BACKFILL_FAILED"

    print(f"\nVERDICT: {verdict}")
    print(f"  market_leaders_daily max    = {leaders_max}")
    print(f"  market_research_controls max = {ctrl_max2}")
    print(f"  feature_differentials max    = {diff_max2}")
    print("=" * 60)
