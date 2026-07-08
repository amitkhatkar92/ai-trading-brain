"""
iios/intelligence/forecast/hypothesis_context.py
================================================
Thread-local execution context for the Hypothesis & Forecast Engine.
Note: context manager helpers use ``_scope`` suffix to avoid name collisions
with the hypothesis_session and forecast subpackage modules.
"""
from __future__ import annotations

import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Generator

from .hypothesis_constants import HypothesisType, ForecastHorizon


@dataclass
class ForecastDiagnostic:
    level:   str
    message: str
    source:  str
    ts:      float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "level":   self.level,
            "message": self.message,
            "source":  self.source,
            "ts":      self.ts,
        }


class ForecastContextState:
    """Mutable per-thread context for an active forecasting chain."""

    def __init__(self) -> None:
        self.hypothesis_id: str | None            = None
        self.forecast_id:   str | None            = None
        self.scenario_id:   str | None            = None
        self.horizon:       ForecastHorizon | None = None
        self.depth:         int                   = 0
        self.started_at:    float                 = time.time()
        self._diagnostics:  list[ForecastDiagnostic] = []

    def add_diagnostic(self, level: str, message: str, source: str) -> None:
        self._diagnostics.append(
            ForecastDiagnostic(level=level, message=message, source=source)
        )

    def warnings(self) -> list[ForecastDiagnostic]:
        return [d for d in self._diagnostics if d.level == "WARNING"]

    def errors(self) -> list[ForecastDiagnostic]:
        return [d for d in self._diagnostics if d.level == "ERROR"]

    @property
    def elapsed_s(self) -> float:
        return time.time() - self.started_at

    def to_dict(self) -> dict[str, Any]:
        return {
            "hypothesis_id": self.hypothesis_id,
            "forecast_id":   self.forecast_id,
            "scenario_id":   self.scenario_id,
            "horizon":       self.horizon.value if self.horizon else None,
            "depth":         self.depth,
            "elapsed_s":     round(self.elapsed_s, 4),
            "diagnostics":   [d.to_dict() for d in self._diagnostics],
        }


# ── Thread-local manager ──────────────────────────────────────────────────────

_CTX_LOCAL: threading.local = threading.local()
_LOCK = threading.Lock()
_INSTANCE: _ForecastContextManager | None = None


class _ForecastContextManager:
    @staticmethod
    def _current() -> ForecastContextState:
        if not hasattr(_CTX_LOCAL, "state"):
            _CTX_LOCAL.state = ForecastContextState()
        return _CTX_LOCAL.state

    def get(self) -> ForecastContextState:
        return self._current()

    @contextmanager
    def hypothesis(
        self,
        hypothesis_id: str,
        horizon:       ForecastHorizon | None = None,
    ) -> Generator[ForecastContextState, None, None]:
        ctx = self._current()
        saved = (ctx.hypothesis_id, ctx.horizon, ctx.depth)
        ctx.hypothesis_id = hypothesis_id
        ctx.horizon        = horizon
        ctx.depth          = saved[2] + 1
        ctx.started_at     = time.time()
        try:
            yield ctx
        finally:
            ctx.hypothesis_id, ctx.horizon, ctx.depth = saved

    @contextmanager
    def forecast(
        self,
        forecast_id: str,
    ) -> Generator[ForecastContextState, None, None]:
        ctx  = self._current()
        prev = ctx.forecast_id
        ctx.forecast_id = forecast_id
        try:
            yield ctx
        finally:
            ctx.forecast_id = prev

    @contextmanager
    def scenario(
        self,
        scenario_id: str,
    ) -> Generator[ForecastContextState, None, None]:
        ctx  = self._current()
        prev = ctx.scenario_id
        ctx.scenario_id = scenario_id
        try:
            yield ctx
        finally:
            ctx.scenario_id = prev


def _get_manager() -> _ForecastContextManager:
    global _INSTANCE
    if _INSTANCE is None:
        with _LOCK:
            if _INSTANCE is None:
                _INSTANCE = _ForecastContextManager()
    return _INSTANCE


def get_forecast_context() -> ForecastContextState:
    return _get_manager().get()


def reset_forecast_context() -> None:
    global _INSTANCE
    with _LOCK:
        _INSTANCE = None
    if hasattr(_CTX_LOCAL, "state"):
        del _CTX_LOCAL.state


# ── Module-level convenience helpers ─────────────────────────────────────────

@contextmanager
def hypothesis_scope(
    hypothesis_id: str,
    horizon:       ForecastHorizon | None = None,
) -> Generator[ForecastContextState, None, None]:
    """Enter a hypothesis-scoped context (named ``_scope`` to avoid clash with module)."""
    with _get_manager().hypothesis(hypothesis_id, horizon) as ctx:
        yield ctx


@contextmanager
def forecast_scope(
    forecast_id: str,
) -> Generator[ForecastContextState, None, None]:
    with _get_manager().forecast(forecast_id) as ctx:
        yield ctx


@contextmanager
def scenario_scope(
    scenario_id: str,
) -> Generator[ForecastContextState, None, None]:
    with _get_manager().scenario(scenario_id) as ctx:
        yield ctx
