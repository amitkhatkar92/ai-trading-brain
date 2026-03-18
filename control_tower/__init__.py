"""
Control Tower — Central Monitoring Package
==========================================
Wire together all 5 sub-monitors and expose a single ControlTower
singleton that the orchestrator imports once:

    from control_tower import ControlTower
    ct = ControlTower.get_instance(bus)

After construction the tower is fully passive — every event on the
shared EventBus is captured automatically with no further calls
required from the orchestrator.

Sub-modules:
  TelemetryLogger     — SQLite persistence    (ct_events / ct_cycles / ct_decisions)
  EventStreamMonitor  — live event timeline
  AgentStatusMonitor  — per-agent health table
  SignalVisualizer    — per-cycle signal funnel
  DecisionTrace       — per-symbol audit trail
"""

from __future__ import annotations

import threading
from typing import Optional

from utils import get_logger

from .telemetry_logger     import TelemetryLogger
from .event_stream_monitor import EventStreamMonitor
from .agent_status_monitor import AgentStatusMonitor
from .signal_visualizer    import SignalVisualizer
from .decision_trace       import DecisionTrace

log = get_logger(__name__)

_instance: Optional["ControlTower"] = None
_init_lock = threading.Lock()


class ControlTower:
    """
    Central observability hub for the AI trading brain.

    All monitoring is passive — sub-modules subscribe to the EventBus
    and react to published events.  No code changes are required in
    individual agents.

    Attributes:
        telemetry    (TelemetryLogger)    persists every event to SQLite
        stream       (EventStreamMonitor) live cycle timeline
        agent_status (AgentStatusMonitor) per-agent health
        funnel       (SignalVisualizer)   signal conversion funnel
        trace        (DecisionTrace)      per-symbol audit trail
    """

    def __init__(self, bus) -> None:
        log.info("[ControlTower] Initialising all monitoring sub-systems...")
        self.telemetry    = TelemetryLogger(bus)
        self.stream       = EventStreamMonitor(bus)
        self.agent_status = AgentStatusMonitor(bus)
        self.funnel       = SignalVisualizer(bus)
        self.trace        = DecisionTrace(bus)
        log.info("[ControlTower] ✓ All sub-systems active. "
                 "Dashboard: streamlit run control_tower/dashboard_app.py")

    # ── Singleton accessor ─────────────────────────────────────────────────

    @classmethod
    def get_instance(cls, bus=None) -> "ControlTower":
        """
        Return the shared ControlTower.  Pass `bus` on the first call
        to initialise.  Subsequent calls may omit bus.
        """
        global _instance
        if _instance is None:
            with _init_lock:
                if _instance is None:
                    if bus is None:
                        from communication.event_bus import get_bus
                        bus = get_bus()
                    _instance = cls(bus)
        return _instance

    # ── Convenience properties (delegate to sub-modules) ──────────────────

    @property
    def current_cycle_id(self) -> str:
        return self.stream.get_current_cycle_id()

    def status_summary(self) -> dict:
        """Quick health snapshot for logging / heartbeat."""
        cycle_summary = self.stream.get_cycle_summary()
        funnel        = self.funnel.get_current_funnel()
        return {
            **cycle_summary,
            "funnel_generated":   funnel.get("generated", 0),
            "funnel_executed":    funnel.get("executed", 0),
            "agents_tracked":     self.agent_status.agent_count(),
            "pending_decisions":  (self.trace.get_approved_count()
                                   + self.trace.get_rejected_count()),
        }
