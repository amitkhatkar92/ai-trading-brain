"""
test_pmci_engine.py — MLS Phase 5 test suite.

Covers:
    MLSConfig Phase 5 fields    — defaults, weight sums, thresholds
    Engine init                 — default, custom config
    PMCIResult structure        — id, date, score bounds, component count
    PMCIComponent structure     — names, values, weights, weighted_values
    PMCIEvidence structure      — fields, contribution formula, flags
    PMCIBreakdown structure     — matched/missing/conflicting, serialisation
    _align() math               — WINNERS_HIGHER/LOWER, clamp, midpoint
    Winner match computation    — all-match, all-miss, mixed, weighting
    Loser match / contradiction — complement invariant, penalty effect
    Evidence strength           — score weighting, matched-only
    Regime/sector stability     — regime_consistency, sector_consistency
    DNA freshness               — linear decay, boundary values
    Knowledge coverage          — present fraction, neutral DNA included
    PMCI formula                — clamping, score bounds, penalty
    evaluate_universe()         — batch, length, skip on error, empty
    top_matches()               — ranking, n limit, fewer-than-n
    statistics()                — counts, averages, top_symbol, empty
    Explainability              — sorted breakdown, explanation text
    evaluate_symbol()           — symbol lookup, None for absent, regime
    Edge cases                  — RETIRED excluded, empty library

Run:
    python test_pmci_engine.py
"""
from __future__ import annotations

import dataclasses
import hashlib
import sys
import time
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from market_learning import (
    MLSConfig,
    PMCIEngine,
    PMCIBreakdown,
    PMCIComponent,
    PMCIEvidence,
    PMCIResult,
    PMCIStatistics,
    ConsensusDNA,
    ConsensusLevel,
    ConsensusLibrary,
    ConsensusState,
    ConsensusStatistics,
    SeparationDirection,
)
from market_learning.market_observer_models import (
    DailyMarketSnapshot,
    MarketObservation,
    ObservationMetadata,
)
from market_learning.pmci_engine import _align, _clamp, _freshness, _make_pmci_id, _mean


# ═════════════════════════════════════════════════════════════════════════════
# Test framework (same pattern as Phases 3 and 4)
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


def _make_obs(
    symbol: str = "TEST",
    features: Optional[Dict[str, float]] = None,
    date: str = "2026-08-04",
) -> MarketObservation:
    f = features or {"rsi": 0.75, "mom_1d": 0.70}
    return MarketObservation(
        symbol=symbol,
        feature_timestamp=f"{date}T09:15:00",
        features=f,
        feature_count=len(f),
    )


def _make_cdna(
    feature: str,
    direction: str = "WINNERS_HIGHER",
    state: str = "INSTITUTIONAL",
    score: float = 0.80,
    regime_cons: float = 0.80,
    sector_cons: float = 0.80,
    conf_trend: float = 0.10,
    last_seen: str = "2026-08-03",
    evidence_count: int = 15,
) -> ConsensusDNA:
    dir_ = SeparationDirection(direction)
    h    = hashlib.sha256(f"{feature}::{direction}".encode()).hexdigest()[:8]
    st   = ConsensusState(state)
    lvl  = ConsensusLevel.MASTER if st == ConsensusState.INSTITUTIONAL else ConsensusLevel.WEEKLY
    return ConsensusDNA(
        consensus_id=f"CON-{h}",
        feature_name=feature,
        direction=dir_,
        consensus_state=st,
        consensus_score=score,
        replication_frequency=0.80,
        evidence_count=evidence_count,
        temporal_stability=0.80,
        regime_consistency=regime_cons,
        sector_consistency=sector_cons,
        confidence_trend=conf_trend,
        feature_persistence=0.80,
        first_seen="2026-01-01",
        last_seen=last_seen,
        all_observations=[],
        regime_counts={"bull_trend": evidence_count},
        level=lvl,
    )


def _make_library(
    dna_list: List[ConsensusDNA],
    date: str = "2026-08-03",
) -> ConsensusLibrary:
    master = [c for c in dna_list if c.consensus_state == ConsensusState.INSTITUTIONAL]
    scores = [c.consensus_score for c in dna_list]
    return ConsensusLibrary(
        library_id=f"MLS-LIB-{date.replace('-', '')}",
        as_of_date=date,
        all_consensus=dna_list,
        master_consensus=master,
        drift_reports=[],
        statistics=ConsensusStatistics(
            as_of_date=date,
            total_consensus_dna=len(dna_list),
            institutional_count=len(master),
            weakening_count=0,
            drifting_count=0,
            retired_count=0,
            avg_consensus_score=sum(scores) / max(1, len(scores)),
            avg_replication_freq=0.80,
            top_institutional_feature=master[0].feature_name if master else None,
        ),
    )


def _make_metadata(date: str = "2026-08-04") -> ObservationMetadata:
    return ObservationMetadata(
        run_id=f"MLS-OBS-{date.replace('-', '')}-091500",
        trading_date=date,
        capture_time=f"{date}T09:15:00",
        universe_size=50,
        feature_count=10,
        snapshot_id=f"MLS-SNAP-{date.replace('-', '')}",
        temporal_contract_verified=True,
        regime="bull_trend",
        volatility="medium",
        vix=15.0,
        pcr=0.9,
        breadth=0.6,
        global_bias=0.5,
        mls_config_hash="abcd1234abcd1234",
    )


def _make_snapshot(
    obs_list: List[MarketObservation],
    date: str = "2026-08-04",
    regime: str = "bull_trend",
) -> DailyMarketSnapshot:
    return DailyMarketSnapshot(
        snapshot_id=f"MLS-SNAP-{date.replace('-', '')}",
        trading_date=date,
        feature_timestamp=f"{date}T09:15:00",
        regime=regime,
        volatility="medium",
        vix=15.0,
        pcr=0.9,
        breadth=0.6,
        global_bias=0.5,
        universe_size=len(obs_list),
        symbols=[o.symbol for o in obs_list],
        observations=obs_list,
        metadata=_make_metadata(date),
        created_at=f"{date}T09:15:00",
    )


def _engine(cfg: Optional[MLSConfig] = None) -> PMCIEngine:
    return PMCIEngine(config=cfg or _TEST_CFG)


def _winner_library(features: List[str] = None, score: float = 0.80) -> ConsensusLibrary:
    """Library of INSTITUTIONAL WINNERS_HIGHER DNA for the given features."""
    feats = features or ["rsi", "mom_1d"]
    return _make_library([_make_cdna(f, score=score) for f in feats])


# ═════════════════════════════════════════════════════════════════════════════
# Tests
# ═════════════════════════════════════════════════════════════════════════════

def main() -> int:
    runner = TestRunner()

    # ── T01-T05: MLSConfig Phase 5 defaults ──────────────────────────────────

    def t01_pmci_winner_weight():
        cfg = MLSConfig()
        ok(cfg.pmci_w_winner == 0.35, cfg.pmci_w_winner)
        return f"pmci_w_winner={cfg.pmci_w_winner}"

    def t02_pmci_loser_penalty():
        cfg = MLSConfig()
        ok(cfg.pmci_w_loser == 0.25, cfg.pmci_w_loser)
        return f"pmci_w_loser={cfg.pmci_w_loser}"

    def t03_pmci_positive_weights_sum_to_1():
        cfg = MLSConfig()
        total = (cfg.pmci_w_winner + cfg.pmci_w_evidence + cfg.pmci_w_regime
                 + cfg.pmci_w_sector + cfg.pmci_w_trend + cfg.pmci_w_freshness
                 + cfg.pmci_w_coverage + cfg.pmci_w_neutral)
        ok(abs(total - 1.0) < 1e-9, f"sum={total}")
        return f"positive weights sum={total:.9f}"

    def t04_pmci_thresholds():
        cfg = MLSConfig()
        ok(cfg.pmci_high_similarity_threshold == 0.70)
        ok(cfg.pmci_low_similarity_threshold  == 0.30)
        ok(cfg.pmci_freshness_days == 30)
        ok(cfg.pmci_feature_midpoint == 0.50)
        return "thresholds correct"

    def t05_pmci_config_overrides():
        cfg = MLSConfig(pmci_w_winner=0.40, pmci_high_similarity_threshold=0.80)
        ok(cfg.pmci_w_winner == 0.40)
        ok(cfg.pmci_high_similarity_threshold == 0.80)
        return "overrides applied"

    # ── T06-T08: Engine init ──────────────────────────────────────────────────

    def t06_engine_default_init():
        eng = PMCIEngine()
        ok(eng is not None)
        return "default init OK"

    def t07_engine_custom_config():
        cfg = MLSConfig(pmci_w_winner=0.40)
        eng = PMCIEngine(config=cfg)
        ok(eng._cfg.pmci_w_winner == 0.40)
        return "custom config assigned"

    def t08_engine_is_readonly():
        eng     = _engine()
        lib     = _winner_library()
        obs     = _make_obs()
        before  = len(lib.all_consensus)
        eng.evaluate(obs, lib)
        ok(len(lib.all_consensus) == before, "library was mutated!")
        return "library not mutated"

    # ── T09-T13: PMCIResult structure ─────────────────────────────────────────

    def t09_result_id_prefix():
        eng = _engine()
        lib = _winner_library()
        res = eng.evaluate(_make_obs(), lib)
        ok(res.result_id.startswith("PMC-"), res.result_id)
        return f"result_id={res.result_id}"

    def t10_result_evaluation_date():
        eng = _engine()
        lib = _winner_library()
        res = eng.evaluate(_make_obs(date="2026-08-04"), lib, evaluation_date="2026-08-04")
        ok(res.evaluation_date == "2026-08-04", res.evaluation_date)
        return f"evaluation_date={res.evaluation_date}"

    def t11_result_pmci_score_in_range():
        eng = _engine()
        lib = _winner_library()
        res = eng.evaluate(_make_obs(), lib)
        ok(0.0 <= res.pmci_score <= 1.0, res.pmci_score)
        return f"pmci_score={res.pmci_score:.6f}"

    def t12_result_has_nine_components():
        eng = _engine()
        lib = _winner_library()
        res = eng.evaluate(_make_obs(), lib)
        ok(len(res.components) == 9, len(res.components))
        return f"components={len(res.components)}"

    def t13_result_explanation_nonempty():
        eng = _engine()
        lib = _winner_library()
        res = eng.evaluate(_make_obs(), lib)
        ok(len(res.explanation) > 20, res.explanation[:60])
        return f"explanation length={len(res.explanation)}"

    # ── T14-T18: PMCIComponent structure ──────────────────────────────────────

    def t14_component_names_correct():
        eng = _engine()
        lib = _winner_library()
        res = eng.evaluate(_make_obs(), lib)
        names = {c.name for c in res.components}
        expected = {
            "winner_match", "loser_match", "neutral_match",
            "evidence_strength", "regime_stability", "sector_stability",
            "confidence_trend", "dna_freshness", "knowledge_coverage",
        }
        ok(names == expected, names)
        return "all 9 component names present"

    def t15_component_values_in_range():
        eng = _engine()
        lib = _winner_library()
        res = eng.evaluate(_make_obs(), lib)
        for c in res.components:
            ok(0.0 <= c.value <= 1.0, f"{c.name}={c.value}")
        return "all component values in [0,1]"

    def t16_component_weighted_value_correct():
        eng = _engine()
        lib = _winner_library()
        res = eng.evaluate(_make_obs(), lib)
        for c in res.components:
            expected = round(c.value * c.weight, 6)
            ok(abs(c.weighted_value - expected) < 1e-5, f"{c.name}: {c.weighted_value} != {expected}")
        return "weighted_value = value × weight for all components"

    def t17_component_weights_match_config():
        eng = _engine()
        cfg = _TEST_CFG
        lib = _winner_library()
        res = eng.evaluate(_make_obs(), lib)
        wmap = {c.name: c.weight for c in res.components}
        ok(wmap["winner_match"]      == cfg.pmci_w_winner)
        ok(wmap["loser_match"]       == cfg.pmci_w_loser)
        ok(wmap["evidence_strength"] == cfg.pmci_w_evidence)
        ok(wmap["regime_stability"]  == cfg.pmci_w_regime)
        return "component weights match MLSConfig"

    def t18_component_matched_count_nonnegative():
        eng = _engine()
        lib = _winner_library()
        res = eng.evaluate(_make_obs(), lib)
        for c in res.components:
            ok(c.matched_count >= 0, f"{c.name}: {c.matched_count}")
        return "all matched_count >= 0"

    # ── T19-T22: PMCIEvidence structure ───────────────────────────────────────

    def t19_evidence_contribution_formula():
        eng = _engine()
        lib = _winner_library(["rsi"])
        obs = _make_obs(features={"rsi": 0.90})
        res = eng.evaluate(obs, lib)
        ev  = res.breakdown.matched_dna[0]
        expected = round(ev.alignment * ev.consensus_score, 6)
        ok(abs(ev.contribution - expected) < 1e-5, f"got {ev.contribution}, expected {expected}")
        return f"contribution={ev.contribution}"

    def t20_evidence_is_match_flag():
        eng = _engine()
        lib = _winner_library(["rsi"])  # WINNERS_HIGHER
        obs = _make_obs(features={"rsi": 0.80})  # above midpoint → match
        res = eng.evaluate(obs, lib)
        ev  = res.breakdown.matched_dna[0]
        ok(ev.is_match, f"alignment={ev.alignment}, midpoint={_TEST_CFG.pmci_feature_midpoint}")
        return f"is_match=True for alignment={ev.alignment}"

    def t21_evidence_is_contradiction_flag():
        eng = _engine()
        lib = _winner_library(["rsi"])  # WINNERS_HIGHER
        obs = _make_obs(features={"rsi": 0.10})  # far below midpoint → contradiction
        res = eng.evaluate(obs, lib)
        ev  = res.breakdown.conflicting_dna[0]
        ok(ev.is_contradiction, f"alignment={ev.alignment}")
        return f"is_contradiction=True for alignment={ev.alignment}"

    def t22_evidence_serialisation():
        eng = _engine()
        lib = _winner_library(["rsi"])
        res = eng.evaluate(_make_obs(), lib)
        if res.breakdown.matched_dna:
            ev  = res.breakdown.matched_dna[0]
            d   = ev.to_dict()
            ev2 = PMCIEvidence.from_dict(d)
            ok(ev2.feature_name == ev.feature_name)
            ok(abs(ev2.alignment - ev.alignment) < 1e-9)
            ok(ev2.is_match == ev.is_match)
        return "PMCIEvidence round-trip OK"

    # ── T23-T27: PMCIBreakdown structure ──────────────────────────────────────

    def t23_breakdown_present():
        eng = _engine()
        lib = _winner_library()
        res = eng.evaluate(_make_obs(), lib)
        ok(isinstance(res.breakdown, PMCIBreakdown))
        return "breakdown type correct"

    def t24_breakdown_coverage_fraction_correct():
        eng = _engine()
        feats = ["rsi", "mom_1d", "adx"]
        lib   = _winner_library(feats)
        # observation only has rsi and mom_1d (not adx)
        obs   = _make_obs(features={"rsi": 0.80, "mom_1d": 0.70})
        res   = eng.evaluate(obs, lib)
        ok(abs(res.breakdown.coverage_fraction - 2/3) < 1e-5, res.breakdown.coverage_fraction)
        return f"coverage_fraction={res.breakdown.coverage_fraction:.4f} = 2/3"

    def t25_breakdown_missing_sorted():
        eng = _engine()
        lib = _winner_library(["zzz", "aaa", "mmm"])
        obs = _make_obs(features={})  # nothing present
        res = eng.evaluate(obs, lib)
        ok(res.breakdown.missing_dna == sorted(res.breakdown.missing_dna))
        return f"missing_dna sorted: {res.breakdown.missing_dna}"

    def t26_breakdown_serialisation():
        eng = _engine()
        lib = _winner_library()
        res = eng.evaluate(_make_obs(), lib)
        d   = res.breakdown.to_dict()
        bd2 = PMCIBreakdown.from_dict(d)
        ok(bd2.coverage_fraction == res.breakdown.coverage_fraction)
        ok(bd2.missing_dna == res.breakdown.missing_dna)
        ok(len(bd2.matched_dna) == len(res.breakdown.matched_dna))
        return "PMCIBreakdown round-trip OK"

    def t27_breakdown_institutional_count():
        eng = _engine()
        lib = _winner_library()
        res = eng.evaluate(_make_obs(), lib)
        # all our DNA is INSTITUTIONAL
        ok(res.breakdown.total_institutional_dna == 2, res.breakdown.total_institutional_dna)
        return f"total_institutional_dna={res.breakdown.total_institutional_dna}"

    # ── T28-T32: _align() math ────────────────────────────────────────────────

    def t28_align_winners_higher_high_value():
        a = _align(0.90, SeparationDirection.WINNERS_HIGHER)
        ok(abs(a - 0.90) < 1e-9, a)
        return f"WINNERS_HIGHER value=0.90 → alignment={a}"

    def t29_align_winners_higher_low_value():
        a = _align(0.10, SeparationDirection.WINNERS_HIGHER)
        ok(abs(a - 0.10) < 1e-9, a)
        return f"WINNERS_HIGHER value=0.10 → alignment={a}"

    def t30_align_winners_lower_low_value():
        a = _align(0.10, SeparationDirection.WINNERS_LOWER)
        ok(abs(a - 0.90) < 1e-9, a)
        return f"WINNERS_LOWER value=0.10 → alignment={a}"

    def t31_align_winners_lower_high_value():
        a = _align(0.90, SeparationDirection.WINNERS_LOWER)
        ok(abs(a - 0.10) < 1e-9, a)
        return f"WINNERS_LOWER value=0.90 → alignment={a}"

    def t32_align_midpoint_gives_half():
        a_h = _align(0.50, SeparationDirection.WINNERS_HIGHER)
        a_l = _align(0.50, SeparationDirection.WINNERS_LOWER)
        ok(abs(a_h - 0.50) < 1e-9, a_h)
        ok(abs(a_l - 0.50) < 1e-9, a_l)
        return "midpoint → alignment=0.50 for both directions"

    def t33_align_clamped_above_1():
        a = _align(5.0, SeparationDirection.WINNERS_HIGHER)
        ok(a == 1.0, a)
        return f"value=5.0 clamped to 1.0"

    # ── T33-T37: Winner match computation ─────────────────────────────────────
    # (T33 already used above for clamp test; continue from T34)

    def t34_winner_match_all_high():
        eng = _engine()
        lib = _winner_library(["rsi", "mom_1d"])  # both WINNERS_HIGHER
        obs = _make_obs(features={"rsi": 1.0, "mom_1d": 1.0})
        res = eng.evaluate(obs, lib)
        wm  = next(c for c in res.components if c.name == "winner_match")
        ok(abs(wm.value - 1.0) < 1e-6, wm.value)
        return f"all-high winner_match={wm.value}"

    def t35_winner_match_all_low():
        eng = _engine()
        lib = _winner_library(["rsi", "mom_1d"])  # WINNERS_HIGHER
        obs = _make_obs(features={"rsi": 0.0, "mom_1d": 0.0})
        res = eng.evaluate(obs, lib)
        wm  = next(c for c in res.components if c.name == "winner_match")
        ok(abs(wm.value - 0.0) < 1e-6, wm.value)
        return f"all-low winner_match={wm.value}"

    def t36_winner_match_mixed():
        eng = _engine()
        lib = _winner_library(["rsi", "mom_1d"])
        obs = _make_obs(features={"rsi": 1.0, "mom_1d": 0.0})
        res = eng.evaluate(obs, lib)
        wm  = next(c for c in res.components if c.name == "winner_match")
        ok(0.0 < wm.value < 1.0, wm.value)
        return f"mixed winner_match={wm.value:.4f}"

    def t37_winner_match_weighted_by_score():
        eng  = _engine()
        # two features: one high-score, one low-score
        dna  = [_make_cdna("rsi",   score=0.90),  # high score
                _make_cdna("mom_1d", score=0.10)] # low score
        lib  = _make_library(dna)
        # rsi=1.0 (perfect match for high-score), mom_1d=0.0 (zero match)
        obs  = _make_obs(features={"rsi": 1.0, "mom_1d": 0.0})
        res  = eng.evaluate(obs, lib)
        wm   = next(c for c in res.components if c.name == "winner_match")
        # weighted avg: (1.0*0.90 + 0.0*0.10) / (0.90+0.10) = 0.90
        ok(abs(wm.value - 0.90) < 1e-6, wm.value)
        return f"weighted winner_match={wm.value:.6f}"

    def t38_winner_match_zero_no_features():
        eng = _engine()
        lib = _winner_library(["rsi"])
        obs = _make_obs(features={"adx": 0.50})  # adx not in DNA
        res = eng.evaluate(obs, lib)
        wm  = next(c for c in res.components if c.name == "winner_match")
        ok(wm.value == 0.0, wm.value)
        return f"no matching features → winner_match={wm.value}"

    # ── T39-T43: Loser match / contradiction ──────────────────────────────────

    def t39_loser_match_complement_of_winner():
        eng = _engine()
        lib = _winner_library(["rsi"])
        obs = _make_obs(features={"rsi": 0.75})
        res = eng.evaluate(obs, lib)
        wm  = next(c for c in res.components if c.name == "winner_match").value
        lm  = next(c for c in res.components if c.name == "loser_match").value
        ok(abs(wm + lm - 1.0) < 1e-6, f"wm={wm} lm={lm} sum={wm+lm}")
        return f"winner_match({wm:.4f}) + loser_match({lm:.4f}) = 1.0"

    def t40_loser_match_zero_when_perfect_winner():
        eng = _engine()
        lib = _winner_library(["rsi"])
        obs = _make_obs(features={"rsi": 1.0})
        res = eng.evaluate(obs, lib)
        lm  = next(c for c in res.components if c.name == "loser_match").value
        ok(abs(lm - 0.0) < 1e-6, lm)
        return f"perfect winner → loser_match={lm}"

    def t41_loser_match_one_when_perfect_loser():
        eng = _engine()
        lib = _winner_library(["rsi"])  # WINNERS_HIGHER
        obs = _make_obs(features={"rsi": 0.0})  # perfectly anti-winner
        res = eng.evaluate(obs, lib)
        lm  = next(c for c in res.components if c.name == "loser_match").value
        ok(abs(lm - 1.0) < 1e-6, lm)
        return f"perfect loser → loser_match={lm}"

    def t42_loser_penalty_reduces_pmci():
        eng  = _engine()
        lib  = _winner_library(["rsi"])
        # perfect winner: winner_match=1, loser_match=0
        res1 = eng.evaluate(_make_obs(features={"rsi": 1.0}), lib)
        # perfect loser: winner_match=0, loser_match=1
        res2 = eng.evaluate(_make_obs(features={"rsi": 0.0}), lib)
        ok(res1.pmci_score > res2.pmci_score, f"{res1.pmci_score} <= {res2.pmci_score}")
        return f"winner={res1.pmci_score:.4f} > loser={res2.pmci_score:.4f}"

    def t43_loser_match_zero_when_no_obs():
        eng = _engine()
        lib = _winner_library(["rsi"])
        obs = _make_obs(features={"adx": 0.50})  # rsi absent
        res = eng.evaluate(obs, lib)
        lm  = next(c for c in res.components if c.name == "loser_match").value
        ok(lm == 0.0, lm)
        return f"no observable features → loser_match={lm}"

    # ── T44-T48: Evidence strength ────────────────────────────────────────────

    def t44_evidence_strength_high_score_dna():
        eng = _engine()
        lib = _make_library([_make_cdna("rsi", score=0.95)])
        obs = _make_obs(features={"rsi": 0.80})  # match
        res = eng.evaluate(obs, lib)
        es  = next(c for c in res.components if c.name == "evidence_strength")
        ok(abs(es.value - 0.95) < 1e-6, es.value)
        return f"evidence_strength={es.value:.6f} (expected 0.95)"

    def t45_evidence_strength_low_score_dna():
        eng = _engine()
        lib = _make_library([_make_cdna("rsi", score=0.20)])
        obs = _make_obs(features={"rsi": 0.80})
        res = eng.evaluate(obs, lib)
        es  = next(c for c in res.components if c.name == "evidence_strength")
        ok(abs(es.value - 0.20) < 1e-6, es.value)
        return f"low-score DNA → evidence_strength={es.value:.6f}"

    def t46_evidence_strength_zero_when_no_match():
        eng = _engine()
        lib = _winner_library(["rsi"])  # WINNERS_HIGHER
        obs = _make_obs(features={"rsi": 0.0})  # no match (alignment=0 < mid=0.5)
        res = eng.evaluate(obs, lib)
        es  = next(c for c in res.components if c.name == "evidence_strength")
        ok(es.value == 0.0, es.value)
        return f"no matched features → evidence_strength={es.value}"

    def t47_evidence_strength_only_from_matched():
        eng  = _engine()
        dna  = [_make_cdna("rsi",    score=0.90),   # rsi=0.9, WINNERS_HIGHER → match
                _make_cdna("mom_1d", score=0.10)]    # mom_1d=0.0, → conflict (not counted)
        lib  = _make_library(dna)
        obs  = _make_obs(features={"rsi": 0.90, "mom_1d": 0.0})
        res  = eng.evaluate(obs, lib)
        es   = next(c for c in res.components if c.name == "evidence_strength")
        # only rsi contributes (mom_1d is conflicting, not in matched_dna)
        ok(abs(es.value - 0.90) < 1e-6, es.value)
        return f"evidence_strength from matched only={es.value:.6f}"

    def t48_evidence_boosts_pmci():
        eng   = _engine()
        obs   = _make_obs(features={"rsi": 0.80})
        lib_h = _make_library([_make_cdna("rsi", score=0.90)])
        lib_l = _make_library([_make_cdna("rsi", score=0.10)])
        r_h   = eng.evaluate(obs, lib_h)
        r_l   = eng.evaluate(obs, lib_l)
        ok(r_h.pmci_score > r_l.pmci_score, f"high={r_h.pmci_score} low={r_l.pmci_score}")
        return f"high-evidence PMCI={r_h.pmci_score:.4f} > low-evidence={r_l.pmci_score:.4f}"

    # ── T49-T53: Regime / sector stability ───────────────────────────────────

    def t49_regime_stability_from_regime_consistency():
        eng = _engine()
        lib = _make_library([_make_cdna("rsi", regime_cons=0.95)])
        obs = _make_obs(features={"rsi": 0.80})
        res = eng.evaluate(obs, lib)
        rs  = next(c for c in res.components if c.name == "regime_stability")
        ok(abs(rs.value - 0.95) < 1e-6, rs.value)
        return f"regime_stability={rs.value:.6f}"

    def t50_sector_stability_from_sector_consistency():
        eng = _engine()
        lib = _make_library([_make_cdna("rsi", sector_cons=0.88)])
        obs = _make_obs(features={"rsi": 0.80})
        res = eng.evaluate(obs, lib)
        ss  = next(c for c in res.components if c.name == "sector_stability")
        ok(abs(ss.value - 0.88) < 1e-6, ss.value)
        return f"sector_stability={ss.value:.6f}"

    def t51_stability_zero_when_no_features_present():
        eng = _engine()
        lib = _winner_library(["rsi"])
        obs = _make_obs(features={"adx": 0.50})  # rsi absent
        res = eng.evaluate(obs, lib)
        rs  = next(c for c in res.components if c.name == "regime_stability")
        ok(rs.value == 0.0, rs.value)
        return f"absent features → regime_stability={rs.value}"

    def t52_stability_computed_for_present_regardless_of_alignment():
        eng = _engine()
        lib = _make_library([
            _make_cdna("rsi",    regime_cons=0.80),
            _make_cdna("mom_1d", regime_cons=0.60),
        ])
        # rsi=0.9 → match; mom_1d=0.1 → conflict; but BOTH present in obs
        obs = _make_obs(features={"rsi": 0.90, "mom_1d": 0.10})
        res = eng.evaluate(obs, lib)
        rs  = next(c for c in res.components if c.name == "regime_stability")
        ok(abs(rs.value - 0.70) < 1e-6, rs.value)  # avg of 0.80 and 0.60
        return f"stability includes conflicting features: rs={rs.value:.4f}"

    def t53_stability_boosts_pmci():
        eng    = _engine()
        obs    = _make_obs(features={"rsi": 0.80})
        lib_hi = _make_library([_make_cdna("rsi", regime_cons=0.95, sector_cons=0.95)])
        lib_lo = _make_library([_make_cdna("rsi", regime_cons=0.10, sector_cons=0.10)])
        r_hi   = eng.evaluate(obs, lib_hi)
        r_lo   = eng.evaluate(obs, lib_lo)
        ok(r_hi.pmci_score > r_lo.pmci_score, f"hi={r_hi.pmci_score} lo={r_lo.pmci_score}")
        return f"stable PMCI={r_hi.pmci_score:.4f} > unstable={r_lo.pmci_score:.4f}"

    # ── T54-T58: DNA freshness ────────────────────────────────────────────────

    def t54_freshness_today_is_one():
        f = _freshness("2026-08-04", "2026-08-04", 30)
        ok(abs(f - 1.0) < 1e-9, f)
        return f"freshness(same day)={f}"

    def t55_freshness_max_days_is_zero():
        f = _freshness("2026-07-05", "2026-08-04", 30)
        ok(abs(f - 0.0) < 1e-9, f)
        return f"freshness(30d ago)={f}"

    def t56_freshness_half_window():
        f = _freshness("2026-07-20", "2026-08-04", 30)  # 15 days ago
        ok(abs(f - 0.50) < 1e-9, f)
        return f"freshness(15d ago, 30d window)={f}"

    def t57_freshness_linear_decay():
        f10 = _freshness("2026-07-25", "2026-08-04", 30)  # 10 days ago
        f20 = _freshness("2026-07-15", "2026-08-04", 30)  # 20 days ago
        ok(f10 > f20, f"f10={f10} f20={f20}")
        ok(abs(f10 - 2 * f20) < 1e-6, f"not linear: f10={f10} f20={f20}")
        return f"linear: f10={f10:.3f}, f20={f20:.3f}"

    def t58_freshness_component_in_result():
        eng = _engine()
        lib = _make_library([_make_cdna("rsi", last_seen="2026-08-04")])
        obs = _make_obs(features={"rsi": 0.80}, date="2026-08-04")
        res = eng.evaluate(obs, lib, evaluation_date="2026-08-04")
        df  = next(c for c in res.components if c.name == "dna_freshness")
        ok(abs(df.value - 1.0) < 1e-6, df.value)
        return f"just-seen DNA → freshness={df.value:.6f}"

    # ── T59-T63: Knowledge coverage ───────────────────────────────────────────

    def t59_coverage_all_present():
        eng   = _engine()
        feats = ["rsi", "mom_1d"]
        lib   = _winner_library(feats)
        obs   = _make_obs(features={"rsi": 0.80, "mom_1d": 0.70})
        res   = eng.evaluate(obs, lib)
        kc    = next(c for c in res.components if c.name == "knowledge_coverage")
        ok(abs(kc.value - 1.0) < 1e-6, kc.value)
        return f"all features present → coverage={kc.value}"

    def t60_coverage_none_present():
        eng = _engine()
        lib = _winner_library(["rsi", "mom_1d"])
        obs = _make_obs(features={"adx": 0.50, "zzz": 0.50})
        res = eng.evaluate(obs, lib)
        kc  = next(c for c in res.components if c.name == "knowledge_coverage")
        ok(abs(kc.value - 0.0) < 1e-6, kc.value)
        return f"no features present → coverage={kc.value}"

    def t61_coverage_partial():
        eng   = _engine()
        feats = ["rsi", "mom_1d", "adx"]
        lib   = _winner_library(feats)
        obs   = _make_obs(features={"rsi": 0.80})
        res   = eng.evaluate(obs, lib)
        kc    = next(c for c in res.components if c.name == "knowledge_coverage")
        ok(abs(kc.value - 1/3) < 1e-5, kc.value)
        return f"1/3 present → coverage={kc.value:.4f}"

    def t62_coverage_boosts_pmci():
        eng    = _engine()
        # same alignment (0.90) for both features; only coverage differs
        obs_hi = _make_obs(features={"rsi": 0.90, "mom_1d": 0.90})   # 2/2 coverage
        obs_lo = _make_obs(features={"rsi": 0.90})                     # 1/2 coverage
        lib    = _winner_library(["rsi", "mom_1d"])
        r_hi   = eng.evaluate(obs_hi, lib)
        r_lo   = eng.evaluate(obs_lo, lib)
        ok(r_hi.pmci_score >= r_lo.pmci_score, f"hi={r_hi.pmci_score} lo={r_lo.pmci_score}")
        return f"full coverage PMCI={r_hi.pmci_score:.4f} >= partial={r_lo.pmci_score:.4f}"

    def t63_coverage_includes_neutral_dna():
        eng = _engine()
        dna = [
            _make_cdna("rsi",   direction="WINNERS_HIGHER"),
            _make_cdna("zzz_n", direction="NEUTRALS_HIGHER"),
        ]
        lib = _make_library(dna)
        obs = _make_obs(features={"rsi": 0.80, "zzz_n": 0.70})
        res = eng.evaluate(obs, lib)
        kc  = next(c for c in res.components if c.name == "knowledge_coverage")
        ok(abs(kc.value - 1.0) < 1e-5, kc.value)
        return f"neutral DNA counts for coverage={kc.value:.4f}"

    # ── T64-T68: evaluate_universe() ─────────────────────────────────────────

    def t64_universe_length_matches_input():
        eng  = _engine()
        lib  = _winner_library()
        obs  = [_make_obs("A"), _make_obs("B"), _make_obs("C")]
        res  = eng.evaluate_universe(obs, lib)
        ok(len(res) == 3, len(res))
        return f"evaluate_universe: {len(res)} results for 3 symbols"

    def t65_universe_result_symbols_correct():
        eng = _engine()
        lib = _winner_library()
        obs = [_make_obs("AAPL"), _make_obs("MSFT")]
        res = eng.evaluate_universe(obs, lib)
        syms = [r.symbol for r in res]
        ok(syms == ["AAPL", "MSFT"], syms)
        return f"symbols={syms}"

    def t66_universe_results_independent():
        eng  = _engine()
        lib  = _winner_library()
        obs1 = _make_obs("X", features={"rsi": 1.0, "mom_1d": 1.0})
        obs2 = _make_obs("Y", features={"rsi": 0.0, "mom_1d": 0.0})
        res  = eng.evaluate_universe([obs1, obs2], lib)
        ok(res[0].pmci_score != res[1].pmci_score, "all scores equal")
        return f"X={res[0].pmci_score:.4f} Y={res[1].pmci_score:.4f}"

    def t67_universe_empty_input():
        eng = _engine()
        lib = _winner_library()
        res = eng.evaluate_universe([], lib)
        ok(res == [], res)
        return "empty input → empty result"

    def t68_universe_library_id_consistent():
        eng = _engine()
        lib = _make_library([_make_cdna("rsi"), _make_cdna("mom_1d")], date="2026-08-03")
        obs = [_make_obs("A"), _make_obs("B")]
        res = eng.evaluate_universe(obs, lib)
        ok(all(r.library_id == lib.library_id for r in res))
        return f"library_id={lib.library_id} consistent across {len(res)} results"

    # ── T69-T73: top_matches() ────────────────────────────────────────────────

    def t69_top_matches_sorted_descending():
        eng  = _engine()
        lib  = _winner_library()
        obs  = [_make_obs(s, features={"rsi": v, "mom_1d": v})
                for s, v in [("A", 0.9), ("B", 0.5), ("C", 0.1)]]
        res  = eng.evaluate_universe(obs, lib)
        top  = eng.top_matches(res)
        ok(top[0].pmci_score >= top[1].pmci_score >= top[2].pmci_score)
        return f"top order: {[r.symbol for r in top]}"

    def t70_top_matches_limit_n():
        eng  = _engine()
        lib  = _winner_library()
        obs  = [_make_obs(f"S{i}", features={"rsi": 0.5}) for i in range(20)]
        res  = eng.evaluate_universe(obs, lib)
        top5 = eng.top_matches(res, n=5)
        ok(len(top5) == 5, len(top5))
        return f"top_matches(n=5) → {len(top5)} results"

    def t71_top_matches_first_is_highest():
        eng  = _engine()
        lib  = _winner_library()
        obs  = [_make_obs("BEST", features={"rsi": 1.0, "mom_1d": 1.0}),
                _make_obs("WORST", features={"rsi": 0.0, "mom_1d": 0.0})]
        res  = eng.evaluate_universe(obs, lib)
        top  = eng.top_matches(res, n=1)
        ok(top[0].symbol == "BEST", top[0].symbol)
        return f"top_matches(n=1) → {top[0].symbol}"

    def t72_top_matches_fewer_than_n():
        eng  = _engine()
        lib  = _winner_library()
        obs  = [_make_obs("A")]
        res  = eng.evaluate_universe(obs, lib)
        top  = eng.top_matches(res, n=10)
        ok(len(top) == 1, len(top))
        return "top_matches returns all when len < n"

    def t73_top_matches_empty_input():
        eng = _engine()
        top = eng.top_matches([], n=5)
        ok(top == [], top)
        return "top_matches([]) → []"

    # ── T74-T78: statistics() ────────────────────────────────────────────────

    def t74_stats_total_symbols():
        eng = _engine()
        lib = _winner_library()
        obs = [_make_obs(f"S{i}") for i in range(5)]
        res = eng.evaluate_universe(obs, lib)
        st  = eng.statistics(res)
        ok(st.total_symbols == 5, st.total_symbols)
        return f"total_symbols={st.total_symbols}"

    def t75_stats_avg_pmci():
        eng  = _engine()
        lib  = _winner_library(["rsi"])
        obs1 = _make_obs("A", features={"rsi": 1.0})
        obs2 = _make_obs("B", features={"rsi": 0.0})
        res  = eng.evaluate_universe([obs1, obs2], lib)
        st   = eng.statistics(res)
        expected = (res[0].pmci_score + res[1].pmci_score) / 2
        ok(abs(st.avg_pmci - expected) < 1e-5, st.avg_pmci)
        return f"avg_pmci={st.avg_pmci:.6f}"

    def t76_stats_high_similarity_count():
        eng = _engine()
        lib = _winner_library(["rsi"])
        # force PMCI > 0.70 with perfect winner features and very high scores
        cfg = MLSConfig(min_universe_size=1, dna_min_group_size=2, pmci_high_similarity_threshold=0.30)
        eng_lo_thr = PMCIEngine(config=cfg)
        obs_hi = [_make_obs(f"H{i}", features={"rsi": 1.0}) for i in range(3)]
        obs_lo = [_make_obs(f"L{i}", features={"rsi": 0.0}) for i in range(2)]
        res    = eng_lo_thr.evaluate_universe(obs_hi + obs_lo, lib)
        st     = eng_lo_thr.statistics(res)
        ok(st.high_similarity_count == 3, st.high_similarity_count)
        return f"high_similarity_count={st.high_similarity_count}"

    def t77_stats_top_symbol():
        eng  = _engine()
        lib  = _winner_library(["rsi"])
        obs  = [_make_obs("BEST", features={"rsi": 1.0}),
                _make_obs("WORST", features={"rsi": 0.0})]
        res  = eng.evaluate_universe(obs, lib)
        st   = eng.statistics(res)
        ok(st.top_symbol == "BEST", st.top_symbol)
        return f"top_symbol={st.top_symbol}"

    def t78_stats_empty_input():
        eng = _engine()
        st  = eng.statistics([])
        ok(st.total_symbols == 0)
        ok(st.top_symbol is None)
        return "statistics([]) → safe defaults"

    # ── T79-T83: Explainability ───────────────────────────────────────────────

    def t79_matched_dna_sorted_by_contribution_desc():
        eng  = _engine()
        dna  = [_make_cdna("rsi",    score=0.90),
                _make_cdna("mom_1d", score=0.50)]
        lib  = _make_library(dna)
        obs  = _make_obs(features={"rsi": 0.90, "mom_1d": 0.80})
        res  = eng.evaluate(obs, lib)
        md   = res.breakdown.matched_dna
        ok(len(md) >= 2)
        ok(md[0].contribution >= md[-1].contribution)
        return f"matched sorted by contribution: {[e.feature_name for e in md]}"

    def t80_conflicting_dna_present_for_loser_stock():
        eng = _engine()
        lib = _winner_library(["rsi"])  # WINNERS_HIGHER
        obs = _make_obs(features={"rsi": 0.05})  # clearly anti-winner
        res = eng.evaluate(obs, lib)
        ok(len(res.breakdown.conflicting_dna) >= 1)
        return f"conflicting_dna={len(res.breakdown.conflicting_dna)}"

    def t81_missing_dna_listed_alphabetically():
        eng = _engine()
        lib = _winner_library(["zzz", "aaa", "mmm"])
        obs = _make_obs(features={})
        res = eng.evaluate(obs, lib)
        md  = res.breakdown.missing_dna
        ok(md == sorted(md), md)
        return f"missing sorted: {md}"

    def t82_explanation_contains_symbol():
        eng = _engine()
        lib = _winner_library()
        res = eng.evaluate(_make_obs("RELIANCE"), lib)
        ok("RELIANCE" in res.explanation, res.explanation[:80])
        return "symbol in explanation"

    def t83_explanation_contains_counts():
        eng = _engine()
        lib = _winner_library(["rsi"])
        obs = _make_obs(features={"rsi": 0.80})
        res = eng.evaluate(obs, lib)
        ok("matched" in res.explanation.lower() or "match" in res.explanation.lower(),
           res.explanation[:80])
        return "explanation mentions matched"

    # ── T84-T88: evaluate_symbol() ───────────────────────────────────────────

    def t84_evaluate_symbol_none_for_absent():
        eng  = _engine()
        lib  = _winner_library()
        snap = _make_snapshot([_make_obs("INFY")])
        res  = eng.evaluate_symbol("MISSING", snap, lib)
        ok(res is None, res)
        return "evaluate_symbol returns None for absent symbol"

    def t85_evaluate_symbol_returns_result():
        eng  = _engine()
        lib  = _winner_library()
        snap = _make_snapshot([_make_obs("TCS")])
        res  = eng.evaluate_symbol("TCS", snap, lib)
        ok(res is not None)
        ok(res.symbol == "TCS", res.symbol)
        return f"evaluate_symbol for TCS → pmci={res.pmci_score:.4f}"

    def t86_evaluate_symbol_uses_trading_date():
        eng  = _engine()
        lib  = _winner_library()
        snap = _make_snapshot([_make_obs("TCS", date="2026-08-04")], date="2026-08-04")
        res  = eng.evaluate_symbol("TCS", snap, lib)
        ok(res.evaluation_date == "2026-08-04", res.evaluation_date)
        return f"evaluation_date={res.evaluation_date}"

    def t87_evaluate_symbol_regime_from_snapshot():
        eng  = _engine()
        lib  = _winner_library()
        snap = _make_snapshot([_make_obs("TCS")], regime="bear_trend")
        res  = eng.evaluate_symbol("TCS", snap, lib)
        ok(res.regime == "bear_trend", res.regime)
        return f"regime from snapshot: {res.regime}"

    def t88_evaluate_symbol_same_as_evaluate():
        eng  = _engine()
        lib  = _winner_library()
        obs  = _make_obs("TCS", features={"rsi": 0.80, "mom_1d": 0.70})
        snap = _make_snapshot([obs])
        r_sym  = eng.evaluate_symbol("TCS", snap, lib, evaluation_date="2026-08-04")
        r_eval = eng.evaluate(obs, lib, evaluation_date="2026-08-04", regime=snap.regime)
        ok(abs(r_sym.pmci_score - r_eval.pmci_score) < 1e-6,
           f"{r_sym.pmci_score} != {r_eval.pmci_score}")
        return f"evaluate_symbol == evaluate: pmci={r_sym.pmci_score:.6f}"

    # ── T89-T90: Edge cases ───────────────────────────────────────────────────

    def t89_retired_dna_excluded():
        eng  = _engine()
        # one active, one retired
        dna  = [_make_cdna("rsi",    state="INSTITUTIONAL"),
                _make_cdna("mom_1d", state="RETIRED")]
        lib  = _make_library(dna)
        obs  = _make_obs(features={"rsi": 0.80, "mom_1d": 0.80})
        res  = eng.evaluate(obs, lib)
        # only rsi should appear in breakdown (mom_1d is retired)
        all_ev_names = (
            {e.feature_name for e in res.breakdown.matched_dna}
            | {e.feature_name for e in res.breakdown.conflicting_dna}
            | set(res.breakdown.missing_dna)
        )
        ok("mom_1d" not in all_ev_names, all_ev_names)
        ok("rsi" in all_ev_names, all_ev_names)
        return "RETIRED DNA excluded from evaluation"

    def t90_empty_library_safe():
        eng = _engine()
        lib = _make_library([])  # no DNA
        obs = _make_obs(features={"rsi": 0.80})
        res = eng.evaluate(obs, lib)
        ok(res.pmci_score == 0.0, res.pmci_score)
        ok(isinstance(res.breakdown, PMCIBreakdown))
        ok(len(res.components) == 9)
        return f"empty library → pmci={res.pmci_score}, 9 components"

    # ── Registration ──────────────────────────────────────────────────────────

    tests = [
        ("T01 MLSConfig pmci_w_winner",                    t01_pmci_winner_weight),
        ("T02 MLSConfig pmci_w_loser",                     t02_pmci_loser_penalty),
        ("T03 MLSConfig positive weights sum to 1",         t03_pmci_positive_weights_sum_to_1),
        ("T04 MLSConfig thresholds and freshness",          t04_pmci_thresholds),
        ("T05 MLSConfig overrides",                         t05_pmci_config_overrides),
        ("T06 Engine default init",                         t06_engine_default_init),
        ("T07 Engine custom config",                        t07_engine_custom_config),
        ("T08 evaluate() is read-only",                     t08_engine_is_readonly),
        ("T09 PMCIResult id prefix PMC-",                   t09_result_id_prefix),
        ("T10 PMCIResult evaluation_date",                  t10_result_evaluation_date),
        ("T11 PMCIResult pmci_score in [0,1]",              t11_result_pmci_score_in_range),
        ("T12 PMCIResult has 9 components",                 t12_result_has_nine_components),
        ("T13 PMCIResult explanation nonempty",             t13_result_explanation_nonempty),
        ("T14 PMCIComponent names correct",                 t14_component_names_correct),
        ("T15 PMCIComponent values in [0,1]",               t15_component_values_in_range),
        ("T16 PMCIComponent weighted_value = value*weight", t16_component_weighted_value_correct),
        ("T17 PMCIComponent weights match config",          t17_component_weights_match_config),
        ("T18 PMCIComponent matched_count >= 0",            t18_component_matched_count_nonnegative),
        ("T19 PMCIEvidence contribution formula",           t19_evidence_contribution_formula),
        ("T20 PMCIEvidence is_match flag",                  t20_evidence_is_match_flag),
        ("T21 PMCIEvidence is_contradiction flag",          t21_evidence_is_contradiction_flag),
        ("T22 PMCIEvidence serialisation round-trip",       t22_evidence_serialisation),
        ("T23 PMCIBreakdown present and typed",             t23_breakdown_present),
        ("T24 PMCIBreakdown coverage_fraction",             t24_breakdown_coverage_fraction_correct),
        ("T25 PMCIBreakdown missing_dna sorted",            t25_breakdown_missing_sorted),
        ("T26 PMCIBreakdown serialisation round-trip",      t26_breakdown_serialisation),
        ("T27 PMCIBreakdown institutional_count",           t27_breakdown_institutional_count),
        ("T28 _align WINNERS_HIGHER high value",            t28_align_winners_higher_high_value),
        ("T29 _align WINNERS_HIGHER low value",             t29_align_winners_higher_low_value),
        ("T30 _align WINNERS_LOWER low value",              t30_align_winners_lower_low_value),
        ("T31 _align WINNERS_LOWER high value",             t31_align_winners_lower_high_value),
        ("T32 _align midpoint gives 0.5",                   t32_align_midpoint_gives_half),
        ("T33 _align clamped when > 1",                     t33_align_clamped_above_1),
        ("T34 winner_match all-high",                       t34_winner_match_all_high),
        ("T35 winner_match all-low",                        t35_winner_match_all_low),
        ("T36 winner_match mixed",                          t36_winner_match_mixed),
        ("T37 winner_match weighted by consensus_score",    t37_winner_match_weighted_by_score),
        ("T38 winner_match zero when no matching features", t38_winner_match_zero_no_features),
        ("T39 loser_match is complement of winner_match",   t39_loser_match_complement_of_winner),
        ("T40 loser_match zero for perfect winner",         t40_loser_match_zero_when_perfect_winner),
        ("T41 loser_match one for perfect loser",           t41_loser_match_one_when_perfect_loser),
        ("T42 loser penalty reduces PMCI",                  t42_loser_penalty_reduces_pmci),
        ("T43 loser_match zero when no observable",         t43_loser_match_zero_when_no_obs),
        ("T44 evidence_strength from high-score DNA",       t44_evidence_strength_high_score_dna),
        ("T45 evidence_strength from low-score DNA",        t45_evidence_strength_low_score_dna),
        ("T46 evidence_strength zero when no match",        t46_evidence_strength_zero_when_no_match),
        ("T47 evidence_strength from matched only",         t47_evidence_strength_only_from_matched),
        ("T48 evidence_strength boosts PMCI",               t48_evidence_boosts_pmci),
        ("T49 regime_stability from regime_consistency",    t49_regime_stability_from_regime_consistency),
        ("T50 sector_stability from sector_consistency",    t50_sector_stability_from_sector_consistency),
        ("T51 stability zero when no features present",     t51_stability_zero_when_no_features_present),
        ("T52 stability includes both match and conflict",  t52_stability_computed_for_present_regardless_of_alignment),
        ("T53 stability boosts PMCI",                       t53_stability_boosts_pmci),
        ("T54 freshness 1.0 when same day",                 t54_freshness_today_is_one),
        ("T55 freshness 0.0 after max_days",                t55_freshness_max_days_is_zero),
        ("T56 freshness 0.5 at half window",                t56_freshness_half_window),
        ("T57 freshness linear decay",                      t57_freshness_linear_decay),
        ("T58 freshness component in PMCIResult",           t58_freshness_component_in_result),
        ("T59 coverage 1.0 all features present",           t59_coverage_all_present),
        ("T60 coverage 0.0 no features present",            t60_coverage_none_present),
        ("T61 coverage partial presence",                   t61_coverage_partial),
        ("T62 coverage boosts PMCI",                        t62_coverage_boosts_pmci),
        ("T63 coverage includes neutral DNA",               t63_coverage_includes_neutral_dna),
        ("T64 evaluate_universe length",                    t64_universe_length_matches_input),
        ("T65 evaluate_universe symbols correct",           t65_universe_result_symbols_correct),
        ("T66 evaluate_universe results independent",       t66_universe_results_independent),
        ("T67 evaluate_universe empty input",               t67_universe_empty_input),
        ("T68 evaluate_universe library_id consistent",     t68_universe_library_id_consistent),
        ("T69 top_matches sorted descending",               t69_top_matches_sorted_descending),
        ("T70 top_matches limit n",                         t70_top_matches_limit_n),
        ("T71 top_matches first is highest",                t71_top_matches_first_is_highest),
        ("T72 top_matches fewer than n",                    t72_top_matches_fewer_than_n),
        ("T73 top_matches empty input",                     t73_top_matches_empty_input),
        ("T74 statistics total_symbols",                    t74_stats_total_symbols),
        ("T75 statistics avg_pmci",                         t75_stats_avg_pmci),
        ("T76 statistics high_similarity_count",            t76_stats_high_similarity_count),
        ("T77 statistics top_symbol",                       t77_stats_top_symbol),
        ("T78 statistics empty input",                      t78_stats_empty_input),
        ("T79 matched_dna sorted by contribution desc",     t79_matched_dna_sorted_by_contribution_desc),
        ("T80 conflicting_dna present for loser stock",     t80_conflicting_dna_present_for_loser_stock),
        ("T81 missing_dna sorted alphabetically",           t81_missing_dna_listed_alphabetically),
        ("T82 explanation contains symbol",                 t82_explanation_contains_symbol),
        ("T83 explanation mentions matched count",          t83_explanation_contains_counts),
        ("T84 evaluate_symbol None for absent symbol",      t84_evaluate_symbol_none_for_absent),
        ("T85 evaluate_symbol returns result",              t85_evaluate_symbol_returns_result),
        ("T86 evaluate_symbol uses trading_date",           t86_evaluate_symbol_uses_trading_date),
        ("T87 evaluate_symbol regime from snapshot",        t87_evaluate_symbol_regime_from_snapshot),
        ("T88 evaluate_symbol matches evaluate()",          t88_evaluate_symbol_same_as_evaluate),
        ("T89 RETIRED DNA excluded from evaluation",        t89_retired_dna_excluded),
        ("T90 empty library safe defaults",                 t90_empty_library_safe),
    ]

    for name, fn in tests:
        runner.run(name, fn)

    return runner.report()


if __name__ == "__main__":
    import sys
    sys.exit(main())
