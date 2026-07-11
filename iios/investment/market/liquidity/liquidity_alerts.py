"""iios/investment/market/liquidity/liquidity_alerts.py
Converts LiquidityEvent objects into LiquidityAlert objects with severity.
"""
from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import ClassVar, Dict, List, Any

from iios.investment.market.liquidity.models import LiquidityEvent, LiquidityEventType

logger = logging.getLogger(__name__)


class AlertSeverity(str, Enum):
    CRITICAL = "critical"
    WARNING  = "warning"
    INFO     = "info"


@dataclass
class LiquidityAlert:
    alert_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    severity: AlertSeverity = AlertSeverity.INFO
    event_type: LiquidityEventType = LiquidityEventType.VOLUME_SPIKE
    symbol: str = ""
    message: str = ""
    timestamp: float = field(default_factory=time.time)
    bar_index: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "alert_id": self.alert_id,
            "severity": self.severity.value,
            "event_type": self.event_type.value,
            "symbol": self.symbol,
            "message": self.message,
            "timestamp": self.timestamp,
            "bar_index": self.bar_index,
        }


class LiquidityAlertGenerator:
    """
    Converts LiquidityEvent objects into LiquidityAlert objects with severity.
    Stateless.
    """

    _SEVERITY_MAP: ClassVar[Dict[LiquidityEventType, AlertSeverity]] = {
        LiquidityEventType.SHOCK:               AlertSeverity.CRITICAL,
        LiquidityEventType.BUYING_CLIMAX:       AlertSeverity.CRITICAL,
        LiquidityEventType.SELLING_CLIMAX:      AlertSeverity.CRITICAL,
        LiquidityEventType.ABSORPTION_DETECTED: AlertSeverity.WARNING,
        LiquidityEventType.VOLUME_SPIKE:        AlertSeverity.WARNING,
        LiquidityEventType.VOLUME_VACUUM:       AlertSeverity.WARNING,
        LiquidityEventType.DRY_UP:              AlertSeverity.WARNING,
        LiquidityEventType.HIGH_PARTICIPATION:  AlertSeverity.INFO,
        LiquidityEventType.LOW_PARTICIPATION:   AlertSeverity.INFO,
        LiquidityEventType.EXPANSION:           AlertSeverity.INFO,
    }

    def generate(self, events: List[LiquidityEvent]) -> List[LiquidityAlert]:
        """Convert events to alerts with appropriate severity."""
        return [self.generate_single(e) for e in events]

    def generate_single(self, event: LiquidityEvent) -> LiquidityAlert:
        severity = self._SEVERITY_MAP.get(event.event_type, AlertSeverity.INFO)
        return LiquidityAlert(
            severity=severity,
            event_type=event.event_type,
            symbol=event.symbol,
            message=event.description or event.event_type.value,
            timestamp=event.timestamp,
            bar_index=event.bar_index,
        )
