"""
resource_coordinator.py -- iios.ai.orchestrator.policy
========================================================
Agent allocation, capability reservation, and execution coordination.

A10 Enterprise AI Orchestrator — Phase 3, Module 10
"""
from __future__ import annotations

import dataclasses
import threading
import time
import uuid
from dataclasses import dataclass
from typing import Dict, FrozenSet, List, Optional

from ..exceptions.orchestrator_exceptions import (
    AIAgentNotAvailableError,
    AIAllocationConflictError,
)


@dataclass(frozen=True)
class ResourceReservation:
    """Immutable resource reservation record."""
    reservation_id: str
    capability_id:  str
    agent_id:       str
    requester_id:   str
    reserved_at:    float
    expires_at:     Optional[float]

    @classmethod
    def create(
        cls,
        capability_id: str,
        agent_id:      str,
        requester_id:  str,
        ttl_seconds:   Optional[float] = None,
    ) -> "ResourceReservation":
        now = time.time()
        return cls(
            reservation_id = str(uuid.uuid4()),
            capability_id  = capability_id,
            agent_id       = agent_id,
            requester_id   = requester_id,
            reserved_at    = now,
            expires_at     = now + ttl_seconds if ttl_seconds else None,
        )

    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at


class AgentAllocator:
    """
    Allocates agents to capability requests using a least-loaded strategy.

    Each agent is registered with the set of capability_ids it supports
    and a ``max_load`` ceiling.
    """

    def __init__(self) -> None:
        self._lock:   threading.Lock    = threading.Lock()
        self._agents: Dict[str, Dict]   = {}
        # {agent_id: {"capabilities": FrozenSet, "max_load": int, "current_load": int}}

    def register_agent(
        self,
        agent_id:     str,
        capabilities: FrozenSet[str],
        max_load:     int = 1,
    ) -> None:
        with self._lock:
            self._agents[agent_id] = {
                "capabilities": capabilities,
                "max_load":     max_load,
                "current_load": 0,
            }

    def deregister_agent(self, agent_id: str) -> None:
        with self._lock:
            self._agents.pop(agent_id, None)

    def allocate(self, capability_id: str) -> str:
        """
        Return the least-loaded agent that supports *capability_id*.
        Raises :class:`AIAgentNotAvailableError` if none is available.
        """
        with self._lock:
            candidates = [
                (aid, info)
                for aid, info in self._agents.items()
                if capability_id in info["capabilities"]
                   and info["current_load"] < info["max_load"]
            ]
            if not candidates:
                raise AIAgentNotAvailableError(
                    f"No available agent for capability '{capability_id}'"
                )
            agent_id, info = min(candidates, key=lambda x: x[1]["current_load"])
            info["current_load"] += 1
            return agent_id

    def release(self, agent_id: str) -> None:
        with self._lock:
            info = self._agents.get(agent_id)
            if info and info["current_load"] > 0:
                info["current_load"] -= 1

    def available_agents(self) -> List[str]:
        with self._lock:
            return [
                aid for aid, info in self._agents.items()
                if info["current_load"] < info["max_load"]
            ]

    def get_load(self, agent_id: str) -> int:
        with self._lock:
            info = self._agents.get(agent_id)
            return info["current_load"] if info else 0

    def agent_count(self) -> int:
        with self._lock:
            return len(self._agents)


class CapabilityAllocator:
    """
    Manages exclusive resource reservations for capabilities.

    Only one active reservation per capability_id is allowed at a time.
    Expired reservations are automatically cleared on the next access.
    """

    def __init__(self) -> None:
        self._lock:         threading.Lock                    = threading.Lock()
        self._reservations: Dict[str, ResourceReservation]   = {}

    def reserve(
        self,
        capability_id: str,
        agent_id:      str,
        requester_id:  str,
        ttl_seconds:   Optional[float] = None,
    ) -> ResourceReservation:
        with self._lock:
            existing = self._reservations.get(capability_id)
            if existing and not existing.is_expired():
                raise AIAllocationConflictError(
                    f"Capability '{capability_id}' is already reserved"
                )
            res = ResourceReservation.create(
                capability_id = capability_id,
                agent_id      = agent_id,
                requester_id  = requester_id,
                ttl_seconds   = ttl_seconds,
            )
            self._reservations[capability_id] = res
        return res

    def release(self, capability_id: str) -> None:
        with self._lock:
            self._reservations.pop(capability_id, None)

    def release_by_id(self, reservation_id: str) -> None:
        with self._lock:
            keys = [
                cid for cid, r in self._reservations.items()
                if r.reservation_id == reservation_id
            ]
            for k in keys:
                del self._reservations[k]

    def is_available(self, capability_id: str) -> bool:
        with self._lock:
            res = self._reservations.get(capability_id)
            return res is None or res.is_expired()

    def reservation_count(self) -> int:
        with self._lock:
            return len(self._reservations)


class ExecutionCoordinator:
    """
    Facade over :class:`AgentAllocator` and :class:`CapabilityAllocator`.

    Allocates an agent and reserves the capability atomically.
    """

    def __init__(
        self,
        agent_allocator:      AgentAllocator,
        capability_allocator: CapabilityAllocator,
    ) -> None:
        self._agents       = agent_allocator
        self._capabilities = capability_allocator

    def coordinate(
        self,
        capability_id: str,
        requester_id:  str,
        ttl_seconds:   Optional[float] = None,
    ) -> ResourceReservation:
        """
        Allocate the best agent and reserve the capability.
        Returns the :class:`ResourceReservation`.
        """
        agent_id = self._agents.allocate(capability_id)
        try:
            return self._capabilities.reserve(
                capability_id = capability_id,
                agent_id      = agent_id,
                requester_id  = requester_id,
                ttl_seconds   = ttl_seconds,
            )
        except Exception:
            self._agents.release(agent_id)
            raise

    def release_coordination(self, capability_id: str, agent_id: str) -> None:
        self._capabilities.release(capability_id)
        self._agents.release(agent_id)
