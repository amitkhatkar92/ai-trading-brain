"""
Trace Logger
============
Subscribes to ALL events on the EventBus using the wildcard "*" handler
and captures a complete decision trace for each replay day.

Each captured event is serialised to a JSON-safe dict so the decision
path from raw data → opportunity → strategy → risk → debate → execution
can be audited and reported.
"""

from __future__ import annotations

import json
import os
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from communication.event_bus import EventBus
from communication.events import Event
from utils import get_logger

log = get_logger(__name__)

DEFAULT_TRACE_DIR = Path(__file__).resolve().parent.parent / "simulation_logs" / "decision_trace"


class TraceCollector:
    """
    Attaches to an EventBus, collects every event, and saves the day's
    full decision trace to a JSON file.

    Usage:
        collector = TraceCollector(bus)
        collector.start()
        # … run one cycle …
        collector.stop()
        collector.save(day_num=1, trading_date=date.today())
    """

    def __init__(self, bus: EventBus) -> None:
        self._bus      = bus
        self._events:  List[Dict[str, Any]] = []
        self._sub_id:  Optional[str] = None
        self._active   = False

    # ── Lifecycle ──────────────────────────────────────────────────────────────

    def start(self) -> None:
        """Subscribe to ALL events on the bus (wildcard)."""
        if self._active:
            return
        self._events.clear()
        # subscribe() returns the sub_id string directly
        self._sub_id = self._bus.subscribe(
            event_type="*",
            handler=self._on_event,
            agent_name="TraceCollector",
        )
        self._active = True
        log.debug("[TraceCollector] started — sub_id=%s", self._sub_id)

    def stop(self) -> None:
        """Unsubscribe from the bus."""
        if not self._active:
            return
        try:
            if self._sub_id:
                self._bus.unsubscribe(self._sub_id)
        except Exception:
            pass          # unsubscribe may not exist — fine
        self._active = False

    def clear(self) -> None:
        self._events.clear()

    # ── Event handler ─────────────────────────────────────────────────────────

    def _on_event(self, event: Event) -> None:
        try:
            entry = {
                "ts":          event.timestamp.isoformat() if hasattr(event, "timestamp") else datetime.now().isoformat(),
                "event_type":  str(getattr(event, "event_type", "")),
                "source":      getattr(event, "source_agent", ""),
                "payload":     _safe_payload(getattr(event, "payload", {})),
            }
            self._events.append(entry)
        except Exception as exc:
            log.warning("[TraceCollector] Failed to capture event: %s", exc)

    # ── Accessors ─────────────────────────────────────────────────────────────

    def get_trace(self) -> List[Dict[str, Any]]:
        return list(self._events)

    def event_count(self) -> int:
        return len(self._events)

    def events_by_type(self) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for e in self._events:
            t = e.get("event_type", "unknown")
            counts[t] = counts.get(t, 0) + 1
        return counts

    # ── I/O ───────────────────────────────────────────────────────────────────

    def save(
        self,
        day_num: int,
        trading_date: date,
        output_dir: Optional[Path] = None,
    ) -> Path:
        """Serialise captured events to JSON and return the written path."""
        out_dir = Path(output_dir) if output_dir else DEFAULT_TRACE_DIR
        out_dir.mkdir(parents=True, exist_ok=True)

        fname = out_dir / f"day_{day_num:02d}_{trading_date.isoformat()}.json"
        payload = {
            "day_num":      day_num,
            "trading_date": trading_date.isoformat(),
            "total_events": len(self._events),
            "event_summary": self.events_by_type(),
            "trace":        self._events,
        }
        with open(fname, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2, default=str)

        log.info("[TraceCollector] Day %d trace saved → %s (%d events)",
                 day_num, fname, len(self._events))
        return fname


# ── Helpers ───────────────────────────────────────────────────────────────────

def _safe_payload(payload: Any) -> Any:
    """Recursively convert a payload to a JSON-serialisable form."""
    if payload is None:
        return None
    if isinstance(payload, dict):
        return {k: _safe_payload(v) for k, v in payload.items()}
    if isinstance(payload, (list, tuple)):
        return [_safe_payload(v) for v in payload]
    if isinstance(payload, (int, float, bool)):
        return payload
    if isinstance(payload, str):
        return payload
    if isinstance(payload, datetime):
        return payload.isoformat()
    # Enum or dataclass — stringify
    return str(payload)
