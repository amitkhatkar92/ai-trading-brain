"""
test_dna_consensus_engine.py — MLS Phase 4 test suite.

Covers:
    MLSConfig Phase 4 fields   — defaults, overrides, weight sum
    Engine init                — default, custom config/dir
    update() structure         — return type, IDs, consensus present, persists
    ConsensusDNA fields        — id prefix, direction, state, all metrics
    ConfidenceEvolution        — structure, trend direction, window filtering
    DriftReport                — 4 drift types, magnitude, significant flag
    DNAStability               — stable vs not-stable classification
    ConsensusStatistics        — counts, averages, top feature
    ConsensusLibrary model     — round-trip, master_consensus subset, library_id
    Lifecycle transitions      — DISCOVERED -> REPLICATED -> VERIFIED -> INSTITUTIONAL
                                 WEAKENING, DRIFTING, RETIRED
    Consensus score math       — known inputs, weight coverage, trend score
    Temporal stability math    — single obs, all same, high var, moderate var
    Regime consistency         — 1 / 3 / 5 regimes
    Drift detection            — statistical, regime, temporal, feature
    Confidence trend           — positive slope, negative slope, flat, n<2
    Storage                    — persist, load, list, .bak overwrite
    Query API                  — stable_dna, retired_dna, confidence_history, drift_report
    master_library()           — structure, master subset, empty before update
    Traceability               — observation audit trail, regime_counts, first_seen immutable
    Thread safety              — 8 concurrent update() calls in isolated dirs, idempotent

Run:
    python test_dna_consensus_engine.py
"""
from __future__ import annotations

import dataclasses
import hashlib
import sys
import tempfile
import threading
import time
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from market_learning import (
    DNAConsensusEngine,
    MLSConfig,
    SeparationDirection,
    DNACharacteristic,
    DNALifecycle,
    DNAInteraction,
    DiscoveryReport,
    FeatureEvidence,
    FeatureType,
    LoserDNA,
    WinnerDNA,
    NeutralDNA,
)
from market_learning.dna_consensus_models import (
    ConsensusDNA,
    ConsensusLevel,
    ConsensusLibrary,
    ConsensusState,
    ConsensusStatistics,
    ConfidenceEvolution,
    ConfidencePoint,
    DNAConsensusError,
    DNAStability,
    DriftMeasurement,
    DriftReport,
    DriftType,
    ConsensusLibraryNotFoundError,
)
from market_learning.dna_consensus_engine import (
    _trend_slope,
    _temporal_stability,
    _replication_freq,
    _regime_consistency,
    _feature_persistence,
    _consensus_score,
    _compute_consensus_state,
    _compute_level,
    _statistical_drift,
    _regime_drift,
    _temporal_drift,
    _feature_drift,
    _make_consensus_id,
    _N_KNOWN_REGIMES,
)


# ═════════════════════════════════════════════════════════════════════════════
# Test framework
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
                duration_ms=(time.perf_counter() - t0) * 1000,
                detail=str(detail),
            ))
        except AssertionError as exc:
            self.results.append(TestResult(
                name=name, passed=False,
                duration_ms=(time.perf_counter() - t0) * 1000,
                detail="ASSERTION FAILED",
                error=str(exc) or "assert failed",
            ))
        except Exception as exc:
            self.results.append(TestResult(
                name=name, passed=False,
                duration_ms=(time.perf_counter() - t0) * 1000,
                detail="EXCEPTION",
                error=traceback.format_exc(),
            ))

    def report(self) -> int:
        W = 72
        print("=" * W)
        for r in self.results:
            tag   = "[PASS]" if r.passed else "[FAIL]"
            label = r.name[:45].ljust(45)
            ms    = f"{r.duration_ms:6.1f}ms"
            short = r.detail[:60]
            print(f"  {tag} {label} {ms}  {short}")
            if not r.passed and r.error:
                for line in r.error.strip().splitlines()[-4:]:
                    print(f"          {line}")
        print("-" * W)
        passed = sum(1 for r in self.results if r.passed)
        total  = len(self.results)
        print(f"  Result:  {passed}/{total} passed, {total - passed} failed")
        print("=" * W)
        return 0 if passed == total else 1


def ok(condition: bool, msg: str = "") -> None:
    if not condition:
        raise AssertionError(msg or "assertion failed")


# ═════════════════════════════════════════════════════════════════════════════
# Test helpers
# ═════════════════════════════════════════════════════════════════════════════

_TEST_CFG = MLSConfig(min_universe_size=1, dna_min_group_size=2)

_DIR_COUNTER = [0]


def fresh_dir(tag: str = "") -> str:
    _DIR_COUNTER[0] += 1
    import shutil
    base = Path(tempfile.gettempdir()) / f"mls_con_{_DIR_COUNTER[0]}_{tag}"
    if base.exists():
        shutil.rmtree(base)
    base.mkdir(parents=True)
    return str(base)


def _make_evidence(fname: str, direction: SeparationDirection,
                   effect_abs: float = 5.0) -> FeatureEvidence:
    return FeatureEvidence(
        feature_name=fname,
        feature_type=FeatureType.CONTINUOUS,
        winner_mean=effect_abs, winner_std=0.1,
        loser_mean=-effect_abs,  loser_std=0.1,
        effect_size=effect_abs,  effect_abs=abs(effect_abs),
        direction=direction,
        ci_low=effect_abs - 0.5, ci_high=effect_abs + 0.5,
        spearman_corr=0.8,
        n_winners=3, n_losers=3,
    )


def _make_char(fname: str, direction: str = "WINNERS_HIGHER",
               effect_abs: float = 5.0, confidence: float = 0.85,
               date: str = "2026-08-03", regime: str = "bull_trend") -> DNACharacteristic:
    dir_ = SeparationDirection(direction)
    h    = hashlib.sha256(f"{fname}::{direction}".encode()).hexdigest()[:8]
    return DNACharacteristic(
        char_id=f"DNA-{h}",
        feature_name=fname,
        feature_type=FeatureType.CONTINUOUS,
        direction=dir_,
        effect_size=effect_abs,
        effect_abs=abs(effect_abs),
        confidence=confidence,
        lifecycle=DNALifecycle.DISCOVERED,
        trading_date=date,
        regime=regime,
        evidence=_make_evidence(fname, dir_, effect_abs),
        first_seen=date,
        last_seen=date,
        occurrence_count=1,
    )


def _make_report(date: str,
                 chars: List[DNACharacteristic],
                 regime: str = "bull_trend") -> DiscoveryReport:
    return DiscoveryReport(
        report_id=f"MLS-DNA-{date.replace('-', '')}",
        trading_date=date,
        snapshot_id=f"MLS-SNAP-{date.replace('-', '')}",
        classification_id=f"MLS-CLS-{date.replace('-', '')}",
        winner_dna=WinnerDNA(date=date, characteristics=[], interactions=[],
                             population_ids=[], n_members=0, regime=regime),
        loser_dna=LoserDNA(date=date,  characteristics=[], interactions=[],
                           population_ids=[], n_members=0, regime=regime),
        neutral_dna=NeutralDNA(date=date, characteristics=[], interactions=[],
                               population_ids=[], n_members=0, regime=regime),
        all_characteristics=chars,
        all_interactions=[],
        regime=regime,
        universe_size=11,
        created_at=f"{date}T09:15:00",
    )


def _engine(tag: str, cfg: Optional[MLSConfig] = None) -> DNAConsensusEngine:
    return DNAConsensusEngine(config=cfg or _TEST_CFG, data_dir=fresh_dir(tag))


def _engine_with_n_updates(
    n: int,
    feature: str = "rsi",
    direction: str = "WINNERS_HIGHER",
    confidence: float = 0.85,
    effect_abs: float = 5.0,
    regime: str = "bull_trend",
    tag: str = "",
    cfg: Optional[MLSConfig] = None,
) -> Tuple[DNAConsensusEngine, ConsensusLibrary]:
    """Create engine and call update() n times with incrementing dates."""
    eng = _engine(tag or f"n{n}", cfg)
    lib = None
    for i in range(n):
        date = f"2026-07-{i + 1:02d}"
        char = _make_char(feature, direction, effect_abs, confidence, date, regime)
        lib  = eng.update(_make_report(date, [char], regime))
    return eng, lib


# ═════════════════════════════════════════════════════════════════════════════
# Tests
# ═════════════════════════════════════════════════════════════════════════════

def main() -> int:
    runner = TestRunner()

    # ── T01-T04: MLSConfig Phase 4 defaults ──────────────────────────────────

    def t01_phase4_defaults():
        cfg = MLSConfig()
        ok(cfg.consensus_institutional_min_count == 10)
        ok(cfg.consensus_institutional_min_score == 0.60)
        ok(cfg.consensus_retirement_absent_days  == 30)
        return "Phase 4 lifecycle defaults correct"

    def t02_phase4_drift_defaults():
        cfg = MLSConfig()
        ok(cfg.consensus_drift_threshold  == 0.30)
        ok(cfg.consensus_drift_window     == 7)
        ok(cfg.consensus_trend_window     == 7)
        ok(cfg.consensus_trend_declining_slope == 0.05)
        return "Phase 4 drift defaults correct"

    def t03_phase4_weights_sum_to_1():
        cfg = MLSConfig()
        total = (cfg.consensus_w_replication + cfg.consensus_w_temporal
                 + cfg.consensus_w_regime + cfg.consensus_w_sector
                 + cfg.consensus_w_confidence + cfg.consensus_w_persistence)
        ok(abs(total - 1.0) < 1e-9, f"weights sum={total}")
        return f"weights sum={total:.6f}"

    def t04_phase4_overrides():
        cfg = MLSConfig(consensus_institutional_min_count=5,
                        consensus_drift_threshold=0.50)
        ok(cfg.consensus_institutional_min_count == 5)
        ok(cfg.consensus_drift_threshold == 0.50)
        return "Phase 4 overrides correct"

    # ── T05-T07: Engine instantiation ─────────────────────────────────────────

    def t05_engine_default_init():
        eng = DNAConsensusEngine()
        ok(eng is not None)
        return "default init OK"

    def t06_engine_custom_config():
        cfg = MLSConfig(consensus_institutional_min_count=3)
        eng = DNAConsensusEngine(config=cfg)
        ok(eng._cfg.consensus_institutional_min_count == 3)
        return "custom config assigned"

    def t07_engine_custom_data_dir():
        d   = fresh_dir("init")
        eng = DNAConsensusEngine(data_dir=d)
        ok(str(eng._dir) == d)
        return f"data_dir={d}"

    # ── T08-T14: update() structure ───────────────────────────────────────────

    def t08_update_returns_consensus_library():
        eng = _engine("u1")
        char = _make_char("rsi")
        lib = eng.update(_make_report("2026-08-03", [char]))
        ok(isinstance(lib, ConsensusLibrary))
        return f"type={type(lib).__name__}"

    def t09_update_library_id_format():
        eng = _engine("u2")
        lib = eng.update(_make_report("2026-08-03", [_make_char("rsi")]))
        ok(lib.library_id == "MLS-LIB-20260803", lib.library_id)
        return f"library_id={lib.library_id}"

    def t10_update_as_of_date():
        eng = _engine("u3")
        lib = eng.update(_make_report("2026-08-03", [_make_char("rsi")]))
        ok(lib.as_of_date == "2026-08-03")
        return f"as_of_date={lib.as_of_date}"

    def t11_update_all_consensus_nonempty():
        eng = _engine("u4")
        chars = [_make_char("rsi"), _make_char("adx_score")]
        lib = eng.update(_make_report("2026-08-03", chars))
        ok(len(lib.all_consensus) == 2, len(lib.all_consensus))
        return f"all_consensus={len(lib.all_consensus)}"

    def t12_update_persists_json():
        eng = _engine("u5")
        eng.update(_make_report("2026-08-03", [_make_char("rsi")]))
        ok(eng._lib_path.exists())
        return f"file={eng._lib_path.name}"

    def t13_update_drift_reports_built():
        eng = _engine("u6")
        char = _make_char("rsi")
        eng.update(_make_report("2026-08-03", [char]))
        eng.update(_make_report("2026-08-04", [_make_char("rsi", date="2026-08-04")]))
        lib = eng.update(_make_report("2026-08-05", [_make_char("rsi", date="2026-08-05")]))
        ok(len(lib.drift_reports) >= 1)
        return f"drift_reports={len(lib.drift_reports)}"

    def t14_update_statistics_present():
        eng = _engine("u7")
        lib = eng.update(_make_report("2026-08-03", [_make_char("rsi")]))
        ok(isinstance(lib.statistics, ConsensusStatistics))
        return f"statistics type correct"

    # ── T15-T19: ConsensusDNA fields ──────────────────────────────────────────

    def t15_cdna_id_prefix():
        eng, lib = _engine_with_n_updates(1, tag="cd1")
        c = lib.all_consensus[0]
        ok(c.consensus_id.startswith("CON-"), c.consensus_id)
        return f"consensus_id={c.consensus_id}"

    def t16_cdna_direction():
        eng = _engine("cd2")
        char = _make_char("rsi", "WINNERS_LOWER")
        lib = eng.update(_make_report("2026-08-03", [char]))
        c = lib.all_consensus[0]
        ok(c.direction == SeparationDirection.WINNERS_LOWER)
        return f"direction={c.direction}"

    def t17_cdna_evidence_count():
        eng, lib = _engine_with_n_updates(3, tag="cd3")
        c = lib.all_consensus[0]
        ok(c.evidence_count == 3, c.evidence_count)
        return f"evidence_count={c.evidence_count}"

    def t18_cdna_first_seen_immutable():
        eng = _engine("cd4")
        eng.update(_make_report("2026-08-01", [_make_char("rsi", date="2026-08-01")]))
        lib = eng.update(_make_report("2026-08-02", [_make_char("rsi", date="2026-08-02")]))
        c = lib.all_consensus[0]
        ok(c.first_seen == "2026-08-01", c.first_seen)
        ok(c.last_seen  == "2026-08-02", c.last_seen)
        return f"first_seen={c.first_seen} last_seen={c.last_seen}"

    def t19_cdna_all_metrics_in_range():
        eng, lib = _engine_with_n_updates(3, tag="cd5")
        c = lib.all_consensus[0]
        ok(0.0 <= c.consensus_score      <= 1.0, c.consensus_score)
        ok(0.0 <= c.replication_frequency <= 1.0, c.replication_frequency)
        ok(0.0 <= c.temporal_stability   <= 1.0, c.temporal_stability)
        ok(0.0 <= c.regime_consistency   <= 1.0, c.regime_consistency)
        ok(0.0 <= c.sector_consistency   <= 1.0, c.sector_consistency)
        ok(0.0 <= c.feature_persistence  <= 1.0, c.feature_persistence)
        return "all metrics in [0,1]"

    # ── T20-T23: ConfidenceEvolution ──────────────────────────────────────────

    def t20_confidence_history_structure():
        eng, _ = _engine_with_n_updates(3, tag="ce1")
        evo_list = eng.confidence_history("rsi")
        ok(len(evo_list) == 1)
        evo = evo_list[0]
        ok(isinstance(evo, ConfidenceEvolution))
        ok(evo.feature_name == "rsi")
        return f"ConfidenceEvolution: {len(evo.points)} points"

    def t21_confidence_history_points_match_updates():
        eng, _ = _engine_with_n_updates(4, tag="ce2")
        evo_list = eng.confidence_history("rsi", level=ConsensusLevel.MASTER)
        ok(len(evo_list[0].points) == 4)
        return f"points={len(evo_list[0].points)}"

    def t22_confidence_history_trend_improving():
        eng = _engine("ce3")
        for i in range(4):
            conf = 0.50 + i * 0.10  # 0.50, 0.60, 0.70, 0.80 — slope=0.10 > thr=0.05
            char = _make_char("rsi", confidence=conf, date=f"2026-08-0{i+1}")
            eng.update(_make_report(f"2026-08-0{i+1}", [char]))
        evo_list = eng.confidence_history("rsi", level=ConsensusLevel.MASTER)
        ok(evo_list[0].trend_direction == "IMPROVING", evo_list[0].trend_direction)
        return f"trend={evo_list[0].trend_direction}"

    def t23_confidence_history_filter_by_direction():
        eng = _engine("ce4")
        eng.update(_make_report("2026-08-03", [
            _make_char("rsi", "WINNERS_HIGHER"),
            _make_char("rsi", "WINNERS_LOWER"),
        ]))
        evo_list = eng.confidence_history("rsi", direction="WINNERS_HIGHER")
        ok(len(evo_list) == 1)
        ok(evo_list[0].direction == "WINNERS_HIGHER")
        return f"filtered direction={evo_list[0].direction}"

    # ── T24-T27: DriftReport ──────────────────────────────────────────────────

    def t24_drift_report_structure():
        eng, lib = _engine_with_n_updates(3, tag="dr1")
        drs = lib.drift_reports
        ok(len(drs) >= 1)
        dr = drs[0]
        ok(isinstance(dr, DriftReport))
        ok(dr.drift_report_id.startswith("DRF-"))
        return f"DriftReport id={dr.drift_report_id}"

    def t25_drift_report_4_drift_types():
        eng, lib = _engine_with_n_updates(3, tag="dr2")
        dr = lib.drift_reports[0]
        types = {dm.drift_type for dm in dr.drifts}
        ok(DriftType.STATISTICAL in types)
        ok(DriftType.REGIME      in types)
        ok(DriftType.TEMPORAL    in types)
        ok(DriftType.FEATURE     in types)
        return f"drift types={[t.value for t in types]}"

    def t26_drift_magnitudes_in_range():
        eng, lib = _engine_with_n_updates(3, tag="dr3")
        for dr in lib.drift_reports:
            for dm in dr.drifts:
                ok(0.0 <= dm.magnitude <= 1.0, f"{dm.drift_type}: {dm.magnitude}")
        return "all drift magnitudes in [0,1]"

    def t27_drift_report_serialisation():
        eng, lib = _engine_with_n_updates(3, tag="dr4")
        dr = lib.drift_reports[0]
        d  = dr.to_dict()
        dr2 = DriftReport.from_dict(d)
        ok(dr2.drift_report_id == dr.drift_report_id)
        ok(len(dr2.drifts) == len(dr.drifts))
        return "DriftReport round-trip OK"

    # ── T28-T31: DNAStability ─────────────────────────────────────────────────

    def t28_stable_dna_empty_initially():
        eng = _engine("st1")
        ok(len(eng.stable_dna()) == 0)
        return "stable_dna empty before updates"

    def t29_stable_dna_after_consistent_updates():
        cfg = MLSConfig(
            min_universe_size=1, dna_min_group_size=2,
            consensus_stability_min_rep_freq=0.10,  # low so 3 updates qualify
            consensus_stability_min_temporal=0.10,
            consensus_stability_min_regime=0.10,
        )
        eng, _ = _engine_with_n_updates(3, tag="st2", cfg=cfg)
        stable = eng.stable_dna()
        ok(len(stable) >= 1)
        return f"stable_dna={len(stable)}"

    def t30_stable_dna_excludes_retired():
        eng = _engine("st3")
        eng.update(_make_report("2026-06-01", [_make_char("rsi", date="2026-06-01")]))
        # 63 days later — above retirement threshold
        eng.update(_make_report("2026-08-03", [_make_char("adx_score", date="2026-08-03")]))
        retired = eng.retired_dna()
        ok(any(c.feature_name == "rsi" for c in retired), "rsi should be retired")
        stable = eng.stable_dna()
        ok(all(c.feature_name != "rsi" for c in stable), "retired feature in stable_dna")
        return f"retired={len(retired)} stable={len(stable)}"

    def t31_retired_dna_correct():
        eng = _engine("st4")
        eng.update(_make_report("2026-06-01", [_make_char("rsi", date="2026-06-01")]))
        eng.update(_make_report("2026-08-03", [_make_char("adx_score", date="2026-08-03")]))
        retired = eng.retired_dna()
        ok(len(retired) >= 1)
        ok(all(c.consensus_state == ConsensusState.RETIRED for c in retired))
        return f"retired_count={len(retired)}"

    # ── T32-T35: ConsensusStatistics ──────────────────────────────────────────

    def t32_statistics_type():
        eng, lib = _engine_with_n_updates(1, tag="cs1")
        ok(isinstance(lib.statistics, ConsensusStatistics))
        return "ConsensusStatistics type correct"

    def t33_statistics_total_count():
        eng = _engine("cs2")
        chars = [_make_char("rsi"), _make_char("adx_score"), _make_char("mom_1d")]
        lib = eng.update(_make_report("2026-08-03", chars))
        ok(lib.statistics.total_consensus_dna == 3, lib.statistics.total_consensus_dna)
        return f"total_consensus_dna={lib.statistics.total_consensus_dna}"

    def t34_statistics_institutional_count():
        cfg = MLSConfig(min_universe_size=1, dna_min_group_size=2,
                        consensus_institutional_min_count=3,
                        consensus_institutional_min_score=0.0)
        eng, lib = _engine_with_n_updates(3, tag="cs3", cfg=cfg)
        ok(lib.statistics.institutional_count >= 1,
           f"expected >=1 institutional, got {lib.statistics.institutional_count}")
        return f"institutional_count={lib.statistics.institutional_count}"

    def t35_statistics_avg_score_positive():
        eng, lib = _engine_with_n_updates(3, tag="cs4")
        ok(lib.statistics.avg_consensus_score > 0.0)
        return f"avg_consensus_score={lib.statistics.avg_consensus_score}"

    # ── T36-T40: ConsensusLibrary model ───────────────────────────────────────

    def t36_library_round_trip():
        eng, lib = _engine_with_n_updates(3, tag="lr1")
        d    = lib.to_dict()
        lib2 = ConsensusLibrary.from_dict(d)
        ok(lib2.library_id  == lib.library_id)
        ok(lib2.as_of_date  == lib.as_of_date)
        ok(len(lib2.all_consensus) == len(lib.all_consensus))
        return "ConsensusLibrary round-trip OK"

    def t37_library_master_consensus_subset():
        cfg = MLSConfig(min_universe_size=1, dna_min_group_size=2,
                        consensus_institutional_min_count=2,
                        consensus_institutional_min_score=0.0)
        eng, lib = _engine_with_n_updates(2, tag="lr2", cfg=cfg)
        for c in lib.master_consensus:
            ok(c.consensus_state == ConsensusState.INSTITUTIONAL)
        return f"master_consensus={len(lib.master_consensus)}"

    def t38_library_drift_reports_count():
        eng, lib = _engine_with_n_updates(4, tag="lr3")
        ok(len(lib.drift_reports) == 1)  # 1 feature (rsi)
        return f"drift_reports={len(lib.drift_reports)}"

    def t39_library_statistics_in_dict():
        eng, lib = _engine_with_n_updates(1, tag="lr4")
        d = lib.to_dict()
        ok("statistics" in d)
        ok("total_consensus_dna" in d["statistics"])
        return "statistics present in dict"

    def t40_library_id_format():
        eng = _engine("lr5")
        lib = eng.update(_make_report("2026-08-03", [_make_char("rsi")]))
        ok(lib.library_id == "MLS-LIB-20260803")
        return f"library_id={lib.library_id}"

    # ── T41-T46: Lifecycle transitions ────────────────────────────────────────

    def t41_lifecycle_1_update_discovered():
        eng, lib = _engine_with_n_updates(1, tag="lc1")
        c = lib.all_consensus[0]
        ok(c.consensus_state == ConsensusState.DISCOVERED, c.consensus_state)
        return f"1 update → {c.consensus_state}"

    def t42_lifecycle_2_updates_replicated():
        eng, lib = _engine_with_n_updates(2, tag="lc2")
        c = lib.all_consensus[0]
        ok(c.consensus_state == ConsensusState.REPLICATED, c.consensus_state)
        return f"2 updates → {c.consensus_state}"

    def t43_lifecycle_5_updates_verified():
        eng, lib = _engine_with_n_updates(5, tag="lc3")
        c = lib.all_consensus[0]
        ok(c.consensus_state == ConsensusState.VERIFIED, c.consensus_state)
        return f"5 updates → {c.consensus_state}"

    def t44_lifecycle_10_updates_institutional():
        cfg = MLSConfig(min_universe_size=1, dna_min_group_size=2,
                        consensus_institutional_min_count=10,
                        consensus_institutional_min_score=0.0)
        eng, lib = _engine_with_n_updates(10, tag="lc4", cfg=cfg)
        c = lib.all_consensus[0]
        ok(c.consensus_state == ConsensusState.INSTITUTIONAL, c.consensus_state)
        return f"10 updates → {c.consensus_state}"

    def t45_lifecycle_drifting():
        """Alternating regimes → high regime_drift → DRIFTING."""
        cfg = MLSConfig(
            min_universe_size=1, dna_min_group_size=2,
            consensus_drift_threshold=0.30,
        )
        eng = _engine("lc5", cfg)
        regimes = ["bull_trend", "bear_trend"] * 8  # alternating
        for i, reg in enumerate(regimes):
            date = f"2026-07-{i + 1:02d}"
            char = _make_char("rsi", date=date, regime=reg)
            lib  = eng.update(_make_report(date, [char], reg))
        c = lib.all_consensus[0]
        ok(c.consensus_state == ConsensusState.DRIFTING,
           f"expected DRIFTING, got {c.consensus_state} (drift measures may need tuning)")
        return f"alternating regimes → {c.consensus_state}"

    def t46_lifecycle_retired():
        """Feature absent for 35 days → RETIRED."""
        eng = _engine("lc6")
        eng.update(_make_report("2026-06-01", [_make_char("rsi", date="2026-06-01")]))
        # next update 35 days later — rsi is absent
        lib = eng.update(_make_report("2026-07-06", [_make_char("adx_score", date="2026-07-06")]))
        rsi_entry = next((c for c in lib.all_consensus if c.feature_name == "rsi"), None)
        ok(rsi_entry is not None)
        ok(rsi_entry.consensus_state == ConsensusState.RETIRED,
           f"expected RETIRED, got {rsi_entry.consensus_state}")
        return f"35-day absence → {rsi_entry.consensus_state}"

    # ── T47-T51: Consensus score math ─────────────────────────────────────────

    def t47_score_perfect_inputs():
        cfg = MLSConfig()
        s = _consensus_score(1.0, 1.0, 1.0, 1.0, 1.0, 1.0, cfg)
        ok(abs(s - 1.0) < 1e-9, s)
        return f"perfect score={s:.6f}"

    def t48_score_zero_inputs():
        cfg = MLSConfig()
        # trend=0 → trend_score=0.5, so score = w_confidence*0.5
        s = _consensus_score(0.0, 0.0, 0.0, 0.0, 0.0, 0.0, cfg)
        expected = cfg.consensus_w_confidence * 0.5
        ok(abs(s - expected) < 1e-9, f"s={s} expected={expected}")
        return f"zero inputs score={s:.6f}"

    def t49_score_weights_covered():
        cfg = MLSConfig()
        s = _consensus_score(1.0, 0.0, 0.0, 0.0, 0.0, 0.0, cfg)
        ok(abs(s - cfg.consensus_w_replication - cfg.consensus_w_confidence * 0.5) < 1e-9)
        return f"replication component correct"

    def t50_score_positive_trend_boosts():
        cfg = MLSConfig(consensus_trend_declining_slope=0.05)
        # trend = +0.05 → trend_score = 0.5 + 0.05/(2*0.05) = 1.0
        s_high = _consensus_score(0.5, 0.5, 0.5, 0.5,  0.05, 0.5, cfg)
        s_flat = _consensus_score(0.5, 0.5, 0.5, 0.5,  0.00, 0.5, cfg)
        ok(s_high > s_flat, f"high={s_high:.4f} flat={s_flat:.4f}")
        return f"positive trend boosts score by {s_high - s_flat:.4f}"

    def t51_score_clamped_0_to_1():
        cfg = MLSConfig()
        s = _consensus_score(1.5, 1.5, 1.5, 1.5, 100.0, 1.5, cfg)
        ok(s <= 1.0 + 1e-9, s)
        return f"score not meaningfully above 1.0: {s:.6f}"

    # ── T52-T55: Temporal stability math ──────────────────────────────────────

    def t52_temporal_stability_single_obs():
        ok(_temporal_stability([5.0]) == 1.0)
        return "single obs → 1.0"

    def t53_temporal_stability_all_same():
        ok(_temporal_stability([5.0, 5.0, 5.0, 5.0]) == 1.0)
        return "all same → 1.0"

    def t54_temporal_stability_high_variation():
        s = _temporal_stability([1.0, 10.0, 1.0, 10.0])
        ok(s < 0.5, f"high variation should give stability<0.5, got {s:.4f}")
        return f"high variation → stability={s:.4f}"

    def t55_temporal_stability_moderate_variation():
        s = _temporal_stability([5.0, 5.1, 4.9, 5.05])
        ok(s > 0.95, f"low CV → high stability, got {s:.4f}")
        return f"moderate variation → stability={s:.4f}"

    # ── T56-T59: Regime consistency ───────────────────────────────────────────

    def t56_regime_consistency_1_regime():
        rc = {"bull_trend": 5}
        r = _regime_consistency(rc)
        ok(abs(r - 1 / _N_KNOWN_REGIMES) < 1e-9, r)
        return f"1 regime → {r:.4f}"

    def t57_regime_consistency_3_regimes():
        rc = {"bull_trend": 3, "bear_trend": 2, "range_bound": 1}
        r = _regime_consistency(rc)
        ok(abs(r - 3 / _N_KNOWN_REGIMES) < 1e-9, r)
        return f"3 regimes → {r:.4f}"

    def t58_regime_consistency_all_5():
        rc = {"a": 1, "b": 1, "c": 1, "d": 1, "e": 1}
        r = _regime_consistency(rc)
        ok(r == 1.0, r)
        return f"5 regimes → {r:.4f}"

    def t59_regime_consistency_empty():
        ok(_regime_consistency({}) == 0.0)
        return "empty → 0.0"

    # ── T60-T63: Drift detection ──────────────────────────────────────────────

    def t60_statistical_drift_large_shift():
        prior  = [5.0] * 7
        recent = [1.0] * 7
        d = _statistical_drift(prior + recent, 7)
        ok(d > 0.50, f"large shift should give high drift, got {d:.4f}")
        return f"large shift → statistical_drift={d:.4f}"

    def t61_regime_drift_alternating():
        obs = [{"regime": ("bull" if i % 2 == 0 else "bear")} for i in range(10)]
        d = _regime_drift(obs)
        ok(d > 0.80, f"alternating regimes → drift={d:.4f}")
        return f"alternating → regime_drift={d:.4f}"

    def t62_temporal_drift_declining():
        # Prior window (days 7-13 ago) had 7 appearances; recent (0-6 days ago) had 0
        as_of = "2026-08-03"
        prior_dates  = [f"2026-07-{27 - i:02d}" for i in range(7)]  # 27,26,...,21
        recent_dates: list = []
        d = _temporal_drift(prior_dates + recent_dates, 7, as_of)
        ok(d > 0.50, f"declining frequency → temporal_drift={d:.4f}")
        return f"declining → temporal_drift={d:.4f}"

    def t63_feature_drift_declining_confidence():
        confs = [0.90, 0.85, 0.80, 0.75, 0.70, 0.65, 0.60]
        d = _feature_drift(confs, 7, 0.05)
        ok(d > 0.0, f"declining confidence → feature_drift={d:.4f}")
        return f"declining conf → feature_drift={d:.4f}"

    # ── T64-T67: Confidence trend ─────────────────────────────────────────────

    def t64_trend_slope_positive():
        slope = _trend_slope([1.0, 2.0, 3.0, 4.0, 5.0])
        ok(slope > 0.0, slope)
        return f"positive slope={slope:.4f}"

    def t65_trend_slope_negative():
        slope = _trend_slope([5.0, 4.0, 3.0, 2.0, 1.0])
        ok(slope < 0.0, slope)
        return f"negative slope={slope:.4f}"

    def t66_trend_slope_flat():
        slope = _trend_slope([3.0, 3.0, 3.0, 3.0])
        ok(abs(slope) < 1e-9, slope)
        return f"flat slope={slope}"

    def t67_trend_slope_single_point():
        ok(_trend_slope([5.0]) == 0.0)
        return "single point → 0.0"

    # ── T68-T71: Storage ──────────────────────────────────────────────────────

    def t68_storage_persist_on_update():
        eng = _engine("sg1")
        eng.update(_make_report("2026-08-03", [_make_char("rsi")]))
        ok(eng._lib_path.exists())
        return f"library.json created"

    def t69_storage_load_after_update():
        eng = _engine("sg2")
        eng.update(_make_report("2026-08-03", [_make_char("rsi")]))
        lib2 = eng.master_library()
        ok(lib2.as_of_date == "2026-08-03")
        return f"load_after_update: as_of={lib2.as_of_date}"

    def t70_storage_accumulates():
        eng = _engine("sg3")
        for i in range(3):
            date = f"2026-08-0{i+1}"
            eng.update(_make_report(date, [_make_char("rsi", date=date)]))
        lib = eng.master_library()
        c = next(c for c in lib.all_consensus if c.feature_name == "rsi")
        ok(c.evidence_count == 3, c.evidence_count)
        return f"accumulated evidence_count={c.evidence_count}"

    def t71_storage_bak_on_overwrite():
        eng = _engine("sg4")
        eng.update(_make_report("2026-08-03", [_make_char("rsi")]))
        eng.update(_make_report("2026-08-04", [_make_char("rsi", date="2026-08-04")]))
        ok(eng._lib_path.with_suffix(".bak").exists())
        return ".bak file created on overwrite"

    # ── T72-T75: Query API ────────────────────────────────────────────────────

    def t72_query_stable_dna():
        cfg = MLSConfig(min_universe_size=1, dna_min_group_size=2,
                        consensus_stability_min_rep_freq=0.10,
                        consensus_stability_min_temporal=0.10,
                        consensus_stability_min_regime=0.10)
        eng, _ = _engine_with_n_updates(3, tag="qa1", cfg=cfg)
        stable = eng.stable_dna()
        ok(len(stable) >= 1)
        return f"stable_dna={len(stable)}"

    def t73_query_retired_dna():
        eng = _engine("qa2")
        eng.update(_make_report("2026-06-01", [_make_char("rsi", date="2026-06-01")]))
        eng.update(_make_report("2026-08-03", [_make_char("adx_score", date="2026-08-03")]))
        retired = eng.retired_dna()
        ok(len(retired) >= 1)
        ok(all(c.consensus_state == ConsensusState.RETIRED for c in retired))
        return f"retired_dna={len(retired)}"

    def t74_query_confidence_history():
        eng, _ = _engine_with_n_updates(4, tag="qa3")
        evo = eng.confidence_history("rsi")
        ok(len(evo) == 1)
        ok(evo[0].feature_name == "rsi")
        return f"confidence_history: {len(evo[0].points)} points"

    def t75_query_drift_report_filter():
        eng = _engine("qa4")
        chars = [_make_char("rsi"), _make_char("adx_score")]
        eng.update(_make_report("2026-08-03", chars))
        eng.update(_make_report("2026-08-04", [
            _make_char("rsi", date="2026-08-04"),
            _make_char("adx_score", date="2026-08-04"),
        ]))
        drs = eng.drift_report(feature_name="rsi")
        ok(all(dr.feature_name == "rsi" for dr in drs))
        return f"filtered drift_report: {len(drs)} reports for rsi"

    # ── T76-T80: master_library() ─────────────────────────────────────────────

    def t76_master_library_type():
        eng, _ = _engine_with_n_updates(1, tag="ml1")
        lib = eng.master_library()
        ok(isinstance(lib, ConsensusLibrary))
        return "master_library() type correct"

    def t77_master_library_master_consensus_institutional_only():
        cfg = MLSConfig(min_universe_size=1, dna_min_group_size=2,
                        consensus_institutional_min_count=2,
                        consensus_institutional_min_score=0.0)
        eng, _ = _engine_with_n_updates(2, tag="ml2", cfg=cfg)
        lib = eng.master_library()
        for c in lib.master_consensus:
            ok(c.consensus_state == ConsensusState.INSTITUTIONAL)
        return f"master_consensus all INSTITUTIONAL: {len(lib.master_consensus)}"

    def t78_master_library_statistics():
        eng, _ = _engine_with_n_updates(2, tag="ml3")
        lib = eng.master_library()
        ok(lib.statistics.total_consensus_dna >= 1)
        return f"statistics present: total={lib.statistics.total_consensus_dna}"

    def t79_master_library_empty_before_update():
        eng = _engine("ml4")
        lib = eng.master_library()
        ok(lib.library_id == "MLS-LIB-EMPTY")
        ok(len(lib.all_consensus) == 0)
        return "empty library before any update"

    def t80_master_library_library_id_format():
        eng = _engine("ml5")
        lib = eng.update(_make_report("2026-08-03", [_make_char("rsi")]))
        lib2 = eng.master_library()
        ok(lib2.library_id == "MLS-LIB-20260803", lib2.library_id)
        return f"library_id={lib2.library_id}"

    # ── T81-T86: Traceability ─────────────────────────────────────────────────

    def t81_all_observations_trace_every_update():
        eng = _engine("tr1")
        dates = ["2026-08-01", "2026-08-02", "2026-08-03"]
        for d in dates:
            eng.update(_make_report(d, [_make_char("rsi", date=d)]))
        lib = eng.master_library()
        c   = next(x for x in lib.all_consensus if x.feature_name == "rsi")
        obs_dates = {o["date"] for o in c.all_observations}
        for d in dates:
            ok(d in obs_dates, f"date {d} missing from all_observations")
        return f"all_observations traces {len(obs_dates)} dates"

    def t82_regime_counts_accurate():
        eng = _engine("tr2")
        eng.update(_make_report("2026-08-01",
                                [_make_char("rsi", date="2026-08-01", regime="bull_trend")],
                                "bull_trend"))
        eng.update(_make_report("2026-08-02",
                                [_make_char("rsi", date="2026-08-02", regime="bear_trend")],
                                "bear_trend"))
        eng.update(_make_report("2026-08-03",
                                [_make_char("rsi", date="2026-08-03", regime="bull_trend")],
                                "bull_trend"))
        lib = eng.master_library()
        c   = next(x for x in lib.all_consensus if x.feature_name == "rsi")
        ok(c.regime_counts.get("bull_trend", 0) == 2, c.regime_counts)
        ok(c.regime_counts.get("bear_trend", 0) == 1, c.regime_counts)
        return f"regime_counts={c.regime_counts}"

    def t83_first_seen_immutable_across_updates():
        eng = _engine("tr3")
        eng.update(_make_report("2026-08-01", [_make_char("rsi", date="2026-08-01")]))
        for d in ["2026-08-02", "2026-08-03", "2026-08-04"]:
            eng.update(_make_report(d, [_make_char("rsi", date=d)]))
        lib = eng.master_library()
        c   = next(x for x in lib.all_consensus if x.feature_name == "rsi")
        ok(c.first_seen == "2026-08-01", c.first_seen)
        return f"first_seen={c.first_seen} (unchanged)"

    def t84_evidence_count_equals_observations_len():
        eng, lib = _engine_with_n_updates(5, tag="tr4")
        c = lib.all_consensus[0]
        ok(c.evidence_count == len(c.all_observations),
           f"count={c.evidence_count} obs={len(c.all_observations)}")
        return f"evidence_count={c.evidence_count} == len(all_observations)"

    def t85_consensus_id_deterministic():
        id1 = _make_consensus_id("rsi", SeparationDirection.WINNERS_HIGHER)
        id2 = _make_consensus_id("rsi", SeparationDirection.WINNERS_HIGHER)
        id3 = _make_consensus_id("rsi", SeparationDirection.WINNERS_LOWER)
        ok(id1 == id2, "same inputs → same id")
        ok(id1 != id3, "different direction → different id")
        return f"id={id1} deterministic"

    def t86_drift_report_traceable_by_feature():
        eng = _engine("tr5")
        for d in ["2026-08-01", "2026-08-02", "2026-08-03"]:
            eng.update(_make_report(d, [
                _make_char("rsi", date=d),
                _make_char("adx_score", date=d),
            ]))
        lib = eng.master_library()
        rsi_reports = [dr for dr in lib.drift_reports if dr.feature_name == "rsi"]
        adx_reports = [dr for dr in lib.drift_reports if dr.feature_name == "adx_score"]
        ok(len(rsi_reports) == 1)
        ok(len(adx_reports) == 1)
        return "one drift_report per feature"

    # ── T87-T90: Thread safety ────────────────────────────────────────────────

    def t87_concurrent_updates_isolated_dirs():
        """8 threads, each with its own engine and data_dir — all must succeed."""
        errors = []

        def worker(i: int) -> None:
            try:
                eng = _engine(f"ts_{i}")
                for j in range(3):
                    date = f"2026-08-0{j + 1}"
                    eng.update(_make_report(date, [_make_char("rsi", date=date)]))
            except Exception as exc:
                errors.append(str(exc))

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        ok(len(errors) == 0, f"errors: {errors}")
        return "8/8 concurrent engines succeeded"

    def t88_update_idempotent_same_date():
        """Calling update() twice with the same trading_date must not double-count."""
        eng = _engine("ts2")
        char = _make_char("rsi")
        r1 = _make_report("2026-08-03", [char])
        eng.update(r1)
        lib = eng.update(r1)   # same date again
        c   = next(x for x in lib.all_consensus if x.feature_name == "rsi")
        ok(c.evidence_count == 1, f"expected 1, got {c.evidence_count}")
        return f"idempotent: evidence_count={c.evidence_count}"

    def t89_statistics_callable_concurrently():
        """statistics() is read-only and must not raise during concurrent update()."""
        eng = _engine("ts3")
        errors = []

        def updater():
            for i in range(5):
                date = f"2026-08-0{i + 1}"
                try:
                    eng.update(_make_report(date, [_make_char("rsi", date=date)]))
                except Exception as exc:
                    errors.append(f"update: {exc}")

        def reader():
            for _ in range(5):
                try:
                    eng.statistics()
                except Exception as exc:
                    errors.append(f"stats: {exc}")

        t1 = threading.Thread(target=updater)
        t2 = threading.Thread(target=reader)
        t1.start(); t2.start()
        t1.join();  t2.join()
        ok(len(errors) == 0, f"errors: {errors}")
        return "concurrent read/write: no errors"

    def t90_master_library_thread_safe():
        """master_library() should not race with update()."""
        eng = _engine("ts4")
        errors = []
        seen_libs = []

        def updater():
            for i in range(4):
                date = f"2026-08-0{i + 1}"
                try:
                    eng.update(_make_report(date, [_make_char("rsi", date=date)]))
                except Exception as exc:
                    errors.append(str(exc))

        def reader():
            for _ in range(4):
                try:
                    lib = eng.master_library()
                    seen_libs.append(lib)
                except Exception as exc:
                    errors.append(str(exc))

        t1 = threading.Thread(target=updater)
        t2 = threading.Thread(target=reader)
        t1.start(); t2.start()
        t1.join();  t2.join()
        ok(len(errors) == 0, f"errors: {errors}")
        ok(len(seen_libs) == 4)
        return f"master_library thread-safe: {len(seen_libs)} reads"

    # ── Register all 90 tests ─────────────────────────────────────────────────

    print("=" * 72)
    tests = [
        ("T01 MLSConfig Phase 4 defaults",             t01_phase4_defaults),
        ("T02 MLSConfig drift defaults",               t02_phase4_drift_defaults),
        ("T03 MLSConfig weights sum to 1",             t03_phase4_weights_sum_to_1),
        ("T04 MLSConfig overrides",                    t04_phase4_overrides),
        ("T05 Engine default init",                    t05_engine_default_init),
        ("T06 Engine custom config",                   t06_engine_custom_config),
        ("T07 Engine custom data_dir",                 t07_engine_custom_data_dir),
        ("T08 update() returns ConsensusLibrary",      t08_update_returns_consensus_library),
        ("T09 update() library_id format",             t09_update_library_id_format),
        ("T10 update() as_of_date",                    t10_update_as_of_date),
        ("T11 update() all_consensus nonempty",        t11_update_all_consensus_nonempty),
        ("T12 update() persists JSON",                 t12_update_persists_json),
        ("T13 update() drift_reports built",           t13_update_drift_reports_built),
        ("T14 update() statistics present",            t14_update_statistics_present),
        ("T15 ConsensusDNA id prefix CON-",            t15_cdna_id_prefix),
        ("T16 ConsensusDNA direction",                 t16_cdna_direction),
        ("T17 ConsensusDNA evidence_count",            t17_cdna_evidence_count),
        ("T18 ConsensusDNA first_seen immutable",      t18_cdna_first_seen_immutable),
        ("T19 ConsensusDNA all metrics in [0,1]",      t19_cdna_all_metrics_in_range),
        ("T20 ConfidenceEvolution structure",          t20_confidence_history_structure),
        ("T21 ConfidenceEvolution points count",       t21_confidence_history_points_match_updates),
        ("T22 ConfidenceEvolution IMPROVING trend",    t22_confidence_history_trend_improving),
        ("T23 ConfidenceEvolution direction filter",   t23_confidence_history_filter_by_direction),
        ("T24 DriftReport structure",                  t24_drift_report_structure),
        ("T25 DriftReport 4 drift types",              t25_drift_report_4_drift_types),
        ("T26 DriftReport magnitudes in [0,1]",        t26_drift_magnitudes_in_range),
        ("T27 DriftReport serialisation",              t27_drift_report_serialisation),
        ("T28 stable_dna empty initially",             t28_stable_dna_empty_initially),
        ("T29 stable_dna after consistent updates",    t29_stable_dna_after_consistent_updates),
        ("T30 stable_dna excludes retired",            t30_stable_dna_excludes_retired),
        ("T31 retired_dna correct",                    t31_retired_dna_correct),
        ("T32 ConsensusStatistics type",               t32_statistics_type),
        ("T33 ConsensusStatistics total_count",        t33_statistics_total_count),
        ("T34 ConsensusStatistics institutional_count",t34_statistics_institutional_count),
        ("T35 ConsensusStatistics avg_score positive", t35_statistics_avg_score_positive),
        ("T36 ConsensusLibrary round-trip",            t36_library_round_trip),
        ("T37 ConsensusLibrary master subset",         t37_library_master_consensus_subset),
        ("T38 ConsensusLibrary drift_reports count",   t38_library_drift_reports_count),
        ("T39 ConsensusLibrary statistics in dict",    t39_library_statistics_in_dict),
        ("T40 ConsensusLibrary library_id format",     t40_library_id_format),
        ("T41 lifecycle: 1 update -> DISCOVERED",      t41_lifecycle_1_update_discovered),
        ("T42 lifecycle: 2 updates -> REPLICATED",     t42_lifecycle_2_updates_replicated),
        ("T43 lifecycle: 5 updates -> VERIFIED",       t43_lifecycle_5_updates_verified),
        ("T44 lifecycle: 10 updates -> INSTITUTIONAL", t44_lifecycle_10_updates_institutional),
        ("T45 lifecycle: drift -> DRIFTING",           t45_lifecycle_drifting),
        ("T46 lifecycle: absent 35d -> RETIRED",       t46_lifecycle_retired),
        ("T47 consensus_score: perfect inputs",        t47_score_perfect_inputs),
        ("T48 consensus_score: zero inputs",           t48_score_zero_inputs),
        ("T49 consensus_score: weights covered",       t49_score_weights_covered),
        ("T50 consensus_score: positive trend boosts", t50_score_positive_trend_boosts),
        ("T51 consensus_score: clamped <= 1",          t51_score_clamped_0_to_1),
        ("T52 temporal_stability: single obs -> 1.0",  t52_temporal_stability_single_obs),
        ("T53 temporal_stability: all same -> 1.0",    t53_temporal_stability_all_same),
        ("T54 temporal_stability: high variation",     t54_temporal_stability_high_variation),
        ("T55 temporal_stability: moderate variation", t55_temporal_stability_moderate_variation),
        ("T56 regime_consistency: 1 regime",           t56_regime_consistency_1_regime),
        ("T57 regime_consistency: 3 regimes",          t57_regime_consistency_3_regimes),
        ("T58 regime_consistency: 5 regimes",          t58_regime_consistency_all_5),
        ("T59 regime_consistency: empty",              t59_regime_consistency_empty),
        ("T60 statistical_drift: large shift",         t60_statistical_drift_large_shift),
        ("T61 regime_drift: alternating regimes",      t61_regime_drift_alternating),
        ("T62 temporal_drift: declining frequency",    t62_temporal_drift_declining),
        ("T63 feature_drift: declining confidence",    t63_feature_drift_declining_confidence),
        ("T64 trend_slope: positive",                  t64_trend_slope_positive),
        ("T65 trend_slope: negative",                  t65_trend_slope_negative),
        ("T66 trend_slope: flat",                      t66_trend_slope_flat),
        ("T67 trend_slope: single point",              t67_trend_slope_single_point),
        ("T68 storage: persist on update",             t68_storage_persist_on_update),
        ("T69 storage: load after update",             t69_storage_load_after_update),
        ("T70 storage: accumulates across updates",    t70_storage_accumulates),
        ("T71 storage: .bak on overwrite",             t71_storage_bak_on_overwrite),
        ("T72 query API: stable_dna()",                t72_query_stable_dna),
        ("T73 query API: retired_dna()",               t73_query_retired_dna),
        ("T74 query API: confidence_history()",        t74_query_confidence_history),
        ("T75 query API: drift_report(filter)",        t75_query_drift_report_filter),
        ("T76 master_library() type",                  t76_master_library_type),
        ("T77 master_library() master subset",         t77_master_library_master_consensus_institutional_only),
        ("T78 master_library() statistics",            t78_master_library_statistics),
        ("T79 master_library() empty before update",   t79_master_library_empty_before_update),
        ("T80 master_library() library_id format",     t80_master_library_library_id_format),
        ("T81 traceability: all_observations audit",   t81_all_observations_trace_every_update),
        ("T82 traceability: regime_counts accurate",   t82_regime_counts_accurate),
        ("T83 traceability: first_seen immutable",     t83_first_seen_immutable_across_updates),
        ("T84 traceability: evidence_count == len(obs)",t84_evidence_count_equals_observations_len),
        ("T85 traceability: consensus_id deterministic",t85_consensus_id_deterministic),
        ("T86 traceability: drift traceable by feature",t86_drift_report_traceable_by_feature),
        ("T87 thread safety: 8 isolated engines",      t87_concurrent_updates_isolated_dirs),
        ("T88 thread safety: idempotent same date",    t88_update_idempotent_same_date),
        ("T89 thread safety: concurrent read/write",   t89_statistics_callable_concurrently),
        ("T90 thread safety: master_library() safe",   t90_master_library_thread_safe),
    ]

    for name, fn in tests:
        runner.run(name, fn)

    return runner.report()


if __name__ == "__main__":
    sys.exit(main())
