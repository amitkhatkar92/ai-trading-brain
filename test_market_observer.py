"""
test_market_observer.py -- MLS Phase 1 test suite.

Covers:
    MLSConfig          -- defaults, overrides, config_hash
    MarketObserver     -- instantiation (default/custom config/custom data_dir)
    capture()          -- happy path, custom symbols, temporal contract (6 cases)
    load_snapshot()    -- existing, missing, field correctness
    list_snapshots()   -- empty, single, multiple, ordering
    statistics()       -- empty, single, aggregation, regimes, violations
    DailyMarketSnapshot -- to_dict/from_dict, get_observation, metadata flags
    MarketObservation  -- to_dict/from_dict, field invariants
    ObservationStatistics -- date range, averages, deduplication
    Storage            -- dir creation, atomic overwrite, .bak creation
    Thread safety      -- concurrent captures on different dates

Run:
    python test_market_observer.py
"""
from __future__ import annotations

import sys
import tempfile
import threading
import time
import traceback
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, List, Optional

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from models.market_data import MarketSnapshot, RegimeLabel, VolatilityLevel
from market_learning import (
    MarketObserver,
    MLSConfig,
    DailyMarketSnapshot,
    MarketObservation,
    ObservationMetadata,
    ObservationStatistics,
    TemporalContractViolation,
    MarketObserverError,
)


# ═════════════════════════════════════════════════════════════════════════════
# Minimal test framework (same pattern as ARS test suites)
# ═════════════════════════════════════════════════════════════════════════════

@dataclass
class TestResult:
    name:        str
    passed:      bool
    duration_ms: float
    detail:      str
    error:       Optional[str] = None


class TestRunner:
    def __init__(self) -> None:
        self.results: List[TestResult] = []

    def run(self, name: str, fn: Callable[[], Any]) -> None:
        t0 = time.perf_counter()
        try:
            detail = fn() or "OK"
            self.results.append(TestResult(
                name=name, passed=True,
                duration_ms=round((time.perf_counter() - t0) * 1000, 1),
                detail=str(detail),
            ))
        except AssertionError as exc:
            self.results.append(TestResult(
                name=name, passed=False,
                duration_ms=round((time.perf_counter() - t0) * 1000, 1),
                detail="ASSERTION FAILED", error=str(exc),
            ))
        except Exception as exc:
            self.results.append(TestResult(
                name=name, passed=False,
                duration_ms=round((time.perf_counter() - t0) * 1000, 1),
                detail="EXCEPTION",
                error=f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}",
            ))

    @property
    def passed(self) -> int:
        return sum(1 for r in self.results if r.passed)

    @property
    def failed(self) -> int:
        return sum(1 for r in self.results if not r.passed)


def ok(cond: bool, msg: str = "") -> None:
    if not cond:
        raise AssertionError(msg or "condition is False")


# ═════════════════════════════════════════════════════════════════════════════
# Shared fixtures
# ═════════════════════════════════════════════════════════════════════════════

_TMP: Optional[Path] = None
_COUNTER = 0

# default config for tests that use small symbol subsets
_TEST_CFG = MLSConfig(min_universe_size=1)


def get_tmp() -> Path:
    global _TMP
    if _TMP is None:
        _TMP = Path(tempfile.mkdtemp(prefix="mls_mo_test_"))
    return _TMP


def fresh_dir(tag: str = "") -> Path:
    """Return a unique subdirectory for test isolation."""
    global _COUNTER
    _COUNTER += 1
    d = get_tmp() / f"{tag}_{_COUNTER}"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _mo(tag: str = "") -> MarketObserver:
    """Create a test observer with min_universe_size=1 for small symbol lists."""
    return MarketObserver(data_dir=fresh_dir(tag), config=_TEST_CFG)


def make_snapshot(
    hour: int = 9,
    minute: int = 10,
    second: int = 0,
    regime: RegimeLabel = RegimeLabel.BULL_TREND,
    volatility: VolatilityLevel = VolatilityLevel.MEDIUM,
    vix: float = 15.0,
    breadth: float = 0.6,
    pcr: float = 0.9,
    global_score: float = 0.3,
    year: int = 2026,
    month: int = 8,
    day: int = 3,
) -> MarketSnapshot:
    return MarketSnapshot(
        timestamp=datetime(year, month, day, hour, minute, second),
        indices={},
        regime=regime,
        volatility=volatility,
        vix=vix,
        market_breadth=breadth,
        pcr=pcr,
        global_sentiment_score=global_score,
    )


# ═════════════════════════════════════════════════════════════════════════════
# Test groups
# ═════════════════════════════════════════════════════════════════════════════

def test_group_mls_config(runner: TestRunner) -> None:

    def t01_defaults():
        cfg = MLSConfig()
        ok(cfg.feature_deadline_hour == 9,   "deadline_hour default")
        ok(cfg.feature_deadline_minute == 15, "deadline_minute default")
        ok(cfg.feature_deadline_second == 0,  "deadline_second default")
        ok(cfg.min_universe_size == 10,        "min_universe_size default")
        ok(cfg.min_group_size == 30,           "min_group_size default")
        ok(cfg.min_effect_size == 0.50,        "min_effect_size default")
        ok(cfg.max_p_value == 0.05,            "max_p_value default")
        ok(cfg.snapshot_retention_days == 90,  "snapshot_retention_days default")
        return "defaults correct"

    def t02_custom_overrides():
        cfg = MLSConfig(min_group_size=50, max_p_value=0.01, snapshot_retention_days=30)
        ok(cfg.min_group_size == 50,          "custom min_group_size")
        ok(cfg.max_p_value == 0.01,           "custom max_p_value")
        ok(cfg.snapshot_retention_days == 30, "custom snapshot_retention_days")
        ok(cfg.min_effect_size == 0.50,       "non-overridden field unchanged")
        return "custom overrides correct"

    def t03_config_hash_deterministic():
        cfg1 = MLSConfig()
        cfg2 = MLSConfig()
        ok(cfg1.config_hash() == cfg2.config_hash(), "hash reproducible")
        ok(len(cfg1.config_hash()) == 16, "hash is 16 chars")
        cfg3 = MLSConfig(min_group_size=99)
        ok(cfg1.config_hash() != cfg3.config_hash(), "different configs -> different hashes")
        return f"hash={cfg1.config_hash()}"

    runner.run("T01 MLSConfig defaults",            t01_defaults)
    runner.run("T02 MLSConfig custom overrides",    t02_custom_overrides)
    runner.run("T03 MLSConfig config_hash",         t03_config_hash_deterministic)


def test_group_instantiation(runner: TestRunner) -> None:

    def t04_default_instantiation():
        mo = MarketObserver()
        ok(mo is not None, "instance created")
        ok(isinstance(mo._config, MLSConfig), "default config assigned")
        return "default instantiation OK"

    def t05_custom_config():
        cfg = MLSConfig(min_universe_size=5)
        mo  = MarketObserver(config=cfg)
        ok(mo._config.min_universe_size == 5, "custom config assigned")
        return "custom config OK"

    def t06_custom_data_dir():
        d  = fresh_dir("init")
        mo = MarketObserver(data_dir=d, config=_TEST_CFG)
        ok(mo._snapshots_dir == d / "snapshots", "snapshots_dir uses custom root")
        return f"data_dir={d}"

    runner.run("T04 MarketObserver default instantiation", t04_default_instantiation)
    runner.run("T05 MarketObserver custom config",         t05_custom_config)
    runner.run("T06 MarketObserver custom data_dir",       t06_custom_data_dir)


def test_group_capture_happy_path(runner: TestRunner) -> None:
    syms = ["RELIANCE", "TCS", "INFY"]

    def t07_returns_daily_snapshot():
        mo   = _mo("cap")
        snap = make_snapshot()
        result = mo.capture(snap, symbols=syms)
        ok(isinstance(result, DailyMarketSnapshot), "returns DailyMarketSnapshot")
        return "type correct"

    def t08_snapshot_id_format():
        mo   = _mo("cap")
        snap = make_snapshot(year=2026, month=8, day=3)
        result = mo.capture(snap, symbols=syms)
        ok(result.snapshot_id == "MLS-SNAP-20260803", f"got {result.snapshot_id}")
        return f"id={result.snapshot_id}"

    def t09_trading_date():
        mo   = _mo("cap")
        snap = make_snapshot(year=2026, month=8, day=3)
        result = mo.capture(snap, symbols=syms)
        ok(result.trading_date == "2026-08-03", f"got {result.trading_date}")
        return f"date={result.trading_date}"

    def t10_feature_timestamp():
        mo   = _mo("cap")
        snap = make_snapshot(year=2026, month=8, day=3, hour=9, minute=10, second=0)
        result = mo.capture(snap, symbols=syms)
        ok(result.feature_timestamp.startswith("2026-08-03T09:10"),
           f"got {result.feature_timestamp}")
        return f"feature_timestamp={result.feature_timestamp}"

    def t11_universe_size():
        mo   = _mo("cap")
        snap = make_snapshot()
        result = mo.capture(snap, symbols=syms)
        ok(result.universe_size == len(syms), f"expected {len(syms)}, got {result.universe_size}")
        return f"universe_size={result.universe_size}"

    def t12_observations_count():
        mo   = _mo("cap")
        snap = make_snapshot()
        result = mo.capture(snap, symbols=syms)
        ok(len(result.observations) == len(syms),
           f"expected {len(syms)} obs, got {len(result.observations)}")
        return f"observations={len(result.observations)}"

    def t13_observation_symbols():
        mo   = _mo("cap")
        snap = make_snapshot()
        result = mo.capture(snap, symbols=syms)
        obs_syms = {o.symbol for o in result.observations}
        ok(obs_syms == set(syms), f"expected {set(syms)}, got {obs_syms}")
        return f"symbols={sorted(obs_syms)}"

    def t14_observation_features_nonempty():
        mo   = _mo("cap")
        snap = make_snapshot()
        result = mo.capture(snap, symbols=syms)
        for obs in result.observations:
            ok(obs.feature_count > 0, f"{obs.symbol} has no features")
            ok(len(obs.features) == obs.feature_count,
               f"{obs.symbol}: feature_count mismatch")
        return f"feature_count={result.observations[0].feature_count}"

    def t15_persists_json_file():
        d    = fresh_dir("persist")
        mo   = MarketObserver(data_dir=d, config=_TEST_CFG)
        snap = make_snapshot(year=2026, month=8, day=3)
        mo.capture(snap, symbols=syms)
        expected = d / "snapshots" / "snapshot_2026-08-03.json"
        ok(expected.exists(), f"file not created: {expected}")
        return f"file={expected.name}"

    runner.run("T07 capture() returns DailyMarketSnapshot",   t07_returns_daily_snapshot)
    runner.run("T08 capture() snapshot_id format",            t08_snapshot_id_format)
    runner.run("T09 capture() trading_date",                   t09_trading_date)
    runner.run("T10 capture() feature_timestamp",              t10_feature_timestamp)
    runner.run("T11 capture() universe_size",                  t11_universe_size)
    runner.run("T12 capture() observations count",             t12_observations_count)
    runner.run("T13 capture() observation symbols correct",    t13_observation_symbols)
    runner.run("T14 capture() observation features non-empty", t14_observation_features_nonempty)
    runner.run("T15 capture() persists JSON file",             t15_persists_json_file)


def test_group_capture_symbols(runner: TestRunner) -> None:

    def t16_custom_two_symbols():
        mo   = _mo("sym2")
        snap = make_snapshot()
        result = mo.capture(snap, symbols=["RELIANCE", "TCS"])
        ok(result.universe_size == 2, f"got {result.universe_size}")
        return "universe_size=2"

    def t17_symbols_list_preserved():
        mo   = _mo("syml")
        snap = make_snapshot()
        syms = ["RELIANCE", "TCS", "INFY", "WIPRO"]
        result = mo.capture(snap, symbols=syms)
        ok(set(result.symbols) == set(syms), f"symbols mismatch: {result.symbols}")
        return f"symbols={sorted(result.symbols)}"

    def t18_default_universe():
        mo   = MarketObserver(data_dir=fresh_dir("universe"), config=_TEST_CFG)
        snap = make_snapshot()
        result = mo.capture(snap)  # no symbols arg -> use SYMBOL_UNIVERSE (20)
        ok(result.universe_size == 20, f"expected 20, got {result.universe_size}")
        return f"universe_size={result.universe_size}"

    runner.run("T16 capture() with 2-symbol list",     t16_custom_two_symbols)
    runner.run("T17 capture() symbols list preserved", t17_symbols_list_preserved)
    runner.run("T18 capture() default universe (20)",  t18_default_universe)


def test_group_temporal_contract(runner: TestRunner) -> None:
    syms = ["RELIANCE", "TCS"]

    def t19_deadline_exact_passes():
        mo   = MarketObserver(data_dir=fresh_dir("tc"), config=_TEST_CFG)
        snap = make_snapshot(hour=9, minute=15, second=0)
        result = mo.capture(snap, symbols=syms)
        ok(result is not None, "09:15:00 should pass")
        return "09:15:00 -> PASS"

    def t20_before_deadline_passes():
        mo   = MarketObserver(data_dir=fresh_dir("tc"), config=MLSConfig(min_universe_size=2))
        snap = make_snapshot(hour=9, minute=10)
        result = mo.capture(snap, symbols=syms)
        ok(result is not None, "09:10 should pass")
        return "09:10 -> PASS"

    def t21_one_second_before_passes():
        mo   = MarketObserver(data_dir=fresh_dir("tc"), config=MLSConfig(min_universe_size=2))
        snap = make_snapshot(hour=9, minute=14, second=59)
        result = mo.capture(snap, symbols=syms)
        ok(result is not None, "09:14:59 should pass")
        return "09:14:59 -> PASS"

    def t22_one_second_after_raises():
        mo   = MarketObserver(data_dir=fresh_dir("tc"), config=_TEST_CFG)
        snap = make_snapshot(hour=9, minute=15, second=1)
        try:
            mo.capture(snap, symbols=syms)
            raise AssertionError("expected TemporalContractViolation, got no exception")
        except TemporalContractViolation:
            return "09:15:01 -> TemporalContractViolation OK"

    def t23_09_16_raises():
        mo   = MarketObserver(data_dir=fresh_dir("tc"), config=_TEST_CFG)
        snap = make_snapshot(hour=9, minute=16)
        try:
            mo.capture(snap, symbols=syms)
            raise AssertionError("expected TemporalContractViolation, got no exception")
        except TemporalContractViolation:
            return "09:16 -> TemporalContractViolation OK"

    def t24_eod_time_raises():
        mo   = MarketObserver(data_dir=fresh_dir("tc"), config=_TEST_CFG)
        snap = make_snapshot(hour=15, minute=30)
        try:
            mo.capture(snap, symbols=syms)
            raise AssertionError("expected TemporalContractViolation, got no exception")
        except TemporalContractViolation:
            return "15:30 -> TemporalContractViolation OK"

    def t25_violation_count_increments():
        mo   = MarketObserver(data_dir=fresh_dir("tc"), config=_TEST_CFG)
        snap_bad = make_snapshot(hour=10, minute=0)
        for _ in range(3):
            try:
                mo.capture(snap_bad, symbols=syms)
            except TemporalContractViolation:
                pass
        ok(mo._violation_count == 3, f"expected 3, got {mo._violation_count}")
        return f"violation_count={mo._violation_count}"

    runner.run("T19 temporal contract: 09:15:00 passes",          t19_deadline_exact_passes)
    runner.run("T20 temporal contract: 09:10 passes",             t20_before_deadline_passes)
    runner.run("T21 temporal contract: 09:14:59 passes",          t21_one_second_before_passes)
    runner.run("T22 temporal contract: 09:15:01 raises",          t22_one_second_after_raises)
    runner.run("T23 temporal contract: 09:16 raises",             t23_09_16_raises)
    runner.run("T24 temporal contract: 15:30 raises",             t24_eod_time_raises)
    runner.run("T25 temporal contract: violation count",          t25_violation_count_increments)


def test_group_load_snapshot(runner: TestRunner) -> None:
    syms = ["RELIANCE", "TCS", "INFY"]

    def t26_load_nonexistent_returns_none():
        mo = MarketObserver(data_dir=fresh_dir("load"), config=_TEST_CFG)
        result = mo.load_snapshot("2099-01-01")
        ok(result is None, "should return None for missing date")
        return "missing -> None"

    def t27_load_after_capture():
        d  = fresh_dir("load")
        mo = MarketObserver(data_dir=d, config=_TEST_CFG)
        mo.capture(make_snapshot(year=2026, month=8, day=3), symbols=syms)
        loaded = mo.load_snapshot("2026-08-03")
        ok(loaded is not None, "should load captured snapshot")
        ok(isinstance(loaded, DailyMarketSnapshot), "wrong type")
        return "loaded DailyMarketSnapshot"

    def t28_loaded_trading_date():
        d  = fresh_dir("load")
        mo = MarketObserver(data_dir=d, config=_TEST_CFG)
        mo.capture(make_snapshot(year=2026, month=8, day=4), symbols=syms)
        loaded = mo.load_snapshot("2026-08-04")
        ok(loaded.trading_date == "2026-08-04", f"got {loaded.trading_date}")
        return f"trading_date={loaded.trading_date}"

    def t29_loaded_universe_size():
        d  = fresh_dir("load")
        mo = MarketObserver(data_dir=d, config=_TEST_CFG)
        mo.capture(make_snapshot(year=2026, month=8, day=5), symbols=syms)
        loaded = mo.load_snapshot("2026-08-05")
        ok(loaded.universe_size == len(syms),
           f"expected {len(syms)}, got {loaded.universe_size}")
        return f"universe_size={loaded.universe_size}"

    def t30_loaded_regime():
        d  = fresh_dir("load")
        mo = MarketObserver(data_dir=d, config=_TEST_CFG)
        snap = make_snapshot(year=2026, month=8, day=6, regime=RegimeLabel.BEAR_MARKET)
        mo.capture(snap, symbols=syms)
        loaded = mo.load_snapshot("2026-08-06")
        ok(loaded.regime == "bear_market", f"got {loaded.regime}")
        return f"regime={loaded.regime}"

    runner.run("T26 load_snapshot() non-existent -> None",   t26_load_nonexistent_returns_none)
    runner.run("T27 load_snapshot() after capture",          t27_load_after_capture)
    runner.run("T28 load_snapshot() trading_date correct",   t28_loaded_trading_date)
    runner.run("T29 load_snapshot() universe_size correct",  t29_loaded_universe_size)
    runner.run("T30 load_snapshot() regime correct",         t30_loaded_regime)


def test_group_list_snapshots(runner: TestRunner) -> None:
    syms = ["RELIANCE", "TCS"]

    def t31_empty_store():
        mo = MarketObserver(data_dir=fresh_dir("list"), config=_TEST_CFG)
        ok(mo.list_snapshots() == [], "empty store should return []")
        return "empty -> []"

    def t32_single_snapshot():
        d  = fresh_dir("list")
        mo = MarketObserver(data_dir=d, config=_TEST_CFG)
        mo.capture(make_snapshot(year=2026, month=8, day=3), symbols=syms)
        dates = mo.list_snapshots()
        ok(dates == ["2026-08-03"], f"got {dates}")
        return f"dates={dates}"

    def t33_two_snapshots():
        d  = fresh_dir("list")
        mo = MarketObserver(data_dir=d, config=_TEST_CFG)
        mo.capture(make_snapshot(year=2026, month=8, day=3), symbols=syms)
        mo.capture(make_snapshot(year=2026, month=8, day=4), symbols=syms)
        dates = mo.list_snapshots()
        ok(len(dates) == 2, f"expected 2, got {len(dates)}")
        ok("2026-08-03" in dates, "date 03 missing")
        ok("2026-08-04" in dates, "date 04 missing")
        return f"dates={dates}"

    def t34_dates_sorted_ascending():
        d  = fresh_dir("list")
        mo = MarketObserver(data_dir=d, config=_TEST_CFG)
        mo.capture(make_snapshot(year=2026, month=8, day=5), symbols=syms)
        mo.capture(make_snapshot(year=2026, month=8, day=3), symbols=syms)
        mo.capture(make_snapshot(year=2026, month=8, day=4), symbols=syms)
        dates = mo.list_snapshots()
        ok(dates == sorted(dates), f"dates not sorted: {dates}")
        return f"sorted={dates}"

    def t35_only_json_files_listed():
        d  = fresh_dir("list")
        mo = MarketObserver(data_dir=d, config=_TEST_CFG)
        mo._ensure_dirs()
        # plant a non-snapshot file -- should be ignored
        (mo._snapshots_dir / "other_file.json").write_text("{}")
        (mo._snapshots_dir / "snapshot_notes.txt").write_text("not json")
        mo.capture(make_snapshot(year=2026, month=8, day=3), symbols=syms)
        dates = mo.list_snapshots()
        ok(all("-" in d and len(d) == 10 for d in dates),
           f"unexpected entries: {dates}")
        return f"dates={dates}"

    runner.run("T31 list_snapshots() empty store",         t31_empty_store)
    runner.run("T32 list_snapshots() single snapshot",     t32_single_snapshot)
    runner.run("T33 list_snapshots() two snapshots",       t33_two_snapshots)
    runner.run("T34 list_snapshots() sorted ascending",    t34_dates_sorted_ascending)
    runner.run("T35 list_snapshots() ignores non-snapshot files", t35_only_json_files_listed)


def test_group_statistics(runner: TestRunner) -> None:
    syms = ["RELIANCE", "TCS", "INFY"]

    def t36_empty_store_zeros():
        mo   = _mo("stats")
        stat = mo.statistics()
        ok(isinstance(stat, ObservationStatistics), "wrong type")
        ok(stat.total_snapshots == 0,     "total_snapshots should be 0")
        ok(stat.date_range_start is None, "date_range_start should be None")
        ok(stat.date_range_end is None,   "date_range_end should be None")
        ok(stat.regimes_observed == [],   "regimes should be empty")
        return "empty stats correct"

    def t37_after_one_capture():
        mo = _mo("stats")
        mo.capture(make_snapshot(year=2026, month=8, day=3), symbols=syms)
        stat = mo.statistics()
        ok(stat.total_snapshots == 1,       "total_snapshots should be 1")
        ok(stat.total_observations == len(syms), f"expected {len(syms)}, got {stat.total_observations}")
        ok(stat.avg_universe_size == float(len(syms)), f"avg wrong: {stat.avg_universe_size}")
        return f"total_snapshots=1, avg_universe_size={stat.avg_universe_size}"

    def t38_avg_universe_size_aggregated():
        mo = _mo("stats")
        # day1: 3 symbols, day2: 2 symbols
        mo.capture(make_snapshot(year=2026, month=8, day=3), symbols=["RELIANCE", "TCS", "INFY"])
        mo.capture(make_snapshot(year=2026, month=8, day=4), symbols=["RELIANCE", "TCS"])
        stat = mo.statistics()
        ok(stat.total_snapshots == 2,    "total_snapshots should be 2")
        ok(stat.total_observations == 5, f"expected 5 total obs, got {stat.total_observations}")
        ok(stat.avg_universe_size == 2.5, f"expected 2.5, got {stat.avg_universe_size}")
        return f"avg_universe_size={stat.avg_universe_size}"

    def t39_regimes_observed():
        mo = _mo("stats")
        mo.capture(make_snapshot(year=2026, month=8, day=3, regime=RegimeLabel.BULL_TREND), symbols=syms)
        mo.capture(make_snapshot(year=2026, month=8, day=4, regime=RegimeLabel.BEAR_MARKET), symbols=syms)
        stat = mo.statistics()
        ok("bull_trend" in stat.regimes_observed, f"got {stat.regimes_observed}")
        ok("bear_market" in stat.regimes_observed, f"got {stat.regimes_observed}")
        return f"regimes={stat.regimes_observed}"

    def t40_violations_tracked():
        mo   = _mo("stats")
        snap_bad = make_snapshot(hour=10, minute=0)
        for _ in range(2):
            try:
                mo.capture(snap_bad, symbols=syms)
            except TemporalContractViolation:
                pass
        stat = mo.statistics()
        ok(stat.temporal_violations_detected == 2,
           f"expected 2, got {stat.temporal_violations_detected}")
        return f"violations={stat.temporal_violations_detected}"

    runner.run("T36 statistics() empty store",              t36_empty_store_zeros)
    runner.run("T37 statistics() after one capture",        t37_after_one_capture)
    runner.run("T38 statistics() avg_universe_size",        t38_avg_universe_size_aggregated)
    runner.run("T39 statistics() regimes_observed",         t39_regimes_observed)
    runner.run("T40 statistics() violations tracked",       t40_violations_tracked)


def test_group_daily_snapshot_model(runner: TestRunner) -> None:
    syms = ["RELIANCE", "TCS", "INFY"]

    def _get_snap() -> DailyMarketSnapshot:
        mo = _mo("model")
        return mo.capture(make_snapshot(year=2026, month=8, day=3), symbols=syms)

    def t41_to_dict_keys():
        s = _get_snap()
        d = s.to_dict()
        required = {
            "snapshot_id", "trading_date", "feature_timestamp", "regime",
            "volatility", "vix", "pcr", "breadth", "global_bias",
            "universe_size", "symbols", "observations", "metadata", "created_at",
        }
        for k in required:
            ok(k in d, f"missing key: {k}")
        return f"keys={sorted(d.keys())}"

    def t42_from_dict_round_trip():
        s1  = _get_snap()
        d   = s1.to_dict()
        s2  = DailyMarketSnapshot.from_dict(d)
        ok(s2.snapshot_id   == s1.snapshot_id,   "snapshot_id mismatch")
        ok(s2.trading_date  == s1.trading_date,  "trading_date mismatch")
        ok(s2.universe_size == s1.universe_size, "universe_size mismatch")
        ok(s2.regime        == s1.regime,        "regime mismatch")
        ok(len(s2.observations) == len(s1.observations), "observations count mismatch")
        return "round-trip OK"

    def t43_get_observation_known():
        s   = _get_snap()
        obs = s.get_observation("RELIANCE")
        ok(obs is not None, "RELIANCE observation should exist")
        ok(obs.symbol == "RELIANCE", "wrong symbol")
        return f"get_observation(RELIANCE) = {obs.symbol}"

    def t44_get_observation_unknown():
        s   = _get_snap()
        obs = s.get_observation("UNKNOWN_SYMBOL_XYZ")
        ok(obs is None, "unknown symbol should return None")
        return "unknown -> None"

    def t45_metadata_contract_verified():
        s = _get_snap()
        ok(s.metadata.temporal_contract_verified is True,
           "temporal_contract_verified should be True")
        return "temporal_contract_verified=True"

    def t46_metadata_config_hash():
        s = _get_snap()
        ok(len(s.metadata.mls_config_hash) == 16, "mls_config_hash should be 16 chars")
        ok(s.metadata.mls_config_hash != "", "mls_config_hash should not be empty")
        return f"hash={s.metadata.mls_config_hash}"

    def t47_metadata_warnings_list():
        s = _get_snap()
        ok(isinstance(s.metadata.warnings, list), "warnings should be a list")
        return f"warnings={s.metadata.warnings}"

    def t48_metadata_run_id_format():
        s = _get_snap()
        ok(s.metadata.run_id.startswith("MLS-OBS-20260803"),
           f"run_id format wrong: {s.metadata.run_id}")
        return f"run_id={s.metadata.run_id}"

    runner.run("T41 DailyMarketSnapshot.to_dict() keys",       t41_to_dict_keys)
    runner.run("T42 DailyMarketSnapshot round-trip",           t42_from_dict_round_trip)
    runner.run("T43 get_observation() known symbol",           t43_get_observation_known)
    runner.run("T44 get_observation() unknown symbol -> None",  t44_get_observation_unknown)
    runner.run("T45 metadata.temporal_contract_verified",      t45_metadata_contract_verified)
    runner.run("T46 metadata.mls_config_hash",                 t46_metadata_config_hash)
    runner.run("T47 metadata.warnings is list",                t47_metadata_warnings_list)
    runner.run("T48 metadata.run_id format",                   t48_metadata_run_id_format)


def test_group_market_observation_model(runner: TestRunner) -> None:
    syms = ["RELIANCE", "TCS"]

    def _get_obs() -> MarketObservation:
        mo = _mo("obs")
        snap_result = mo.capture(make_snapshot(), symbols=syms)
        return snap_result.observations[0]

    def t49_to_dict_keys():
        obs = _get_obs()
        d   = obs.to_dict()
        for k in ("symbol", "feature_timestamp", "features", "feature_count"):
            ok(k in d, f"missing key: {k}")
        return f"keys={sorted(d.keys())}"

    def t50_round_trip():
        obs1 = _get_obs()
        d    = obs1.to_dict()
        obs2 = MarketObservation.from_dict(d)
        ok(obs2.symbol        == obs1.symbol,        "symbol mismatch")
        ok(obs2.feature_count == obs1.feature_count, "feature_count mismatch")
        ok(obs2.features      == obs1.features,      "features mismatch")
        return "round-trip OK"

    def t51_feature_count_invariant():
        obs = _get_obs()
        ok(obs.feature_count == len(obs.features),
           f"feature_count={obs.feature_count}, len(features)={len(obs.features)}")
        return f"feature_count={obs.feature_count}"

    def t52_feature_timestamp_matches_capture():
        mo   = _mo("obs")
        snap = make_snapshot(year=2026, month=8, day=3, hour=9, minute=12)
        result = mo.capture(snap, symbols=syms)
        for obs in result.observations:
            ok(obs.feature_timestamp.startswith("2026-08-03T09:12"),
               f"wrong feature_timestamp: {obs.feature_timestamp}")
        return f"feature_timestamp={result.observations[0].feature_timestamp}"

    def t53_features_are_floats():
        obs = _get_obs()
        for k, v in obs.features.items():
            ok(isinstance(v, float), f"feature {k} is not float: {type(v)}")
        return f"all {obs.feature_count} features are float"

    runner.run("T49 MarketObservation.to_dict() keys",           t49_to_dict_keys)
    runner.run("T50 MarketObservation round-trip",               t50_round_trip)
    runner.run("T51 MarketObservation feature_count invariant",  t51_feature_count_invariant)
    runner.run("T52 MarketObservation feature_timestamp",        t52_feature_timestamp_matches_capture)
    runner.run("T53 MarketObservation features are float",       t53_features_are_floats)


def test_group_storage(runner: TestRunner) -> None:
    syms = ["RELIANCE", "TCS"]

    def t54_dir_created_if_missing():
        d  = get_tmp() / f"new_dir_{time.time_ns()}"
        mo = MarketObserver(data_dir=d, config=_TEST_CFG)
        ok(not d.exists(), "dir should not exist before capture")
        mo.capture(make_snapshot(), symbols=syms)
        ok((d / "snapshots").exists(), "snapshots dir should be created")
        return "dir created on first capture"

    def t55_overwrite_same_date():
        d  = fresh_dir("overwrite")
        mo = MarketObserver(data_dir=d, config=_TEST_CFG)
        snap = make_snapshot(year=2026, month=8, day=3)
        r1 = mo.capture(snap, symbols=["RELIANCE"])
        r2 = mo.capture(snap, symbols=["RELIANCE", "TCS"])  # 2nd capture same date
        loaded = mo.load_snapshot("2026-08-03")
        ok(loaded.universe_size == 2, f"should be overwritten with 2, got {loaded.universe_size}")
        return "overwrite replaced old snapshot"

    def t56_bak_created_on_overwrite():
        d  = fresh_dir("bak")
        mo = MarketObserver(data_dir=d, config=_TEST_CFG)
        snap = make_snapshot(year=2026, month=8, day=3)
        mo.capture(snap, symbols=["RELIANCE"])
        mo.capture(snap, symbols=["RELIANCE", "TCS"])  # 2nd write -> .bak
        bak = d / "snapshots" / "snapshot_2026-08-03.bak"
        ok(bak.exists(), ".bak should be created on overwrite")
        return ".bak created"

    def t57_json_valid():
        d  = fresh_dir("json")
        mo = MarketObserver(data_dir=d, config=_TEST_CFG)
        mo.capture(make_snapshot(year=2026, month=8, day=3), symbols=syms)
        path = d / "snapshots" / "snapshot_2026-08-03.json"
        import json as _json
        with path.open() as fh:
            data = _json.load(fh)
        ok("snapshot_id" in data, "JSON missing snapshot_id")
        ok("observations" in data, "JSON missing observations")
        return f"JSON valid, {len(data['observations'])} observations"

    runner.run("T54 storage dir created if missing",   t54_dir_created_if_missing)
    runner.run("T55 overwrite same date",               t55_overwrite_same_date)
    runner.run("T56 .bak created on overwrite",        t56_bak_created_on_overwrite)
    runner.run("T57 persisted JSON is valid",           t57_json_valid)


def test_group_statistics_detail(runner: TestRunner) -> None:
    syms = ["RELIANCE", "TCS"]

    def t58_date_range_correct():
        d  = fresh_dir("statdet")
        mo = MarketObserver(data_dir=d, config=_TEST_CFG)
        mo.capture(make_snapshot(year=2026, month=7, day=28), symbols=syms)
        mo.capture(make_snapshot(year=2026, month=8, day=3),  symbols=syms)
        stat = mo.statistics()
        ok(stat.date_range_start == "2026-07-28", f"got {stat.date_range_start}")
        ok(stat.date_range_end   == "2026-08-03", f"got {stat.date_range_end}")
        return f"range={stat.date_range_start} -> {stat.date_range_end}"

    def t59_regimes_deduplicated():
        d  = fresh_dir("statdet")
        mo = MarketObserver(data_dir=d, config=_TEST_CFG)
        for day in (3, 4, 5):
            mo.capture(make_snapshot(year=2026, month=8, day=day, regime=RegimeLabel.BULL_TREND),
                       symbols=syms)
        stat = mo.statistics()
        ok(len(stat.regimes_observed) == 1, f"expected 1, got {stat.regimes_observed}")
        ok("bull_trend" in stat.regimes_observed, "bull_trend missing")
        return f"regimes={stat.regimes_observed}"

    def t60_avg_feature_count():
        d  = fresh_dir("statdet")
        mo = MarketObserver(data_dir=d, config=_TEST_CFG)
        mo.capture(make_snapshot(year=2026, month=8, day=3), symbols=syms)
        stat = mo.statistics()
        ok(stat.avg_feature_count > 0, f"avg_feature_count should be > 0, got {stat.avg_feature_count}")
        return f"avg_feature_count={stat.avg_feature_count}"

    runner.run("T58 statistics() date_range correct",       t58_date_range_correct)
    runner.run("T59 statistics() regimes deduplicated",     t59_regimes_deduplicated)
    runner.run("T60 statistics() avg_feature_count > 0",   t60_avg_feature_count)


def test_group_thread_safety(runner: TestRunner) -> None:

    def t61_concurrent_captures_no_corruption():
        mo   = _mo("thread")
        syms = ["RELIANCE", "TCS"]
        errors: list[str] = []

        def do_capture(day: int) -> None:
            try:
                mo.capture(
                    make_snapshot(year=2026, month=8, day=day, hour=9, minute=5),
                    symbols=syms,
                )
            except Exception as exc:
                errors.append(f"day={day}: {exc}")

        threads = [threading.Thread(target=do_capture, args=(d_,)) for d_ in range(1, 11)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        ok(len(errors) == 0, f"concurrent errors: {errors}")
        dates = mo.list_snapshots()
        ok(len(dates) == 10, f"expected 10 snapshots, got {len(dates)}")
        return f"concurrent: 10/10 succeeded, snapshots={len(dates)}"

    runner.run("T61 thread safety: concurrent captures", t61_concurrent_captures_no_corruption)


# ═════════════════════════════════════════════════════════════════════════════
# Main
# ═════════════════════════════════════════════════════════════════════════════

def main() -> None:
    runner = TestRunner()

    test_group_mls_config(runner)
    test_group_instantiation(runner)
    test_group_capture_happy_path(runner)
    test_group_capture_symbols(runner)
    test_group_temporal_contract(runner)
    test_group_load_snapshot(runner)
    test_group_list_snapshots(runner)
    test_group_statistics(runner)
    test_group_daily_snapshot_model(runner)
    test_group_market_observation_model(runner)
    test_group_storage(runner)
    test_group_statistics_detail(runner)
    test_group_thread_safety(runner)

    # ── Report ───────────────────────────────────────────────────────────
    print("\n" + "=" * 72)
    print("MLS Phase 1 -- MarketObserver Test Report")
    print("=" * 72)

    width = max(len(r.name) for r in runner.results) + 2
    for r in runner.results:
        status = "PASS" if r.passed else "FAIL"
        print(f"  [{status}] {r.name:<{width}} {r.duration_ms:6.1f}ms  {r.detail}")
        if r.error:
            for line in r.error.splitlines():
                print(f"         {line}")

    print("-" * 72)
    print(f"  Result:  {runner.passed}/{len(runner.results)} passed, {runner.failed} failed")
    print("=" * 72 + "\n")

    if runner.failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
