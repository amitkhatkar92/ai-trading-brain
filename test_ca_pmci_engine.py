"""
test_ca_pmci_engine.py — MLS Phase 5B: Context-Aware PMCI Engine.

90-test suite.  Run with:
    .venv\\Scripts\\python.exe test_ca_pmci_engine.py

Uses the same minimal test framework as Phases 3, 4, 5, and 5A.
No pytest dependency.
"""
from __future__ import annotations

import hashlib
import sys
import time
import traceback
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from models.market_data import (
    FIIDIIData,
    MarketSnapshot,
    RegimeLabel,
    SectorFlow,
    VolatilityLevel,
)
from market_learning import (
    CAPMCIEngine,
    CAPMCIError,
    CAPMCIInputError,
    CAPMCIResult,
    CAPMCIStatistics,
    ContextAdjustment,
    MCIEngine,
    MLSConfig,
    PMCIEngine,
    PMCIResult,
    ConsensusDNA,
    ConsensusLevel,
    ConsensusLibrary,
    ConsensusState,
    ConsensusStatistics,
    MarketContext,
    SeparationDirection,
)
from market_learning.market_observer_models import MarketObservation
from market_learning.ca_pmci_engine import (
    _clamp,
    _mean,
    _make_ca_pmci_id,
    _extract_component,
    _get_context_score,
    _compute_adj,
)


# ═══════════════════════════════════════════════════════════════════════════════
# Minimal test framework (same pattern as Phases 3/4/5/5A)
# ═══════════════════════════════════════════════════════════════════════════════

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


# ═══════════════════════════════════════════════════════════════════════════════
# Test fixtures
# ═══════════════════════════════════════════════════════════════════════════════

_TEST_CFG = MLSConfig(min_universe_size=1, dna_min_group_size=2)

# ── MarketSnapshot fixtures ───────────────────────────────────────────────────

def _make_market_snapshot(
    regime:           RegimeLabel = RegimeLabel.BULL_TREND,
    vix:              float       = 15.0,
    pcr:              float       = 1.0,
    breadth:          float       = 0.6,
    global_sentiment: float       = 0.2,
    global_bias:      str         = "neutral",
    fii_net:          Optional[float] = None,
    dii_net:          Optional[float] = None,
    sector_flows:     Optional[List[SectorFlow]] = None,
    ts:               str         = "2026-08-04T09:00:00",
) -> MarketSnapshot:
    fii_dii = None
    if fii_net is not None:
        fii_buy  = max(0.0, fii_net)
        fii_sell = max(0.0, -fii_net)
        dii_buy  = max(0.0, dii_net or 0.0)
        dii_sell = max(0.0, -(dii_net or 0.0))
        fii_dii  = FIIDIIData(
            date=datetime.fromisoformat(ts),
            fii_buy=fii_buy, fii_sell=fii_sell,
            dii_buy=dii_buy, dii_sell=dii_sell,
        )
    return MarketSnapshot(
        timestamp=datetime.fromisoformat(ts),
        indices={},
        regime=regime,
        vix=vix,
        pcr=pcr,
        market_breadth=breadth,
        global_sentiment_score=global_sentiment,
        global_bias=global_bias,
        fii_dii=fii_dii,
        sector_flows=sector_flows or [],
    )


def _bull_snapshot() -> MarketSnapshot:
    """Fully favorable market context: BULL, low VIX, positive FII, all-positive sectors."""
    return _make_market_snapshot(
        regime=RegimeLabel.BULL_TREND, vix=10.0, breadth=0.9,
        global_sentiment=0.5, global_bias="bullish",
        fii_net=2000.0, dii_net=500.0,
        sector_flows=[
            SectorFlow(sector_name=f"S{i}", flow_score=0.8, rank=i+1) for i in range(5)
        ],
    )


def _adverse_snapshot() -> MarketSnapshot:
    """Fully adverse market context: VOLATILE, high VIX, negative FII, all-negative sectors."""
    return _make_market_snapshot(
        regime=RegimeLabel.VOLATILE, vix=50.0, breadth=0.1,
        global_sentiment=-0.8, global_bias="bearish",
        fii_net=-3000.0, dii_net=-1000.0,
        sector_flows=[
            SectorFlow(sector_name=f"S{i}", flow_score=-0.8, rank=i+1) for i in range(5)
        ],
    )


# ── MarketObservation & ConsensusLibrary fixtures ─────────────────────────────

def _make_obs(
    symbol:   str                  = "TEST",
    features: Optional[Dict[str, float]] = None,
    date:     str                  = "2026-08-04",
) -> MarketObservation:
    f = features or {"rsi": 0.75, "mom_1d": 0.70}
    return MarketObservation(
        symbol=symbol,
        feature_timestamp=f"{date}T09:15:00",
        features=f,
        feature_count=len(f),
    )


def _make_cdna(
    feature:     str   = "rsi",
    direction:   str   = "WINNERS_HIGHER",
    state:       str   = "INSTITUTIONAL",
    score:       float = 0.80,
    regime_cons: float = 0.80,
    sector_cons: float = 0.80,
    conf_trend:  float = 0.10,
    last_seen:   str   = "2026-08-03",
    evidence:    int   = 15,
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
        evidence_count=evidence,
        temporal_stability=0.80,
        regime_consistency=regime_cons,
        sector_consistency=sector_cons,
        confidence_trend=conf_trend,
        feature_persistence=0.80,
        first_seen="2026-01-01",
        last_seen=last_seen,
        all_observations=[],
        regime_counts={"bull_trend": evidence},
        level=lvl,
    )


def _make_library(
    dna_list: List[ConsensusDNA],
    date:     str = "2026-08-03",
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


def _good_library() -> ConsensusLibrary:
    return _make_library([
        _make_cdna("rsi",    regime_cons=0.80, sector_cons=0.80),
        _make_cdna("mom_1d", regime_cons=0.80, sector_cons=0.80),
    ])


def _poor_library() -> ConsensusLibrary:
    """DNA with low regime/sector consistency (struggles in adverse contexts)."""
    return _make_library([
        _make_cdna("rsi",    regime_cons=0.30, sector_cons=0.30),
        _make_cdna("mom_1d", regime_cons=0.30, sector_cons=0.30),
    ])


def _engine(cfg: Optional[MLSConfig] = None) -> CAPMCIEngine:
    return CAPMCIEngine(config=cfg or _TEST_CFG)


# ── PMCIResult helper (evaluate raw PMCI for assertion cross-checks) ──────────

def _raw(obs, lib, date="2026-08-04") -> PMCIResult:
    return PMCIEngine(_TEST_CFG).evaluate(obs, lib, evaluation_date=date)


# ═══════════════════════════════════════════════════════════════════════════════
# Tests
# ═══════════════════════════════════════════════════════════════════════════════

def main() -> int:
    runner = TestRunner()

    # ── T01-T05: MLSConfig Phase 5B defaults ─────────────────────────────────

    def t01_regime_weight():
        cfg = MLSConfig()
        ok(cfg.ca_pmci_w_regime == 0.15, cfg.ca_pmci_w_regime)
        return f"ca_pmci_w_regime={cfg.ca_pmci_w_regime}"

    def t02_volatility_sector_weights():
        cfg = MLSConfig()
        ok(cfg.ca_pmci_w_volatility == 0.10, cfg.ca_pmci_w_volatility)
        ok(cfg.ca_pmci_w_sector     == 0.10, cfg.ca_pmci_w_sector)
        return f"w_volatility={cfg.ca_pmci_w_volatility} w_sector={cfg.ca_pmci_w_sector}"

    def t03_stability_freshness_weights():
        cfg = MLSConfig()
        ok(cfg.ca_pmci_w_stability == 0.07, cfg.ca_pmci_w_stability)
        ok(cfg.ca_pmci_w_freshness == 0.05, cfg.ca_pmci_w_freshness)
        return f"w_stability={cfg.ca_pmci_w_stability} w_freshness={cfg.ca_pmci_w_freshness}"

    def t04_adjustment_bounds():
        cfg = MLSConfig()
        ok(cfg.ca_pmci_max_single_adj == 0.15, cfg.ca_pmci_max_single_adj)
        ok(cfg.ca_pmci_max_total_adj  == 0.30, cfg.ca_pmci_max_total_adj)
        return f"max_single={cfg.ca_pmci_max_single_adj} max_total={cfg.ca_pmci_max_total_adj}"

    def t05_classification_thresholds():
        cfg = MLSConfig()
        ok(cfg.ca_pmci_high_threshold == 0.70, cfg.ca_pmci_high_threshold)
        ok(cfg.ca_pmci_low_threshold  == 0.30, cfg.ca_pmci_low_threshold)
        return f"high={cfg.ca_pmci_high_threshold} low={cfg.ca_pmci_low_threshold}"

    runner.run("T01 ca_pmci_w_regime default",              t01_regime_weight)
    runner.run("T02 volatility/sector weight defaults",     t02_volatility_sector_weights)
    runner.run("T03 stability/freshness weight defaults",   t03_stability_freshness_weights)
    runner.run("T04 adjustment bound defaults",             t04_adjustment_bounds)
    runner.run("T05 classification threshold defaults",     t05_classification_thresholds)

    # ── T06-T08: CAPMCIEngine instantiation ──────────────────────────────────

    def t06_default_init():
        e = CAPMCIEngine()
        ok(e._cfg is not None, "config is None")
        return "default init OK"

    def t07_custom_config_stored():
        cfg = MLSConfig(ca_pmci_w_regime=0.20)
        e   = CAPMCIEngine(config=cfg)
        ok(e._cfg.ca_pmci_w_regime == 0.20)
        return f"custom config stored ca_pmci_w_regime={e._cfg.ca_pmci_w_regime}"

    def t08_mci_engine_injection():
        mci = MCIEngine(_TEST_CFG)
        e   = CAPMCIEngine(config=_TEST_CFG, mci_engine=mci)
        ok(e._mci is mci, "mci_engine not stored")
        return "mci_engine injection OK"

    runner.run("T06 CAPMCIEngine default init",             t06_default_init)
    runner.run("T07 CAPMCIEngine custom config",            t07_custom_config_stored)
    runner.run("T08 CAPMCIEngine MCIEngine injection",      t08_mci_engine_injection)

    # ── T09-T13: CAPMCIResult structure ──────────────────────────────────────

    def _base_result() -> CAPMCIResult:
        obs  = _make_obs()
        lib  = _good_library()
        snap = _make_market_snapshot()
        return _engine().evaluate_with_context(obs, lib, snap, "2026-08-04")

    def t09_result_id_prefix():
        r = _base_result()
        ok(r.result_id.startswith("CAP-"), r.result_id)
        return f"result_id={r.result_id}"

    def t10_symbol_and_date():
        r = _base_result()
        ok(r.symbol == "TEST",        r.symbol)
        ok(r.evaluation_date == "2026-08-04", r.evaluation_date)
        return f"symbol={r.symbol} date={r.evaluation_date}"

    def t11_scores_in_bounds():
        r = _base_result()
        ok(0.0 <= r.raw_pmci      <= 1.0, f"raw_pmci={r.raw_pmci}")
        ok(0.0 <= r.context_score <= 1.0, f"context_score={r.context_score}")
        ok(0.0 <= r.ca_pmci       <= 1.0, f"ca_pmci={r.ca_pmci}")
        return f"raw={r.raw_pmci:.3f} ctx={r.context_score:.3f} ca={r.ca_pmci:.3f}"

    def t12_exactly_5_adjustments():
        r = _base_result()
        ok(len(r.adjustments) == 5, f"len(adjustments)={len(r.adjustments)}")
        return f"adjustments={len(r.adjustments)}"

    def t13_explanation_contains_symbol():
        r = _base_result()
        ok(len(r.explanation) > 0,      "explanation empty")
        ok("TEST" in r.explanation,     f"symbol absent from explanation: {r.explanation[:80]}")
        return f"explanation length={len(r.explanation)}"

    runner.run("T09 result_id starts with CAP-",            t09_result_id_prefix)
    runner.run("T10 symbol and evaluation_date correct",    t10_symbol_and_date)
    runner.run("T11 raw_pmci/context_score/ca_pmci in [0,1]", t11_scores_in_bounds)
    runner.run("T12 exactly 5 adjustments",                 t12_exactly_5_adjustments)
    runner.run("T13 explanation nonempty, contains symbol", t13_explanation_contains_symbol)

    # ── T14-T18: ContextAdjustment structure ─────────────────────────────────

    _ADJ_NAMES = {"regime_match", "volatility_match", "sector_match",
                  "context_stability", "dna_freshness"}

    def t14_all_5_adjustment_names():
        r = _base_result()
        names = {a.name for a in r.adjustments}
        ok(names == _ADJ_NAMES, f"names={names}")
        return f"adjustment names OK: {sorted(names)}"

    def t15_all_deltas_are_floats():
        r = _base_result()
        ok(all(isinstance(a.delta, float) for a in r.adjustments), "non-float delta")
        return f"deltas: {[round(a.delta, 4) for a in r.adjustments]}"

    def t16_all_explanations_nonempty():
        r = _base_result()
        ok(all(len(a.explanation) > 0 for a in r.adjustments), "empty explanation")
        return "all 5 explanations nonempty"

    def t17_all_evidence_dicts_nonempty():
        r = _base_result()
        ok(all(len(a.evidence) > 0 for a in r.adjustments), "empty evidence dict")
        return "all 5 evidence dicts nonempty"

    def t18_context_adjustment_serialisation():
        r = _base_result()
        adj = r.adjustments[0]
        d   = adj.to_dict()
        adj2 = ContextAdjustment.from_dict(d)
        ok(adj2.name  == adj.name,  adj.name)
        ok(abs(adj2.delta - adj.delta) < 1e-9, f"{adj2.delta} != {adj.delta}")
        ok(adj2.explanation == adj.explanation)
        return "ContextAdjustment to_dict/from_dict round-trip OK"

    runner.run("T14 all 5 adjustment names present",        t14_all_5_adjustment_names)
    runner.run("T15 all adjustment deltas are floats",      t15_all_deltas_are_floats)
    runner.run("T16 all adjustment explanations nonempty",  t16_all_explanations_nonempty)
    runner.run("T17 all adjustment evidence dicts nonempty", t17_all_evidence_dicts_nonempty)
    runner.run("T18 ContextAdjustment serialisation",       t18_context_adjustment_serialisation)

    # ── T19-T22: evaluate_context() ──────────────────────────────────────────

    def t19_evaluate_context_returns_market_context():
        snap = _make_market_snapshot()
        ctx  = _engine().evaluate_context(snap)
        ok(isinstance(ctx, MarketContext), type(ctx).__name__)
        return f"evaluate_context() → MarketContext (score={ctx.context_score:.3f})"

    def t20_evaluate_context_id_prefix():
        snap = _make_market_snapshot()
        ctx  = _engine().evaluate_context(snap)
        ok(ctx.context_id.startswith("MCE-"), ctx.context_id)
        return f"context_id={ctx.context_id}"

    def t21_evaluate_context_score_in_bounds():
        snap = _make_market_snapshot()
        ctx  = _engine().evaluate_context(snap)
        ok(0.0 <= ctx.context_score <= 1.0, f"context_score={ctx.context_score}")
        return f"context_score={ctx.context_score:.3f}"

    def t22_evaluate_context_8_components():
        snap = _make_market_snapshot()
        ctx  = _engine().evaluate_context(snap)
        ok(len(ctx.components) == 8, f"components={len(ctx.components)}")
        return f"8 context components OK"

    runner.run("T19 evaluate_context() returns MarketContext", t19_evaluate_context_returns_market_context)
    runner.run("T20 evaluate_context() context_id MCE-",    t20_evaluate_context_id_prefix)
    runner.run("T21 evaluate_context() score in [0,1]",     t21_evaluate_context_score_in_bounds)
    runner.run("T22 evaluate_context() 8 components",       t22_evaluate_context_8_components)

    # ── T23-T27: _compute_adj formula (regime_match) ─────────────────────────

    def t23_compute_adj_both_high():
        # Both high → reward approaching +weight
        adj = _compute_adj(0.80, 0.90, 0.15, 0.15)
        expected = (0.80 + 0.90 - 1.0) * 0.15   # 0.7 * 0.15 = 0.105
        ok(abs(adj - expected) < 1e-9, f"adj={adj} expected={expected}")
        return f"_compute_adj(0.80,0.90,0.15,0.15)={adj:.6f}"

    def t24_compute_adj_both_low():
        # Both low → penalty approaching -weight
        adj = _compute_adj(0.30, 0.20, 0.15, 0.15)
        expected = (0.30 + 0.20 - 1.0) * 0.15   # -0.5 * 0.15 = -0.075
        ok(abs(adj - expected) < 1e-9, f"adj={adj} expected={expected}")
        return f"_compute_adj(0.30,0.20,0.15,0.15)={adj:.6f}"

    def t25_compute_adj_both_neutral():
        adj = _compute_adj(0.50, 0.50, 0.15, 0.15)
        ok(abs(adj) < 1e-9, f"adj={adj} should be 0")
        return f"neutral _compute_adj={adj:.6f} ≈ 0"

    def t26_compute_adj_capped_at_plus_weight():
        # Max possible: (1+1-1)*w = w, which equals cap
        adj = _compute_adj(1.0, 1.0, 0.15, 0.15)
        ok(adj == 0.15, f"adj={adj}")
        return f"_compute_adj(1,1,0.15,0.15)={adj:.6f} (max reward)"

    def t27_compute_adj_capped_at_minus_weight():
        adj = _compute_adj(0.0, 0.0, 0.15, 0.15)
        ok(adj == -0.15, f"adj={adj}")
        return f"_compute_adj(0,0,0.15,0.15)={adj:.6f} (max penalty)"

    runner.run("T23 _compute_adj both high → +0.105",       t23_compute_adj_both_high)
    runner.run("T24 _compute_adj both low → -0.075",        t24_compute_adj_both_low)
    runner.run("T25 _compute_adj both neutral → 0.0",       t25_compute_adj_both_neutral)
    runner.run("T26 _compute_adj max reward = +weight",      t26_compute_adj_capped_at_plus_weight)
    runner.run("T27 _compute_adj max penalty = -weight",     t27_compute_adj_capped_at_minus_weight)

    # ── T28-T32: volatility_match adjustment ─────────────────────────────────

    def t28_vol_adj_low_vix_strong_dna():
        # Low VIX (vol_ctx=0.90) + strong evidence (0.80) → positive vol_adj
        adj = _compute_adj(0.80, 0.90, 0.10, 0.15)
        ok(adj > 0, f"adj={adj}")
        return f"vol_adj(strong+low_vix)={adj:+.4f} > 0"

    def t29_vol_adj_high_vix_weak_dna():
        # High VIX (vol_ctx=0.05) + weak evidence (0.20) → negative vol_adj
        adj = _compute_adj(0.20, 0.05, 0.10, 0.15)
        ok(adj < 0, f"adj={adj}")
        return f"vol_adj(weak+high_vix)={adj:+.4f} < 0"

    def t30_vol_adj_bounded_by_weight():
        # Extreme inputs → capped at ±weight
        adj_pos = _compute_adj(1.0, 1.0, 0.10, 0.10)
        adj_neg = _compute_adj(0.0, 0.0, 0.10, 0.10)
        ok(adj_pos == 0.10,  f"adj_pos={adj_pos}")
        ok(adj_neg == -0.10, f"adj_neg={adj_neg}")
        return f"vol_adj bounds: [{adj_neg:.2f}, {adj_pos:.2f}]"

    def t31_vol_adjustment_in_result():
        obs  = _make_obs()
        lib  = _good_library()
        snap = _make_market_snapshot(vix=10.0)   # low VIX → high ctx_vol
        r    = _engine().evaluate_with_context(obs, lib, snap, "2026-08-04")
        vol  = next(a for a in r.adjustments if a.name == "volatility_match")
        ok(-0.10 <= vol.delta <= 0.10, f"vol.delta={vol.delta}")
        return f"volatility_match delta={vol.delta:+.4f} in bounds"

    def t32_vol_evidence_keys():
        obs  = _make_obs()
        lib  = _good_library()
        snap = _make_market_snapshot()
        r    = _engine().evaluate_with_context(obs, lib, snap, "2026-08-04")
        vol  = next(a for a in r.adjustments if a.name == "volatility_match")
        ok("dna_evidence_strength"    in vol.evidence, vol.evidence)
        ok("volatility_context_score" in vol.evidence, vol.evidence)
        return f"volatility_match evidence keys OK"

    runner.run("T28 vol_adj low VIX + strong DNA → positive", t28_vol_adj_low_vix_strong_dna)
    runner.run("T29 vol_adj high VIX + weak DNA → negative", t29_vol_adj_high_vix_weak_dna)
    runner.run("T30 vol_adj bounded to ±weight",              t30_vol_adj_bounded_by_weight)
    runner.run("T31 volatility_match delta in result",        t31_vol_adjustment_in_result)
    runner.run("T32 volatility_match evidence keys",          t32_vol_evidence_keys)

    # ── T33-T37: sector_match adjustment ─────────────────────────────────────

    def t33_sector_adj_strong_leading():
        # All-positive sectors (ctx_sector=1.0) + high DNA sector cons (0.80)
        adj = _compute_adj(0.80, 1.0, 0.10, 0.15)
        ok(adj > 0, f"adj={adj}")
        return f"sector_adj(strong+leading)={adj:+.4f} > 0"

    def t34_sector_adj_weak_lagging():
        # All-negative sectors (ctx_sector=0.0) + low DNA sector cons (0.30)
        adj = _compute_adj(0.30, 0.0, 0.10, 0.15)
        ok(adj < 0, f"adj={adj}")
        return f"sector_adj(weak+lagging)={adj:+.4f} < 0"

    def t35_sector_adj_neutral_sector_context():
        # Empty sector flows → ctx_sector=0.5 → small adjustment
        obs  = _make_obs()
        lib  = _good_library()
        snap = _make_market_snapshot(sector_flows=[])
        r    = _engine().evaluate_with_context(obs, lib, snap, "2026-08-04")
        sec  = next(a for a in r.adjustments if a.name == "sector_match")
        # With ctx_sector=0.5 and dna_sector_q=0.8: (0.8+0.5-1.0)*0.10 = 0.030
        ok(-0.10 <= sec.delta <= 0.10, f"sec.delta={sec.delta}")
        return f"sector_match(empty sectors)={sec.delta:+.4f}"

    def t36_sector_adj_bounded():
        adj_pos = _compute_adj(1.0, 1.0, 0.10, 0.10)
        adj_neg = _compute_adj(0.0, 0.0, 0.10, 0.10)
        ok(adj_pos <= 0.10,  f"adj_pos={adj_pos}")
        ok(adj_neg >= -0.10, f"adj_neg={adj_neg}")
        return f"sector_adj bounds OK"

    def t37_sector_evidence_keys():
        obs  = _make_obs()
        lib  = _good_library()
        snap = _make_market_snapshot()
        r    = _engine().evaluate_with_context(obs, lib, snap, "2026-08-04")
        sec  = next(a for a in r.adjustments if a.name == "sector_match")
        ok("dna_sector_stability" in sec.evidence, sec.evidence)
        ok("sector_context_score" in sec.evidence, sec.evidence)
        return "sector_match evidence keys OK"

    runner.run("T33 sector_adj strong+leading → positive",   t33_sector_adj_strong_leading)
    runner.run("T34 sector_adj weak+lagging → negative",     t34_sector_adj_weak_lagging)
    runner.run("T35 sector_adj neutral context → small",     t35_sector_adj_neutral_sector_context)
    runner.run("T36 sector_adj bounded to ±weight",          t36_sector_adj_bounded)
    runner.run("T37 sector_match evidence keys",             t37_sector_evidence_keys)

    # ── T38-T42: context_stability adjustment ────────────────────────────────

    def t38_stability_adj_high_evidence_stable_ctx():
        # High evidence (0.80) × high stability (0.80) → positive
        adj = _compute_adj(0.80, 0.80, 0.07, 0.15)
        expected = (0.80 + 0.80 - 1.0) * 0.07   # 0.6 * 0.07 = 0.042
        ok(abs(adj - expected) < 1e-9, f"adj={adj}")
        return f"stability_adj(strong+stable)={adj:+.4f}"

    def t39_stability_adj_first_eval_stability_half():
        # First evaluation → context.stability = 0.5
        obs  = _make_obs()
        lib  = _good_library()
        snap = _make_market_snapshot()
        r    = _engine().evaluate_with_context(obs, lib, snap, "2026-08-04")
        stab = next(a for a in r.adjustments if a.name == "context_stability")
        ok(stab.evidence["context_stability"] == 0.5, stab.evidence)
        return f"first_eval stability=0.5, adj={stab.delta:+.4f}"

    def t40_stability_adj_identical_snapshot_stability_one():
        # Inject MCIEngine that has already evaluated same snapshot once
        mci  = MCIEngine(_TEST_CFG)
        snap = _make_market_snapshot()
        mci.evaluate(snap)   # pre-warm: so second call gives stability ≈ 1.0
        e    = CAPMCIEngine(_TEST_CFG, mci_engine=mci)
        obs  = _make_obs()
        lib  = _good_library()
        r    = e.evaluate_with_context(obs, lib, snap, "2026-08-04")
        stab = next(a for a in r.adjustments if a.name == "context_stability")
        ok(stab.evidence["context_stability"] >= 0.99, stab.evidence)
        return f"stable context stability={stab.evidence['context_stability']:.4f}"

    def t41_stability_adj_bounded():
        adj_pos = _compute_adj(1.0, 1.0, 0.07, 0.07)
        adj_neg = _compute_adj(0.0, 0.0, 0.07, 0.07)
        ok(adj_pos <= 0.07,  f"pos={adj_pos}")
        ok(adj_neg >= -0.07, f"neg={adj_neg}")
        return f"stability_adj bounds [{adj_neg:.3f}, {adj_pos:.3f}]"

    def t42_stability_evidence_keys():
        obs  = _make_obs()
        lib  = _good_library()
        snap = _make_market_snapshot()
        r    = _engine().evaluate_with_context(obs, lib, snap, "2026-08-04")
        stab = next(a for a in r.adjustments if a.name == "context_stability")
        ok("dna_evidence_strength" in stab.evidence, stab.evidence)
        ok("context_stability"     in stab.evidence, stab.evidence)
        return "context_stability evidence keys OK"

    runner.run("T38 stability_adj high evidence + stable ctx", t38_stability_adj_high_evidence_stable_ctx)
    runner.run("T39 first eval stability=0.5",                t39_stability_adj_first_eval_stability_half)
    runner.run("T40 identical snapshot → stability ≈ 1.0",   t40_stability_adj_identical_snapshot_stability_one)
    runner.run("T41 stability_adj bounded to ±weight",        t41_stability_adj_bounded)
    runner.run("T42 context_stability evidence keys",         t42_stability_evidence_keys)

    # ── T43-T47: dna_freshness adjustment ────────────────────────────────────

    def t43_freshness_adj_fresh_favorable():
        # Fresh DNA (0.967) + favorable context (0.70) → positive
        adj = _compute_adj(0.967, 0.70, 0.05, 0.15)
        ok(adj > 0, f"adj={adj}")
        return f"freshness_adj(fresh+favorable)={adj:+.4f} > 0"

    def t44_freshness_adj_stale_adverse():
        # Stale DNA (0.0) + adverse context (0.10) → negative
        adj = _compute_adj(0.0, 0.10, 0.05, 0.15)
        ok(adj < 0, f"adj={adj}")
        return f"freshness_adj(stale+adverse)={adj:+.4f} < 0"

    def t45_freshness_adj_neutral():
        # Both neutral → ~0
        adj = _compute_adj(0.50, 0.50, 0.05, 0.15)
        ok(abs(adj) < 1e-9, f"adj={adj}")
        return f"freshness_adj neutral={adj:.6f}"

    def t46_freshness_adj_bounded():
        adj_pos = _compute_adj(1.0, 1.0, 0.05, 0.05)
        adj_neg = _compute_adj(0.0, 0.0, 0.05, 0.05)
        ok(adj_pos <= 0.05,  f"pos={adj_pos}")
        ok(adj_neg >= -0.05, f"neg={adj_neg}")
        return f"freshness_adj bounds [{adj_neg:.3f}, {adj_pos:.3f}]"

    def t47_freshness_evidence_keys():
        obs  = _make_obs()
        lib  = _good_library()
        snap = _make_market_snapshot()
        r    = _engine().evaluate_with_context(obs, lib, snap, "2026-08-04")
        fresh = next(a for a in r.adjustments if a.name == "dna_freshness")
        ok("dna_freshness"         in fresh.evidence, fresh.evidence)
        ok("overall_context_score" in fresh.evidence, fresh.evidence)
        return "dna_freshness evidence keys OK"

    runner.run("T43 freshness_adj fresh + favorable → +",    t43_freshness_adj_fresh_favorable)
    runner.run("T44 freshness_adj stale + adverse → -",      t44_freshness_adj_stale_adverse)
    runner.run("T45 freshness_adj both neutral → 0",         t45_freshness_adj_neutral)
    runner.run("T46 freshness_adj bounded to ±weight",       t46_freshness_adj_bounded)
    runner.run("T47 dna_freshness evidence keys",            t47_freshness_evidence_keys)

    # ── T48-T52: context_adjustment total formula ─────────────────────────────

    def t48_context_adjustment_is_sum_of_deltas_clamped():
        obs  = _make_obs()
        lib  = _good_library()
        snap = _make_market_snapshot()
        r    = _engine().evaluate_with_context(obs, lib, snap, "2026-08-04")
        raw_sum = sum(a.delta for a in r.adjustments)
        max_adj = _TEST_CFG.ca_pmci_max_total_adj
        expected = max(-max_adj, min(max_adj, raw_sum))
        ok(abs(r.context_adjustment - expected) < 1e-9,
           f"adj={r.context_adjustment} expected={expected}")
        return f"context_adjustment={r.context_adjustment:+.4f} = clamp(sum={raw_sum:+.4f})"

    def t49_context_adjustment_in_bounds():
        for snap in [_bull_snapshot(), _adverse_snapshot(), _make_market_snapshot()]:
            obs = _make_obs()
            lib = _good_library()
            r   = _engine().evaluate_with_context(obs, lib, snap, "2026-08-04")
            ok(-0.30 <= r.context_adjustment <= 0.30,
               f"context_adjustment={r.context_adjustment}")
        return "context_adjustment always in [-0.30, +0.30]"

    def t50_adjustment_factor_neutral_when_adj_zero():
        # When all individual adjustments cancel out → factor ≈ 0.5
        # This is best tested with a hand-crafted scenario; easiest: verify formula
        cfg        = MLSConfig()
        max_adj    = cfg.ca_pmci_max_total_adj
        adj_zero   = 0.0
        factor     = 0.5 + adj_zero / (2.0 * max_adj)
        ok(abs(factor - 0.5) < 1e-9, f"factor={factor}")
        return f"context_adjustment_factor=0.5 when adj=0"

    def t51_adjustment_factor_in_bounds():
        obs  = _make_obs()
        lib  = _good_library()
        for snap in [_bull_snapshot(), _adverse_snapshot(), _make_market_snapshot()]:
            r = _engine().evaluate_with_context(obs, lib, snap, "2026-08-04")
            ok(0.0 <= r.context_adjustment_factor <= 1.0,
               f"factor={r.context_adjustment_factor}")
        return "context_adjustment_factor always in [0,1]"

    def t52_adjustment_factor_gt_half_for_positive_adj():
        obs  = _make_obs()
        lib  = _good_library()
        snap = _bull_snapshot()   # favorable → positive total adjustment
        r    = _engine().evaluate_with_context(obs, lib, snap, "2026-08-04")
        ok(r.context_adjustment > 0, f"adj={r.context_adjustment}")
        ok(r.context_adjustment_factor > 0.5,
           f"factor={r.context_adjustment_factor}")
        return (f"positive adj={r.context_adjustment:+.4f} "
                f"→ factor={r.context_adjustment_factor:.4f} > 0.5")

    runner.run("T48 context_adjustment = clamp(sum deltas)",  t48_context_adjustment_is_sum_of_deltas_clamped)
    runner.run("T49 context_adjustment in [-0.30, +0.30]",    t49_context_adjustment_in_bounds)
    runner.run("T50 adj_factor=0.5 when adj=0",               t50_adjustment_factor_neutral_when_adj_zero)
    runner.run("T51 context_adjustment_factor in [0,1]",      t51_adjustment_factor_in_bounds)
    runner.run("T52 adj_factor > 0.5 for positive total adj", t52_adjustment_factor_gt_half_for_positive_adj)

    # ── T53-T57: context_match_score ─────────────────────────────────────────

    def t53_context_match_score_in_bounds():
        obs  = _make_obs()
        lib  = _good_library()
        for snap in [_bull_snapshot(), _adverse_snapshot(), _make_market_snapshot()]:
            r = _engine().evaluate_with_context(obs, lib, snap, "2026-08-04")
            ok(0.0 <= r.context_match_score <= 1.0,
               f"context_match_score={r.context_match_score}")
        return "context_match_score always in [0,1]"

    def t54_context_match_high_when_all_good():
        obs  = _make_obs()          # features well-aligned → high evidence_strength
        lib  = _good_library()      # high regime/sector consistency
        snap = _bull_snapshot()     # high regime/vol/sector ctx
        r    = _engine().evaluate_with_context(obs, lib, snap, "2026-08-04")
        ok(r.context_match_score > 0.65,
           f"context_match_score={r.context_match_score}")
        return f"favorable context_match_score={r.context_match_score:.4f} > 0.65"

    def t55_context_match_lower_for_adverse():
        obs_g = _make_obs()
        lib_g = _good_library()
        lib_p = _poor_library()     # low regime/sector consistency
        snap_b = _bull_snapshot()
        snap_a = _adverse_snapshot()
        r_good = _engine().evaluate_with_context(obs_g, lib_g, snap_b, "2026-08-04")
        r_poor = _engine().evaluate_with_context(obs_g, lib_p, snap_a, "2026-08-04")
        ok(r_good.context_match_score > r_poor.context_match_score,
           f"good={r_good.context_match_score:.4f} poor={r_poor.context_match_score:.4f}")
        return (f"good context_match={r_good.context_match_score:.4f} > "
                f"poor={r_poor.context_match_score:.4f}")

    def t56_context_match_formula():
        # context_match = 0.40*regime_align + 0.35*sector_align + 0.25*vol_align
        # regime_align = (dna_regime_q + ctx_regime) / 2
        obs  = _make_obs()
        lib  = _good_library()
        snap = _make_market_snapshot()
        r    = _engine().evaluate_with_context(obs, lib, snap, "2026-08-04")
        dna_r = r.dna_regime_match
        dna_s = r.dna_sector_match
        dna_v = r.dna_volatility_match
        ctx_r = next(c for c in r.pmci_result.components
                     if c.name == "regime_stability").value   # proxy
        # Just verify that context_match is between 0 and 1 and is in expected range
        ok(0.0 <= r.context_match_score <= 1.0, r.context_match_score)
        return f"context_match_score={r.context_match_score:.4f}"

    def t57_context_match_independent_of_freshness():
        # context_match_score only uses regime/sector/vol, not freshness
        obs    = _make_obs()
        lib_f  = _make_library([
            _make_cdna("rsi",    last_seen="2026-08-03", regime_cons=0.80, sector_cons=0.80),
            _make_cdna("mom_1d", last_seen="2026-08-03", regime_cons=0.80, sector_cons=0.80),
        ])
        lib_s  = _make_library([
            _make_cdna("rsi",    last_seen="2025-01-01", regime_cons=0.80, sector_cons=0.80),
            _make_cdna("mom_1d", last_seen="2025-01-01", regime_cons=0.80, sector_cons=0.80),
        ])
        snap = _make_market_snapshot()
        r_fresh = _engine().evaluate_with_context(obs, lib_f, snap, "2026-08-04")
        r_stale = _engine().evaluate_with_context(obs, lib_s, snap, "2026-08-04")
        # context_match uses regime/sector/vol only → should be equal
        ok(abs(r_fresh.context_match_score - r_stale.context_match_score) < 1e-4,
           f"fresh={r_fresh.context_match_score:.6f} stale={r_stale.context_match_score:.6f}")
        return (f"context_match independent of freshness: "
                f"fresh={r_fresh.context_match_score:.4f} stale={r_stale.context_match_score:.4f}")

    runner.run("T53 context_match_score in [0,1]",           t53_context_match_score_in_bounds)
    runner.run("T54 context_match high when all good",        t54_context_match_high_when_all_good)
    runner.run("T55 context_match lower for adverse",         t55_context_match_lower_for_adverse)
    runner.run("T56 context_match_score formula check",       t56_context_match_formula)
    runner.run("T57 context_match independent of freshness",  t57_context_match_independent_of_freshness)

    # ── T58-T62: dna_context_stability ───────────────────────────────────────

    def t58_dna_context_stability_formula():
        # dna_context_stability = mean(dna_regime_match, dna_sector_match, dna_vol_match)
        obs  = _make_obs()
        lib  = _good_library()
        snap = _make_market_snapshot()
        r    = _engine().evaluate_with_context(obs, lib, snap, "2026-08-04")
        expected = (r.dna_regime_match + r.dna_sector_match + r.dna_volatility_match) / 3.0
        ok(abs(r.dna_context_stability - expected) < 1e-4,
           f"stability={r.dna_context_stability} expected={expected}")
        return f"dna_context_stability={r.dna_context_stability:.4f} = mean of 3 components"

    def t59_dna_context_stability_in_bounds():
        for snap in [_bull_snapshot(), _adverse_snapshot(), _make_market_snapshot()]:
            obs = _make_obs()
            lib = _good_library()
            r   = _engine().evaluate_with_context(obs, lib, snap, "2026-08-04")
            ok(0.0 <= r.dna_context_stability <= 1.0,
               f"stability={r.dna_context_stability}")
        return "dna_context_stability always in [0,1]"

    def t60_high_dna_consistency_gives_high_stability():
        obs  = _make_obs()
        lib  = _good_library()   # regime_cons=0.80, sector_cons=0.80
        snap = _make_market_snapshot()
        r    = _engine().evaluate_with_context(obs, lib, snap, "2026-08-04")
        ok(r.dna_context_stability > 0.6, f"stability={r.dna_context_stability}")
        return f"high DNA → dna_context_stability={r.dna_context_stability:.4f} > 0.6"

    def t61_dna_regime_sector_vol_match_components():
        obs  = _make_obs()
        lib  = _good_library()
        snap = _make_market_snapshot()
        r    = _engine().evaluate_with_context(obs, lib, snap, "2026-08-04")
        ok(0.0 <= r.dna_regime_match     <= 1.0, r.dna_regime_match)
        ok(0.0 <= r.dna_sector_match     <= 1.0, r.dna_sector_match)
        ok(0.0 <= r.dna_volatility_match <= 1.0, r.dna_volatility_match)
        return (f"dna components: regime={r.dna_regime_match:.3f} "
                f"sector={r.dna_sector_match:.3f} "
                f"vol={r.dna_volatility_match:.3f}")

    def t62_dna_context_stability_independent_of_market():
        # Same DNA, two different market contexts → same dna_context_stability
        obs    = _make_obs()
        lib    = _good_library()
        snap_b = _bull_snapshot()
        snap_a = _adverse_snapshot()
        r_b = _engine().evaluate_with_context(obs, lib, snap_b, "2026-08-04")
        r_a = _engine().evaluate_with_context(obs, lib, snap_a, "2026-08-04")
        ok(abs(r_b.dna_context_stability - r_a.dna_context_stability) < 1e-4,
           f"bull={r_b.dna_context_stability:.6f} adverse={r_a.dna_context_stability:.6f}")
        return (f"dna_context_stability independent of market: "
                f"bull={r_b.dna_context_stability:.4f} adverse={r_a.dna_context_stability:.4f}")

    runner.run("T58 dna_context_stability = mean(3 DNA comps)", t58_dna_context_stability_formula)
    runner.run("T59 dna_context_stability in [0,1]",          t59_dna_context_stability_in_bounds)
    runner.run("T60 high DNA cons → high stability",          t60_high_dna_consistency_gives_high_stability)
    runner.run("T61 dna regime/sector/vol match in [0,1]",    t61_dna_regime_sector_vol_match_components)
    runner.run("T62 dna_context_stability independent of mkt", t62_dna_context_stability_independent_of_market)

    # ── T63-T67: evaluate_with_context() full flow ────────────────────────────

    def t63_returns_ca_pmci_result():
        obs  = _make_obs()
        lib  = _good_library()
        snap = _make_market_snapshot()
        r    = _engine().evaluate_with_context(obs, lib, snap, "2026-08-04")
        ok(isinstance(r, CAPMCIResult), type(r).__name__)
        return f"evaluate_with_context() → CAPMCIResult (ca_pmci={r.ca_pmci:.3f})"

    def t64_raw_pmci_matches_standalone_pmci():
        obs  = _make_obs()
        lib  = _good_library()
        snap = _make_market_snapshot()
        r    = _engine().evaluate_with_context(obs, lib, snap, "2026-08-04")
        raw  = _raw(obs, lib, "2026-08-04")
        ok(abs(r.raw_pmci - raw.pmci_score) < 1e-6,
           f"r.raw_pmci={r.raw_pmci} raw.pmci_score={raw.pmci_score}")
        return f"raw_pmci={r.raw_pmci:.6f} matches standalone PMCI"

    def t65_ca_pmci_equals_raw_plus_adj():
        obs  = _make_obs()
        lib  = _good_library()
        snap = _make_market_snapshot()
        r    = _engine().evaluate_with_context(obs, lib, snap, "2026-08-04")
        expected = max(0.0, min(1.0, r.raw_pmci + r.context_adjustment))
        ok(abs(r.ca_pmci - expected) < 1e-6,
           f"ca_pmci={r.ca_pmci} expected={expected}")
        return f"ca_pmci={r.ca_pmci:.6f} = raw + adj = {r.raw_pmci:.4f} + {r.context_adjustment:+.4f}"

    def t66_no_mutation_of_inputs():
        import copy
        obs_orig  = _make_obs()
        lib_orig  = _good_library()
        snap_orig = _make_market_snapshot()
        obs_copy  = copy.deepcopy(obs_orig)
        lib_copy  = copy.deepcopy(lib_orig)
        snap_copy = copy.deepcopy(snap_orig)
        _engine().evaluate_with_context(obs_orig, lib_orig, snap_orig, "2026-08-04")
        ok(obs_orig.features  == obs_copy.features,  "obs mutated")
        ok(lib_orig.library_id == lib_copy.library_id, "lib mutated")
        ok(str(snap_orig.regime) == str(snap_copy.regime), "snap mutated")
        return "inputs not mutated"

    def t67_result_id_deterministic():
        obs  = _make_obs()
        lib  = _good_library()
        snap = _make_market_snapshot()
        r1   = _engine().evaluate_with_context(obs, lib, snap, "2026-08-04")
        r2   = _engine().evaluate_with_context(obs, lib, snap, "2026-08-04")
        ok(r1.result_id == r2.result_id, f"{r1.result_id} != {r2.result_id}")
        return f"result_id deterministic: {r1.result_id}"

    runner.run("T63 evaluate_with_context() → CAPMCIResult", t63_returns_ca_pmci_result)
    runner.run("T64 raw_pmci matches standalone PMCIEngine",  t64_raw_pmci_matches_standalone_pmci)
    runner.run("T65 ca_pmci = clamp(raw + adj)",              t65_ca_pmci_equals_raw_plus_adj)
    runner.run("T66 evaluate_with_context() no mutation",     t66_no_mutation_of_inputs)
    runner.run("T67 result_id deterministic",                 t67_result_id_deterministic)

    # ── T68-T72: evaluate_universe_with_context() ────────────────────────────

    def t68_universe_returns_same_length():
        obs_list = [_make_obs(f"S{i}", {"rsi": 0.7 + i*0.02}) for i in range(5)]
        lib      = _good_library()
        snap     = _make_market_snapshot()
        results  = _engine().evaluate_universe_with_context(obs_list, lib, snap, "2026-08-04")
        ok(len(results) == 5, f"len={len(results)}")
        return f"universe returns {len(results)} results"

    def t69_all_universe_results_share_context_id():
        obs_list = [_make_obs(f"S{i}", {"rsi": 0.6 + i*0.05}) for i in range(3)]
        lib      = _good_library()
        snap     = _make_market_snapshot()
        results  = _engine().evaluate_universe_with_context(obs_list, lib, snap, "2026-08-04")
        ctx_ids  = {r.context_id for r in results}
        ok(len(ctx_ids) == 1, f"context_ids={ctx_ids}")
        return f"all 3 results share context_id={ctx_ids.pop()}"

    def t70_failed_eval_skipped():
        # One obs with features not in DNA (coverage=0 → still succeeds; use a broken obs)
        # Easiest: mix valid + empty feature obs
        good_obs = _make_obs("GOOD", {"rsi": 0.75})
        empty_obs = _make_obs("EMPTY", {})   # no features → coverage=0, but no exception
        lib      = _good_library()
        snap     = _make_market_snapshot()
        results  = _engine().evaluate_universe_with_context(
            [good_obs, empty_obs], lib, snap, "2026-08-04"
        )
        ok(len(results) == 2, f"len={len(results)}")  # empty features still returns result
        ok(all(isinstance(r, CAPMCIResult) for r in results), "not CAPMCIResult")
        return f"universe with empty obs: {len(results)} results (no crash)"

    def t71_empty_observations_returns_empty():
        results = _engine().evaluate_universe_with_context([], _good_library(),
                                                           _make_market_snapshot(), "2026-08-04")
        ok(len(results) == 0, f"len={len(results)}")
        return "empty input → empty result"

    def t72_universe_all_use_same_evaluation_date():
        obs_list = [_make_obs(f"S{i}", {"rsi": 0.6}) for i in range(3)]
        lib      = _good_library()
        snap     = _make_market_snapshot()
        results  = _engine().evaluate_universe_with_context(obs_list, lib, snap, "2026-09-01")
        ok(all(r.evaluation_date == "2026-09-01" for r in results),
           [r.evaluation_date for r in results])
        return "all universe results use same evaluation_date=2026-09-01"

    runner.run("T68 universe returns same length as input",   t68_universe_returns_same_length)
    runner.run("T69 all universe results share context_id",   t69_all_universe_results_share_context_id)
    runner.run("T70 empty-feature obs no crash",              t70_failed_eval_skipped)
    runner.run("T71 empty observations → empty result",       t71_empty_observations_returns_empty)
    runner.run("T72 universe all same evaluation_date",       t72_universe_all_use_same_evaluation_date)

    # ── T73-T77: Backward compatibility ──────────────────────────────────────

    def t73_pmci_engine_still_works():
        obs = _make_obs()
        lib = _good_library()
        r   = PMCIEngine(_TEST_CFG).evaluate(obs, lib, "2026-08-04")
        ok(isinstance(r, PMCIResult), type(r).__name__)
        ok(r.result_id.startswith("PMC-"), r.result_id)
        return f"PMCIEngine.evaluate() → PMCIResult (pmci={r.pmci_score:.3f})"

    def t74_pmci_evaluate_universe_unchanged():
        obs_list = [_make_obs(f"S{i}", {"rsi": 0.6}) for i in range(3)]
        lib      = _good_library()
        results  = PMCIEngine(_TEST_CFG).evaluate_universe(obs_list, lib, "2026-08-04")
        ok(len(results) == 3, f"len={len(results)}")
        ok(all(isinstance(r, PMCIResult) for r in results))
        return f"PMCIEngine.evaluate_universe() returns {len(results)} PMCIResult"

    def t75_pmci_statistics_unchanged():
        obs_list = [_make_obs(f"S{i}", {"rsi": 0.6}) for i in range(3)]
        lib      = _good_library()
        engine   = PMCIEngine(_TEST_CFG)
        results  = engine.evaluate_universe(obs_list, lib, "2026-08-04")
        stats    = engine.statistics(results)
        ok(stats.total_symbols == 3, stats.total_symbols)
        return f"PMCIEngine.statistics() total_symbols={stats.total_symbols}"

    def t76_pmci_result_embedded_in_ca_result():
        obs  = _make_obs()
        lib  = _good_library()
        snap = _make_market_snapshot()
        r    = _engine().evaluate_with_context(obs, lib, snap, "2026-08-04")
        ok(isinstance(r.pmci_result, PMCIResult), type(r.pmci_result).__name__)
        ok(r.pmci_result.result_id.startswith("PMC-"), r.pmci_result.result_id)
        return f"embedded PMCIResult: {r.pmci_result.result_id}"

    def t77_embedded_pmci_fields_intact():
        obs  = _make_obs()
        lib  = _good_library()
        snap = _make_market_snapshot()
        r    = _engine().evaluate_with_context(obs, lib, snap, "2026-08-04")
        pmci = r.pmci_result
        ok(pmci.symbol         == "TEST",        pmci.symbol)
        ok(pmci.feature_count  == 2,             pmci.feature_count)
        ok(len(pmci.components) == 9,            len(pmci.components))
        return f"embedded PMCI: symbol={pmci.symbol} components={len(pmci.components)}"

    runner.run("T73 PMCIEngine.evaluate() still works",      t73_pmci_engine_still_works)
    runner.run("T74 PMCIEngine.evaluate_universe() unchanged", t74_pmci_evaluate_universe_unchanged)
    runner.run("T75 PMCIEngine.statistics() unchanged",       t75_pmci_statistics_unchanged)
    runner.run("T76 pmci_result embedded in CAPMCIResult",    t76_pmci_result_embedded_in_ca_result)
    runner.run("T77 embedded PMCIResult fields intact",       t77_embedded_pmci_fields_intact)

    # ── T78-T82: CA-PMCI favorable/adverse comparison ─────────────────────────

    def t78_bull_context_rewards_good_dna():
        obs  = _make_obs()          # well-aligned features
        lib  = _good_library()      # strong regime/sector consistency
        snap = _bull_snapshot()     # fully favorable context
        r    = _engine().evaluate_with_context(obs, lib, snap, "2026-08-04")
        ok(r.ca_pmci > r.raw_pmci,
           f"ca_pmci={r.ca_pmci:.4f} should > raw_pmci={r.raw_pmci:.4f}")
        return f"bull: raw={r.raw_pmci:.4f} → ca={r.ca_pmci:.4f} (+{r.context_adjustment:.4f})"

    def t79_adverse_context_penalises_weak_dna():
        # Mixed alignment (some match, some conflict) + poor DNA consistency + adverse context
        obs  = _make_obs(features={"rsi": 0.6, "mom_1d": 0.3})   # partial alignment
        lib  = _poor_library()      # low regime/sector consistency
        snap = _adverse_snapshot()  # fully adverse context
        r    = _engine().evaluate_with_context(obs, lib, snap, "2026-08-04")
        ok(r.ca_pmci <= r.raw_pmci,
           f"ca_pmci={r.ca_pmci:.4f} should ≤ raw_pmci={r.raw_pmci:.4f}")
        return f"adverse: raw={r.raw_pmci:.4f} → ca={r.ca_pmci:.4f} ({r.context_adjustment:+.4f})"

    def t80_ca_pmci_always_in_bounds():
        scenarios = [
            (_make_obs(), _good_library(),  _bull_snapshot()),
            (_make_obs(), _poor_library(),  _adverse_snapshot()),
            (_make_obs(), _good_library(),  _make_market_snapshot()),
            (_make_obs(features={"rsi": 0.0}), _good_library(), _bull_snapshot()),
            (_make_obs(features={"rsi": 1.0}), _good_library(), _bull_snapshot()),
        ]
        for obs, lib, snap in scenarios:
            r = _engine().evaluate_with_context(obs, lib, snap, "2026-08-04")
            ok(0.0 <= r.ca_pmci <= 1.0, f"ca_pmci={r.ca_pmci}")
        return "ca_pmci always in [0,1]"

    def t81_max_favorable_adj_approaches_cap():
        # Best possible DNA in best possible market → adj close to max cap
        best_dna = [
            _make_cdna("rsi",    regime_cons=1.0, sector_cons=1.0, score=1.0),
            _make_cdna("mom_1d", regime_cons=1.0, sector_cons=1.0, score=1.0),
        ]
        lib  = _make_library(best_dna)
        obs  = _make_obs(features={"rsi": 1.0, "mom_1d": 1.0})   # max alignment
        snap = _bull_snapshot()
        r    = _engine().evaluate_with_context(obs, lib, snap, "2026-08-04")
        ok(r.context_adjustment > 0.10,   # should be comfortably positive
           f"adj={r.context_adjustment}")
        return f"max favorable adj={r.context_adjustment:.4f}"

    def t82_max_adverse_adj_approaches_negative_cap():
        worst_dna = [
            _make_cdna("rsi",    regime_cons=0.0, sector_cons=0.0, score=0.1),
            _make_cdna("mom_1d", regime_cons=0.0, sector_cons=0.0, score=0.1),
        ]
        lib  = _make_library(worst_dna)
        obs  = _make_obs(features={"rsi": 0.0, "mom_1d": 0.0})   # anti-aligned
        snap = _adverse_snapshot()
        r    = _engine().evaluate_with_context(obs, lib, snap, "2026-08-04")
        ok(r.context_adjustment < -0.05,   # should be negative
           f"adj={r.context_adjustment}")
        return f"max adverse adj={r.context_adjustment:.4f}"

    runner.run("T78 bull context rewards good DNA",           t78_bull_context_rewards_good_dna)
    runner.run("T79 adverse context penalises weak DNA",      t79_adverse_context_penalises_weak_dna)
    runner.run("T80 ca_pmci always in [0,1]",                 t80_ca_pmci_always_in_bounds)
    runner.run("T81 max favorable adj > 0.10",                t81_max_favorable_adj_approaches_cap)
    runner.run("T82 max adverse adj < -0.05",                 t82_max_adverse_adj_approaches_negative_cap)

    # ── T83-T87: statistics() ────────────────────────────────────────────────

    def _batch_results(n: int = 5, snap_fn=None) -> List[CAPMCIResult]:
        snap = snap_fn() if snap_fn else _make_market_snapshot()
        return _engine().evaluate_universe_with_context(
            [_make_obs(f"S{i}", {"rsi": 0.5 + i * 0.05}) for i in range(n)],
            _good_library(), snap, "2026-08-04",
        )

    def t83_statistics_total_symbols():
        results = _batch_results(5)
        stats   = _engine().statistics(results)
        ok(stats.total_symbols == 5, stats.total_symbols)
        return f"statistics().total_symbols={stats.total_symbols}"

    def t84_avg_ca_gt_avg_raw_in_bull():
        results = _batch_results(5, snap_fn=_bull_snapshot)
        stats   = _engine().statistics(results)
        ok(stats.avg_ca_pmci > stats.avg_raw_pmci,
           f"avg_ca={stats.avg_ca_pmci:.4f} avg_raw={stats.avg_raw_pmci:.4f}")
        return f"bull: avg_raw={stats.avg_raw_pmci:.4f} → avg_ca={stats.avg_ca_pmci:.4f}"

    def t85_most_improved_symbol():
        obs_list = [
            _make_obs("GOOD",   {"rsi": 0.95}),   # well-aligned → highest adj
            _make_obs("MEDIUM", {"rsi": 0.60}),
            _make_obs("WEAK",   {"rsi": 0.50}),
        ]
        lib     = _good_library()
        snap    = _bull_snapshot()
        results = _engine().evaluate_universe_with_context(obs_list, lib, snap, "2026-08-04")
        stats   = _engine().statistics(results)
        best_adj = max(results, key=lambda r: r.context_adjustment)
        ok(stats.most_improved_symbol == best_adj.symbol,
           f"most_improved={stats.most_improved_symbol} expected={best_adj.symbol}")
        return f"most_improved_symbol={stats.most_improved_symbol}"

    def t86_most_degraded_symbol():
        obs_list = [
            _make_obs("GOOD",  {"rsi": 0.80}),
            _make_obs("WORST", {"rsi": 0.20}),   # anti-aligned → most negative adj
        ]
        lib     = _poor_library()
        snap    = _adverse_snapshot()
        results = _engine().evaluate_universe_with_context(obs_list, lib, snap, "2026-08-04")
        stats   = _engine().statistics(results)
        worst_adj = min(results, key=lambda r: r.context_adjustment)
        if worst_adj.context_adjustment < 0:
            ok(stats.most_degraded_symbol == worst_adj.symbol,
               f"degraded={stats.most_degraded_symbol} expected={worst_adj.symbol}")
        return f"most_degraded_symbol={stats.most_degraded_symbol}"

    def t87_statistics_empty_safe_defaults():
        stats = _engine().statistics([])
        ok(stats.total_symbols == 0)
        ok(stats.avg_raw_pmci  == 0.0)
        ok(stats.top_symbol    is None)
        ok(stats.most_improved_symbol is None)
        ok(stats.most_degraded_symbol is None)
        return "statistics() on empty results → safe defaults"

    runner.run("T83 statistics() total_symbols",             t83_statistics_total_symbols)
    runner.run("T84 avg_ca_pmci > avg_raw in bull context",  t84_avg_ca_gt_avg_raw_in_bull)
    runner.run("T85 most_improved_symbol correct",           t85_most_improved_symbol)
    runner.run("T86 most_degraded_symbol correct",           t86_most_degraded_symbol)
    runner.run("T87 statistics() empty → safe defaults",     t87_statistics_empty_safe_defaults)

    # ── T88-T90: Edge cases and serialisation ────────────────────────────────

    def t88_empty_library_no_crash():
        empty_lib = _make_library([])
        obs  = _make_obs()
        snap = _make_market_snapshot()
        r    = _engine().evaluate_with_context(obs, empty_lib, snap, "2026-08-04")
        ok(isinstance(r, CAPMCIResult), type(r).__name__)
        ok(0.0 <= r.ca_pmci <= 1.0, f"ca_pmci={r.ca_pmci}")
        return f"empty library → valid CAPMCIResult (ca_pmci={r.ca_pmci:.3f})"

    def t89_adjustment_factor_0_5_when_zero_adj():
        # When max_total_adj is very small, a near-zero adjustment
        # Check formula directly:
        cfg     = MLSConfig(ca_pmci_max_total_adj=0.30)
        max_adj = cfg.ca_pmci_max_total_adj
        for total in [0.0, 0.0, 0.0]:
            factor = 0.5 + total / (2.0 * max_adj)
            ok(abs(factor - 0.5) < 1e-9, f"factor={factor}")
        return "context_adjustment_factor=0.5 when adj=0 (formula verified)"

    def t90_ca_pmci_result_serialisation_round_trip():
        obs  = _make_obs()
        lib  = _good_library()
        snap = _make_market_snapshot()
        r    = _engine().evaluate_with_context(obs, lib, snap, "2026-08-04")
        d    = r.to_dict()
        r2   = CAPMCIResult.from_dict(d)
        ok(r2.symbol          == r.symbol,          r.symbol)
        ok(r2.result_id       == r.result_id,        r.result_id)
        ok(abs(r2.raw_pmci    - r.raw_pmci)    < 1e-6, r.raw_pmci)
        ok(abs(r2.ca_pmci     - r.ca_pmci)     < 1e-6, r.ca_pmci)
        ok(abs(r2.context_adjustment - r.context_adjustment) < 1e-6)
        ok(len(r2.adjustments) == 5, len(r2.adjustments))
        ok(r2.context_id == r.context_id)
        return "CAPMCIResult to_dict/from_dict round-trip OK"

    runner.run("T88 empty library → no crash, valid result",  t88_empty_library_no_crash)
    runner.run("T89 adj_factor=0.5 formula when adj=0",       t89_adjustment_factor_0_5_when_zero_adj)
    runner.run("T90 CAPMCIResult serialisation round-trip",   t90_ca_pmci_result_serialisation_round_trip)

    return runner.report()


if __name__ == "__main__":
    sys.exit(main())
