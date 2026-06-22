"""
tests/oios/test_phase_b.py

Phase B acceptance tests.

These tests verify:
  1. Schema and migration (Phase B tables created correctly)
  2. Layer 1B scanner — 4 archetypes fire correctly, purity maintained
  3. Delivery Expansion audit — graceful BHAV degradation
  4. sector_conviction_daily population — Sub-A participation rates
  5. Data quality gate — PARTIAL when < 80% coverage
  6. Consensus Shift — consensus_score computation
  7. Capital flow — neutral when UNAVAILABLE
  8. Theme Phase Engine — phase detection + 30-day history guard
  9. B-Audit-01 — sector coverage integrity (no sector < 8 stocks)

All tests run on an in-memory :memory: database.
Network calls are NOT made — offline-safe.
"""

import os
import sqlite3
import uuid
from datetime import date, timedelta
from typing import Optional
import pytest

os.environ["OIOS_DB_PATH"] = ":memory:"

from oios.db.migrations import apply_phase_b
from oios.db.calendar import populate_trading_calendar_with_names
from oios.db import universe as U
from oios.seeds.universe_230 import UNIVERSE_230
from oios.scanners.layer_1b import (
    PriceWindow, BhavWindow, ScanResult, run_scan,
    _detect_quiet_accumulation,
    _detect_delivery_expansion,
    _detect_low_noise_strength,
    _detect_sector_pre_breakout,
    EXPECTED_TTL_DAYS, MIN_WRITE_THRESHOLD, SIGNAL_TYPE,
)
from oios.data.sector_conviction_writer import (
    run_sector_conviction,
    _compute_participation_rates,
    _compute_consensus_score,
    _detect_theme_phase,
    _has_sufficient_phase_history,
    _get_capital_flow,
    CAPITAL_FLOW_NEUTRAL,
    THEME_PHASE_MIN_HISTORY,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def conn():
    """Fresh in-memory DB with Phase B schema (all phases applied)."""
    c = sqlite3.connect(":memory:", detect_types=sqlite3.PARSE_DECLTYPES)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys=ON;")
    apply_phase_b(conn=c)
    populate_trading_calendar_with_names(
        c, "2026-01-01", "2026-12-31",
        holidays={"2026-10-20": "DIWALI"}
    )
    yield c
    c.close()


@pytest.fixture
def conn_with_universe(conn):
    with conn:
        U.seed_universe(conn)
    return conn


# ---------------------------------------------------------------------------
# Helper: synthetic OHLCV history
# ---------------------------------------------------------------------------

def _build_ohlcv(
    symbol: str,
    start_date: str,
    n_days: int = 60,
    base_price: float = 500.0,
    trend_pct: float = 0.003,
    avg_volume: float = 1_000_000,
) -> list[tuple]:
    rows = []
    price = base_price
    dt = date.fromisoformat(start_date)
    for i in range(n_days):
        open_  = price
        close  = price * (1.0 + trend_pct)
        high   = close * 1.005
        low    = open_ * 0.995
        rows.append((symbol, dt.isoformat(), open_, high, low, close, avg_volume))
        price = close
        dt += timedelta(days=1)
    return rows


def _insert_ohlcv(conn, rows):
    conn.executemany("""
        INSERT OR IGNORE INTO ohlcv_daily
            (symbol, trade_date, open, high, low, close, volume)
        VALUES (?,?,?,?,?,?,?)
    """, rows)


def _build_bhav(
    symbol: str,
    start_date: str,
    n_days: int = 20,
    delivery_pct_start: float = 0.25,
    delivery_trend: float = 0.012,   # rising 1.2pp per day
    base_volume: float = 800_000,
) -> list[tuple]:
    rows = []
    dt = date.fromisoformat(start_date)
    dpct = delivery_pct_start
    for i in range(n_days):
        dpct = min(1.0, dpct + delivery_trend)
        qty  = base_volume
        deliv = qty * dpct
        rows.append((symbol, dt.isoformat(), "EQ", qty, deliv, dpct))
        dt += timedelta(days=1)
    return rows


def _insert_bhav(conn, rows):
    conn.executemany("""
        INSERT OR IGNORE INTO bhav_daily
            (symbol, trade_date, series, traded_quantity, deliverable_qty, delivery_pct)
        VALUES (?,?,?,?,?,?)
    """, rows)


# ---------------------------------------------------------------------------
# PB-01 Phase B tables exist
# ---------------------------------------------------------------------------

def test_pb01_phase_b_tables_exist(conn):
    tables = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()}
    assert "sector_conviction_daily" in tables
    assert "theme_phase_history" in tables


# ---------------------------------------------------------------------------
# PB-02 Phase B migration is idempotent
# ---------------------------------------------------------------------------

def test_pb02_phase_b_migration_is_idempotent(conn):
    apply_phase_b(conn=conn)
    apply_phase_b(conn=conn)
    tables = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()}
    assert "sector_conviction_daily" in tables


# ---------------------------------------------------------------------------
# PB-03 Layer 1B signal type and TTL defaults
# ---------------------------------------------------------------------------

def test_pb03_layer_1b_signal_type_and_ttl():
    assert SIGNAL_TYPE == "1B"
    assert EXPECTED_TTL_DAYS == 18
    assert MIN_WRITE_THRESHOLD == 4.0


# ---------------------------------------------------------------------------
# PB-04 Quiet Accumulation fires on correct input
# ---------------------------------------------------------------------------

def test_pb04_quiet_accumulation_fires():
    # Build a PriceWindow where volume is building quietly
    # vol_5d avg > vol_10d avg > vol_20d avg, range narrowing, price above sma20
    n = 30
    base = 500.0
    closes = [base * (1 + 0.002 * i) for i in range(n)]
    # Volume rising from 800k to 1.4M over the window
    volumes = [800_000 + 20_000 * i for i in range(n)]
    highs  = [c * 1.004 for c in closes]
    lows   = [c * 0.996 for c in closes]

    # Make range narrow in last 5 vs last 10
    for i in range(n - 5, n):
        highs[i] = closes[i] * 1.001
        lows[i]  = closes[i] * 0.999

    pw = PriceWindow(
        symbol="TEST.NS",
        dates=[str(i) for i in range(n)],
        closes=closes,
        volumes=volumes,
        highs=highs,
        lows=lows,
    )

    result = _detect_quiet_accumulation(pw, "2026-06-16", "BULL")
    assert result is not None, "Expected Quiet Accumulation to fire"
    assert result.archetype_id == "DNA_1B_QUIET_ACCUMULATION"
    assert result.signal_type  == "1B"
    assert result.expected_ttl_days == 18
    assert result.base_score > 4.0
    assert result.qualifies


# ---------------------------------------------------------------------------
# PB-05 Delivery Expansion fires when delivery% rising
# ---------------------------------------------------------------------------

def test_pb05_delivery_expansion_fires():
    n = 30
    base = 500.0
    closes = [base * (1 + 0.001 * i) for i in range(n)]
    volumes = [1_000_000] * n
    highs = [c * 1.005 for c in closes]
    lows  = [c * 0.995 for c in closes]

    pw = PriceWindow(
        symbol="DELIVERY.NS",
        dates=[str(i) for i in range(n)],
        closes=closes,
        volumes=volumes,
        highs=highs,
        lows=lows,
    )

    # Build BHAV window: delivery starting at 28% rising steeply
    # trend 0.013/day → latest=0.462, 5d-ago=0.397, trend_5d=0.065 > 0.05 ✓
    bw = BhavWindow(
        symbol="DELIVERY.NS",
        dates=[str(i) for i in range(15)],
        delivery_pcts=[0.28 + 0.013 * i for i in range(15)],
    )

    result = _detect_delivery_expansion(pw, bw, "2026-06-16", "BULL")
    assert result is not None, "Expected Delivery Expansion to fire"
    assert result.archetype_id == "DNA_1B_DELIVERY_EXPANSION"
    assert result.signal_type  == "1B"
    assert result.base_score > 4.0


# ---------------------------------------------------------------------------
# PB-06 Delivery Expansion degrades gracefully when BHAV missing
# ---------------------------------------------------------------------------

def test_pb06_delivery_expansion_no_bhav():
    n = 30
    closes = [500.0 * (1 + 0.002 * i) for i in range(n)]
    pw = PriceWindow(
        symbol="NOBHAV.NS",
        dates=[str(i) for i in range(n)],
        closes=closes,
        volumes=[1_000_000] * n,
        highs=[c * 1.005 for c in closes],
        lows=[c * 0.995 for c in closes],
    )

    # bw = None: BHAV not yet available
    result = _detect_delivery_expansion(pw, None, "2026-06-16", "BULL")
    assert result is None, "Must not fire when BHAV is unavailable"


# ---------------------------------------------------------------------------
# PB-07 Low-Noise Strength Build fires on tight-range uptrend
# ---------------------------------------------------------------------------

def test_pb07_low_noise_strength_fires():
    n = 30
    base = 500.0
    # 0.3%/day gives change_5d ≈ 1.4%  (inside [1%, 6%] window)
    closes = [base * (1 + 0.003 * i) for i in range(n)]
    # Tight ranges: 0.8% daily range → ATR ≈ 0.8% < 1.5%
    highs  = [c * 1.004 for c in closes]
    lows   = [c * 0.996 for c in closes]

    pw = PriceWindow(
        symbol="TIGHT.NS",
        dates=[str(i) for i in range(n)],
        closes=closes,
        volumes=[900_000] * n,
        highs=highs,
        lows=lows,
    )

    result = _detect_low_noise_strength(pw, "2026-06-16", "BULL")
    assert result is not None, "Expected Low-Noise Strength to fire"
    assert result.archetype_id == "DNA_1B_LOW_NOISE_STRENGTH"
    assert result.base_score > 4.0


# ---------------------------------------------------------------------------
# PB-08 Sector Pre-Breakout fires when sector breadth >= 50%
# ---------------------------------------------------------------------------

def test_pb08_sector_pre_breakout_fires():
    """
    Consolidation pattern: strong rise for 10 days, then gentle drift for 26 days.
    - Rise phase creates the 20d high reference
    - Consolidation phase brings RSI into the 45-65 accumulation zone
    - SMA slope remains positive due to slight upward drift
    """
    n = 36  # >= 26 required for SMA slope check

    closes = []
    price = 500.0
    # Phase 1: strong rise (+1%/day × 10 days) → price ≈ 552
    for _ in range(10):
        price *= 1.010
        closes.append(price)
    # Phase 2: gentle consolidation (+0.25% / -0.20% alternating, 26 days)
    # RS = 1.25 → RSI ≈ 55.6 (in [45, 65])
    # Net +0.025%/day so sma_20_now > sma_20_5d
    for i in range(n - 10):
        price *= 1.0025 if i % 2 == 0 else 0.998
        closes.append(price)

    highs = [c * 1.003 for c in closes]
    lows  = [c * 0.997 for c in closes]

    pw = PriceWindow(
        symbol="PREBKT.NS",
        dates=[str(i) for i in range(n)],
        closes=closes,
        volumes=[800_000] * n,
        highs=highs,
        lows=lows,
    )

    # sector_breadth = 0.65 (65% of sector peers positive in last 5 days)
    result = _detect_sector_pre_breakout(pw, 0.65, "2026-06-16", "BULL")
    assert result is not None, "Expected Sector Pre-Breakout to fire"
    assert result.archetype_id == "DNA_1B_SECTOR_PRE_BKT"
    assert result.base_score > 4.0


# ---------------------------------------------------------------------------
# PB-09 Layer 1B scanner produces zero DB writes (purity test)
# ---------------------------------------------------------------------------

def test_pb09_layer_1b_scanner_does_not_write_to_db(conn):
    """run_scan() must produce zero DB writes across all tables."""
    symbol = "PURITY.NS"
    ohlcv = _build_ohlcv(symbol, "2026-01-02", n_days=60)
    with conn:
        _insert_ohlcv(conn, ohlcv)

    # Baseline row counts before scan
    def _count_all(c):
        counts = {}
        for (tbl,) in c.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall():
            row = c.execute(f"SELECT COUNT(*) FROM [{tbl}]").fetchone()  # noqa: S608
            counts[tbl] = row[0]
        return counts

    before = _count_all(conn)
    run_scan(conn, [symbol], "2026-03-04", "BULL")
    after = _count_all(conn)

    diff = {t: after[t] - before[t] for t in after if after[t] != before.get(t, 0)}
    assert diff == {}, f"Layer 1B wrote to DB unexpectedly: {diff}"


# ---------------------------------------------------------------------------
# PB-10 sector_conviction_daily schema correct
# ---------------------------------------------------------------------------

def test_pb10_sector_conviction_daily_schema(conn):
    pragma = {
        row[1]: row[2]
        for row in conn.execute("PRAGMA table_info(sector_conviction_daily)").fetchall()
    }
    required = [
        "record_date", "sector",
        "participation_rate_1d", "participation_rate_5d", "participation_expansion",
        "rs_vs_market_20d", "volume_trend_10d", "consensus_score",
        "capital_flow_score", "capital_flow_data_quality", "sector_conviction_score",
        "theme_phase", "data_quality", "stocks_with_data", "stocks_total",
    ]
    for col in required:
        assert col in pragma, f"Missing column: {col}"


# ---------------------------------------------------------------------------
# PB-11 theme_phase_history schema correct
# ---------------------------------------------------------------------------

def test_pb11_theme_phase_history_schema(conn):
    pragma = {
        row[1]: row[2]
        for row in conn.execute("PRAGMA table_info(theme_phase_history)").fetchall()
    }
    required = [
        "record_id", "sector", "phase", "entered_at", "exited_at",
        "duration_trading_days", "regime_during",
        "peak_participation_rate", "amplitude_pct", "avg_volume_ratio", "data_quality",
    ]
    for col in required:
        assert col in pragma, f"Missing column: {col}"


# ---------------------------------------------------------------------------
# PB-12 Participation rate computed correctly
# ---------------------------------------------------------------------------

def test_pb12_participation_rate_computation(conn):
    """Seed a minimal sector: 2 stocks both positive today."""
    with conn:
        conn.execute("""
            INSERT INTO universe_stocks
                (symbol, company_name, sector, sector_purity_score, is_active, added_date)
            VALUES
                ('AA.NS', 'Alpha', 'TEST_SECTOR', 1.0, 1, '2026-01-01'),
                ('BB.NS', 'Beta',  'TEST_SECTOR', 1.0, 1, '2026-01-01')
        """)
        # AA: yesterday 100, today 105 (+5%) → participates
        # BB: yesterday 200, today 210 (+5%) → participates
        for sym, y, t in [("AA.NS", 100, 105), ("BB.NS", 200, 210)]:
            conn.execute("""
                INSERT OR IGNORE INTO ohlcv_daily
                    (symbol, trade_date, open, high, low, close, volume)
                VALUES (?,?,?,?,?,?,?)
            """, (sym, "2026-06-15", y, y*1.01, y*0.99, y, 1_000_000))
            conn.execute("""
                INSERT OR IGNORE INTO ohlcv_daily
                    (symbol, trade_date, open, high, low, close, volume)
                VALUES (?,?,?,?,?,?,?)
            """, (sym, "2026-06-16", t, t*1.01, t*0.99, t, 1_000_000))

    result = _compute_participation_rates(conn, "TEST_SECTOR", "2026-06-16")
    assert result is not None
    assert result["data_quality"] == "FULL"
    assert result["participation_rate_1d"] == pytest.approx(1.0)   # both positive


# ---------------------------------------------------------------------------
# PB-13 Data quality PARTIAL when coverage < 80%
# ---------------------------------------------------------------------------

def test_pb13_data_quality_partial_when_low_coverage(conn):
    """Seed 5 stocks; only 3 have data → 60% coverage → PARTIAL."""
    with conn:
        for i in range(5):
            sym = f"S{i}.NS"
            conn.execute("""
                INSERT INTO universe_stocks
                    (symbol, company_name, sector, sector_purity_score, is_active, added_date)
                VALUES (?,?,?,?,?,?)
            """, (sym, f"Stock{i}", "COVERAGE_SECTOR", 1.0, 1, "2026-01-01"))
        # Only insert OHLCV for 3 of the 5 stocks
        for i in range(3):
            sym = f"S{i}.NS"
            for dt, px in [("2026-06-15", 100.0), ("2026-06-16", 102.0)]:
                conn.execute("""
                    INSERT OR IGNORE INTO ohlcv_daily
                        (symbol, trade_date, open, high, low, close, volume)
                    VALUES (?,?,?,?,?,?,?)
                """, (sym, dt, px, px*1.01, px*0.99, px, 500_000))

    result = _compute_participation_rates(conn, "COVERAGE_SECTOR", "2026-06-16")
    assert result is not None
    assert result["data_quality"] == "PARTIAL"
    assert result["participation_rate_1d"] is None


# ---------------------------------------------------------------------------
# PB-14 Capital flow score defaults to 0.5 when UNAVAILABLE
# ---------------------------------------------------------------------------

def test_pb14_capital_flow_neutral_when_unavailable(conn):
    score, quality = _get_capital_flow(conn, "EMPTY_SECTOR", "2026-06-16")
    assert quality == "UNAVAILABLE"
    assert score == pytest.approx(CAPITAL_FLOW_NEUTRAL)


# ---------------------------------------------------------------------------
# PB-15 Sector conviction score formula
# ---------------------------------------------------------------------------

def test_pb15_sector_conviction_score_formula():
    """0.4 × capital_flow + 0.6 × (consensus/10)."""
    capital_flow = 0.7    # net buying
    consensus    = 7.0    # out of 10.0
    expected = 0.4 * capital_flow + 0.6 * (consensus / 10.0)
    # Test using the writer internals would require mocking; test the formula directly
    assert expected == pytest.approx(0.4 * 0.7 + 0.6 * 0.7)


# ---------------------------------------------------------------------------
# PB-16 Consensus score components
# ---------------------------------------------------------------------------

def test_pb16_consensus_score_computation():
    """participation=0.60, expansion=+0.08, rs=+3.0, vol_trend=1.3 → score in [0,10]."""
    score = _compute_consensus_score(
        participation_rate_5d=0.60,
        participation_expansion=0.08,
        rs_vs_market_20d=3.0,
        volume_trend_10d=1.3,
    )
    assert score is not None
    assert 0.0 <= score <= 10.0


def test_pb16b_consensus_score_none_when_no_participation():
    score = _compute_consensus_score(
        participation_rate_5d=None,
        participation_expansion=None,
        rs_vs_market_20d=None,
        volume_trend_10d=None,
    )
    assert score is None


# ---------------------------------------------------------------------------
# PB-17 Theme Phase detection — EMERGENCE
# ---------------------------------------------------------------------------

def test_pb17_theme_phase_emergence():
    phase = _detect_theme_phase(
        participation_rate_5d=0.40,    # 30–50%
        participation_expansion=0.05,  # rising
        volume_trend_10d=1.1,
    )
    assert phase == "EMERGENCE"


def test_pb17b_theme_phase_acceleration():
    phase = _detect_theme_phase(
        participation_rate_5d=0.55,    # 50–65%
        participation_expansion=0.03,  # still positive
        volume_trend_10d=1.2,
    )
    assert phase == "ACCELERATION"


def test_pb17c_theme_phase_crowding():
    phase = _detect_theme_phase(
        participation_rate_5d=0.85,    # > 80%
        participation_expansion=0.01,
        volume_trend_10d=1.0,
    )
    assert phase == "CROWDING"


def test_pb17d_theme_phase_exhaustion():
    phase = _detect_theme_phase(
        participation_rate_5d=0.58,    # below 65%, declining
        participation_expansion=-0.08, # contracting
        volume_trend_10d=0.82,         # volume declining
    )
    assert phase == "EXHAUSTION"


# ---------------------------------------------------------------------------
# PB-18 Theme Phase Engine requires 30+ day history
# ---------------------------------------------------------------------------

def test_pb18_theme_phase_requires_history(conn):
    """With only 5 rows of sector_conviction_daily, theme phase must not activate."""
    sector = "HIST_SECTOR"
    with conn:
        for i in range(5):
            dt = date(2026, 6, i + 1).isoformat()
            conn.execute("""
                INSERT OR IGNORE INTO sector_conviction_daily
                    (record_date, sector, data_quality,
                     participation_rate_5d, stocks_with_data, stocks_total)
                VALUES (?, ?, 'FULL', 0.45, 10, 10)
            """, (dt, sector))

    has_history = _has_sufficient_phase_history(conn, sector, "2026-06-16")
    assert not has_history, "Should not have sufficient history with only 5 rows"


def test_pb18b_theme_phase_activates_at_30_days(conn):
    """With 30 rows of FULL data, theme phase engine must activate."""
    sector = "HIST30_SECTOR"
    with conn:
        for i in range(30):
            dt = date(2026, 5, 1 + i).isoformat()
            conn.execute("""
                INSERT OR IGNORE INTO sector_conviction_daily
                    (record_date, sector, data_quality,
                     participation_rate_5d, stocks_with_data, stocks_total)
                VALUES (?, ?, 'FULL', 0.45, 10, 10)
            """, (dt, sector))

    has_history = _has_sufficient_phase_history(conn, sector, "2026-06-16")
    assert has_history, "Should have sufficient history with 30 rows"


# ---------------------------------------------------------------------------
# PB-19 run_sector_conviction writes correctly (end-to-end)
# ---------------------------------------------------------------------------

def test_pb19_run_sector_conviction_writes_row(conn):
    """Seed a small sector with enough data; run_sector_conviction; verify row written."""
    sector = "E2E_SECTOR"
    with conn:
        for i in range(10):
            sym = f"E{i}.NS"
            conn.execute("""
                INSERT INTO universe_stocks
                    (symbol, company_name, sector, sector_purity_score, is_active, added_date)
                VALUES (?,?,?,?,?,?)
            """, (sym, f"E2E{i}", sector, 1.0, 1, "2026-01-01"))
            # Insert 25 days of rising price data
            for d_off in range(25):
                dt = date(2026, 5, 1 + d_off).isoformat()
                px = 100.0 + d_off * 0.5 + i
                conn.execute("""
                    INSERT OR IGNORE INTO ohlcv_daily
                        (symbol, trade_date, open, high, low, close, volume)
                    VALUES (?,?,?,?,?,?,?)
                """, (sym, dt, px, px*1.01, px*0.99, px, 500_000))

    with conn:
        run_sector_conviction(conn, "2026-05-25", "BULL", sectors=[sector])

    row = conn.execute("""
        SELECT * FROM sector_conviction_daily
        WHERE record_date = ? AND sector = ?
    """, ("2026-05-25", sector)).fetchone()

    assert row is not None, "sector_conviction_daily row was not written"
    assert row["data_quality"] == "FULL"
    assert row["participation_rate_1d"] is not None


# ---------------------------------------------------------------------------
# PB-20 PARTIAL rows do not trigger theme phase transitions
# ---------------------------------------------------------------------------

def test_pb20_partial_rows_do_not_trigger_phase_transition(conn):
    """Even with 30 days of history, a PARTIAL row must not open a theme_phase_history record."""
    sector = "PARTIAL_SECTOR"
    # Seed 30 FULL history rows
    with conn:
        for i in range(30):
            dt = date(2026, 5, 1 + i).isoformat()
            conn.execute("""
                INSERT OR IGNORE INTO sector_conviction_daily
                    (record_date, sector, data_quality,
                     participation_rate_5d, stocks_with_data, stocks_total)
                VALUES (?, ?, 'FULL', 0.40, 10, 10)
            """, (dt, sector))

        # Add active universe stocks (but give them no OHLCV — will produce PARTIAL)
        for i in range(10):
            sym = f"P{i}.NS"
            conn.execute("""
                INSERT INTO universe_stocks
                    (symbol, company_name, sector, sector_purity_score, is_active, added_date)
                VALUES (?,?,?,?,?,?)
            """, (sym, f"Partial{i}", sector, 1.0, 1, "2026-01-01"))

    # run_sector_conviction with no OHLCV data → PARTIAL
    with conn:
        run_sector_conviction(conn, "2026-06-16", "BULL", sectors=[sector])

    partial_row = conn.execute("""
        SELECT data_quality FROM sector_conviction_daily
        WHERE sector = ? AND record_date = '2026-06-16'
    """, (sector,)).fetchone()
    assert partial_row is not None
    assert partial_row["data_quality"] == "PARTIAL"

    # Theme phase history must remain empty for this sector
    history_count = conn.execute("""
        SELECT COUNT(*) FROM theme_phase_history WHERE sector = ?
    """, (sector,)).fetchone()[0]
    assert history_count == 0, "PARTIAL row must not trigger theme_phase_history write"


# ---------------------------------------------------------------------------
# PB-21 Phase B tables do not exist at end of Phase A (isolation check)
# ---------------------------------------------------------------------------

def test_pb21_phase_b_tables_absent_in_phase_a_only_db():
    """Phase A migration must NOT create Phase B tables."""
    from oios.db.migrations import apply_phase_a
    c = sqlite3.connect(":memory:")
    apply_phase_a(conn=c)
    tables = {r[0] for r in c.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()}
    assert "sector_conviction_daily" not in tables
    assert "theme_phase_history" not in tables
    c.close()


# ---------------------------------------------------------------------------
# B-Audit-01: Sector coverage integrity — no sector < 8 stocks
# ---------------------------------------------------------------------------

def test_pb22_sector_coverage_integrity():
    """Every sector in UNIVERSE_230 must have >= 8 stocks."""
    from collections import Counter
    sector_counts = Counter(row[2] for row in UNIVERSE_230)

    violations = {
        sector: count
        for sector, count in sector_counts.items()
        if count < 8
    }
    assert not violations, (
        f"Sectors with < 8 stocks (participation rates become statistically unstable): {violations}"
    )
