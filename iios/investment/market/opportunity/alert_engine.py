"""iios/investment/market/opportunity/alert_engine.py
Manages alert generation and alert history.
"""
from __future__ import annotations

from collections import deque
from typing import Callable, Iterator, List, Optional

from iios.investment.market.opportunity.models import AlertType, OpportunityAlert


class AlertEngine:
    """Stores alerts and dispatches callbacks."""

    def __init__(self, maxlen: int = 500) -> None:
        self._buffer: deque[OpportunityAlert] = deque(maxlen=maxlen)
        self.on_alert: Optional[Callable[[OpportunityAlert], None]] = None

    def publish(self, alerts: List[OpportunityAlert]) -> None:
        for alert in alerts:
            self._buffer.append(alert)
            if self.on_alert:
                try:
                    self.on_alert(alert)
                except Exception:
                    pass

    def recent(self, n: int) -> List[OpportunityAlert]:
        return list(self._buffer)[-n:]

    def by_type(self, alert_type: AlertType) -> List[OpportunityAlert]:
        return [a for a in self._buffer if a.alert_type is alert_type]

    def for_symbol(self, symbol: str) -> List[OpportunityAlert]:
        return [a for a in self._buffer if a.symbol == symbol]

    def high_severity(self, threshold: float = 0.7) -> List[OpportunityAlert]:
        return [a for a in self._buffer if a.severity >= threshold]

    def __len__(self) -> int:
        return len(self._buffer)

    def __iter__(self) -> Iterator[OpportunityAlert]:
        return iter(self._buffer)
