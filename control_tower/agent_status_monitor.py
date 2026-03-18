"""
Agent Status Monitor — Control Tower Module 3
=============================================
Tracks per-agent health: last-seen timestamp, total events emitted,
and error events.  Any agent that has not emitted for > 120 s is
flagged "Stale"; one that never appeared is "Unknown".

Public API:
  get_status_table()    → List[Dict]  — one row per known agent
  get_stale_agents()    → List[str]   — agents silent > STALE_SECS
  get_error_agents()    → List[str]   — agents with error_count > 0
"""

from __future__ import annotations

import threading
import time
from typing import Any, Dict, List

from communication.events import Event
from utils import get_logger

log = get_logger(__name__)

STALE_SECS   = 120    # seconds after which agent is considered "stale"
ERROR_PREFIX = ("error", "fail", "timeout", "abort")  # et prefixes → error


class AgentStatusMonitor:

    def __init__(self, bus) -> None:
        self._lock   = threading.Lock()
        self._agents: Dict[str, Dict[str, Any]] = {}

        bus.subscribe("*", self._on_event,
                      agent_name="ControlTower.AgentStatusMonitor", priority=97)
        log.info("[AgentStatusMonitor] Initialised.")

    # ── Public API ─────────────────────────────────────────────────────────

    def get_status_table(self) -> List[Dict[str, Any]]:
        """
        Returns a list of agent-status dicts sorted by last_seen descending.
        Each dict: {name, event_count, error_count, last_seen_epoch,
                    last_seen_str, status}
        """
        now = time.time()
        rows = []
        with self._lock:
            for name, info in self._agents.items():
                age    = now - info["last_seen_epoch"]
                status = "OK" if age < STALE_SECS else "STALE"
                if info["error_count"] > 0:
                    status = "ERROR"
                rows.append({
                    "name":             name,
                    "event_count":      info["event_count"],
                    "error_count":      info["error_count"],
                    "last_seen_epoch":  info["last_seen_epoch"],
                    "last_seen_str":    info["last_seen_str"],
                    "status":           status,
                })
        rows.sort(key=lambda r: r["last_seen_epoch"], reverse=True)
        return rows

    def get_stale_agents(self) -> List[str]:
        return [r["name"] for r in self.get_status_table() if r["status"] == "STALE"]

    def get_error_agents(self) -> List[str]:
        return [r["name"] for r in self.get_status_table() if r["status"] == "ERROR"]

    def agent_count(self) -> int:
        with self._lock:
            return len(self._agents)

    # ── Internal ───────────────────────────────────────────────────────────

    def _on_event(self, event: Event) -> None:
        agent = event.source_agent or "UnknownAgent"
        et    = (event.event_type.value
                 if hasattr(event.event_type, "value")
                 else str(event.event_type)).lower()
        is_err = any(et.startswith(p) for p in ERROR_PREFIX)

        ts_epoch = event.timestamp.timestamp()
        ts_str   = event.timestamp.strftime("%H:%M:%S")

        with self._lock:
            if agent not in self._agents:
                self._agents[agent] = {
                    "event_count":     0,
                    "error_count":     0,
                    "last_seen_epoch": 0.0,
                    "last_seen_str":   "",
                }
            rec = self._agents[agent]
            rec["event_count"]    += 1
            rec["last_seen_epoch"] = ts_epoch
            rec["last_seen_str"]   = ts_str
            if is_err:
                rec["error_count"] += 1
