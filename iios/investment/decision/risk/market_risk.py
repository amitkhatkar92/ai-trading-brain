"""iios/investment/decision/risk/market_risk.py
MarketRiskEvaluator — derives market-environment risk from EvidenceSnapshot quality.
"""
from __future__ import annotations

import statistics
from dataclasses import dataclass
from typing import Any, Dict, List

from iios.investment.decision.evidence.evidence_constants import EvidenceSourceType
from iios.investment.decision.evidence.evidence_snapshot import EvidenceSnapshot


@dataclass(frozen=True)
class MarketRiskResult:
    evidence_coverage:  float   # 0–1 fraction of expected market items present
    freshness_risk:     float   # 0–100 (100 = very stale market data)
    quality_risk:       float   # 0–100 inverse of market evidence quality
    gap_risk:           float   # 0–100 risk from missing market evidence
    tail_risk:          float   # 0–100 estimated tail risk from low coverage
    market_risk:        float   # 0–100 overall market dimension risk

    def to_dict(self) -> Dict[str, Any]:
        return {
            "evidence_coverage": round(self.evidence_coverage, 4),
            "freshness_risk":    round(self.freshness_risk, 2),
            "quality_risk":      round(self.quality_risk, 2),
            "gap_risk":          round(self.gap_risk, 2),
            "tail_risk":         round(self.tail_risk, 2),
            "market_risk":       round(self.market_risk, 2),
        }


_EXPECTED_MARKET_KEYS = {"last_price", "rsi_14", "volume", "bid_ask_spread", "market_cap"}


class MarketRiskEvaluator:
    """
    Derives market dimension risk from EvidenceSnapshot.
    ONLY consumes Evidence Collection Engine output.
    Does NOT access external market data.
    """

    def evaluate(self, snapshot: EvidenceSnapshot) -> MarketRiskResult:
        market_items = [
            i for i in snapshot.items
            if i.source_type == EvidenceSourceType.MARKET
        ]

        if not market_items:
            # No market evidence = maximum gap risk
            return MarketRiskResult(
                evidence_coverage=0.0,
                freshness_risk=100.0,
                quality_risk=100.0,
                gap_risk=100.0,
                tail_risk=80.0,
                market_risk=95.0,
            )

        # Coverage
        present_keys  = {i.key for i in market_items}
        coverage      = min(1.0, len(present_keys & _EXPECTED_MARKET_KEYS) /
                           max(1, len(_EXPECTED_MARKET_KEYS)))

        # Freshness risk (inverse of freshness)
        avg_freshness = statistics.mean(i.freshness_score for i in market_items)
        freshness_risk = (1.0 - avg_freshness) * 100.0

        # Quality risk (inverse of confidence)
        avg_conf   = statistics.mean(i.confidence for i in market_items)
        quality_risk = max(0.0, 100.0 - avg_conf)

        # Gap risk: penalty for missing expected keys
        missing_fraction = 1.0 - coverage
        gap_risk = missing_fraction * 70.0   # up to 70 points

        # Tail risk: rough proxy — high when few items + low freshness
        tail_risk = max(0.0, (1.0 - coverage) * 50.0 + freshness_risk * 0.3)

        # Composite
        market_risk = (
            freshness_risk * 0.30
            + quality_risk * 0.30
            + gap_risk     * 0.25
            + tail_risk    * 0.15
        )
        market_risk = max(0.0, min(100.0, market_risk))

        return MarketRiskResult(
            evidence_coverage=round(coverage, 4),
            freshness_risk=round(freshness_risk, 4),
            quality_risk=round(quality_risk, 4),
            gap_risk=round(gap_risk, 4),
            tail_risk=round(tail_risk, 4),
            market_risk=round(market_risk, 4),
        )
