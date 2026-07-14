"""iios/investment/decision/evidence/strategy_evidence.py
StrategyEvidenceProvider — extracts strategy performance evidence.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from iios.investment.decision.evidence.evidence_constants import (
    EvidenceCategory, EvidencePriority, EvidenceSourceType,
)
from iios.investment.decision.evidence.evidence_item import EvidenceItem, make_evidence_item
from iios.investment.decision.evidence.evidence_provider import BaseEvidenceProvider


class StrategyEvidenceProvider(BaseEvidenceProvider):

    @property
    def source_type(self) -> EvidenceSourceType:
        return EvidenceSourceType.STRATEGY

    @property
    def provider_name(self) -> str:
        return "StrategyEvidenceProvider"

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
        confidence = float(payload.get("confidence", 72.0))

        _fields: List[tuple] = [
            ("signal_strength",    "signal_strength",   "points", EvidenceCategory.QUANTITATIVE, EvidencePriority.CRITICAL, True),
            ("win_rate",           "win_rate",          "%",      EvidenceCategory.QUANTITATIVE, EvidencePriority.HIGH,     True),
            ("sharpe_ratio",       "sharpe_ratio",      "x",      EvidenceCategory.QUANTITATIVE, EvidencePriority.HIGH,     False),
            ("max_drawdown",       "max_drawdown",      "%",      EvidenceCategory.QUANTITATIVE, EvidencePriority.HIGH,     False),
            ("avg_return",         "avg_return",        "%",      EvidenceCategory.QUANTITATIVE, EvidencePriority.MEDIUM,   False),
            ("regime_fitness",     "regime_fitness",    "points", EvidenceCategory.QUANTITATIVE, EvidencePriority.HIGH,     False),
            ("backtest_trades",    "backtest_trades",   "count",  EvidenceCategory.QUANTITATIVE, EvidencePriority.MEDIUM,   False),
            ("strategy_name",      "strategy_name",     "",       EvidenceCategory.QUALITATIVE,  EvidencePriority.MEDIUM,   False),
            ("last_signal_action", "last_signal_action","",       EvidenceCategory.QUALITATIVE,  EvidencePriority.MEDIUM,   False),
        ]

        for payload_key, ev_key, unit, category, priority, required in _fields:
            if payload_key in payload and payload[payload_key] is not None:
                items.append(make_evidence_item(
                    decision_id=decision_id,
                    source_type=EvidenceSourceType.STRATEGY,
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
