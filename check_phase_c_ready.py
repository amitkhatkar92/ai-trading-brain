"""
check_phase_c_ready.py

Phase C Readiness Check — answers C-Ready-1 through C-Ready-5.

Run this against a live database after the system has been operational
for a meaningful period. NOT a pass/fail gate — a diagnostic tool.

Usage:
    python check_phase_c_ready.py
    python check_phase_c_ready.py --db data/market_behavior.db

Output:
    READY / NOT READY per criterion, with diagnostic counts and notes.

Criteria:
    C-Ready-1  signal_births >= 100 records
    C-Ready-2  sector_conviction_daily >= 30 FULL rows per sector
    C-Ready-3  theme_phase_history >= 5 transitions
    C-Ready-4  archetype firing frequencies within expected bounds
    C-Ready-5  opportunity lifecycle diversity (not all in one state)

Recommended reading order when results arrive:
    1. C-Ready-5 (Lifecycle Diversity)
       Fastest indicator of system health.
       DISCOVERED=92% means activation is rare; investigate before touching ELE.

    2. Invalidation Reason Breakdown (printed inside C-Ready-5 section)
       Free calibration dashboard without adaptive learning:
         NEVER_MATURED dominant  -> activation threshold too strict
         TTL_EXHAUSTED dominant  -> TTL assumptions too short for current regime
         EC_THRESHOLD dominant   -> expected move assumptions too optimistic

    3. C-Ready-4 (Archetype Firing Rates)
       Earliest detector of scanner drift.
       One archetype at 55/day and another at 0/day is a threshold problem,
       not a market condition.

    4. C-Ready-2 (Sector Conviction)
       Validates the data foundation Layer 1.5 is writing to. PARTIAL rows
       that never become FULL indicate an upstream data pipeline issue.

Phase C discipline:
    Phase C implements RE Calculator + Maturity Engine + State Machine ONLY.
    Nothing learned. Nothing adaptive. Nothing probabilistic.
    Velocity Attribution, Transition Probabilities, and Adaptive Intelligence
    are Phase D gates per MAS Section 7.
    If Phase C stays deterministic, any strange behaviour traces directly to:
        Inputs -> RE computation -> State transitions
    rather than hidden adaptation. That makes debugging tractable.
"""

import argparse
import sqlite3
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

READY_SIGNAL_BIRTHS    = 100   # minimum for C-Ready-1
READY_CONVICTION_ROWS  = 30    # FULL rows per sector for C-Ready-2
READY_THEME_TRANSITIONS = 5    # transition records for C-Ready-3

# Symbol concentration warning threshold for C-Ready-4
# If the top symbol accounts for more than this fraction of all signals, flag it.
SYMBOL_CONCENTRATION_WARN = 0.15   # >15% from one symbol = worth investigating

# Minimum number of distinct lifecycle states for C-Ready-5
MIN_LIFECYCLE_STATES = 2   # must have seen at least 2 distinct states
# Additionally, no single state may hold more than this fraction of all opportunities
LIFECYCLE_MAX_CONCENTRATION = 0.90  # >90% in one state = degenerate population
ARCHETYPE_BOUNDS = {
    "DNA_1A_MOMENTUM_CONT":     (1, 20),
    "DNA_1A_52W_HIGH_EXPAND":   (1, 15),
    "DNA_1A_SECTOR_BKT":        (1, 20),
    "DNA_1A_RESULTS_FOLLOWTHR": (0, 10),   # event-driven; can be 0 in quiet periods
    "DNA_1B_QUIET_ACCUMULATION":(2, 15),
    "DNA_1B_DELIVERY_EXPANSION":(1, 12),
    "DNA_1B_LOW_NOISE_STRENGTH":(1, 15),
    "DNA_1B_SECTOR_PRE_BKT":    (1, 20),
}


def _banner(title):
    print(f"\n{'─'*60}")
    print(f"  {title}")
    print(f"{'─'*60}")


def _ready(label, ok, detail=""):
    icon = "✓ READY    " if ok else "✗ NOT READY"
    print(f"  {icon}  {label}")
    if detail:
        print(f"             {detail}")
    return ok


def check_phase_c_ready(db_path: str) -> bool:
    if not Path(db_path).exists():
        print(f"\n[ERROR] Database not found: {db_path}")
        print("  The system has not been initialised or run yet.")
        print("  Start the live trading system and allow it to collect data first.")
        sys.exit(1)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    results = []

    # -----------------------------------------------------------------------
    # C-Ready-1: signal_births volume
    # -----------------------------------------------------------------------
    _banner("C-Ready-1: Signal Birth Volume")

    row = conn.execute("SELECT COUNT(*) AS n FROM signal_births").fetchone()
    total_births = row["n"] if row else 0

    by_type = conn.execute("""
        SELECT signal_type, COUNT(*) AS n
        FROM signal_births GROUP BY signal_type ORDER BY signal_type
    """).fetchall()

    by_arch = conn.execute("""
        SELECT archetype_id, COUNT(*) AS n
        FROM signal_births GROUP BY archetype_id ORDER BY n DESC
    """).fetchall()

    print(f"  Total signal_births: {total_births}")
    print(f"  By type:  {dict((r['signal_type'], r['n']) for r in by_type)}")
    print(f"  By archetype:")
    for r in by_arch:
        print(f"    {r['archetype_id']:<38} {r['n']}")

    ok1 = _ready("signal_births ≥ 100",
                 total_births >= READY_SIGNAL_BIRTHS,
                 f"actual={total_births}, need={READY_SIGNAL_BIRTHS}")
    results.append(ok1)

    # -----------------------------------------------------------------------
    # C-Ready-2: sector_conviction_daily coverage
    # -----------------------------------------------------------------------
    _banner("C-Ready-2: Sector Conviction History (30 FULL rows per sector)")

    by_sector = conn.execute("""
        SELECT sector,
               COUNT(*) AS total_rows,
               SUM(CASE WHEN data_quality = 'FULL' THEN 1 ELSE 0 END) AS full_rows,
               SUM(CASE WHEN data_quality = 'PARTIAL' THEN 1 ELSE 0 END) AS partial_rows,
               MIN(record_date) AS earliest,
               MAX(record_date) AS latest
        FROM sector_conviction_daily
        GROUP BY sector
        ORDER BY sector
    """).fetchall()

    sectors_below_threshold = []
    if not by_sector:
        print("  sector_conviction_daily is empty — system has not run yet.")
        sectors_below_threshold = ["ALL_SECTORS"]
    else:
        for r in by_sector:
            badge = "✓" if r["full_rows"] >= READY_CONVICTION_ROWS else "✗"
            print(f"  {badge} {r['sector']:<22}  "
                  f"FULL={r['full_rows']:>3}  PARTIAL={r['partial_rows']:>3}  "
                  f"range={r['earliest']}→{r['latest']}")
            if r["full_rows"] < READY_CONVICTION_ROWS:
                sectors_below_threshold.append(r["sector"])

    # Check for sectors in universe not yet in conviction table
    universe_sectors = {
        r[0] for r in conn.execute(
            "SELECT DISTINCT sector FROM universe_stocks WHERE is_active = 1"
        ).fetchall()
    }
    conviction_sectors = {r["sector"] for r in by_sector}
    missing_sectors = universe_sectors - conviction_sectors
    if missing_sectors:
        print(f"\n  Missing sectors (no conviction rows at all): {sorted(missing_sectors)}")
        sectors_below_threshold.extend(missing_sectors)

    ok2 = _ready(
        f"all sectors have ≥ {READY_CONVICTION_ROWS} FULL rows",
        len(sectors_below_threshold) == 0,
        f"below threshold: {sectors_below_threshold}" if sectors_below_threshold else "",
    )
    results.append(ok2)

    # -----------------------------------------------------------------------
    # C-Ready-3: theme_phase_history population
    # -----------------------------------------------------------------------
    _banner("C-Ready-3: Theme Phase History")

    tph_total = conn.execute(
        "SELECT COUNT(*) AS n FROM theme_phase_history"
    ).fetchone()["n"]

    tph_by_sector = conn.execute("""
        SELECT sector, COUNT(*) AS transitions,
               GROUP_CONCAT(DISTINCT phase) AS phases_seen
        FROM theme_phase_history
        GROUP BY sector ORDER BY transitions DESC
    """).fetchall()

    tph_open = conn.execute("""
        SELECT COUNT(*) AS n FROM theme_phase_history WHERE exited_at IS NULL
    """).fetchone()["n"]

    print(f"  Total phase records: {tph_total} ({tph_open} currently open)")
    if tph_by_sector:
        print("  Transitions by sector:")
        for r in tph_by_sector:
            print(f"    {r['sector']:<22}  {r['transitions']} transitions  "
                  f"phases seen: {r['phases_seen']}")
    else:
        print("  theme_phase_history is empty — Theme Phase Engine has not activated.")
        print(f"  (Activates automatically after each sector reaches {READY_CONVICTION_ROWS}"
              " FULL days of conviction data)")

    ok3 = _ready(
        f"theme_phase_history ≥ {READY_THEME_TRANSITIONS} transitions",
        tph_total >= READY_THEME_TRANSITIONS,
        f"actual={tph_total}, need={READY_THEME_TRANSITIONS}",
    )
    results.append(ok3)

    # -----------------------------------------------------------------------
    # C-Ready-4: Signal sanity check
    # -----------------------------------------------------------------------
    _banner("C-Ready-4: Signal Frequency Sanity Check")

    # Get min and max date range of signal_births
    date_range = conn.execute("""
        SELECT MIN(detected_at) AS min_dt,
               MAX(detected_at) AS max_dt,
               COUNT(DISTINCT detected_at) AS trading_days
        FROM signal_births
    """).fetchone()

    trading_days = date_range["trading_days"] or 0
    print(f"  Signal date range: {date_range['min_dt']} → {date_range['max_dt']}")
    print(f"  Trading days with at least one signal: {trading_days}")

    if trading_days > 0:
        print(f"\n  Archetype daily firing rates (over {trading_days} observed days):")

        out_of_bounds = []
        for arch, (low, high) in ARCHETYPE_BOUNDS.items():
            row_a = conn.execute("""
                SELECT COUNT(*) AS n FROM signal_births WHERE archetype_id = ?
            """, (arch,)).fetchone()
            count = row_a["n"] if row_a else 0
            daily_rate = count / trading_days if trading_days > 0 else 0.0
            badge = "✓" if low <= daily_rate <= high else "!"
            expected = f"[{low}–{high}/day]"
            print(f"    {badge} {arch:<38}  avg={daily_rate:5.1f}/day  expected={expected}")
            if not (low <= daily_rate <= high) and count > 0:
                out_of_bounds.append(f"{arch}={daily_rate:.1f}")

        ok4 = _ready(
            "all archetypes firing within expected frequency bounds",
            len(out_of_bounds) == 0,
            f"out-of-bounds: {out_of_bounds}" if out_of_bounds else "",
        )
        # Zero fires for never-seen archetypes: note but don't fail
        never_fired = [
            arch for arch in ARCHETYPE_BOUNDS
            if conn.execute(
                "SELECT COUNT(*) FROM signal_births WHERE archetype_id = ?", (arch,)
            ).fetchone()[0] == 0
        ]
        if never_fired:
            print(f"\n  NOTE: archetypes with zero signals (may need more history): {never_fired}")

        # Symbol concentration warning (not a READY/NOT READY gate — informational)
        top_symbols = conn.execute("""
            SELECT symbol, COUNT(*) AS n
            FROM signal_births
            GROUP BY symbol
            ORDER BY n DESC
            LIMIT 10
        """).fetchall()
        if top_symbols and total_births > 0:
            top_sym      = top_symbols[0]["symbol"]
            top_sym_count = top_symbols[0]["n"]
            top_fraction  = top_sym_count / total_births
            print(f"\n  Top 10 symbols by signal count:")
            for r in top_symbols:
                bar = "█" * min(30, r["n"] * 30 // max(top_sym_count, 1))
                pct = r["n"] / total_births * 100
                print(f"    {r['symbol']:<18}  {r['n']:>4}  ({pct:4.1f}%)  {bar}")
            if top_fraction > SYMBOL_CONCENTRATION_WARN:
                print(f"\n  WARNING: {top_sym} accounts for {top_fraction*100:.1f}% of all signals.")
                print("           Possible causes: symbol-specific threshold bias, sector")
                print("           mapping issue, or unusual price-series behaviour.")
                print("           Investigate before Phase C processes this population.")
    else:
        ok4 = _ready("signal frequency check", False,
                     "no signal_births data — system has not run yet")

    results.append(ok4)

    # -----------------------------------------------------------------------
    # C-Ready-5: Opportunity lifecycle diversity
    # -----------------------------------------------------------------------
    _banner("C-Ready-5: Opportunity Lifecycle Diversity")

    state_rows = conn.execute("""
        SELECT current_state, COUNT(*) AS n
        FROM opportunities
        GROUP BY current_state
        ORDER BY n DESC
    """).fetchall()

    total_opps    = sum(r["n"] for r in state_rows)
    distinct_states = len(state_rows)

    if total_opps == 0:
        print("  opportunities table is empty — no lifecycle data yet.")
        ok5 = _ready("opportunity lifecycle diversity", False,
                     "no opportunities created yet")
    else:
        print(f"  Total opportunities: {total_opps}")
        print(f"  State distribution:")
        dominant_state = None
        dominant_fraction = 0.0
        for r in state_rows:
            pct = r["n"] / total_opps * 100
            bar = "█" * int(pct / 2)
            print(f"    {r['current_state']:<12}  {r['n']:>5}  ({pct:5.1f}%)  {bar}")
            if pct / 100 > dominant_fraction:
                dominant_fraction = pct / 100
                dominant_state    = r["current_state"]

        # Also show final states (INVALID breakdown by reason)
        invalid_reasons = conn.execute("""
            SELECT invalidation_reason, COUNT(*) AS n
            FROM opportunities
            WHERE current_state = 'INVALID'
              AND invalidation_reason IS NOT NULL
            GROUP BY invalidation_reason
            ORDER BY n DESC
        """).fetchall()
        if invalid_reasons:
            print(f"\n  INVALID breakdown by reason:")
            for r in invalid_reasons:
                print(f"    {r['invalidation_reason']:<30}  {r['n']}")

        diversity_ok = (
            distinct_states >= MIN_LIFECYCLE_STATES
            and dominant_fraction <= LIFECYCLE_MAX_CONCENTRATION
        )
        detail = ""
        if distinct_states < MIN_LIFECYCLE_STATES:
            detail = f"only {distinct_states} state(s) seen — lifecycle not cycling"
        elif dominant_fraction > LIFECYCLE_MAX_CONCENTRATION:
            detail = (f"{dominant_state} holds {dominant_fraction*100:.1f}% of opportunities "
                      f"— lifecycle is degenerate (ELE has nothing meaningful to manage)")

        ok5 = _ready(
            "opportunities spread across ≥ 2 states, no state > 90%",
            diversity_ok,
            detail,
        )

    results.append(ok5)

    # -----------------------------------------------------------------------
    # Data quality spot check
    # -----------------------------------------------------------------------
    _banner("Bonus: Data Quality Spot Check")

    # Sector dominance (are any sectors permanently winning conviction?)
    dominance = conn.execute("""
        SELECT sector,
               AVG(sector_conviction_score) AS avg_conviction,
               COUNT(*) AS rows
        FROM sector_conviction_daily
        WHERE data_quality = 'FULL'
          AND sector_conviction_score IS NOT NULL
        GROUP BY sector
        ORDER BY avg_conviction DESC
    """).fetchall()

    if dominance:
        print("  Average conviction score by sector (descending):")
        for r in dominance:
            bar = "█" * int((r["avg_conviction"] or 0) * 20)
            print(f"    {r['sector']:<22}  {(r['avg_conviction'] or 0):.3f}  {bar}")
        top    = dominance[0]["sector"]
        bottom = dominance[-1]["sector"]
        spread = (dominance[0]["avg_conviction"] or 0) - (dominance[-1]["avg_conviction"] or 0)
        if spread > 0.5:
            print(f"\n  NOTE: Large spread ({spread:.3f}) between {top} and {bottom}.")
            print("        If this persists, check sector participation normalisation.")
    else:
        print("  No conviction data yet.")

    # -----------------------------------------------------------------------
    # Summary
    # -----------------------------------------------------------------------
    _banner("PHASE C READINESS SUMMARY")

    labels = [
        "C-Ready-1: signal_births ≥ 100",
        "C-Ready-2: sector_conviction 30 FULL/sector",
        "C-Ready-3: theme_phase_history ≥ 5 transitions",
        "C-Ready-4: archetype firing frequencies plausible",
        "C-Ready-5: opportunity lifecycle diversity",
    ]
    all_ready = all(results)
    for label, ok in zip(labels, results):
        icon = "✓ READY" if ok else "✗ NOT READY"
        print(f"  {icon}  {label}")

    print()
    if all_ready:
        print("  → PHASE C MAY BEGIN")
    else:
        not_ready = sum(1 for r in results if not r)
        print(f"  → PHASE C BLOCKED — {not_ready} prerequisite(s) not yet met.")
        print("  → Run the live system and collect data. Re-check periodically.")

    conn.close()
    return all_ready


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Phase C Readiness Check")
    parser.add_argument(
        "--db",
        default="data/market_behavior.db",
        help="Path to SQLite database (default: data/market_behavior.db)",
    )
    args = parser.parse_args()
    ready = check_phase_c_ready(args.db)
    sys.exit(0 if ready else 1)
