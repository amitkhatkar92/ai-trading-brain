"""OIOS audit fixes: trading calendar, discovered-expiry repair, evidence de-duplication,
volume-burst rule, sector peer groups, sector classification and sector conviction.

Each of these was a defect found by tracing an empty or saturated output to its cause:
the calendar was never populated (signal ages 0, 999-day expiries), the same archetype
re-detected daily was counted as new evidence (conviction pinned at 10), the volume-burst
terminal rule was never computed, the Sector Breakout Accelerator never received a sector
return, 48% of the universe had no sector, and the sector conviction writer had no caller.
"""
from __future__ import annotations

import os
import sqlite3
import uuid
from datetime import date, timedelta

import pytest

os.environ["OIOS_DB_PATH"] = ":memory:"

from oios.data import sector_classifier as sc
from oios.data import sector_conviction_writer as scw
from oios.db import repository as R
from oios.db.calendar import (
    count_trading_days, ensure_trading_calendar, is_trading_day, populate_trading_calendar_with_names,
)
from oios.db.migrations import apply_phase_c
from oios.domain.models import (
    Opportunity, OpportunitySignal, OpportunityState, SignalBirth,
)
from oios.domain.opportunity_service import repair_unset_discovered_expiry
from oios.engine.ele import _compute_conviction_re_weighted, run_ele_cycle_for_opportunity
from oios.engine.re_calculator import compute_volume_burst
from oios.scanners import layer_1a as l1a


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:", detect_types=sqlite3.PARSE_DECLTYPES)
    c.row_factory = sqlite3.Row
    apply_phase_c(conn=c)
    yield c
    c.close()


# ── trading calendar ────────────────────────────────────────────────────────

def test_ensure_trading_calendar_marks_weekends_and_verified_holidays_and_is_idempotent(conn):
    first = ensure_trading_calendar(conn)
    assert first["rows"] == 365 and first["from"] == "2026-01-01" and first["to"] == "2026-12-31"
    assert not is_trading_day(conn, "2026-11-10")          # Diwali Balipratipada
    assert not is_trading_day(conn, "2026-11-14")          # Saturday
    assert is_trading_day(conn, "2026-11-11")
    assert count_trading_days(conn, "2026-11-09", "2026-11-12") == 2
    ensure_trading_calendar(conn)
    assert conn.execute("SELECT COUNT(*) FROM trading_calendar").fetchone()[0] == 365


def test_ensure_trading_calendar_never_raises(monkeypatch):
    broken = sqlite3.connect(":memory:")                    # no trading_calendar table
    result = ensure_trading_calendar(broken)
    assert result["rows"] == 0 and "error" in result


# ── discovered-expiry sentinel repair ───────────────────────────────────────

def _opportunity(conn, symbol, created, expires, state=OpportunityState.DISCOVERED, ttl=10):
    opp_id = str(uuid.uuid4())
    signal_id = str(uuid.uuid4())
    R.create_signal_birth(conn, SignalBirth(
        signal_id=signal_id, symbol=symbol, archetype_id="DNA_1A_MOMENTUM_CONT", signal_type="1A",
        detected_at=created, birth_price=100.0, base_score=3.0, regime_at_birth="RANGE",
        expected_ttl_days=ttl, expected_move_direction="LONG", expected_move_pct=8.0))
    R.create_opportunity(conn, Opportunity(
        opportunity_id=opp_id, symbol=symbol, direction="LONG", sector="IT", created_at=created,
        first_signal_id=signal_id, regime_at_birth="RANGE", birth_ttl_days=ttl, effective_ttl_days=ttl,
        discovered_expires_at=expires, conviction_score=0.0, confirming_count=1))
    conn.execute("UPDATE opportunities SET current_state = ? WHERE opportunity_id = ?",
                 (state.value if hasattr(state, "value") else state, opp_id))
    conn.execute("UPDATE signal_births SET opportunity_id = ? WHERE signal_id = ?", (opp_id, signal_id))
    R.add_opportunity_signal(conn, OpportunitySignal(
        opportunity_id=opp_id, signal_id=signal_id, signal_type="1A",
        signal_direction="CONFIRMING", evidence_weight=1.0, added_at=created))
    return opp_id


def _expiry(conn, opp_id):
    return conn.execute("SELECT discovered_expires_at FROM opportunities WHERE opportunity_id = ?",
                        (opp_id,)).fetchone()[0]


def test_sentinel_expiry_is_recomputed_from_the_trading_calendar(conn):
    ensure_trading_calendar(conn)
    sentinel = _opportunity(conn, "A.NS", "2026-11-02", "2029-07-28")            # 999-day sentinel
    real = _opportunity(conn, "B.NS", "2026-11-02", "2026-11-06")                # genuine expiry
    done = _opportunity(conn, "C.NS", "2026-11-02", "2029-07-28", state=OpportunityState.INVALID)
    result = repair_unset_discovered_expiry(conn)
    assert result == {"repaired": 1, "skipped": 0}
    assert _expiry(conn, sentinel) == "2026-11-09"       # floor(10 x 0.5) = 5 trading days after Mon 2 Nov
    assert _expiry(conn, real) == "2026-11-06" and _expiry(conn, done) == "2029-07-28"
    assert repair_unset_discovered_expiry(conn) == {"repaired": 0, "skipped": 0}


def test_sentinel_repair_skips_rows_the_empty_calendar_cannot_resolve(conn):
    opp = _opportunity(conn, "A.NS", "2026-11-02", "2029-07-28")
    assert repair_unset_discovered_expiry(conn) == {"repaired": 0, "skipped": 1}
    assert _expiry(conn, opp) == "2029-07-28"


# ── volume burst ────────────────────────────────────────────────────────────

def _prices(conn, symbol, last_volume, last_close, days=25, prev_close=100.0, base_volume=1000.0):
    start = date(2026, 10, 1)
    rows = []
    for i in range(days):
        day = (start + timedelta(days=i)).isoformat()
        last = i == days - 1
        close = last_close if last else (prev_close if i == days - 2 else 100.0)
        rows.append((symbol, day, close, close * 1.01, close * 0.99, close,
                     last_volume if last else base_volume, None, "TEST"))
    conn.executemany("INSERT INTO ohlcv_daily (symbol, trade_date, open, high, low, close, volume, "
                     "adjusted_close, data_source) VALUES (?,?,?,?,?,?,?,?,?)", rows)
    return (start + timedelta(days=days - 1)).isoformat()


def test_volume_burst_requires_a_spike_and_a_close_against_the_thesis(conn):
    adverse = _prices(conn, "DOWN.NS", last_volume=4000, last_close=96)
    confirming = _prices(conn, "UP.NS", last_volume=4000, last_close=104)
    quiet = _prices(conn, "QUIET.NS", last_volume=2500, last_close=96)
    assert compute_volume_burst(conn, "DOWN.NS", adverse, "LONG") is True
    assert compute_volume_burst(conn, "UP.NS", confirming, "LONG") is False      # spike on a confirming day
    assert compute_volume_burst(conn, "QUIET.NS", quiet, "LONG") is False        # 2.5x is not a burst
    assert compute_volume_burst(conn, "UP.NS", confirming, "SHORT") is True      # mirrored for shorts


def test_volume_burst_ignores_stale_data_and_holiday_placeholder_bars(conn):
    day = _prices(conn, "DOWN.NS", last_volume=4000, last_close=96)
    stale = (date.fromisoformat(day) + timedelta(days=3)).isoformat()
    assert compute_volume_burst(conn, "DOWN.NS", stale, "LONG") is False          # no bar for that date
    conn.execute("INSERT INTO ohlcv_daily (symbol, trade_date, open, high, low, close, volume, adjusted_close, "
                 "data_source) VALUES ('DOWN.NS', ?, 96, 96, 96, 96, 0, NULL, 'TEST')", (stale,))
    assert compute_volume_burst(conn, "DOWN.NS", stale, "LONG") is False          # volume 0 placeholder
    assert compute_volume_burst(conn, "NOPE.NS", day, "LONG") is False


def test_ele_invalidates_an_active_long_thesis_on_an_adverse_volume_burst(conn):
    ensure_trading_calendar(conn)
    day = _prices(conn, "DOWN.NS", last_volume=4000, last_close=96)
    opp_id = _opportunity(conn, "DOWN.NS", "2026-10-05", "2026-10-20", state=OpportunityState.ACTIVE)
    conn.execute("UPDATE opportunities SET age_trading_days = 2 WHERE opportunity_id = ?", (opp_id,))
    cycle = run_ele_cycle_for_opportunity(conn, opp_id, day, "RANGE")
    assert cycle.new_state == OpportunityState.INVALID
    assert conn.execute("SELECT invalidation_reason FROM opportunities WHERE opportunity_id = ?",
                        (opp_id,)).fetchone()[0] == "THESIS_INVALIDATED"


# ── conviction: repeated detections are one piece of evidence ───────────────

def _add_signal(conn, opp_id, symbol, archetype, detected, base=3.0):
    signal_id = str(uuid.uuid4())
    R.create_signal_birth(conn, SignalBirth(
        signal_id=signal_id, symbol=symbol, archetype_id=archetype, signal_type="1A",
        detected_at=detected, birth_price=100.0, base_score=base, regime_at_birth="RANGE",
        expected_ttl_days=10, expected_move_direction="LONG", expected_move_pct=8.0))
    R.add_opportunity_signal(conn, OpportunitySignal(
        opportunity_id=opp_id, signal_id=signal_id, signal_type="1A",
        signal_direction="CONFIRMING", evidence_weight=1.0, added_at=detected))
    conn.execute("UPDATE signal_births SET opportunity_id = ? WHERE signal_id = ?", (opp_id, signal_id))


def test_same_archetype_redetected_daily_does_not_inflate_conviction(conn):
    ensure_trading_calendar(conn)
    for symbol in ("OLD.NS", "MANY.NS", "FRESH.NS", "TWO.NS"):
        day = _prices(conn, symbol, last_volume=1000, last_close=100)
    old = _opportunity(conn, "OLD.NS", "2026-10-20", "2026-10-30")
    many = _opportunity(conn, "MANY.NS", "2026-10-20", "2026-10-30")
    fresh = _opportunity(conn, "FRESH.NS", "2026-10-23", "2026-10-30")
    two = _opportunity(conn, "TWO.NS", "2026-10-20", "2026-10-30")
    for detected in ("2026-10-21", "2026-10-22", "2026-10-23"):
        _add_signal(conn, many, "MANY.NS", "DNA_1A_MOMENTUM_CONT", detected)      # same archetype again
    _add_signal(conn, two, "TWO.NS", "DNA_1B_DELIVERY_EXPANSION", "2026-10-20")   # a different archetype
    stale_single = _compute_conviction_re_weighted(conn, old, day, "RANGE")
    repeated = _compute_conviction_re_weighted(conn, many, day, "RANGE")
    freshest_only = _compute_conviction_re_weighted(conn, fresh, day, "RANGE")
    independent = _compute_conviction_re_weighted(conn, two, day, "RANGE")
    assert 0 < stale_single < repeated < 10
    assert repeated == pytest.approx(freshest_only, rel=1e-6)   # four detections = the freshest one, not their sum
    assert repeated < 4 * stale_single                          # the old rule summed all four
    assert independent > stale_single                           # a genuinely different archetype adds evidence


# ── Layer 1A sector return ──────────────────────────────────────────────────

def _universe(conn, sector_symbols):
    conn.execute("DELETE FROM universe_stocks")
    for sector, symbols in sector_symbols.items():
        for symbol in symbols:
            conn.execute("INSERT INTO universe_stocks (symbol, company_name, sector, is_active, sector_purity_score, "
                         "added_date) VALUES (?,?,?,1,1.0,'2026-01-01')", (symbol, symbol, sector))


def _closes(conn, symbol, last_return_pct):
    """30 sessions: flat, then a final 5-day return of last_return_pct."""
    start = date(2026, 10, 1)
    for i in range(30):
        day = (start + timedelta(days=i)).isoformat()
        close = 100.0 if i < 25 else 100.0 * (1 + last_return_pct / 100 * (i - 24) / 5)
        conn.execute("INSERT INTO ohlcv_daily (symbol, trade_date, open, high, low, close, volume, "
                     "adjusted_close, data_source) VALUES (?,?,?,?,?,?,?,?,?)",
                     (symbol, day, close, close, close, close, 1000.0, None, "TEST"))
    return (start + timedelta(days=29)).isoformat()


def test_sector_return_uses_only_real_peer_groups(conn):
    tech = [f"T{i}.NS" for i in range(6)]
    _universe(conn, {"IT": tech, "UNKNOWN": [f"U{i}.NS" for i in range(6)], "TINY": ["X1.NS", "X2.NS", "X3.NS"]})
    returns = {**{s: 2.0 for s in tech[:5]}, tech[5]: 12.0}
    for symbol in [r[0] for r in conn.execute("SELECT symbol FROM universe_stocks")]:
        day = _closes(conn, symbol, returns.get(symbol, 1.0))
    result = l1a._sector_returns_5d(conn, day)
    assert result[tech[5]] == pytest.approx(2.0, abs=0.01)         # leave-one-out: the other five peers
    assert result[tech[0]] == pytest.approx((4 * 2.0 + 12.0) / 5, abs=0.01)
    assert not any(s.startswith(("U", "X")) for s in result)       # UNKNOWN and a 3-stock sector get nothing


def _momentum_window():
    closes, price = [100.0] * 25, 100.0
    for i in range(10):
        price *= 1.02 if i % 2 == 0 else 0.994
        closes.append(price)
    n = len(closes)
    return l1a.PriceWindow(symbol="M.NS", dates=[str(i) for i in range(n)], closes=closes,
                           volumes=[1000.0] * (n - 1) + [2000.0],
                           highs=[c * 1.005 for c in closes], lows=[c * 0.995 for c in closes])


def test_sector_breakout_needs_to_beat_the_sector_when_one_is_known():
    window = _momentum_window()
    assert 55 <= 100 and window.price_change_pct(10) > 7.0
    assert l1a._detect_sector_breakout_accelerator(window, "d", "RANGE") is not None            # legacy path
    assert l1a._detect_sector_breakout_accelerator(window, "d", "RANGE", sector_return_5d=-1.0) is not None
    assert l1a._detect_sector_breakout_accelerator(window, "d", "RANGE", sector_return_5d=window.price_change_pct(5)) is None


def test_scan_symbol_skips_the_sector_archetype_when_no_sector_return_exists(conn):
    ensure_trading_calendar(conn)
    start = date(2026, 9, 1)
    window = _momentum_window()
    for i, close in enumerate(window.closes):
        conn.execute("INSERT INTO ohlcv_daily (symbol, trade_date, open, high, low, close, volume, "
                     "adjusted_close, data_source) VALUES (?,?,?,?,?,?,?,?,?)",
                     ("M.NS", (start + timedelta(days=i)).isoformat(), close, close * 1.005, close * 0.995,
                      close, window.volumes[i], None, "TEST"))
    last = (start + timedelta(days=len(window.closes) - 1)).isoformat()

    def archetypes(**kw):
        return {s.archetype_id for s in l1a.scan_symbol(conn, "M.NS", last, "RANGE", **kw)}
    assert "DNA_1A_SECTOR_BKT" in archetypes()                                               # legacy default
    assert "DNA_1A_SECTOR_BKT" not in archetypes(sector_required=True)                       # no sector peers
    assert "DNA_1A_SECTOR_BKT" in archetypes(sector_return_5d=0.0, sector_required=True)     # outperforms its sector


# ── sector classification ───────────────────────────────────────────────────

@pytest.mark.parametrize("industry,coarse,expected", [
    ("Banks - Regional", "Financial Services", "BANKING_FINANCE"),
    ("Asset Management", None, "BANKING_FINANCE"),
    ("Drug Manufacturers - Specialty & Generic", "Healthcare", "PHARMA"),
    ("Software - Application", "Technology", "IT"),
    ("Aerospace & Defense", "Industrials", "DEFENCE"),
    ("Specialty Chemicals", "Basic Materials", "CHEMICALS"),
    ("Auto Parts", "Consumer Cyclical", "AUTO"),
    ("Steel", "Basic Materials", "METALS"),
    ("Oil & Gas Refining & Marketing", "Energy", "ENERGY"),
    ("Utilities - Renewable", "Utilities", "POWER"),
    ("Packaged Foods", "Consumer Defensive", "FMCG"),
    ("Real Estate - Development", "Real Estate", "REALESTATE"),
    ("Specialty Industrial Machinery", "Industrials", "INFRA"),
    ("Textile Manufacturing", "Consumer Cyclical", "TEXTILES"),
    ("Some Industry NSE Invents", "Financial Services", "BANKING_FINANCE"),     # unambiguous coarse fallback
    ("Some Industry NSE Invents", "Basic Materials", None),                     # ambiguous coarse: stay unknown
    (None, "Consumer Cyclical", None), (None, None, None),
])
def test_industry_maps_to_the_oios_vocabulary(industry, coarse, expected):
    assert sc.classify(industry, coarse) == expected


def _universe_conn(rows):
    c = sqlite3.connect(":memory:")
    c.execute("CREATE TABLE universe_stocks (symbol TEXT PRIMARY KEY, sector TEXT, is_active INTEGER)")
    c.executemany("INSERT INTO universe_stocks VALUES (?,?,?)", rows)
    return c


def test_classification_fills_unknown_only_merges_aliases_and_caches(tmp_path):
    conn = _universe_conn([("CURATED.NS", "AUTO", 1), ("NEW.NS", "UNKNOWN", 1), ("EMPTY.NS", None, 1),
                           ("DUP.NS", "FINANCIAL", 1), ("OFF.NS", "UNKNOWN", 0), ("NONE.NS", "UNKNOWN", 1)])
    answers = {"NEW.NS": ("Software - Application", "Technology"), "EMPTY.NS": ("Steel", "Basic Materials"),
               "NONE.NS": (None, None)}
    calls = []

    def fetch(symbol):
        calls.append(symbol)
        return answers[symbol]
    cache = str(tmp_path / "cache.json")
    result = sc.run_sector_classification(conn, fetch_fn=fetch, cache_path=cache, today=date(2026, 11, 18))
    sectors = dict(conn.execute("SELECT symbol, sector FROM universe_stocks").fetchall())
    assert sectors["NEW.NS"] == "IT" and sectors["EMPTY.NS"] == "METALS"
    assert sectors["CURATED.NS"] == "AUTO" and sectors["OFF.NS"] == "UNKNOWN"              # never overwritten / inactive
    assert sectors["DUP.NS"] == "BANKING_FINANCE" and sectors["NONE.NS"] == "UNKNOWN"      # alias merged / no guess
    assert result["classified"] == 2 and result["aliased"] == 1 and result["still_unknown"] == 1
    assert sorted(calls) == ["EMPTY.NS", "NEW.NS", "NONE.NS"]
    calls.clear()                                                                           # second run: cache, no fetch
    again = sc.run_sector_classification(conn, fetch_fn=fetch, cache_path=cache, today=date(2026, 11, 20))
    assert calls == [] and again["fetched"] == 0
    later = sc.run_sector_classification(conn, fetch_fn=fetch, cache_path=cache, today=date(2026, 12, 5))
    assert calls == ["NONE.NS"]                                                              # failed lookup retried after the window


def test_classification_is_bounded_per_run_and_never_raises(tmp_path):
    conn = _universe_conn([(f"S{i}.NS", "UNKNOWN", 1) for i in range(10)])
    result = sc.run_sector_classification(conn, max_fetches=4, fetch_fn=lambda s: ("Steel", None),
                                          cache_path=str(tmp_path / "c.json"))
    assert result["fetched"] == 4 and result["classified"] == 4 and result["still_unknown"] == 6
    broken = sqlite3.connect(":memory:")
    assert "error" in sc.run_sector_classification(broken, cache_path=str(tmp_path / "x.json"))


# ── sector conviction ───────────────────────────────────────────────────────

def test_sector_conviction_skips_unknown_and_backfills_each_missing_session_once(conn):
    symbols = [f"IT{i}.NS" for i in range(6)]
    _universe(conn, {"IT": symbols, "UNKNOWN": [f"U{i}.NS" for i in range(6)], "TINY": ["X1.NS", "X2.NS"]})
    start = date(2026, 9, 1)
    for symbol in [r[0] for r in conn.execute("SELECT symbol FROM universe_stocks")]:
        for i in range(60):
            day = (start + timedelta(days=i)).isoformat()
            price = 100.0 + i * 0.3
            conn.execute("INSERT INTO ohlcv_daily (symbol, trade_date, open, high, low, close, volume, "
                         "adjusted_close, data_source) VALUES (?,?,?,?,?,?,?,?,?)",
                         (symbol, day, price, price, price, price, 1000.0, None, "TEST"))
    end = (start + timedelta(days=59)).isoformat()
    first = scw.backfill_sector_conviction(conn, end, days=12)
    assert first["dates"] >= 7                                    # twelve calendar rows minus weekends/holidays
    sectors = {r[0] for r in conn.execute("SELECT DISTINCT sector FROM sector_conviction_daily")}
    assert sectors == {"IT"}                                      # UNKNOWN is not a peer group, TINY is too small
    assert {r[0] for r in conn.execute("SELECT DISTINCT data_quality FROM sector_conviction_daily")} == {"FULL"}
    count = conn.execute("SELECT COUNT(*) FROM sector_conviction_daily").fetchone()[0]
    assert scw.backfill_sector_conviction(conn, end, days=12)["dates"] == 0
    assert conn.execute("SELECT COUNT(*) FROM sector_conviction_daily").fetchone()[0] == count
    assert not conn.execute(
        "SELECT 1 FROM sector_conviction_daily WHERE record_date IN ('2026-09-05', '2026-09-06')").fetchone() \
        or date(2026, 9, 5).weekday() < 5                          # weekends are never written


def test_health_check_warns_when_the_calendar_is_missing_or_about_to_run_out(tmp_path):
    from datetime import datetime
    from analysis import pipeline_health_monitor as health
    path = tmp_path / "market_behavior.db"
    db = sqlite3.connect(path)
    db.execute("CREATE TABLE trading_calendar (calendar_date TEXT PRIMARY KEY, is_trading_day INTEGER, holiday_name TEXT)")
    db.commit()
    ctx = lambda day: health.HealthContext(now=datetime.fromisoformat(f"{day} 09:00").replace(tzinfo=health.IST),
                                           data_dir=str(tmp_path))
    assert health.check_trading_calendar(ctx("2026-11-18"))["status"] == "WARN"            # empty
    populate_trading_calendar_with_names(db, "2026-01-01", "2026-12-31")
    db.commit()
    assert health.check_trading_calendar(ctx("2026-11-18"))["status"] == "OK"
    expiring = health.check_trading_calendar(ctx("2026-12-15"))                            # < 21 days of cover left
    assert expiring["status"] == "WARN" and "NSE_HOLIDAYS" in expiring["detail"]
    assert health.check_trading_calendar(health.HealthContext(
        now=ctx("2026-11-18").now, data_dir=str(tmp_path / "none")))["status"] == "INFO"
    db.close()


def test_orchestrator_wires_calendar_repair_conviction_and_classification():
    from pathlib import Path
    source = (Path(__file__).resolve().parents[1] / "orchestrator" / "master_orchestrator.py"
              ).read_text(encoding="utf-8")
    ele = source.index("run_ele_daily as _ele_run_daily")
    assert source.index("ensure_trading_calendar as _ele_cal") > ele - 200
    assert source.index("ensure_trading_calendar as _ele_cal") < source.index("_ele_run_daily(_ele_conn")
    assert source.index("run_sector_conviction as _sc15_run") < ele
    assert source.index("run_sector_classification as _run_sc") < source.index("signal_births: 1A=")
