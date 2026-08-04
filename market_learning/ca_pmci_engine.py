"""
ca_pmci_engine.py — MLS Phase 5B: Context-Aware PMCI Engine.

Responsibilities:
    Bridge PMCIEngine (stock DNA similarity) and MCIEngine (market context).
    Compute Context-Aware PMCI (CA-PMCI) by adjusting raw PMCI scores
    according to the current market environment across five named dimensions.
    New API: evaluate_context(), evaluate_with_context(),
             evaluate_universe_with_context().

Explicitly NOT responsible for:
    Computing raw PMCI (Phase 5 — PMCIEngine).
    Evaluating market context (Phase 5A — MCIEngine).
    Feature extraction (Phase 1 — MarketObserver / FeatureExtractor).
    Population classification (Phase 2 — PopulationClassifier).
    DNA discovery (Phase 3 — DNADiscoveryEngine).
    Consensus building (Phase 4 — DNAConsensusEngine).
    Changing any DNA, ARS knowledge store, strategy, threshold, or signal.
    Executing, recommending, or signalling trades.
    Writing to any persistent store.

CA-PMCI is read-only.  evaluate_with_context() never mutates its inputs.

Context adjustment formula (per dimension):
    adj = (dna_quality + ctx_quality - 1.0) × weight
    Clamped to [-ca_pmci_max_single_adj, +ca_pmci_max_single_adj].

    Both at 1.0  →  +weight    (maximum reward)
    Both at 0.0  →  -weight    (maximum penalty)
    Both at 0.5  →   0.0       (neutral, no change)
"""
from __future__ import annotations

import hashlib
import logging
from datetime import datetime
from typing import List, Optional

from market_learning.mls_config import MLSConfig
from market_learning.market_observer_models import MarketObservation
from market_learning.dna_consensus_models import ConsensusLibrary
from market_learning.pmci_engine import PMCIEngine
from market_learning.pmci_models import PMCIResult
from market_learning.mcie_engine import MCIEngine
from market_learning.mcie_models import MarketContext
from market_learning.ca_pmci_models import (
    CAPMCIError,
    CAPMCIResult,
    CAPMCIStatistics,
    ContextAdjustment,
)

log = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# Pure helpers — no class state, directly importable for unit testing
# ═══════════════════════════════════════════════════════════════════════════════

def _clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    """Clamp v to [lo, hi]."""
    return lo if v < lo else (hi if v > hi else v)


def _mean(xs: List[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def _make_ca_pmci_id(symbol: str, evaluation_date: str) -> str:
    raw = f"{symbol}::ca::{evaluation_date}"
    return "CAP-" + hashlib.sha256(raw.encode()).hexdigest()[:8]


def _extract_component(result: PMCIResult, name: str) -> float:
    """Extract named component value from PMCIResult; return 0.0 if absent."""
    for c in result.components:
        if c.name == name:
            return c.value
    return 0.0


def _get_context_score(context: MarketContext, name: str) -> float:
    """Extract named component score from MarketContext; return 0.5 if absent."""
    for c in context.components:
        if c.name == name:
            return c.score
    return 0.5


def _compute_adj(
    dna_quality: float,
    ctx_quality: float,
    weight:      float,
    cap:         float,
) -> float:
    """
    Compute one context adjustment delta.

    Formula: (dna_quality + ctx_quality - 1.0) × weight, clamped to ±cap.

    Neutral point: dna_quality=0.5 AND ctx_quality=0.5 → delta=0.
    Maximum reward:  both=1.0 → +weight (before cap).
    Maximum penalty: both=0.0 → -weight (before cap).
    """
    raw = (dna_quality + ctx_quality - 1.0) * weight
    return _clamp(raw, -cap, cap)


# ═══════════════════════════════════════════════════════════════════════════════
# Engine
# ═══════════════════════════════════════════════════════════════════════════════

class CAPMCIEngine:
    """
    MLS Phase 5B — Context-Aware PMCI Engine.

    Combines PMCIEngine (stock DNA similarity) with MCIEngine (market context)
    to produce a Context-Aware PMCI score that reflects BOTH institutional
    Winner DNA AND the current market environment.

    CA-PMCI = raw_pmci + context_adjustment

    Five named adjustments are computed independently:
        1. regime_match      — DNA regime stability in current regime context
        2. volatility_match  — DNA evidence resilience in current volatility
        3. sector_match      — DNA sector stability vs current sector leadership
        4. context_stability — DNA confidence modulated by market context drift
        5. dna_freshness     — DNA recency weighted by overall context quality

    Every adjustment is explained and traceable to its source values.

    Backward compatibility: PMCIEngine.evaluate() and all existing PMCI API
    methods remain unchanged and continue to work independently.
    CAPMCIEngine adds evaluate_context(), evaluate_with_context(), and
    evaluate_universe_with_context() as new methods.
    """

    def __init__(
        self,
        config:     Optional[MLSConfig] = None,
        mci_engine: Optional[MCIEngine] = None,
    ) -> None:
        self._cfg = config or MLSConfig()
        # Allow injection of a pre-warmed MCIEngine (e.g. with existing history)
        self._mci = mci_engine

    # ── public API ────────────────────────────────────────────────────────────

    def evaluate_context(self, snapshot) -> MarketContext:
        """
        Evaluate the current market context from a MarketSnapshot.

        Returns a MarketContext without modifying any PMCI state.
        When an MCIEngine was injected at construction, it is reused
        (preserving history for drift/stability); otherwise a fresh
        single-use MCIEngine is created.
        """
        mci = self._mci or MCIEngine(self._cfg)
        return mci.evaluate(snapshot)

    def evaluate_with_context(
        self,
        observation:     MarketObservation,
        library:         ConsensusLibrary,
        snapshot,
        evaluation_date: Optional[str] = None,
    ) -> CAPMCIResult:
        """
        Evaluate one MarketObservation with full context awareness.

        Parameters
        ----------
        observation     : pre-move feature vector for one symbol
        library         : institutional DNA knowledge base (Phase 4 output)
        snapshot        : current MarketSnapshot (from models.market_data)
        evaluation_date : ISO date override; defaults to observation timestamp date

        Returns
        -------
        CAPMCIResult with raw_pmci, five named context adjustments, and ca_pmci.

        This method is read-only: library, observation, and snapshot are
        never modified.
        """
        context = self.evaluate_context(snapshot)
        raw     = PMCIEngine(self._cfg).evaluate(observation, library, evaluation_date)
        return self._adjust(raw, context)

    def evaluate_universe_with_context(
        self,
        observations:    List[MarketObservation],
        library:         ConsensusLibrary,
        snapshot,
        evaluation_date: Optional[str] = None,
    ) -> List[CAPMCIResult]:
        """
        Evaluate every observation in the list against the same library and context.

        The market context is computed ONCE and shared across all evaluations
        (batch efficiency — same snapshot, same context for all stocks).
        Failed individual evaluations are skipped with a warning.
        Order of results matches order of input observations.
        """
        context     = self.evaluate_context(snapshot)
        pmci_engine = PMCIEngine(self._cfg)
        results: List[CAPMCIResult] = []
        for obs in observations:
            try:
                raw = pmci_engine.evaluate(obs, library, evaluation_date)
                results.append(self._adjust(raw, context))
            except Exception as exc:
                log.warning("CA-PMCI evaluate failed for %s: %s", obs.symbol, exc)
        return results

    def statistics(self, results: List[CAPMCIResult]) -> CAPMCIStatistics:
        """Return aggregate CA-PMCI statistics for a batch of CAPMCIResult objects."""
        if not results:
            return CAPMCIStatistics(
                evaluation_date="",
                total_symbols=0,
                avg_raw_pmci=0.0,
                avg_ca_pmci=0.0,
                avg_context_adjustment=0.0,
                avg_context_score=0.0,
                high_ca_pmci_count=0,
                low_ca_pmci_count=0,
                top_symbol=None,
                top_ca_pmci=0.0,
                most_improved_symbol=None,
                most_degraded_symbol=None,
            )

        thr_hi = self._cfg.ca_pmci_high_threshold
        thr_lo = self._cfg.ca_pmci_low_threshold

        raw_scores  = [r.raw_pmci           for r in results]
        ca_scores   = [r.ca_pmci            for r in results]
        adjs        = [r.context_adjustment for r in results]
        ctx_scores  = [r.context_score      for r in results]

        top      = max(results, key=lambda r: r.ca_pmci)
        best_adj = max(results, key=lambda r: r.context_adjustment)
        worst_adj = min(results, key=lambda r: r.context_adjustment)

        return CAPMCIStatistics(
            evaluation_date=results[0].evaluation_date,
            total_symbols=len(results),
            avg_raw_pmci=round(_mean(raw_scores), 6),
            avg_ca_pmci=round(_mean(ca_scores), 6),
            avg_context_adjustment=round(_mean(adjs), 6),
            avg_context_score=round(_mean(ctx_scores), 6),
            high_ca_pmci_count=sum(1 for s in ca_scores if s >= thr_hi),
            low_ca_pmci_count=sum(1 for s in ca_scores if s <= thr_lo),
            top_symbol=top.symbol,
            top_ca_pmci=round(top.ca_pmci, 6),
            most_improved_symbol=(best_adj.symbol if best_adj.context_adjustment > 0 else None),
            most_degraded_symbol=(worst_adj.symbol if worst_adj.context_adjustment < 0 else None),
        )

    # ── private ───────────────────────────────────────────────────────────────

    def _adjust(self, raw: PMCIResult, context: MarketContext) -> CAPMCIResult:
        """Compute all context adjustments and assemble CAPMCIResult."""
        cfg = self._cfg
        cap = cfg.ca_pmci_max_single_adj

        # ── DNA quality proxies from PMCI components ──────────────────────────
        dna_regime_q  = _extract_component(raw, "regime_stability")   # regime consistency
        dna_sector_q  = _extract_component(raw, "sector_stability")   # sector consistency
        dna_vol_q     = _extract_component(raw, "evidence_strength")  # volatility resilience
        dna_freshness = _extract_component(raw, "dna_freshness")      # DNA recency
        dna_evidence  = _extract_component(raw, "evidence_strength")  # evidence confidence

        # ── market context quality from MCIE ──────────────────────────────────
        ctx_regime  = _get_context_score(context, "regime_context")
        ctx_vol     = _get_context_score(context, "volatility_context")
        ctx_sector  = _get_context_score(context, "sector_context")

        # ── 1. Regime match ───────────────────────────────────────────────────
        regime_adj   = _compute_adj(dna_regime_q, ctx_regime, cfg.ca_pmci_w_regime, cap)
        regime_label = ("Bull" if ctx_regime > 0.7 else "Bear" if ctx_regime > 0.5 else "Range/Volatile")
        regime_verb  = "favours" if regime_adj >= 0 else "weakens"

        # ── 2. Volatility match ───────────────────────────────────────────────
        vol_adj   = _compute_adj(dna_vol_q, ctx_vol, cfg.ca_pmci_w_volatility, cap)
        vol_env   = "Low" if ctx_vol > 0.7 else "High"
        vol_verb  = "supports" if vol_adj >= 0 else "weakens"

        # ── 3. Sector match ───────────────────────────────────────────────────
        sector_adj   = _compute_adj(dna_sector_q, ctx_sector, cfg.ca_pmci_w_sector, cap)
        sector_env   = "leading" if ctx_sector > 0.6 else "lagging/neutral"
        sector_verb  = "rewards" if sector_adj >= 0 else "penalises"

        # ── 4. Context stability ──────────────────────────────────────────────
        stability_adj = _compute_adj(dna_evidence, context.stability, cfg.ca_pmci_w_stability, cap)
        stab_label    = "stable" if context.stability > 0.6 else "drifting"
        stab_verb     = "reinforces" if stability_adj >= 0 else "reduces"

        # ── 5. DNA freshness ──────────────────────────────────────────────────
        freshness_adj = _compute_adj(dna_freshness, context.context_score, cfg.ca_pmci_w_freshness, cap)
        fresh_label   = "fresh" if dna_freshness > 0.6 else "stale"
        ctx_quality   = "favorable" if context.context_score > 0.5 else "adverse"
        fresh_verb    = "amplifies" if freshness_adj >= 0 else "discounts"

        adjustments = [
            ContextAdjustment(
                name="regime_match",
                delta=round(regime_adj, 6),
                explanation=f"{regime_label} regime {regime_verb} this DNA ({regime_adj:+.4f})",
                evidence={
                    "dna_regime_stability":  round(dna_regime_q, 4),
                    "regime_context_score":  round(ctx_regime, 4),
                },
            ),
            ContextAdjustment(
                name="volatility_match",
                delta=round(vol_adj, 6),
                explanation=f"{vol_env} VIX {vol_verb} this DNA ({vol_adj:+.4f})",
                evidence={
                    "dna_evidence_strength":    round(dna_vol_q, 4),
                    "volatility_context_score": round(ctx_vol, 4),
                },
            ),
            ContextAdjustment(
                name="sector_match",
                delta=round(sector_adj, 6),
                explanation=f"Sector currently {sector_env} — {sector_verb} this DNA ({sector_adj:+.4f})",
                evidence={
                    "dna_sector_stability": round(dna_sector_q, 4),
                    "sector_context_score": round(ctx_sector, 4),
                },
            ),
            ContextAdjustment(
                name="context_stability",
                delta=round(stability_adj, 6),
                explanation=f"Context {stab_label} — {stab_verb} confidence ({stability_adj:+.4f})",
                evidence={
                    "dna_evidence_strength": round(dna_evidence, 4),
                    "context_stability":     round(context.stability, 4),
                },
            ),
            ContextAdjustment(
                name="dna_freshness",
                delta=round(freshness_adj, 6),
                explanation=(
                    f"DNA {fresh_label} in {ctx_quality} context — "
                    f"{fresh_verb} weight ({freshness_adj:+.4f})"
                ),
                evidence={
                    "dna_freshness":         round(dna_freshness, 4),
                    "overall_context_score": round(context.context_score, 4),
                },
            ),
        ]

        # ── total context adjustment (clamped) ────────────────────────────────
        total_raw      = sum(a.delta for a in adjustments)
        max_adj        = cfg.ca_pmci_max_total_adj
        context_adj    = _clamp(total_raw, -max_adj, max_adj)

        # ── derived new context components ────────────────────────────────────
        # DNA context stability: how consistently does this DNA work across contexts?
        dna_ctx_stability = _clamp(_mean([dna_regime_q, dna_sector_q, dna_vol_q]))

        # Context match score: weighted alignment of DNA with current market context
        regime_align  = (dna_regime_q + ctx_regime) / 2.0
        sector_align  = (dna_sector_q + ctx_sector) / 2.0
        vol_align     = (dna_vol_q    + ctx_vol)    / 2.0
        context_match = _clamp(0.40 * regime_align + 0.35 * sector_align + 0.25 * vol_align)

        # Context adjustment factor: normalized [0, 1] (0.5 = neutral, >0.5 = net positive)
        ctx_adj_factor = _clamp(0.5 + context_adj / (2.0 * max(1e-12, max_adj)))

        # ── final CA-PMCI ──────────────────────────────────────────────────────
        ca_pmci = _clamp(raw.pmci_score + context_adj)

        # ── blended confidence ─────────────────────────────────────────────────
        confidence = _clamp((raw.confidence + context.confidence) / 2.0)

        # ── explanation (each adjustment on its own line) ─────────────────────
        adj_lines = " | ".join(a.explanation for a in adjustments)
        explanation = (
            f"CA-PMCI={ca_pmci:.3f} for {raw.symbol} on {raw.evaluation_date}. "
            f"Raw PMCI={raw.pmci_score:.3f}, context_score={context.context_score:.3f}, "
            f"context_adjustment={context_adj:+.4f}. "
            f"Adjustments: [{adj_lines}]."
        )

        return CAPMCIResult(
            result_id=_make_ca_pmci_id(raw.symbol, raw.evaluation_date),
            symbol=raw.symbol,
            evaluation_date=raw.evaluation_date,
            raw_pmci=round(raw.pmci_score, 6),
            context_score=round(context.context_score, 6),
            context_id=context.context_id,
            regime=context.regime,
            context_match_score=round(context_match, 6),
            dna_context_stability=round(dna_ctx_stability, 6),
            dna_regime_match=round(dna_regime_q, 6),
            dna_sector_match=round(dna_sector_q, 6),
            dna_volatility_match=round(dna_vol_q, 6),
            dna_freshness_weight=round(dna_freshness, 6),
            context_adjustment_factor=round(ctx_adj_factor, 6),
            adjustments=adjustments,
            context_adjustment=round(context_adj, 6),
            ca_pmci=round(ca_pmci, 6),
            confidence=round(confidence, 6),
            explanation=explanation,
            pmci_result=raw,
            library_id=raw.library_id,
            feature_count=raw.feature_count,
            evaluated_at=datetime.now().isoformat(timespec="seconds"),
        )
