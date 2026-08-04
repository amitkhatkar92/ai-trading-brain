"""
pmci_engine.py — MLS Phase 5: Pre-Movement Consensus Intelligence Engine.

Responsibilities:
    Transform institutional DNA knowledge (ConsensusLibrary) into an
    evidence-based similarity score for each stock.
    Measure how closely a MarketObservation resembles Winner DNA before movement.
    Compute all nine PMCI components with full explainability.
    Provide batch evaluation, ranking, and aggregate statistics.

Explicitly NOT responsible for:
    Feature extraction (Phase 1 — MarketObserver / FeatureExtractor).
    Population classification (Phase 2 — PopulationClassifier).
    DNA discovery (Phase 3 — DNADiscoveryEngine).
    Consensus building (Phase 4 — DNAConsensusEngine).
    Changing any DNA, ARS knowledge store, strategy, or threshold.
    Executing, recommending, or signalling trades.
    Writing to any persistent store.

PMCI is read-only.  evaluate() never mutates its inputs.
"""
from __future__ import annotations

import hashlib
import logging
from datetime import date as _date, datetime
from typing import Dict, List, Optional, Tuple

from market_learning.mls_config import MLSConfig
from market_learning.market_observer_models import DailyMarketSnapshot, MarketObservation
from market_learning.dna_discovery_models import SeparationDirection
from market_learning.dna_consensus_models import (
    ConsensusDNA,
    ConsensusLibrary,
    ConsensusState,
)
from market_learning.pmci_models import (
    PMCIBreakdown,
    PMCIComponent,
    PMCIError,
    PMCIEvidence,
    PMCIResult,
    PMCIStatistics,
)

log = logging.getLogger(__name__)

# ConsensusState values that contribute to PMCI (RETIRED excluded)
_ACTIVE_STATES = frozenset({
    ConsensusState.DISCOVERED,
    ConsensusState.REPLICATED,
    ConsensusState.VERIFIED,
    ConsensusState.INSTITUTIONAL,
    ConsensusState.WEAKENING,
    ConsensusState.DRIFTING,
})

_WINNER_DIRECTIONS = frozenset({
    SeparationDirection.WINNERS_HIGHER,
    SeparationDirection.WINNERS_LOWER,
})

_NEUTRAL_DIRECTIONS = frozenset({
    SeparationDirection.NEUTRALS_HIGHER,
    SeparationDirection.NEUTRALS_LOWER,
})


# ═══════════════════════════════════════════════════════════════════════════════
# Pure helpers — no class state, directly importable for unit testing
# ═══════════════════════════════════════════════════════════════════════════════

def _clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    """Clamp v to [lo, hi]."""
    return lo if v < lo else (hi if v > hi else v)


def _mean(xs: List[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def _align(value: float, direction: SeparationDirection) -> float:
    """
    Return [0, 1] alignment of a feature value with the winner direction.

    Assumes feature values normalised to [0, 1].  Values outside that range
    are clamped before the alignment is computed.

    WINNERS_HIGHER : high value → alignment 1.0, low value → 0.0
    WINNERS_LOWER  : low value  → alignment 1.0, high value → 0.0
    NEUTRALS_HIGHER: treated symmetrically with WINNERS_HIGHER
    NEUTRALS_LOWER : treated symmetrically with WINNERS_LOWER
    """
    v = _clamp(value)
    if direction in (SeparationDirection.WINNERS_HIGHER,
                     SeparationDirection.NEUTRALS_HIGHER):
        return v
    return 1.0 - v          # WINNERS_LOWER or NEUTRALS_LOWER


def _freshness(last_seen: str, as_of: str, max_days: int) -> float:
    """
    Linear decay from 1.0 (last_seen == as_of) to 0.0 (last_seen == as_of - max_days).

    Returns 0.5 on any parse error.
    """
    try:
        delta = (_date.fromisoformat(as_of) - _date.fromisoformat(last_seen)).days
        return _clamp(1.0 - delta / max(1, max_days))
    except (ValueError, OverflowError):
        return 0.5


def _make_pmci_id(symbol: str, evaluation_date: str) -> str:
    raw = f"{symbol}::{evaluation_date}"
    return "PMC-" + hashlib.sha256(raw.encode()).hexdigest()[:8]


# ═══════════════════════════════════════════════════════════════════════════════
# Engine
# ═══════════════════════════════════════════════════════════════════════════════

class PMCIEngine:
    """
    MLS Phase 5 — Pre-Movement Consensus Intelligence Engine.

    Transforms a MarketObservation + ConsensusLibrary into a PMCI score that
    measures how closely the stock resembles institutional Winner DNA before any
    price movement.

    PMCI is a similarity measure.  It is NOT a trade signal.
    This engine is stateless and read-only: every call to evaluate() is
    independent and leaves no side-effects.
    """

    def __init__(self, config: Optional[MLSConfig] = None) -> None:
        self._cfg = config or MLSConfig()

    # ── public API ────────────────────────────────────────────────────────────

    def evaluate(
        self,
        observation: MarketObservation,
        library: ConsensusLibrary,
        evaluation_date: Optional[str] = None,
        regime: str = "unknown",
    ) -> PMCIResult:
        """
        Evaluate one MarketObservation against the ConsensusLibrary.

        Parameters
        ----------
        observation     : pre-move feature vector for one symbol
        library         : institutional DNA knowledge base (Phase 4 output)
        evaluation_date : ISO date override; defaults to observation timestamp date
        regime          : market regime string for context (does not affect score)

        Returns
        -------
        PMCIResult with full component breakdown and explainability.

        This method is read-only: library and observation are never modified.
        """
        as_of = evaluation_date or observation.feature_timestamp[:10]
        return self._compute(observation, library, as_of, regime)

    def evaluate_universe(
        self,
        observations: List[MarketObservation],
        library: ConsensusLibrary,
        evaluation_date: Optional[str] = None,
        regime: str = "unknown",
    ) -> List[PMCIResult]:
        """
        Evaluate every observation in the list against the same library.

        Failed evaluations are skipped with a warning; all others are returned.
        Order of results matches order of input observations.
        """
        results: List[PMCIResult] = []
        for obs in observations:
            try:
                results.append(self.evaluate(obs, library, evaluation_date, regime))
            except Exception as exc:
                log.warning("PMCI evaluate failed for %s: %s", obs.symbol, exc)
        return results

    def evaluate_symbol(
        self,
        symbol: str,
        snapshot: DailyMarketSnapshot,
        library: ConsensusLibrary,
        evaluation_date: Optional[str] = None,
    ) -> Optional[PMCIResult]:
        """
        Evaluate a named symbol found in a DailyMarketSnapshot.

        Returns None if symbol is not present in the snapshot.
        Uses snapshot.regime and snapshot.trading_date as context.
        """
        obs = snapshot.get_observation(symbol)
        if obs is None:
            return None
        as_of = evaluation_date or snapshot.trading_date
        return self._compute(obs, library, as_of, regime=snapshot.regime)

    def top_matches(
        self,
        results: List[PMCIResult],
        n: int = 10,
    ) -> List[PMCIResult]:
        """
        Return the top-n PMCIResult entries sorted by pmci_score descending.

        Returns all results if len(results) <= n.
        """
        return sorted(results, key=lambda r: r.pmci_score, reverse=True)[:n]

    def statistics(self, results: List[PMCIResult]) -> PMCIStatistics:
        """Return aggregate statistics for a batch of PMCIResult objects."""
        if not results:
            return PMCIStatistics(
                evaluation_date="",
                total_symbols=0,
                avg_pmci=0.0, max_pmci=0.0, min_pmci=0.0,
                high_similarity_count=0, low_similarity_count=0,
                avg_winner_match=0.0, avg_loser_match=0.0,
                avg_coverage=0.0, top_symbol=None, top_pmci=0.0,
            )

        scores         = [r.pmci_score for r in results]
        thr_high       = self._cfg.pmci_high_similarity_threshold
        thr_low        = self._cfg.pmci_low_similarity_threshold
        winner_vals    = self._extract_component(results, "winner_match")
        loser_vals     = self._extract_component(results, "loser_match")
        coverage_vals  = self._extract_component(results, "knowledge_coverage")
        top            = max(results, key=lambda r: r.pmci_score)

        return PMCIStatistics(
            evaluation_date=results[0].evaluation_date,
            total_symbols=len(results),
            avg_pmci=round(_mean(scores), 6),
            max_pmci=round(max(scores), 6),
            min_pmci=round(min(scores), 6),
            high_similarity_count=sum(1 for s in scores if s >= thr_high),
            low_similarity_count=sum(1 for s in scores if s <= thr_low),
            avg_winner_match=round(_mean(winner_vals), 6),
            avg_loser_match=round(_mean(loser_vals), 6),
            avg_coverage=round(_mean(coverage_vals), 6),
            top_symbol=top.symbol,
            top_pmci=round(top.pmci_score, 6),
        )

    # ── private ────────────────────────────────────────────────────────────────

    @staticmethod
    def _extract_component(results: List[PMCIResult], name: str) -> List[float]:
        out: List[float] = []
        for r in results:
            for c in r.components:
                if c.name == name:
                    out.append(c.value)
        return out

    def _compute(
        self,
        obs: MarketObservation,
        library: ConsensusLibrary,
        as_of: str,
        regime: str,
    ) -> PMCIResult:
        cfg  = self._cfg
        mid  = cfg.pmci_feature_midpoint
        fmax = cfg.pmci_freshness_days
        thr  = cfg.consensus_trend_declining_slope

        # ── partition library into active winner / neutral DNA ────────────────
        active_dna   = [c for c in library.all_consensus
                        if c.consensus_state in _ACTIVE_STATES]
        winner_dna   = [c for c in active_dna if c.direction in _WINNER_DIRECTIONS]
        neutral_dna_ = [c for c in active_dna if c.direction in _NEUTRAL_DIRECTIONS]

        # ── score each winner DNA feature against observation ─────────────────
        matched_ev:     List[PMCIEvidence] = []
        conflicting_ev: List[PMCIEvidence] = []
        missing:        List[str]          = []

        for cdna in winner_dna:
            fname = cdna.feature_name
            if fname not in obs.features:
                missing.append(fname)
                continue
            v         = obs.features[fname]
            alignment = _align(v, cdna.direction)
            contrib   = alignment * cdna.consensus_score
            is_match  = alignment >= mid
            is_contra = alignment < (1.0 - mid)
            ev = PMCIEvidence(
                feature_name=fname,
                direction=cdna.direction.value,
                stock_value=v,
                alignment=round(alignment, 6),
                consensus_score=cdna.consensus_score,
                evidence_count=cdna.evidence_count,
                last_seen=cdna.last_seen,
                consensus_state=cdna.consensus_state.value,
                contribution=round(contrib, 6),
                is_match=is_match,
                is_contradiction=is_contra,
            )
            (matched_ev if is_match else conflicting_ev).append(ev)

        # ── score neutral DNA ─────────────────────────────────────────────────
        neutral_ev: List[PMCIEvidence] = []
        for cdna in neutral_dna_:
            fname = cdna.feature_name
            if fname not in obs.features:
                continue
            v         = obs.features[fname]
            alignment = _align(v, cdna.direction)
            neutral_ev.append(PMCIEvidence(
                feature_name=fname,
                direction=cdna.direction.value,
                stock_value=v,
                alignment=round(alignment, 6),
                consensus_score=cdna.consensus_score,
                evidence_count=cdna.evidence_count,
                last_seen=cdna.last_seen,
                consensus_state=cdna.consensus_state.value,
                contribution=round(alignment * cdna.consensus_score, 6),
                is_match=alignment >= mid,
                is_contradiction=alignment < (1.0 - mid),
            ))

        all_winner_ev = matched_ev + conflicting_ev

        # ── component 1: winner DNA match (weighted avg alignment) ────────────
        if all_winner_ev:
            wt_sum = sum(e.consensus_score for e in all_winner_ev)
            winner_match = (
                sum(e.contribution for e in all_winner_ev) / wt_sum
                if wt_sum > 1e-12
                else _mean([e.alignment for e in all_winner_ev])
            )
        else:
            winner_match = 0.0

        # ── component 2: loser DNA match (complement of winner match) ─────────
        # winner_match + loser_match = 1.0 for any non-empty observation
        loser_match = (1.0 - winner_match) if all_winner_ev else 0.0

        # ── component 3: neutral DNA match ────────────────────────────────────
        if neutral_ev:
            wt_sum = sum(e.consensus_score for e in neutral_ev)
            neutral_match = (
                sum(e.contribution for e in neutral_ev) / wt_sum
                if wt_sum > 1e-12
                else _mean([e.alignment for e in neutral_ev])
            )
        else:
            neutral_match = 0.0

        # ── component 4: evidence strength (avg score of matched features) ────
        evidence_strength = _mean([e.consensus_score for e in matched_ev]) if matched_ev else 0.0

        # ── components 5+6: cross-regime / cross-sector stability ─────────────
        relevant_dna = [c for c in winner_dna if c.feature_name in obs.features]
        regime_stability = _mean([c.regime_consistency for c in relevant_dna]) if relevant_dna else 0.0
        sector_stability = _mean([c.sector_consistency for c in relevant_dna]) if relevant_dna else 0.0

        # ── component 7: confidence trend (fraction with IMPROVING slope) ─────
        improving_count = sum(1 for c in relevant_dna if c.confidence_trend > thr)
        trend_score = improving_count / len(relevant_dna) if relevant_dna else 0.0

        # ── component 8: DNA freshness ────────────────────────────────────────
        freshness = (
            _mean([_freshness(e.last_seen, as_of, fmax) for e in all_winner_ev])
            if all_winner_ev else 0.0
        )

        # ── component 9: knowledge coverage ──────────────────────────────────
        total_active   = len(winner_dna) + len(neutral_dna_)
        observed_total = len(all_winner_ev) + len(neutral_ev)
        coverage       = observed_total / total_active if total_active > 0 else 0.0

        # ── PMCI formula ──────────────────────────────────────────────────────
        positive = (
            cfg.pmci_w_winner    * winner_match
            + cfg.pmci_w_evidence  * evidence_strength
            + cfg.pmci_w_regime    * regime_stability
            + cfg.pmci_w_sector    * sector_stability
            + cfg.pmci_w_trend     * trend_score
            + cfg.pmci_w_freshness * freshness
            + cfg.pmci_w_coverage  * coverage
            + cfg.pmci_w_neutral   * neutral_match
        )
        penalty  = cfg.pmci_w_loser * loser_match
        pmci     = _clamp(positive - penalty)

        # ── meta-confidence: fraction of INSTITUTIONAL DNA features present ───
        inst_dna  = [c for c in library.all_consensus
                     if c.consensus_state == ConsensusState.INSTITUTIONAL]
        if inst_dna:
            inst_present = sum(1 for c in inst_dna if c.feature_name in obs.features)
            confidence   = inst_present / len(inst_dna)
        else:
            confidence = coverage

        # ── assemble components ───────────────────────────────────────────────
        cw, cl, ce = cfg.pmci_w_winner, cfg.pmci_w_loser, cfg.pmci_w_evidence
        cr, cs, ct = cfg.pmci_w_regime, cfg.pmci_w_sector, cfg.pmci_w_trend
        cf, ck, cn = cfg.pmci_w_freshness, cfg.pmci_w_coverage, cfg.pmci_w_neutral

        n_obs = len(all_winner_ev)

        components = [
            PMCIComponent("winner_match",      winner_match,      cw, round(cw * winner_match, 6),      len(matched_ev),    f"{len(matched_ev)}/{n_obs} features align with winner DNA"),
            PMCIComponent("loser_match",        loser_match,       cl, round(cl * loser_match, 6),        len(conflicting_ev),f"{len(conflicting_ev)}/{n_obs} features contradict winner DNA"),
            PMCIComponent("neutral_match",      neutral_match,     cn, round(cn * neutral_match, 6),      len(neutral_ev),    f"{len(neutral_ev)} neutral DNA features evaluated"),
            PMCIComponent("evidence_strength",  evidence_strength, ce, round(ce * evidence_strength, 6),  len(matched_ev),    f"avg consensus_score of matched features={evidence_strength:.3f}"),
            PMCIComponent("regime_stability",   regime_stability,  cr, round(cr * regime_stability, 6),   len(relevant_dna),  f"avg regime_consistency across present DNA={regime_stability:.3f}"),
            PMCIComponent("sector_stability",   sector_stability,  cs, round(cs * sector_stability, 6),   len(relevant_dna),  f"avg sector_consistency across present DNA={sector_stability:.3f}"),
            PMCIComponent("confidence_trend",   trend_score,       ct, round(ct * trend_score, 6),        improving_count,    f"{improving_count}/{len(relevant_dna)} present DNA features have improving trend"),
            PMCIComponent("dna_freshness",      freshness,         cf, round(cf * freshness, 6),          n_obs,              f"avg DNA freshness (decay over {fmax}d)={freshness:.3f}"),
            PMCIComponent("knowledge_coverage", coverage,          ck, round(ck * coverage, 6),           observed_total,     f"{observed_total}/{total_active} active DNA features found in observation"),
        ]

        breakdown = PMCIBreakdown(
            matched_dna=sorted(matched_ev, key=lambda e: e.contribution, reverse=True),
            missing_dna=sorted(set(missing)),
            conflicting_dna=sorted(conflicting_ev, key=lambda e: e.contribution),
            neutral_dna=neutral_ev,
            total_institutional_dna=len(inst_dna),
            coverage_fraction=round(coverage, 6),
        )

        explanation = (
            f"PMCI={pmci:.3f} for {obs.symbol} on {as_of}. "
            f"Winner DNA: {len(matched_ev)} matched, {len(conflicting_ev)} contradicted, "
            f"{len(missing)} missing. "
            f"Evidence strength={evidence_strength:.2f}, "
            f"coverage={coverage:.0%}, confidence={confidence:.0%}."
        )

        return PMCIResult(
            result_id=_make_pmci_id(obs.symbol, as_of),
            symbol=obs.symbol,
            evaluation_date=as_of,
            regime=regime,
            pmci_score=round(pmci, 6),
            components=components,
            breakdown=breakdown,
            confidence=round(confidence, 6),
            explanation=explanation,
            library_id=library.library_id,
            feature_count=obs.feature_count,
            evaluated_at=datetime.now().isoformat(timespec="seconds"),
        )
