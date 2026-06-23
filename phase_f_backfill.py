"""
PHASE_F_FEATURE_EXTRACTION_REMEDIATION — backfill + differential computation.

Runs inside the container. Steps:
  1. Backfill extract_features_batch() for all dates with leaders but no features.
  2. Run build_controls_for_date() for all dates with leaders.
  3. Run compute_differentials() for all dates with both features + controls.
  4. Print verification counts.
"""
import sys, logging
sys.path.insert(0, "/app")
logging.basicConfig(level=logging.WARNING)

from oios.db.connection import get_connection
from oios.phase_f import feature_extractor
from oios.phase_f import control_population
from oios.phase_f import differential_engine

print("=" * 60)
print("Phase F Feature Extraction Remediation")
print("=" * 60)

with get_connection() as conn:

    # ── Step 1: Find all trade_dates that have leaders ────────────────────
    leader_dates = [r[0] for r in conn.execute(
        "SELECT DISTINCT trade_date FROM market_leaders_daily ORDER BY trade_date"
    ).fetchall()]
    print(f"[1] Leader dates found: {leader_dates}")

    if not leader_dates:
        print("No leader dates — nothing to process.")
        sys.exit(0)

    # ── Step 2: Feature extraction for each date ──────────────────────────
    print("[2] Extracting features for all leader dates...")
    for td in leader_dates:
        leaders = [
            dict(r) for r in conn.execute(
                "SELECT leader_id, symbol, trade_date, sector "
                "FROM market_leaders_daily WHERE trade_date=?",
                (td,),
            ).fetchall()
        ]
        existing_feat = conn.execute(
            "SELECT COUNT(DISTINCT leader_id) FROM market_leader_features "
            "WHERE leader_id IN ("
            "  SELECT leader_id FROM market_leaders_daily WHERE trade_date=?"
            ")",
            (td,),
        ).fetchone()[0]
        print(f"    {td}: {len(leaders)} leaders, {existing_feat} already have features → extracting...")
        feature_extractor.extract_features_batch(leaders, conn)
        new_feat = conn.execute(
            "SELECT COUNT(DISTINCT leader_id) FROM market_leader_features "
            "WHERE leader_id IN ("
            "  SELECT leader_id FROM market_leaders_daily WHERE trade_date=?"
            ")",
            (td,),
        ).fetchone()[0]
        feat_rows = conn.execute(
            "SELECT COUNT(*) FROM market_leader_features "
            "WHERE leader_id IN ("
            "  SELECT leader_id FROM market_leaders_daily WHERE trade_date=?"
            ")",
            (td,),
        ).fetchone()[0]
        print(f"    {td}: leaders_with_features={new_feat} total_feature_rows={feat_rows}")

    # ── Step 3: Build control population for each date ─────────────────────
    print("[3] Building control populations...")
    for td in leader_dates:
        n_ctrl_before = conn.execute(
            "SELECT COUNT(*) FROM market_research_controls WHERE trade_date=?", (td,)
        ).fetchone()[0]
        if n_ctrl_before > 0:
            print(f"    {td}: {n_ctrl_before} controls already exist — skipping (idempotent guard)")
            continue
        n_ctrl = control_population.build_controls_for_date(td, conn)
        print(f"    {td}: built {n_ctrl} control rows")

    # ── Step 4: Compute differentials ──────────────────────────────────────
    print("[4] Computing differentials...")
    for td in leader_dates:
        n_diff_before = conn.execute(
            "SELECT COUNT(*) FROM feature_differentials WHERE trade_date=?", (td,)
        ).fetchone()[0]
        if n_diff_before > 0:
            print(f"    {td}: {n_diff_before} differentials already exist — skipping")
            continue
        n_diff = differential_engine.compute_differentials(td, conn)
        print(f"    {td}: computed {n_diff} differential rows")

    # ── Step 5: Final verification ─────────────────────────────────────────
    print()
    print("[5] Verification queries:")
    print()

    q1 = conn.execute("SELECT COUNT(*) FROM market_leaders_daily").fetchone()[0]
    q2 = conn.execute("SELECT COUNT(*) FROM market_leader_features").fetchone()[0]
    q3 = conn.execute("SELECT COUNT(*) FROM feature_differentials").fetchone()[0]
    q4 = conn.execute("SELECT COUNT(*) FROM market_research_controls").fetchone()[0]
    q5 = conn.execute("SELECT COUNT(*) FROM market_leader_outcomes").fetchone()[0]

    print(f"  market_leaders_daily     = {q1}")
    print(f"  market_leader_features   = {q2}")
    print(f"  market_research_controls = {q4}")
    print(f"  feature_differentials    = {q3}")
    print(f"  market_leader_outcomes   = {q5}")
    print()
    print("  By date:")
    by_date = conn.execute("""
        SELECT mld.trade_date,
               COUNT(DISTINCT mld.leader_id) AS leaders,
               COUNT(DISTINCT mlf.leader_id) AS with_features,
               COUNT(DISTINCT mrc.control_id) AS controls,
               COUNT(DISTINCT fd.diff_id) AS diffs
        FROM market_leaders_daily mld
        LEFT JOIN market_leader_features mlf ON mld.leader_id = mlf.leader_id
        LEFT JOIN market_research_controls mrc ON mld.trade_date = mrc.trade_date
        LEFT JOIN feature_differentials fd ON mld.trade_date = fd.trade_date
        GROUP BY mld.trade_date
        ORDER BY mld.trade_date DESC
        LIMIT 10
    """).fetchall()
    for row in by_date:
        print(f"  {row[0]}  leaders={row[1]}  features={row[2]}  controls={row[3]}  diffs={row[4]}")
    print()

    # Verdict
    features_ok = q2 > 0
    if features_ok:
        if q3 > 0:
            verdict = "FIXED_AND_VERIFIED"
        else:
            verdict = "FEATURES_OK_DIFFS_BLOCKED_NO_CONTROLS"
            if q4 > 0:
                verdict = "FEATURES_OK_CONTROLS_OK_DIFFS_MISSING"
    else:
        verdict = "EXTRACTION_FAILED"
    print(f"VERDICT: {verdict}")
    print("=" * 60)
