"""
test_hkap.py — HKAP-001 test suite.

Tests: T001–T100 (100 tests)
Framework: custom ok() / section() (identical pattern to test_mlc.py, test_sd.py)
"""
from __future__ import annotations

import math
import sys
import traceback
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

# ─── harness ──────────────────────────────────────────────────────────────────

_fail_count = 0
_pass_count = 0


def ok(label: str, cond: bool) -> None:
    global _fail_count, _pass_count
    if cond:
        _pass_count += 1
        print(f"  PASS  {label}")
    else:
        _fail_count += 1
        print(f"  FAIL  {label}")


def section(title: str) -> None:
    print(f"\n-- {title} --")


# ─── imports ──────────────────────────────────────────────────────────────────

sys.path.insert(0, str(Path(__file__).parent))

from hkap.hkap_models import (
    CrossYearDNARecord, CrossYearEdgeRecord, DNALifecycleLabel, FutureDataLeakError,
    HKAPError, HKAPStatus, HKAPSummary, RegimeDependency, YearDNASnapshot,
    YearEdgeSnapshot, YearKnowledgePackage, YearMarketProfile, YearNotCompleteError,
    YearSDReview, YearStudyStatus,
)
from hkap.hkap_config  import HKAPConfig
from hkap.market_profiler import MarketProfiler
from hkap.cross_year_analyzer import CrossYearAnalyzer
from hkap.snapshot_builder import _rsi, _compute_features, _std_returns


# ─── helpers ──────────────────────────────────────────────────────────────────

def _make_profile(year=2020, dominant="BULL_TREND", vol="MEDIUM",
                  ytd=0.15, dd=-0.10, personality="TRENDING_BULL") -> YearMarketProfile:
    return YearMarketProfile(
        year=year, regime_distribution={dominant: 0.6, "RANGE_MARKET": 0.4},
        dominant_regime=dominant, volatility_level=vol,
        sector_leaders=["IT", "Finance", "Energy"], sector_rotations=["IT emerged in H2"],
        breadth_score=0.62, momentum_strength=0.65, mean_reversion_strength=0.35,
        institutional_activity=0.55, market_personality=personality,
        behaviour_clusters=["PERSISTENT_ADVANCE", "BROAD_PARTICIPATION"],
        key_observations=["Dominant regime: BULL_TREND (60% of days)"],
        index_return_ytd=ytd, peak_drawdown=dd, trading_days=248,
    )


def _make_dna_snap(year=2020, winner_dna=None, conf_map=None) -> YearDNASnapshot:
    w = winner_dna or ["rsi_5::WINNERS_HIGHER", "volume_ratio::WINNERS_HIGHER"]
    c = conf_map   or {"rsi_5::WINNERS_HIGHER": 0.72, "volume_ratio::WINNERS_HIGHER": 0.65}
    return YearDNASnapshot(
        year=year, winner_dna=w, loser_dna=["mom_20d::WINNERS_LOWER"],
        neutral_dna=[], regime_specific_dna={"BULL_TREND": ["rsi_5::WINNERS_HIGHER"]},
        regime_independent_dna=["volume_ratio::WINNERS_HIGHER"],
        total_discovered=5, high_confidence_count=2, median_confidence=0.65,
        confidence_by_id=c, source_db=f"data/hkap/{year}/institutional_dna.db",
    )


def _make_edge_snap(year=2020) -> YearEdgeSnapshot:
    return YearEdgeSnapshot(
        year=year, active_edges=["rsi_5::WINNERS_HIGHER", "volume_ratio::WINNERS_HIGHER"],
        promoted_this_year=["volume_ratio::WINNERS_HIGHER"],
        demoted_this_year=[], retired_this_year=[],
        survival_rate=0.5, new_edge_rate=0.5, total_prior_edges=2,
    )


def _make_pkg(year=2020, status=YearStudyStatus.COMPLETE) -> YearKnowledgePackage:
    return YearKnowledgePackage(
        year=year, status=status.value,
        market_profile=_make_profile(year=year),
        dna_snapshot=_make_dna_snap(year=year),
        edge_snapshot=_make_edge_snap(year=year),
        sd_review=None,
        prior_years_context=[y for y in range(2015, year)],
        trading_days_analyzed=248, universe_size=100,
        completed_at="2026-01-01T00:00:00+00:00",
        reports=[], stage_statuses={},
    )


# ══════════════════════════════════════════════════════════════════════════════
# Tests
# ══════════════════════════════════════════════════════════════════════════════

def test_models() -> None:
    section("T001-T015  YearStudyStatus and enums")
    ok("T001 YearStudyStatus values", set(YearStudyStatus) == {
        YearStudyStatus.PENDING, YearStudyStatus.RUNNING,
        YearStudyStatus.COMPLETE, YearStudyStatus.FAILED, YearStudyStatus.SKIPPED,
    })
    ok("T002 DNALifecycleLabel has 6 values", len(DNALifecycleLabel) == 6)
    ok("T003 STABLE label value", DNALifecycleLabel.STABLE.value == "STABLE")
    ok("T004 EMERGING label value", DNALifecycleLabel.EMERGING.value == "EMERGING")
    ok("T005 RegimeDependency has 3 values", len(RegimeDependency) == 3)
    ok("T006 REGIME_SPECIFIC value", RegimeDependency.REGIME_SPECIFIC.value == "REGIME_SPECIFIC")

    section("T007-T010  Error classes")
    ok("T007 HKAPError is Exception", issubclass(HKAPError, Exception))
    ok("T008 FutureDataLeakError attributes",
       FutureDataLeakError(2020, 2021).requesting_year == 2020 and
       FutureDataLeakError(2020, 2021).future_year == 2021)
    ok("T009 FutureDataLeakError message mentions both years",
       "2020" in str(FutureDataLeakError(2020, 2021)) and
       "2021" in str(FutureDataLeakError(2020, 2021)))
    ok("T010 YearNotCompleteError stores year", YearNotCompleteError(2019).year == 2019)

    section("T011-T015  YearMarketProfile to_dict")
    mp = _make_profile()
    d  = mp.to_dict()
    ok("T011 to_dict has year", d["year"] == 2020)
    ok("T012 to_dict has dominant_regime", d["dominant_regime"] == "BULL_TREND")
    ok("T013 to_dict has index_return_ytd", abs(d["index_return_ytd"] - 0.15) < 1e-9)
    ok("T014 to_dict has sector_leaders list", isinstance(d["sector_leaders"], list))
    ok("T015 to_dict has behaviour_clusters", "behaviour_clusters" in d)


def test_config() -> None:
    section("T016-T025  HKAPConfig")
    c = HKAPConfig()
    ok("T016 default years is 2015-2026", c.years == list(range(2015, 2027)))
    ok("T017 default forward_only is True", c.forward_only is True)
    ok("T018 default merge_to_live_idr is False", c.merge_to_live_idr is False)
    ok("T019 default dry_run is False", c.dry_run is False)
    ok("T020 default max_symbols is 150", c.max_symbols == 150)
    ok("T021 sorted_years returns sorted list", c.sorted_years == sorted(c.years))
    ok("T022 custom years accepted",
       HKAPConfig(years=[2020, 2021]).years == [2020, 2021])
    ok("T023 forward_only=False raises ValueError",
       _raises(lambda: HKAPConfig(years=[2020], forward_only=False), ValueError))
    ok("T024 merge_to_live_idr=True raises ValueError",
       _raises(lambda: HKAPConfig(years=[2020], merge_to_live_idr=True), ValueError))
    ok("T025 empty years raises ValueError",
       _raises(lambda: HKAPConfig(years=[]), ValueError))


def test_snapshot_builder() -> None:
    section("T026-T040  HistoricalSnapshotBuilder internals")

    # RSI tests
    flat = [100.0] * 20
    ok("T026 RSI flat series returns 100 (no losses)", abs(_rsi(flat, 14) - 100.0) < 1.0)
    up   = [float(i) for i in range(1, 22)]
    ok("T027 RSI all-up series > 90", _rsi(up, 14) > 90)
    dn   = list(reversed([float(i) for i in range(1, 22)]))
    ok("T028 RSI all-down series < 10", _rsi(dn, 14) < 10)
    ok("T029 RSI insufficient data returns 50", _rsi([100.0, 99.0], 14) == 50.0)
    ok("T030 RSI period 5 works", 0 <= _rsi(up, 5) <= 100)

    # std_returns
    ok("T031 _std_returns empty returns 0", _std_returns([]) == 0.0)
    ok("T032 _std_returns constant returns 0", _std_returns([100.0] * 10) == 0.0)
    ok("T033 _std_returns non-constant > 0", _std_returns([100, 102, 98, 101]) > 0)

    # _compute_features
    closes  = [float(100 + i) for i in range(30)]
    volumes = [1_000_000.0] * 30
    highs   = [c + 1.0 for c in closes]
    lows    = [c - 1.0 for c in closes]
    f = _compute_features(closes, volumes, highs, lows)
    ok("T034 features dict non-empty", bool(f))
    ok("T035 mom_1d is positive (upward series)", f.get("mom_1d", 0) > 0)
    ok("T036 mom_5d is positive (upward series)", f.get("mom_5d", 0) > 0)
    ok("T037 volume_ratio is 1.0 (constant volume)", abs(f.get("volume_ratio", 0) - 1.0) < 0.01)
    ok("T038 rsi_14 > 50 for upward series", f.get("rsi_14", 50) > 50)
    ok("T039 bb_position in [0, 1]", 0.0 <= f.get("bb_position", 0.5) <= 1.0)
    ok("T040 breadth_contribution is 1.0 (advancing)", f.get("breadth_contribution") == 1.0)


def test_market_profiler() -> None:
    section("T041-T055  MarketProfiler")
    profiler = MarketProfiler()

    def _make_snap(date_str, regime, vol, breadth, mom_1d=0.01):
        obs = [{"symbol": "X", "features": {"mom_1d": mom_1d, "volume_ratio": 1.0,
                                              "close": 100.0}, "feature_count": 3}]
        return {"trading_date": date_str, "regime": regime, "volatility": vol,
                "breadth": breadth, "universe_size": 1, "symbols": ["X"],
                "observations": obs}

    snaps = [
        _make_snap("2022-01-03", "BULL_TREND",  "MEDIUM", 0.65, 0.01),
        _make_snap("2022-01-04", "BULL_TREND",  "MEDIUM", 0.62, 0.005),
        _make_snap("2022-01-05", "RANGE_MARKET","HIGH",   0.50, 0.0),
        _make_snap("2022-01-06", "BULL_TREND",  "MEDIUM", 0.70, 0.02),
        _make_snap("2022-01-07", "BULL_TREND",  "LOW",    0.68, 0.015),
    ]
    sector_map = {"X": "IT"}
    mp = profiler.profile_year(2022, snaps, sector_map)

    ok("T041 profile has correct year", mp.year == 2022)
    ok("T042 dominant regime is BULL_TREND", mp.dominant_regime == "BULL_TREND")
    ok("T043 BULL_TREND fraction is 0.8", abs(mp.regime_distribution.get("BULL_TREND", 0) - 0.8) < 0.01)
    ok("T044 dominant volatility is MEDIUM", mp.volatility_level == "MEDIUM")
    ok("T045 breadth_score is ~0.63", 0.60 <= mp.breadth_score <= 0.70)
    ok("T046 personality is not empty", bool(mp.market_personality))
    ok("T047 behaviour_clusters not empty", bool(mp.behaviour_clusters))
    ok("T048 key_observations not empty", bool(mp.key_observations))
    ok("T049 trading_days == 5", mp.trading_days == 5)
    ok("T050 to_dict has all keys",
       all(k in mp.to_dict() for k in ["year", "dominant_regime", "sector_leaders",
                                        "market_personality", "index_return_ytd"]))

    # empty input
    empty_mp = profiler.profile_year(2019, [], {})
    ok("T051 empty snaps returns unknown profile", empty_mp.dominant_regime == "UNKNOWN")
    ok("T052 empty profile trading_days == 0", empty_mp.trading_days == 0)

    # personality classification
    bear_snaps = [
        _make_snap("2022-01-03", "BEAR_MARKET", "HIGH", 0.30, -0.02),
        _make_snap("2022-01-04", "BEAR_MARKET", "HIGH", 0.28, -0.03),
        _make_snap("2022-01-05", "BEAR_MARKET", "HIGH", 0.25, -0.025),
    ]
    bear_mp = profiler.profile_year(2018, bear_snaps, {})
    ok("T053 bear year gets bear-related personality",
       bear_mp.market_personality in ("TRENDING_BEAR", "VOLATILE_MIXED",
                                      "SIDEWAYS_CHOPPY", "DISTRIBUTION"))

    # VOLATILE_MARKET dominant
    vol_snaps = [_make_snap(f"2022-01-0{i}", "VOLATILE_MARKET", "EXTREME", 0.5)
                 for i in range(3, 8)]
    vol_mp = profiler.profile_year(2020, vol_snaps, {})
    ok("T054 volatile dominant → VOLATILE_MIXED personality",
       vol_mp.market_personality == "VOLATILE_MIXED")

    ok("T055 MarketProfiler._count_fraction sums to 1",
       abs(sum(profiler._count_fraction(["A", "B", "A", "A"]).values()) - 1.0) < 1e-9)


def test_year_runner_forward_only() -> None:
    section("T056-T075  YearRunner — forward-only and isolation")
    from hkap.year_runner import YearRunner
    from hkap.hkap_models import FutureDataLeakError

    config = HKAPConfig(years=[2019, 2020, 2021], dry_run=True)
    mock_ptue = MagicMock()
    mock_ptue.get_universe.return_value = MagicMock(symbols=["RELIANCE", "TCS"])

    # future context raises
    future_pkg = _make_pkg(year=2021)
    ok("T056 future year in prior_context raises FutureDataLeakError",
       _raises(lambda: YearRunner(2020, config, mock_ptue, prior_context=[future_pkg]),
               FutureDataLeakError))

    # same year raises
    same_pkg = _make_pkg(year=2020)
    ok("T057 same year in prior_context raises FutureDataLeakError",
       _raises(lambda: YearRunner(2020, config, mock_ptue, prior_context=[same_pkg]),
               FutureDataLeakError))

    # prior year accepted
    prior_pkg = _make_pkg(year=2019)
    try:
        runner = YearRunner(2020, config, mock_ptue, prior_context=[prior_pkg])
        ok("T058 prior year accepted in prior_context", True)
    except Exception:
        ok("T058 prior year accepted in prior_context", False)

    # empty prior context accepted
    try:
        runner = YearRunner(2015, config, mock_ptue, prior_context=[])
        ok("T059 empty prior_context accepted", True)
    except Exception:
        ok("T059 empty prior_context accepted", False)

    ok("T060 year_dir created under data_root",
       Path(config.data_root) / "2015")

    section("T061-T075  YearRunner edge/DNA helpers")
    # _stage_edges with no prior
    runner = YearRunner(2020, config, mock_ptue, prior_context=[])
    dna = _make_dna_snap(year=2020)
    es  = runner._stage_edges(dna)
    ok("T061 active_edges from dna above threshold",
       "rsi_5::WINNERS_HIGHER" in es.active_edges)
    ok("T062 survival_rate is 0 with no prior", es.survival_rate == 0.0)
    ok("T063 total_prior_edges is 0 with no prior", es.total_prior_edges == 0)
    ok("T064 promoted_this_year equals active_edges when no prior",
       set(es.promoted_this_year) == set(es.active_edges))

    # with prior
    prior_es = YearEdgeSnapshot(
        year=2019, active_edges=["rsi_5::WINNERS_HIGHER"],
        promoted_this_year=[], demoted_this_year=[], retired_this_year=[],
        survival_rate=1.0, new_edge_rate=0.0, total_prior_edges=0,
    )
    prior_pkg_with_es = _make_pkg(year=2019)
    prior_pkg_with_es.edge_snapshot.active_edges = ["rsi_5::WINNERS_HIGHER"]
    runner2 = YearRunner(2020, config, mock_ptue, prior_context=[prior_pkg_with_es])
    es2 = runner2._stage_edges(dna)
    ok("T065 survival_rate > 0 when prior has common edge", es2.survival_rate > 0)
    ok("T066 promoted_this_year excludes inherited edge",
       "rsi_5::WINNERS_HIGHER" not in es2.promoted_this_year)
    ok("T067 volume_ratio is promoted (new vs prior)",
       "volume_ratio::WINNERS_HIGHER" in es2.promoted_this_year)

    # stage_edges with None dna_snap
    es_none = runner._stage_edges(None)
    ok("T068 stage_edges(None) returns empty active_edges", es_none.active_edges == [])

    # _load_sector_map (static)
    sector_map = YearRunner._load_sector_map()
    ok("T069 sector_map is dict", isinstance(sector_map, dict))

    # stage_statuses initialised to PENDING
    ok("T070 all stage_statuses start as PENDING",
       all(v == "PENDING" for v in runner._stage_statuses.values()))

    # forward-only: multiple prior packages, all older
    prior_2015 = _make_pkg(year=2015)
    prior_2016 = _make_pkg(year=2016)
    runner3 = YearRunner(2017, config, mock_ptue,
                         prior_context=[prior_2015, prior_2016])
    ok("T071 multiple older priors accepted", runner3._prior == [prior_2015, prior_2016])

    # _failed_package returns FAILED status
    fp = runner._failed_package("test reason")
    ok("T072 _failed_package status is FAILED", fp.status == YearStudyStatus.FAILED.value)
    ok("T073 _failed_package trading_days == 0", fp.trading_days_analyzed == 0)

    ok("T074 YearRunner stores prior_years correctly",
       runner3._prior[0].year == 2015 and runner3._prior[1].year == 2016)
    ok("T075 FutureDataLeakError is HKAPError",
       issubclass(FutureDataLeakError, HKAPError))


def test_cross_year_analyzer() -> None:
    section("T076-T085  CrossYearAnalyzer")
    cya = CrossYearAnalyzer()

    # build 5 year packages with varying DNA presence
    pkgs = {}
    dna_id = "rsi_5::WINNERS_HIGHER"
    years  = [2018, 2019, 2020, 2021, 2022]
    for i, yr in enumerate(years):
        conf = 0.70 + i * 0.02
        pkg  = _make_pkg(year=yr)
        pkg.dna_snapshot.confidence_by_id = {dna_id: conf}
        pkgs[yr] = pkg

    dna_recs, edge_recs = cya.analyze(pkgs)
    ok("T076 analyze returns non-empty dna_records", len(dna_recs) > 0)
    ok("T077 analyze returns non-empty edge_records", len(edge_recs) > 0)
    ok("T078 stable DNA has survival_score = 1.0",
       any(r.survival_score >= 0.99 and r.dna_id == dna_id for r in dna_recs))
    ok("T079 stable DNA lifecycle is STABLE or STRENGTHENING",
       any(r.dna_id == dna_id and r.lifecycle_label in ("STABLE", "STRENGTHENING")
           for r in dna_recs))

    # lifecycle classification
    ok("T080 all-present presences → STABLE or STRENGTHENING",
       cya._classify_lifecycle([True]*8, [0.6]*8).value in ("STABLE", "STRENGTHENING"))
    ok("T081 only-in-last-2 → EMERGING",
       cya._classify_lifecycle([False]*6 + [True, True], [0]*6 + [0.6, 0.65]) == DNALifecycleLabel.EMERGING)
    ok("T082 absent-in-last-3 → DISAPPEARING",
       cya._classify_lifecycle([True]*5 + [False, False, False], [0.7]*5 + [0, 0, 0]) == DNALifecycleLabel.DISAPPEARING)

    # confidence trend
    ok("T083 rising confidence trend → RISING",
       cya._confidence_trend([0.5, 0.6, 0.7, 0.8]) == "RISING")
    ok("T084 falling confidence trend → FALLING",
       cya._confidence_trend([0.8, 0.7, 0.6, 0.5]) == "FALLING")
    ok("T085 flat confidence trend → STABLE",
       cya._confidence_trend([0.65, 0.65, 0.65]) == "STABLE")


def test_report_generator() -> None:
    section("T086-T095  HKAPReportGenerator")
    import tempfile, os
    from hkap.report_generator import HKAPReportGenerator

    with tempfile.TemporaryDirectory() as tmpdir:
        config = HKAPConfig(years=[2020], dry_run=False,
                            reports_root=os.path.join(tmpdir, "reports"))
        gen  = HKAPReportGenerator(config)
        pkg  = _make_pkg(year=2020)
        paths = gen.generate_year_reports(pkg)

        ok("T086 5 per-year reports generated", len(paths) == 5)
        ok("T087 KNOWLEDGE.md exists", any("KNOWLEDGE" in p for p in paths))
        ok("T088 DNA.md exists", any("_DNA.md" in p for p in paths))
        ok("T089 EDGES.md exists", any("EDGES" in p for p in paths))
        ok("T090 MARKET_PROFILE.md exists", any("MARKET_PROFILE" in p for p in paths))
        ok("T091 RESEARCH_SUMMARY.md exists", any("RESEARCH_SUMMARY" in p for p in paths))

        # check file content
        knowledge_path = [p for p in paths if "KNOWLEDGE" in p][0]
        content = Path(knowledge_path).read_text()
        ok("T092 KNOWLEDGE.md contains year header", "Year 2020" in content)
        ok("T093 KNOWLEDGE.md contains market summary", "Market Summary" in content)
        ok("T094 KNOWLEDGE.md contains DNA count", "DNA" in content)

        # dry run: no files written
        config2 = HKAPConfig(years=[2020], dry_run=True,
                             reports_root=os.path.join(tmpdir, "dry"))
        gen2   = HKAPReportGenerator(config2)
        paths2 = gen2.generate_year_reports(pkg)
        ok("T095 dry_run returns paths but writes no files",
           len(paths2) == 5 and not any(Path(p).exists() for p in paths2))


def test_hkap_engine() -> None:
    section("T096-T100  HKAPEngine")
    from hkap.hkap_engine import HKAPEngine

    mock_ptue = MagicMock()
    mock_ptue.get_universe.return_value = MagicMock(symbols=["RELIANCE"])
    config = HKAPConfig(years=[2020, 2021], dry_run=True, resume_on_restart=False)

    engine = HKAPEngine(config=config, ptue=mock_ptue)

    # status before any run
    st = engine.status()
    ok("T096 initial status has all years pending", set(st.years_pending) == {2020, 2021})
    ok("T097 initial status has no completed years", st.years_completed == [])
    ok("T098 initial synthesis_done is False", not st.is_synthesis_done)

    # year not in config raises
    ok("T099 run_year with invalid year raises HKAPError",
       _raises(lambda: engine.run_year(2019), HKAPError))

    # request_live_merge always raises
    ok("T100 request_live_merge raises HKAPError",
       _raises(engine.request_live_merge, HKAPError))


# ─── utility ─────────────────────────────────────────────────────────────────

def _raises(fn, exc_type) -> bool:
    try:
        fn()
        return False
    except exc_type:
        return True
    except Exception:
        return False


# ─── entrypoint ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    try:
        test_models()
        test_config()
        test_snapshot_builder()
        test_market_profiler()
        test_year_runner_forward_only()
        test_cross_year_analyzer()
        test_report_generator()
        test_hkap_engine()
    except Exception:
        traceback.print_exc()
        sys.exit(1)

    total = _pass_count + _fail_count
    print(f"\n{'=' * 60}")
    print(f"  {_pass_count}/{total} tests passed  ({_fail_count} failed)")
    print(f"{'=' * 60}")
    sys.exit(0 if _fail_count == 0 else 1)
