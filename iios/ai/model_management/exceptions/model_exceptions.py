"""
model_exceptions.py -- iios.ai.model_management.exceptions
=============================================================
A2 exception hierarchy.  All exceptions extend A1's :class:`AIException`
so the entire AI Platform shares one base exception type.

Error-code range claimed by A2: AI-850 – AI-889.

A2 Model Management — Phase 3, Module 2
"""
from __future__ import annotations

from iios.ai.foundation.exceptions import AIException


# ---------------------------------------------------------------------------
# AI-850  Base
# ---------------------------------------------------------------------------

class AIModelException(AIException):
    """Base exception for all A2 Model Management errors."""
    CODE = "AI-850"


# ---------------------------------------------------------------------------
# AI-851  Model Registry
# ---------------------------------------------------------------------------

class AIModelNotFoundError(AIModelException):
    """Raised when a model_id or name cannot be found in the registry."""
    CODE = "AI-851"

    def __init__(self, model_id: str) -> None:
        super().__init__(f"Model not found: {model_id!r}")
        self.model_id = model_id


class AIModelAlreadyExistsError(AIModelException):
    """Raised when registering a model whose name is already in use."""
    CODE = "AI-852"

    def __init__(self, name: str) -> None:
        super().__init__(f"Model already registered with name: {name!r}")
        self.name = name


class AIModelVersionError(AIModelException):
    """Raised for version management failures (activate unknown id, etc.)."""
    CODE = "AI-853"


class AIModelDisabledError(AIModelException):
    """Raised when an operation requires a model that is currently disabled."""
    CODE = "AI-854"

    def __init__(self, model_id: str) -> None:
        super().__init__(f"Model is disabled: {model_id!r}")
        self.model_id = model_id


class AIModelValidationError(AIModelException):
    """Raised when model registration data fails validation."""
    CODE = "AI-855"


# ---------------------------------------------------------------------------
# AI-860  Routing
# ---------------------------------------------------------------------------

class AIRoutingException(AIModelException):
    """Base exception for model routing errors."""
    CODE = "AI-860"


class AINoModelAvailableError(AIRoutingException):
    """Raised when no eligible model can be found for a routing context."""
    CODE = "AI-861"

    def __init__(self, reason: str = "no eligible model found") -> None:
        super().__init__(reason)


class AIRoutingFailedError(AIRoutingException):
    """Raised when a routing strategy fails unexpectedly."""
    CODE = "AI-862"


class AIFailoverExhaustedError(AIRoutingException):
    """Raised when all failover candidates have been exhausted."""
    CODE = "AI-863"


# ---------------------------------------------------------------------------
# AI-870  Health
# ---------------------------------------------------------------------------

class AIHealthException(AIModelException):
    """Base exception for health-related errors."""
    CODE = "AI-870"


class AIModelUnhealthyError(AIHealthException):
    """Raised when a model is unhealthy and cannot serve requests."""
    CODE = "AI-871"

    def __init__(self, model_id: str) -> None:
        super().__init__(f"Model is unhealthy: {model_id!r}")
        self.model_id = model_id


# ---------------------------------------------------------------------------
# AI-875  Configuration
# ---------------------------------------------------------------------------

class AIModelConfigurationError(AIModelException):
    """Raised for configuration load/validation failures."""
    CODE = "AI-875"


# ---------------------------------------------------------------------------
# AI-880  Policy
# ---------------------------------------------------------------------------

class AIModelPolicyViolationError(AIModelException):
    """Raised when a model management policy is violated."""
    CODE = "AI-880"
