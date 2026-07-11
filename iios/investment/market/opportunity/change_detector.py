"""iios/investment/market/opportunity/change_detector.py
Detects significant changes in priority, confidence, and lifecycle.
"""
from __future__ import annotations

from typing import Dict, List, Optional

from iios.investment.market.opportunity.models import (
    AlertType,
    Opportunity,
    OpportunityAlert,
    OpportunityLifecycleStage,
    OpportunityPriority,
)

_CONFIDENCE_SURGE_DELTA = 0.15
_CONFIDENCE_DROP_DELTA  = 0.15
_SCORE_CHANGE_THR       = 10.0   # pts


class ChangeDetector:
    """Compares each opportunity against its previous state and generates alerts."""

    def __init__(self) -> None:
        # symbol → (priority, confidence, lifecycle_stage, composite_score)
        self._prev: Dict[str, tuple] = {}

    def detect(
        self,
        opportunities: List[Opportunity],
        bar_index: int,
    ) -> List[OpportunityAlert]:
        alerts: List[OpportunityAlert] = []

        for opp in opportunities:
            prev = self._prev.get(opp.symbol)
            if prev is None:
                # First time seen → new discovery alert
                alerts.append(OpportunityAlert.make(
                    alert_type=AlertType.NEW_OPPORTUNITY,
                    opp=opp,
                    bar_index=bar_index,
                    severity=0.5,
                    description=f"New opportunity discovered: {opp.symbol} ({opp.primary_category.value})",
                ))
            else:
                prev_pri, prev_conf, prev_stage, prev_score = prev

                # Priority change
                if opp.priority != prev_pri:
                    _PRI_ORDER = {
                        OpportunityPriority.LOW: 0,
                        OpportunityPriority.MEDIUM: 1,
                        OpportunityPriority.HIGH: 2,
                        OpportunityPriority.CRITICAL: 3,
                    }
                    upgraded = _PRI_ORDER.get(opp.priority, 0) > _PRI_ORDER.get(prev_pri, 0)
                    at = AlertType.PRIORITY_UPGRADE if upgraded else AlertType.PRIORITY_DOWNGRADE
                    alerts.append(OpportunityAlert.make(
                        alert_type=at,
                        opp=opp,
                        bar_index=bar_index,
                        severity=0.7 if upgraded else 0.6,
                        description=f"{opp.symbol}: priority {prev_pri.value} → {opp.priority.value}",
                        old_value=prev_pri.value,
                        new_value=opp.priority.value,
                    ))

                # Confidence change
                conf_delta = opp.confidence - prev_conf
                if conf_delta >= _CONFIDENCE_SURGE_DELTA:
                    alerts.append(OpportunityAlert.make(
                        alert_type=AlertType.CONFIDENCE_SURGE,
                        opp=opp, bar_index=bar_index, severity=0.6,
                        description=f"{opp.symbol}: confidence +{conf_delta:.0%}",
                        old_value=f"{prev_conf:.2f}",
                        new_value=f"{opp.confidence:.2f}",
                    ))
                elif conf_delta <= -_CONFIDENCE_DROP_DELTA:
                    alerts.append(OpportunityAlert.make(
                        alert_type=AlertType.CONFIDENCE_DROP,
                        opp=opp, bar_index=bar_index, severity=0.6,
                        description=f"{opp.symbol}: confidence {conf_delta:.0%}",
                        old_value=f"{prev_conf:.2f}",
                        new_value=f"{opp.confidence:.2f}",
                    ))

                # Lifecycle change
                if opp.lifecycle_stage != prev_stage:
                    _advanced = {
                        OpportunityLifecycleStage.EMERGING,
                        OpportunityLifecycleStage.GROWING,
                        OpportunityLifecycleStage.HIGH_PRIORITY,
                        OpportunityLifecycleStage.CONFIRMED,
                    }
                    if opp.lifecycle_stage in _advanced:
                        alerts.append(OpportunityAlert.make(
                            alert_type=AlertType.LIFECYCLE_ADVANCE,
                            opp=opp, bar_index=bar_index, severity=0.75,
                            description=f"{opp.symbol}: lifecycle → {opp.lifecycle_stage.value}",
                            old_value=prev_stage.value,
                            new_value=opp.lifecycle_stage.value,
                        ))
                    elif opp.lifecycle_stage in (
                        OpportunityLifecycleStage.WEAKENING,
                        OpportunityLifecycleStage.EXPIRED,
                    ):
                        alerts.append(OpportunityAlert.make(
                            alert_type=AlertType.LIFECYCLE_DECAY
                            if opp.lifecycle_stage is OpportunityLifecycleStage.WEAKENING
                            else AlertType.EXPIRATION,
                            opp=opp, bar_index=bar_index, severity=0.5,
                            description=f"{opp.symbol}: lifecycle → {opp.lifecycle_stage.value}",
                            old_value=prev_stage.value,
                            new_value=opp.lifecycle_stage.value,
                        ))

            # Update state
            self._prev[opp.symbol] = (
                opp.priority, opp.confidence,
                opp.lifecycle_stage, opp.composite_score,
            )

        return alerts
