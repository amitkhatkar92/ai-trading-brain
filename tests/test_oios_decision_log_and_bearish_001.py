"""OIOS: bearish archetypes (CONTRADICTED was unreachable), decision_log (never written) and
archetype_versions (never seeded). Each was an empty output traced to a missing producer."""
from __future__ import annotations

import os
import sqlite3
import uuid
from datetime import date, timedelta

import pytest

os.environ["OIOS_DB_PATH"] = ":memory:"

from oios.db import repository as R
from oios.db.calendar import ensure_trading_calendar
from oios.db.migrations import apply_phase_c
from oios.domain.models import Opportunity, OpportunitySignal, OpportunityState, SignalBirth
from oios.domain.opportunity_service import attach_or_create_opportunity
from oios.engine import decision_logger as DL
from oios.engine.archetype_registry import ARCHETYPES, seed_archetype_versions
from oios.engine.counterfactual_engine import run_nightly_retroactive_job
from oios.engine.ele import run_ele_daily
from oios.scanners import layer_1a as l1a


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:", detect_types=sqlite3.PARSE_DECLTYPES)
    c.row_factory = sqlite3.Row
    apply_phase_c(conn=c)
    yield c
    c.close()


def _window(closes, volumes=None, highs=None, lows=None, symbol="TEST.NS"):
    n = len(closes)
    return l1a.PriceWindow(
        symbol=symbol, dates=[f"2026-01-{i:02d}" for i in range(n)], closes=closes,
        volumes=volumes or [1000.0] * (n - 1) + [2000.0],
        highs=highs or [c + 0.2 for c in closes], lows=lows or [c - 0.2 for c in closes])


# ── bearish archetypes ──────────────────────────────────────────────────────

def test_momentum_breakdown_fires_on_a_volume_confirmed_drop_and_is_short():
    closes = [90.0] * 30 + [120.0 - i * 0.7 for i in range(30)]
    raw = l1a._detect_momentum_breakdown(_window(closes), "2026-11-18", "BEAR")
    assert raw is not None and raw.direction == "SHORT" and raw.archetype_id == "DNA_1A_MOMENTUM_BREAKDOWN"
    assert raw.qualifies


def test_momentum_breakdown_ignores_uptrends_weak_volume_and_stocks_already_at_the_low():
    rising = [100.0 + i * 0.5 for i in range(60)]
    assert l1a._detect_momentum_breakdown(_window(rising), "d", "r") is None
    falling = [90.0] * 30 + [120.0 - i * 0.7 for i in range(30)]
    assert l1a._detect_momentum_breakdown(_window(falling, volumes=[1000.0] * 60), "d", "r") is None
    capitulated = [120.0 - i * 0.7 for i in range(60)]          # last close sits on the 52w low
    assert l1a._detect_momentum_breakdown(_window(capitulated), "d", "r") is None


def test_52w_low_expansion_fires_on_a_fresh_low_with_volume_and_not_on_a_stale_one():
    closes = [100.0] * 54 + [99.5] * 5 + [98.0]
    lows = [c - 0.2 for c in closes]
    lows[-1] = 97.5
    raw = l1a._detect_52w_low_expansion(_window(closes, lows=lows), "2026-11-18", "BEAR")
    assert raw is not None and raw.direction == "SHORT" and raw.archetype_id == "DNA_1A_52W_LOW_EXPAND"
    stale = list(lows)
    stale[-3] = 97.4                                            # the low was already touched this week
    assert l1a._detect_52w_low_expansion(_window(closes, lows=stale), "d", "r") is None
    assert l1a._detect_52w_low_expansion(_window(closes, lows=lows, volumes=[1000.0] * 60), "d", "r") is None


def _store_prices(conn, symbol, closes, start=date(2026, 8, 3)):
    day, last = start, start
    for i, close in enumerate(closes):
        while day.weekday() >= 5:                       # trading days only
            day += timedelta(days=1)
        conn.execute("INSERT INTO ohlcv_daily (symbol, trade_date, open, high, low, close, volume) "
                     "VALUES (?,?,?,?,?,?,?)",
                     (symbol, day.isoformat(), close, close + 0.2, close - 0.2, close,
                      2000.0 if i == len(closes) - 1 else 1000.0))
        last = day
        day += timedelta(days=1)
    return last.isoformat()


def test_scan_symbol_emits_the_bearish_signals_and_keeps_the_sector_detector_index():
    c = sqlite3.connect(":memory:")
    apply_phase_c(conn=c)
    last = _store_prices(c, "DROP.NS", [90.0] * 30 + [120.0 - i * 0.7 for i in range(30)])
    ids = {s.archetype_id for s in l1a.scan_symbol(c, "DROP.NS", last, "BEAR", sector_return_5d=None,
                                                   sector_required=True)}
    assert "DNA_1A_MOMENTUM_BREAKDOWN" in ids and "DNA_1A_SECTOR_BKT" not in ids     # sector detector removed, not a bearish one


def test_a_short_signal_is_conflicting_evidence_for_a_live_long_opportunity(conn):
    ensure_trading_calendar(conn)
    long_id = _opportunity(conn, "CONF.NS", "LONG", "2026-11-10")
    short_signal = SignalBirth(
        signal_id=str(uuid.uuid4()), symbol="CONF.NS", archetype_id="DNA_1A_MOMENTUM_BREAKDOWN",
        signal_type="1A", detected_at="2026-11-18", birth_price=95.0, base_score=5.0, regime_at_birth="BEAR",
        expected_ttl_days=10, expected_move_direction="SHORT", expected_move_pct=8.0)
    R.create_signal_birth(conn, short_signal)
    attach_or_create_opportunity(conn, short_signal, 10, "BEAR", today="2026-11-18")
    assert R.get_opportunity(conn, long_id).conflicting_count == 1


# ── decision_log ────────────────────────────────────────────────────────────

def _opportunity(conn, symbol, direction="LONG", created="2026-11-02", state=OpportunityState.ACTIVE, reason=None):
    opp_id, signal_id = str(uuid.uuid4()), str(uuid.uuid4())
    R.create_signal_birth(conn, SignalBirth(
        signal_id=signal_id, symbol=symbol, archetype_id="DNA_1A_MOMENTUM_CONT", signal_type="1A",
        detected_at=created, birth_price=100.0, base_score=5.0, regime_at_birth="RANGE",
        expected_ttl_days=10, expected_move_direction=direction, expected_move_pct=8.0))
    R.create_opportunity(conn, Opportunity(
        opportunity_id=opp_id, symbol=symbol, direction=direction, sector="IT", created_at=created,
        first_signal_id=signal_id, regime_at_birth="RANGE", birth_ttl_days=10, effective_ttl_days=10,
        discovered_expires_at="2026-12-30", conviction_score=7.0, confirming_count=1))
    conn.execute("UPDATE opportunities SET current_state = ?, invalidation_reason = ?, re_score = 5.0 "
                 "WHERE opportunity_id = ?", (state, reason, opp_id))
    conn.execute("UPDATE signal_births SET opportunity_id = ? WHERE signal_id = ?", (opp_id, signal_id))
    R.add_opportunity_signal(conn, OpportunitySignal(
        opportunity_id=opp_id, signal_id=signal_id, signal_type="1A",
        signal_direction="CONFIRMING", evidence_weight=1.0, added_at=created))
    return opp_id


def test_every_state_and_invalidation_reason_maps_to_a_spec_action():
    d = DL.decision_for
    assert d("ACTIVE", None, 6.0, 4.0)[0] == "ENTER"
    assert d("WATCHING", None, 3.0, 4.0)[0] == "PASS_RE_LOW" and d("WATCHING", None, 5.0, 4.0)[0] == "PASS_WATCHING"
    assert d("DISCOVERED", None, None, 4.0)[0] == "PASS_WATCHING"
    for reason, action in {"TTL_EXHAUSTED": "INVALID_TTL", "EC_EXHAUSTED": "INVALID_EC",
                           "THESIS_INVALIDATED": "INVALID_VOLUME_BURST", "ZOMBIE_CAP": "INVALID_ZOMBIE",
                           "CONTRADICTED": "INVALID_CONTRADICTED", "NEVER_MATURED": "INVALID_NEVER_MATURED"}.items():
        assert d("INVALID", reason, 1.0, 4.0) == (action, reason)


def test_a_cycle_decision_is_written_once_per_opportunity_per_day_with_the_price(conn):
    opp = _opportunity(conn, "DEC.NS")
    _store_prices(conn, "DEC.NS", [100.0, 101.0, 102.0], start=date(2026, 11, 16))
    assert DL.log_cycle_decision(conn, opp, "2026-11-18", "RANGE", 4.0) is True
    assert DL.log_cycle_decision(conn, opp, "2026-11-18", "RANGE", 4.0) is False
    row = conn.execute("SELECT * FROM decision_log").fetchone()
    assert row["action"] == "ENTER" and row["price_at_decision"] == 102.0 and row["regime"] == "RANGE"
    assert conn.execute("SELECT COUNT(*) FROM decision_log").fetchone()[0] == 1


def test_no_price_means_no_row_because_price_at_decision_is_mandatory(conn):
    opp = _opportunity(conn, "NOPX.NS")
    assert DL.log_cycle_decision(conn, opp, "2026-11-18", "RANGE", 4.0) is False
    assert conn.execute("SELECT COUNT(*) FROM decision_log").fetchone()[0] == 0


def test_run_ele_daily_writes_decisions_without_breaking_the_cycle(conn):
    ensure_trading_calendar(conn)
    _opportunity(conn, "ELE.NS", state=OpportunityState.DISCOVERED)
    _store_prices(conn, "ELE.NS", [100.0 + i for i in range(40)], start=date(2026, 10, 12))
    result = run_ele_daily(conn, "2026-11-18", "RANGE")
    assert result.opps_processed == 1
    assert conn.execute("SELECT COUNT(*) FROM decision_log").fetchone()[0] == 1


def test_outcomes_are_filled_in_the_trade_direction_and_classified(conn):
    ensure_trading_calendar(conn)
    long_id = _opportunity(conn, "UP.NS", "LONG")
    short_id = _opportunity(conn, "DN.NS", "SHORT")
    for opp_id in (long_id, short_id):
        conn.execute("UPDATE opportunities SET current_state = 'WATCHING' WHERE opportunity_id = ?", (opp_id,))
    _store_prices(conn, "UP.NS", [100.0 + i for i in range(30)], start=date(2026, 9, 21))
    _store_prices(conn, "DN.NS", [100.0 - i * 0.5 for i in range(30)], start=date(2026, 9, 21))
    for opp_id in (long_id, short_id):
        DL.log_cycle_decision(conn, opp_id, "2026-09-21", "RANGE", 4.0)
    assert run_nightly_retroactive_job(conn, "2026-11-18")["prices_populated"] == 2
    rows = {r["symbol"]: r for r in conn.execute("SELECT * FROM decision_log")}
    assert rows["UP.NS"]["price_5d_later"] == 105.0 and rows["UP.NS"]["price_20d_later"] > 115.0
    assert rows["UP.NS"]["max_favorable_20d"] > 0 and rows["UP.NS"]["max_adverse_20d"] <= 0
    assert rows["DN.NS"]["max_favorable_20d"] > 0 and rows["DN.NS"]["max_adverse_20d"] <= 0   # falling price favours a SHORT
    assert rows["UP.NS"]["counterfactual_type"] == "CLEAN"


def test_a_split_artefact_in_the_window_is_not_turned_into_a_return(conn):
    ensure_trading_calendar(conn)
    opp = _opportunity(conn, "SPLIT.NS", "LONG")
    conn.execute("UPDATE opportunities SET current_state = 'WATCHING' WHERE opportunity_id = ?", (opp,))
    _store_prices(conn, "SPLIT.NS", [100.0] * 5 + [50.0] * 25, start=date(2026, 9, 21))
    DL.log_cycle_decision(conn, opp, "2026-09-21", "RANGE", 4.0)
    assert run_nightly_retroactive_job(conn, "2026-11-18")["prices_populated"] == 0
    row = conn.execute("SELECT * FROM decision_log").fetchone()
    assert row["price_5d_later"] is None and row["max_favorable_20d"] is None and row["outcome_populated_at"]


def test_a_decision_less_than_twenty_sessions_old_is_left_open(conn):
    ensure_trading_calendar(conn)
    opp = _opportunity(conn, "NEW.NS")
    _store_prices(conn, "NEW.NS", [100.0 + i for i in range(8)], start=date(2026, 11, 2))
    DL.log_cycle_decision(conn, opp, "2026-11-02", "RANGE", 4.0)
    run_nightly_retroactive_job(conn, "2026-11-18")
    row = conn.execute("SELECT * FROM decision_log").fetchone()
    assert row["price_5d_later"] is None and row["outcome_populated_at"] is None


# ── archetype_versions ──────────────────────────────────────────────────────

def test_every_archetype_gets_version_one_once_and_new_ids_from_signals_are_anchored(conn):
    added = seed_archetype_versions(conn, "2026-11-18")
    assert added == len(ARCHETYPES) == 10
    assert seed_archetype_versions(conn, "2026-11-19") == 0
    assert conn.execute("SELECT COUNT(*) FROM archetype_versions WHERE version_number = 1").fetchone()[0] == 10
    snap = conn.execute("SELECT parameter_snapshot FROM archetype_versions WHERE archetype_id = "
                        "'DNA_1A_MOMENTUM_BREAKDOWN'").fetchone()[0]
    assert '"direction": "SHORT"' in snap
    _opportunity(conn, "X.NS")
    conn.execute("UPDATE signal_births SET archetype_id = 'DNA_1A_FUTURE' ")
    assert seed_archetype_versions(conn, "2026-11-20") == 1
