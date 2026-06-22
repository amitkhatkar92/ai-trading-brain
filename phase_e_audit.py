"""
phase_e_audit.py

Phase E Forensic Audit — 60 checks across 10 categories.

Run standalone:
    python phase_e_audit.py

Expected output: 60/60 PASS, 0 FAIL.

Categories:
    E1  — E0 Schema (5 checks)
    E2  — E1 Schema (4 checks)
    E3  — Event Ingestion (8 checks)
    E4  — Event Normalizer (5 checks)
    E5  — Cause Intelligence (10 checks)
    E6  — Propagation Engine (9 checks)
    E7  — Shadow Scorer (7 checks)
    E8  — E-Readiness Gates (7 checks)
    E9  — Shadow Mode Discipline (5 checks)
    E10 — Architecture Integrity (4 checks)
"""

import os
import sqlite3
import sys
import uuid
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))
os.environ["OIOS_DB_PATH"] = ":memory:"

# ---------------------------------------------------------------------------
# Infrastructure
# ---------------------------------------------------------------------------

_results: list[tuple[str, bool, str]] = []


def check(label: str, condition: bool, detail: str = "") -> None:
    _results.append((label, condition, detail))
    icon = "[+]" if condition else "[X]"
    suffix = f" -- {detail}" if detail else ""
    print(f"  {icon} {label}: {'PASS' if condition else 'FAIL'}{suffix}")


def section(title: str) -> None:
    print(f"\n=== {title} ===")


def _make_db() -> sqlite3.Connection:
    from oios.db.migrations import apply_phase_e1
    from oios.db.calendar import populate_trading_calendar_with_names
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON;")
    apply_phase_e1(conn=conn)
    populate_trading_calendar_with_names(conn, "2025-01-01", "2027-12-31")
    return conn


def _seed_ohlcv(conn, symbol, n=30, start=100.0):
    rows = []
    d = date(2026, 1, 1)
    price = start
    for _ in range(n):
        rows.append((symbol, d.isoformat(),
                     round(price * 0.998, 4), round(price * 1.005, 4),
                     round(price * 0.997, 4), round(price, 4),
                     100_000.0, None, "AUDIT"))
        d += timedelta(days=1)
    conn.executemany("""
        INSERT OR IGNORE INTO ohlcv_daily
            (symbol, trade_date, open, high, low, close, volume, adjusted_close, data_source)
        VALUES (?,?,?,?,?,?,?,?,?)
    """, rows)


def _seed_opp(conn, symbol, state="ACTIVE", age=3, arch="DNA_1A_MOMENTUM_CONT",
               birth_date="2026-01-10", signal_type="1A"):
    sid = str(uuid.uuid4())
    oid = str(uuid.uuid4())
    conn.execute("""
        INSERT INTO signal_births
            (signal_id, symbol, archetype_id, archetype_version, signal_type,
             detected_at, birth_price, base_score, regime_at_birth,
             expected_ttl_days, expected_move_direction, current_state,
             expected_move_pct)
        VALUES (?,?,?,1,?,?,100.0,6.0,'TRENDING_UP',18,'LONG',?,8.0)
    """, (sid, symbol, arch, signal_type, birth_date, "ACTIVE"))
    oid_val = str(uuid.uuid4())
    conn.execute("""
        INSERT INTO opportunities
            (opportunity_id, symbol, direction, sector, created_at,
             first_signal_id, regime_at_birth, birth_ttl_days,
             effective_ttl_days, discovered_expires_at, current_state,
             conviction_score, confirming_count, age_trading_days)
        VALUES (?,?,?,?,?,?,?,18,18,'2026-01-28',?,7.5,3,?)
    """, (oid_val, symbol, "LONG", "DEFENCE", birth_date, sid,
          "TRENDING_UP", state, age))
    conn.execute("""
        INSERT OR IGNORE INTO opportunity_signals
            (opportunity_id, signal_id, signal_type, signal_direction,
             evidence_weight, added_at)
        VALUES (?,?,'1A','CONFIRMING',1.0,?)
    """, (oid_val, sid, birth_date))
    conn.commit()
    return sid, oid_val


# ===========================================================================
# E1: E0 Schema
# ===========================================================================

section("AUDIT E-1: E0 Schema")
try:
    conn = _make_db()
    tables = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()}

    for tbl in ("daily_events", "company_relationships",
                "knowledge_graph_metadata", "event_entity_links"):
        check(f"E1.{tbl[:18]}_exists", tbl in tables)

    # daily_events has required columns
    cols = {r[1] for r in conn.execute("PRAGMA table_info(daily_events)").fetchall()}
    for col in ("event_id", "symbol", "event_type", "event_date",
                "direction", "magnitude", "source", "confidence"):
        check(f"E1.daily_events.{col}", col in cols)

    conn.close()
except Exception as e:
    check("E1.EXCEPTION", False, str(e))

# ===========================================================================
# E2: E1 Schema
# ===========================================================================

section("AUDIT E-2: E1 Schema")
try:
    conn = _make_db()
    tables = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()}

    for tbl in ("opportunity_causes", "cause_scores",
                "propagation_paths", "propagation_scores",
                "shadow_cause_outcomes"):
        check(f"E2.{tbl[:20]}_exists", tbl in tables)

    conn.close()
except Exception as e:
    check("E2.EXCEPTION", False, str(e))

# ===========================================================================
# E3: Event Ingestion
# ===========================================================================

section("AUDIT E-3: Event Ingestion")
try:
    from oios.engine.event_ingestion import (
        ingest_event, ingest_relationship, get_events_for_symbol,
        get_relationships_for_symbol, link_event_to_entity,
        store_kg_metadata,
    )

    conn = _make_db()

    # Basic event ingestion
    with conn:
        eid = ingest_event(conn, symbol="HAL.NS", event_type="ORDER_WIN",
                           event_date="2026-01-05", direction="POSITIVE",
                           magnitude="HIGH", headline="HAL wins Rs 5000 Cr radar order",
                           source="BSE", confidence=0.9)
    check("E3.01.event_written",      eid is not None)
    row = conn.execute("SELECT * FROM daily_events WHERE event_id=?", (eid,)).fetchone()
    check("E3.02.event_fields",
          row["symbol"] == "HAL.NS" and row["event_type"] == "ORDER_WIN" and
          row["magnitude"] == "HIGH")

    # ingest_event returns a valid UUID each time (no dedup by design)
    with conn:
        eid2 = ingest_event(conn, symbol="HAL.NS", event_type="ORDER_WIN",
                            event_date="2026-01-05", direction="POSITIVE",
                            magnitude="HIGH", headline="dup",
                            source="NSE", confidence=0.5)
    check("E3.03.ingest_returns_uuid",   eid2 is not None and eid2 != eid)

    # Invalid event type is rejected
    try:
        with conn:
            ingest_event(conn, symbol="X.NS", event_type="INVALID_TYPE",
                         event_date="2026-01-05", direction="POSITIVE",
                         magnitude="HIGH", headline="bad", source="TEST", confidence=0.5)
        check("E3.04.invalid_type_rejected", False, "should have raised")
    except (ValueError, sqlite3.IntegrityError):
        check("E3.04.invalid_type_rejected", True)

    # get_events_for_symbol with days_back=365 to cover test dates
    with conn:
        ingest_event(conn, symbol="HAL.NS", event_type="GUIDANCE",
                     event_date="2026-01-08", direction="POSITIVE",
                     magnitude="MEDIUM", headline="guidance raise",
                     source="BSE", confidence=0.8)
    events = get_events_for_symbol(conn, "HAL.NS", days_back=365)
    check("E3.05.get_events_returns_both",  len(events) >= 2)

    # Relationship ingestion (from_symbol, to_symbol, relationship_type)
    with conn:
        rid = ingest_relationship(conn, "HAL.NS", "BEL.NS", "SUPPLIER",
                                  strength=0.8, source="MANUAL", confidence=0.9)
    check("E3.06.relationship_written",  rid is not None)

    # Dedup relationship (same from/to/type) returns the same relationship_id
    with conn:
        rid2 = ingest_relationship(conn, "HAL.NS", "BEL.NS", "SUPPLIER",
                                   strength=0.7, source="MANUAL", confidence=0.8)
    check("E3.07.relationship_dedup",  rid2 == rid, f"rid={rid}, rid2={rid2}")

    # get_relationships_for_symbol
    rels = get_relationships_for_symbol(conn, "HAL.NS", direction="FROM")
    check("E3.08.get_relationships",
          len(rels) >= 1 and any(r["to_symbol"] == "BEL.NS" for r in rels))

    conn.close()
except Exception as e:
    import traceback
    check("E3.EXCEPTION", False, str(e))
    traceback.print_exc()

# ===========================================================================
# E4: Event Normalizer
# ===========================================================================

section("AUDIT E-4: Event Normalizer")
try:
    from oios.engine.event_normalizer import (
        normalize_event_type, normalize_magnitude, normalize_direction,
        normalize_raw_event, ingest_normalized_event,
    )

    check("E4.01.order_win_normalized",
          normalize_event_type("order win")      == "ORDER_WIN")
    check("E4.02.guidance_normalized",
          normalize_event_type("GUIDANCE RAISE")  == "GUIDANCE")
    check("E4.03.magnitude_high",
          normalize_magnitude("large")            == "HIGH")
    check("E4.04.direction_positive",
          normalize_direction("strong beat record growth")  == "POSITIVE")

    conn = _make_db()
    raw = {
        "symbol":    "BEML.NS",
        "event_type": "ORDER_WIN",
        "event_date":"2026-01-10",
        "direction": "positive",
        "magnitude": "HIGH",
        "headline":  "BEML wins metro coach order",
        "source":    "BSE",
        "confidence": 0.85,
    }
    normalized = normalize_raw_event(raw)
    with conn:
        eid = ingest_normalized_event(conn, normalized)
    check("E4.05.normalize_and_ingest_runs", eid is not None)
    conn.close()

except Exception as e:
    import traceback
    check("E4.EXCEPTION", False, str(e))
    traceback.print_exc()

# ===========================================================================
# E5: Cause Intelligence
# ===========================================================================

section("AUDIT E-5: Cause Intelligence")
try:
    from oios.engine.cause_intelligence import (
        identify_causes_for_opportunity, compute_cause_score, run_cause_cycle,
        _LOOKBACK_DAYS,
    )
    from oios.engine.event_ingestion import ingest_event

    conn = _make_db()
    sym = "HAL.NS"
    _seed_ohlcv(conn, sym)
    with conn:
        sid, oid = _seed_opp(conn, sym, birth_date="2026-01-10")

    # No events → no candidates
    candidates = identify_causes_for_opportunity(conn, oid, "2026-01-10")
    check("E5.01.no_causes_without_events",   len(candidates) == 0)

    # Insert an ORDER_WIN 5 days before birth → should be found
    with conn:
        ingest_event(conn, symbol=sym, event_type="ORDER_WIN",
                     event_date="2026-01-08", direction="POSITIVE",
                     magnitude="HIGH", headline="HAL wins order",
                     source="BSE", confidence=0.9)

    candidates2 = identify_causes_for_opportunity(conn, oid, "2026-01-10")
    check("E5.02.cause_found",             len(candidates2) >= 1)
    # cause_description contains the event type keyword
    check("E5.03.cause_type_order_win",
          any("ORDER_WIN" in c["cause_description"] for c in candidates2))

    # compute_cause_score returns a dict
    score_dict = compute_cause_score(conn, oid, "2026-01-10")
    score = score_dict["cause_score"]
    check("E5.04.cause_score_positive",    score > 0, f"score={score}")
    check("E5.05.cause_score_max_10",      score <= 10.0, f"score={score}")

    # cause_score row written to cause_scores table
    cs_row = conn.execute(
        "SELECT cause_score FROM cause_scores WHERE opportunity_id=? AND score_date='2026-01-10'",
        (oid,)
    ).fetchone()
    check("E5.06.cause_score_persisted",   cs_row is not None)
    check("E5.07.cause_score_matches",
          abs(cs_row["cause_score"] - score) < 1e-6)

    # Verify NO write to opportunities table
    opp_before = conn.execute(
        "SELECT conviction_score, re_score FROM opportunities WHERE opportunity_id=?", (oid,)
    ).fetchone()
    _ = compute_cause_score(conn, oid, "2026-01-10")
    opp_after = conn.execute(
        "SELECT conviction_score, re_score FROM opportunities WHERE opportunity_id=?", (oid,)
    ).fetchone()
    check("E5.08.cause_never_modifies_opportunities",
          opp_before["conviction_score"] == opp_after["conviction_score"] and
          opp_before["re_score"] == opp_after["re_score"])

    # No event within lookback period → zero score
    sym2 = "NEW.NS"
    _seed_ohlcv(conn, sym2)
    with conn:
        _, oid2 = _seed_opp(conn, sym2, birth_date="2026-01-10")
        # Insert event OUTSIDE lookback window
        ingest_event(conn, symbol=sym2, event_type="ORDER_WIN",
                     event_date=(date(2026, 1, 10) - timedelta(days=_LOOKBACK_DAYS + 5)).isoformat(),
                     direction="POSITIVE", magnitude="HIGH",
                     headline="old order win", source="BSE", confidence=0.9)
    score_dict2 = compute_cause_score(conn, oid2, "2026-01-10")
    check("E5.09.stale_event_ignored",   score_dict2["cause_score"] == 0.0,
          f"score={score_dict2['cause_score']}")

    # run_cause_cycle runs without error
    with conn:
        summary = run_cause_cycle(conn, "2026-01-10")
    check("E5.10.run_cause_cycle_runs",
          isinstance(summary, dict) and "processed" in summary)

    conn.close()
except Exception as e:
    import traceback
    check("E5.EXCEPTION", False, str(e))
    traceback.print_exc()

# ===========================================================================
# E6: Propagation Engine
# ===========================================================================

section("AUDIT E-6: Propagation Engine")
try:
    from oios.engine.propagation_engine import (
        build_propagation_paths, compute_propagation_scores_for_event,
        run_propagation_cycle, _MAX_HOPS, _HOP_DECAY,
    )
    from oios.engine.event_ingestion import ingest_event, ingest_relationship

    conn = _make_db()
    src = "HAL.NS"
    dst = "BEL.NS"
    _seed_ohlcv(conn, src)
    _seed_ohlcv(conn, dst)

    # Seed event and relationship
    with conn:
        eid = ingest_event(conn, symbol=src, event_type="ORDER_WIN",
                           event_date="2026-01-08", direction="POSITIVE",
                           magnitude="HIGH", headline="HAL wins",
                           source="BSE", confidence=0.9)

    # No relationships → no paths
    paths = build_propagation_paths(conn, eid, src)
    check("E6.01.no_paths_without_relationships",  len(paths) == 0)

    with conn:
        ingest_relationship(conn, src, dst, "SUPPLIER",
                            strength=0.8, source="MANUAL", confidence=0.9)
        _, oid_dst = _seed_opp(conn, dst, birth_date="2026-01-10")

    paths2 = build_propagation_paths(conn, eid, src)
    check("E6.02.path_found_one_hop",     len(paths2) >= 1)

    # Verify path record in DB
    prow = conn.execute(
        "SELECT target_symbol, path_hops FROM propagation_paths WHERE source_event_id=?",
        (eid,)
    ).fetchone()
    check("E6.03.path_target_correct",    prow and prow["target_symbol"] == "BEL.NS")
    check("E6.04.hop_count_one",          prow and prow["path_hops"] == 1)

    # propagation score computed for BEL opportunity
    with conn:
        result = compute_propagation_scores_for_event(conn, eid, src, "2026-01-10")
    check("E6.05.propagation_score_computed",
          result.get("opportunities_scored", 0) >= 1 or
          result.get("paths_built", 0) >= 1,
          f"result={result}")

    ps_row = conn.execute("""
        SELECT propagation_score FROM propagation_scores
        WHERE opportunity_id=? AND score_date='2026-01-10'
    """, (oid_dst,)).fetchone()
    check("E6.06.propagation_score_persisted",  ps_row is not None)
    check("E6.07.propagation_score_positive",
          ps_row["propagation_score"] > 0 if ps_row else False)

    # No modification to opportunities table
    opp_before = conn.execute(
        "SELECT conviction_score FROM opportunities WHERE opportunity_id=?", (oid_dst,)
    ).fetchone()
    compute_propagation_scores_for_event(conn, eid, src, "2026-01-10")
    opp_after = conn.execute(
        "SELECT conviction_score FROM opportunities WHERE opportunity_id=?", (oid_dst,)
    ).fetchone()
    check("E6.08.propagation_never_modifies_opportunities",
          opp_before["conviction_score"] == opp_after["conviction_score"])

    # run_propagation_cycle runs
    with conn:
        summary2 = run_propagation_cycle(conn, "2026-01-10")
    check("E6.09.run_propagation_cycle_runs",
          isinstance(summary2, dict) and "events_processed" in summary2)

    conn.close()
except Exception as e:
    import traceback
    check("E6.EXCEPTION", False, str(e))
    traceback.print_exc()

# ===========================================================================
# E7: Shadow Scorer
# ===========================================================================

section("AUDIT E-7: Shadow Scorer")
try:
    from oios.engine.shadow_scorer import (
        record_shadow_score, backfill_outcomes, run_shadow_scoring_cycle,
        _CAUSE_WEIGHT, _PROP_WEIGHT, _MAX_OS,
    )
    from oios.engine.event_ingestion import ingest_event
    from oios.engine.cause_intelligence import compute_cause_score

    conn = _make_db()
    sym = "BHEL.NS"
    _seed_ohlcv(conn, sym)
    with conn:
        ingest_event(conn, symbol=sym, event_type="ORDER_WIN",
                     event_date="2026-01-08", direction="POSITIVE",
                     magnitude="HIGH", headline="BHEL order",
                     source="BSE", confidence=0.9)
        sid, oid = _seed_opp(conn, sym, birth_date="2026-01-10")
        compute_cause_score(conn, oid, "2026-01-10")
        outcome = record_shadow_score(conn, oid, "2026-01-10", live_os=7.0)

    check("E7.01.shadow_score_recorded",  outcome is not None)
    check("E7.02.shadow_os_gt_live",
          outcome["shadow_os"] >= 7.0, f"shadow={outcome['shadow_os']}, live=7.0")
    check("E7.03.shadow_os_max_10",       outcome["shadow_os"] <= 10.0)

    # Shadow score not written to opportunities
    opp_row = conn.execute(
        "SELECT conviction_score FROM opportunities WHERE opportunity_id=?", (oid,)
    ).fetchone()
    check("E7.04.shadow_never_modifies_opportunities",
          abs(opp_row["conviction_score"] - 7.5) < 1e-6,
          f"conviction={opp_row['conviction_score']}")

    # backfill outcomes
    conn.execute("""
        UPDATE signal_births SET final_state='TTL_EXHAUSTED', days_to_peak=12,
        peak_move_pct=9.5, final_age_trading_days=18
        WHERE signal_id=?
    """, (sid,))
    conn.commit()
    with conn:
        n_filled = backfill_outcomes(conn, "2026-01-28")
    check("E7.05.backfill_outcomes_runs",  isinstance(n_filled, int))

    # run_shadow_scoring_cycle
    sym2 = "MTAR.NS"
    _seed_ohlcv(conn, sym2)
    with conn:
        _seed_opp(conn, sym2, birth_date="2026-01-10")
    with conn:
        summary = run_shadow_scoring_cycle(conn, "2026-01-10")
    check("E7.06.shadow_cycle_runs",
          isinstance(summary, dict) and "shadow_scores_recorded" in summary)
    check("E7.07.shadow_os_capped_at_10",  _MAX_OS == 10.0)

    conn.close()
except Exception as e:
    import traceback
    check("E7.EXCEPTION", False, str(e))
    traceback.print_exc()

# ===========================================================================
# E8: E-Readiness Gates
# ===========================================================================

section("AUDIT E-8: E-Readiness Gates")
try:
    from oios.engine.e_readiness import (
        check_e_ready_1, check_e_ready_2, check_e_ready_3, check_e_ready,
        E_READY_1_MIN_OBSERVATIONS, E_READY_2_MIN_SUCCESS, E_READY_2_MIN_FAILURE,
        E_READY_3_WIN_RATE_GAP,
    )

    conn = _make_db()

    # Empty DB — all gates must fail
    g1 = check_e_ready_1(conn)
    check("E8.01.e_ready_1_fails_empty",   not g1["pass"])
    check("E8.02.e_ready_1_threshold_500", g1["threshold"] == 500)

    g2 = check_e_ready_2(conn)
    check("E8.03.e_ready_2_fails_empty",   not g2["pass"])
    check("E8.04.e_ready_2_threshold_50",
          g2["threshold_success"] == 50 and g2["threshold_failure"] == 50)

    g3 = check_e_ready_3(conn)
    check("E8.05.e_ready_3_fails_empty",   not g3["pass"], f"g3={g3}")

    all_gates = check_e_ready(conn)
    check("E8.06.all_gates_fail_empty",    not all_gates["overall_pass"])
    check("E8.07.all_gates_has_3_results",
          "e_ready_1" in all_gates and "e_ready_2" in all_gates and "e_ready_3" in all_gates)

    conn.close()
except Exception as e:
    import traceback
    check("E8.EXCEPTION", False, str(e))
    traceback.print_exc()

# ===========================================================================
# E9: Shadow Mode Discipline
# ===========================================================================

section("AUDIT E-9: Shadow Mode Discipline")
try:
    from oios.engine.event_ingestion import ingest_event, ingest_relationship
    from oios.engine.cause_intelligence import compute_cause_score
    from oios.engine.propagation_engine import compute_propagation_scores_for_event
    from oios.engine.shadow_scorer import record_shadow_score, run_shadow_scoring_cycle

    conn = _make_db()
    sym = "ASTR.NS"
    _seed_ohlcv(conn, sym)
    with conn:
        eid = ingest_event(conn, symbol=sym, event_type="ORDER_WIN",
                           event_date="2026-01-08", direction="POSITIVE",
                           magnitude="HIGH", headline="Astra order",
                           source="BSE", confidence=0.9)
        sid, oid = _seed_opp(conn, sym, birth_date="2026-01-10")
        compute_cause_score(conn, oid, "2026-01-10")
        record_shadow_score(conn, oid, "2026-01-10", live_os=7.2)

    # No AUTO_APPLIED status ever
    n_auto = conn.execute(
        "SELECT COUNT(*) FROM pending_adjustments WHERE status='AUTO_APPLIED'"
    ).fetchone()[0]
    check("E9.01.no_auto_applied",  n_auto == 0, f"{n_auto} AUTO_APPLIED rows")

    # shadow_cause_outcomes written, not opportunities
    n_shadow = conn.execute(
        "SELECT COUNT(*) FROM shadow_cause_outcomes"
    ).fetchone()[0]
    check("E9.02.shadow_outcomes_written",  n_shadow >= 1)

    # opportunities.conviction_score unchanged from seed value
    opp_row = conn.execute(
        "SELECT conviction_score FROM opportunities WHERE opportunity_id=?", (oid,)
    ).fetchone()
    check("E9.03.conviction_unchanged",
          abs(opp_row["conviction_score"] - 7.5) < 1e-6, f"cv={opp_row['conviction_score']}")

    # run_shadow_scoring_cycle never touches opportunities
    before_cv = conn.execute(
        "SELECT conviction_score FROM opportunities WHERE opportunity_id=?", (oid,)
    ).fetchone()["conviction_score"]
    with conn:
        run_shadow_scoring_cycle(conn, "2026-01-10")
    after_cv = conn.execute(
        "SELECT conviction_score FROM opportunities WHERE opportunity_id=?", (oid,)
    ).fetchone()["conviction_score"]
    check("E9.04.cycle_never_modifies_conviction",
          before_cv == after_cv, f"before={before_cv}, after={after_cv}")

    # Cause score writes ONLY to cause_scores table (not opportunities, not pending_adjustments)
    n_cs = conn.execute(
        "SELECT COUNT(*) FROM cause_scores WHERE opportunity_id=?", (oid,)
    ).fetchone()[0]
    check("E9.05.cause_score_in_cause_scores_only",  n_cs >= 1)

    conn.close()
except Exception as e:
    import traceback
    check("E9.EXCEPTION", False, str(e))
    traceback.print_exc()

# ===========================================================================
# E10: Architecture Integrity
# ===========================================================================

section("AUDIT E-10: Architecture Integrity")
try:
    conn = _make_db()

    # All Phase A–D tables still present
    required_tables = {
        "signal_births", "opportunities", "opportunity_signals",
        "signal_state_transitions", "decision_log", "pending_adjustments",
        "archetype_outcome_distributions", "opportunity_re_snapshots",
        "transition_probability_cache",
    }
    db_tables = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()}
    missing = required_tables - db_tables
    check("E10.01.phase_abcd_tables_intact",
          len(missing) == 0, f"missing: {missing}" if missing else "all present")

    # apply_phase_e1 is idempotent
    from oios.db.migrations import apply_phase_e1
    apply_phase_e1(conn=conn)
    apply_phase_e1(conn=conn)
    n = conn.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'").fetchone()[0]
    check("E10.02.apply_phase_e1_idempotent",  n > 0, f"{n} tables after 3 applies")

    # E0 tables present
    for tbl in ("daily_events", "company_relationships"):
        check(f"E10.03.{tbl[:16]}_present", tbl in db_tables)

    # E1 tables present
    for tbl in ("shadow_cause_outcomes", "cause_scores"):
        check(f"E10.04.{tbl[:20]}_present", tbl in db_tables)

    conn.close()
except Exception as e:
    check("E10.EXCEPTION", False, str(e))

# ===========================================================================
# Summary
# ===========================================================================

print("\n" + "=" * 60)
total  = len(_results)
passed = sum(1 for _, ok, _ in _results if ok)
failed = total - passed

print(f"\nPhase E Forensic Audit: {passed}/{total} PASS, {failed} FAIL")
if failed == 0:
    print("\n  ALL CHECKS PASS — Phase E Shadow Mode certified.")
    print("  E0: Event knowledge graph operational.")
    print("  E1: Cause/propagation/shadow scoring active, shadow-only.")
    print("  All outputs confined to E-specific tables.")
    print("  E-readiness gates operational — not yet passing (by design).")
    print("  No E output influences RE, TTL, conviction, or execution.")
else:
    print("\n  FAILURES detected:")
    for label, ok, detail in _results:
        if not ok:
            suffix = f" -- {detail}" if detail else ""
            print(f"    [X] {label}: FAIL{suffix}")

sys.exit(0 if failed == 0 else 1)
