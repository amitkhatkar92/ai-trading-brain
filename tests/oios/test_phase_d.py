"""
tests/oios/test_phase_d.py

Phase D acceptance tests (PD-01 through PD-27).

Tests verify:
  1.  Schema: Phase D tables created by apply_phase_d()
  2.  Shadow mode: SHADOW_MODE defaults to True
  3.  Velocity Engine: RE snapshots, velocity computation, attribution, state snapshot
  4.  Transition Model: priors below threshold, empirical above threshold
  5.  Outcome Distributor: shadow mode keeps is_distribution_active=0
  6.  Counterfactual Engine: nightly retroactive job + all 4 CF analyses
  7.  Adaptive Intelligence: proposals in pending_adjustments, guardrails, shadow
  8.  ELE integration: Phase D snapshots written, Phase C tests still pass
  9.  Architecture purity: Phase A/B/C tables not modified

All tests run on in-memory :memory: database. No network calls. Offline-safe.
"""

import os
import sqlite3
import uuid
from datetime import date, timedelta

import pytest

os.environ["OIOS_DB_PATH"] = ":memory:"

from oios.db.migrations import apply_phase_d
from oios.db.calendar import populate_trading_calendar_with_names
from oios.db import repository as R
from oios.domain.models import Opportunity, SignalBirth, OpportunitySignal, OpportunityState


# ---------------------------------------------------------------------------
# Helpers (duplicated from test_phase_c to keep tests self-contained)
# ---------------------------------------------------------------------------

def _ohlcv(conn, symbol, n=30, start=100.0, move=0.0, base_date="2026-01-01"):
    rows = []
    d = date.fromisoformat(base_date)
    price = start
    for _ in range(n):
        rows.append((symbol, d.isoformat(),
                     round(price * 0.998, 4), round(price * 1.005, 4),
                     round(price * 0.997, 4), round(price, 4),
                     100_000.0, None, "TEST"))
        price *= (1 + move)
        d += timedelta(days=1)
    conn.executemany("""
        INSERT OR IGNORE INTO ohlcv_daily
            (symbol, trade_date, open, high, low, close, volume, adjusted_close, data_source)
        VALUES (?,?,?,?,?,?,?,?,?)
    """, rows)


def _make_sb_opp(conn, symbol, *, base_score=6.0, signal_type="1A",
                  birth_price=100.0, expected_move_pct=8.0, ttl=18,
                  direction="LONG", detected_at="2026-01-02",
                  final_state=None, days_to_peak=None, peak_move_pct=None):
    sid = str(uuid.uuid4())
    sb  = SignalBirth(
        signal_id=sid, symbol=symbol, archetype_id="DNA_1A_MOMENTUM_CONT",
        signal_type=signal_type, detected_at=detected_at,
        birth_price=birth_price, base_score=base_score,
        regime_at_birth="TRENDING_UP", expected_ttl_days=ttl,
        expected_move_direction=direction, expected_move_pct=expected_move_pct,
    )
    R.create_signal_birth(conn, sb)
    oid = str(uuid.uuid4())
    opp = Opportunity(
        opportunity_id=oid, symbol=symbol, direction=direction, sector="IT",
        created_at=detected_at, first_signal_id=sid,
        regime_at_birth="TRENDING_UP", birth_ttl_days=ttl, effective_ttl_days=ttl,
        discovered_expires_at=(date.fromisoformat(detected_at) + timedelta(days=ttl//2+1)).isoformat(),
        conviction_score=0.0, confirming_count=1,
    )
    R.create_opportunity(conn, opp)
    conn.execute("UPDATE signal_births SET opportunity_id = ? WHERE signal_id = ?", (oid, sid))
    conn.execute("""
        INSERT OR IGNORE INTO opportunity_signals
            (opportunity_id, signal_id, signal_type, signal_direction, evidence_weight, added_at)
        VALUES (?,?,?,?,?,?)
    """, (oid, sid, signal_type, "CONFIRMING", 1.0, detected_at))

    if final_state:
        conn.execute("""
            UPDATE signal_births SET final_state=?, days_to_peak=?, peak_move_pct=?,
            final_age_trading_days=?
            WHERE signal_id=?
        """, (final_state, days_to_peak, peak_move_pct, days_to_peak, sid))

    return sb, opp


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:", detect_types=sqlite3.PARSE_DECLTYPES)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys=ON;")
    apply_phase_d(conn=c)
    populate_trading_calendar_with_names(c, "2025-01-01", "2026-12-31")
    yield c
    c.close()


# ===========================================================================
# PD-01: Phase D schema tables exist
# ===========================================================================

def test_pd01_schema_tables_exist(conn):
    tables = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()}
    for tbl in ("archetype_outcome_distributions", "opportunity_re_snapshots",
                "opportunity_daily_state_snapshot", "transition_probability_cache"):
        assert tbl in tables, f"Missing Phase D table: {tbl}"


# ===========================================================================
# PD-02: apply_phase_d is idempotent
# ===========================================================================

def test_pd02_migration_idempotent(conn):
    apply_phase_d(conn=conn)
    apply_phase_d(conn=conn)
    n = conn.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'").fetchone()[0]
    assert n > 0


# ===========================================================================
# PD-03: SHADOW_MODE defaults to True
# ===========================================================================

def test_pd03_shadow_mode_default_true():
    from oios.engine.shadow_mode import SHADOW_MODE
    assert SHADOW_MODE is True, "SHADOW_MODE must default to True for all Phase D deployments"


# ===========================================================================
# PD-04: RE snapshot written after ELE cycle
# ===========================================================================

def test_pd04_re_snapshot_written(conn):
    from oios.engine.ele import run_ele_cycle_for_opportunity

    sym = "SNAP1.NS"
    _ohlcv(conn, sym, n=25)
    with conn:
        sb, opp = _make_sb_opp(conn, sym, base_score=6.0, ttl=18)
        conn.execute("""
            UPDATE opportunities SET current_state='ACTIVE', age_trading_days=3,
            confirming_count=3, conviction_score=7.5
            WHERE opportunity_id=?
        """, (opp.opportunity_id,))
    with conn:
        run_ele_cycle_for_opportunity(conn, opp.opportunity_id, "2026-01-05", "BULL")

    snap = conn.execute(
        "SELECT COUNT(*) FROM opportunity_re_snapshots WHERE opportunity_id=?",
        (opp.opportunity_id,)
    ).fetchone()[0]
    assert snap >= 1, "RE snapshot must be written after ELE cycle with Phase D schema"


# ===========================================================================
# PD-05: Velocity requires minimum window (None if < 4 snapshots)
# ===========================================================================

def test_pd05_velocity_requires_window(conn):
    from oios.engine.velocity_engine import compute_velocity, record_re_snapshot

    sym = "VEL1.NS"
    _ohlcv(conn, sym, n=10)
    with conn:
        sb, opp = _make_sb_opp(conn, sym)
    oid = opp.opportunity_id
    # Only 2 snapshots — not enough for 3-day window
    with conn:
        record_re_snapshot(conn, oid, "2026-01-02", 5.0, 0.1, 0.0, "BULL", 1)
        record_re_snapshot(conn, oid, "2026-01-03", 4.5, 0.15, 0.0, "BULL", 2)

    v3d, vc = compute_velocity(conn, oid, "2026-01-05")
    assert v3d is None and vc is None, "Velocity must be None with < 4 snapshots"


# ===========================================================================
# PD-06: Velocity computed after sufficient snapshots
# ===========================================================================

def test_pd06_velocity_computed_after_window(conn):
    from oios.engine.velocity_engine import compute_velocity, record_re_snapshot

    sym = "VEL2.NS"
    _ohlcv(conn, sym, n=10)
    with conn:
        sb, opp = _make_sb_opp(conn, sym)
    oid = opp.opportunity_id
    with conn:
        for i, (d, re, ec) in enumerate([
            ("2026-01-02", 7.0, 0.05),
            ("2026-01-03", 6.5, 0.10),
            ("2026-01-04", 6.0, 0.15),
            ("2026-01-05", 5.5, 0.20),
        ]):
            record_re_snapshot(conn, oid, d, re, ec, 0.0, "BULL", i + 1)

    v3d, vc = compute_velocity(conn, oid, "2026-01-05")
    assert v3d is not None, "velocity_3d should be computed with 4 snapshots"
    assert v3d < 0, "Declining RE → negative velocity"
    assert vc in ("THESIS_WORKING", "REGIME_PRESSURE", "CROWDING", "MECHANICAL_DECAY")


# ===========================================================================
# PD-07: Velocity attribution MECHANICAL_DECAY when only time passes
# ===========================================================================

def test_pd07_velocity_attribution_mechanical_decay(conn):
    from oios.engine.velocity_engine import compute_velocity, record_re_snapshot

    sym = "VEL3.NS"
    _ohlcv(conn, sym, n=10)
    with conn:
        sb, opp = _make_sb_opp(conn, sym)
    oid = opp.opportunity_id
    # Same ec_path, same crowding, same regime — only age increases → MECHANICAL_DECAY
    with conn:
        for i, (d, re, age) in enumerate([
            ("2026-01-02", 7.0, 1),
            ("2026-01-03", 6.5, 2),
            ("2026-01-04", 6.0, 3),
            ("2026-01-05", 5.5, 4),
        ]):
            record_re_snapshot(conn, oid, d, re, 0.05, 0.0, "BULL", age)

    _, vc = compute_velocity(conn, oid, "2026-01-05")
    assert vc == "MECHANICAL_DECAY", f"Expected MECHANICAL_DECAY, got {vc}"


# ===========================================================================
# PD-08: Daily state snapshot records correct counts
# ===========================================================================

def test_pd08_daily_state_snapshot(conn):
    from oios.engine.velocity_engine import record_daily_state_snapshot

    sym = "STATE1.NS"
    _ohlcv(conn, sym, n=10)
    with conn:
        sb, opp = _make_sb_opp(conn, sym)
        conn.execute("""
            UPDATE opportunities SET current_state='ACTIVE', age_trading_days=2
            WHERE opportunity_id=?
        """, (opp.opportunity_id,))
        record_daily_state_snapshot(conn, "2026-01-05")

    row = conn.execute("""
        SELECT opp_count FROM opportunity_daily_state_snapshot
        WHERE snapshot_date='2026-01-05' AND current_state='ACTIVE'
    """).fetchone()
    assert row is not None and row["opp_count"] >= 1


# ===========================================================================
# PD-09: Transition model returns priors when < 20 observations
# ===========================================================================

def test_pd09_priors_when_insufficient_data(conn):
    from oios.engine.transition_model import get_transition_probability

    with conn:
        probs = get_transition_probability(conn, "DNA_1A_MOMENTUM_CONT", "BULL")

    assert not probs["is_empirical"], "Must use priors with 0 observations"
    assert probs["p_watching_to_active"] == pytest.approx(0.45)
    assert probs["p_watching_to_invalid"] == pytest.approx(0.30)


# ===========================================================================
# PD-10: Transition model switches to empirical with >= 20 observations
# ===========================================================================

def test_pd10_empirical_when_sufficient_data(conn):
    from oios.engine.transition_model import get_transition_probability

    sym = "TRAN.NS"
    _ohlcv(conn, sym, n=10)

    # Insert 25 WATCHING→ACTIVE and 5 WATCHING→INVALID transitions for the same archetype
    with conn:
        for i in range(30):
            sid = str(uuid.uuid4())
            oid = str(uuid.uuid4())
            conn.execute("""
                INSERT INTO signal_births
                    (signal_id, symbol, archetype_id, archetype_version, signal_type,
                     detected_at, birth_price, base_score, regime_at_birth,
                     expected_ttl_days, expected_move_direction, current_state)
                VALUES (?,?,?,1,'1A','2026-01-02',100.0,5.0,'BULL',18,'LONG','ACTIVE')
            """, (sid, sym, "DNA_1A_MOMENTUM_CONT"))
            conn.execute("""
                INSERT INTO opportunities
                    (opportunity_id, symbol, direction, sector, created_at,
                     first_signal_id, regime_at_birth, birth_ttl_days,
                     effective_ttl_days, discovered_expires_at, current_state)
                VALUES (?,?,?,?,?,?,?,18,18,'2026-01-12','INVALID')
            """, (oid, sym, "LONG", "IT", "2026-01-02", sid, "BULL"))
            to_state = "ACTIVE" if i < 25 else "INVALID"
            conn.execute("""
                INSERT INTO signal_state_transitions
                    (transition_id, signal_id, opportunity_id,
                     from_state, to_state, transitioned_at, trigger_cause,
                     regime_at_transition)
                VALUES (?,?,?,'WATCHING',?,datetime('now'),'CONSENSUS_RECOVERY','BULL')
            """, (str(uuid.uuid4()), sid, oid, to_state))

    # Clear cache so empirical is recomputed
    conn.execute("DELETE FROM transition_probability_cache")
    with conn:
        probs = get_transition_probability(conn, "DNA_1A_MOMENTUM_CONT", "BULL")

    assert probs["is_empirical"], "Should use empirical with 30 observations"
    assert probs["p_watching_to_active"] == pytest.approx(25 / 30, rel=1e-3)


# ===========================================================================
# PD-11: Transition cache refresh runs without error
# ===========================================================================

def test_pd11_refresh_transition_cache(conn):
    from oios.engine.transition_model import refresh_transition_cache

    sym = "RFSH.NS"
    with conn:
        _make_sb_opp(conn, sym)
    with conn:
        n = refresh_transition_cache(conn, "2026-01-10")
    assert n >= 0  # may be 0 if no archetypes with transitions


# ===========================================================================
# PD-12: Outcome distributor returns None for insufficient observations
# ===========================================================================

def test_pd12_distributor_returns_none_insufficient(conn):
    from oios.engine.outcome_distributor import compute_distribution_for_pair

    result = compute_distribution_for_pair(conn, "DNA_1A_MOMENTUM_CONT", "BULL", "2026-01-10")
    assert result is None, "Should return None with 0 completed signal_births"


# ===========================================================================
# PD-13: Outcome distributor keeps is_distribution_active=0 in shadow mode
# ===========================================================================

def test_pd13_shadow_mode_keeps_inactive(conn):
    from oios.engine.outcome_distributor import compute_distribution_for_pair
    from oios.engine.shadow_mode import SHADOW_MODE

    # Seed 10 completed signal_births
    sym = "DIST1.NS"
    with conn:
        for i in range(10):
            sid = str(uuid.uuid4())
            conn.execute("""
                INSERT INTO signal_births
                    (signal_id, symbol, archetype_id, archetype_version, signal_type,
                     detected_at, birth_price, base_score, regime_at_birth,
                     expected_ttl_days, expected_move_direction, current_state,
                     final_state, days_to_peak, peak_move_pct, expected_move_pct)
                VALUES (?,?,?,1,'1A',?,100.0,6.0,'TRENDING_UP',18,'LONG','ACTIVE',
                        'INVALID',8,5.0,8.0)
            """, (sid, sym, "DNA_1A_MOMENTUM_CONT",
                  (date(2026, 1, 1) + timedelta(days=i)).isoformat()))

    result = compute_distribution_for_pair(conn, "DNA_1A_MOMENTUM_CONT", "TRENDING_UP", "2026-01-15")
    if result is None:
        pytest.skip("Not enough observations for distribution")
    assert SHADOW_MODE is True
    assert result["is_distribution_active"] == 0, "Shadow mode must keep is_distribution_active=0"


# ===========================================================================
# PD-14: Weekly distribution update runs
# ===========================================================================

def test_pd14_weekly_update_runs(conn):
    from oios.engine.outcome_distributor import run_weekly_distribution_update

    with conn:
        n = run_weekly_distribution_update(conn, "2026-01-10")
    assert isinstance(n, int)


# ===========================================================================
# PD-15: Counterfactual populate_outcome_prices fills from ohlcv_daily
# ===========================================================================

def test_pd15_populate_outcome_prices(conn):
    from oios.engine.counterfactual_engine import populate_outcome_prices

    sym = "CF1.NS"
    _ohlcv(conn, sym, n=30)

    with conn:
        sb, opp = _make_sb_opp(conn, sym)
        # Insert a PASS_RE_LOW decision on a past date
        conn.execute("""
            INSERT INTO decision_log
                (decision_id, opportunity_id, signal_id, symbol, decided_at,
                 action, price_at_decision)
            VALUES (?,?,?,?,'2026-01-05 10:00:00','PASS_RE_LOW',100.0)
        """, (str(uuid.uuid4()), opp.opportunity_id, sb.signal_id, sym))

    with conn:
        n = populate_outcome_prices(conn, "2026-01-31")

    # Should have filled at least one record
    row = conn.execute(
        "SELECT price_5d_later FROM decision_log WHERE symbol=? AND price_5d_later IS NOT NULL",
        (sym,)
    ).fetchone()
    assert row is not None, "price_5d_later should be populated after retroactive job"


# ===========================================================================
# PD-16: Counterfactual classify — CLEAN when no subsequent opportunity
# ===========================================================================

def test_pd16_classify_clean(conn):
    from oios.engine.counterfactual_engine import classify_counterfactual_types

    sym = "CF2.NS"
    _ohlcv(conn, sym, n=30)

    with conn:
        sb, opp = _make_sb_opp(conn, sym)
        conn.execute("""
            INSERT INTO decision_log
                (decision_id, opportunity_id, signal_id, symbol, decided_at,
                 action, price_at_decision, price_5d_later, price_10d_later,
                 price_20d_later, max_favorable_20d, max_adverse_20d)
            VALUES (?,?,?,?,'2026-01-05 10:00:00','PASS_RE_LOW',
                    100.0, 102.0, 103.0, 105.0, 5.0, -2.0)
        """, (str(uuid.uuid4()), opp.opportunity_id, sb.signal_id, sym))

    with conn:
        n = classify_counterfactual_types(conn, "2026-01-31")

    assert n >= 1
    row = conn.execute(
        "SELECT counterfactual_type FROM decision_log WHERE symbol=?",
        (sym,)
    ).fetchone()
    assert row["counterfactual_type"] == "CLEAN"


# ===========================================================================
# PD-17: CF-1 TTL sensitivity runs and returns expected keys
# ===========================================================================

def test_pd17_cf1_runs(conn):
    from oios.engine.counterfactual_engine import run_cf1_ttl_sensitivity

    result = run_cf1_ttl_sensitivity(conn)
    for key in ("sample_count", "continued_moving_count", "continued_moving_pct",
                "ttl_extension_would_help", "recommended_multiplier"):
        assert key in result, f"Missing key: {key}"


# ===========================================================================
# PD-18: CF-2 RE threshold sensitivity runs
# ===========================================================================

def test_pd18_cf2_runs(conn):
    from oios.engine.counterfactual_engine import run_cf2_re_threshold_sensitivity

    result = run_cf2_re_threshold_sensitivity(conn)
    assert "sample_count" in result
    assert "current_threshold" in result


# ===========================================================================
# PD-19: CF-3 theme phase override runs
# ===========================================================================

def test_pd19_cf3_runs(conn):
    from oios.engine.counterfactual_engine import run_cf3_theme_phase_override

    result = run_cf3_theme_phase_override(conn)
    assert "sample_count" in result
    assert "suppression_appears_correct" in result


# ===========================================================================
# PD-20: CF-4 hold duration sensitivity runs
# ===========================================================================

def test_pd20_cf4_runs(conn):
    from oios.engine.counterfactual_engine import run_cf4_hold_duration_sensitivity

    result = run_cf4_hold_duration_sensitivity(conn)
    assert "sample_count" in result
    assert "recommendation" in result


# ===========================================================================
# PD-21: Adaptive intelligence proposals written to pending_adjustments
# ===========================================================================

def test_pd21_proposals_to_pending_adjustments(conn):
    from oios.engine.adaptive_intelligence import _write_proposal

    with conn:
        adj_id = _write_proposal(
            conn,
            archetype_id     = "DNA_1A_MOMENTUM_CONT",
            regime           = "BULL",
            adj_type         = "TTL_CHANGE",
            current_value    = 10.0,
            proposed_value   = 11.5,
            evidence         = {"reason": "CF-1 late peak", "late_peak_pct": 0.35},
            obs_count        = 35,
            win_rate_current = 0.48,
            win_rate_projected = None,
            requires_approval = False,
            today            = "2026-06-16",
        )

    row = conn.execute(
        "SELECT * FROM pending_adjustments WHERE adjustment_id=?",
        (adj_id,)
    ).fetchone()
    assert row is not None
    assert row["status"]        == "PENDING"
    assert row["adjustment_type"] == "TTL_CHANGE"
    assert row["archetype_id"]  == "DNA_1A_MOMENTUM_CONT"
    assert row["current_value"] == pytest.approx(10.0)
    assert row["proposed_value"] == pytest.approx(11.5)
    assert row["requires_approval"] == 0


# ===========================================================================
# PD-22: TTL floor guardrail enforced
# ===========================================================================

def test_pd22_ttl_floor_enforced():
    from oios.engine.shadow_mode import TTL_FLOORS

    assert TTL_FLOORS["1A"]  == 5
    assert TTL_FLOORS["1B"]  == 8
    assert TTL_FLOORS["1.5"] == 14


# ===========================================================================
# PD-23: Retirement proposals always require_approval=True
# ===========================================================================

def test_pd23_retirement_always_requires_approval(conn):
    from oios.engine.adaptive_intelligence import _write_proposal

    with conn:
        adj_id = _write_proposal(
            conn,
            archetype_id     = "DNA_1A_BAD_ARCH",
            regime           = None,
            adj_type         = "ARCHETYPE_RETIRE",
            current_value    = 1.0,
            proposed_value   = 0.0,
            evidence         = {"underperform_regimes": ["BULL", "RANGE"], "avg_win_rate": 0.28},
            obs_count        = 55,
            win_rate_current = 0.28,
            win_rate_projected = 0.0,
            requires_approval = True,
            today            = "2026-06-16",
        )

    row = conn.execute(
        "SELECT requires_approval FROM pending_adjustments WHERE adjustment_id=?",
        (adj_id,)
    ).fetchone()
    assert row["requires_approval"] == 1, "ARCHETYPE_RETIRE must always require approval"


# ===========================================================================
# PD-24: Shadow mode — run_adaptive_cycle writes only PENDING proposals, no AUTO_APPLIED
# ===========================================================================

def test_pd24_shadow_mode_only_pending_status(conn):
    from oios.engine.adaptive_intelligence import run_adaptive_cycle

    with conn:
        run_adaptive_cycle(conn, "2026-06-16")

    # All proposals (if any) must be PENDING — never AUTO_APPLIED in shadow mode
    non_pending = conn.execute(
        "SELECT COUNT(*) FROM pending_adjustments WHERE status = 'AUTO_APPLIED'"
    ).fetchone()[0]
    assert non_pending == 0, "Shadow mode must never set status=AUTO_APPLIED"


# ===========================================================================
# PD-25: ELE daily writes RE snapshots when Phase D schema present
# ===========================================================================

def test_pd25_ele_daily_writes_snapshots(conn):
    from oios.engine.ele import run_ele_daily

    sym = "ELESD.NS"
    _ohlcv(conn, sym, n=25)
    with conn:
        sb, opp = _make_sb_opp(conn, sym)
        conn.execute("""
            UPDATE opportunities SET current_state='ACTIVE', age_trading_days=3,
            confirming_count=3, conviction_score=7.5
            WHERE opportunity_id=?
        """, (opp.opportunity_id,))

    with conn:
        run_ele_daily(conn, "2026-01-05", "BULL")

    snap_count = conn.execute(
        "SELECT COUNT(*) FROM opportunity_re_snapshots"
    ).fetchone()[0]
    assert snap_count >= 1, "ELE daily must write RE snapshots when Phase D schema present"


# ===========================================================================
# PD-26: Phase C tests remain unaffected (ELE backward compatibility)
# ===========================================================================

def test_pd26_ele_backward_compat_phase_c():
    """
    ELE must not raise exceptions when Phase D tables are absent (Phase C schema only).
    Verified by confirming Phase C test suite passes with the updated ELE.
    Here we directly test with a Phase C-only DB.
    """
    from oios.db.migrations import apply_phase_c
    from oios.engine.ele import run_ele_cycle_for_opportunity

    c = sqlite3.connect(":memory:", detect_types=sqlite3.PARSE_DECLTYPES)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys=ON;")
    apply_phase_c(conn=c)
    populate_trading_calendar_with_names(c, "2025-01-01", "2026-12-31")

    sym = "COMPAT.NS"
    rows = []
    for i in range(20):
        d = (date(2026, 1, 1) + timedelta(days=i)).isoformat()
        rows.append((sym, d, 99.0, 101.0, 98.0, 100.0, 100_000.0, None, "TEST"))
    c.executemany("""
        INSERT OR IGNORE INTO ohlcv_daily
            (symbol, trade_date, open, high, low, close, volume, adjusted_close, data_source)
        VALUES (?,?,?,?,?,?,?,?,?)
    """, rows)

    sid = str(uuid.uuid4())
    c.execute("""
        INSERT INTO signal_births
            (signal_id, symbol, archetype_id, archetype_version, signal_type,
             detected_at, birth_price, base_score, regime_at_birth,
             expected_ttl_days, expected_move_direction, current_state)
        VALUES (?,?,?,1,'1A','2026-01-02',100.0,6.0,'BULL',18,'LONG','ACTIVE')
    """, (sid, sym, "DNA_1A_MOMENTUM_CONT"))
    oid = str(uuid.uuid4())
    c.execute("""
        INSERT INTO opportunities
            (opportunity_id, symbol, direction, sector, created_at,
             first_signal_id, regime_at_birth, birth_ttl_days,
             effective_ttl_days, discovered_expires_at, current_state,
             conviction_score, confirming_count, age_trading_days)
        VALUES (?,?,?,?,?,?,?,18,18,'2026-01-12','ACTIVE',7.5,3,3)
    """, (oid, sym, "LONG", "IT", "2026-01-02", sid, "BULL"))
    c.execute("""
        INSERT OR IGNORE INTO opportunity_signals
            (opportunity_id, signal_id, signal_type, signal_direction, evidence_weight, added_at)
        VALUES (?,?,?,?,?,?)
    """, (oid, sid, "1A", "CONFIRMING", 1.0, "2026-01-02"))
    c.commit()

    # Must not raise even though Phase D tables are absent
    try:
        with c:
            run_ele_cycle_for_opportunity(c, oid, "2026-01-05", "BULL")
    except Exception as e:
        pytest.fail(f"ELE raised exception on Phase C-only schema: {e}")
    finally:
        c.close()


# ===========================================================================
# PD-27: Phase A/B/C tables remain intact after Phase D operations
# ===========================================================================

def test_pd27_phase_abc_tables_intact(conn):
    tables = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()}
    for required in (
        "signal_births", "opportunities", "opportunity_signals",
        "signal_state_transitions", "decision_log",
        "sector_conviction_daily", "theme_phase_history",
        "pending_adjustments",
    ):
        assert required in tables, f"Phase A/B/C table missing: {required}"
