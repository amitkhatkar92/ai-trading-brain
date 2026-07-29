"""
prompt_context_snapshot.py -- iios.ai.prompt_context.snapshot
=================================================================
:class:`PromptContextSnapshot` -- immutable point-in-time capture of
the A3 Prompt & Context Platform's state (registry + event bus
counters).  Suitable for dashboards, audits, and health endpoints.

A3 Prompt & Context Platform -- Phase 3, Module 3
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from typing import Optional

from ..events.event_bus     import PromptEventBus
from ..registry.prompt_registry import PromptRegistry


@dataclass(frozen=True)
class PromptContextSnapshot:
    """Immutable snapshot of the A3 Prompt & Context Platform's state."""
    snapshot_id:             str
    taken_at:                float
    template_count:          int
    enabled_template_count:  int
    total_versions:          int
    events_published:        int

    @classmethod
    def capture(
        cls,
        registry:  PromptRegistry,
        event_bus: Optional[PromptEventBus] = None,
    ) -> "PromptContextSnapshot":
        templates      = registry.list_all()
        total_versions = sum(len(t.history()) for t in templates)
        enabled_count  = sum(1 for t in templates if t.enabled)
        return cls(
            snapshot_id            = str(uuid.uuid4()),
            taken_at                = time.time(),
            template_count          = len(templates),
            enabled_template_count  = enabled_count,
            total_versions          = total_versions,
            events_published        = event_bus.published_count if event_bus else 0,
        )
