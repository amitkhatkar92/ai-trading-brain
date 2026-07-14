"""iios/investment/decision/evidence/company_evidence.py
CompanyEvidenceProvider — extracts fundamental company data evidence.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from iios.investment.decision.evidence.evidence_constants import (
    EvidenceCategory, EvidencePriority, EvidenceSourceType,
)
from iios.investment.decision.evidence.evidence_item import make_evidence_item, EvidenceItem
from iios.investment.decision.evidence.evidence_provider import BaseEvidenceProvider


class CompanyEvidenceProvider(BaseEvidenceProvider):

    @property
    def source_type(self) -> EvidenceSourceType:
        return EvidenceSourceType.COMPANY

    @property
    def provider_name(self) -> str:
        return "CompanyEvidenceProvider"

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
        confidence = float(payload.get("confidence", 65.0))

        _fields: List[tuple] = [
            ("pe_ratio",          "pe_ratio",         "x",  EvidenceCategory.FUNDAMENTAL,  EvidencePriority.HIGH,   True),
            ("pb_ratio",          "pb_ratio",         "x",  EvidenceCategory.FUNDAMENTAL,  EvidencePriority.MEDIUM, False),
            ("roe",               "roe",              "%",  EvidenceCategory.FUNDAMENTAL,  EvidencePriority.HIGH,   False),
            ("revenue_growth",    "revenue_growth",   "%",  EvidenceCategory.FUNDAMENTAL,  EvidencePriority.HIGH,   False),
            ("earnings_growth",   "earnings_growth",  "%",  EvidenceCategory.FUNDAMENTAL,  EvidencePriority.HIGH,   False),
            ("debt_equity",       "debt_equity",      "x",  EvidenceCategory.FUNDAMENTAL,  EvidencePriority.MEDIUM, False),
            ("free_cash_flow",    "free_cash_flow",   "cr", EvidenceCategory.FUNDAMENTAL,  EvidencePriority.HIGH,   False),
            ("dividend_yield",    "dividend_yield",   "%",  EvidenceCategory.FUNDAMENTAL,  EvidencePriority.LOW,    False),
            ("market_cap",        "market_cap",       "cr", EvidenceCategory.FUNDAMENTAL,  EvidencePriority.MEDIUM, False),
            ("sector",            "sector",           "",   EvidenceCategory.QUALITATIVE,  EvidencePriority.MEDIUM, False),
            ("management_quality","management_quality","",  EvidenceCategory.QUALITATIVE,  EvidencePriority.MEDIUM, False),
            ("promoter_holding",  "promoter_holding", "%",  EvidenceCategory.QUANTITATIVE, EvidencePriority.MEDIUM, False),
        ]

        for payload_key, ev_key, unit, category, priority, required in _fields:
            if payload_key in payload and payload[payload_key] is not None:
                items.append(make_evidence_item(
                    decision_id=decision_id,
                    source_type=EvidenceSourceType.COMPANY,
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
