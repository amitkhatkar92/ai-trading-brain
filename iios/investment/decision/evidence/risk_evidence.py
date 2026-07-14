"""iios/investment/decision/evidence/risk_evidence.py
RiskEvidenceProvider — extracts risk assessment evidence.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from iios.investment.decision.evidence.evidence_constants import (
    EvidenceCategory, EvidencePriority, EvidenceSourceType,
)
from iios.investment.decision.evidence.evidence_item import EvidenceItem, make_evidence_item
from iios.investment.decision.evidence.evidence_provider import BaseEvidenceProvider


class RiskEvidenceProvider(BaseEvidenceProvider):

    @property
    def source_type(self) -> EvidenceSourceType:
        return EvidenceSourceType.RISK

    @property
    def provider_name(self) -> str:
        return "RiskEvidenceProvider"

    def collect(
        self,
        decision_id:  str,
        subject_id:   str,
        subject_type: str,
        payload:      Optional[Dict[str, Any]] = None,
    ) -> List[EvidenceItem]:
        if not payload:
            return []

        items: List[EvidenceItem] = []
        confidence = float(payload.get("confidence", 78.0))

        _fields: List[tuple] = [
            ("risk_score",          "risk_score",          "points", EvidenceCategory.QUANTITATIVE, EvidencePriority.CRITICAL, True),
            ("portfolio_risk_pct",  "portfolio_risk_pct",  "%",      EvidenceCategory.QUANTITATIVE, EvidencePriority.CRITICAL, True),
            ("var_95",              "var_95",              "%",      EvidenceCategory.QUANTITATIVE, EvidencePriority.HIGH,     False),
            ("correlation_risk",    "correlation_risk",    "x",      EvidenceCategory.QUANTITATIVE, EvidencePriority.HIGH,     False),
            ("concentration_risk",  "concentration_risk",  "%",      EvidenceCategory.QUANTITATIVE, EvidencePriority.MEDIUM,   False),
            ("stress_test_result",  "stress_test_result",  "points", EvidenceCategory.QUANTITATIVE, EvidencePriority.HIGH,     False),
            ("liquidity_risk",      "liquidity_risk",      "points", EvidenceCategory.QUANTITATIVE, EvidencePriority.MEDIUM,   False),
            ("position_size_limit", "position_size_limit", "%",      EvidenceCategory.QUANTITATIVE, EvidencePriority.HIGH,     False),
        ]

        for payload_key, ev_key, unit, category, priority, required in _fields:
            if payload_key in payload and payload[payload_key] is not None:
                items.append(make_evidence_item(
                    decision_id=decision_id,
                    source_type=EvidenceSourceType.RISK,
                    source_provider=self.provider_name,
                    subject_id=subject_id,
                    subject_type=subject_type,
                    category=category,
                    key=ev_key,
                    value=payload[payload_key],
                    unit=unit,
                    confidence=confidence,
                    priority=priority,
                    is_required=required,
                    trace_id=payload.get("trace_id"),
                ))
        return items
