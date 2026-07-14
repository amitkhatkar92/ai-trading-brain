"""iios/investment/decision/integration/decision_confidence.py
IntegrationConfidenceCalculator — aggregates upstream engine confidences into
one overall integration-level confidence score.
"""
from __future__ import annotations

from iios.investment.decision.integration.aggregation_state import _AggregationStateSnapshot
from iios.investment.decision.integration.integration_constants import (
    CONF_WEIGHT_COMMITTEE,
    CONF_WEIGHT_CONFIDENCE,
    CONF_WEIGHT_EVIDENCE,
    CONF_WEIGHT_REASONING,
    CONF_WEIGHT_RISK,
)


class IntegrationConfidenceCalculator:
    """
    Computes a 0–100 integration-level confidence by weighting the confidence
    signals from each upstream engine.  Missing engines reduce the denominator
    so the score remains calibrated for partial snapshots.
    """

    def calculate(self, snap: _AggregationStateSnapshot) -> float:
        weighted_sum = 0.0
        total_weight = 0.0

        # Evidence — use quality_score × coverage as proxy for confidence contribution
        if snap.evidence is not None:
            ev_conf = snap.evidence.overall_confidence
            weighted_sum += ev_conf * CONF_WEIGHT_EVIDENCE
            total_weight += CONF_WEIGHT_EVIDENCE

        # Reasoning — use is_usable flag; full confidence if usable
        if snap.reasoning is not None:
            rs_conf = 80.0 if snap.reasoning.is_usable else 30.0
            weighted_sum += rs_conf * CONF_WEIGHT_REASONING
            total_weight += CONF_WEIGHT_REASONING

        # Confidence engine — use its own overall_confidence directly
        if snap.confidence is not None:
            cs_conf = snap.confidence.overall_confidence
            weighted_sum += cs_conf * CONF_WEIGHT_CONFIDENCE
            total_weight += CONF_WEIGHT_CONFIDENCE

        # Risk — inverted (low risk → high confidence contribution)
        if snap.risk is not None:
            ri_conf = 100.0 - snap.risk.overall_risk
            weighted_sum += ri_conf * CONF_WEIGHT_RISK
            total_weight += CONF_WEIGHT_RISK

        # Committee — use committee_confidence directly
        if snap.committee is not None:
            cm_conf = getattr(snap.committee, "committee_confidence", 50.0)
            weighted_sum += cm_conf * CONF_WEIGHT_COMMITTEE
            total_weight += CONF_WEIGHT_COMMITTEE

        if total_weight == 0.0:
            return 0.0
        raw = weighted_sum / total_weight
        return max(0.0, min(100.0, raw))
