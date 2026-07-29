"""
capability_executor.py -- iios.ai.capability.engine
=====================================================
:class:`CapabilityExecutor` — invokes registered handler functions,
enforcing authorization, retry, and result wrapping.

A9 Enterprise Capability Platform — Phase 3, Module 9
"""
from __future__ import annotations

import threading
import time
from typing import Any, Callable, Dict, Optional

from ..core.capability_descriptor import CapabilityDescriptor
from ..exceptions.capability_exceptions import (
    AICapabilityDisabledError,
    AICapabilityNotFoundError,
    AICapabilityPermissionDeniedError,
    AICapabilityRetryExhaustedError,
)
from .capability_request  import CapabilityRequest
from .capability_response import CapabilityResponse, ExecutionResult

# Handler callable: (params_dict) -> Any
HandlerFn = Callable[[Dict[str, Any]], Any]
# Authorize callable: (principal_id, capability_id) -> None  (raises on denial)
AuthorizeFn = Callable[[str, str], None]


class CapabilityExecutor:
    """
    Thread-safe executor that dispatches capability invocations.

    Usage::

        executor = CapabilityExecutor()
        executor.register_handler("cap_id", lambda p: p["x"] * 2)
        response = executor.execute(request, descriptor)
    """

    def __init__(self) -> None:
        self._lock:     threading.Lock                    = threading.Lock()
        self._handlers: Dict[str, HandlerFn]              = {}
        self._total_executions: int                        = 0
        self._failed_executions: int                       = 0

    # ── handler registration ─────────────────────────────────────────────────

    def register_handler(self, capability_id: str, handler: HandlerFn) -> None:
        """Register a callable as the execution handler for *capability_id*."""
        with self._lock:
            self._handlers[capability_id] = handler

    def has_handler(self, capability_id: str) -> bool:
        with self._lock:
            return capability_id in self._handlers

    def handler_count(self) -> int:
        with self._lock:
            return len(self._handlers)

    # ── execution ─────────────────────────────────────────────────────────────

    def execute(
        self,
        request:      CapabilityRequest,
        descriptor:   CapabilityDescriptor,
        authorize_fn: Optional[AuthorizeFn] = None,
    ) -> CapabilityResponse:
        """
        Execute *request* against the registered handler for *descriptor*.

        Steps:
          1. Verify descriptor is ACTIVE.
          2. Optional authorization check.
          3. Invoke handler with retries.
          4. Return :class:`CapabilityResponse`.
        """
        if not descriptor.is_executable():
            raise AICapabilityDisabledError(
                f"Capability '{descriptor.name}' is not executable "
                f"(status={descriptor.status.value})"
            )

        if authorize_fn is not None:
            authorize_fn(request.context.principal_id, request.capability_id)

        with self._lock:
            handler = self._handlers.get(request.capability_id)

        if handler is None:
            raise AICapabilityNotFoundError(
                f"No handler registered for capability '{request.capability_id}'"
            )

        params     = request.params_dict()
        max_tries  = max(1, descriptor.max_retries + 1)
        started_at = time.time()
        last_error: Optional[Exception] = None

        for attempt in range(max_tries):
            try:
                output = handler(params)
                result = ExecutionResult.success(
                    request.request_id, request.capability_id, output, started_at
                )
                with self._lock:
                    self._total_executions += 1
                return CapabilityResponse.create(request.request_id, result)
            except AICapabilityPermissionDeniedError:
                raise
            except Exception as exc:
                last_error = exc

        # All retries exhausted
        with self._lock:
            self._total_executions  += 1
            self._failed_executions += 1

        if descriptor.max_retries > 0:
            raise AICapabilityRetryExhaustedError(
                f"Capability '{descriptor.name}' failed after "
                f"{max_tries} attempt(s): {last_error}"
            )

        result = ExecutionResult.failure(
            request.request_id,
            request.capability_id,
            str(last_error),
            started_at,
        )
        return CapabilityResponse.create(request.request_id, result)

    # ── stats ─────────────────────────────────────────────────────────────────

    def total_executions(self) -> int:
        with self._lock:
            return self._total_executions

    def failed_executions(self) -> int:
        with self._lock:
            return self._failed_executions
