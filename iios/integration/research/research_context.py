"""iios/integration/research/research_context.py

Thread-local context for the research framework.
"""
from __future__ import annotations

import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Generator


@dataclass
class ResearchContextState:
    operation:     str   = ""
    project_id:    str   = ""
    experiment_id: str   = ""
    session_id:    str   = ""
    started_at:    float = field(default_factory=time.time)
    metadata:      dict[str, Any] = field(default_factory=dict)

    def elapsed_ms(self) -> float:
        return (time.time() - self.started_at) * 1_000


_local = threading.local()


def _get_state() -> ResearchContextState:
    if not hasattr(_local, "state"):
        _local.state = ResearchContextState()
    return _local.state


class ResearchContext:
    """Thread-local context for research operations."""

    @staticmethod
    def set(
        operation:     str = "",
        project_id:    str = "",
        experiment_id: str = "",
        session_id:    str = "",
    ) -> None:
        s = _get_state()
        s.operation     = operation
        s.project_id    = project_id
        s.experiment_id = experiment_id
        s.session_id    = session_id
        s.started_at    = time.time()

    @staticmethod
    def get() -> ResearchContextState:
        return _get_state()

    @staticmethod
    def clear() -> None:
        _local.state = ResearchContextState()

    @staticmethod
    @contextmanager
    def scope(
        operation:     str,
        project_id:    str = "",
        experiment_id: str = "",
        session_id:    str = "",
    ) -> Generator[ResearchContextState, None, None]:
        ResearchContext.set(
            operation     = operation,
            project_id    = project_id,
            experiment_id = experiment_id,
            session_id    = session_id,
        )
        try:
            yield _get_state()
        finally:
            ResearchContext.clear()
