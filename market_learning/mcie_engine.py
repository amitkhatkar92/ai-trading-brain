"""
mcie_engine.py — MLS Phase 5A: Market Context Intelligence Engine.

Responsibilities:
    Evaluate the CURRENT market environment from a MarketSnapshot.
    Convert raw market indicators into a multi-dimensional context profile.
    Measure Regime, Volatility, Liquidity, Participation, Sector,
    Institutional, Global, and Risk context dimensions.
    Maintain an in-memory evaluation history for drift and statistics.
    Provide full explainability for every context score.

Explicitly NOT responsible for:
    Scoring individual stocks (Phase 5 — PMCIEngine).
    Feature extraction (Phase 1 — MarketObserver / FeatureExtractor).
    Population classification (Phase 2 — PopulationClassifier).
    DNA discovery (Phase 3 — DNADiscoveryEngine).
    Consensus building (Phase 4 — DNAConsensusEngine).
    PMCI evaluation (Phase 5 — PMCIEngine).
    Changing any DNA, ARS knowledge store, strategy, threshold, or PMCI score.
    Executing, recommending, or signalling trades.
    Writing to any persistent store.

MCIE is stateful (maintains in-memory history) but never mutates its inputs.
Each call to evaluate() is pure with respect to the snapshot.
"""
from __future__ import annotations

import hashlib
import logging
from typing import Dict, List, Optional

from market_learning.mls_config import MLSConfig
from market_learning.mcie_models import (
    ContextComponent,
    ContextDrift,
    ContextHistory,
    ContextStatistics,
    MarketContext,
    MCIEError,
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


def _make_context_id(timestamp_iso: str, evaluation_date: str) -> str:
    raw = f"{timestamp_iso}::{evaluation_date}"
    return "MCE-" + hashlib.sha256(raw.encode()).hexdigest()[:8]


def _score_regime(regime_str: str) -> float:
    """
    Clarity / quality of the current market regime as a context signal.

    A clear, strong regime (bull or bear) scores higher than uncertain
    or sideways regimes.  VOLATILE is scored lowest because it implies
    confusion and rapid direction changes.
    """
    return {
        "bull_trend":   0.90,  # clear strong uptrend
        "bear_market":  0.65,  # clear downtrend — adverse but certain
        "range_market": 0.45,  # no directional clarity
        "volatile":     0.20,  # chaotic, rapidly changing
    }.get(regime_str.lower(), 0.50)


def _score_volatility(
    vix: float,
    vix_low: float,
    vix_medium: float,
    vix_high: float,
    vix_extreme: float,
) -> float:
    """
    Volatility environment quality for strategy execution.

    Lower VIX = less uncertainty = higher score.
    Thresholds come from MLSConfig (mcie_vix_*).
    """
    if vix <= vix_low:     return 0.90
    if vix <= vix_medium:  return 0.70
    if vix <= vix_high:    return 0.40
    if vix <= vix_extreme: return 0.20
    return 0.05


def _score_liquidity(breadth: float, fii_dii) -> float:
    """
    Market liquidity from institutional flow + breadth.

    When FII/DII data is absent, breadth alone proxies liquidity.
    Reference scale: ±4000 crore / day separates high from low flow.
    """
    if fii_dii is None:
        return _clamp(breadth)
    total_net = fii_dii.fii_net + fii_dii.dii_net
    flow_score = _clamp(0.5 + total_net / 4000.0)
    return _clamp(0.4 * breadth + 0.6 * flow_score)


def _score_sector(sector_flows: list) -> float:
    """
    Sector rotation context: fraction of sectors with positive flow.

    0 sectors positive → 0.0; all positive → 1.0; empty → neutral 0.5.
    """
    if not sector_flows:
        return 0.5
    positive = sum(1 for sf in sector_flows if sf.flow_score > 0)
    return positive / len(sector_flows)


def _score_institutional(fii_dii) -> float:
    """
    Institutional activity context from FII (70%) and DII (30%) net flows.

    Reference: ±3000 crore maps to score ≈ 1.0 or ≈ 0.0.
    Returns 0.5 when FII/DII data is absent.
    """
    if fii_dii is None:
        return 0.5
    fii_score = _clamp(0.5 + fii_dii.fii_net / 3000.0)
    dii_score = _clamp(0.5 + fii_dii.dii_net / 3000.0)
    return _clamp(0.70 * fii_score + 0.30 * dii_score)


def _score_global(global_sentiment_score: float, global_bias) -> float:
    """
    Global market sentiment context.

    global_sentiment_score ∈ [−1, +1] → linearly mapped to [0, 1].
    global_bias ("bullish"/"neutral"/"bearish") adds a ±0.05 adjustment.
    """
    base = _clamp(0.5 + float(global_sentiment_score or 0.0) / 2.0)
    bias_adj = {"bullish": 0.05, "neutral": 0.0, "bearish": -0.05}
    adj = bias_adj.get(str(global_bias or "neutral").lower(), 0.0)
    return _clamp(base + adj)


def _score_risk(
    pcr: float,
    vix: float,
    pcr_lo: float,
    pcr_hi: float,
    vix_low: float,
    vix_medium: float,
    vix_high: float,
    vix_extreme: float,
) -> float:
    """
    Combined risk environment score from PCR and VIX.

    PCR in balanced zone [pcr_lo, pcr_hi] → pcr_score = 1.0.
    PCR below zone (call-heavy / complacent) → proportionally lower.
    PCR above zone (put-heavy / defensive fear) → proportionally lower.
    Combined as 50% PCR + 50% VIX.
    """
    if pcr_lo <= pcr <= pcr_hi:
        pcr_score = 1.0
    elif pcr < pcr_lo:
        pcr_score = _clamp(pcr / pcr_lo)
    else:  # pcr > pcr_hi
        excess = pcr - pcr_hi
        pcr_score = _clamp(1.0 - excess / max(1e-9, 3.0 - pcr_hi))

    vix_score = _score_volatility(vix, vix_low, vix_medium, vix_high, vix_extreme)
    return _clamp(0.5 * pcr_score + 0.5 * vix_score)


# ═══════════════════════════════════════════════════════════════════════════════
# Engine
# ═══════════════════════════════════════════════════════════════════════════════

# Fixed order of the 8 context dimension names
_COMPONENT_NAMES = (
    "regime_context",
    "volatility_context",
    "liquidity_context",
    "participation_context",
    "sector_context",
    "institutional_context",
    "global_context",
    "risk_context",
)


class MCIEngine:
    """
    MLS Phase 5A — Market Context Intelligence Engine.

    Transforms a MarketSnapshot into a multi-dimensional MarketContext that
    describes the current market environment across 8 independent dimensions.

    MCIE is the market-awareness layer for IIOS:
    - It evaluates the market, not individual stocks.
    - It is stateful: evaluate() appends to in-memory history.
    - It never writes to disk, changes DNA, changes thresholds, or signals trades.
    - Each call to evaluate() is pure with respect to the snapshot.
    """

    def __init__(self, config: Optional[MLSConfig] = None) -> None:
        self._cfg = config or MLSConfig()
        self._history: List[MarketContext] = []

    # ── public API ────────────────────────────────────────────────────────────

    def evaluate(
        self,
        snapshot,
        evaluation_date: Optional[str] = None,
    ) -> MarketContext:
        """
        Evaluate a MarketSnapshot and return a complete MarketContext.

        Parameters
        ----------
        snapshot        : MarketSnapshot (from models.market_data)
        evaluation_date : ISO date override; defaults to snapshot.timestamp date

        Returns
        -------
        MarketContext with 8 dimensions, full evidence, and explainability.

        Side effects: appends result to in-memory history (bounded).
        The snapshot is never modified.
        """
        as_of = evaluation_date or snapshot.timestamp.strftime("%Y-%m-%d")
        prev  = self._history[-1] if self._history else None
        ctx   = self._compute(snapshot, as_of, prev)
        self._history.append(ctx)
        if len(self._history) > self._cfg.mcie_max_history_size:
            self._history.pop(0)
        return ctx

    def current_context(self) -> Optional[MarketContext]:
        """Return the most recently evaluated MarketContext, or None."""
        return self._history[-1] if self._history else None

    def history(self) -> ContextHistory:
        """Return a snapshot of the full evaluation history (oldest first)."""
        return ContextHistory(contexts=list(self._history))

    def drift(self) -> Optional[ContextDrift]:
        """
        Return drift between the last two evaluations.

        Returns None if fewer than two evaluations have been performed.
        """
        if len(self._history) < 2:
            return None
        return self._compute_drift(self._history[-2], self._history[-1])

    def statistics(self) -> ContextStatistics:
        """Return aggregate statistics over all evaluations in history."""
        if not self._history:
            return ContextStatistics(
                evaluation_date="",
                total_evaluations=0,
                avg_context_score=0.0,
                max_context_score=0.0,
                min_context_score=0.0,
                avg_confidence=0.0,
                avg_stability=0.0,
                most_volatile_component="",
                regime_distribution={},
                high_context_count=0,
                low_context_count=0,
            )

        scores      = [c.context_score for c in self._history]
        confs       = [c.confidence    for c in self._history]
        stabs       = [c.stability     for c in self._history]
        thr_hi      = self._cfg.mcie_high_context_threshold
        thr_lo      = self._cfg.mcie_low_context_threshold

        # per-component score ranges for "most volatile" detection
        comp_ranges: Dict[str, List[float]] = {}
        for ctx in self._history:
            for comp in ctx.components:
                comp_ranges.setdefault(comp.name, []).append(comp.score)
        most_volatile = max(
            comp_ranges,
            key=lambda n: (
                max(comp_ranges[n]) - min(comp_ranges[n])
                if len(comp_ranges[n]) > 1 else 0.0
            ),
            default="",
        )

        regime_dist: Dict[str, int] = {}
        for ctx in self._history:
            regime_dist[ctx.regime] = regime_dist.get(ctx.regime, 0) + 1

        return ContextStatistics(
            evaluation_date=self._history[-1].evaluation_date,
            total_evaluations=len(self._history),
            avg_context_score=round(_mean(scores), 6),
            max_context_score=round(max(scores), 6),
            min_context_score=round(min(scores), 6),
            avg_confidence=round(_mean(confs), 6),
            avg_stability=round(_mean(stabs), 6),
            most_volatile_component=most_volatile,
            regime_distribution=regime_dist,
            high_context_count=sum(1 for s in scores if s >= thr_hi),
            low_context_count=sum(1 for s in scores if s  <= thr_lo),
        )

    # ── private ────────────────────────────────────────────────────────────────

    def _compute(
        self,
        snapshot,
        as_of: str,
        prev_context: Optional[MarketContext],
    ) -> MarketContext:
        cfg = self._cfg

        # ── extract inputs safely ─────────────────────────────────────────────
        regime_str = (
            snapshot.regime.value
            if hasattr(snapshot.regime, "value")
            else str(snapshot.regime or "unknown")
        )
        vix      = float(getattr(snapshot, "vix",                   15.0) or 15.0)
        pcr      = float(getattr(snapshot, "pcr",                    1.0)  or  1.0)
        _mb      = getattr(snapshot, "market_breadth", None)
        breadth  = float(_mb if _mb is not None else 0.5)
        g_score  = float(getattr(snapshot, "global_sentiment_score", 0.0) or  0.0)
        g_bias   = getattr(snapshot, "global_bias", None)
        fii_dii  = getattr(snapshot, "fii_dii",     None)
        s_flows  = list(getattr(snapshot, "sector_flows", None) or [])

        fii_net  = float(fii_dii.fii_net) if fii_dii else None
        dii_net  = float(fii_dii.dii_net) if fii_dii else None
        pos_secs = sum(1 for sf in s_flows if sf.flow_score > 0)

        # ── score each dimension ──────────────────────────────────────────────
        s_regime = _score_regime(regime_str)
        s_vola   = _score_volatility(vix, cfg.mcie_vix_low, cfg.mcie_vix_medium,
                                     cfg.mcie_vix_high, cfg.mcie_vix_extreme)
        s_liq    = _score_liquidity(breadth, fii_dii)
        s_part   = _clamp(breadth)
        s_sector = _score_sector(s_flows)
        s_inst   = _score_institutional(fii_dii)
        s_global = _score_global(g_score, g_bias)
        s_risk   = _score_risk(pcr, vix, cfg.mcie_pcr_balanced_lo,
                               cfg.mcie_pcr_balanced_hi,
                               cfg.mcie_vix_low, cfg.mcie_vix_medium,
                               cfg.mcie_vix_high, cfg.mcie_vix_extreme)

        weights = [
            cfg.mcie_w_regime, cfg.mcie_w_volatility, cfg.mcie_w_liquidity,
            cfg.mcie_w_participation, cfg.mcie_w_sector, cfg.mcie_w_institutional,
            cfg.mcie_w_global, cfg.mcie_w_risk,
        ]
        scores_list = [s_regime, s_vola, s_liq, s_part, s_sector, s_inst, s_global, s_risk]
        evidences   = [
            {"regime": regime_str},
            {"vix": vix},
            {"breadth": breadth, "fii_net": fii_net, "dii_net": dii_net},
            {"market_breadth": breadth},
            {"sector_count": len(s_flows), "positive_sectors": pos_secs},
            {"fii_net": fii_net, "dii_net": dii_net},
            {"global_sentiment_score": g_score, "global_bias": g_bias},
            {"pcr": pcr, "vix": vix},
        ]
        explanations = [
            f"regime={regime_str} → clarity={s_regime:.2f}",
            f"VIX={vix:.1f} → volatility_context={s_vola:.2f}",
            f"breadth={breadth:.2f} fii_net={fii_net} → liquidity={s_liq:.2f}",
            f"market_breadth={breadth:.2f} (direct participation)",
            f"{pos_secs}/{len(s_flows)} positive sectors" if s_flows else "no sector data → neutral",
            f"fii_net={fii_net} dii_net={dii_net} → institutional={s_inst:.2f}",
            f"global_sentiment={g_score:.2f} bias={g_bias} → global={s_global:.2f}",
            f"PCR={pcr:.2f} VIX={vix:.1f} → risk={s_risk:.2f}",
        ]

        components = [
            ContextComponent(
                name=_COMPONENT_NAMES[i],
                score=round(scores_list[i], 6),
                weight=weights[i],
                weighted_score=round(scores_list[i] * weights[i], 6),
                confidence=1.0,
                explanation=explanations[i],
                evidence=evidences[i],
            )
            for i in range(8)
        ]

        # ── context_score = weighted sum ──────────────────────────────────────
        context_score = _clamp(sum(c.weighted_score for c in components))

        # ── confidence: data richness ─────────────────────────────────────────
        confidence = _clamp(
            0.60
            + (0.20 if fii_dii is not None else 0.0)
            + (0.20 if s_flows              else 0.0)
        )

        # ── stability: mean per-component delta vs previous context ───────────
        if prev_context is None:
            stability = 0.5
        else:
            prev_scores = {c.name: c.score for c in prev_context.components}
            deltas = [
                abs(c.score - prev_scores[c.name])
                for c in components if c.name in prev_scores
            ]
            stability = _clamp(1.0 - _mean(deltas)) if deltas else 0.5

        # ── raw inputs for full traceability ──────────────────────────────────
        raw_inputs: dict = {
            "regime":                regime_str,
            "vix":                   vix,
            "pcr":                   pcr,
            "market_breadth":        breadth,
            "global_sentiment_score": g_score,
            "global_bias":           str(g_bias or "neutral"),
            "has_fii_data":          fii_dii is not None,
            "fii_net":               fii_net,
            "dii_net":               dii_net,
            "sector_count":          len(s_flows),
            "positive_sectors":      pos_secs,
        }

        context_id = _make_context_id(snapshot.timestamp.isoformat(), as_of)
        summary = (
            f"MarketContext {as_of}: score={context_score:.3f} "
            f"[{regime_str}] "
            f"VIX={vix:.1f} breadth={breadth:.0%} PCR={pcr:.2f} "
            f"confidence={confidence:.0%} stability={stability:.0%} | "
            f"8 dimensions evaluated."
        )

        return MarketContext(
            context_id=context_id,
            evaluation_date=as_of,
            evaluation_time=snapshot.timestamp.isoformat(),
            regime=regime_str,
            context_score=round(context_score, 6),
            confidence=round(confidence, 6),
            stability=round(stability, 6),
            freshness=1.0,
            components=components,
            summary=summary,
            raw_inputs=raw_inputs,
        )

    def _compute_drift(
        self,
        prev: MarketContext,
        curr: MarketContext,
    ) -> ContextDrift:
        score_delta    = curr.context_score - prev.context_score
        regime_changed = prev.regime != curr.regime

        prev_by_name = {c.name: c.score for c in prev.components}
        curr_by_name = {c.name: c.score for c in curr.components}

        thr = self._cfg.mcie_drift_threshold
        drifting = sorted(
            name
            for name in curr_by_name
            if abs(curr_by_name[name] - prev_by_name.get(name, curr_by_name[name])) >= thr
        )

        all_deltas = [
            abs(curr_by_name[n] - prev_by_name.get(n, curr_by_name[n]))
            for n in curr_by_name
        ]
        drift_magnitude = _clamp(_mean(all_deltas))

        regime_part = ""
        if regime_changed:
            regime_part = f"Regime {prev.regime!r} → {curr.regime!r}. "

        explanation = (
            f"Context drift {prev.evaluation_date} → {curr.evaluation_date}. "
            f"Score delta={score_delta:+.3f}. "
            f"{regime_part}"
            f"{len(drifting)} dimension(s) drifted ≥ {thr}."
        )

        return ContextDrift(
            from_date=prev.evaluation_date,
            to_date=curr.evaluation_date,
            score_delta=round(score_delta, 6),
            regime_changed=regime_changed,
            drifting_components=drifting,
            drift_magnitude=round(drift_magnitude, 6),
            explanation=explanation,
        )
