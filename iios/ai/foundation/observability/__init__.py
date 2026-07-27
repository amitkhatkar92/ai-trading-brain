"""
iios.ai.foundation.observability
==================================
A1 AI Foundation -- Structured Logging & Observability.

A1 AI Foundation -- Phase 3, Module 1
"""
from .observability import (
    CorrelationContext,
    StructuredLogEntry,
    StructuredLogger,
    TimingResult,
    ExecutionTimer,
)

__all__ = [
    "CorrelationContext",
    "StructuredLogEntry",
    "StructuredLogger",
    "TimingResult",
    "ExecutionTimer",
]
