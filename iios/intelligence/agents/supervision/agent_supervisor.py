"""
iios/intelligence/agents/supervision/agent_supervisor.py
=========================================================
AgentSupervisor — monitors registered agents via heartbeat
and automatically applies their SupervisionPolicy when they fail.

Runs a daemon background thread that ticks every SUPERVISOR_TICK_S.

Singleton: get_agent_supervisor() / reset_agent_supervisor()
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Callable, Optional

from ..agent_constants import (
    AgentStatus, SupervisionPolicy, AgentEventType,
    HEARTBEAT_TIMEOUT_S, MAX_RESTART_ATTEMPTS, SUPERVISOR_TICK_S,
)
from ..agent_exceptions import (
    SupervisorNotRunningError, MaxRestartsExceededError, HeartbeatTimeoutError,
)
from ..core.base_agent import BaseAgent

log = logging.getLogger(__name__)

__all__ = [
    "AgentRecord",
    "AgentSupervisor",
    "get_agent_supervisor",
    "reset_agent_supervisor",
]


@dataclass
class AgentRecord:
    """Supervision state for a single agent."""
    agent:            BaseAgent
    restart_count:    int       = 0
    last_restart_at:  float     = 0.0
    restart_fn:       Optional[Callable[[], None]] = field(default=None, repr=False)

    @property
    def agent_id(self) -> str:
        return self.agent.agent_id

    def to_dict(self) -> dict:
        return {
            "agent_id":       self.agent_id,
            "status":         self.agent.status.value,
            "restart_count":  self.restart_count,
            "is_alive":       self.agent.is_alive(),
        }


class AgentSupervisor:
    """
    Heartbeat-based agent supervisor.

    - Monitors all registered agents every SUPERVISOR_TICK_S
    - When an agent's heartbeat times out or status == ERROR:
        * RESTART_ALWAYS / RESTART_ON_FAILURE → call agent.recover() (or restart_fn)
        * ISOLATE_ON_FAILURE → call agent.pause()
        * NO_RESTART → do nothing (alert only)
    - Raises MaxRestartsExceededError if restart_count > MAX_RESTART_ATTEMPTS
    """

    def __init__(
        self,
        heartbeat_timeout_s: float = HEARTBEAT_TIMEOUT_S,
        max_restarts:        int   = MAX_RESTART_ATTEMPTS,
        tick_s:              float = SUPERVISOR_TICK_S,
    ) -> None:
        self._timeout    = heartbeat_timeout_s
        self._max_restarts = max_restarts
        self._tick_s     = tick_s
        self._lock       = threading.RLock()
        self._records:   dict[str, AgentRecord] = {}
        self._running    = False
        self._thread:    Optional[threading.Thread] = None
        self._event_handlers: list[Callable] = []
        self._check_count = 0
        self._restart_count = 0

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def start(self) -> None:
        with self._lock:
            if self._running:
                return
            self._running = True
        self._thread = threading.Thread(
            target=self._loop, daemon=True, name="AgentSupervisor"
        )
        self._thread.start()
        log.info("AgentSupervisor started (tick=%.1fs, timeout=%.1fs)",
                 self._tick_s, self._timeout)

    def stop(self) -> None:
        with self._lock:
            self._running = False
        if self._thread:
            self._thread.join(timeout=self._tick_s * 2)
            self._thread = None
        log.info("AgentSupervisor stopped")

    @property
    def is_running(self) -> bool:
        return self._running

    # ── Registration ──────────────────────────────────────────────────────────

    def register(
        self,
        agent:       BaseAgent,
        restart_fn:  Optional[Callable[[], None]] = None,
    ) -> AgentRecord:
        """Register an agent for supervision."""
        with self._lock:
            record = AgentRecord(agent=agent, restart_fn=restart_fn)
            self._records[agent.agent_id] = record
        log.debug("Supervisor registered agent %r", agent.agent_id)
        return record

    def unregister(self, agent_id: str) -> bool:
        with self._lock:
            return self._records.pop(agent_id, None) is not None

    def is_supervised(self, agent_id: str) -> bool:
        with self._lock:
            return agent_id in self._records

    def on_event(self, handler: Callable) -> None:
        """Register a handler that receives (agent_id, event_type, data) tuples."""
        self._event_handlers.append(handler)

    # ── Manual health check ───────────────────────────────────────────────────

    def check(self, agent_id: str) -> dict:
        """Force an immediate health check for a specific agent."""
        with self._lock:
            rec = self._records.get(agent_id)
        if rec is None:
            return {"agent_id": agent_id, "supervised": False}
        return self._evaluate(rec)

    # ── Background loop ───────────────────────────────────────────────────────

    def _loop(self) -> None:
        while self._running:
            try:
                self._tick()
            except Exception as exc:
                log.error("Supervisor tick error: %s", exc)
            time.sleep(self._tick_s)

    def _tick(self) -> None:
        with self._lock:
            records = list(self._records.values())
        self._check_count += 1
        for rec in records:
            self._evaluate(rec)

    def _evaluate(self, rec: AgentRecord) -> dict:
        agent  = rec.agent
        alive  = agent.is_alive(self._timeout)
        status = agent.status

        outcome = {"agent_id": agent.agent_id, "action": "none"}

        if not alive:
            silence = time.time() - agent._last_heartbeat
            log.warning(
                "Agent %r heartbeat timeout (%.1fs silent)", agent.agent_id, silence
            )
            outcome["action"] = "heartbeat_timeout"
            self._apply_policy(rec, "heartbeat_timeout")

        elif status == AgentStatus.ERROR:
            log.warning("Agent %r in ERROR state", agent.agent_id)
            outcome["action"] = "error_detected"
            self._apply_policy(rec, "error")

        return outcome

    def _apply_policy(self, rec: AgentRecord, reason: str) -> None:
        policy    = rec.agent.supervision_policy
        agent_id  = rec.agent_id

        if policy == SupervisionPolicy.NO_RESTART:
            self._emit(agent_id, AgentEventType.FAILED, {"reason": reason})
            return

        if policy == SupervisionPolicy.ISOLATE_ON_FAILURE:
            try:
                rec.agent.pause()
            except Exception:
                # Force-set if pause() refuses (e.g., agent is in ERROR state)
                with rec.agent._lock:
                    rec.agent._status = AgentStatus.PAUSED
            self._emit(agent_id, AgentEventType.STOPPED, {"reason": reason})
            return

        # RESTART_ALWAYS or RESTART_ON_FAILURE
        if reason == "heartbeat_timeout" and policy == SupervisionPolicy.RESTART_ON_FAILURE:
            # Heartbeat timeout doesn't trigger restart for RESTART_ON_FAILURE
            # (agent may be busy). Only error state does.
            self._emit(agent_id, AgentEventType.FAILED, {"reason": reason})
            return

        if rec.restart_count >= self._max_restarts:
            log.error(
                "Agent %r exceeded max restarts (%d)", agent_id, self._max_restarts
            )
            self._emit(agent_id, AgentEventType.FAILED, {
                "reason": "max_restarts_exceeded",
                "restart_count": rec.restart_count,
            })
            return

        # Perform restart
        try:
            if rec.restart_fn is not None:
                rec.restart_fn()
            else:
                rec.agent.recover()
            rec.restart_count   += 1
            rec.last_restart_at  = time.time()
            self._restart_count += 1
            log.info("Agent %r restarted (attempt %d)", agent_id, rec.restart_count)
            self._emit(agent_id, AgentEventType.RECOVERED, {
                "restart_count": rec.restart_count
            })
        except Exception as exc:
            log.error("Failed to restart agent %r: %s", agent_id, exc)

    def _emit(self, agent_id: str, event_type: AgentEventType, data: dict) -> None:
        for h in self._event_handlers:
            try:
                h(agent_id, event_type, data)
            except Exception:
                pass

    # ── Stats ─────────────────────────────────────────────────────────────────

    def stats(self) -> dict:
        with self._lock:
            records = list(self._records.values())
        return {
            "running":        self._running,
            "supervised":     len(records),
            "check_count":    self._check_count,
            "restart_count":  self._restart_count,
            "agents":         [r.to_dict() for r in records],
        }


# ── Singleton ─────────────────────────────────────────────────────────────────

_sup_lock = threading.Lock()
_sup_inst: Optional[AgentSupervisor] = None


def get_agent_supervisor() -> AgentSupervisor:
    global _sup_inst
    if _sup_inst is None:
        with _sup_lock:
            if _sup_inst is None:
                _sup_inst = AgentSupervisor()
    return _sup_inst


def reset_agent_supervisor() -> None:
    global _sup_inst
    with _sup_lock:
        if _sup_inst is not None:
            try:
                _sup_inst.stop()
            except Exception:
                pass
        _sup_inst = None
