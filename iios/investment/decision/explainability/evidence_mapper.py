"""iios/investment/decision/explainability/evidence_mapper.py
EvidenceMapper — maps EvidenceSnapshot items to their traceability nodes.
"""
from __future__ import annotations

from typing import List

from iios.investment.decision.evidence.evidence_snapshot import EvidenceSnapshot
from iios.investment.decision.explainability.decision_trace import EvidenceTraceNode


_HIGH_IMPACT_KEYS = frozenset({
    "last_price", "pe_ratio", "roe", "win_rate", "sharpe_ratio",
    "earnings_growth", "revenue_growth", "rsi_14", "market_cap",
    "signal_strength", "bid_ask_spread",
})


class EvidenceMapper:
    """Maps EvidenceSnapshot items to EvidenceTraceNodes."""

    def map(
        self,
        snapshot: EvidenceSnapshot,
        reasoned_keys: frozenset | None = None,
    ) -> List[EvidenceTraceNode]:
        """
        Build trace nodes for all evidence items.

        Args:
            snapshot: the upstream EvidenceSnapshot
            reasoned_keys: set of evidence keys that appear in reasoning steps
                           (from ReasoningMapper). None = mark all as unknown.
        """
        if reasoned_keys is None:
            reasoned_keys = frozenset()

        nodes: List[EvidenceTraceNode] = []
        total_items = max(1, snapshot.item_count)

        for item in snapshot.items:
            # Estimate impact: high-impact keys + confidence + freshness
            base = 60.0 if item.key in _HIGH_IMPACT_KEYS else 30.0
            impact = min(100.0, base * (item.confidence / 100.0) * item.freshness_score + base * 0.2)
            nodes.append(EvidenceTraceNode(
                item_key=item.key,
                source_type=item.source_type.value,
                confidence=item.confidence,
                freshness_score=item.freshness_score,
                impact_score=round(impact, 4),
                reasoning_referenced=item.key in reasoned_keys,
            ))

        return nodes
