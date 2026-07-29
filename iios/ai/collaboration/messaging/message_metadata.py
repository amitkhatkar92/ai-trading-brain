"""
message_metadata.py -- iios.ai.collaboration.messaging
========================================================
:class:`MessageMetadata` — routing and delivery metadata attached to
every :class:`MessageEnvelope`.

A6 Multi-Agent Collaboration Framework — Phase 3, Module 6
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from enum import Enum
from typing import FrozenSet, Optional


class RetryPolicy(str, Enum):
    NONE         = "none"
    ONCE         = "once"
    THREE_TIMES  = "three_times"


@dataclass(frozen=True)
class MessageMetadata:
    """Routing and delivery metadata for one message envelope."""

    metadata_id:  str
    session_id:   str
    created_at:   float
    ttl_s:        Optional[float]  # time-to-live in seconds; None = unlimited
    retry_policy: RetryPolicy
    tags:         FrozenSet[str]

    @classmethod
    def create(
        cls,
        session_id:   str,
        ttl_s:        Optional[float] = None,
        retry_policy: RetryPolicy     = RetryPolicy.NONE,
        tags:         FrozenSet[str]  = frozenset(),
    ) -> "MessageMetadata":
        return cls(
            metadata_id  = str(uuid.uuid4()),
            session_id   = session_id,
            created_at   = time.time(),
            ttl_s        = ttl_s,
            retry_policy = retry_policy,
            tags         = frozenset(tags),
        )

    def is_expired(self, at: Optional[float] = None) -> bool:
        if self.ttl_s is None:
            return False
        t = at or time.time()
        return (t - self.created_at) > self.ttl_s
