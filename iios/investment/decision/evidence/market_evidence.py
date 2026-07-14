"""iios/investment/decision/evidence/market_evidence.py
MarketEvidenceProvider — extracts market data evidence from an intelligence payload.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from iios.investment.decision.evidence.evidence_constants import (
    EvidenceCategory, EvidencePriority, EvidenceSourceType,
)
from iios.investment.decision.evidence.evidence_item import EvidenceItem, make_evidence_item
from iios.investment.decision.evidence.evidence_provider import BaseEvidenceProvider


class MarketEvidenceProvider(BaseEvidenceProvider):
    """
    Extracts market-related evidence items (price, volume, volatility, momentum).
    Payload format: dict with optional keys produced by market intelligence layers.
    """

    @property
    def source_type(self) -> EvidenceSourceType:
        return EvidenceSourceType.MARKET

    @property
    def provider_name(self) -> str:
        return "MarketEvidenceProvider"

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
        confidence = float(payload.get("confidence", 70.0))

        _scalar_fields: List[tuple] = [
            ("last_price",          "last_price",          "%",      EvidenceCategory.TECHNICAL,    EvidencePriority.CRITICAL,  True),
            ("volume",              "volume",              "shares",  EvidenceCategory.TECHNICAL,    EvidencePriority.HIGH,      False),
            ("avg_volume",          "avg_volume_20d",      "shares",  EvidenceCategory.TECHNICAL,    EvidencePriority.MEDIUM,    False),
            ("implied_volatility",  "implied_volatility",  "%",      EvidenceCategory.QUANTITATIVE, EvidencePriority.HIGH,      False),
            ("beta",                "beta",                "x",      EvidenceCategory.QUANTITATIVE, EvidencePriority.MEDIUM,    False),
            ("rsi_14",              "rsi_14",              "points",  EvidenceCategory.TECHNICAL,    EvidencePriority.MEDIUM,    False),
            ("macd_signal",         "macd_signal",         "",       EvidenceCategory.TECHNICAL,    EvidencePriority.LOW,       False),
            ("52w_high",            "52w_high",            "%",      EvidenceCategory.TECHNICAL,    EvidencePriority.MEDIUM,    False),
            ("52w_low",             "52w_low",             "%",      EvidenceCategory.TECHNICAL,    EvidencePriority.MEDIUM,    False),
            ("regime",              "market_regime",       "",       EvidenceCategory.MACRO,        EvidencePriority.HIGH,      False),
            ("market_breadth",      "market_breadth",      "%",      EvidenceCategory.MACRO,        EvidencePriority.MEDIUM,    False),
        ]

        for payload_key, ev_key, unit, category, priority, required in _scalar_fields:
            if payload_key in payload and payload[payload_key] is not None:
                items.append(make_evidence_item(
                    decision_id=decision_id,
                    source_type=EvidenceSourceType.MARKET,
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
