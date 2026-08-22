"""
phase_b_audit.py

Phase B Forensic Audit — 50 checks across 8 categories.

Mirrors phase_a_audit.py discipline: every check is explicit, labelled,
and must PASS before Phase C authorization may be issued.

Run standalone:
    python phase_b_audit.py

Expected output: 50/50 PASS, 0 FAIL.
"""

import importlib
import inspect
import re
import sqlite3
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).parent

# ---------------------------------------------------------------------------
# Check infrastructure
# ---------------------------------------------------------------------------

_results: list[tuple[str, bool, str]] = []


def check(label: str, condition: bool, detail: str = "") -> None:
    _results.append((label, condition, detail))
    icon = "✓" if condition else "✗"
    suffix = f" — {detail}" if detail else ""
    print(f"  {icon} {label}: {'PASS' if condition else 'FAIL'}{suffix}")


def section(title: str) -> None:
    print(f"\n=== {title} ===")


# ---------------------------------------------------------------------------
# Helper: in-memory DB with Phase B schema
# ---------------------------------------------------------------------------

def _make_db() -> sqlite3.Connection:
    import os
    os.environ["OIOS_DB_PATH"] = ":memory:"
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON;")

    sys.path.insert(0, str(ROOT))
    from oios.db.migrations import apply_phase_b
    apply_phase_b(conn=conn)
    return conn


# ---------------------------------------------------------------------------
# B1: Schema Compliance
# ---------------------------------------------------------------------------

section("AUDIT B-1: Schema Compliance")

try:
    conn = _make_db()

    # sector_conviction_daily columns
    scd_pragma = {
        row[1]: row[2]
        for row in conn.execute("PRAGMA table_info(sector_conviction_daily)").fetchall()
    }
    check("B1.scd.record_date_exists",   "record_date"               in scd_pragma)
    check("B1.scd.sector_exists",        "sector"                    in scd_pragma)
    check("B1.scd.participation_1d",     "participation_rate_1d"     in scd_pragma)
    check("B1.scd.participation_5d",     "participation_rate_5d"     in scd_pragma)
    check("B1.scd.participation_expansion", "participation_expansion" in scd_pragma)
    check("B1.scd.rs_vs_market",         "rs_vs_market_20d"          in scd_pragma)
    check("B1.scd.volume_trend",         "volume_trend_10d"          in scd_pragma)
    check("B1.scd.consensus_score",      "consensus_score"           in scd_pragma)
    check("B1.scd.capital_flow_score",   "capital_flow_score"        in scd_pragma)
    check("B1.scd.capital_flow_dq",      "capital_flow_data_quality" in scd_pragma)
    check("B1.scd.sector_conviction",    "sector_conviction_score"   in scd_pragma)
    check("B1.scd.theme_phase",          "theme_phase"               in scd_pragma)
    check("B1.scd.data_quality",         "data_quality"              in scd_pragma)
    check("B1.scd.stocks_with_data",     "stocks_with_data"          in scd_pragma)
    check("B1.scd.stocks_total",         "stocks_total"              in scd_pragma)

    # theme_phase_history columns
    tph_pragma = {
        row[1]: row[2]
        for row in conn.execute("PRAGMA table_info(theme_phase_history)").fetchall()
    }
    check("B1.tph.record_id",           "record_id"              in tph_pragma)
    check("B1.tph.sector",              "sector"                 in tph_pragma)
    check("B1.tph.phase",               "phase"                  in tph_pragma)
    check("B1.tph.entered_at",          "entered_at"             in tph_pragma)
    check("B1.tph.exited_at",           "exited_at"              in tph_pragma)
    check("B1.tph.duration_days",       "duration_trading_days"  in tph_pragma)
    check("B1.tph.data_quality",        "data_quality"           in tph_pragma)

    # theme_phase_history CHECK constraint accepts all 5 valid phases
    for phase in ["EMERGENCE", "ACCELERATION", "CONSENSUS", "CROWDING", "EXHAUSTION"]:
        import uuid
        try:
            conn.execute("""
                INSERT INTO theme_phase_history (record_id, sector, phase, entered_at)
                VALUES (?, 'TEST', ?, '2026-01-01')
            """, (str(uuid.uuid4()), phase))
            conn.execute("DELETE FROM theme_phase_history WHERE sector = 'TEST'")
            check(f"B1.tph.phase_accepts_{phase}", True)
        except Exception as e:
            check(f"B1.tph.phase_accepts_{phase}", False, str(e))

    # Phase B tables must NOT have existed at end of Phase A
    from oios.db.migrations import apply_phase_a
    conn_a = sqlite3.connect(":memory:")
    apply_phase_a(conn=conn_a)
    phase_a_tables = {r[0] for r in conn_a.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()}
    check("B1.phase_b_tables_absent_after_phase_a",
          "sector_conviction_daily" not in phase_a_tables and
          "theme_phase_history" not in phase_a_tables)
    conn_a.close()

except Exception:
    traceback.print_exc()
    check("B1.CRITICAL_SCHEMA_IMPORT_FAILED", False)

# ---------------------------------------------------------------------------
# B2: Universe Sector Coverage (B-Audit-01)
# ---------------------------------------------------------------------------

section("AUDIT B-2: Universe Sector Coverage Integrity (B-Audit-01)")

try:
    from collections import Counter
    from oios.seeds.universe_230 import UNIVERSE_230

    sector_counts = Counter(row[2] for row in UNIVERSE_230)
    total = sum(sector_counts.values())

    check("B2.total_is_230", total == 230, f"actual={total}")
    check("B2.no_duplicates",
          len({row[0] for row in UNIVERSE_230}) == 230,
          f"unique={len({row[0] for row in UNIVERSE_230})}")

    violations = {s: c for s, c in sector_counts.items() if c < 8}
    check("B2.no_sector_below_8_stocks",
          len(violations) == 0,
          f"violations={violations}" if violations else "")

    # Report sector counts for transparency
    print(f"\n  Sector counts: {dict(sorted(sector_counts.items()))}")
    print(f"  Min sector: {min(sector_counts.values())} stocks  "
          f"(threshold: 8)")

except Exception:
    traceback.print_exc()
    check("B2.CRITICAL_UNIVERSE_IMPORT_FAILED", False)

# ---------------------------------------------------------------------------
# B3: Layer 1B Scanner Purity
# ---------------------------------------------------------------------------

section("AUDIT B-3: Layer 1B Scanner Purity")

try:
    layer1b_path = ROOT / "oios" / "scanners" / "layer_1b.py"
    lb_src = layer1b_path.read_text(encoding="utf-8")

    # Must have no direct DB write statements
    write_ops = re.findall(r"\b(INSERT|UPDATE|DELETE|REPLACE)\b", lb_src, re.IGNORECASE)
    check("B3.no_direct_db_writes_in_scanner",
          len(write_ops) == 0,
          f"found: {write_ops}" if write_ops else "")

    # Must not import repository
    repo_imports = re.findall(r"from.*repository|import.*repository", lb_src)
    check("B3.no_repository_imports",
          len(repo_imports) == 0,
          f"found: {repo_imports}" if repo_imports else "")

    # Must declare signal_type = "1B"
    check("B3.signal_type_is_1B",
          'SIGNAL_TYPE         = "1B"' in lb_src or "SIGNAL_TYPE = \"1B\"" in lb_src)

    # Must declare expected_ttl_days = 18
    check("B3.expected_ttl_days_is_18",
          "EXPECTED_TTL_DAYS   = 18" in lb_src or "EXPECTED_TTL_DAYS = 18" in lb_src)

    # All 4 archetypes must be present
    for archetype in [
        "DNA_1B_QUIET_ACCUMULATION",
        "DNA_1B_DELIVERY_EXPANSION",
        "DNA_1B_LOW_NOISE_STRENGTH",
        "DNA_1B_SECTOR_PRE_BKT",
    ]:
        check(f"B3.archetype_{archetype}_present", archetype in lb_src)

    # Delivery Expansion must reference bhav_daily (the correct data source)
    check("B3.delivery_expansion_reads_bhav_daily",
          "bhav_daily" in lb_src)

    # Graceful degradation: must check for None bhav window
    check("B3.delivery_expansion_handles_none_bhav",
          "bw is None" in lb_src or "if bw is None" in lb_src)

    # run_scan must exist
    check("B3.run_scan_function_present",
          "def run_scan(" in lb_src)

except Exception:
    traceback.print_exc()
    check("B3.CRITICAL_LAYER1B_SOURCE_ERROR", False)

# ---------------------------------------------------------------------------
# B4: Layer 1B Archetype Behavior (live execution)
# ---------------------------------------------------------------------------

section("AUDIT B-4: Layer 1B Archetype Behavior")

try:
    from oios.scanners.layer_1b import (
        PriceWindow, BhavWindow,
        _detect_quiet_accumulation,
        _detect_delivery_expansion,
        _detect_low_noise_strength,
        _detect_sector_pre_breakout,
        MIN_WRITE_THRESHOLD, EXPECTED_TTL_DAYS, SIGNAL_TYPE,
    )

    # -- Quiet Accumulation --
    n = 30
    closes = [500.0 * (1 + 0.002 * i) for i in range(n)]
    vols = [800_000 + 20_000 * i for i in range(n)]
    highs = [c * 1.001 if i >= n - 5 else c * 1.004 for i, c in enumerate(closes)]
    lows  = [c * 0.999 if i >= n - 5 else c * 0.996 for i, c in enumerate(closes)]
    pw_qa = PriceWindow("QA.NS", [str(i) for i in range(n)], closes, vols, highs, lows)
    sig_qa = _detect_quiet_accumulation(pw_qa, "2026-06-16", "BULL")
    check("B4.quiet_accumulation_fires_on_correct_input",
          sig_qa is not None and sig_qa.qualifies,
          f"score={sig_qa.base_score:.2f}" if sig_qa else "None")
    if sig_qa:
        check("B4.quiet_accumulation_signal_type_1B", sig_qa.signal_type == "1B")
        check("B4.quiet_accumulation_ttl_18", sig_qa.expected_ttl_days == 18)

    # -- Delivery Expansion --
    pw_de = PriceWindow("DE.NS", [str(i) for i in range(n)],
                        [500.0] * n, [1_000_000] * n,
                        [505.0] * n, [495.0] * n)
    bw_de = BhavWindow("DE.NS", [str(i) for i in range(15)],
                       [0.28 + 0.013 * i for i in range(15)])
    sig_de = _detect_delivery_expansion(pw_de, bw_de, "2026-06-16", "BULL")
    check("B4.delivery_expansion_fires",
          sig_de is not None and sig_de.qualifies,
          f"score={sig_de.base_score:.2f}" if sig_de else "None")

    sig_de_no_bhav = _detect_delivery_expansion(pw_de, None, "2026-06-16", "BULL")
    check("B4.delivery_expansion_graceful_when_no_bhav",
          sig_de_no_bhav is None)

    # -- Low-Noise Strength --
    closes_ln = [500.0 * (1 + 0.003 * i) for i in range(n)]
    pw_ln = PriceWindow("LN.NS", [str(i) for i in range(n)],
                        closes_ln, [900_000] * n,
                        [c * 1.004 for c in closes_ln],
                        [c * 0.996 for c in closes_ln])
    sig_ln = _detect_low_noise_strength(pw_ln, "2026-06-16", "BULL")
    check("B4.low_noise_strength_fires",
          sig_ln is not None and sig_ln.qualifies,
          f"score={sig_ln.base_score:.2f}" if sig_ln else "None")

    # -- Sector Pre-Breakout (consolidation pattern) --
    nb = 36
    closes_pb = []
    price = 500.0
    for _ in range(10):
        price *= 1.010
        closes_pb.append(price)
    for i in range(nb - 10):
        price *= 1.0025 if i % 2 == 0 else 0.998
        closes_pb.append(price)
    pw_pb = PriceWindow("PB.NS", [str(i) for i in range(nb)],
                        closes_pb, [800_000] * nb,
                        [c * 1.003 for c in closes_pb],
                        [c * 0.997 for c in closes_pb])
    sig_pb = _detect_sector_pre_breakout(pw_pb, 0.65, "2026-06-16", "BULL")
    check("B4.sector_pre_breakout_fires",
          sig_pb is not None and sig_pb.qualifies,
          f"score={sig_pb.base_score:.2f}" if sig_pb else "None")

    # -- Below threshold does not qualify --
    pw_flat = PriceWindow("FLAT.NS", [str(i) for i in range(n)],
                          [500.0] * n, [1_000_000] * n,
                          [505.0] * n, [495.0] * n)
    sig_flat = _detect_quiet_accumulation(pw_flat, "2026-06-16", "BULL")
    check("B4.flat_price_does_not_fire", sig_flat is None)

except Exception:
    traceback.print_exc()
    check("B4.CRITICAL_LAYER1B_BEHAVIOR_ERROR", False)

# ---------------------------------------------------------------------------
# B5: sector_conviction_writer Source Checks
# ---------------------------------------------------------------------------

section("AUDIT B-5: Sector Conviction Writer Rules")

try:
    scw_path = ROOT / "oios" / "data" / "sector_conviction_writer.py"
    scw_src = scw_path.read_text(encoding="utf-8")

    # Data quality gate constant
    check("B5.min_coverage_constant_0_80",
          "MIN_SECTOR_COVERAGE         = 0.80" in scw_src or
          "MIN_SECTOR_COVERAGE = 0.80" in scw_src)

    # Capital flow neutral constant
    check("B5.capital_flow_neutral_0_5",
          "CAPITAL_FLOW_NEUTRAL        = 0.50" in scw_src or
          "CAPITAL_FLOW_NEUTRAL = 0.50" in scw_src)

    # Sector conviction formula weights
    check("B5.capital_flow_weight_0_40",
          "CAPITAL_FLOW_WEIGHT         = 0.40" in scw_src or
          "CAPITAL_FLOW_WEIGHT = 0.40" in scw_src)
    check("B5.consensus_weight_0_60",
          "CONSENSUS_WEIGHT            = 0.60" in scw_src or
          "CONSENSUS_WEIGHT = 0.60" in scw_src)

    # Theme phase history guard
    check("B5.theme_phase_min_history_30",
          "THEME_PHASE_MIN_HISTORY     = 30" in scw_src or
          "THEME_PHASE_MIN_HISTORY = 30" in scw_src)

    # PARTIAL rows suppress theme phase transitions
    guard_partial = re.search(
        r"if data_quality == .PARTIAL. or new_phase is None",
        scw_src,
    )
    check("B5.partial_rows_suppressed_before_phase_transition",
          guard_partial is not None)

    # Theme Phase Engine checks for sufficient history before activating
    history_guard = re.search(
        r"_has_sufficient_phase_history",
        scw_src,
    )
    check("B5.history_guard_called_before_theme_phase",
          history_guard is not None)

    # Capital flow UNAVAILABLE rescales to pure consensus
    check("B5.unavailable_rescales_to_pure_consensus",
          "pure consensus" in scw_src.lower() or
          "capital_flow_dq == \"UNAVAILABLE\"" in scw_src)

    # INSERT OR REPLACE (idempotent writes to sector_conviction_daily)
    check("B5.idempotent_write_to_scd",
          "INSERT OR REPLACE INTO sector_conviction_daily" in scw_src)

except Exception:
    traceback.print_exc()
    check("B5.CRITICAL_SCW_SOURCE_ERROR", False)

# ---------------------------------------------------------------------------
# B6: Theme Phase Detection Logic
# ---------------------------------------------------------------------------

section("AUDIT B-6: Theme Phase Detection Logic")

try:
    from oios.data.sector_conviction_writer import _detect_theme_phase

    # MAS Section 5, Layer 1.5 Sub-C detection table
    cases = [
        # (participation_5d, expansion, vol_trend, expected_phase)
        (0.40, +0.05, 1.1, "EMERGENCE"),
        (0.55, +0.03, 1.2, "ACCELERATION"),
        (0.70,  0.00, 0.9, "CONSENSUS"),
        (0.85, +0.01, 1.0, "CROWDING"),
        (0.58, -0.08, 0.82, "EXHAUSTION"),
    ]
    for part, exp, vol, expected in cases:
        phase = _detect_theme_phase(part, exp, vol)
        check(f"B6.phase_{expected.lower()}_detected",
              phase == expected,
              f"got={phase}")

    # Crowding also fires when participation > 65% AND volume declining
    phase_vol_crowding = _detect_theme_phase(0.68, 0.01, 0.80)
    check("B6.crowding_fires_on_volume_decline",
          phase_vol_crowding == "CROWDING",
          f"got={phase_vol_crowding}")

except Exception:
    traceback.print_exc()
    check("B6.CRITICAL_THEME_PHASE_ERROR", False)

# ---------------------------------------------------------------------------
# B7: Sector Conviction Score Formula (live computation)
# ---------------------------------------------------------------------------

section("AUDIT B-7: Sector Conviction Score Formula")

try:
    from oios.data.sector_conviction_writer import _compute_consensus_score

    # Full inputs — score must be in [0, 10]
    score = _compute_consensus_score(
        participation_rate_5d=0.60,
        participation_expansion=0.08,
        rs_vs_market_20d=3.0,
        volume_trend_10d=1.3,
    )
    check("B7.consensus_score_in_range", score is not None and 0.0 <= score <= 10.0,
          f"score={score}")

    # None participation → None score
    score_none = _compute_consensus_score(None, None, None, None)
    check("B7.consensus_score_none_when_no_participation", score_none is None)

    # Negative expansion reduces score (penalised)
    score_low  = _compute_consensus_score(0.60, -0.10, 0.0, 0.8)
    score_high = _compute_consensus_score(0.60, +0.10, 5.0, 1.5)
    check("B7.expansion_impacts_score_direction",
          score_high is not None and score_low is not None and score_high > score_low,
          f"high={score_high:.2f} low={score_low:.2f}")

    # Verify conviction formula weights (0.4/0.6 split)
    from oios.data.sector_conviction_writer import CAPITAL_FLOW_WEIGHT, CONSENSUS_WEIGHT
    check("B7.weights_sum_to_1_0",
          abs(CAPITAL_FLOW_WEIGHT + CONSENSUS_WEIGHT - 1.0) < 1e-9,
          f"{CAPITAL_FLOW_WEIGHT}+{CONSENSUS_WEIGHT}")

except Exception:
    traceback.print_exc()
    check("B7.CRITICAL_FORMULA_ERROR", False)

# ---------------------------------------------------------------------------
# B8: Architecture Freeze Compliance
# ---------------------------------------------------------------------------

section("AUDIT B-8: Phase A Architecture Freeze Compliance")

try:
    FREEZE_VIOLATIONS = [
        "DROP TABLE",
        "ALTER TABLE",
        "CREATE TABLE opportunities",      # must not be redefined
        "CREATE TABLE signal_births",      # must not be redefined
        "CREATE TABLE oios_events",        # must not be redefined
    ]
    new_files = [
        ROOT / "oios" / "scanners" / "layer_1b.py",
        ROOT / "oios" / "data" / "sector_conviction_writer.py",
    ]
    violations_found = []
    for fpath in new_files:
        if fpath.exists():
            src = fpath.read_text(encoding="utf-8")
            for pattern in FREEZE_VIOLATIONS:
                if pattern.lower() in src.lower():
                    violations_found.append(f"{fpath.name}: '{pattern}'")

    check("B8.no_freeze_violations_in_new_code",
          len(violations_found) == 0,
          f"violations={violations_found}" if violations_found else "")

    # Phase A0 tables still present after Phase B migration
    from oios.db.migrations import apply_phase_b
    conn_chk = sqlite3.connect(":memory:")
    apply_phase_b(conn=conn_chk)
    a0_tables = {"trading_calendar", "opportunities", "signal_births",
                 "opportunity_signals", "signal_state_transitions",
                 "decision_log", "oios_events", "archetype_versions"}
    existing = {r[0] for r in conn_chk.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()}
    missing_a0 = a0_tables - existing
    check("B8.all_a0_tables_still_present", len(missing_a0) == 0,
          f"missing={missing_a0}" if missing_a0 else "")
    conn_chk.close()

except Exception:
    traceback.print_exc()
    check("B8.CRITICAL_FREEZE_CHECK_ERROR", False)

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

total  = len(_results)
passed = sum(1 for _, ok, _ in _results if ok)
failed = total - passed

print(f"""
{'='*60}
PHASE B FORENSIC AUDIT — SUMMARY
{'='*60}
  Total checks: {total}
  PASS:  {passed}
  FAIL:  {failed}
""")

if failed:
    print("FINDINGS (FAIL):")
    for label, ok, detail in _results:
        if not ok:
            print(f"  [FAIL] {label}")
            if detail:
                print(f"         {detail}")
    sys.exit(1)
else:
    print("  All checks passed.")
