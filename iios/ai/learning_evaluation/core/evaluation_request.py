"""
evaluation_request.py -- iios.ai.learning_evaluation.core
===========================================================
:class:`EvaluationRequest` — immutable specification for a single
evaluation task within a session.

A7 Learning & Evaluation Platform — Phase 3, Module 7
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from typing import Any, FrozenSet, Optional, Tuple


@dataclass(frozen=True)
class EvaluationRequest:
    """
    Immutable specification for one evaluation task.

    ``input_data``   — the data fed to the AI system under evaluation.
    ``expected``     — optional ground-truth / reference output.
    ``parameters``   — evaluation-specific key→value settings (frozen).
    """

    request_id:   str
    session_id:   str
    input_data:   Any
    expected:     Optional[Any]
    parameters:   FrozenSet[Tuple[str, Any]]
    submitted_at: float

    @classmethod
    def create(
        cls,
        session_id:  str,
        input_data:  Any,
        expected:    Optional[Any] = None,
        **parameters: Any,
    ) -> "EvaluationRequest":
        return cls(
            request_id   = str(uuid.uuid4()),
            session_id   = session_id,
            input_data   = input_data,
            expected     = expected,
            parameters   = frozenset(parameters.items()),
            submitted_at = time.time(),
        )

    def get_param(self, key: str, default: Any = None) -> Any:
        for k, v in self.parameters:
            if k == key:
                return v
        return default
