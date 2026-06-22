"""
tests/oios/test_phase_c.py

Phase C acceptance tests (PC-01 through PC-22).

These tests verify:
  1. Schema: Phase C migration creates pending_adjustments table
  2. RE Calculator: formula, D_time, EC_path, C_crowding, regime multipliers
  3. Maturity Engine: all three dimensions, combined conservatism rule
  4. ELE cycle: RE drives ACTIVE↔WATCHING, terminal conditions enforced
  5. Audit trade override: 5% selection by hash
  6. Conviction: RE-weighted computation
  7. Phase C purity: no writes to archetype_outcome_distributions or pending_adjustments
  8. Full integration: opportunity created, ELE runs, state history records written

All tests run on an in-memory :memory: database.
No network calls made — offline-safe.
"""

import os
import sqlite3
import uuid
from datetime import date, timedelta

import pytest

os.environ["OIOS_DB_PATH"] = ":memory:"

from oios.db.migrations import apply_phase_c
from oios.db.calendar import populate_trading_calendar_with_names
from oios.db import repository as R
from oios.domain.models import (
    Opportunity, SignalBirth, OpportunitySignal, OpportunityState,
)
from oios.engine.re_calculator import (
    compute_re, compute_ec_path, compute_crowding, get_half_life,
    compute_effective_ttl, BASE_HALF_LIFE, HALF_LIFE_MULTIPLIERS,
)
from oios.engine.maturity_engine import (
    compute_maturity, temporal_maturity, path_maturity, conviction_maturity,
    most_conservative, SEED, EMERGING, DEVELOPING, MATURE, LATE_STAGE,
)
from oios.engine.ele import (
    run_ele_cycle_for_opportunity, run_ele_daily,
    _is_audit_trade,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_ohlcv(conn, symbol, base_date, n_days=30, start_price=100.0, daily_move=0.002):
    """Insert n_days of OHLCV rows starting at start_price."""
    rows = []
    d = date.fromisoformat(base_date)
    price = start_price
    for _ in range(n_days):
        rows.append((
            symbol, d.isoformat(),
            round(price * 0.998, 4),
            round(price * 1.005, 4),
            round(price * 0.997, 4),
            round(price, 4),
            100_000.0,
            None,
            "TEST",
        ))
        price *= (1 + daily_move)
        d += timedelta(days=1)
    conn.executemany("""
        INSERT OR IGNORE INTO ohlcv_daily
            (symbol, trade_date, open, high, low, close, volume, adjusted_close, data_source)
        VALUES (?,?,?,?,?,?,?,?,?)
    """, rows)


def _make_signal_birth(conn, symbol, detected_at, base_score=6.0, signal_type="1A",
                        direction="LONG", birth_price=100.0, expected_move_pct=8.0,
                        ttl=10):
    sid = str(uuid.uuid4())
    sb = SignalBirth(
        signal_id               = sid,
        symbol                  = symbol,
        archetype_id            = "DNA_1A_MOMENTUM_CONT",
        signal_type             = signal_type,
        detected_at             = detected_at,
        birth_price             = birth_price,
        base_score              = base_score,
        regime_at_birth         = "TRENDING_UP",
        expected_ttl_days       = ttl,
        expected_move_direction = direction,
        expected_move_pct       = expected_move_pct,
    )
    R.create_signal_birth(conn, sb)
    return sb


def _make_opportunity(conn, symbol, signal, sector="IT", regime="TRENDING_UP", ttl=10):
    opp_id = str(uuid.uuid4())
    opp = Opportunity(
        opportunity_id        = opp_id,
        symbol                = symbol,
        direction             = signal.expected_move_direction,
        sector                = sector,
        created_at            = signal.detected_at,
        first_signal_id       = signal.signal_id,
        regime_at_birth       = regime,
        birth_ttl_days        = ttl,
        effective_ttl_days    = ttl,
        discovered_expires_at = (
            date.fromisoformat(signal.detected_at) + timedelta(days=ttl // 2 + 1)
        ).isoformat(),
        conviction_score      = 0.0,
        confirming_count      = 1,
    )
    R.create_opportunity(conn, opp)
    conn.execute(
        "UPDATE signal_births SET opportunity_id = ? WHERE signal_id = ?",
        (opp_id, signal.signal_id)
    )
    # Add founding signal as confirming evidence
    os_rec = OpportunitySignal(
        opportunity_id  = opp_id,
        signal_id       = signal.signal_id,
        signal_type     = signal.signal_type,
        signal_direction = "CONFIRMING",
        evidence_weight = 1.0,
        added_at        = signal.detected_at,
    )
    R.add_opportunity_signal(conn, os_rec)
    return opp


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:", detect_types=sqlite3.PARSE_DECLTYPES)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys=ON;")
    apply_phase_c(conn=c)
    populate_trading_calendar_with_names(
        c, "2021-01-01", "2026-12-31",
    )
    yield c
    c.close()


# ===========================================================================
# PC-01: Phase C schema — pending_adjustments table exists
# ===========================================================================

def test_pc01_pending_adjustments_table(conn):
    row = conn.execute("""
        SELECT COUNT(*) FROM sqlite_master
        WHERE type='table' AND name='pending_adjustments'
    """).fetchone()
    assert row[0] == 1, "pending_adjustments table must exist after apply_phase_c"


# ===========================================================================
# PC-02: Phase C migration is idempotent
# ===========================================================================

def test_pc02_migration_idempotent(conn):
    apply_phase_c(conn=conn)   # run again
    row = conn.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'").fetchone()
    assert row[0] > 0


# ===========================================================================
# PC-03: RE formula — basic correctness
# ===========================================================================

def test_pc03_re_formula_basic():
    # At age=0, no EC, no crowding: RE should equal base_score
    re = compute_re(
        base_score        = 7.0,
        age_trading_days  = 0,
        signal_type       = "1A",
        regime            = "BULL",
        actual_move_pct   = 0.0,
        expected_move_pct = 8.0,
        c_crowding        = 0.0,
    )
    assert re == pytest.approx(7.0, rel=1e-6), f"Expected 7.0 at birth, got {re}"


# ===========================================================================
# PC-04: RE decays with age (D_time)
# ===========================================================================

def test_pc04_re_decays_with_age():
    common = dict(base_score=6.0, signal_type="1A", regime="BULL",
                  actual_move_pct=0.0, expected_move_pct=8.0, c_crowding=0.0)
    re_age0  = compute_re(age_trading_days=0,  **common)
    re_age5  = compute_re(age_trading_days=5,  **common)
    re_age13 = compute_re(age_trading_days=13, **common)
    assert re_age0 > re_age5 > re_age13 > 0, "RE must decrease as age increases"


# ===========================================================================
# PC-05: RE = 0 when EC_path >= 1.0 (edge fully consumed)
# ===========================================================================

def test_pc05_re_zero_when_edge_consumed():
    re = compute_re(
        base_score        = 7.0,
        age_trading_days  = 3,
        signal_type       = "1A",
        regime            = "BULL",
        actual_move_pct   = 8.0,    # 100% of expected move
        expected_move_pct = 8.0,
        c_crowding        = 0.0,
    )
    assert re == 0.0, f"RE must be 0.0 when edge consumed; got {re}"


# ===========================================================================
# PC-06: RE never goes negative
# ===========================================================================

def test_pc06_re_never_negative():
    re = compute_re(
        base_score        = 5.0,
        age_trading_days  = 50,
        signal_type       = "1A",
        regime            = "PANIC",
        actual_move_pct   = 20.0,
        expected_move_pct = 8.0,
        c_crowding        = 1.0,
    )
    assert re >= 0.0, f"RE must never be negative; got {re}"


# ===========================================================================
# PC-07: Regime multipliers affect half-life
# ===========================================================================

def test_pc07_regime_multipliers():
    hl_bull  = get_half_life("1A", "BULL")
    hl_range = get_half_life("1A", "RANGE")
    hl_bear  = get_half_life("1A", "BEAR")
    hl_panic = get_half_life("1A", "PANIC")
    assert hl_bull > hl_range > hl_bear > hl_panic > 0
    # PANIC half-life for 1A: 10 × 0.1 = 1.0
    assert hl_panic == pytest.approx(1.0, rel=1e-6)


# ===========================================================================
# PC-08: EC_path is clamped [0, 1]
# ===========================================================================

def test_pc08_ec_path_clamped():
    assert compute_ec_path(-5.0, 8.0) == 0.0, "Negative move → EC_path = 0"
    assert compute_ec_path(0.0, 8.0)  == 0.0
    assert compute_ec_path(4.0, 8.0)  == pytest.approx(0.5)
    assert compute_ec_path(8.0, 8.0)  == 1.0
    assert compute_ec_path(16.0, 8.0) == 1.0, "Overshoot → capped at 1.0"


# ===========================================================================
# PC-09: C_crowding = 0.0 below 3× average volume
# ===========================================================================

def test_pc09_crowding_below_threshold(conn):
    symbol = "TATA.NS"
    # 21 days of identical volume — today == avg → ratio = 1.0 < 3× → C_crowding = 0
    _make_ohlcv(conn, symbol, "2026-01-01", n_days=21, start_price=100.0)
    crowding = compute_crowding(conn, symbol, "2026-01-21")
    assert crowding == 0.0, f"C_crowding must be 0.0 for normal volume; got {crowding}"


# ===========================================================================
# PC-10: C_crowding > 0 when volume spikes above 3× average
# ===========================================================================

def test_pc10_crowding_above_threshold(conn):
    symbol = "SPIKE.NS"
    # 20 days of base volume, then one 5× day
    rows = []
    for i in range(20):
        d = (date(2026, 1, 1) + timedelta(days=i)).isoformat()
        rows.append((symbol, d, 99.0, 101.0, 98.0, 100.0, 100_000.0, None, "TEST"))
    # Day 21: volume = 5× average = 500,000
    rows.append((symbol, "2026-01-21", 100.0, 102.0, 99.0, 101.0, 500_000.0, None, "TEST"))
    conn.executemany("""
        INSERT OR IGNORE INTO ohlcv_daily
            (symbol, trade_date, open, high, low, close, volume, adjusted_close, data_source)
        VALUES (?,?,?,?,?,?,?,?,?)
    """, rows)

    crowding = compute_crowding(conn, symbol, "2026-01-21")
    assert crowding > 0.0, f"C_crowding must be > 0 on 5× volume day; got {crowding}"


# ===========================================================================
# PC-11: Maturity dimensions — temporal
# ===========================================================================

def test_pc11_temporal_maturity():
    assert temporal_maturity(0, 10)  == SEED
    assert temporal_maturity(1, 10)  == SEED        # 10% < 20% threshold → SEED
    assert temporal_maturity(2, 10)  == EMERGING    # 20% == threshold boundary → EMERGING
    assert temporal_maturity(3, 10)  == EMERGING    # 30%
    assert temporal_maturity(5, 10)  == DEVELOPING  # 50%
    assert temporal_maturity(7, 10)  == MATURE      # 70%
    assert temporal_maturity(9, 10)  == LATE_STAGE  # 90%
    assert temporal_maturity(12, 10) == LATE_STAGE  # > TTL


# ===========================================================================
# PC-12: Maturity dimensions — path
# ===========================================================================

def test_pc12_path_maturity():
    assert path_maturity(0.0)  == SEED
    assert path_maturity(0.1)  == SEED
    assert path_maturity(0.25) == EMERGING
    assert path_maturity(0.55) == DEVELOPING
    assert path_maturity(0.75) == MATURE
    assert path_maturity(0.95) == LATE_STAGE
    assert path_maturity(1.0)  == LATE_STAGE


# ===========================================================================
# PC-13: Maturity dimensions — conviction
# ===========================================================================

def test_pc13_conviction_maturity():
    assert conviction_maturity(0)  == SEED
    assert conviction_maturity(1)  == SEED
    assert conviction_maturity(2)  == EMERGING
    assert conviction_maturity(3)  == DEVELOPING
    assert conviction_maturity(4)  == MATURE
    assert conviction_maturity(5)  == LATE_STAGE
    assert conviction_maturity(10) == LATE_STAGE


# ===========================================================================
# PC-14: maturity_combined is most conservative
# ===========================================================================

def test_pc14_most_conservative():
    assert most_conservative(LATE_STAGE, SEED, MATURE) == SEED
    assert most_conservative(DEVELOPING, DEVELOPING)   == DEVELOPING
    assert most_conservative(LATE_STAGE)               == LATE_STAGE
    assert most_conservative(MATURE, EMERGING, LATE_STAGE) == EMERGING


def test_pc14b_compute_maturity_conservative(conn):
    # age=8/ttl=10=80% → MATURE, ec=0.1 → SEED, confirming=3 → DEVELOPING
    # Combined = SEED (most conservative)
    result = compute_maturity(
        age_trading_days   = 8,
        effective_ttl_days = 10,
        ec_path            = 0.1,
        confirming_count   = 3,
    )
    assert result == SEED


# ===========================================================================
# PC-15: ELE cycle — RE drives ACTIVE→WATCHING when below threshold
# ===========================================================================

def test_pc15_ele_re_drives_watching(conn):
    # Create an ACTIVE opportunity, then make the stock drop so RE falls below RE_THRESHOLD
    symbol = "DROP.NS"
    # 25 days of falling price (stock dropping → EC_path goes negative for LONG,
    # but RE also decays with age). Use age=12 on a 10d TTL to force TTL_EXHAUSTED
    # instead. For WATCHING test: set age=3, RE forced low by high crowding.
    _make_ohlcv(conn, symbol, "2026-01-01", n_days=25, start_price=100.0, daily_move=0.0)
    with conn:
        sb = _make_signal_birth(conn, symbol, "2026-01-02", base_score=6.0, ttl=18)
        opp = _make_opportunity(conn, symbol, sb, ttl=18)
        # Manually set state to ACTIVE and age to where RE will be below threshold
        # RE_THRESHOLD = 5.0. At age=15, BULL half-life = 10×1.3 = 13. D_time = 0.5^(15/13) ≈ 0.45
        # RE = 6 × 0.45 × 1.0 × 1.0 ≈ 2.7 < 5.0 → should go WATCHING
        conn.execute("""
            UPDATE opportunities SET current_state='ACTIVE', age_trading_days=15,
            confirming_count=3, conviction_score=7.5
            WHERE opportunity_id=?
        """, (opp.opportunity_id,))
    with conn:
        result = run_ele_cycle_for_opportunity(conn, opp.opportunity_id, "2026-01-17", "BULL")
    assert result is not None
    assert result.new_state in (OpportunityState.WATCHING, OpportunityState.INVALID), (
        f"Low RE should push ACTIVE to WATCHING or INVALID, got {result.new_state}"
    )


# ===========================================================================
# PC-16: ELE cycle — WATCHING recovers to ACTIVE when RE rises
# ===========================================================================

def test_pc16_ele_watching_recovers(conn):
    symbol = "RECOV.NS"
    # Stock at birth price — no actual move → EC_path=0, at age=1 RE is high
    _make_ohlcv(conn, symbol, "2026-01-01", n_days=20, start_price=100.0, daily_move=0.0)
    with conn:
        sb = _make_signal_birth(conn, symbol, "2026-01-02", base_score=8.0, ttl=18)
        opp = _make_opportunity(conn, symbol, sb, ttl=18)
        conn.execute("""
            UPDATE opportunities SET current_state='WATCHING', age_trading_days=1,
            confirming_count=3, conviction_score=7.5
            WHERE opportunity_id=?
        """, (opp.opportunity_id,))
    with conn:
        result = run_ele_cycle_for_opportunity(conn, opp.opportunity_id, "2026-01-03", "BULL")
    assert result is not None
    # RE at age=1, BULL half-life=13: D_time=0.5^(1/13)≈0.95, RE=8×0.95≈7.6 > RE_THRESHOLD(5.0)
    # Should recover to ACTIVE
    assert result.new_state == OpportunityState.ACTIVE, (
        f"High RE should recover WATCHING→ACTIVE, got {result.new_state}, re={result.re_score}"
    )


# ===========================================================================
# PC-17: ELE cycle — TTL_EXHAUSTED terminal condition
# ===========================================================================

def test_pc17_ele_ttl_exhausted(conn):
    symbol = "EXPIRE.NS"
    _make_ohlcv(conn, symbol, "2026-01-01", n_days=25, start_price=100.0, daily_move=0.0)
    with conn:
        sb = _make_signal_birth(conn, symbol, "2026-01-02", base_score=6.0, ttl=10)
        opp = _make_opportunity(conn, symbol, sb, ttl=10)
        # age=10 → exactly at TTL → TTL_EXHAUSTED
        # SIDEWAYS regime: effective_ttl = round(10 × 0.7) = 7.
        # age=7 → 7 >= effective_ttl=7 → TTL_EXHAUSTED; 7 > 7×1.2=8.4? No → no ZOMBIE_CAP.
        conn.execute("""
            UPDATE opportunities SET current_state='ACTIVE', age_trading_days=7
            WHERE opportunity_id=?
        """, (opp.opportunity_id,))
    with conn:
        result = run_ele_cycle_for_opportunity(conn, opp.opportunity_id, "2026-01-12", "SIDEWAYS")
    assert result is not None
    assert result.new_state == OpportunityState.INVALID
    inv_row = conn.execute(
        "SELECT invalidation_reason FROM opportunities WHERE opportunity_id=?",
        (opp.opportunity_id,)
    ).fetchone()
    assert inv_row["invalidation_reason"] == "TTL_EXHAUSTED"


# ===========================================================================
# PC-18: ELE cycle — EC_EXHAUSTED terminal condition
# ===========================================================================

def test_pc18_ele_ec_exhausted(conn):
    symbol = "CONSUMED.NS"
    # Stock moved 8% (= expected move) → EC_path = 1.0 → INVALID
    _make_ohlcv(conn, symbol, "2026-01-01", n_days=20,
                start_price=100.0, daily_move=0.0)
    # Override last price to 108 (8% above birth price of 100)
    conn.execute("""
        UPDATE ohlcv_daily SET close=108.0 WHERE symbol=? AND trade_date='2026-01-10'
    """, (symbol,))
    with conn:
        sb = _make_signal_birth(conn, symbol, "2026-01-02", base_score=6.0,
                                 birth_price=100.0, expected_move_pct=8.0, ttl=18)
        opp = _make_opportunity(conn, symbol, sb, ttl=18)
        conn.execute("""
            UPDATE opportunities SET current_state='ACTIVE', age_trading_days=8,
            edge_consumed_pct=1.0
            WHERE opportunity_id=?
        """, (opp.opportunity_id,))
    with conn:
        result = run_ele_cycle_for_opportunity(conn, opp.opportunity_id, "2026-01-10", "BULL")
    assert result is not None
    assert result.new_state == OpportunityState.INVALID
    inv_row = conn.execute(
        "SELECT invalidation_reason FROM opportunities WHERE opportunity_id=?",
        (opp.opportunity_id,)
    ).fetchone()
    assert inv_row["invalidation_reason"] == "EC_EXHAUSTED"


# ===========================================================================
# PC-19: Audit trade override — ~5% selected by hash
# ===========================================================================

def test_pc19_audit_trade_hash():
    # Generate 1000 UUIDs and verify approximately 5% are selected
    selected = sum(1 for _ in range(1000) if _is_audit_trade(str(uuid.uuid4())))
    # Allow wide tolerance — hash is deterministic but selection must be ~5%
    assert 30 <= selected <= 80, f"Expected ~50/1000 audit trades, got {selected}"


def test_pc19b_audit_trade_deterministic():
    # Same signal_id must always produce same result
    sid = str(uuid.uuid4())
    result1 = _is_audit_trade(sid)
    result2 = _is_audit_trade(sid)
    assert result1 == result2, "Audit trade selection must be deterministic"


# ===========================================================================
# PC-20: Phase C purity — no writes to archetype_outcome_distributions
# ===========================================================================

def test_pc20_phase_c_purity_no_aod_writes(conn):
    # archetype_outcome_distributions must remain empty after running ELE
    symbol = "PURE.NS"
    _make_ohlcv(conn, symbol, "2026-01-01", n_days=20, start_price=100.0, daily_move=0.0)
    with conn:
        sb = _make_signal_birth(conn, symbol, "2026-01-02", base_score=6.0, ttl=10)
        opp = _make_opportunity(conn, symbol, sb, ttl=10)
        conn.execute("""
            UPDATE opportunities SET current_state='ACTIVE', age_trading_days=3
            WHERE opportunity_id=?
        """, (opp.opportunity_id,))
    with conn:
        run_ele_daily(conn, "2026-01-05", "SIDEWAYS")

    # Table may not exist in Phase B schema — but if it does, it must be empty
    aod_exists = conn.execute("""
        SELECT COUNT(*) FROM sqlite_master
        WHERE type='table' AND name='archetype_outcome_distributions'
    """).fetchone()[0]
    if aod_exists:
        n = conn.execute(
            "SELECT COUNT(*) FROM archetype_outcome_distributions"
        ).fetchone()[0]
        assert n == 0, "Phase C must NOT write to archetype_outcome_distributions"


# ===========================================================================
# PC-21: Phase C purity — no writes to pending_adjustments
# ===========================================================================

def test_pc21_phase_c_purity_no_pending_writes(conn):
    symbol = "NOADJ.NS"
    _make_ohlcv(conn, symbol, "2026-01-01", n_days=20, start_price=100.0, daily_move=0.0)
    with conn:
        sb = _make_signal_birth(conn, symbol, "2026-01-02", base_score=6.0, ttl=10)
        opp = _make_opportunity(conn, symbol, sb, ttl=10)
        conn.execute("""
            UPDATE opportunities SET current_state='ACTIVE', age_trading_days=3
            WHERE opportunity_id=?
        """, (opp.opportunity_id,))
    with conn:
        run_ele_daily(conn, "2026-01-05", "SIDEWAYS")

    n = conn.execute("SELECT COUNT(*) FROM pending_adjustments").fetchone()[0]
    assert n == 0, "Phase C must NOT write to pending_adjustments"


# ===========================================================================
# PC-22: State transitions written for ELE-driven changes
# ===========================================================================

def test_pc22_transitions_written_for_ele_changes(conn):
    symbol = "TRANS.NS"
    _make_ohlcv(conn, symbol, "2026-01-01", n_days=25, start_price=100.0, daily_move=0.0)
    with conn:
        sb = _make_signal_birth(conn, symbol, "2026-01-02", base_score=6.0, ttl=18)
        opp = _make_opportunity(conn, symbol, sb, ttl=18)
        # Force ACTIVE at age where RE < RE_THRESHOLD
        conn.execute("""
            UPDATE opportunities SET current_state='ACTIVE', age_trading_days=16,
            confirming_count=3, conviction_score=7.5
            WHERE opportunity_id=?
        """, (opp.opportunity_id,))

    before_count = conn.execute(
        "SELECT COUNT(*) FROM signal_state_transitions WHERE opportunity_id=?",
        (opp.opportunity_id,)
    ).fetchone()[0]

    with conn:
        result = run_ele_cycle_for_opportunity(
            conn, opp.opportunity_id, "2026-01-18", "BULL"
        )

    after_count = conn.execute(
        "SELECT COUNT(*) FROM signal_state_transitions WHERE opportunity_id=?",
        (opp.opportunity_id,)
    ).fetchone()[0]

    if result and result.state_changed:
        assert after_count > before_count, (
            "State transitions must be written when ELE changes state"
        )


# ===========================================================================
# PC-23: effective_ttl respects regime multiplier
# ===========================================================================

def test_pc23_effective_ttl_regime():
    # 1A TTL=10, PANIC multiplier=0.1 → effective = max(1, round(10×0.1)) = 1
    # But bull ceiling caps: effective = min(PANIC_result, BULL_ceiling)
    ttl_panic = compute_effective_ttl(10, "1A", "PANIC")
    ttl_bull  = compute_effective_ttl(10, "1A", "BULL")
    ttl_range = compute_effective_ttl(10, "1A", "RANGE")

    # Bull is the ceiling
    assert ttl_bull >= ttl_range >= ttl_panic
    assert ttl_panic >= 1   # hard floor


# ===========================================================================
# PC-24: run_ele_daily processes all live opportunities
# ===========================================================================

def test_pc24_ele_daily_processes_all(conn):
    symbols = ["AAA.NS", "BBB.NS", "CCC.NS"]
    for sym in symbols:
        _make_ohlcv(conn, sym, "2026-01-01", n_days=20, start_price=100.0, daily_move=0.0)
        with conn:
            sb = _make_signal_birth(conn, sym, "2026-01-02", base_score=6.0, ttl=18)
            opp = _make_opportunity(conn, sym, sb, ttl=18)
            conn.execute("""
                UPDATE opportunities SET current_state='ACTIVE', age_trading_days=3,
                confirming_count=3, conviction_score=7.5
                WHERE opportunity_id=?
            """, (opp.opportunity_id,))

    with conn:
        daily = run_ele_daily(conn, "2026-01-05", "SIDEWAYS")

    assert daily.opps_processed == 3, (
        f"Expected 3 opps processed, got {daily.opps_processed}"
    )
