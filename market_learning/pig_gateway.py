"""
pig_gateway.py — R-001 Phase 1: Platform Intelligence Gateway.

The ONLY public entry point between the Trading Platform and the
institutional intelligence stack.

Responsibilities:
    Collect intelligence from PMCI, CA-PMCI, CDS, MCIE, and IDR.
    Aggregate results into a single PlatformIntelligence response.
    Normalise all outputs to [0, 1] where applicable.
    Provide full explainability: every score traces to its source.
    Hide all MLS implementation details from trading modules.

Explicitly NOT responsible for:
    Discovering, updating, or retiring DNA.
    Changing PMCI scores, CDS scores, or any strategy.
    Executing or recommending trades.
    Any write operation to any persistent store.

PIG is read-only.  evaluate_symbol() never mutates its inputs.
"""
from __future__ import annotations

import hashlib
import logging
from datetime import datetime
from typing import List, Optional

from market_learning.mls_config import MLSConfig
from market_learning.pmci_engine import PMCIEngine
from market_learning.pmci_models import PMCIResult
from market_learning.mcie_engine import MCIEngine
from market_learning.mcie_models import MarketContext
from market_learning.cds_engine import CDSEngine
from market_learning.cds_models import CDSLibraryResult
from market_learning.ca_pmci_engine import CAPMCIEngine
from market_learning.ca_pmci_models import CAPMCIResult
from market_learning.dna_consensus_models import ConsensusLibrary
from market_learning.market_observer_models import DailyMarketSnapshot, MarketObservation
from market_learning.idr_repository import IDRRepository
from market_learning.idr_models import DNARepositoryStatistics
from market_learning.pig_models import (
    PlatformConfidence,
    PlatformEvidence,
    PlatformGatewayError,
    PlatformGatewayInputError,
    PlatformGatewayStatistics,
    PlatformIntelligence,
    PlatformRecommendationContext,
)

log = logging.getLogger(__name__)


# ==============================================================================
# Pure helpers
# ==============================================================================

def _clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return lo if v < lo else (hi if v > hi else v)


def _mean(xs: List[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def _make_pig_id(symbol: str, evaluation_date: str) -> str:
    raw = f"{symbol}::pig::{evaluation_date}"
    return "PIG-" + hashlib.sha256(raw.encode()).hexdigest()[:8]


def _get_component(result: PMCIResult, name: str) -> float:
    """Extract named component value from PMCIResult; return 0.0 if absent."""
    for c in result.components:
        if c.name == name:
            return c.value
    return 0.0


def _build_confidence(
    pmci:      PMCIResult,
    ca_pmci:   CAPMCIResult,
    context:   MarketContext,
    idr_stats: DNARepositoryStatistics,
) -> PlatformConfidence:
    pc = pmci.confidence
    cc = ca_pmci.confidence
    mc = context.confidence
    ic = idr_stats.avg_confidence
    overall = _clamp(0.40 * pc + 0.35 * cc + 0.15 * mc + 0.10 * ic)
    return PlatformConfidence(
        overall=round(overall, 6),
        pmci=round(pc, 6),
        ca_pmci=round(cc, 6),
        context=round(mc, 6),
        institutional=round(ic, 6),
        explanation=(
            f"Blended confidence {overall:.3f} = "
            f"0.40*PMCI({pc:.3f}) + 0.35*CA-PMCI({cc:.3f}) + "
            f"0.15*context({mc:.3f}) + 0.10*IDR({ic:.3f})"
        ),
    )


def _build_evidence(
    pmci:      PMCIResult,
    ca_pmci:   CAPMCIResult,
    cds:       CDSLibraryResult,
    context:   MarketContext,
    idr_stats: DNARepositoryStatistics,
) -> List[PlatformEvidence]:
    wm = _get_component(pmci, "winner_match")
    lm = _get_component(pmci, "loser_match")
    fr = _get_component(pmci, "dna_freshness")
    drift = _clamp(1.0 - ca_pmci.dna_context_stability)
    ev_count = len(pmci.breakdown.matched_dna)
    avg_cds = cds.statistics.avg_cds if cds.scores else 0.0

    return [
        PlatformEvidence(
            source="PMCI", component="raw_pmci",
            value=round(pmci.pmci_score, 6),
            explanation=f"Raw PMCI={pmci.pmci_score:.3f} from PMCIEngine ({len(pmci.breakdown.matched_dna)} DNA matches)",
            raw={"pmci_score": pmci.pmci_score, "result_id": pmci.result_id, "library_id": pmci.library_id},
        ),
        PlatformEvidence(
            source="CA-PMCI", component="ca_pmci",
            value=round(ca_pmci.ca_pmci, 6),
            explanation=f"CA-PMCI={ca_pmci.ca_pmci:.3f} = raw({ca_pmci.raw_pmci:.3f}) + adj({ca_pmci.context_adjustment:+.3f})",
            raw={"raw_pmci": ca_pmci.raw_pmci, "context_adjustment": ca_pmci.context_adjustment, "result_id": ca_pmci.result_id},
        ),
        PlatformEvidence(
            source="CDS", component="cds_score",
            value=round(avg_cds, 6),
            explanation=f"Avg CDS={avg_cds:.3f} over {cds.statistics.total_dna} DNA; {cds.statistics.highly_relevant_count} highly relevant",
            raw={"avg_cds": avg_cds, "total_dna": cds.statistics.total_dna, "library_id": cds.library_id},
        ),
        PlatformEvidence(
            source="PMCI", component="winner_dna_match",
            value=round(wm, 6),
            explanation=f"Winner DNA alignment={wm:.3f}: {len(pmci.breakdown.matched_dna)} features align with winner DNA",
            raw={"winner_match": wm, "matched_count": len(pmci.breakdown.matched_dna)},
        ),
        PlatformEvidence(
            source="PMCI", component="loser_dna_match",
            value=round(lm, 6),
            explanation=f"Loser DNA presence={lm:.3f}: {len(pmci.breakdown.conflicting_dna)} features contradict winner DNA",
            raw={"loser_match": lm, "conflicting_count": len(pmci.breakdown.conflicting_dna)},
        ),
        PlatformEvidence(
            source="PMCI", component="evidence_count",
            value=float(ev_count),
            explanation=f"{ev_count} matched DNA features from library ({pmci.breakdown.total_institutional_dna} institutional total)",
            raw={"matched": ev_count, "missing": len(pmci.breakdown.missing_dna), "total_institutional": pmci.breakdown.total_institutional_dna},
        ),
        PlatformEvidence(
            source="MCIE", component="context_score",
            value=round(context.context_score, 6),
            explanation=f"Market context={context.context_score:.3f} (regime={context.regime}, stability={context.stability:.3f})",
            raw={"context_score": context.context_score, "regime": context.regime, "stability": context.stability, "context_id": context.context_id},
        ),
        PlatformEvidence(
            source="PMCI", component="dna_freshness",
            value=round(fr, 6),
            explanation=f"DNA freshness={fr:.3f}: recency of matched winner DNA",
            raw={"dna_freshness": fr},
        ),
        PlatformEvidence(
            source="CA-PMCI", component="dna_drift",
            value=round(drift, 6),
            explanation=f"DNA drift={drift:.3f} = 1 - context_stability({ca_pmci.dna_context_stability:.3f})",
            raw={"dna_context_stability": ca_pmci.dna_context_stability, "drift": drift},
        ),
        PlatformEvidence(
            source="IDR", component="institutional_confidence",
            value=round(idr_stats.avg_confidence, 6),
            explanation=f"IDR avg confidence={idr_stats.avg_confidence:.3f} over {idr_stats.total_dna} DNA ({idr_stats.institutional_dna} institutional)",
            raw={"avg_confidence": idr_stats.avg_confidence, "total_dna": idr_stats.total_dna, "institutional_dna": idr_stats.institutional_dna},
        ),
        PlatformEvidence(
            source="CA-PMCI", component="context_adjustment",
            value=round(ca_pmci.context_adjustment, 6),
            explanation=f"Context adjustment={ca_pmci.context_adjustment:+.3f} applied to raw PMCI across 5 named dimensions",
            raw={"context_adjustment": ca_pmci.context_adjustment, "regime": ca_pmci.regime, "context_score": ca_pmci.context_score},
        ),
    ]


def _classify_winner_alignment(ca_pmci_score: float, cfg: MLSConfig) -> str:
    if ca_pmci_score >= cfg.pig_high_threshold:
        return "HIGH"
    if ca_pmci_score >= cfg.pig_medium_threshold:
        return "MEDIUM"
    return "LOW"


def _classify_context_support(context_score: float, cfg: MLSConfig) -> str:
    if context_score >= cfg.mcie_high_context_threshold:
        return "STRONG"
    if context_score >= cfg.mcie_low_context_threshold:
        return "MODERATE"
    return "WEAK"


def _classify_intelligence_quality(ca_pmci: float, confidence: float, cfg: MLSConfig) -> str:
    if ca_pmci >= cfg.pig_high_threshold and confidence >= 0.60:
        return "HIGH"
    if ca_pmci >= cfg.pig_medium_threshold and confidence >= 0.40:
        return "MEDIUM"
    if ca_pmci > cfg.pig_low_threshold:
        return "LOW"
    return "INSUFFICIENT"


def _build_recommendation_context(
    symbol:   str,
    eval_date: str,
    ca_pmci:  CAPMCIResult,
    context:  MarketContext,
    conf:     PlatformConfidence,
    cfg:      MLSConfig,
) -> PlatformRecommendationContext:
    wa = _classify_winner_alignment(ca_pmci.ca_pmci, cfg)
    cs = _classify_context_support(context.context_score, cfg)
    iq = _classify_intelligence_quality(ca_pmci.ca_pmci, conf.overall, cfg)
    stability_label = ca_pmci.regime  # use regime as proxy when stability label unavailable
    # prefer the context stability label from CAPMCIResult if available via adjustments
    for adj in ca_pmci.adjustments:
        if adj.name == "context_stability":
            break
    explanation = (
        f"{symbol} on {eval_date}: CA-PMCI={ca_pmci.ca_pmci:.3f}, "
        f"winner_alignment={wa}, context_support={cs}, quality={iq}. "
        f"Regime={context.regime}, context_score={context.context_score:.3f}."
    )
    return PlatformRecommendationContext(
        symbol=symbol,
        evaluation_date=eval_date,
        regime=context.regime,
        context_stability=stability_label,
        winner_alignment=wa,
        context_support=cs,
        intelligence_quality=iq,
        raw_pmci=round(ca_pmci.raw_pmci, 6),
        ca_pmci=round(ca_pmci.ca_pmci, 6),
        confidence=round(conf.overall, 6),
        institutional_confidence=round(conf.institutional, 6),
        explanation=explanation,
    )


def _build_explanation(
    symbol:  str,
    pmci:    PMCIResult,
    ca_pmci: CAPMCIResult,
    cds:     CDSLibraryResult,
    context: MarketContext,
    idr_stats: DNARepositoryStatistics,
) -> str:
    avg_cds = cds.statistics.avg_cds if cds.scores else 0.0
    return (
        f"PIG evaluation for {symbol} on {pmci.evaluation_date}. "
        f"Raw PMCI={pmci.pmci_score:.3f} (source: PMCIEngine, {len(pmci.breakdown.matched_dna)} DNA matches). "
        f"CA-PMCI={ca_pmci.ca_pmci:.3f} (source: CAPMCIEngine, adjustment={ca_pmci.context_adjustment:+.3f}). "
        f"CDS={avg_cds:.3f} (source: CDSEngine, {cds.statistics.highly_relevant_count} highly relevant DNA). "
        f"Context={context.context_score:.3f} regime={context.regime} (source: MCIEngine). "
        f"IDR: {idr_stats.total_dna} DNA, {idr_stats.institutional_dna} institutional, "
        f"avg_confidence={idr_stats.avg_confidence:.3f}."
    )


# ==============================================================================
# PlatformIntelligenceGateway
# ==============================================================================

class PlatformIntelligenceGateway:
    """
    R-001 Phase 1 — Platform Intelligence Gateway.

    Single entry point for institutional intelligence.  Delegates all
    computation to the existing MLS engines without duplicating logic.

    Usage
    -----
    ::

        from market_learning import PlatformIntelligenceGateway

        gw = PlatformIntelligenceGateway()
        intel = gw.evaluate_symbol(
            symbol="RELIANCE",
            observation=obs,
            library=library,
            market_snapshot=snapshot,
            repo=idr_repo,
        )
        # intel.ca_pmci, intel.winner_dna_match, intel.recommendation_context ...

    PIG is read-only.  No method ever modifies DNA, PMCI, CDS, strategies,
    or any persistent store.
    """

    def __init__(
        self,
        config:         Optional[MLSConfig]    = None,
        mci_engine:     Optional[MCIEngine]    = None,
        pmci_engine:    Optional[PMCIEngine]   = None,
        cds_engine:     Optional[CDSEngine]    = None,
        ca_pmci_engine: Optional[CAPMCIEngine] = None,
    ) -> None:
        self._cfg     = config or MLSConfig()
        self._mci     = mci_engine     or MCIEngine(self._cfg)
        self._pmci    = pmci_engine    or PMCIEngine(self._cfg)
        self._cds     = cds_engine     or CDSEngine(self._cfg)
        self._ca_pmci = ca_pmci_engine or CAPMCIEngine(self._cfg)

    # --------------------------------------------------------------------------
    # Public API — query methods
    # --------------------------------------------------------------------------

    def evaluate_symbol(
        self,
        symbol:          str,
        observation:     MarketObservation,
        library:         ConsensusLibrary,
        market_snapshot,
        repo:            IDRRepository,
        evaluation_date: Optional[str] = None,
    ) -> PlatformIntelligence:
        """
        Evaluate one symbol against the full institutional intelligence stack.

        Parameters
        ----------
        symbol          : NSE ticker
        observation     : pre-move feature vector (MarketObservation)
        library         : DNA knowledge base (ConsensusLibrary from Phase 4)
        market_snapshot : current market snapshot (models.market_data.MarketSnapshot)
        repo            : Institutional DNA Repository
        evaluation_date : ISO date override; defaults to observation timestamp date

        Returns
        -------
        PlatformIntelligence — aggregated, normalised, fully explainable result.

        Read-only: no argument is ever modified.
        """
        if not symbol:
            raise PlatformGatewayInputError("symbol cannot be empty")
        if observation is None:
            raise PlatformGatewayInputError("observation cannot be None")
        if library is None:
            raise PlatformGatewayInputError("library cannot be None")
        if market_snapshot is None:
            raise PlatformGatewayInputError("market_snapshot cannot be None")
        if repo is None:
            raise PlatformGatewayInputError("repo cannot be None")

        context    = self._mci.evaluate(market_snapshot, evaluation_date)
        pmci_res   = self._pmci.evaluate(
            observation, library, evaluation_date, regime=str(context.regime)
        )
        ca_pmci_res = self._ca_pmci.evaluate_with_context(
            observation, library, market_snapshot, evaluation_date
        )
        cds_res    = self._cds.evaluate_library(library, context, market_snapshot, evaluation_date)
        idr_stats  = repo.statistics()

        return self._build_intelligence(
            symbol, pmci_res, ca_pmci_res, cds_res, context, idr_stats, evaluation_date
        )

    def evaluate_universe(
        self,
        daily_snapshot:  DailyMarketSnapshot,
        library:         ConsensusLibrary,
        market_snapshot,
        repo:            IDRRepository,
        evaluation_date: Optional[str] = None,
    ) -> List[PlatformIntelligence]:
        """
        Evaluate all symbols in a DailyMarketSnapshot.

        Market context and CDS are computed ONCE and shared across all symbols.
        Failed individual evaluations are skipped with a warning.
        Order of results matches daily_snapshot.observations order.
        """
        if daily_snapshot is None:
            raise PlatformGatewayInputError("daily_snapshot cannot be None")
        if library is None:
            raise PlatformGatewayInputError("library cannot be None")
        if market_snapshot is None:
            raise PlatformGatewayInputError("market_snapshot cannot be None")
        if repo is None:
            raise PlatformGatewayInputError("repo cannot be None")

        context   = self._mci.evaluate(market_snapshot, evaluation_date)
        cds_res   = self._cds.evaluate_library(library, context, market_snapshot, evaluation_date)
        idr_stats = repo.statistics()
        regime    = str(context.regime)

        results: List[PlatformIntelligence] = []
        for obs in daily_snapshot.observations:
            try:
                pmci_res    = self._pmci.evaluate(obs, library, evaluation_date, regime=regime)
                ca_pmci_res = self._ca_pmci.evaluate_with_context(
                    obs, library, market_snapshot, evaluation_date
                )
                results.append(self._build_intelligence(
                    obs.symbol, pmci_res, ca_pmci_res, cds_res, context, idr_stats, evaluation_date
                ))
            except Exception as exc:
                log.warning("PIG evaluate_universe failed for %s: %s", obs.symbol, exc)
        return results

    def get_context(
        self,
        market_snapshot,
        evaluation_date: Optional[str] = None,
    ) -> MarketContext:
        """
        Evaluate and return the current MarketContext.

        Delegates to MCIEngine.  Side effect: appends to MCIEngine history.
        """
        return self._mci.evaluate(market_snapshot, evaluation_date)

    def get_pmci(
        self,
        observation:     MarketObservation,
        library:         ConsensusLibrary,
        evaluation_date: Optional[str] = None,
        regime:          str = "unknown",
    ) -> PMCIResult:
        """
        Evaluate and return raw PMCI for one observation.

        Delegates to PMCIEngine.  Read-only.
        """
        return self._pmci.evaluate(observation, library, evaluation_date, regime=regime)

    def get_cds(
        self,
        library:         ConsensusLibrary,
        context:         MarketContext,
        market_snapshot  = None,
        evaluation_date: Optional[str] = None,
    ) -> CDSLibraryResult:
        """
        Evaluate and return CDS for the full library against the current context.

        Delegates to CDSEngine.  Read-only.
        """
        return self._cds.evaluate_library(library, context, market_snapshot, evaluation_date)

    def statistics(
        self,
        results: List[PlatformIntelligence],
    ) -> PlatformGatewayStatistics:
        """Return aggregate statistics for a batch of PlatformIntelligence results."""
        if not results:
            return PlatformGatewayStatistics.empty()

        raw_scores  = [r.raw_pmci              for r in results]
        ca_scores   = [r.ca_pmci               for r in results]
        conf_scores = [r.confidence            for r in results]
        cds_scores  = [r.cds_score             for r in results]
        inst_scores = [r.institutional_confidence for r in results]
        ev_counts   = [float(r.evidence_count) for r in results]

        thr_hi = self._cfg.pig_high_threshold
        thr_lo = self._cfg.pig_low_threshold
        top    = max(results, key=lambda r: r.ca_pmci)

        return PlatformGatewayStatistics(
            evaluation_date=results[0].evaluation_date,
            total_symbols=len(results),
            avg_raw_pmci=round(_mean(raw_scores), 6),
            avg_ca_pmci=round(_mean(ca_scores), 6),
            avg_confidence=round(_mean(conf_scores), 6),
            avg_cds_score=round(_mean(cds_scores), 6),
            avg_evidence_count=round(_mean(ev_counts), 3),
            high_quality_count=sum(1 for s in ca_scores if s >= thr_hi),
            low_quality_count=sum(1 for s in ca_scores if s <= thr_lo),
            avg_institutional_confidence=round(_mean(inst_scores), 6),
            top_symbol=top.symbol,
            top_ca_pmci=round(top.ca_pmci, 6),
            context_score=round(results[0].context_score, 6),
            regime=results[0].regime,
        )

    # --------------------------------------------------------------------------
    # Internal aggregation
    # --------------------------------------------------------------------------

    def _build_intelligence(
        self,
        symbol:     str,
        pmci_res:   PMCIResult,
        ca_res:     CAPMCIResult,
        cds_res:    CDSLibraryResult,
        context:    MarketContext,
        idr_stats:  DNARepositoryStatistics,
        eval_date:  Optional[str],
    ) -> PlatformIntelligence:
        date     = eval_date or pmci_res.evaluation_date
        avg_cds  = cds_res.statistics.avg_cds if cds_res.scores else 0.0
        wm       = _get_component(pmci_res, "winner_match")
        lm       = _get_component(pmci_res, "loser_match")
        fr       = _get_component(pmci_res, "dna_freshness")
        drift    = _clamp(1.0 - ca_res.dna_context_stability)

        platform_conf = _build_confidence(pmci_res, ca_res, context, idr_stats)
        evidence      = _build_evidence(pmci_res, ca_res, cds_res, context, idr_stats)
        rec_ctx       = _build_recommendation_context(symbol, date, ca_res, context, platform_conf, self._cfg)
        explanation   = _build_explanation(symbol, pmci_res, ca_res, cds_res, context, idr_stats)

        return PlatformIntelligence(
            result_id=_make_pig_id(symbol, date),
            symbol=symbol,
            evaluation_date=date,
            evaluated_at=datetime.utcnow().isoformat(),
            raw_pmci=round(pmci_res.pmci_score, 6),
            ca_pmci=round(ca_res.ca_pmci, 6),
            cds_score=round(avg_cds, 6),
            winner_dna_match=round(wm, 6),
            loser_dna_match=round(lm, 6),
            evidence_count=len(pmci_res.breakdown.matched_dna),
            confidence=platform_conf.overall,
            dna_freshness=round(fr, 6),
            dna_drift=round(drift, 6),
            institutional_confidence=round(idr_stats.avg_confidence, 6),
            context_score=round(context.context_score, 6),
            regime=str(context.regime),
            context_adjustment=round(ca_res.context_adjustment, 6),
            cds_highly_relevant_count=cds_res.statistics.highly_relevant_count,
            cds_relevant_count=cds_res.statistics.relevant_count,
            cds_total_dna=cds_res.statistics.total_dna,
            evidence=evidence,
            platform_confidence=platform_conf,
            recommendation_context=rec_ctx,
            explanation=explanation,
            pmci_result=pmci_res,
            ca_pmci_result=ca_res,
            market_context=context,
        )
