"""
iios.ai.foundation.request
===========================
A1 AI Foundation -- Request Framework.

    from iios.ai.foundation.request import AIRequest, AIResponse, AIExecutionRequest

A1 AI Foundation -- Phase 3, Module 1
"""
from __future__ import annotations

from .request_models import (
    RequestMetadata,
    AIRequest,
    AIResponse,
    AIExecutionRequest,
    AIExecutionResult,
)

__all__ = [
    "RequestMetadata",
    "AIRequest",
    "AIResponse",
    "AIExecutionRequest",
    "AIExecutionResult",
]
