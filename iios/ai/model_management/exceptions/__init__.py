"""
iios.ai.model_management.exceptions
======================================
Exception hierarchy for A2 Model Management.
"""
from __future__ import annotations

from .model_exceptions import (
    AIFailoverExhaustedError,
    AIHealthException,
    AIModelAlreadyExistsError,
    AIModelConfigurationError,
    AIModelDisabledError,
    AIModelException,
    AIModelNotFoundError,
    AIModelPolicyViolationError,
    AIModelUnhealthyError,
    AIModelValidationError,
    AIModelVersionError,
    AINoModelAvailableError,
    AIRoutingException,
    AIRoutingFailedError,
)

__all__ = [
    "AIModelException",
    "AIModelNotFoundError",
    "AIModelAlreadyExistsError",
    "AIModelVersionError",
    "AIModelDisabledError",
    "AIModelValidationError",
    "AIRoutingException",
    "AINoModelAvailableError",
    "AIRoutingFailedError",
    "AIFailoverExhaustedError",
    "AIHealthException",
    "AIModelUnhealthyError",
    "AIModelConfigurationError",
    "AIModelPolicyViolationError",
]
