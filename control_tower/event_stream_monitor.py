"""
Event Stream Monitor — Control Tower Module 2
=============================================
Maintains a live timeline of every event in the current cycle.
Pure in-memory; the TelemetryLogger handles persistence.

Provides:
  - get_timeline()         → last N events as list[dict]
  - get_current_cycle_id() → current cycle identifier string
  - get_cycle_summary()    → short stats dict for the banner row
"""

from __future__ import annotations

import threading
from collections import deque
from typing import Any, Deque, Dict, List, Optional

from communication.events import Event, EventType
from utils import get_logger

log = get_logger(__name__)

_TIMELINE_SIZE = 200   # events to keep in memory per session


class EventStreamMonitor:
    """
    Lightweight in-memory event timeline observer.

    Subscribes to '*' and records a short human-readable summary
    for every event so the dashboard can show a live feed.
    """

    def __init__(self, bus) -> None:
        self._lock           = threading.Lock()
        self._timeline: Deque[Dict[str, Any]] = deque(maxlen=_TIMELINE_SIZE)
        self._current_cycle  = ""
        self._cycle_start_ts = ""
        self._event_count    = 0
        self._error_count    = 0
        self._last_regime    = "UNKNOWN"
        self._last_vix       = 0.0

        bus.subscribe("*", self._on_event,
                      agent_name="ControlTower.EventStreamMonitor", priority=98)
        log.info("[EventStreamMonitor] Initialised.")

    # ── Public API ─────────────────────────────────────────────────────────

    def get_timeline(self, n: int = 50) -> List[Dict[str, Any]]:
        """Return last n timeline entries (newest last)."""
        with self._lock:
            items = list(self._timeline)
        return items[-n:]

    def get_current_cycle_id(self) -> str:
        return self._current_cycle

    def get_cycle_summary(self) -> Dict[str, Any]:
        """One-line stats shown in the Control Tower banner."""
        return {
            "cycle_id":    self._current_cycle,
            "started_at":  self._cycle_start_ts,
            "event_count": self._event_count,
            "error_count": self._error_count,
            "regime":      self._last_regime,
            "vix":         self._last_vix,
        }

    # ── Internal ───────────────────────────────────────────────────────────

    def _on_event(self, event: Event) -> None:
        try:
            et  = (event.event_type.value
                   if hasattr(event.event_type, "value")
                   else str(event.event_type))
            pay = event.payload if isinstance(event.payload, dict) else {}

            with self._lock:
                self._event_count += 1

                if et == EventType.CYCLE_STARTED.value:
                    self._current_cycle  = event.correlation_id or event.timestamp.strftime(
                        "%Y%m%d_%H%M%S")
                    self._cycle_start_ts = event.timestamp.strftime("%H:%M:%S")
                    self._event_count    = 0
                    self._error_count    = 0
                    self._timeline.clear()

                elif et == EventType.MARKET_DATA_READY.value:
                    self._last_regime = pay.get("regime", "UNKNOWN")
                    self._last_vix    = pay.get("vix", 0.0)

                elif "error" in et.lower() or "fail" in et.lower():
                    self._error_count += 1

                self._timeline.append({
                    "ts":      event.timestamp.strftime("%H:%M:%S.%f")[:-3],
                    "type":    et,
                    "source":  event.source_agent or "–",
                    "summary": self._summarise(et, pay),
                })
        except Exception as exc:
            log.debug("[EventStreamMonitor] Error: %s", exc)

    @staticmethod
    def _summarise(et: str, pay: Dict) -> str:
        """Return a short one-line description of the event."""
        if et == EventType.CYCLE_STARTED.value:
            return "New cycle started"
        if et == EventType.CYCLE_COMPLETE.value:
            return "Cycle complete"
        if et == EventType.MARKET_DATA_READY.value:
            return f"Regime={pay.get('regime','?')} VIX={pay.get('vix','?')}"
        if et == EventType.EQUITY_OPPORTUNITY_FOUND.value:
            return (f"{pay.get('symbol','?')} strategy={pay.get('strategy','?')} "
                    f"conf={pay.get('confidence', 0):.2f}")
        if et == EventType.RISK_CHECK_PASSED.value:
            return f"Risk approved: {pay.get('approved', '?')} signals"
        if et == EventType.RISK_CHECK_FAILED.value:
            return f"Risk rejected: {pay.get('symbol','?')} — {pay.get('reason','?')}"
        if et == EventType.SIMULATION_COMPLETE.value:
            return (f"Sim approved: {pay.get('approved', '?')} "
                    f"(rate={pay.get('rate', 0):.0%})")
        if et == EventType.TRADE_APPROVED.value:
            return f"Trade APPROVED: {pay.get('symbol','?')} {pay.get('strategy','?')}"
        if et == EventType.TRADE_REJECTED.value:
            return f"Trade REJECTED: {pay.get('symbol','?')} — {pay.get('reason','?')}"
        if et == EventType.ORDER_PLACED.value:
            return (f"ORDER {pay.get('direction','?')} {pay.get('symbol','?')} "
                    f"qty={pay.get('quantity','?')} @ {pay.get('entry_price','?')}")
        return str(pay)[:80] if pay else ""
