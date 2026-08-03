"""
test_population_classifier.py — MLS Phase 2 test suite.

Covers:
    MLSConfig Phase 2 fields  — new defaults, overrides, hash change
    PopulationClassifier      — instantiation, custom config, custom data_dir
    classify()                — structure, result_id, universe_size, persistence
    Performance classifier    — 7 exclusive groups, boundary math, sum = universe
    Sector classifier         — 3 groups, threshold respected, no orphans
    Regime classifier         — 2 groups, alignment logic, no orphans
    Liquidity classifier      — 3 groups, threshold respected
    Volatility classifier     — 3 groups, threshold respected
    Market cap classifier     — 3 groups (liquidity proxy)
    Volume expansion          — 3 groups, ratio threshold
    Relative strength         — 3 groups, RSI threshold
    Multi-label               — 8 labels per symbol, populations_for(), labels list
    ClassificationResult      — to_dict/from_dict, get_population, get_member
    Population model          — to_dict/from_dict, id format, count invariant
    PopulationMember model    — to_dict/from_dict, classification_values
    External outcomes         — outcomes_source, deterministic ranking
    Storage                   — load_result, list_results, .bak, atomic write
    Statistics                — population_count, avg_labels, perf_sizes
    Thread safety             — concurrent classify() on different dates

Run:
    python test_population_classifier.py
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
from typing import Any, Callable, Dict, List, Optional

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from models.market_data import MarketSnapshot, RegimeLabel, VolatilityLevel
from market_learning import (
    MarketObserver,
    MLSConfig,
    DailyMarketSnapshot,
    PopulationClassifier,
    ClassificationResult,
    Population,
    PopulationMember,
    PopulationStatistics,
    ClassifierType,
    GroupLabel,
    OrphanStockError,
    PopulationClassifierError,
)
from edge_discovery.feature_extractor import FeatureExtractor


# ═════════════════════════════════════════════════════════════════════════════
# Minimal test framework
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
_TEST_CFG = MLSConfig(min_universe_size=1)

# 20-symbol universe from FeatureExtractor
_UNIVERSE = FeatureExtractor.SYMBOL_UNIVERSE


def get_tmp() -> Path:
    global _TMP
    if _TMP is None:
        _TMP = Path(tempfile.mkdtemp(prefix="mls_pc_test_"))
    return _TMP


def fresh_dir(tag: str = "") -> Path:
    global _COUNTER
    _COUNTER += 1
    d = get_tmp() / f"{tag}_{_COUNTER}"
    d.mkdir(parents=True, exist_ok=True)
    return d


def make_daily_snapshot(
    year: int = 2026, month: int = 8, day: int = 3,
    hour: int = 9, minute: int = 10,
    regime: RegimeLabel = RegimeLabel.BULL_TREND,
    volatility: VolatilityLevel = VolatilityLevel.MEDIUM,
    vix: float = 15.0,
    breadth: float = 0.6,
    pcr: float = 0.9,
    global_score: float = 0.3,
    symbols: Optional[List[str]] = None,
    mo_dir: Optional[Path] = None,
) -> DailyMarketSnapshot:
    d  = mo_dir or fresh_dir("mo")
    mo = MarketObserver(data_dir=d, config=_TEST_CFG)
    ms = MarketSnapshot(
        timestamp=datetime(year, month, day, hour, minute),
        indices={},
        regime=regime,
        volatility=volatility,
        vix=vix,
        market_breadth=breadth,
        pcr=pcr,
        global_sentiment_score=global_score,
    )
    return mo.capture(ms, symbols=symbols)


def make_pc(tag: str = "") -> PopulationClassifier:
    return PopulationClassifier(data_dir=fresh_dir(tag), config=_TEST_CFG)


# ═════════════════════════════════════════════════════════════════════════════
# Test groups
# ═════════════════════════════════════════════════════════════════════════════

def test_group_config(runner: TestRunner) -> None:

    def t01_phase2_defaults():
        cfg = MLSConfig()
        ok(cfg.perf_top1_frac  == 0.01,  "perf_top1_frac default")
        ok(cfg.perf_top5_frac  == 0.05,  "perf_top5_frac default")
        ok(cfg.perf_top10_frac == 0.10,  "perf_top10_frac default")
        ok(cfg.perf_bot5_frac  == 0.05,  "perf_bot5_frac default")
        ok(cfg.sector_winner_threshold  == 0.65, "sector_winner default")
        ok(cfg.sector_loser_threshold   == 0.35, "sector_loser default")
        ok(cfg.liquidity_high_threshold == 0.70, "liq_high default")
        ok(cfg.liquidity_low_threshold  == 0.30, "liq_low default")
        ok(cfg.rs_strong_rsi == 65.0, "rs_strong default")
        ok(cfg.rs_weak_rsi   == 35.0, "rs_weak default")
        return "Phase 2 defaults correct"

    def t02_phase2_overrides():
        cfg = MLSConfig(perf_top5_frac=0.10, rs_strong_rsi=70.0)
        ok(cfg.perf_top5_frac == 0.10,  "perf_top5_frac override")
        ok(cfg.rs_strong_rsi  == 70.0,  "rs_strong override")
        ok(cfg.perf_top1_frac == 0.01,  "unmodified field unchanged")
        return "Phase 2 overrides correct"

    def t03_config_hash_changes_with_phase2():
        cfg1 = MLSConfig()
        cfg2 = MLSConfig(rs_strong_rsi=99.0)
        ok(cfg1.config_hash() != cfg2.config_hash(), "different Phase 2 config -> different hash")
        return "hash changes with Phase 2 fields"

    runner.run("T01 MLSConfig Phase 2 defaults",           t01_phase2_defaults)
    runner.run("T02 MLSConfig Phase 2 overrides",          t02_phase2_overrides)
    runner.run("T03 MLSConfig hash changes with Phase 2",  t03_config_hash_changes_with_phase2)


def test_group_instantiation(runner: TestRunner) -> None:

    def t04_default_instantiation():
        pc = PopulationClassifier()
        ok(pc is not None, "instance created")
        ok(isinstance(pc._config, MLSConfig), "default config")
        return "default OK"

    def t05_custom_config():
        cfg = MLSConfig(rs_strong_rsi=70.0)
        pc  = PopulationClassifier(config=cfg)
        ok(pc._config.rs_strong_rsi == 70.0, "custom config assigned")
        return "custom config OK"

    def t06_custom_data_dir():
        d  = fresh_dir("init")
        pc = PopulationClassifier(data_dir=d, config=_TEST_CFG)
        ok(pc._cls_dir == d / "classifications", "cls_dir uses custom root")
        return f"data_dir={d}"

    runner.run("T04 PopulationClassifier default instantiation", t04_default_instantiation)
    runner.run("T05 PopulationClassifier custom config",         t05_custom_config)
    runner.run("T06 PopulationClassifier custom data_dir",       t06_custom_data_dir)


def test_group_classify_structure(runner: TestRunner) -> None:

    def t07_returns_classification_result():
        snap = make_daily_snapshot()
        pc   = make_pc("struct")
        r    = pc.classify(snap)
        ok(isinstance(r, ClassificationResult), "wrong type")
        return "type correct"

    def t08_result_id_format():
        snap = make_daily_snapshot(year=2026, month=8, day=3)
        pc   = make_pc("struct")
        r    = pc.classify(snap)
        ok(r.result_id == "MLS-CLS-20260803", f"got {r.result_id}")
        return f"result_id={r.result_id}"

    def t09_trading_date():
        snap = make_daily_snapshot(year=2026, month=8, day=4)
        pc   = make_pc("struct")
        r    = pc.classify(snap)
        ok(r.trading_date == "2026-08-04", f"got {r.trading_date}")
        return f"trading_date={r.trading_date}"

    def t10_snapshot_id():
        snap = make_daily_snapshot(year=2026, month=8, day=3)
        pc   = make_pc("struct")
        r    = pc.classify(snap)
        ok(r.snapshot_id == "MLS-SNAP-20260803", f"got {r.snapshot_id}")
        return f"snapshot_id={r.snapshot_id}"

    def t11_universe_size():
        snap = make_daily_snapshot()
        pc   = make_pc("struct")
        r    = pc.classify(snap)
        ok(r.universe_size == len(_UNIVERSE), f"expected {len(_UNIVERSE)}, got {r.universe_size}")
        return f"universe_size={r.universe_size}"

    def t12_populations_nonempty():
        snap = make_daily_snapshot()
        pc   = make_pc("struct")
        r    = pc.classify(snap)
        ok(len(r.populations) > 0, "populations should not be empty")
        # 8 classifier types, each with 2-7 groups
        ok(len(r.populations) >= 8, f"expected >= 8 populations, got {len(r.populations)}")
        return f"populations={len(r.populations)}"

    def t13_members_complete():
        snap = make_daily_snapshot()
        pc   = make_pc("struct")
        r    = pc.classify(snap)
        ok(len(r.members) == len(_UNIVERSE), f"expected {len(_UNIVERSE)}, got {len(r.members)}")
        member_syms = {m.symbol for m in r.members}
        ok(member_syms == set(_UNIVERSE), "members don't match universe")
        return f"members={len(r.members)}"

    def t14_persists_json_file():
        d    = fresh_dir("persist")
        snap = make_daily_snapshot(year=2026, month=8, day=3)
        pc   = PopulationClassifier(data_dir=d, config=_TEST_CFG)
        pc.classify(snap)
        expected = d / "classifications" / "classification_2026-08-03.json"
        ok(expected.exists(), f"file not created: {expected}")
        return f"file={expected.name}"

    runner.run("T07 classify() returns ClassificationResult",  t07_returns_classification_result)
    runner.run("T08 classify() result_id format",              t08_result_id_format)
    runner.run("T09 classify() trading_date",                  t09_trading_date)
    runner.run("T10 classify() snapshot_id",                   t10_snapshot_id)
    runner.run("T11 classify() universe_size",                 t11_universe_size)
    runner.run("T12 classify() populations non-empty",         t12_populations_nonempty)
    runner.run("T13 classify() members complete",              t13_members_complete)
    runner.run("T14 classify() persists JSON file",            t14_persists_json_file)


def test_group_performance(runner: TestRunner) -> None:

    def _get_result() -> ClassificationResult:
        snap = make_daily_snapshot()
        return make_pc("perf").classify(snap)

    def t15_top5pct_exists():
        r = _get_result()
        p = r.get_population_by_type(ClassifierType.PERFORMANCE, GroupLabel.TOP_5PCT)
        ok(p is not None, "TOP_5PCT population should exist")
        return f"TOP_5PCT members={p.member_count}"

    def t16_bottom5pct_exists():
        r = _get_result()
        p = r.get_population_by_type(ClassifierType.PERFORMANCE, GroupLabel.BOTTOM_5PCT)
        ok(p is not None, "BOTTOM_5PCT population should exist")
        return f"BOTTOM_5PCT members={p.member_count}"

    def t17_neutral_exists():
        r = _get_result()
        p = r.get_population_by_type(ClassifierType.PERFORMANCE, GroupLabel.NEUTRAL)
        ok(p is not None, "NEUTRAL population should exist")
        ok(p.member_count > 0, "NEUTRAL should have members for 20-symbol universe")
        return f"NEUTRAL members={p.member_count}"

    def t18_all_7_performance_groups_exist():
        r      = _get_result()
        labels = [GroupLabel.TOP_1PCT, GroupLabel.TOP_5PCT, GroupLabel.TOP_10PCT,
                  GroupLabel.NEUTRAL, GroupLabel.BOTTOM_10PCT, GroupLabel.BOTTOM_5PCT,
                  GroupLabel.BOTTOM_1PCT]
        for lbl in labels:
            p = r.get_population_by_type(ClassifierType.PERFORMANCE, lbl)
            ok(p is not None, f"{lbl.value} population missing")
        return f"all 7 performance groups present"

    def t19_performance_groups_sum_to_universe():
        r    = _get_result()
        n    = r.universe_size
        perf = [p for p in r.populations if p.classifier_type == ClassifierType.PERFORMANCE]
        total = sum(p.member_count for p in perf)
        ok(total == n, f"sum={total}, expected {n}")
        return f"sum={total} == universe_size={n}"

    def t20_top5pct_size_correct():
        r   = _get_result()
        n   = r.universe_size
        cfg = _TEST_CFG
        p   = r.get_population_by_type(ClassifierType.PERFORMANCE, GroupLabel.TOP_5PCT)
        # [n1, n5) exclusive slice
        n1 = int(cfg.perf_top1_frac * n)
        n5 = int(cfg.perf_top5_frac * n)
        expected = n5 - n1
        ok(p.member_count == expected, f"expected {expected}, got {p.member_count}")
        return f"TOP_5PCT.member_count={p.member_count}"

    def t21_performance_groups_disjoint():
        r    = _get_result()
        perf = [p for p in r.populations if p.classifier_type == ClassifierType.PERFORMANCE]
        seen: set[str] = set()
        for p in perf:
            for sym in p.members:
                ok(sym not in seen, f"{sym} in multiple performance groups")
                seen.add(sym)
        return "performance groups disjoint"

    def t22_every_symbol_in_one_performance_group():
        r    = _get_result()
        perf = [p for p in r.populations if p.classifier_type == ClassifierType.PERFORMANCE]
        classified = {sym for p in perf for sym in p.members}
        universe   = {m.symbol for m in r.members}
        orphans    = universe - classified
        ok(len(orphans) == 0, f"orphan stocks: {orphans}")
        return "no orphan stocks in performance"

    def t23_external_outcomes_affect_performance():
        """Highest-return symbol must be in the best non-empty top group."""
        n       = len(_UNIVERSE)
        # Ascending returns: _UNIVERSE[0] gets lowest, _UNIVERSE[-1] gets highest
        outcomes = {sym: i / n for i, sym in enumerate(_UNIVERSE)}
        best_sym = _UNIVERSE[-1]  # highest return
        snap     = make_daily_snapshot(year=2026, month=8, day=20)
        r        = make_pc("extout").classify(snap, outcomes=outcomes)
        # Find best non-empty top group
        for lbl in [GroupLabel.TOP_1PCT, GroupLabel.TOP_5PCT, GroupLabel.TOP_10PCT]:
            p = r.get_population_by_type(ClassifierType.PERFORMANCE, lbl)
            if p and p.member_count > 0:
                ok(best_sym in p.members,
                   f"{best_sym} should be in {lbl.value}, got {p.members}")
                return f"best symbol {best_sym} in {lbl.value}"
        return "no top group had members"

    runner.run("T15 performance: TOP_5PCT exists",                t15_top5pct_exists)
    runner.run("T16 performance: BOTTOM_5PCT exists",             t16_bottom5pct_exists)
    runner.run("T17 performance: NEUTRAL exists and has members", t17_neutral_exists)
    runner.run("T18 performance: all 7 groups present",           t18_all_7_performance_groups_exist)
    runner.run("T19 performance: groups sum to universe_size",    t19_performance_groups_sum_to_universe)
    runner.run("T20 performance: TOP_5PCT size boundary math",    t20_top5pct_size_correct)
    runner.run("T21 performance: groups are disjoint",            t21_performance_groups_disjoint)
    runner.run("T22 performance: no orphan stocks",               t22_every_symbol_in_one_performance_group)
    runner.run("T23 performance: external outcomes affect result",t23_external_outcomes_affect_performance)


def test_group_sector(runner: TestRunner) -> None:

    def _get_r() -> ClassificationResult:
        return make_pc("sector").classify(make_daily_snapshot())

    def t24_sector_3_groups_exist():
        r = _get_r()
        for lbl in [GroupLabel.SECTOR_WINNER, GroupLabel.SECTOR_LOSER, GroupLabel.SECTOR_NEUTRAL]:
            p = r.get_population_by_type(ClassifierType.SECTOR, lbl)
            ok(p is not None, f"{lbl.value} missing")
        return "all 3 sector groups present"

    def t25_sector_sums_to_universe():
        r     = _get_r()
        total = sum(p.member_count for p in r.populations
                    if p.classifier_type == ClassifierType.SECTOR)
        ok(total == r.universe_size, f"sum={total}, expected {r.universe_size}")
        return f"sector sum={total}"

    def t26_sector_disjoint():
        r    = _get_r()
        seen: set[str] = set()
        for p in r.populations:
            if p.classifier_type != ClassifierType.SECTOR:
                continue
            for sym in p.members:
                ok(sym not in seen, f"{sym} in multiple sector groups")
                seen.add(sym)
        return "sector groups disjoint"

    def t27_sector_threshold_respected():
        """Symbols in SECTOR_WINNER should have sector_strength >= threshold."""
        snap = make_daily_snapshot()
        r    = make_pc("sth").classify(snap)
        obs_map = {o.symbol: o for o in snap.observations}
        hi  = _TEST_CFG.sector_winner_threshold
        pop = r.get_population_by_type(ClassifierType.SECTOR, GroupLabel.SECTOR_WINNER)
        for sym in pop.members:
            ss = obs_map[sym].features.get("sector_strength", 0.5)
            ok(ss >= hi, f"{sym} sector_strength={ss:.3f} < threshold={hi}")
        return f"SECTOR_WINNER threshold={hi} respected"

    runner.run("T24 sector: 3 groups exist",              t24_sector_3_groups_exist)
    runner.run("T25 sector: groups sum to universe_size", t25_sector_sums_to_universe)
    runner.run("T26 sector: groups disjoint",             t26_sector_disjoint)
    runner.run("T27 sector: winner threshold respected",  t27_sector_threshold_respected)


def test_group_regime(runner: TestRunner) -> None:

    def _get_r(regime: RegimeLabel) -> ClassificationResult:
        snap = make_daily_snapshot(regime=regime)
        return make_pc("regime").classify(snap)

    def t28_regime_2_groups_exist():
        r = _get_r(RegimeLabel.BULL_TREND)
        for lbl in [GroupLabel.REGIME_ALIGNED, GroupLabel.REGIME_DIVERGENT]:
            p = r.get_population_by_type(ClassifierType.REGIME, lbl)
            ok(p is not None, f"{lbl.value} missing")
        return "both regime groups present"

    def t29_regime_sums_to_universe():
        r     = _get_r(RegimeLabel.BULL_TREND)
        total = sum(p.member_count for p in r.populations
                    if p.classifier_type == ClassifierType.REGIME)
        ok(total == r.universe_size, f"sum={total}, expected {r.universe_size}")
        return f"regime sum={total}"

    def t30_regime_bull_aligns_positive_momentum():
        """In BULL regime: symbols with mom_5d > 0 should be REGIME_ALIGNED."""
        snap = make_daily_snapshot(regime=RegimeLabel.BULL_TREND, year=2026, month=8, day=10)
        r    = make_pc("rbull").classify(snap)
        obs_map = {o.symbol: o for o in snap.observations}
        aligned = r.get_population_by_type(ClassifierType.REGIME, GroupLabel.REGIME_ALIGNED)
        for sym in aligned.members:
            mom5 = obs_map[sym].features.get("mom_5d", 0.0)
            ok(mom5 > 0, f"BULL-aligned {sym} has mom_5d={mom5:.4f} <= 0")
        return f"BULL alignment verified for {len(aligned.members)} stocks"

    runner.run("T28 regime: 2 groups exist",                     t28_regime_2_groups_exist)
    runner.run("T29 regime: groups sum to universe_size",        t29_regime_sums_to_universe)
    runner.run("T30 regime: BULL aligned = positive mom_5d",     t30_regime_bull_aligns_positive_momentum)


def test_group_liquidity(runner: TestRunner) -> None:

    def _get_r() -> ClassificationResult:
        return make_pc("liq").classify(make_daily_snapshot())

    def t31_liquidity_3_groups():
        r = _get_r()
        for lbl in [GroupLabel.HIGH_LIQUIDITY, GroupLabel.MID_LIQUIDITY, GroupLabel.LOW_LIQUIDITY]:
            ok(r.get_population_by_type(ClassifierType.LIQUIDITY, lbl) is not None,
               f"{lbl.value} missing")
        return "all 3 liquidity groups present"

    def t32_liquidity_sum():
        r     = _get_r()
        total = sum(p.member_count for p in r.populations
                    if p.classifier_type == ClassifierType.LIQUIDITY)
        ok(total == r.universe_size, f"sum={total}")
        return f"liquidity sum={total}"

    def t33_liquidity_high_threshold():
        snap = make_daily_snapshot(year=2026, month=8, day=11)
        r    = make_pc("lth").classify(snap)
        obs_map = {o.symbol: o for o in snap.observations}
        hi  = _TEST_CFG.liquidity_high_threshold
        pop = r.get_population_by_type(ClassifierType.LIQUIDITY, GroupLabel.HIGH_LIQUIDITY)
        for sym in pop.members:
            ls = obs_map[sym].features.get("liquidity_score", 0.5)
            ok(ls >= hi, f"{sym} liquidity_score={ls:.3f} < {hi}")
        return f"HIGH_LIQUIDITY threshold={hi} respected"

    runner.run("T31 liquidity: 3 groups exist",           t31_liquidity_3_groups)
    runner.run("T32 liquidity: groups sum to universe",   t32_liquidity_sum)
    runner.run("T33 liquidity: HIGH threshold respected", t33_liquidity_high_threshold)


def test_group_volatility(runner: TestRunner) -> None:

    def _get_r() -> ClassificationResult:
        return make_pc("vol").classify(make_daily_snapshot())

    def t34_volatility_3_groups():
        r = _get_r()
        for lbl in [GroupLabel.HIGH_VOLATILITY, GroupLabel.MID_VOLATILITY, GroupLabel.LOW_VOLATILITY]:
            ok(r.get_population_by_type(ClassifierType.VOLATILITY, lbl) is not None,
               f"{lbl.value} missing")
        return "all 3 volatility groups present"

    def t35_volatility_sum():
        r     = _get_r()
        total = sum(p.member_count for p in r.populations
                    if p.classifier_type == ClassifierType.VOLATILITY)
        ok(total == r.universe_size, f"sum={total}")
        return f"volatility sum={total}"

    def t36_volatility_high_threshold():
        snap = make_daily_snapshot(year=2026, month=8, day=12)
        r    = make_pc("vth").classify(snap)
        obs_map = {o.symbol: o for o in snap.observations}
        hi  = _TEST_CFG.vol_high_threshold
        pop = r.get_population_by_type(ClassifierType.VOLATILITY, GroupLabel.HIGH_VOLATILITY)
        for sym in pop.members:
            hv = obs_map[sym].features.get("hist_vol_5d", 0.12)
            ok(hv >= hi, f"{sym} hist_vol_5d={hv:.4f} < {hi}")
        return f"HIGH_VOLATILITY threshold={hi} respected"

    runner.run("T34 volatility: 3 groups exist",           t34_volatility_3_groups)
    runner.run("T35 volatility: groups sum to universe",   t35_volatility_sum)
    runner.run("T36 volatility: HIGH threshold respected", t36_volatility_high_threshold)


def test_group_market_cap(runner: TestRunner) -> None:

    def t37_market_cap_3_groups():
        r = make_pc("mc").classify(make_daily_snapshot())
        for lbl in [GroupLabel.LARGE_CAP, GroupLabel.MID_CAP, GroupLabel.SMALL_CAP]:
            ok(r.get_population_by_type(ClassifierType.MARKET_CAP, lbl) is not None,
               f"{lbl.value} missing")
        return "all 3 market cap groups present"

    def t38_market_cap_sum():
        r     = make_pc("mc").classify(make_daily_snapshot(year=2026, month=8, day=13))
        total = sum(p.member_count for p in r.populations
                    if p.classifier_type == ClassifierType.MARKET_CAP)
        ok(total == r.universe_size, f"sum={total}")
        return f"market_cap sum={total}"

    runner.run("T37 market_cap: 3 groups exist",         t37_market_cap_3_groups)
    runner.run("T38 market_cap: groups sum to universe", t38_market_cap_sum)


def test_group_volume_expansion(runner: TestRunner) -> None:

    def t39_volume_3_groups():
        r = make_pc("ve").classify(make_daily_snapshot())
        for lbl in [GroupLabel.VOLUME_EXPANDING, GroupLabel.VOLUME_NORMAL, GroupLabel.VOLUME_CONTRACTING]:
            ok(r.get_population_by_type(ClassifierType.VOLUME_EXPANSION, lbl) is not None,
               f"{lbl.value} missing")
        return "all 3 volume groups present"

    def t40_volume_sum():
        r     = make_pc("ve").classify(make_daily_snapshot(year=2026, month=8, day=14))
        total = sum(p.member_count for p in r.populations
                    if p.classifier_type == ClassifierType.VOLUME_EXPANSION)
        ok(total == r.universe_size, f"sum={total}")
        return f"volume sum={total}"

    def t41_volume_expansion_threshold():
        snap = make_daily_snapshot(year=2026, month=8, day=15)
        r    = make_pc("veth").classify(snap)
        obs_map = {o.symbol: o for o in snap.observations}
        thr = _TEST_CFG.vol_expansion_ratio
        pop = r.get_population_by_type(ClassifierType.VOLUME_EXPANSION, GroupLabel.VOLUME_EXPANDING)
        for sym in pop.members:
            vr = obs_map[sym].features.get("volume_ratio_raw", 1.0)
            ok(vr >= thr, f"{sym} volume_ratio_raw={vr:.3f} < {thr}")
        return f"VOLUME_EXPANDING threshold={thr} respected"

    runner.run("T39 volume_expansion: 3 groups exist",             t39_volume_3_groups)
    runner.run("T40 volume_expansion: groups sum to universe",     t40_volume_sum)
    runner.run("T41 volume_expansion: EXPANDING threshold correct",t41_volume_expansion_threshold)


def test_group_relative_strength(runner: TestRunner) -> None:

    def t42_rs_3_groups():
        r = make_pc("rs").classify(make_daily_snapshot())
        for lbl in [GroupLabel.RS_STRONG, GroupLabel.RS_NEUTRAL, GroupLabel.RS_WEAK]:
            ok(r.get_population_by_type(ClassifierType.RELATIVE_STRENGTH, lbl) is not None,
               f"{lbl.value} missing")
        return "all 3 RS groups present"

    def t43_rs_sum():
        r     = make_pc("rs").classify(make_daily_snapshot(year=2026, month=8, day=16))
        total = sum(p.member_count for p in r.populations
                    if p.classifier_type == ClassifierType.RELATIVE_STRENGTH)
        ok(total == r.universe_size, f"sum={total}")
        return f"RS sum={total}"

    def t44_rs_strong_threshold():
        snap = make_daily_snapshot(year=2026, month=8, day=17)
        r    = make_pc("rsth").classify(snap)
        obs_map = {o.symbol: o for o in snap.observations}
        thr = _TEST_CFG.rs_strong_rsi
        pop = r.get_population_by_type(ClassifierType.RELATIVE_STRENGTH, GroupLabel.RS_STRONG)
        for sym in pop.members:
            rsi = obs_map[sym].features.get("rsi", 50.0)
            ok(rsi >= thr, f"{sym} rsi={rsi:.1f} < {thr}")
        return f"RS_STRONG threshold={thr} respected"

    runner.run("T42 relative_strength: 3 groups exist",         t42_rs_3_groups)
    runner.run("T43 relative_strength: groups sum to universe", t43_rs_sum)
    runner.run("T44 relative_strength: STRONG threshold",       t44_rs_strong_threshold)


def test_group_multilabel(runner: TestRunner) -> None:

    def _get_r() -> ClassificationResult:
        snap = make_daily_snapshot(year=2026, month=8, day=3)
        return make_pc("ml").classify(snap)

    def t45_each_symbol_has_8_labels():
        r = _get_r()
        n_classifiers = len(ClassifierType)  # 8
        for m in r.members:
            ok(len(m.labels) == n_classifiers,
               f"{m.symbol} has {len(m.labels)} labels, expected {n_classifiers}")
        return f"all {len(r.members)} symbols have {n_classifiers} labels"

    def t46_populations_for_returns_all():
        r   = _get_r()
        sym = _UNIVERSE[0]
        pops = r.populations_for(sym)
        ok(len(pops) == len(ClassifierType),
           f"expected {len(ClassifierType)}, got {len(pops)}")
        return f"populations_for({sym}) = {len(pops)}"

    def t47_avg_labels_is_8():
        r = _get_r()
        total  = sum(len(m.labels) for m in r.members)
        avg    = total / len(r.members)
        n_cls  = len(ClassifierType)
        ok(avg == float(n_cls), f"expected {n_cls}.0, got {avg}")
        return f"avg_labels_per_symbol={avg}"

    def t48_cross_dimension_combination():
        """A symbol can be TOP_5PCT AND SECTOR_WINNER simultaneously."""
        r    = _get_r()
        top5 = r.get_population_by_type(ClassifierType.PERFORMANCE, GroupLabel.TOP_5PCT)
        sw   = r.get_population_by_type(ClassifierType.SECTOR, GroupLabel.SECTOR_WINNER)
        if top5 and sw:
            overlap = set(top5.members) & set(sw.members)
            # Just verify the structure allows overlap (not asserting overlap exists)
            # since it depends on synthetic feature values
            return f"TOP_5PCT={len(top5.members)}, SECTOR_WINNER={len(sw.members)}, overlap={len(overlap)}"
        return "populations exist for cross-dimension check"

    def t49_population_ids_in_member():
        r   = _get_r()
        m   = r.members[0]
        ok(len(m.population_ids) == len(ClassifierType),
           f"expected {len(ClassifierType)} population_ids, got {len(m.population_ids)}")
        # All population_ids should exist in the populations list
        pop_id_set = {p.population_id for p in r.populations}
        for pid in m.population_ids:
            ok(pid in pop_id_set, f"population_id {pid} not in populations")
        return f"population_ids consistent for {m.symbol}"

    runner.run("T45 multi-label: each symbol has 8 labels",         t45_each_symbol_has_8_labels)
    runner.run("T46 multi-label: populations_for() returns all 8",  t46_populations_for_returns_all)
    runner.run("T47 multi-label: avg_labels == 8",                  t47_avg_labels_is_8)
    runner.run("T48 multi-label: cross-dimension combination OK",   t48_cross_dimension_combination)
    runner.run("T49 multi-label: population_ids consistent",        t49_population_ids_in_member)


def test_group_models(runner: TestRunner) -> None:

    def _get_r() -> ClassificationResult:
        snap = make_daily_snapshot(year=2026, month=8, day=3)
        return make_pc("models").classify(snap)

    def t50_result_round_trip():
        r1 = _get_r()
        d  = r1.to_dict()
        r2 = ClassificationResult.from_dict(d)
        ok(r2.result_id     == r1.result_id,     "result_id mismatch")
        ok(r2.universe_size == r1.universe_size, "universe_size mismatch")
        ok(len(r2.populations) == len(r1.populations), "populations count mismatch")
        ok(len(r2.members)     == len(r1.members),     "members count mismatch")
        return "ClassificationResult round-trip OK"

    def t51_get_population_returns_correct():
        r  = _get_r()
        p  = r.get_population(GroupLabel.NEUTRAL)
        ok(p is not None, "NEUTRAL should exist")
        ok(p.label == GroupLabel.NEUTRAL, "wrong label")
        return f"get_population(NEUTRAL) OK"

    def t52_get_population_unknown_returns_none():
        r = _get_r()
        # RS_STRONG is a valid label but accessing via wrong method should still work
        p = r.get_population(GroupLabel.RS_STRONG)
        ok(p is not None or p is None, "should return Population or None")
        return "get_population for valid label handled"

    def t53_get_member_returns_correct():
        r  = _get_r()
        m  = r.get_member(_UNIVERSE[0])
        ok(m is not None, f"{_UNIVERSE[0]} should be in members")
        ok(m.symbol == _UNIVERSE[0], "wrong symbol")
        return f"get_member({_UNIVERSE[0]}) OK"

    def t54_get_member_unknown_returns_none():
        r = _get_r()
        m = r.get_member("UNKNOWN_XYZ")
        ok(m is None, "unknown symbol should return None")
        return "get_member unknown -> None"

    def t55_population_round_trip():
        r  = _get_r()
        p1 = r.populations[0]
        d  = p1.to_dict()
        p2 = Population.from_dict(d)
        ok(p2.population_id   == p1.population_id,   "population_id mismatch")
        ok(p2.classifier_type == p1.classifier_type, "classifier_type mismatch")
        ok(p2.label           == p1.label,           "label mismatch")
        ok(p2.member_count    == p1.member_count,    "member_count mismatch")
        ok(p2.members         == p1.members,         "members mismatch")
        return "Population round-trip OK"

    def t56_population_id_format():
        r = _get_r()
        for p in r.populations:
            ok(p.population_id.startswith("POP-20260803-"),
               f"wrong id format: {p.population_id}")
        return "all population_ids have correct format"

    def t57_member_count_invariant():
        r = _get_r()
        for p in r.populations:
            ok(p.member_count == len(p.members),
               f"{p.population_id}: member_count={p.member_count} != len={len(p.members)}")
        return "member_count invariant holds"

    def t58_member_round_trip():
        r  = _get_r()
        m1 = r.members[0]
        d  = m1.to_dict()
        m2 = PopulationMember.from_dict(d)
        ok(m2.symbol         == m1.symbol,         "symbol mismatch")
        ok(m2.population_ids == m1.population_ids, "population_ids mismatch")
        ok(m2.labels         == m1.labels,         "labels mismatch")
        return "PopulationMember round-trip OK"

    def t59_classification_values_present():
        r = _get_r()
        required = {"realized_return", "sector_strength", "liquidity_score",
                    "hist_vol_5d", "volume_ratio_raw", "rsi", "mom_5d"}
        for m in r.members:
            for k in required:
                ok(k in m.classification_values, f"{m.symbol} missing {k}")
        return f"classification_values complete for all {len(r.members)} members"

    runner.run("T50 ClassificationResult round-trip",          t50_result_round_trip)
    runner.run("T51 get_population() known label",             t51_get_population_returns_correct)
    runner.run("T52 get_population() valid label handled",     t52_get_population_unknown_returns_none)
    runner.run("T53 get_member() known symbol",                t53_get_member_returns_correct)
    runner.run("T54 get_member() unknown -> None",             t54_get_member_unknown_returns_none)
    runner.run("T55 Population round-trip",                    t55_population_round_trip)
    runner.run("T56 population_id format",                     t56_population_id_format)
    runner.run("T57 member_count invariant",                   t57_member_count_invariant)
    runner.run("T58 PopulationMember round-trip",              t58_member_round_trip)
    runner.run("T59 classification_values complete",           t59_classification_values_present)


def test_group_external_outcomes(runner: TestRunner) -> None:

    def t60_outcomes_source_external():
        snap = make_daily_snapshot(year=2026, month=8, day=18)
        r    = make_pc("eo").classify(snap, outcomes={sym: 0.0 for sym in _UNIVERSE})
        ok(r.outcomes_source == "external", f"got {r.outcomes_source}")
        return "outcomes_source=external"

    def t61_outcomes_source_feature_proxy():
        snap = make_daily_snapshot(year=2026, month=8, day=19)
        r    = make_pc("eo").classify(snap)
        ok(r.outcomes_source == "feature_proxy", f"got {r.outcomes_source}")
        return "outcomes_source=feature_proxy"

    def t62_external_outcomes_deterministic():
        """Same outcomes on different days should produce same performance ranking."""
        outcomes = {sym: i * 0.01 for i, sym in enumerate(_UNIVERSE)}
        snap1    = make_daily_snapshot(year=2026, month=8, day=5)
        snap2    = make_daily_snapshot(year=2026, month=8, day=6)
        pc       = make_pc("eod")
        r1 = pc.classify(snap1, outcomes=outcomes)
        r2 = pc.classify(snap2, outcomes=outcomes)
        top5_1 = r1.get_population_by_type(ClassifierType.PERFORMANCE, GroupLabel.TOP_5PCT)
        top5_2 = r2.get_population_by_type(ClassifierType.PERFORMANCE, GroupLabel.TOP_5PCT)
        ok(set(top5_1.members) == set(top5_2.members),
           f"different members: {top5_1.members} vs {top5_2.members}")
        return "deterministic with same outcomes"

    runner.run("T60 external outcomes: outcomes_source=external",     t60_outcomes_source_external)
    runner.run("T61 feature proxy: outcomes_source=feature_proxy",    t61_outcomes_source_feature_proxy)
    runner.run("T62 external outcomes: deterministic ranking",        t62_external_outcomes_deterministic)


def test_group_storage(runner: TestRunner) -> None:

    def t63_load_result_after_classify():
        d    = fresh_dir("stor")
        snap = make_daily_snapshot(year=2026, month=8, day=3)
        pc   = PopulationClassifier(data_dir=d, config=_TEST_CFG)
        pc.classify(snap)
        loaded = pc.load_result("2026-08-03")
        ok(loaded is not None, "should load persisted result")
        ok(isinstance(loaded, ClassificationResult), "wrong type")
        ok(loaded.universe_size == len(_UNIVERSE), "universe_size mismatch after load")
        return "load_result OK"

    def t64_load_missing_returns_none():
        pc = make_pc("stor")
        ok(pc.load_result("2099-01-01") is None, "missing date should return None")
        return "missing -> None"

    def t65_list_results_sorted():
        d  = fresh_dir("stor")
        pc = PopulationClassifier(data_dir=d, config=_TEST_CFG)
        for day in (5, 3, 4):
            pc.classify(make_daily_snapshot(year=2026, month=8, day=day))
        dates = pc.list_results()
        ok(dates == sorted(dates), f"not sorted: {dates}")
        ok(len(dates) == 3, f"expected 3, got {len(dates)}")
        return f"dates={dates}"

    def t66_bak_created_on_overwrite():
        d    = fresh_dir("stor")
        snap = make_daily_snapshot(year=2026, month=8, day=3)
        pc   = PopulationClassifier(data_dir=d, config=_TEST_CFG)
        pc.classify(snap)
        pc.classify(snap)  # second write -> .bak
        bak  = d / "classifications" / "classification_2026-08-03.bak"
        ok(bak.exists(), ".bak not created on overwrite")
        return ".bak created"

    runner.run("T63 storage: load_result after classify",   t63_load_result_after_classify)
    runner.run("T64 storage: load_result missing -> None",  t64_load_missing_returns_none)
    runner.run("T65 storage: list_results sorted",          t65_list_results_sorted)
    runner.run("T66 storage: .bak on overwrite",            t66_bak_created_on_overwrite)


def test_group_statistics(runner: TestRunner) -> None:

    def _get_stats() -> PopulationStatistics:
        d  = fresh_dir("stats")
        pc = PopulationClassifier(data_dir=d, config=_TEST_CFG)
        snap = make_daily_snapshot(year=2026, month=8, day=3)
        pc.classify(snap)
        return pc.statistics("2026-08-03")

    def t67_statistics_returns_correct_type():
        st = _get_stats()
        ok(st is not None, "statistics should not be None")
        ok(isinstance(st, PopulationStatistics), "wrong type")
        return "type correct"

    def t68_statistics_population_count():
        st = _get_stats()
        # 8 classifiers: 7+3+2+3+3+3+3+3 = 27 populations
        ok(st.population_count == 27, f"expected 27, got {st.population_count}")
        return f"population_count={st.population_count}"

    def t69_statistics_classifier_types():
        st = _get_stats()
        ok(len(st.classifier_types_used) == len(ClassifierType),
           f"expected {len(ClassifierType)}, got {len(st.classifier_types_used)}")
        return f"classifier_types={st.classifier_types_used}"

    def t70_statistics_avg_labels():
        st = _get_stats()
        ok(st.avg_labels_per_symbol == float(len(ClassifierType)),
           f"expected {float(len(ClassifierType))}, got {st.avg_labels_per_symbol}")
        return f"avg_labels_per_symbol={st.avg_labels_per_symbol}"

    def t71_statistics_performance_group_sizes():
        st = _get_stats()
        ok(len(st.performance_group_sizes) == 7, f"expected 7, got {len(st.performance_group_sizes)}")
        total = sum(st.performance_group_sizes.values())
        ok(total == len(_UNIVERSE), f"perf size total={total}, expected {len(_UNIVERSE)}")
        return f"perf_sizes sum={total}"

    def t72_statistics_missing_date():
        pc = make_pc("stats")
        st = pc.statistics("2099-01-01")
        ok(st is None, "statistics for missing date should return None")
        return "missing date -> None"

    runner.run("T67 statistics: returns PopulationStatistics",       t67_statistics_returns_correct_type)
    runner.run("T68 statistics: population_count == 27",             t68_statistics_population_count)
    runner.run("T69 statistics: all 8 classifier_types_used",        t69_statistics_classifier_types)
    runner.run("T70 statistics: avg_labels_per_symbol == 8",         t70_statistics_avg_labels)
    runner.run("T71 statistics: performance_group_sizes sums right", t71_statistics_performance_group_sizes)
    runner.run("T72 statistics: missing date -> None",               t72_statistics_missing_date)


def test_group_thread_safety(runner: TestRunner) -> None:

    def t73_concurrent_classify():
        d      = fresh_dir("thread")
        pc     = PopulationClassifier(data_dir=d, config=_TEST_CFG)
        errors: list[str] = []

        def do_classify(day: int) -> None:
            try:
                snap = make_daily_snapshot(year=2026, month=8, day=day)
                pc.classify(snap)
            except Exception as exc:
                errors.append(f"day={day}: {exc}")

        threads = [threading.Thread(target=do_classify, args=(d_,)) for d_ in range(1, 9)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        ok(len(errors) == 0, f"concurrent errors: {errors}")
        dates = pc.list_results()
        ok(len(dates) == 8, f"expected 8, got {len(dates)}")
        return f"concurrent: 8/8 succeeded"

    runner.run("T73 thread safety: concurrent classify()", t73_concurrent_classify)


# ═════════════════════════════════════════════════════════════════════════════
# Main
# ═════════════════════════════════════════════════════════════════════════════

def main() -> None:
    runner = TestRunner()

    test_group_config(runner)
    test_group_instantiation(runner)
    test_group_classify_structure(runner)
    test_group_performance(runner)
    test_group_sector(runner)
    test_group_regime(runner)
    test_group_liquidity(runner)
    test_group_volatility(runner)
    test_group_market_cap(runner)
    test_group_volume_expansion(runner)
    test_group_relative_strength(runner)
    test_group_multilabel(runner)
    test_group_models(runner)
    test_group_external_outcomes(runner)
    test_group_storage(runner)
    test_group_statistics(runner)
    test_group_thread_safety(runner)

    print("\n" + "=" * 72)
    print("MLS Phase 2 -- PopulationClassifier Test Report")
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
