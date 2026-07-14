"""iios/investment/decision/evidence/research_evidence.py
ResearchEvidenceProvider — extracts research-derived evidence items.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from iios.investment.decision.evidence.evidence_constants import (
    EvidenceCategory, EvidencePriority, EvidenceSourceType,
)
from iios.investment.decision.evidence.evidence_item import EvidenceItem, make_evidence_item
from iios.investment.decision.evidence.evidence_provider import BaseEvidenceProvider


class ResearchEvidenceProvider(BaseEvidenceProvider):

    @property
    def source_type(self) -> EvidenceSourceType:
        return EvidenceSourceType.RESEARCH

    @property
    def provider_name(self) -> str:
        return "ResearchEvidenceProvider"

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
        confidence = float(payload.get("confidence", 62.0))

        _fields: List[tuple] = [
            ("target_price",     "target_price",     "%",      EvidenceCategory.FUNDAMENTAL,  EvidencePriority.HIGH,        False),
            ("analyst_rating",   "analyst_rating",   "",       EvidenceCategory.QUALITATIVE,  EvidencePriority.MEDIUM,      False),
            ("research_score",   "research_score",   "points", EvidenceCategory.QUANTITATIVE, EvidencePriority.HIGH,        False),
            ("catalyst_count",   "catalyst_count",   "count",  EvidenceCategory.QUALITATIVE,  EvidencePriority.MEDIUM,      False),
            ("publication_count","publication_count","count",  EvidenceCategory.QUALITATIVE,  EvidencePriority.SUPPLEMENTARY, False),
            ("consensus_eps",    "consensus_eps",    "rs",     EvidenceCategory.FUNDAMENTAL,  EvidencePriority.MEDIUM,      False),
        ]

        for payload_key, ev_key, unit, category, priority, required in _fields:
            if payload_key in payload and payload[payload_key] is not None:
                items.append(make_evidence_item(
                    decision_id=decision_id,
                    source_type=EvidenceSourceType.RESEARCH,
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
