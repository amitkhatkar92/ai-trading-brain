"""
test_cds_engine.py — MLS Phase 5A.1: Contextual DNA Score Engine.

90-test suite.  Run with:
    .venv\\Scripts\\python.exe test_cds_engine.py

Uses the same minimal test framework as Phases 3, 4, 5, 5A, 5B.
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

from market_learning import (
    CDSEngine,
    CDSError,
    CDSInputError,
    CDSLibraryResult,
    ContextStabilityLabel,
    ContextualDNAScore,
    DNAContextContribution,
    DNAContextEvidence,
    DNAContextHistory,
    DNAContextProfile,
    DNAContextSimilarity,
    DNAContextStatistics,
    DNARelevance,
    MCIEngine,
    MLSConfig,
    ConsensusDNA,
    ConsensusLevel,
    ConsensusLibrary,
    ConsensusState,
    ConsensusStatistics,
    MarketContext,
    SeparationDirection,
)
from market_learning.mcie_models import ContextComponent
from market_learning.cds_engine import (
    _clamp,
    _mean,
    _make_cds_id,
    _get_ctx_score,
    _score_regime_match,
    _score_volatility_match,
    _score_sector_match,
    _score_breadth_match,
    _score_liquidity_match,
    _score_institutional_match,
    _score_global_match,
    _score_freshness,
    _score_stability_match,
    _cosine_similarity,
    _classify_relevance,
    _classify_stability,
)


# ═══════════════════════════════════════════════════════════════════════════════
# Test framework
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
# Fixtures
# ═══════════════════════════════════════════════════════════════════════════════

_TEST_CFG = MLSConfig(min_universe_size=1, dna_min_group_size=2)

_BULL_COMP_SCORES = {
    "regime_context":        0.90,
    "volatility_context":    0.80,
    "liquidity_context":     0.85,
    "participation_context": 0.80,
    "sector_context":        0.75,
    "institutional_context": 0.80,
    "global_context":        0.75,
    "risk_context":          0.65,
}

_ADVERSE_COMP_SCORES = {
    "regime_context":        0.20,
    "volatility_context":    0.10,
    "liquidity_context":     0.25,
    "participation_context": 0.20,
    "sector_context":        0.25,
    "institutional_context": 0.20,
    "global_context":        0.25,
    "risk_context":          0.15,
}

_ORDERED_COMP_NAMES = (
    "global_context",
    "institutional_context",
    "liquidity_context",
    "participation_context",
    "regime_context",
    "risk_context",
    "sector_context",
    "volatility_context",
)


def _make_context(
    regime: str = "bull_trend",
    context_score: float = 0.75,
    stability: float = 0.97,
    comp_scores: Optional[Dict[str, float]] = None,
    context_id: Optional[str] = None,
    date: str = "2026-08-04",
) -> MarketContext:
    scores = dict(_BULL_COMP_SCORES)
    if comp_scores:
        scores.update(comp_scores)
    comps = [
        ContextComponent(
            name=n,
            score=scores.get(n, 0.5),
            weight=0.125,
            weighted_score=round(scores.get(n, 0.5) * 0.125, 6),
            confidence=0.80,
            explanation=f"{n}={scores.get(n, 0.5):.2f}",
            evidence={},
        )
        for n in sorted(scores.keys())
    ]
    cid = context_id or f"MCE-test{int(context_score * 100):03d}"
    return MarketContext(
        context_id=cid,
        evaluation_date=date,
        evaluation_time=f"{date}T09:00:00",
        regime=regime,
        context_score=context_score,
        confidence=0.80,
        stability=stability,
        freshness=1.0,
        components=comps,
        summary=f"Test {regime} ctx={context_score:.2f}",
        raw_inputs={},
    )


def _bull_context() -> MarketContext:
    return _make_context(
        "bull_trend", 0.82, 0.97, _BULL_COMP_SCORES, "MCE-bulltst1",
    )


def _adverse_context() -> MarketContext:
    return _make_context(
        "volatile", 0.22, 0.40, _ADVERSE_COMP_SCORES, "MCE-adverst1",
    )


def _make_dna(
    feature_name: str = "rsi",
    direction: SeparationDirection = SeparationDirection.WINNERS_HIGHER,
    state: ConsensusState = ConsensusState.INSTITUTIONAL,
    regime_consistency: float = 0.70,
    temporal_stability: float = 0.80,
    sector_consistency: float = 0.65,
    replication_frequency: float = 0.80,
    feature_persistence: float = 0.75,
    evidence_count: int = 15,
    last_seen: str = "2026-08-03",
    regime_counts: Optional[Dict[str, int]] = None,
) -> ConsensusDNA:
    rc = regime_counts or {"bull_trend": 8, "range_market": 4, "bear_market": 2, "volatile": 1}
    cid = "CON-" + hashlib.sha256(feature_name.encode()).hexdigest()[:8]
    return ConsensusDNA(
        consensus_id=cid,
        feature_name=feature_name,
        direction=direction,
        consensus_state=state,
        consensus_score=0.75,
        replication_frequency=replication_frequency,
        evidence_count=evidence_count,
        temporal_stability=temporal_stability,
        regime_consistency=regime_consistency,
        sector_consistency=sector_consistency,
        confidence_trend=0.05,
        feature_persistence=feature_persistence,
        first_seen="2026-01-01",
        last_seen=last_seen,
        all_observations=[],
        regime_counts=rc,
        level=ConsensusLevel.MASTER,
    )


def _strong_dna() -> ConsensusDNA:
    """Regime-agnostic, high-evidence DNA — expected HIGHLY_RELEVANT in bull context."""
    return _make_dna(
        feature_name="mom_5d",
        regime_consistency=0.85,
        temporal_stability=0.95,
        sector_consistency=0.90,
        replication_frequency=0.90,
        feature_persistence=0.90,
        evidence_count=50,
        last_seen="2026-08-04",  # today
    )


def _make_library(*dnas: ConsensusDNA) -> ConsensusLibrary:
    institutional = [d for d in dnas if d.consensus_state == ConsensusState.INSTITUTIONAL]
    return ConsensusLibrary(
        library_id="MLS-LIB-20260804",
        as_of_date="2026-08-04",
        all_consensus=list(dnas),
        master_consensus=institutional,
        drift_reports=[],
        statistics=ConsensusStatistics(
            as_of_date="2026-08-04",
            total_consensus_dna=len(dnas),
            institutional_count=len(institutional),
            weakening_count=0,
            drifting_count=0,
            retired_count=0,
            avg_consensus_score=0.75,
            avg_replication_freq=0.75,
            top_institutional_feature=dnas[0].feature_name if dnas else None,
        ),
    )


def _engine(cfg=None) -> CDSEngine:
    return CDSEngine(config=cfg or _TEST_CFG)


# ═══════════════════════════════════════════════════════════════════════════════
# Tests
# ═══════════════════════════════════════════════════════════════════════════════

def _run_all(runner: TestRunner) -> None:

    # ── Group 1: MLSConfig Phase 5A.1 defaults (T01-T05) ─────────────────────

    def t01():
        ok(_TEST_CFG.cds_w_regime == 0.20, "cds_w_regime")
        return f"cds_w_regime={_TEST_CFG.cds_w_regime}"

    def t02():
        ok(_TEST_CFG.cds_w_sector == 0.15, "sector")
        ok(_TEST_CFG.cds_w_volatility == 0.15, "volatility")
        ok(_TEST_CFG.cds_w_breadth == 0.12, "breadth")
        return "sector=0.15 vol=0.15 breadth=0.12"

    def t03():
        total = sum([
            _TEST_CFG.cds_w_regime, _TEST_CFG.cds_w_sector,
            _TEST_CFG.cds_w_volatility, _TEST_CFG.cds_w_breadth,
            _TEST_CFG.cds_w_liquidity, _TEST_CFG.cds_w_institutional,
            _TEST_CFG.cds_w_global, _TEST_CFG.cds_w_freshness,
            _TEST_CFG.cds_w_stability, _TEST_CFG.cds_w_historical,
        ])
        ok(abs(total - 1.0) < 1e-9, f"weights sum={total}")
        return f"sum={total:.10f}"

    def t04():
        ok(_TEST_CFG.cds_highly_relevant == 0.75, "highly_relevant")
        ok(_TEST_CFG.cds_relevant == 0.55, "relevant")
        ok(_TEST_CFG.cds_neutral == 0.40, "neutral")
        ok(_TEST_CFG.cds_weak == 0.25, "weak")
        ok(_TEST_CFG.cds_irrelevant == 0.10, "irrelevant")
        return "all 5 relevance thresholds correct"

    def t05():
        ok(_TEST_CFG.cds_stable_threshold == 0.05, "stable_threshold")
        ok(_TEST_CFG.cds_max_history_size == 200, "max_history_size")
        ok(_TEST_CFG.cds_top_analogues == 5, "top_analogues")
        ok(_TEST_CFG.cds_freshness_days == 30, "freshness_days")
        return "stability/history/freshness defaults correct"

    runner.run("T01 — config.cds_w_regime default", t01)
    runner.run("T02 — config sector/volatility/breadth defaults", t02)
    runner.run("T03 — all 10 CDS weights sum to 1.0", t03)
    runner.run("T04 — relevance threshold defaults", t04)
    runner.run("T05 — stability/history/freshness defaults", t05)

    # ── Group 2: CDSEngine instantiation (T06-T08) ────────────────────────────

    def t06():
        e = CDSEngine()
        ok(isinstance(e._cfg, MLSConfig), "MLSConfig stored")
        ok(len(e._context_history) == 0, "empty history")
        return "default init OK"

    def t07():
        cfg = MLSConfig(cds_w_regime=0.25, cds_w_historical=0.0)
        e = CDSEngine(config=cfg)
        ok(e._cfg.cds_w_regime == 0.25, "custom weight stored")
        return "custom config stored"

    def t08():
        mci = MCIEngine()
        e = CDSEngine(mci_engine=mci)
        ok(e._mci is mci, "MCIEngine preserved")
        return "MCIEngine injection preserved"

    runner.run("T06 — CDSEngine default instantiation", t06)
    runner.run("T07 — CDSEngine custom config", t07)
    runner.run("T08 — CDSEngine MCIEngine injection", t08)

    # ── Group 3: ContextualDNAScore structure (T09-T13) ───────────────────────

    def _default_score():
        return _engine().evaluate_dna(_make_dna(), _bull_context(), evaluation_date="2026-08-04")

    def t09():
        s = _default_score()
        ok(s.evaluation_id.startswith("CDS-"), f"got {s.evaluation_id}")
        return f"id={s.evaluation_id}"

    def t10():
        s = _default_score()
        ok(len(s.contributions) == 10, f"got {len(s.contributions)}")
        return "exactly 10 contributions"

    def t11():
        s = _default_score()
        ok(0.0 <= s.cds <= 1.0, f"cds={s.cds}")
        return f"cds={s.cds:.4f}"

    def t12():
        s = _default_score()
        ok(len(s.supporting_dimensions) + len(s.conflicting_dimensions) == 10,
           f"support={len(s.supporting_dimensions)} conflict={len(s.conflicting_dimensions)}")
        return f"support={len(s.supporting_dimensions)} conflict={len(s.conflicting_dimensions)}"

    def t13():
        s = _default_score()
        ok(len(s.explanation) > 0, "explanation empty")
        ok("rsi" in s.explanation, "feature_name in explanation")
        return f"explanation contains 'rsi'"

    runner.run("T09 — evaluation_id starts with CDS-", t09)
    runner.run("T10 — exactly 10 contributions", t10)
    runner.run("T11 — cds in [0, 1]", t11)
    runner.run("T12 — supporting + conflicting == 10", t12)
    runner.run("T13 — explanation contains feature_name", t13)

    # ── Group 4: DNAContextContribution structure (T14-T18) ───────────────────

    _DIM_NAMES = {
        "regime_match", "volatility_match", "sector_match", "breadth_match",
        "liquidity_match", "institutional_match", "global_match",
        "freshness_match", "stability_match", "historical_match",
    }

    def t14():
        s = _default_score()
        names = {c.name for c in s.contributions}
        ok(names == _DIM_NAMES, f"missing={_DIM_NAMES - names}")
        return "all 10 dimension names present"

    def t15():
        s = _default_score()
        for c in s.contributions:
            ok(0.0 <= c.score <= 1.0, f"{c.name}.score={c.score}")
        return "all scores in [0, 1]"

    def t16():
        s = _default_score()
        for c in s.contributions:
            expected = round(c.score * c.weight, 6)
            ok(abs(c.weighted_score - expected) < 1e-5,
               f"{c.name}: {c.weighted_score} != {expected}")
        return "weighted_score == score * weight for all"

    def t17():
        s = _default_score()
        for c in s.contributions:
            ok(c.supporting == (c.score >= 0.50),
               f"{c.name}: supporting={c.supporting} but score={c.score}")
        return "supporting == (score >= 0.50)"

    def t18():
        s = _default_score()
        for c in s.contributions:
            d = c.to_dict()
            c2 = DNAContextContribution.from_dict(d)
            ok(c2.name == c.name, "name")
            ok(abs(c2.score - c.score) < 1e-6, "score")
            ok(c2.supporting == c.supporting, "supporting")
        return "to_dict/from_dict round-trip for all contributions"

    runner.run("T14 — all 10 dimension names present", t14)
    runner.run("T15 — all contribution scores in [0, 1]", t15)
    runner.run("T16 — weighted_score == score × weight", t16)
    runner.run("T17 — supporting == (score >= 0.50)", t17)
    runner.run("T18 — DNAContextContribution round-trip", t18)

    # ── Group 5: DNAContextEvidence structure (T19-T23) ───────────────────────

    def t19():
        s = _default_score()
        ok(s.evidence.evaluation_id.startswith("CDS-"), s.evidence.evaluation_id)
        return f"evidence.evaluation_id={s.evidence.evaluation_id}"

    def t20():
        dna = _make_dna("volume_ratio", SeparationDirection.WINNERS_LOWER)
        s = _engine().evaluate_dna(dna, _bull_context(), evaluation_date="2026-08-04")
        ok(s.evidence.dna_id == dna.consensus_id, "dna_id mismatch")
        ok(s.evidence.feature_name == "volume_ratio", "feature_name")
        ok(s.evidence.direction == SeparationDirection.WINNERS_LOWER.value, "direction")
        return "dna_id/feature_name/direction match"

    def t21():
        ctx = _bull_context()
        s = _engine().evaluate_dna(_make_dna(), ctx, evaluation_date="2026-08-04")
        ok(s.evidence.regime_at_eval == ctx.regime, f"regime={s.evidence.regime_at_eval}")
        return f"regime_at_eval={s.evidence.regime_at_eval}"

    def t22():
        ctx = _bull_context()
        s = _engine().evaluate_dna(_make_dna(), ctx, evaluation_date="2026-08-04")
        ok(abs(s.evidence.context_score_at_eval - ctx.context_score) < 1e-6,
           f"{s.evidence.context_score_at_eval} != {ctx.context_score}")
        return f"context_score_at_eval={s.evidence.context_score_at_eval:.4f}"

    def t23():
        s = _default_score()
        ev = s.evidence
        d = ev.to_dict()
        ev2 = DNAContextEvidence.from_dict(d)
        ok(ev2.evaluation_id == ev.evaluation_id, "evaluation_id")
        ok(ev2.dna_id == ev.dna_id, "dna_id")
        ok(ev2.dna_evidence_count == ev.dna_evidence_count, "evidence_count")
        return "DNAContextEvidence round-trip"

    runner.run("T19 — evidence.evaluation_id starts with CDS-", t19)
    runner.run("T20 — evidence dna_id/feature_name/direction match", t20)
    runner.run("T21 — evidence.regime_at_eval matches context", t21)
    runner.run("T22 — evidence.context_score_at_eval matches context", t22)
    runner.run("T23 — DNAContextEvidence to_dict/from_dict round-trip", t23)

    # ── Group 6: regime_match dimension (T24-T28) ─────────────────────────────

    def t24():
        # Bull DNA (8/15 = 0.533 observations in bull_trend) in bull regime
        score = _score_regime_match(0.70, 8/15, 0.90)
        ok(score > 0.50, f"bull DNA in bull regime should be > 0.50, got {score}")
        return f"score={score:.4f}"

    def t25():
        # Bull DNA has 1/15 = 0.067 observations in volatile regime
        score = _score_regime_match(0.70, 1/15, 0.20)
        ok(score < 0.50, f"bull DNA in volatile regime should be < 0.50, got {score}")
        return f"score={score:.4f}"

    def t26():
        # Regime-agnostic DNA (consistency=0.85) in clear bull regime (ctx=0.90)
        score = _score_regime_match(0.85, 0.1, 0.90)
        ok(score > 0.70, f"regime-agnostic in clear regime should be > 0.70, got {score}")
        return f"score={score:.4f} (regime-agnostic formula)"

    def t27():
        for rc, frac, ctx in [
            (0.70, 8/15, 0.90), (0.85, 0.5, 0.90),
            (0.50, 0.0, 0.20), (0.90, 1.0, 0.50),
        ]:
            s = _score_regime_match(rc, frac, ctx)
            ok(0.0 <= s <= 1.0, f"out of range: {s}")
        return "regime_match always in [0, 1]"

    def t28():
        s = _default_score()
        regime_c = next(c for c in s.contributions if c.name == "regime_match")
        ev = regime_c.evidence
        ok("regime_context_score" in ev, "missing regime_context_score")
        ok("dna_regime_counts" in ev, "missing dna_regime_counts")
        ok("dna_regime_consistency" in ev, "missing dna_regime_consistency")
        return f"regime evidence keys present"

    runner.run("T24 — regime_match: bull DNA in bull regime > 0.50", t24)
    runner.run("T25 — regime_match: bull DNA in volatile regime < 0.50", t25)
    runner.run("T26 — regime_match: regime-agnostic DNA scores high", t26)
    runner.run("T27 — regime_match always in [0, 1]", t27)
    runner.run("T28 — regime_match evidence has required keys", t28)

    # ── Group 7: volatility_match dimension (T29-T33) ─────────────────────────

    def t29():
        # Low vol context (0.80) + high temporal_stability (0.80)
        score = _score_volatility_match(0.80, 0.80)
        ok(score > 0.60, f"expected > 0.60, got {score}")
        return f"score={score:.4f}"

    def t30():
        # High vol (0.10) + low temporal_stability (0.30)
        score = _score_volatility_match(0.30, 0.10)
        ok(score < 0.30, f"expected < 0.30, got {score}")
        return f"score={score:.4f}"

    def t31():
        for ts, vx in [(0.0, 0.0), (0.5, 0.5), (1.0, 1.0), (0.8, 0.1)]:
            s = _score_volatility_match(ts, vx)
            ok(0.0 <= s <= 1.0, f"out of range: {s}")
        return "volatility_match always in [0, 1]"

    def t32():
        # High temporal_stability + adverse vol → moderate (not necessarily < 0.5)
        score_high_stab = _score_volatility_match(0.95, 0.10)
        score_low_stab  = _score_volatility_match(0.20, 0.10)
        ok(score_high_stab > score_low_stab,
           f"high stability should do better: {score_high_stab} <= {score_low_stab}")
        return f"high_stab={score_high_stab:.3f} > low_stab={score_low_stab:.3f}"

    def t33():
        s = _default_score()
        vol_c = next(c for c in s.contributions if c.name == "volatility_match")
        ok("volatility_context_score" in vol_c.evidence, "missing volatility_context_score")
        ok("dna_temporal_stability" in vol_c.evidence, "missing dna_temporal_stability")
        return "volatility_match evidence keys present"

    runner.run("T29 — volatility_match: low vol + stable DNA > 0.60", t29)
    runner.run("T30 — volatility_match: high vol + unstable DNA < 0.30", t30)
    runner.run("T31 — volatility_match always in [0, 1]", t31)
    runner.run("T32 — volatility_match: high stab > low stab in same vol", t32)
    runner.run("T33 — volatility_match evidence keys present", t33)

    # ── Group 8: sector_match dimension (T34-T38) ─────────────────────────────

    def t34():
        # High sector consistency + good sector context
        score = _score_sector_match(0.90, 0.75)
        ok(score > 0.60, f"expected > 0.60, got {score}")
        return f"score={score:.4f}"

    def t35():
        # Low sector consistency + poor sector context
        score = _score_sector_match(0.30, 0.25)
        ok(score < 0.50, f"expected < 0.50, got {score}")
        return f"score={score:.4f}"

    def t36():
        for sc, sx in [(0.0, 0.0), (0.5, 0.5), (1.0, 1.0), (0.9, 0.1)]:
            s = _score_sector_match(sc, sx)
            ok(0.0 <= s <= 1.0, f"out of range: {s}")
        return "sector_match always in [0, 1]"

    def t37():
        bull_s = _score_sector_match(0.65, 0.75)    # bull context sector_ctx=0.75
        adv_s  = _score_sector_match(0.65, 0.25)    # adverse context sector_ctx=0.25
        ok(bull_s > adv_s, f"bull={bull_s} <= adverse={adv_s}")
        return f"bull={bull_s:.3f} > adverse={adv_s:.3f}"

    def t38():
        s = _default_score()
        sec_c = next(c for c in s.contributions if c.name == "sector_match")
        ok("sector_context_score" in sec_c.evidence, "missing sector_context_score")
        ok("dna_sector_consistency" in sec_c.evidence, "missing dna_sector_consistency")
        return "sector_match evidence keys present"

    runner.run("T34 — sector_match: high consistency + good ctx > 0.60", t34)
    runner.run("T35 — sector_match: poor ctx → score < 0.50", t35)
    runner.run("T36 — sector_match always in [0, 1]", t36)
    runner.run("T37 — sector_match: bull sector > adverse sector", t37)
    runner.run("T38 — sector_match evidence keys present", t38)

    # ── Group 9: breadth_match dimension (T39-T43) ────────────────────────────

    def t39():
        # High persistence + high breadth context
        score = _score_breadth_match(0.90, 0.80)
        ok(score > 0.60, f"expected > 0.60, got {score}")
        return f"score={score:.4f}"

    def t40():
        # Low persistence + low breadth context
        score = _score_breadth_match(0.20, 0.20)
        ok(score < 0.35, f"expected < 0.35, got {score}")
        return f"score={score:.4f}"

    def t41():
        for fp, bx in [(0.0, 0.0), (0.5, 0.5), (1.0, 1.0)]:
            s = _score_breadth_match(fp, bx)
            ok(0.0 <= s <= 1.0, f"out of range: {s}")
        return "breadth_match always in [0, 1]"

    def t42():
        bull_s = _score_breadth_match(0.75, 0.80)
        adv_s  = _score_breadth_match(0.75, 0.20)
        ok(bull_s > adv_s, f"bull={bull_s} <= adverse={adv_s}")
        return f"bull={bull_s:.3f} > adverse={adv_s:.3f}"

    def t43():
        s = _default_score()
        br_c = next(c for c in s.contributions if c.name == "breadth_match")
        ok("breadth_context_score" in br_c.evidence, "missing breadth_context_score")
        ok("dna_feature_persistence" in br_c.evidence, "missing dna_feature_persistence")
        return "breadth_match evidence keys present"

    runner.run("T39 — breadth_match: high persistence + high ctx > 0.60", t39)
    runner.run("T40 — breadth_match: low ctx → score < 0.35", t40)
    runner.run("T41 — breadth_match always in [0, 1]", t41)
    runner.run("T42 — breadth_match: bull > adverse", t42)
    runner.run("T43 — breadth_match evidence keys present", t43)

    # ── Group 10: liquidity_match dimension (T44-T48) ─────────────────────────

    def t44():
        # High evidence_count + good liquidity context
        score = _score_liquidity_match(50, 0.85)
        ok(score > 0.60, f"expected > 0.60, got {score}")
        return f"score={score:.4f}"

    def t45():
        # Low evidence_count + poor liquidity
        score = _score_liquidity_match(2, 0.20)
        ok(score < 0.25, f"expected < 0.25, got {score}")
        return f"score={score:.4f}"

    def t46():
        for ec, lx in [(0, 0.0), (25, 0.5), (50, 1.0)]:
            s = _score_liquidity_match(ec, lx)
            ok(0.0 <= s <= 1.0, f"out of range: {s}")
        return "liquidity_match always in [0, 1]"

    def t47():
        # evidence_count=50 → evidence_proxy = clamp(50/50) = 1.0
        score_50 = _score_liquidity_match(50, 0.70)
        score_51 = _score_liquidity_match(51, 0.70)
        ok(abs(score_50 - score_51) < 1e-9, "saturated at 50 obs")
        # evidence_proxy at 50 = 1.0 exactly
        expected = _clamp(1.0 * 0.30 + 0.70 * 0.70)
        ok(abs(score_50 - expected) < 1e-9, f"formula: {score_50} != {expected}")
        return f"evidence_proxy saturates at 50 obs, score={score_50:.4f}"

    def t48():
        s = _default_score()
        liq_c = next(c for c in s.contributions if c.name == "liquidity_match")
        ok("liquidity_context_score" in liq_c.evidence, "missing liquidity_context_score")
        ok("dna_evidence_count" in liq_c.evidence, "missing dna_evidence_count")
        ok("evidence_proxy" in liq_c.evidence, "missing evidence_proxy")
        return "liquidity_match evidence keys present"

    runner.run("T44 — liquidity_match: high evidence + good ctx > 0.60", t44)
    runner.run("T45 — liquidity_match: low evidence + poor ctx < 0.25", t45)
    runner.run("T46 — liquidity_match always in [0, 1]", t46)
    runner.run("T47 — liquidity_match evidence_proxy saturates at 50 obs", t47)
    runner.run("T48 — liquidity_match evidence keys present", t48)

    # ── Group 11: institutional_match dimension (T49-T53) ─────────────────────

    def t49():
        score = _score_institutional_match(0.80, 0.80)
        ok(score > 0.60, f"expected > 0.60, got {score}")
        return f"score={score:.4f}"

    def t50():
        score = _score_institutional_match(0.20, 0.20)
        ok(score < 0.30, f"expected < 0.30, got {score}")
        return f"score={score:.4f}"

    def t51():
        for rc, ix in [(0.0, 0.0), (0.5, 0.5), (1.0, 1.0)]:
            s = _score_institutional_match(rc, ix)
            ok(0.0 <= s <= 1.0, f"out of range: {s}")
        return "institutional_match always in [0, 1]"

    def t52():
        bull_s = _score_institutional_match(0.70, 0.80)
        adv_s  = _score_institutional_match(0.70, 0.20)
        ok(bull_s > adv_s, f"bull={bull_s} <= adverse={adv_s}")
        return f"bull={bull_s:.3f} > adverse={adv_s:.3f}"

    def t53():
        s = _default_score()
        ic = next(c for c in s.contributions if c.name == "institutional_match")
        ok("institutional_context_score" in ic.evidence)
        ok("dna_regime_consistency" in ic.evidence)
        return "institutional_match evidence keys present"

    runner.run("T49 — institutional_match: high consistency + good ctx > 0.60", t49)
    runner.run("T50 — institutional_match: low ctx < 0.30", t50)
    runner.run("T51 — institutional_match always in [0, 1]", t51)
    runner.run("T52 — institutional_match: bull > adverse", t52)
    runner.run("T53 — institutional_match evidence keys present", t53)

    # ── Group 12: global_match dimension (T54-T58) ────────────────────────────

    def t54():
        score = _score_global_match(0.95, 0.75)
        ok(score > 0.60, f"expected > 0.60, got {score}")
        return f"score={score:.4f}"

    def t55():
        score = _score_global_match(0.20, 0.25)
        ok(score < 0.30, f"expected < 0.30, got {score}")
        return f"score={score:.4f}"

    def t56():
        for ts, gx in [(0.0, 0.0), (0.5, 0.5), (1.0, 1.0)]:
            s = _score_global_match(ts, gx)
            ok(0.0 <= s <= 1.0, f"out of range: {s}")
        return "global_match always in [0, 1]"

    def t57():
        bull_s = _score_global_match(0.80, 0.75)
        adv_s  = _score_global_match(0.80, 0.25)
        ok(bull_s > adv_s, f"bull={bull_s} <= adverse={adv_s}")
        return f"bull={bull_s:.3f} > adverse={adv_s:.3f}"

    def t58():
        s = _default_score()
        gc = next(c for c in s.contributions if c.name == "global_match")
        ok("global_context_score" in gc.evidence)
        ok("dna_temporal_stability" in gc.evidence)
        return "global_match evidence keys present"

    runner.run("T54 — global_match: high stability + good global > 0.60", t54)
    runner.run("T55 — global_match: adverse global < 0.30", t55)
    runner.run("T56 — global_match always in [0, 1]", t56)
    runner.run("T57 — global_match: bull > adverse", t57)
    runner.run("T58 — global_match evidence keys present", t58)

    # ── Group 13: freshness_match dimension (T59-T63) ─────────────────────────

    def t59():
        score = _score_freshness("2026-08-03", "2026-08-04", 30)
        ok(score >= 0.96, f"1 day old should be >= 0.96, got {score}")
        return f"score={score:.4f} (1 day old)"

    def t60():
        score = _score_freshness("2026-08-04", "2026-08-04", 30)
        ok(score == 1.0, f"today should be 1.0, got {score}")
        return f"score={score:.4f} (today)"

    def t61():
        score = _score_freshness("2026-07-05", "2026-08-04", 30)
        ok(score <= 0.0, f"30+ days old should be <= 0.0, got {score}")
        return f"score={score:.4f} (30 days old)"

    def t62():
        for ls, ed in [("2026-08-04", "2026-08-04"), ("2025-01-01", "2026-08-04")]:
            s = _score_freshness(ls, ed, 30)
            ok(0.0 <= s <= 1.0, f"out of range: {s}")
        return "freshness_match always in [0, 1]"

    def t63():
        s = _default_score()
        fc = next(c for c in s.contributions if c.name == "freshness_match")
        ok("age_days" in fc.evidence, "missing age_days")
        ok("freshness_window" in fc.evidence, "missing freshness_window")
        ok("dna_last_seen" in fc.evidence, "missing dna_last_seen")
        return "freshness_match evidence keys present"

    runner.run("T59 — freshness_match: yesterday DNA >= 0.96", t59)
    runner.run("T60 — freshness_match: today DNA == 1.0", t60)
    runner.run("T61 — freshness_match: 30+ day old DNA == 0.0", t61)
    runner.run("T62 — freshness_match always in [0, 1]", t62)
    runner.run("T63 — freshness_match evidence keys present", t63)

    # ── Group 14: stability_match dimension (T64-T68) ─────────────────────────

    def t64():
        # High replication + high context stability
        score = _score_stability_match(0.90, 0.95)
        ok(score > 0.70, f"expected > 0.70, got {score}")
        return f"score={score:.4f}"

    def t65():
        # Low replication + low context stability
        score = _score_stability_match(0.20, 0.40)
        ok(score < 0.40, f"expected < 0.40, got {score}")
        return f"score={score:.4f}"

    def t66():
        for rf, cs in [(0.0, 0.0), (0.5, 0.5), (1.0, 1.0)]:
            s = _score_stability_match(rf, cs)
            ok(0.0 <= s <= 1.0, f"out of range: {s}")
        return "stability_match always in [0, 1]"

    def t67():
        # stability=0.97 → delta=0.03 < 0.05 → STABLE
        label = _classify_stability(0.97, _TEST_CFG)
        ok(label == ContextStabilityLabel.STABLE, f"got {label}")
        # stability=0.40 → delta=0.60 >= 0.35 → DRIFTING
        label2 = _classify_stability(0.40, _TEST_CFG)
        ok(label2 == ContextStabilityLabel.DRIFTING, f"got {label2}")
        return f"STABLE (0.97) and DRIFTING (0.40) correctly classified"

    def t68():
        s = _default_score()
        sc = next(c for c in s.contributions if c.name == "stability_match")
        ok("context_stability" in sc.evidence)
        ok("dna_replication_freq" in sc.evidence)
        return "stability_match evidence keys present"

    runner.run("T64 — stability_match: high replication + stable ctx > 0.70", t64)
    runner.run("T65 — stability_match: low replication + unstable ctx < 0.40", t65)
    runner.run("T66 — stability_match always in [0, 1]", t66)
    runner.run("T67 — context_stability_label: STABLE=0.97, DRIFTING=0.40", t67)
    runner.run("T68 — stability_match evidence keys present", t68)

    # ── Group 15: historical_match dimension (T69-T73) ────────────────────────

    def t69():
        # Fresh engine — no history → historical_similarity_score == 0.5
        e = _engine()
        s = e.evaluate_dna(_make_dna(), _bull_context(), evaluation_date="2026-08-04")
        ok(abs(s.historical_similarity_score - 0.5) < 1e-6,
           f"expected 0.5, got {s.historical_similarity_score}")
        return f"historical_score={s.historical_similarity_score}"

    def t70():
        # Store one historical context, then evaluate similar context → sim > 0.5
        e = _engine()
        ctx_a = _make_context(
            "bull_trend", 0.80, 0.95, _BULL_COMP_SCORES, "MCE-hist001", "2026-07-30",
        )
        ctx_b = _make_context(
            "bull_trend", 0.82, 0.97, _BULL_COMP_SCORES, "MCE-hist002", "2026-08-04",
        )
        e.evaluate_dna(_make_dna(), ctx_a, evaluation_date="2026-07-30")
        s = e.evaluate_dna(_make_dna(), ctx_b, evaluation_date="2026-08-04")
        ok(s.historical_similarity_score > 0.5,
           f"expected > 0.5, got {s.historical_similarity_score}")
        return f"historical_score={s.historical_similarity_score:.4f} (after storing similar ctx)"

    def t71():
        # Fresh engine — historical_matches() returns [] when < 2 entries
        e = _engine()
        matches = e.historical_matches(_bull_context())
        ok(matches == [], f"expected [], got {len(matches)} items")
        return "historical_matches() = [] for empty history"

    def t72():
        e = _engine()
        ctx_a = _make_context(
            "bull_trend", 0.80, 0.95, _BULL_COMP_SCORES, "MCE-anal001", "2026-07-30",
        )
        ctx_b = _make_context(
            "bull_trend", 0.82, 0.97, _BULL_COMP_SCORES, "MCE-anal002", "2026-08-04",
        )
        e.evaluate_dna(_make_dna(), ctx_a, evaluation_date="2026-07-30")
        matches = e.historical_matches(ctx_b)
        ok(len(matches) > 0, "expected at least 1 match")
        ok(matches[0].analogue_id.startswith("MCE-"), f"got {matches[0].analogue_id}")
        return f"analogue_id={matches[0].analogue_id}"

    def t73():
        e = _engine()
        ctx_a = _make_context(
            "bull_trend", 0.80, 0.95, _BULL_COMP_SCORES, "MCE-mdim001", "2026-07-30",
        )
        ctx_b = _make_context(
            "bull_trend", 0.82, 0.97, _BULL_COMP_SCORES, "MCE-mdim002", "2026-08-04",
        )
        e.evaluate_dna(_make_dna(), ctx_a, evaluation_date="2026-07-30")
        matches = e.historical_matches(ctx_b)
        ok(len(matches) > 0, "no matches")
        ok(len(matches[0].matched_dimensions) > 0, "expected matched dimensions")
        return f"matched_dimensions={matches[0].matched_dimensions}"

    runner.run("T69 — no history → historical_similarity_score == 0.5", t69)
    runner.run("T70 — similar ctx stored → historical_score > 0.5", t70)
    runner.run("T71 — historical_matches() returns [] for empty history", t71)
    runner.run("T72 — DNAContextSimilarity.analogue_id starts with MCE-", t72)
    runner.run("T73 — DNAContextSimilarity.matched_dimensions populated", t73)

    # ── Group 16: evaluate_dna() full flow (T74-T78) ──────────────────────────

    def t74():
        dna = _make_dna("rsi_14")
        s = _engine().evaluate_dna(dna, _bull_context(), evaluation_date="2026-08-04")
        ok(s.dna_id == dna.consensus_id, f"dna_id mismatch: {s.dna_id}")
        ok(s.feature_name == "rsi_14", f"feature_name: {s.feature_name}")
        return f"dna_id={s.dna_id} feature={s.feature_name}"

    def t75():
        s = _engine().evaluate_dna(_make_dna(), _bull_context(), evaluation_date="2026-08-04")
        ok(0.0 <= s.cds <= 1.0, f"cds={s.cds}")
        ok(0.0 <= s.confidence <= 1.0, f"confidence={s.confidence}")
        return f"cds={s.cds:.4f} confidence={s.confidence:.4f}"

    def t76():
        # Standard DNA in bull context → RELEVANT (cds ≈ 0.73, between 0.55 and 0.75)
        s = _engine().evaluate_dna(_make_dna(), _bull_context(), evaluation_date="2026-08-04")
        ok(s.relevance in (DNARelevance.RELEVANT, DNARelevance.HIGHLY_RELEVANT),
           f"expected RELEVANT/HIGHLY_RELEVANT, got {s.relevance}")
        # Strong DNA → HIGHLY_RELEVANT
        ss = _engine().evaluate_dna(_strong_dna(), _bull_context(), evaluation_date="2026-08-04")
        ok(ss.relevance == DNARelevance.HIGHLY_RELEVANT,
           f"strong DNA expected HIGHLY_RELEVANT, got {ss.relevance} (cds={ss.cds:.3f})")
        return f"standard={s.relevance.value} strong={ss.relevance.value}"

    def t77():
        dna = _make_dna()
        ctx = _bull_context()
        s1 = _engine().evaluate_dna(dna, ctx, evaluation_date="2026-08-04")
        s2 = _engine().evaluate_dna(dna, ctx, evaluation_date="2026-08-04")
        ok(s1.evaluation_id == s2.evaluation_id,
           f"non-deterministic: {s1.evaluation_id} != {s2.evaluation_id}")
        ok(abs(s1.cds - s2.cds) < 1e-9, "cds non-deterministic")
        return f"deterministic id={s1.evaluation_id}"

    def t78():
        # snapshot=None → no crash, uses neutral defaults for snapshot fields
        s = _engine().evaluate_dna(_make_dna(), _bull_context(), snapshot=None,
                                   evaluation_date="2026-08-04")
        ok(isinstance(s, ContextualDNAScore), "wrong type")
        ok(s.evidence.vix_at_eval == 0.0, f"vix={s.evidence.vix_at_eval}")
        ok(s.evidence.fii_net_at_eval == 0.0, f"fii_net={s.evidence.fii_net_at_eval}")
        return "snapshot=None handled correctly"

    runner.run("T74 — evaluate_dna(): dna_id and feature_name match", t74)
    runner.run("T75 — evaluate_dna(): cds and confidence in [0, 1]", t75)
    runner.run("T76 — evaluate_dna(): correct relevance classification", t76)
    runner.run("T77 — evaluate_dna(): deterministic evaluation_id", t77)
    runner.run("T78 — evaluate_dna(): snapshot=None handled gracefully", t78)

    # ── Group 17: evaluate() and evaluate_library() (T79-T83) ─────────────────

    def t79():
        lib = _make_library(_make_dna("rsi"), _make_dna("mom_5d"), _make_dna("volume_ratio"))
        results = _engine().evaluate(lib, _bull_context(), evaluation_date="2026-08-04")
        ok(len(results) == 3, f"expected 3, got {len(results)}")
        return f"evaluate() returned {len(results)} scores"

    def t80():
        lib = _make_library(_make_dna("rsi"), _make_dna("mom_5d"))
        result = _engine().evaluate_library(lib, _bull_context(), evaluation_date="2026-08-04")
        ok(isinstance(result, CDSLibraryResult), "wrong type")
        ok(len(result.scores) == 2, f"expected 2 scores, got {len(result.scores)}")
        ok(isinstance(result.statistics, DNAContextStatistics), "stats type")
        return f"CDSLibraryResult with {len(result.scores)} scores"

    def t81():
        empty_lib = _make_library()
        results = _engine().evaluate(empty_lib, _bull_context())
        ok(results == [], f"expected [], got {results}")
        return "empty library → empty list"

    def t82():
        lib = _make_library(_make_dna("rsi"), _make_dna("mom_5d"), _make_dna("bb_pct"))
        results = _engine().evaluate(lib, _bull_context(), evaluation_date="2026-08-04")
        dates = {r.evaluation_date for r in results}
        ok(dates == {"2026-08-04"}, f"mixed dates: {dates}")
        return "all scores share same evaluation_date"

    def t83():
        lib = _make_library(_make_dna("rsi"), _make_dna("mom_5d"))
        result = _engine().evaluate_library(lib, _bull_context(), evaluation_date="2026-08-04")
        ok(result.statistics.total_dna == 2, f"total_dna={result.statistics.total_dna}")
        ok(result.statistics.library_id == lib.library_id, "library_id mismatch")
        return f"statistics.total_dna={result.statistics.total_dna}"

    runner.run("T79 — evaluate() returns one result per INSTITUTIONAL DNA", t79)
    runner.run("T80 — evaluate_library() returns CDSLibraryResult", t80)
    runner.run("T81 — evaluate() with empty library returns []", t81)
    runner.run("T82 — all scores share same evaluation_date", t82)
    runner.run("T83 — CDSLibraryResult.statistics.total_dna correct", t83)

    # ── Group 18: top/least/statistics (T84-T87) ──────────────────────────────

    def _multi_results():
        dnas = [
            _strong_dna(),                                    # high CDS in bull
            _make_dna("rsi",        last_seen="2026-08-03"),  # standard
            _make_dna("mom_5d_wk",  last_seen="2026-06-01"),  # stale (lower freshness)
            _make_dna("vol_ratio",  evidence_count=1),        # weak evidence
        ]
        lib = _make_library(*dnas)
        e = _engine()
        return e.evaluate(lib, _bull_context(), evaluation_date="2026-08-04"), e

    def t84():
        results, _ = _multi_results()
        top = CDSEngine().top_supported_dna(results, n=2)
        ok(len(top) == 2, f"expected 2, got {len(top)}")
        ok(top[0].cds >= top[1].cds, "not sorted descending")
        return f"top2: {top[0].feature_name}={top[0].cds:.3f}, {top[1].feature_name}={top[1].cds:.3f}"

    def t85():
        results, _ = _multi_results()
        least = CDSEngine().least_supported_dna(results, n=2)
        ok(len(least) == 2, f"expected 2, got {len(least)}")
        ok(least[0].cds <= least[1].cds, "not sorted ascending")
        return f"least2: {least[0].feature_name}={least[0].cds:.3f}"

    def t86():
        results, _ = _multi_results()
        stats = CDSEngine().statistics(results, "2026-08-04", "MLS-LIB-20260804")
        ok(stats.total_dna == 4, f"total_dna={stats.total_dna}")
        ok(stats.total_dna == (
            stats.highly_relevant_count + stats.relevant_count + stats.neutral_count +
            stats.weak_count + stats.irrelevant_count + stats.deprecated_count
        ), "relevance counts don't sum to total_dna")
        return f"relevance distribution sum={stats.total_dna}"

    def t87():
        stats = CDSEngine().statistics([], "2026-08-04", "")
        ok(stats.total_dna == 0, "total_dna")
        ok(stats.top_dna_id is None, "top_dna_id")
        ok(stats.avg_cds == 0.0, "avg_cds")
        return "statistics() on empty list returns safe defaults"

    runner.run("T84 — top_supported_dna() sorted descending", t84)
    runner.run("T85 — least_supported_dna() sorted ascending", t85)
    runner.run("T86 — statistics() relevance counts sum to total_dna", t86)
    runner.run("T87 — statistics() on empty list: safe zero defaults", t87)

    # ── Group 19: edge cases and serialization (T88-T90) ──────────────────────

    def t88():
        s = _default_score()
        d = s.to_dict()
        s2 = ContextualDNAScore.from_dict(d)
        ok(s2.evaluation_id == s.evaluation_id, "evaluation_id")
        ok(s2.dna_id == s.dna_id, "dna_id")
        ok(abs(s2.cds - s.cds) < 1e-5, "cds")
        ok(s2.relevance == s.relevance, "relevance")
        ok(len(s2.contributions) == 10, "contributions count")
        ok(s2.context_stability_label == s.context_stability_label, "stability_label")
        return "ContextualDNAScore full round-trip"

    def t89():
        s = _default_score()
        profile = DNAContextProfile.from_score(s)
        ok(profile.dna_id == s.dna_id, "dna_id")
        ok(profile.latest_cds == s.cds, "latest_cds")
        ok(profile.latest_relevance == s.relevance, "relevance")
        ok(len(profile.top_contribution) > 0, "top_contribution empty")
        ok(profile.supporting_count + profile.conflicting_count == 10, "count sum")
        return f"profile.top_contribution={profile.top_contribution}"

    def t90():
        # DNAContextHistory.from_scores() trend detection
        s_early = _engine().evaluate_dna(_make_dna(), _adverse_context(), evaluation_date="2026-07-01")
        s_late  = _engine().evaluate_dna(_make_dna(), _bull_context(),    evaluation_date="2026-08-04")
        # Override dates to make ordering predictable
        object.__setattr__(s_early, "evaluation_date", "2026-07-01")
        object.__setattr__(s_late,  "evaluation_date", "2026-08-04")
        # Patch evidence to match dates
        object.__setattr__(s_early.evidence, "context_score_at_eval", 0.22)
        object.__setattr__(s_late.evidence,  "context_score_at_eval", 0.82)

        history = DNAContextHistory.from_scores([s_early, s_late])
        ok(history.dna_id == s_early.dna_id, "dna_id")
        ok(len(history.entries) == 2, "entries count")
        # CDS should improve from adverse → bull
        ok(history.cds_trend in ("IMPROVING", "STABLE"),
           f"expected IMPROVING, got {history.cds_trend}")
        return f"history.cds_trend={history.cds_trend} avg={history.avg_cds:.3f}"

    runner.run("T88 — ContextualDNAScore full to_dict/from_dict round-trip", t88)
    runner.run("T89 — DNAContextProfile.from_score() valid profile", t89)
    runner.run("T90 — DNAContextHistory.from_scores() trend detection", t90)


# ═══════════════════════════════════════════════════════════════════════════════
# Entry point
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    runner = TestRunner()
    _run_all(runner)
    sys.exit(runner.report())
