"""
iios/ontology/reasoning/reasoning_factory.py
=============================================
Request/response models and factory for the reasoning engine.
"""

from __future__ import annotations

import time
import threading
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

from .reasoning_constants import (
    ReasoningType,
    SYSTEM_REASONING_ACTOR,
    MAX_INFERENCE_DEPTH,
)
from .reasoning_result import ReasoningResult
from .reasoning_trace  import ReasoningTrace

__all__ = [
    "ReasoningRequest",
    "ReasoningResponse",
    "ReasoningFactory",
    "get_reasoning_factory",
    "reset_reasoning_factory",
]


@dataclass
class ReasoningRequest:
    """Specification for a single reasoning operation."""
    reasoning_type: ReasoningType
    target_uri:     str                     # Entry-point URI (type / namespace / "*" for all)
    max_depth:      int                     = MAX_INFERENCE_DEPTH
    rule_ids:       list[str]               = field(default_factory=list)  # empty = all enabled
    options:        dict[str, Any]          = field(default_factory=dict)
    actor:          str                     = SYSTEM_REASONING_ACTOR
    request_id:     str                     = field(default_factory=lambda: str(uuid.uuid4()))
    created_at:     float                   = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "request_id":    self.request_id,
            "reasoning_type": self.reasoning_type.value,
            "target_uri":    self.target_uri,
            "max_depth":     self.max_depth,
            "rule_ids":      self.rule_ids,
            "options":       self.options,
            "actor":         self.actor,
            "created_at":    self.created_at,
        }


@dataclass
class ReasoningResponse:
    """Complete response from a reasoning operation."""
    request: ReasoningRequest
    result:  ReasoningResult
    trace:   ReasoningTrace

    @property
    def succeeded(self) -> bool:
        return self.result.succeeded

    def to_dict(self) -> dict:
        return {
            "request":  self.request.to_dict(),
            "result":   self.result.to_dict(),
            "trace":    self.trace.summary(),
        }


class ReasoningFactory:
    """Convenience constructors for reasoning request/response objects."""

    def make_request(
        self,
        reasoning_type: ReasoningType,
        target_uri:     str,
        max_depth:      int            = MAX_INFERENCE_DEPTH,
        rule_ids:       list[str] | None = None,
        options:        dict[str, Any] | None = None,
        actor:          str            = SYSTEM_REASONING_ACTOR,
    ) -> ReasoningRequest:
        return ReasoningRequest(
            reasoning_type = reasoning_type,
            target_uri     = target_uri,
            max_depth      = max_depth,
            rule_ids       = rule_ids or [],
            options        = options or {},
            actor          = actor,
        )

    def make_response(
        self,
        request: ReasoningRequest,
        result:  ReasoningResult,
        trace:   ReasoningTrace,
    ) -> ReasoningResponse:
        return ReasoningResponse(request=request, result=result, trace=trace)


_fac_lock = threading.Lock()
_fac_inst: Optional[ReasoningFactory] = None


def get_reasoning_factory() -> ReasoningFactory:
    global _fac_inst
    if _fac_inst is None:
        with _fac_lock:
            if _fac_inst is None:
                _fac_inst = ReasoningFactory()
    return _fac_inst


def reset_reasoning_factory() -> None:
    global _fac_inst
    with _fac_lock:
        _fac_inst = None
