"""iios/investment/strategy/opportunity/change_detector.py
ChangeDetector — detects significant changes in market or company
intelligence that should trigger re-evaluation of active opportunities.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union

from iios.investment.strategy.opportunity.market_opportunity import (
    MarketOpportunity, MarketRegime, VolatilityRegime
)
from iios.investment.strategy.opportunity.company_opportunity import CompanyOpportunity


@dataclass(frozen=True)
class ChangeEvent:
    """Describes a detected change in opportunity intelligence."""
    change_id:         str
    source_id:         str       # ID of the changed opportunity
    change_type:       str       # "regime_shift" | "vol_spike" | "sentiment_flip" | etc.
    severity:          str       # "minor" | "moderate" | "major" | "critical"
    description:       str
    previous_value:    Any
    current_value:     Any
    detected_at:       datetime
    requires_reeval:   bool      # True → trigger re-evaluation of active matches

    def to_dict(self) -> Dict[str, Any]:
        return {
            "change_id":       self.change_id,
            "source_id":       self.source_id,
            "change_type":     self.change_type,
            "severity":        self.severity,
            "description":     self.description,
            "previous_value":  str(self.previous_value),
            "current_value":   str(self.current_value),
            "detected_at":     self.detected_at.isoformat(),
            "requires_reeval": self.requires_reeval,
        }


_VOL_SEVERITY = {
    ("low", "moderate"):  ("minor",    False),
    ("low", "high"):      ("major",    True),
    ("low", "extreme"):   ("critical", True),
    ("moderate", "high"): ("moderate", True),
    ("moderate", "extreme"): ("major", True),
    ("high", "extreme"):  ("major",    True),
}

_REGIME_SEVERITY = {
    ("bull", "sideways"):        ("minor",    False),
    ("bull", "bear"):            ("critical", True),
    ("bull", "high_volatility"): ("major",    True),
    ("bear", "bull"):            ("major",    True),
    ("sideways", "bull"):        ("minor",    False),
    ("sideways", "bear"):        ("major",    True),
    ("crisis", "recovery"):      ("major",    True),
}


class ChangeDetector:
    """
    Compares successive snapshots of the same opportunity and emits
    ChangeEvent objects for significant differences.
    Stateless — all state is provided by the caller.
    """

    def detect_market_changes(
        self,
        previous: MarketOpportunity,
        current: MarketOpportunity,
    ) -> List[ChangeEvent]:
        events: List[ChangeEvent] = []

        # Regime change
        if previous.regime != current.regime:
            key = (previous.regime.value, current.regime.value)
            sev, reeval = _REGIME_SEVERITY.get(key, ("moderate", True))
            events.append(self._make_event(
                source_id=current.opportunity_id,
                change_type="regime_shift",
                severity=sev,
                description=f"Market regime shifted: {previous.regime.value} → {current.regime.value}",
                prev=previous.regime.value,
                curr=current.regime.value,
                requires_reeval=reeval,
            ))

        # Volatility change
        if previous.volatility_regime != current.volatility_regime:
            key = (previous.volatility_regime.value, current.volatility_regime.value)
            sev, reeval = _VOL_SEVERITY.get(key, ("moderate", True))
            events.append(self._make_event(
                source_id=current.opportunity_id,
                change_type="volatility_shift",
                severity=sev,
                description=f"Volatility shifted: {previous.volatility_regime.value} → {current.volatility_regime.value}",
                prev=previous.volatility_regime.value,
                curr=current.volatility_regime.value,
                requires_reeval=reeval,
            ))

        # Confidence drop
        conf_delta = current.confidence - previous.confidence
        if conf_delta < -0.20:
            events.append(self._make_event(
                source_id=current.opportunity_id,
                change_type="confidence_drop",
                severity="major" if conf_delta < -0.35 else "moderate",
                description=f"Confidence dropped by {abs(conf_delta):.0%}",
                prev=previous.confidence,
                curr=current.confidence,
                requires_reeval=True,
            ))

        # Direction flip
        if previous.direction != current.direction and current.direction != "neutral":
            events.append(self._make_event(
                source_id=current.opportunity_id,
                change_type="direction_flip",
                severity="critical",
                description=f"Direction flipped: {previous.direction} → {current.direction}",
                prev=previous.direction,
                curr=current.direction,
                requires_reeval=True,
            ))

        return events

    def detect_company_changes(
        self,
        previous: CompanyOpportunity,
        current: CompanyOpportunity,
    ) -> List[ChangeEvent]:
        events: List[ChangeEvent] = []

        # Sentiment flip
        sent_delta = current.sentiment_score - previous.sentiment_score
        if abs(sent_delta) >= 0.30:
            events.append(self._make_event(
                source_id=current.opportunity_id,
                change_type="sentiment_shift",
                severity="major" if abs(sent_delta) >= 0.50 else "moderate",
                description=f"Sentiment shifted by {sent_delta:+.2f}",
                prev=previous.sentiment_score,
                curr=current.sentiment_score,
                requires_reeval=abs(sent_delta) >= 0.50,
            ))

        # Confidence drop
        if current.confidence - previous.confidence < -0.25:
            events.append(self._make_event(
                source_id=current.opportunity_id,
                change_type="confidence_drop",
                severity="major",
                description="Company confidence deteriorated significantly",
                prev=previous.confidence,
                curr=current.confidence,
                requires_reeval=True,
            ))

        return events

    @staticmethod
    def _make_event(
        source_id: str, change_type: str, severity: str,
        description: str, prev: Any, curr: Any, requires_reeval: bool,
    ) -> ChangeEvent:
        import uuid
        return ChangeEvent(
            change_id=str(uuid.uuid4()),
            source_id=source_id,
            change_type=change_type,
            severity=severity,
            description=description,
            previous_value=prev,
            current_value=curr,
            detected_at=datetime.now(timezone.utc),
            requires_reeval=requires_reeval,
        )
