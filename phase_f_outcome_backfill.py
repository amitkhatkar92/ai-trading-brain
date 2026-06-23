"""
PHASE_F_OUTCOME_ATTRIBUTION_REMEDIATION — backfill outcome gaps.

Steps:
  1. Call update_outcomes() with latest OHLCV date to populate
     market_leader_outcomes.return_* and market_research_controls.return_*
  2. Re-run compute_differentials() for all historical dates — uses
     INSERT OR REPLACE with deterministic diff_id so existing NULL gaps
     are overwritten with actual values.
  3. Verify the target SQL from the task:
       SELECT
         SUM(outcome_gap_1d IS NOT NULL),
         SUM(outcome_gap_3d IS NOT NULL),
         SUM(outcome_gap_5d IS NOT NULL),
         SUM(outcome_gap_20d IS NOT NULL)
       FROM feature_differentials;
  4. Test aggregate_top_differentiators() produces non-empty output.
"""
import sys, logging
sys.path.insert(0, "/app")
logging.basicConfig(level=logging.WARNING)

from datetime import date, timedelta
from oios.db.connection import get_connection
from oios.phase_f.outcome_tracker import update_outcomes
from oios.phase_f.differential_engine import (
    compute_differentials,
    aggregate_top_differentiators,
)

print("=" * 60)
print("Phase F Outcome Attribution Remediation")
print("=" * 60)

with get_connection() as conn:

    # ── Step 1: Find latest available OHLCV date ──────────────────────────
    as_of = conn.execute("SELECT MAX(trade_date) FROM ohlcv_daily").fetchone()[0]
    print(f"[1] OHLCV max date: {as_of}")

    if not as_of:
        print("ERROR: ohlcv_daily is empty. Cannot proceed.")
        sys.exit(1)

    # ── Step 2: Update multi-horizon outcome returns ──────────────────────
    print(f"[2] Running update_outcomes(as_of={as_of})...")
    n_updated = update_outcomes(as_of, conn)
    print(f"    Updated {n_updated} outcome rows")

    # Show current state of returns
    ret_summary = conn.execute("""
        SELECT
            COUNT(*) as total,
            SUM(return_1d IS NOT NULL) as has_1d,
            SUM(return_3d IS NOT NULL) as has_3d,
            SUM(return_5d IS NOT NULL) as has_5d,
            SUM(return_10d IS NOT NULL) as has_10d,
            SUM(return_20d IS NOT NULL) as has_20d,
            SUM(outcome_class != 'UNKNOWN') as classified
        FROM market_leader_outcomes
    """).fetchone()
    print(f"    market_leader_outcomes: total={ret_summary[0]}")
    print(f"      return_1d={ret_summary[1]}  return_3d={ret_summary[2]}")
    print(f"      return_5d={ret_summary[3]}  return_10d={ret_summary[4]}")
    print(f"      return_20d={ret_summary[5]}  classified={ret_summary[6]}")

    ctrl_summary = conn.execute("""
        SELECT
            COUNT(*) as total,
            SUM(return_1d IS NOT NULL) as has_1d,
            SUM(return_5d IS NOT NULL) as has_5d,
            SUM(return_20d IS NOT NULL) as has_20d
        FROM market_research_controls
    """).fetchone()
    print(f"    market_research_controls: total={ctrl_summary[0]}")
    print(f"      return_1d={ctrl_summary[1]}  return_5d={ctrl_summary[2]}  return_20d={ctrl_summary[3]}")

    # ── Step 3: Re-run compute_differentials() for all dates ──────────────
    print("[3] Re-running compute_differentials() for all dates (INSERT OR REPLACE)...")
    leader_dates = [r[0] for r in conn.execute(
        "SELECT DISTINCT trade_date FROM market_leaders_daily ORDER BY trade_date"
    ).fetchall()]
    print(f"    Dates: {leader_dates}")

    total_diffs = 0
    for td in leader_dates:
        n = compute_differentials(td, conn)
        total_diffs += n
        print(f"    {td}: {n} differentials written (INSERT OR REPLACE)")

    # ── Step 4: Required verification query ───────────────────────────────
    print()
    print("[4] Required verification SQL:")
    print("    SELECT")
    print("      SUM(outcome_gap_1d IS NOT NULL),")
    print("      SUM(outcome_gap_3d IS NOT NULL),")
    print("      SUM(outcome_gap_5d IS NOT NULL),")
    print("      SUM(outcome_gap_20d IS NOT NULL)")
    print("    FROM feature_differentials;")
    row = conn.execute("""
        SELECT
          SUM(outcome_gap_1d IS NOT NULL),
          SUM(outcome_gap_3d IS NOT NULL),
          SUM(outcome_gap_5d IS NOT NULL),
          SUM(outcome_gap_20d IS NOT NULL)
        FROM feature_differentials
    """).fetchone()
    print(f"    → {row[0]}, {row[1]}, {row[2]}, {row[3]}")
    print()

    # By date breakdown
    print("    By date:")
    by_date = conn.execute("""
        SELECT trade_date,
               COUNT(*) as total,
               SUM(outcome_gap_1d IS NOT NULL) as g1d,
               SUM(outcome_gap_3d IS NOT NULL) as g3d,
               SUM(outcome_gap_5d IS NOT NULL) as g5d,
               SUM(outcome_gap_20d IS NOT NULL) as g20d
        FROM feature_differentials
        GROUP BY trade_date ORDER BY trade_date DESC LIMIT 15
    """).fetchall()
    for r in by_date:
        print(f"    {r[0]}  total={r[1]}  g1d={r[2]}  g3d={r[3]}  g5d={r[4]}  g20d={r[5]}")
    print()

    # ── Step 5: Test aggregate_top_differentiators() ──────────────────────
    print("[5] Testing aggregate_top_differentiators()...")
    top_diffs = aggregate_top_differentiators(as_of, conn, lookback_days=30, min_pairs=3)
    if top_diffs:
        print(f"    Top differentiators ({len(top_diffs)} features):")
        for d in top_diffs[:5]:
            print(f"      {d['feature']:22s}  winner_higher={d['winner_higher_pct']:.0%}"
                  f"  avg_delta={d['avg_delta']:+.3f}  avg_gap={d['avg_outcome_gap']:+.2f}%"
                  f"  pairs={d['pair_count']}")
    else:
        print("    WARNING: aggregate_top_differentiators() returned empty — gaps still NULL?")
    print()

    # ── Verdict ───────────────────────────────────────────────────────────
    g1d_count = row[0] or 0
    g5d_count = row[2] or 0
    total_diffs_db = conn.execute("SELECT COUNT(*) FROM feature_differentials").fetchone()[0]
    if g1d_count > 0 and len(top_diffs) > 0:
        verdict = "BUG_FIXED_AND_VERIFIED"
    elif g1d_count > 0:
        verdict = "GAPS_POPULATED_DIFFERENTIATORS_NEED_MORE_DATA"
    else:
        verdict = "FAILED"
    print(f"VERDICT: {verdict}")
    print(f"  feature_differentials total    = {total_diffs_db}")
    print(f"  outcome_gap_1d non-null        = {g1d_count}")
    print(f"  aggregate_top_differentiators  = {len(top_diffs)} features")
    print("=" * 60)
