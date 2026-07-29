"""
routing_decision.py -- iios.ai.model_management.router
========================================================
:class:`RoutingDecision` — immutable result of a routing operation.

A2 Model Management — Phase 3, Module 2
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Tuple


@dataclass(frozen=True)
class RoutingDecision:
    """Immutable routing outcome returned to the caller."""
    decision_id:        str
    model_id:           str
    model_name:         str
    strategy_used:      str
    score:              float
    alternatives:       Tuple[str, ...]   = field(default_factory=tuple)   # model_ids considered
    decided_at:         float             = field(default_factory=time.time)

    @classmethod
    def create(
        cls,
        model_id:     str,
        model_name:   str,
        strategy_used: str,
        score:        float                = 1.0,
        alternatives: Tuple[str, ...]      = (),
    ) -> "RoutingDecision":
        return cls(
            decision_id   = str(uuid.uuid4()),
            model_id      = model_id,
            model_name    = model_name,
            strategy_used = strategy_used,
            score         = score,
            alternatives  = tuple(alternatives),
        )
