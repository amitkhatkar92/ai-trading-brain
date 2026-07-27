"""
foundation_snapshot.py — iios.ai.foundation.snapshot
======================================================
:class:`FoundationSnapshot` — point-in-time immutable view of the entire
AI Foundation module state.

Snapshots are the sole mechanism for external observability.  No module
outside A1 holds a live reference to internal A1 state — they receive a
snapshot instead.

A1 AI Foundation — Phase 3, Module 5
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ..lifecycle.constants import AILifecycleState, VERSION
from ..adapters.constants  import AIProviderHealth


SCHEMA_VERSION = "1.0"


@dataclass(frozen=True)
class ProviderStatusEntry:
    """Health entry for one registered AI provider."""
    provider_id:   str
    model_id:      str
    health:        AIProviderHealth
    capabilities:  tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "provider_id":  self.provider_id,
            "model_id":     self.model_id,
            "health":       self.health.value,
            "capabilities": list(self.capabilities),
        }


@dataclass(frozen=True)
class FoundationSnapshot:
    """
    Immutable full-state snapshot of the AI Foundation module (A1).

    Produced by :class:`AIFoundationGateway.snapshot()` and consumed by
    the dashboard (A10 equivalent) and automated health checks.

    Fields
    ------
    snapshot_id :       Unique snapshot identifier.
    module_id :         AI Foundation module identifier.
    lifecycle_state :   Current lifecycle state.
    is_running :        ``True`` iff lifecycle state is RUNNING.
    provider_count :    Number of registered AI providers.
    providers :         Health entry per registered provider.
    active_sessions :   Number of currently active sessions.
    total_requests :    Cumulative requests processed.
    total_errors :      Cumulative errors encountered.
    uptime_s :          Seconds since module start.
    governance_tier :   Active governance tier.
    environment :       Deployment environment label.
    timestamp :         Wall-clock time of snapshot creation.
    version :           Module version string.
    schema :            Serialisation schema version.
    """
    snapshot_id:      str
    module_id:        str
    lifecycle_state:  AILifecycleState
    is_running:       bool
    provider_count:   int
    providers:        tuple[ProviderStatusEntry, ...]
    active_sessions:  int
    total_requests:   int
    total_errors:     int
    uptime_s:         float
    governance_tier:  str
    environment:      str
    timestamp:        float
    version:          str  = VERSION
    schema:           str  = SCHEMA_VERSION
    metadata:         Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        module_id:       str,
        lifecycle_state: AILifecycleState,
        providers:       List[ProviderStatusEntry],
        active_sessions: int,
        total_requests:  int,
        total_errors:    int,
        uptime_s:        float,
        governance_tier: str,
        environment:     str,
        **metadata: Any,
    ) -> "FoundationSnapshot":
        return cls(
            snapshot_id     = str(uuid.uuid4()),
            module_id       = module_id,
            lifecycle_state = lifecycle_state,
            is_running      = (lifecycle_state == AILifecycleState.RUNNING),
            provider_count  = len(providers),
            providers       = tuple(providers),
            active_sessions = active_sessions,
            total_requests  = total_requests,
            total_errors    = total_errors,
            uptime_s        = uptime_s,
            governance_tier = governance_tier,
            environment     = environment,
            timestamp       = time.time(),
            metadata        = dict(metadata),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id":     self.snapshot_id,
            "module_id":       self.module_id,
            "lifecycle_state": self.lifecycle_state.value,
            "is_running":      self.is_running,
            "provider_count":  self.provider_count,
            "providers":       [p.to_dict() for p in self.providers],
            "active_sessions": self.active_sessions,
            "total_requests":  self.total_requests,
            "total_errors":    self.total_errors,
            "uptime_s":        round(self.uptime_s, 2),
            "governance_tier": self.governance_tier,
            "environment":     self.environment,
            "timestamp":       self.timestamp,
            "version":         self.version,
            "schema":          self.schema,
        }
