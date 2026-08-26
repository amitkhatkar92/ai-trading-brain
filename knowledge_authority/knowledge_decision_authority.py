"""
knowledge_authority/knowledge_decision_authority.py
=====================================================
KDA-001 — Knowledge Decision Authority

Produces a structured, immutable SHADOW_DECISION record from all available
Knowledge evidence. Runs in shadow mode: complete decision logic, no execution.

Architecture position:
  Knowledge Fusion → KDA → (compared with StrategyLab) → Risk / Execution

StrategyLab is DEMOTED to informational context only. A StrategyLab rejection
must NOT suppress a DECISION_ELIGIBLE Knowledge decision. A StrategyLab pass
does NOT automatically mean Knowledge approval.

SAFETY CONTRACT (never violated):
  broker_calls == 0
  orders == 0
  modifications == 0
  PAPER_TRADING state never read or set
  No imports from: OrderManager, execution_engine, broker APIs, dhan_feed
"""
from __future__ import annotations

import math
import statistics
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from .kda_models import (
    AngleAnalysis,
    AngleVerdict,
    CounterfactualResult,
    DecisionAuthority,
    DecisionOutcome,
    EvidenceHierarchyLevel,
    EvidenceState,
    ExitState,
    InformationContribution,
    KDADecision,
    KDADecisionRecord,
    KDARelationship,
    KnowledgeAuthorityComponents,
    StrategyContext,
)

# ─────────────────────────────────────────────────────────────────────────────
# Evidence state thresholds
# ─────────────────────────────────────────────────────────────────────────────
#
# INSUFFICIENT:      ESS < 3
# DEVELOPING:        ESS 3–9
# USEFUL:            ESS 10–29
# VALIDATED:         ESS 30–99 AND stability satisfactory
# DECISION_ELIGIBLE: ESS ≥ 100 AND stability ≥ 0.6 AND OOS not failed
#                    AND contradiction_factor ≥ 0.4
#
# These thresholds are justified by evidence_tier definitions in hbe_models.py:
#   TIER_1_WEAK (n < 10), TIER_2_DEVELOPING (n < 20), TIER_3_USEFUL (n < 50),
#   TIER_4_STRONG_DEVELOPING (n < 100), TIER_5_STRONG (n < 250)
#
_ESS_DEVELOPING        = 3.0
_ESS_USEFUL            = 10.0
_ESS_VALIDATED         = 30.0
_ESS_DECISION_ELIGIBLE = 100.0

_STABILITY_DECISION_MIN = 0.6    # minimum stability for DECISION_ELIGIBLE
_CONTRADICTION_DECISION_MIN = 0.4  # contradiction_factor must exceed this

# Authority thresholds for decision roles
_AUTHORITY_KNOWLEDGE_MIN = 0.50   # knowledge becomes decision authority
_AUTHORITY_STRATEGY_MIN  = 0.20   # knowledge informs but defers to strategy

# Angle confidence → verdict thresholds
_SUPPORT_THRESHOLD    = 0.55
_CONTRADICT_THRESHOLD = 0.30  # confidence ≤ this AND metric direction opposing

# ATR fallback multipliers (when no empirical evidence)
_ATR_TARGET_MULT = 2.0   # target = entry ± 2×ATR
_ATR_STOP_MULT   = 1.0   # stop   = entry ∓ 1×ATR


# ─────────────────────────────────────────────────────────────────────────────
# Evidence hierarchy order (most → least specific)
# ─────────────────────────────────────────────────────────────────────────────

_HIERARCHY_ORDER: List[EvidenceHierarchyLevel] = [
    EvidenceHierarchyLevel.SYMBOL_DIR_REGIME_CTX,
    EvidenceHierarchyLevel.SYMBOL_DIR,
    EvidenceHierarchyLevel.SECTOR_DIR_REGIME,
    EvidenceHierarchyLevel.REGIME_DIR,
    EvidenceHierarchyLevel.SECTOR_DIR,
    EvidenceHierarchyLevel.BROAD_DIR,
    EvidenceHierarchyLevel.ATR_FALLBACK,
]


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _safe_product(vals: List[float]) -> float:
    """Product of a list of floats, clamped to [0, 1]."""
    result = 1.0
    for v in vals:
        result *= max(0.0, min(1.0, v))
    return result


def _pct(vals: List[float], p: float) -> Optional[float]:
    """p-th percentile of a list (0 ≤ p ≤ 100)."""
    vs = [v for v in vals if v is not None]
    if not vs:
        return None
    vs.sort()
    idx = (p / 100.0) * (len(vs) - 1)
    lo = int(idx)
    hi = min(lo + 1, len(vs) - 1)
    return vs[lo] * (1 - (idx - lo)) + vs[hi] * (idx - lo)


def _oos_quality(oos_status: str) -> float:
    """Convert OOS status string to quality score."""
    return {"PASSED": 0.9, "TESTED": 0.5, "NOT_TESTED": 0.35, "FAILED": 0.05}.get(
        oos_status.upper(), 0.35
    )


# ─────────────────────────────────────────────────────────────────────────────
# KnowledgeDecisionAuthority
# ─────────────────────────────────────────────────────────────────────────────

class KnowledgeDecisionAuthority:
    """
    Produces SHADOW_DECISION records from all available Knowledge evidence.

    Inputs:
      observation      — scanner observation dict (symbol, direction, entry_price, atr, etc.)
      angle_view       — MultiAngleView from KnowledgeFusionEngine (optional)
      behaviour        — BehaviourMetrics from HistoricalBehaviourEngine (optional)
      strategy_context — StrategyLab output dict (optional, informational only)
      market_context   — dict with regime, vix, pcr, breadth

    Output: KDADecisionRecord (immutable, no_lookahead=True, broker_calls=0)
    """

    def evaluate(
        self,
        observation: Dict[str, Any],
        angle_view: Optional[Any] = None,     # MultiAngleView
        behaviour: Optional[Any] = None,       # BehaviourMetrics
        strategy_context: Optional[Dict[str, Any]] = None,
        market_context: Optional[Dict[str, Any]] = None,
    ) -> KDADecisionRecord:
        """
        Full KDA evaluation pipeline.
        Returns a complete SHADOW_DECISION record.
        Never raises — returns a KNOWLEDGE_WAIT record on any unexpected error.
        """
        try:
            return self._evaluate_impl(
                observation, angle_view, behaviour, strategy_context, market_context
            )
        except Exception as exc:
            return self._fallback_record(observation, str(exc))

    # ── Main pipeline ─────────────────────────────────────────────────────────

    def _evaluate_impl(
        self,
        obs:      Dict[str, Any],
        av:       Optional[Any],
        bm:       Optional[Any],
        strat_raw: Optional[Dict[str, Any]],
        mkt:      Optional[Dict[str, Any]],
    ) -> KDADecisionRecord:

        symbol    = str(obs.get("symbol", "UNKNOWN"))
        direction = str(obs.get("direction", "BUY")).upper()
        entry     = float(obs.get("entry_price", 0.0))
        atr       = float(obs.get("atr", 0.0))
        atr_pct   = float(obs.get("atr_pct", 1.0))
        scanner_conf = float(obs.get("scanner_confidence", 0.0))

        mc = mkt or {}
        regime = str(mc.get("regime", "UNKNOWN"))

        # 1. Angle analyses
        angle_analyses = self._evaluate_all_angles(av)

        # 2. Evidence characterisation (from BehaviourMetrics + angles)
        ess          = self._extract_ess(bm)
        stability    = self._extract_stability(bm, angle_analyses)
        oos_status   = self._extract_oos(bm)
        outcome_linked = self._extract_outcome_linked(bm)
        recency_frac = self._extract_recency(angle_analyses)
        source_count = self._count_sources(bm, av)
        contradiction_factor = self._extract_contradiction_factor(angle_analyses)

        # 3. Evidence state
        evidence_state = self._classify_evidence_state(
            ess, stability, oos_status, contradiction_factor
        )

        # 4. Evidence hierarchy level
        evidence_level = self._determine_hierarchy_level(bm, symbol, direction, regime)

        # 5. Authority components
        auth_components = self._compute_authority(
            ess, stability, oos_status, source_count, contradiction_factor, obs, av
        )

        # 6. Supporting / contradicting angles
        supporting  = [n for n, a in angle_analyses.items() if a.verdict == AngleVerdict.SUPPORT]
        contradicting = [n for n, a in angle_analyses.items() if a.verdict == AngleVerdict.CONTRADICT]
        source_agreement = (
            len(supporting) / max(len(angle_analyses), 1) if angle_analyses else 0.0
        )

        # 7. Target / stop / horizon
        target, stop_loss, target_src, stop_src, fallback = self._derive_target_stop(
            bm, entry, atr, direction
        )
        em_p25, em_p50, em_p75 = self._extract_expected_move(bm)
        days_p25, days_p50, days_p75, horizon_src = self._derive_horizon(bm)

        # 8. Decision
        authority_role = self._classify_authority(evidence_state, auth_components)
        decision       = self._determine_decision(
            direction, evidence_state, auth_components, contradicting, supporting
        )

        # 9. StrategyLab context + relationship
        strat_ctx     = self._parse_strategy_context(strat_raw)
        kda_strat_rel = self._classify_relationship(
            decision, evidence_state, auth_components, strat_ctx
        )

        # 10. Information contributions
        contributions = self._compute_contributions(angle_analyses, auth_components)

        # 11. Counterfactual analysis
        counterfactuals = self._compute_counterfactuals(
            angle_analyses, auth_components, decision
        )

        # 12. Exit conditions
        exit_conds = self._derive_exit_conditions(bm, decision, contradicting)

        return KDADecisionRecord(
            decision_id=str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            symbol=symbol,
            direction=direction,
            authority=authority_role,
            decision=decision,
            knowledge_score=scanner_conf,
            knowledge_authority=auth_components.composite_authority,
            evidence_state=evidence_state,
            evidence_level=evidence_level,
            evidence_count=int(ess) if bm is not None else 0,
            effective_sample_size=ess,
            evidence_confidence=auth_components.evidence_strength,
            expected_move_p25=em_p25,
            expected_move_p50=em_p50,
            expected_move_p75=em_p75,
            target=target,
            stop_loss=stop_loss,
            expected_days_p25=days_p25,
            expected_days_p50=days_p50,
            expected_days_p75=days_p75,
            target_source=target_src,
            stop_source=stop_src,
            horizon_source=horizon_src,
            supporting_angles=supporting,
            contradicting_angles=contradicting,
            source_count=source_count,
            source_agreement=round(source_agreement, 4),
            contradiction_status=self._summarise_contradiction(contradicting),
            oos_status=oos_status,
            strategy_context=strat_ctx,
            kda_strategy_relationship=kda_strat_rel,
            risk_constraints=self._extract_risk_constraints(mc),
            fallback_used=fallback,
            authority_components=auth_components,
            angle_analyses=angle_analyses,
            information_contributions=contributions,
            counterfactual_results=counterfactuals,
            exit_conditions=exit_conds,
            opportunity_id=str(obs.get("opportunity_id", "") or ""),
        )

    # ── Angle evaluation ──────────────────────────────────────────────────────

    def _evaluate_all_angles(
        self, av: Optional[Any]
    ) -> Dict[str, AngleAnalysis]:
        if av is None:
            return {}
        result: Dict[str, AngleAnalysis] = {}
        for name, angle_result in (av.angles or {}).items():
            result[name] = self._evaluate_angle(name, angle_result)
        return result

    def _evaluate_angle(self, name: str, ar: Any) -> AngleAnalysis:
        conf   = float(getattr(ar, "confidence", 0.0))
        n      = int(getattr(ar, "sample_count", 0))
        metrics = dict(getattr(ar, "metrics", {}) or {})
        summary = str(getattr(ar, "summary", ""))

        # CONTRADICTION angle with n=0 = no contradictions found → still meaningful
        is_insufficient = (n == 0 and name != "CONTRADICTION") or conf < 0.05
        if is_insufficient:
            verdict = AngleVerdict.INSUFFICIENT
        else:
            verdict = self._classify_angle_verdict(name, conf, metrics, n)

        return AngleAnalysis(
            angle_name=name,
            verdict=verdict,
            confidence=round(conf, 4),
            sample_count=n,
            summary=summary,
            metrics=metrics,
        )

    def _classify_angle_verdict(
        self, name: str, conf: float, metrics: Dict[str, Any], n: int = 0
    ) -> AngleVerdict:
        """Map angle name + confidence + metrics to SUPPORT/NEUTRAL/CONTRADICT."""
        # Explicit major contradiction in metrics always → CONTRADICT regardless of confidence
        if metrics.get("major", 0) > 0:
            return AngleVerdict.CONTRADICT

        if conf >= _SUPPORT_THRESHOLD:
            # Angles where high confidence directly means SUPPORT
            if name in ("STOCK", "SECTOR", "VOLATILITY", "DIRECTION",
                        "LEADER_OUTCOME", "SOURCE_QUALITY", "REDUNDANCY"):
                return AngleVerdict.SUPPORT

            if name == "CONTRADICTION":
                # High confidence + 0 contradictions = SUPPORT
                n_minor = metrics.get("minor", 0)
                return AngleVerdict.NEUTRAL if n_minor > 0 else AngleVerdict.SUPPORT

            if name == "OOS_VALIDATION":
                rate = metrics.get("oos_pass_rate")
                if rate is None:
                    return AngleVerdict.NEUTRAL
                return AngleVerdict.SUPPORT if rate >= 0.6 else (
                    AngleVerdict.CONTRADICT if rate < 0.3 else AngleVerdict.NEUTRAL
                )

            if name == "RECENCY":
                ess_frac = metrics.get("ess_fraction", 0.0)
                return AngleVerdict.SUPPORT if ess_frac >= 0.5 else AngleVerdict.NEUTRAL

            return AngleVerdict.NEUTRAL

        elif conf < 0.20 and n >= 10:
            # Low confidence with sufficient sample → evidence actively opposing
            if name in ("STOCK", "SECTOR", "DIRECTION", "VOLATILITY", "LEADER_OUTCOME"):
                return AngleVerdict.CONTRADICT
            if name == "OOS_VALIDATION":
                rate = metrics.get("oos_pass_rate")
                if rate is not None and rate < 0.3:
                    return AngleVerdict.CONTRADICT
            return AngleVerdict.NEUTRAL

        elif conf <= _CONTRADICT_THRESHOLD and conf > 0.05:
            # Borderline low confidence: contradict only with explicit negative signal
            if name in ("STOCK", "SECTOR", "DIRECTION"):
                win_rate = metrics.get("win_rate", metrics.get("positive_rate"))
                if win_rate is not None and win_rate < 0.35:
                    return AngleVerdict.CONTRADICT
            return AngleVerdict.NEUTRAL
        else:
            return AngleVerdict.NEUTRAL

    # ── Evidence extraction from BehaviourMetrics ────────────────────────────

    def _extract_ess(self, bm: Optional[Any]) -> float:
        if bm is None:
            return 0.0
        return float(getattr(bm, "effective_sample_size", 0.0) or 0.0)

    def _extract_stability(
        self, bm: Optional[Any], angles: Dict[str, AngleAnalysis]
    ) -> float:
        """Stability score 0–1 from BehaviourMetrics and angle confidences."""
        if bm is not None:
            target_prob = getattr(bm, "target_hit_probability", None)
            stop_prob   = getattr(bm, "stop_first_probability", None)
            if target_prob is not None and stop_prob is not None:
                # Consistency: larger margin between target and stop = more stable
                margin = abs(target_prob - stop_prob)
                return min(0.5 + margin * 0.5, 1.0)

        # Fall back to STOCK angle confidence
        stock = angles.get("STOCK")
        if stock and stock.confidence > 0:
            return stock.confidence
        return 0.3  # default neutral stability

    def _extract_oos(self, bm: Optional[Any]) -> str:
        if bm is None:
            return "NOT_TESTED"
        ts = getattr(bm, "target_source", "ATR_FALLBACK")
        # A BehaviourMetrics with EMPIRICAL target has been through real observations
        # OOS is tracked at KnowledgeObject level; here we use a proxy
        return "TESTED" if ts == "EMPIRICAL" else "NOT_TESTED"

    def _extract_outcome_linked(self, bm: Optional[Any]) -> int:
        if bm is None:
            return 0
        return int(getattr(bm, "relevant_sample_size", 0) or 0)

    def _extract_recency(self, angles: Dict[str, AngleAnalysis]) -> float:
        rec = angles.get("RECENCY")
        if rec:
            return rec.metrics.get("ess_fraction", 0.5)
        return 0.5

    def _count_sources(self, bm: Optional[Any], av: Optional[Any]) -> int:
        """Count distinct knowledge sources contributing to this evaluation."""
        count = 0
        if bm is not None:
            count += 1  # HBE
        if av is not None:
            # Each non-INSUFFICIENT angle is an independent source signal
            count += sum(
                1 for name in (av.angles or {})
                if name in ("STOCK", "SECTOR", "MARKET", "LEADER_OUTCOME",
                             "REJECTION_AUDIT", "SHADOW_EVIDENCE")
            )
        return max(count, 1)

    def _extract_contradiction_factor(
        self, angles: Dict[str, AngleAnalysis]
    ) -> float:
        n_major = sum(
            1 for a in angles.values() if a.verdict == AngleVerdict.CONTRADICT
            and a.metrics.get("major", 0) > 0
        )
        n_minor = sum(
            1 for a in angles.values() if a.verdict == AngleVerdict.CONTRADICT
            and a.metrics.get("major", 0) == 0
        )
        raw = 1.0 - n_major * 0.35 - n_minor * 0.12
        return max(raw, 0.0)

    # ── Evidence state classification ──────────────────────────────────────────

    def _classify_evidence_state(
        self,
        ess: float,
        stability: float,
        oos_status: str,
        contradiction_factor: float,
    ) -> EvidenceState:
        if ess < _ESS_DEVELOPING:
            return EvidenceState.INSUFFICIENT
        if ess < _ESS_USEFUL:
            return EvidenceState.DEVELOPING
        if ess < _ESS_VALIDATED:
            return EvidenceState.USEFUL
        if ess < _ESS_DECISION_ELIGIBLE:
            return EvidenceState.VALIDATED
        # DECISION_ELIGIBLE requires: ESS ≥ 100, stability ≥ 0.6,
        # OOS not failed, contradiction controlled
        if (stability >= _STABILITY_DECISION_MIN
                and oos_status.upper() != "FAILED"
                and contradiction_factor >= _CONTRADICTION_DECISION_MIN):
            return EvidenceState.DECISION_ELIGIBLE
        return EvidenceState.VALIDATED

    # ── Evidence hierarchy level ───────────────────────────────────────────────

    def _determine_hierarchy_level(
        self, bm: Optional[Any], symbol: str, direction: str, regime: str
    ) -> EvidenceHierarchyLevel:
        if bm is None:
            return EvidenceHierarchyLevel.ATR_FALLBACK
        src = str(getattr(bm, "evidence_source", "") or "")
        mapping = {
            "SYMBOL_DIRECTION_REGIME": EvidenceHierarchyLevel.SYMBOL_DIR_REGIME_CTX,
            "SYMBOL_DIRECTION":        EvidenceHierarchyLevel.SYMBOL_DIR,
            "SECTOR_DIRECTION_REGIME": EvidenceHierarchyLevel.SECTOR_DIR_REGIME,
            "SECTOR_DIRECTION":        EvidenceHierarchyLevel.SECTOR_DIR,
            "REGIME_DIRECTION":        EvidenceHierarchyLevel.REGIME_DIR,
            "BROAD_DIRECTION":         EvidenceHierarchyLevel.BROAD_DIR,
        }
        return mapping.get(src.upper(), EvidenceHierarchyLevel.ATR_FALLBACK)

    # ── Authority computation ──────────────────────────────────────────────────

    def _compute_authority(
        self,
        ess:                  float,
        stability:            float,
        oos_status:           str,
        source_count:         int,
        contradiction_factor: float,
        obs:                  Dict[str, Any],
        av:                   Optional[Any],
    ) -> KnowledgeAuthorityComponents:
        evidence_strength = min(ess / _ESS_DECISION_ELIGIBLE, 1.0)

        # Relevance: scanner confidence / 10, bounded
        scanner_conf = float(obs.get("scanner_confidence", 0.0))
        relevance = min(max(scanner_conf / 10.0, 0.1), 1.0)

        oos_q = _oos_quality(oos_status)

        # Source independence: needs at least 3 truly distinct sources for full score
        src_indep = min(source_count / 4.0, 1.0)

        composite = _safe_product([
            evidence_strength,
            relevance,
            stability,
            oos_q,
            src_indep,
            contradiction_factor,
        ])

        return KnowledgeAuthorityComponents(
            evidence_strength=round(evidence_strength, 4),
            relevance=round(relevance, 4),
            stability=round(stability, 4),
            oos_quality=round(oos_q, 4),
            source_independence=round(src_indep, 4),
            contradiction_factor=round(contradiction_factor, 4),
            composite_authority=round(composite, 4),
        )

    # ── Decision logic ────────────────────────────────────────────────────────

    def _classify_authority(
        self,
        evidence_state: EvidenceState,
        components:     KnowledgeAuthorityComponents,
    ) -> DecisionAuthority:
        # ARCH-005: KDA is the intelligence authority for all non-insufficient states.
        # Authority ROLE = KNOWLEDGE (architecture decision, not a data threshold).
        # composite_authority score captures evidence quality separately.
        if evidence_state != EvidenceState.INSUFFICIENT:
            return DecisionAuthority.KNOWLEDGE
        return DecisionAuthority.NONE

    def _determine_decision(
        self,
        direction:      str,
        evidence_state: EvidenceState,
        components:     KnowledgeAuthorityComponents,
        contradicting:  List[str],
        supporting:     List[str],
    ) -> KDADecision:
        # ARCH-005: KNOWLEDGE_WAIT only for truly insufficient evidence (no basis for decision).
        if evidence_state == EvidenceState.INSUFFICIENT:
            return KDADecision.KNOWLEDGE_WAIT

        n_contradict = len(contradicting)
        n_support    = len(supporting)

        # Material conflict: evidence reviewed but actively contradicted → HOLD.
        # StrategyLab cannot override a KDA HOLD (spec: KDA rejects = StrategyLab blocked).
        if n_contradict > n_support and n_contradict >= 3:
            return KDADecision.KNOWLEDGE_HOLD

        # For ALL non-insufficient states with no material conflict, KDA expresses a
        # directional view. evidence_state remains visible on the record to show quality.
        # DEVELOPING: ATR fallback target/stop.  USEFUL+: mixed empirical/ATR.
        # DECISION_ELIGIBLE: empirical when available.
        if direction.upper() in ("BUY", "LONG"):
            return KDADecision.KNOWLEDGE_BUY
        if direction.upper() in ("SELL", "SHORT"):
            return KDADecision.KNOWLEDGE_SELL

        return KDADecision.KNOWLEDGE_HOLD  # unknown direction fallback

    # ── Target / stop derivation ───────────────────────────────────────────────

    def _derive_target_stop(
        self,
        bm:        Optional[Any],
        entry:     float,
        atr:       float,
        direction: str,
    ) -> Tuple[Optional[float], Optional[float], str, str, bool]:
        """
        Returns (target, stop_loss, target_source, stop_source, fallback_used).
        Uses empirical offsets from BehaviourMetrics when available;
        falls back to ATR multiples otherwise.
        """
        is_long = direction.upper() in ("BUY", "LONG")

        if bm is not None:
            tgt_offset = getattr(bm, "knowledge_target_offset_p50", None)
            stp_offset = getattr(bm, "knowledge_stop_offset_p50", None)
            tgt_src    = str(getattr(bm, "target_source", "ATR_FALLBACK"))
            stp_src    = str(getattr(bm, "stop_source",   "ATR_FALLBACK"))

            if tgt_offset is not None and stp_offset is not None and tgt_src == "EMPIRICAL":
                if entry > 0:
                    mul = 1 if is_long else -1
                    target   = round(entry * (1 + mul * tgt_offset / 100.0), 2)
                    stop_loss = round(entry * (1 - mul * abs(stp_offset) / 100.0), 2)
                    return target, stop_loss, "EMPIRICAL", "EMPIRICAL", False

        if entry > 0 and atr > 0:
            mul = 1 if is_long else -1
            target    = round(entry + mul * _ATR_TARGET_MULT * atr, 2)
            stop_loss = round(entry - mul * _ATR_STOP_MULT  * atr, 2)
            return target, stop_loss, "ATR_FALLBACK", "ATR_FALLBACK", True

        return None, None, "NONE", "NONE", True

    def _extract_expected_move(
        self, bm: Optional[Any]
    ) -> Tuple[Optional[float], Optional[float], Optional[float]]:
        if bm is None:
            return None, None, None
        return (
            getattr(bm, "expected_move_p25", None),
            getattr(bm, "expected_move_p50", None),
            getattr(bm, "expected_move_p75", None),
        )

    def _derive_horizon(
        self, bm: Optional[Any]
    ) -> Tuple[Optional[float], Optional[float], Optional[float], str]:
        if bm is None:
            return None, None, None, "UNKNOWN"
        p25 = getattr(bm, "expected_days_p25", None)
        p50 = getattr(bm, "expected_days_p50", None)
        p75 = getattr(bm, "expected_days_p75", None)
        src = "EMPIRICAL" if any(v is not None for v in (p25, p50, p75)) else "UNKNOWN"
        return p25, p50, p75, src

    # ── StrategyLab context ───────────────────────────────────────────────────

    def _parse_strategy_context(
        self, raw: Optional[Dict[str, Any]]
    ) -> Optional[StrategyContext]:
        if raw is None:
            return None
        return StrategyContext(
            status=str(raw.get("status", "UNKNOWN")).upper(),
            strategy_name=raw.get("strategy_name"),
            disagreement=raw.get("disagreement"),
            informational_only=True,
        )

    def _classify_relationship(
        self,
        decision:       KDADecision,
        evidence_state: EvidenceState,
        components:     KnowledgeAuthorityComponents,
        strat:          Optional[StrategyContext],
    ) -> str:
        if strat is None:
            return KDARelationship.KNOWLEDGE_INSUFFICIENT.value

        if evidence_state in (EvidenceState.INSUFFICIENT, EvidenceState.DEVELOPING):
            return KDARelationship.KNOWLEDGE_INSUFFICIENT.value

        strat_approved = strat.status.upper() == "PASS"
        kda_directional = decision in (KDADecision.KNOWLEDGE_BUY, KDADecision.KNOWLEDGE_SELL)

        if strat_approved and kda_directional:
            return KDARelationship.KNOWLEDGE_AGREES.value

        if not strat_approved and not kda_directional:
            return KDARelationship.KNOWLEDGE_AGREES.value

        if (kda_directional and not strat_approved
                and evidence_state == EvidenceState.DECISION_ELIGIBLE):
            return KDARelationship.KNOWLEDGE_OVERRULES_STRATEGY.value

        if not kda_directional and strat_approved:
            return KDARelationship.STRATEGY_OVERRULES_KNOWLEDGE.value

        if kda_directional and not strat_approved:
            return KDARelationship.KNOWLEDGE_DISAGREES.value

        return KDARelationship.KNOWLEDGE_CONFLICTED.value

    # ── Information contributions ─────────────────────────────────────────────

    def _compute_contributions(
        self,
        angle_analyses: Dict[str, AngleAnalysis],
        auth:           KnowledgeAuthorityComponents,
    ) -> List[InformationContribution]:
        contributions: List[InformationContribution] = []
        for name, aa in angle_analyses.items():
            if aa.verdict == AngleVerdict.INSUFFICIENT:
                continue
            sign = 1.0 if aa.verdict == AngleVerdict.SUPPORT else (
                -1.0 if aa.verdict == AngleVerdict.CONTRADICT else 0.0
            )
            value = aa.confidence * abs(sign)
            contributions.append(InformationContribution(
                source=name,
                angle=name,
                contribution=round(sign * value, 4),
                direction=aa.verdict.value,
                value=round(value, 4),
            ))
        return sorted(contributions, key=lambda c: abs(c.contribution), reverse=True)

    # ── Counterfactual analysis ───────────────────────────────────────────────

    def _compute_counterfactuals(
        self,
        angle_analyses: Dict[str, AngleAnalysis],
        auth:           KnowledgeAuthorityComponents,
        decision:       KDADecision,
    ) -> List[CounterfactualResult]:
        """
        For each supporting/contradicting angle, compute the decision
        and authority if that source were removed.

        Does NOT double-count redundant sources (skips NEUTRAL angles).
        """
        results: List[CounterfactualResult] = []
        base_auth = auth.composite_authority

        active_angles = {
            n: a for n, a in angle_analyses.items()
            if a.verdict in (AngleVerdict.SUPPORT, AngleVerdict.CONTRADICT)
        }

        for removed_name in active_angles:
            remaining = {n: a for n, a in active_angles.items() if n != removed_name}

            n_support    = sum(1 for a in remaining.values() if a.verdict == AngleVerdict.SUPPORT)
            n_contradict = sum(1 for a in remaining.values() if a.verdict == AngleVerdict.CONTRADICT)

            # Re-estimate contradiction_factor without this source
            cf_without = auth.contradiction_factor
            removed = active_angles[removed_name]
            if removed.verdict == AngleVerdict.CONTRADICT:
                cf_without = min(cf_without + 0.12, 1.0)  # fewer contradictions → higher

            auth_without = round(base_auth / max(auth.contradiction_factor, 0.01) * cf_without, 4)
            auth_without = min(auth_without, 1.0)

            dec_without = self._determine_decision(
                "BUY",  # direction proxy
                EvidenceState.VALIDATED if auth_without >= 0.3 else EvidenceState.DEVELOPING,
                KnowledgeAuthorityComponents(
                    evidence_strength=auth.evidence_strength,
                    relevance=auth.relevance,
                    stability=auth.stability,
                    oos_quality=auth.oos_quality,
                    source_independence=auth.source_independence,
                    contradiction_factor=cf_without,
                    composite_authority=auth_without,
                ),
                [n for n, a in remaining.items() if a.verdict == AngleVerdict.CONTRADICT],
                [n for n, a in remaining.items() if a.verdict == AngleVerdict.SUPPORT],
            )

            results.append(CounterfactualResult(
                source_removed=removed_name,
                decision_with=decision.value,
                decision_without=dec_without.value,
                authority_with=round(base_auth, 4),
                authority_without=auth_without,
                delta=round(base_auth - auth_without, 4),
            ))

        return sorted(results, key=lambda r: abs(r.delta), reverse=True)

    # ── Exit conditions ────────────────────────────────────────────────────────

    def _derive_exit_conditions(
        self,
        bm:           Optional[Any],
        decision:     KDADecision,
        contradicting: List[str],
    ) -> List[str]:
        exits: List[str] = []
        if decision in (KDADecision.KNOWLEDGE_BUY, KDADecision.KNOWLEDGE_SELL):
            exits += [ExitState.TARGET_REACHED.value, ExitState.STOP_REACHED.value]
            exits.append(ExitState.THESIS_INVALIDATED.value)
        if len(contradicting) >= 3:
            exits.append(ExitState.KNOWLEDGE_CONTRADICTION.value)
        exits.append(ExitState.RISK_OVERRIDE.value)
        if bm is not None:
            p75 = getattr(bm, "expected_days_p75", None)
            if p75 is not None:
                exits.append(ExitState.TIME_DECAY.value)
        return exits

    # ── Utilities ─────────────────────────────────────────────────────────────

    def _summarise_contradiction(self, contradicting: List[str]) -> str:
        n = len(contradicting)
        if n == 0:
            return "NONE"
        if n == 1:
            return "MINOR"
        if n >= 3:
            return "MAJOR"
        return "MODERATE"

    def _extract_risk_constraints(self, mc: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "vix":     mc.get("vix"),
            "regime":  mc.get("regime"),
            "breadth": mc.get("breadth"),
            "pcr":     mc.get("pcr"),
        }

    def _fallback_record(self, obs: Dict[str, Any], error: str) -> KDADecisionRecord:
        null_auth = KnowledgeAuthorityComponents(
            evidence_strength=0.0, relevance=0.0, stability=0.0,
            oos_quality=0.0, source_independence=0.0, contradiction_factor=0.0,
            composite_authority=0.0,
        )
        return KDADecisionRecord(
            decision_id=str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            symbol=str(obs.get("symbol", "UNKNOWN")),
            direction=str(obs.get("direction", "BUY")),
            authority=DecisionAuthority.NONE,
            decision=KDADecision.KNOWLEDGE_WAIT,
            knowledge_score=0.0,
            knowledge_authority=0.0,
            evidence_state=EvidenceState.INSUFFICIENT,
            evidence_level=EvidenceHierarchyLevel.ATR_FALLBACK,
            evidence_count=0,
            effective_sample_size=0.0,
            evidence_confidence=0.0,
            expected_move_p25=None, expected_move_p50=None, expected_move_p75=None,
            target=None, stop_loss=None,
            expected_days_p25=None, expected_days_p50=None, expected_days_p75=None,
            target_source="NONE", stop_source="NONE", horizon_source="UNKNOWN",
            supporting_angles=[], contradicting_angles=[],
            source_count=0, source_agreement=0.0,
            contradiction_status="NONE", oos_status="NOT_TESTED",
            strategy_context=None,
            kda_strategy_relationship=KDARelationship.KNOWLEDGE_INSUFFICIENT.value,
            risk_constraints={}, fallback_used=True,
            authority_components=null_auth,
            angle_analyses={}, information_contributions=[], counterfactual_results=[],
            exit_conditions=[ExitState.RISK_OVERRIDE.value],
        )
