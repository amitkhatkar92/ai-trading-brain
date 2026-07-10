"""iios/integration/integration_context.py

Thread-local context for integration operations.
"""
from __future__ import annotations

import threading
import time
from contextlib import contextmanager
from typing import Any, Generator


class _IntegrationThreadLocal(threading.local):
    def __init__(self) -> None:
        super().__init__()
        self.request_id:  str | None = None
        self.provider_id: str | None = None
        self.category:    str | None = None
        self.pipeline_id: str | None = None
        self.started_at:  float | None = None


_tl = _IntegrationThreadLocal()


class IntegrationContextState:
    @classmethod
    def set(
        cls,
        request_id:  str,
        provider_id: str = "",
        category:    str = "",
        pipeline_id: str = "",
    ) -> None:
        _tl.request_id  = request_id
        _tl.provider_id = provider_id
        _tl.category    = category
        _tl.pipeline_id = pipeline_id
        _tl.started_at  = time.time()

    @classmethod
    def get_request_id(cls) -> str | None:
        return _tl.request_id

    @classmethod
    def get_provider_id(cls) -> str | None:
        return _tl.provider_id

    @classmethod
    def elapsed_ms(cls) -> float:
        if _tl.started_at is None:
            return 0.0
        return (time.time() - _tl.started_at) * 1_000

    @classmethod
    def clear(cls) -> None:
        _tl.request_id  = None
        _tl.provider_id = None
        _tl.category    = None
        _tl.pipeline_id = None
        _tl.started_at  = None

    @classmethod
    def to_dict(cls) -> dict[str, Any]:
        return {
            "request_id":  _tl.request_id,
            "provider_id": _tl.provider_id,
            "category":    _tl.category,
            "pipeline_id": _tl.pipeline_id,
            "started_at":  _tl.started_at,
        }


@contextmanager
def integration_operation_context(
    request_id:  str,
    provider_id: str = "",
    category:    str = "",
    pipeline_id: str = "",
) -> Generator[IntegrationContextState, None, None]:
    IntegrationContextState.set(request_id, provider_id, category, pipeline_id)
    try:
        yield IntegrationContextState
    finally:
        IntegrationContextState.clear()
