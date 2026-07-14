"""iios/investment/decision/evidence/knowledge_evidence.py
KnowledgeEvidenceProvider — extracts knowledge base evidence.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from iios.investment.decision.evidence.evidence_constants import (
    EvidenceCategory, EvidencePriority, EvidenceSourceType,
)
from iios.investment.decision.evidence.evidence_item import EvidenceItem, make_evidence_item
from iios.investment.decision.evidence.evidence_provider import BaseEvidenceProvider


class KnowledgeEvidenceProvider(BaseEvidenceProvider):

    @property
    def source_type(self) -> EvidenceSourceType:
        return EvidenceSourceType.KNOWLEDGE

    @property
    def provider_name(self) -> str:
        return "KnowledgeEvidenceProvider"

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
        confidence = float(payload.get("confidence", 60.0))

        _fields: List[tuple] = [
            ("industry_outlook",     "industry_outlook",     "",       EvidenceCategory.QUALITATIVE,  EvidencePriority.MEDIUM,      False),
            ("competitive_position", "competitive_position", "points", EvidenceCategory.QUALITATIVE,  EvidencePriority.MEDIUM,      False),
            ("regulatory_risk",      "regulatory_risk",      "points", EvidenceCategory.REGULATORY,   EvidencePriority.MEDIUM,      False),
            ("news_sentiment",       "news_sentiment",       "points", EvidenceCategory.SENTIMENT,    EvidencePriority.MEDIUM,      False),
            ("analyst_consensus",    "analyst_consensus",    "",       EvidenceCategory.QUALITATIVE,  EvidencePriority.LOW,         False),
            ("esg_score",            "esg_score",            "points", EvidenceCategory.ALTERNATIVE,  EvidencePriority.SUPPLEMENTARY, False),
            ("insider_activity",     "insider_activity",     "",       EvidenceCategory.ALTERNATIVE,  EvidencePriority.LOW,         False),
        ]

        for payload_key, ev_key, unit, category, priority, required in _fields:
            if payload_key in payload and payload[payload_key] is not None:
                items.append(make_evidence_item(
                    decision_id=decision_id,
                    source_type=EvidenceSourceType.KNOWLEDGE,
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
