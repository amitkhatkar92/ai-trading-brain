"""
cds_engine.py — MLS Phase 5A.1: Contextual DNA Score Engine.

Responsibilities:
    For every ConsensusDNA in the library, evaluate how well the current
    market context supports that DNA characteristic.
    Compute 10 named match dimensions per DNA with full explainability.
    Maintain an in-memory context history for historical analogue search.
    Classify each DNA by contextual relevance (HIGHLY_RELEVANT → DEPRECATED).
    Provide deterministic, reproducible CDS results.

Explicitly NOT responsible for:
    Changing PMCI scores (Phase 5 / Phase 5B — read-only integration).
    Changing DNA, ARS, strategies, thresholds, or any persistent store.
    Executing, recommending, or signalling trades.
    Feature extraction (Phase 1).
    Population classification (Phase 2).
    DNA discovery or consensus building (Phases 3-4).
    Computing the market context (Phase 5A — MCIEngine does that).

CDS is stateful (context history for analogue search) but never mutates inputs.
"""
from __future__ import annotations

import hashlib
import logging
import math
from collections import deque
from datetime import date as _date, datetime
from typing import Dict, List, Optional, Tuple

from market_learning.mls_config import MLSConfig
from market_learning.dna_consensus_models import ConsensusDNA, ConsensusLibrary
from market_learning.mcie_models import MarketContext
from market_learning.cds_models import (
    CDSError,
    CDSInputError,
    CDSLibraryResult,
    ContextStabilityLabel,
    ContextualDNAScore,
    DNAContextContribution,
    DNAContextEvidence,
    DNAContextProfile,
    DNAContextSimilarity,
    DNAContextStatistics,
    DNARelevance,
)

log = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# Pure helpers — no class state, directly importable for unit testing
# ═══════════════════════════════════════════════════════════════════════════════

def _clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return lo if v < lo else (hi if v > hi else v)


def _mean(xs: List[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def _make_cds_id(dna_id: str, evaluation_date: str) -> str:
    raw = f"{dna_id}::{evaluation_date}"
    return "CDS-" + hashlib.sha256(raw.encode()).hexdigest()[:8]


def _get_ctx_score(context: MarketContext, name: str) -> float:
    """Extract a named component score from MarketContext; default 0.5 if absent."""
    for c in context.components:
        if c.name == name:
            return c.score
    return 0.5


def _score_regime_match(
    regime_consistency: float,
    regime_fraction: float,
    regime_ctx_score: float,
) -> float:
    """
    Regime match: does current regime support this DNA?

    Regime-agnostic DNA (consistency >= 0.80) benefits from any clear regime.
    Regime-specific DNA scores by fraction of history in current regime.
    """
    if regime_consistency >= 0.80:
        return _clamp(0.50 + regime_ctx_score * 0.50)
    return _clamp(regime_fraction * 0.70 + regime_ctx_score * 0.30)


def _score_volatility_match(temporal_stability: float, vol_ctx_score: float) -> float:
    """Volatility match: stable DNA works in varied vol; unstable DNA needs calm markets."""
    return _clamp(temporal_stability * 0.40 + vol_ctx_score * 0.60)


def _score_sector_match(sector_consistency: float, sector_ctx_score: float) -> float:
    """Sector match: broadly consistent DNA + broad sector participation."""
    return _clamp(sector_consistency * 0.40 + sector_ctx_score * 0.60)


def _score_breadth_match(feature_persistence: float, breadth_ctx_score: float) -> float:
    """Breadth match: persistent DNA + wide market participation."""
    return _clamp(feature_persistence * 0.30 + breadth_ctx_score * 0.70)


def _score_liquidity_match(evidence_count: int, liq_ctx_score: float) -> float:
    """Liquidity match: evidence proxy (saturates at 50 obs) + liquidity environment."""
    evidence_proxy = _clamp(evidence_count / 50.0)
    return _clamp(evidence_proxy * 0.30 + liq_ctx_score * 0.70)


def _score_institutional_match(regime_consistency: float, inst_ctx_score: float) -> float:
    """Institutional match: regime-consistent DNA + institutional activity."""
    return _clamp(regime_consistency * 0.40 + inst_ctx_score * 0.60)


def _score_global_match(temporal_stability: float, global_ctx_score: float) -> float:
    """Global context match: stable DNA + favorable global environment."""
    return _clamp(temporal_stability * 0.30 + global_ctx_score * 0.70)


def _score_freshness(last_seen: str, evaluation_date: str, freshness_days: int) -> float:
    """Freshness match: linear decay from 1.0 (today) to 0.0 at freshness_days."""
    try:
        age = max(0, (_date.fromisoformat(evaluation_date) - _date.fromisoformat(last_seen)).days)
        return _clamp(1.0 - age / max(1, freshness_days))
    except Exception:
        return 0.5


def _score_stability_match(replication_frequency: float, context_stability: float) -> float:
    """Stability match: replicating DNA + stable context reinforces confidence."""
    return _clamp(replication_frequency * 0.40 + context_stability * 0.60)


def _cosine_similarity(a: List[float], b: List[float]) -> float:
    """Cosine similarity between two equal-length vectors."""
    if len(a) != len(b) or not a:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = math.sqrt(sum(x * x for x in a))
    mag_b = math.sqrt(sum(y * y for y in b))
    if mag_a < 1e-9 or mag_b < 1e-9:
        return 0.0
    return _clamp(dot / (mag_a * mag_b))


def _classify_relevance(cds: float, cfg: MLSConfig) -> DNARelevance:
    if cds >= cfg.cds_highly_relevant:  return DNARelevance.HIGHLY_RELEVANT
    if cds >= cfg.cds_relevant:         return DNARelevance.RELEVANT
    if cds >= cfg.cds_neutral:          return DNARelevance.NEUTRAL
    if cds >= cfg.cds_weak:             return DNARelevance.WEAK
    if cds >= cfg.cds_irrelevant:       return DNARelevance.IRRELEVANT
    return DNARelevance.DEPRECATED


def _classify_stability(context_stability: float, cfg: MLSConfig) -> ContextStabilityLabel:
    """Classify context stability from (1 - stability) delta."""
    delta = 1.0 - context_stability
    if delta < cfg.cds_stable_threshold:            return ContextStabilityLabel.STABLE
    if delta < cfg.cds_changing_threshold:          return ContextStabilityLabel.CHANGING
    if delta < cfg.cds_rapidly_changing_threshold:  return ContextStabilityLabel.RAPIDLY_CHANGING
    if delta < cfg.cds_unstable_threshold:          return ContextStabilityLabel.UNSTABLE
    return ContextStabilityLabel.DRIFTING


# ═══════════════════════════════════════════════════════════════════════════════
# CDSEngine
# ═══════════════════════════════════════════════════════════════════════════════

class CDSEngine:
    """
    MLS Phase 5A.1 — Contextual DNA Score Engine.

    Evaluates how well the current market context supports each ConsensusDNA.
    Computes 10 named match dimensions per DNA with full explainability.
    Maintains an in-memory context history for historical analogue search.

    Stateful (context history), but never mutates its inputs.
    """

    def __init__(
        self,
        config: Optional[MLSConfig] = None,
        mci_engine=None,
    ) -> None:
        self._cfg = config or MLSConfig()
        self._mci = mci_engine  # optional pre-warmed MCIEngine
        self._context_history: deque = deque(maxlen=self._cfg.cds_max_history_size)

    # ── public API ────────────────────────────────────────────────────────────

    def evaluate_dna(
        self,
        dna: ConsensusDNA,
        context: MarketContext,
        snapshot=None,
        evaluation_date: Optional[str] = None,
        library_id: str = "",
    ) -> ContextualDNAScore:
        """
        Evaluate contextual relevance of one ConsensusDNA.

        Parameters
        ----------
        dna             : ConsensusDNA to evaluate.
        context         : Current MarketContext (from MCIEngine.evaluate()).
        snapshot        : Optional MarketSnapshot for raw evidence capture.
        evaluation_date : ISO date string; defaults to context.evaluation_date.
        library_id      : Source library identifier; defaults to empty string.

        Returns
        -------
        ContextualDNAScore — reproducible, fully explainable CDS result.
        """
        self._store_context(context)
        eval_date = evaluation_date or context.evaluation_date
        return self._score(dna, context, snapshot, eval_date, library_id)

    def evaluate(
        self,
        library: ConsensusLibrary,
        context: MarketContext,
        snapshot=None,
        evaluation_date: Optional[str] = None,
    ) -> List[ContextualDNAScore]:
        """
        Evaluate all INSTITUTIONAL DNA in the library against the current context.

        Uses library.master_consensus (state == INSTITUTIONAL only).
        Context is stored once; all DNA share the same MarketContext.

        Returns
        -------
        List[ContextualDNAScore] — one result per INSTITUTIONAL DNA.
        """
        self._store_context(context)
        eval_date = evaluation_date or context.evaluation_date
        results: List[ContextualDNAScore] = []
        for dna in library.master_consensus:
            try:
                results.append(self._score(dna, context, snapshot, eval_date, library.library_id))
            except Exception as exc:
                log.warning("CDS failed for %s: %s", dna.feature_name, exc)
        return results

    def evaluate_library(
        self,
        library: ConsensusLibrary,
        context: MarketContext,
        snapshot=None,
        evaluation_date: Optional[str] = None,
    ) -> CDSLibraryResult:
        """
        Full library CDS evaluation — returns scores AND aggregate statistics.

        Returns
        -------
        CDSLibraryResult with scores, statistics, context metadata.
        """
        scores = self.evaluate(library, context, snapshot, evaluation_date)
        stats = self.statistics(scores, evaluation_date or context.evaluation_date, library.library_id)
        stability_label = _classify_stability(context.stability, self._cfg)
        return CDSLibraryResult(
            library_id=library.library_id,
            evaluation_date=evaluation_date or context.evaluation_date,
            scores=scores,
            statistics=stats,
            context_id=context.context_id,
            context_stability=stability_label,
            evaluated_at=datetime.utcnow().isoformat(),
        )

    def top_supported_dna(
        self,
        results: List[ContextualDNAScore],
        n: int = 10,
    ) -> List[ContextualDNAScore]:
        """Return up to n results sorted by CDS descending."""
        return sorted(results, key=lambda r: r.cds, reverse=True)[:n]

    def least_supported_dna(
        self,
        results: List[ContextualDNAScore],
        n: int = 10,
    ) -> List[ContextualDNAScore]:
        """Return up to n results sorted by CDS ascending."""
        return sorted(results, key=lambda r: r.cds)[:n]

    def historical_matches(
        self,
        context: MarketContext,
        top_n: Optional[int] = None,
    ) -> List[DNAContextSimilarity]:
        """
        Find historical contexts most similar to the provided context.

        Uses cosine similarity over the 8-component score vector.

        Returns
        -------
        List[DNAContextSimilarity] sorted by similarity descending.
        """
        return self._find_similar_contexts(context, top_n or self._cfg.cds_top_analogues)

    def statistics(
        self,
        results: List[ContextualDNAScore],
        evaluation_date: str = "",
        library_id: str = "",
    ) -> DNAContextStatistics:
        """Aggregate CDS statistics over a batch of ContextualDNAScore results."""
        if not results:
            return DNAContextStatistics.empty(evaluation_date, library_id)

        counts: Dict[DNARelevance, int] = {r: 0 for r in DNARelevance}
        for r in results:
            counts[r.relevance] += 1

        cds_values = [r.cds for r in results]
        avg_cds = _mean(cds_values)

        top_r = max(results, key=lambda r: r.cds)
        least_r = min(results, key=lambda r: r.cds)

        avg_support = _mean([len(r.supporting_dimensions) for r in results])
        avg_hist = _mean([r.historical_similarity_score for r in results])
        dom_stab = results[0].context_stability_label.value  # same for all in batch

        return DNAContextStatistics(
            evaluation_date=evaluation_date or results[0].evaluation_date,
            library_id=library_id or results[0].library_id,
            total_dna=len(results),
            highly_relevant_count=counts[DNARelevance.HIGHLY_RELEVANT],
            relevant_count=counts[DNARelevance.RELEVANT],
            neutral_count=counts[DNARelevance.NEUTRAL],
            weak_count=counts[DNARelevance.WEAK],
            irrelevant_count=counts[DNARelevance.IRRELEVANT],
            deprecated_count=counts[DNARelevance.DEPRECATED],
            avg_cds=avg_cds,
            top_dna_id=top_r.dna_id,
            top_dna_feature=top_r.feature_name,
            top_cds=top_r.cds,
            least_dna_id=least_r.dna_id,
            least_dna_feature=least_r.feature_name,
            least_cds=least_r.cds,
            avg_supporting_dimensions=avg_support,
            avg_historical_similarity=avg_hist,
            dominant_context_stability=dom_stab,
        )

    # ── private ───────────────────────────────────────────────────────────────

    def _store_context(self, context: MarketContext) -> None:
        """Store context vector for future historical analogue search (deduplicates by id)."""
        if any(e["context_id"] == context.context_id for e in self._context_history):
            return
        vec = [c.score for c in sorted(context.components, key=lambda c: c.name)]
        names = [c.name for c in sorted(context.components, key=lambda c: c.name)]
        self._context_history.append({
            "context_id":    context.context_id,
            "date":          context.evaluation_date,
            "regime":        context.regime,
            "context_score": context.context_score,
            "vector":        vec,
            "names":         names,
        })

    def _find_similar_contexts(
        self,
        context: MarketContext,
        top_n: int,
    ) -> List[DNAContextSimilarity]:
        if len(self._context_history) == 0:
            return []

        current_vec = [c.score for c in sorted(context.components, key=lambda c: c.name)]
        current_names = [c.name for c in sorted(context.components, key=lambda c: c.name)]

        matches: List[DNAContextSimilarity] = []
        for entry in self._context_history:
            if entry["context_id"] == context.context_id:
                continue
            hist_vec = entry["vector"]
            sim = _cosine_similarity(current_vec, hist_vec)

            # Matched dimensions: component names with |delta| < 0.20
            hist_names = entry.get("names", [])
            if len(hist_vec) == len(current_vec):
                matched = [
                    name
                    for name, cv, hv in zip(current_names, current_vec, hist_vec)
                    if abs(cv - hv) < 0.20
                ]
            else:
                matched = []

            n_matched = len(matched)
            explanation = (
                f"Context on {entry['date']} ({entry['regime']}) "
                f"resembles today with {n_matched}/{len(current_vec)} aligned dimensions "
                f"(similarity={sim:.3f})"
            )
            matches.append(DNAContextSimilarity(
                analogue_id=entry["context_id"],
                analogue_date=entry["date"],
                similarity_score=round(sim, 6),
                context_score=entry["context_score"],
                regime=entry["regime"],
                explanation=explanation,
                matched_dimensions=matched,
            ))

        matches.sort(key=lambda m: m.similarity_score, reverse=True)
        return matches[:top_n]

    def _historical_dimension(
        self,
        context: MarketContext,
    ) -> Tuple[float, List[DNAContextSimilarity]]:
        """Compute historical match score and top-N similar past contexts."""
        matches = self._find_similar_contexts(context, self._cfg.cds_top_analogues)
        score = _mean([m.similarity_score for m in matches]) if matches else 0.5
        return score, matches

    def _score(
        self,
        dna: ConsensusDNA,
        context: MarketContext,
        snapshot,
        eval_date: str,
        library_id: str,
    ) -> ContextualDNAScore:
        eval_id = _make_cds_id(dna.consensus_id, eval_date)
        cfg = self._cfg

        # ── extract context component scores ──────────────────────────────────
        r_ctx  = _get_ctx_score(context, "regime_context")
        v_ctx  = _get_ctx_score(context, "volatility_context")
        l_ctx  = _get_ctx_score(context, "liquidity_context")
        p_ctx  = _get_ctx_score(context, "participation_context")
        s_ctx  = _get_ctx_score(context, "sector_context")
        i_ctx  = _get_ctx_score(context, "institutional_context")
        g_ctx  = _get_ctx_score(context, "global_context")

        # ── regime fraction for current regime ────────────────────────────────
        total_obs = sum(dna.regime_counts.values())
        regime_fraction = (
            dna.regime_counts.get(context.regime, 0) / total_obs
            if total_obs > 0 else 0.5
        )

        # ── freshness age in days ─────────────────────────────────────────────
        try:
            age_days = max(
                0,
                (_date.fromisoformat(eval_date) - _date.fromisoformat(dna.last_seen)).days,
            )
        except Exception:
            age_days = 0

        evidence_proxy = _clamp(dna.evidence_count / 50.0)

        # ── 10 dimension scores ───────────────────────────────────────────────
        s_regime  = _score_regime_match(dna.regime_consistency, regime_fraction, r_ctx)
        s_vol     = _score_volatility_match(dna.temporal_stability, v_ctx)
        s_sector  = _score_sector_match(dna.sector_consistency, s_ctx)
        s_breadth = _score_breadth_match(dna.feature_persistence, p_ctx)
        s_liq     = _score_liquidity_match(dna.evidence_count, l_ctx)
        s_inst    = _score_institutional_match(dna.regime_consistency, i_ctx)
        s_global  = _score_global_match(dna.temporal_stability, g_ctx)
        s_fresh   = _score_freshness(dna.last_seen, eval_date, cfg.cds_freshness_days)
        s_stab    = _score_stability_match(dna.replication_frequency, context.stability)
        s_hist, hist_matches = self._historical_dimension(context)

        # ── CDS = weighted sum ────────────────────────────────────────────────
        cds = _clamp(
            s_regime  * cfg.cds_w_regime       +
            s_vol     * cfg.cds_w_volatility   +
            s_sector  * cfg.cds_w_sector       +
            s_breadth * cfg.cds_w_breadth      +
            s_liq     * cfg.cds_w_liquidity    +
            s_inst    * cfg.cds_w_institutional +
            s_global  * cfg.cds_w_global       +
            s_fresh   * cfg.cds_w_freshness    +
            s_stab    * cfg.cds_w_stability    +
            s_hist    * cfg.cds_w_historical
        )

        # ── build 10 contributions ────────────────────────────────────────────
        raw = [
            (
                "regime_match", s_regime, cfg.cds_w_regime,
                {
                    "current_regime":       context.regime,
                    "regime_context_score": r_ctx,
                    "dna_regime_fraction":  round(regime_fraction, 3),
                    "dna_regime_consistency": dna.regime_consistency,
                    "dna_regime_counts":    dict(dna.regime_counts),
                },
                (
                    f"Regime-agnostic DNA benefits from {context.regime} regime (score={s_regime:.3f})"
                    if dna.regime_consistency >= 0.80 else
                    f"{dna.regime_counts.get(context.regime, 0)}/{total_obs} DNA observations"
                    f" in {context.regime} (score={s_regime:.3f})"
                ),
            ),
            (
                "volatility_match", s_vol, cfg.cds_w_volatility,
                {
                    "volatility_context_score": v_ctx,
                    "dna_temporal_stability":   dna.temporal_stability,
                },
                f"Volatility environment {'favorable' if s_vol >= 0.50 else 'adverse'}"
                f" for DNA (score={s_vol:.3f})",
            ),
            (
                "sector_match", s_sector, cfg.cds_w_sector,
                {
                    "sector_context_score":   s_ctx,
                    "dna_sector_consistency": dna.sector_consistency,
                },
                f"Sector rotation {'supports' if s_sector >= 0.50 else 'opposes'}"
                f" DNA (score={s_sector:.3f})",
            ),
            (
                "breadth_match", s_breadth, cfg.cds_w_breadth,
                {
                    "breadth_context_score":    p_ctx,
                    "dna_feature_persistence":  dna.feature_persistence,
                },
                f"Market breadth {'supports' if s_breadth >= 0.50 else 'weakens'}"
                f" DNA spread (score={s_breadth:.3f})",
            ),
            (
                "liquidity_match", s_liq, cfg.cds_w_liquidity,
                {
                    "liquidity_context_score": l_ctx,
                    "dna_evidence_count":      dna.evidence_count,
                    "evidence_proxy":          round(evidence_proxy, 3),
                },
                f"Liquidity {'adequate' if s_liq >= 0.50 else 'insufficient'}"
                f" for DNA (score={s_liq:.3f})",
            ),
            (
                "institutional_match", s_inst, cfg.cds_w_institutional,
                {
                    "institutional_context_score": i_ctx,
                    "dna_regime_consistency":      dna.regime_consistency,
                },
                f"Institutional activity {'aligns' if s_inst >= 0.50 else 'conflicts'}"
                f" with DNA (score={s_inst:.3f})",
            ),
            (
                "global_match", s_global, cfg.cds_w_global,
                {
                    "global_context_score":   g_ctx,
                    "dna_temporal_stability": dna.temporal_stability,
                },
                f"Global context {'favors' if s_global >= 0.50 else 'weakens'}"
                f" DNA signal (score={s_global:.3f})",
            ),
            (
                "freshness_match", s_fresh, cfg.cds_w_freshness,
                {
                    "dna_last_seen":    dna.last_seen,
                    "evaluation_date":  eval_date,
                    "age_days":         age_days,
                    "freshness_window": cfg.cds_freshness_days,
                },
                f"DNA is {age_days}d old"
                f" (freshness={s_fresh:.3f}, window={cfg.cds_freshness_days}d)",
            ),
            (
                "stability_match", s_stab, cfg.cds_w_stability,
                {
                    "context_stability":    context.stability,
                    "dna_replication_freq": dna.replication_frequency,
                },
                f"Context {'stable' if s_stab >= 0.50 else 'unstable'} — "
                f"reliability {'reinforced' if s_stab >= 0.50 else 'reduced'}"
                f" (score={s_stab:.3f})",
            ),
            (
                "historical_match", s_hist, cfg.cds_w_historical,
                {
                    "historical_match_count": len(hist_matches),
                    "avg_similarity":         round(s_hist, 3),
                    "top_analogue_date":      hist_matches[0].analogue_date if hist_matches else None,
                },
                f"{len(hist_matches)} historical analogues, avg similarity={s_hist:.3f}",
            ),
        ]

        contributions = [
            DNAContextContribution(
                name=name,
                score=score,
                weight=weight,
                weighted_score=round(score * weight, 6),
                supporting=score >= 0.50,
                explanation=expl,
                evidence=evidence,
            )
            for name, score, weight, evidence, expl in raw
        ]

        supporting  = [c.name for c in contributions if c.supporting]
        conflicting = [c.name for c in contributions if not c.supporting]
        relevance        = _classify_relevance(cds, cfg)
        stability_label  = _classify_stability(context.stability, cfg)

        # ── snapshot-derived values for evidence ──────────────────────────────
        fii_net     = 0.0
        vix_val     = 0.0
        breadth_val = 0.5
        g_sentiment = 0.0
        if snapshot is not None:
            vix_val     = getattr(snapshot, "vix", 0.0)
            breadth_val = getattr(snapshot, "market_breadth", 0.5)
            g_sentiment = getattr(snapshot, "global_sentiment_score", 0.0)
            fii_dii = getattr(snapshot, "fii_dii", None)
            if fii_dii is not None:
                fii_net = fii_dii.fii_net

        evidence_obj = DNAContextEvidence(
            evaluation_id=eval_id,
            dna_id=dna.consensus_id,
            feature_name=dna.feature_name,
            direction=dna.direction.value,
            regime_at_eval=context.regime,
            vix_at_eval=vix_val,
            breadth_at_eval=breadth_val,
            context_score_at_eval=context.context_score,
            context_stability_at_eval=context.stability,
            fii_net_at_eval=fii_net,
            sector_score_at_eval=s_ctx,
            global_sentiment_at_eval=g_sentiment,
            dna_regime_counts=dict(dna.regime_counts),
            dna_evidence_count=dna.evidence_count,
            dna_last_seen=dna.last_seen,
            dna_replication_freq=dna.replication_frequency,
            dna_temporal_stability=dna.temporal_stability,
            dna_regime_consistency=dna.regime_consistency,
            dna_sector_consistency=dna.sector_consistency,
        )

        # ── confidence ────────────────────────────────────────────────────────
        evidence_conf = _clamp(dna.evidence_count / 20.0)
        confidence = _clamp((context.confidence + evidence_conf) / 2.0)

        # ── explanation ───────────────────────────────────────────────────────
        top3_s = ", ".join(supporting[:3])   if supporting   else "none"
        top3_c = ", ".join(conflicting[:3])  if conflicting  else "none"
        explanation = (
            f"CDS={cds:.3f} for {dna.feature_name} ({dna.direction.value}) on {eval_date}. "
            f"Relevance: {relevance.value}. "
            f"Context: {context.regime} score={context.context_score:.3f}. "
            f"Supporting: [{top3_s}]. Conflicting: [{top3_c}]."
        )

        return ContextualDNAScore(
            evaluation_id=eval_id,
            dna_id=dna.consensus_id,
            feature_name=dna.feature_name,
            direction=dna.direction.value,
            evaluation_date=eval_date,
            cds=cds,
            relevance=relevance,
            contributions=contributions,
            supporting_dimensions=supporting,
            conflicting_dimensions=conflicting,
            context_stability_label=stability_label,
            historical_similarity_score=s_hist,
            historical_matches=hist_matches,
            evidence=evidence_obj,
            explanation=explanation,
            confidence=confidence,
            library_id=library_id,
            evaluated_at=datetime.utcnow().isoformat(),
        )
