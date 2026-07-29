"""
capability_exceptions.py -- iios.ai.capability.exceptions
===========================================================
M4 exception hierarchy for the A9 Enterprise Capability Platform.

Error code range: AI-1400 – AI-1499

Hierarchy
---------
AIException (A1)
└── AICapabilityException                    AI-1400  base
    ├── AICapabilityNotFoundError            AI-1401
    ├── AICapabilityAlreadyExistsError       AI-1402
    ├── AICapabilityDisabledError            AI-1403
    ├── AICapabilityVersionError             AI-1404
    ├── AICapabilityRegistrationError        AI-1405
    ├── AICapabilityExecutionException       AI-1410  base execution
    │   ├── AICapabilityTimeoutError         AI-1411
    │   ├── AICapabilityRetryExhaustedError  AI-1412
    │   ├── AICapabilityValidationError      AI-1413
    │   └── AICapabilityResultError          AI-1414
    ├── AICapabilityAuthorizationException   AI-1420  base authorization
    │   ├── AICapabilityPermissionDeniedError AI-1421
    │   ├── AICapabilityPolicyViolationError  AI-1422
    │   ├── AICapabilityQuotaExceededError    AI-1423
    │   └── AICapabilityRateLimitError        AI-1424
    ├── AIConnectorException                 AI-1430  base connector
    │   ├── AIConnectorNotFoundError         AI-1431
    │   ├── AIConnectorConnectionError       AI-1432
    │   └── AIConnectorTimeoutError          AI-1433
    ├── AISkillException                     AI-1440  base skill
    │   ├── AISkillNotFoundError             AI-1441
    │   └── AISkillExecutionError            AI-1442
    └── AICapabilityAuditException           AI-1450

A9 Enterprise Capability Platform -- Phase 3, Module 9
"""
from __future__ import annotations

from iios.ai.foundation.exceptions import AIException


# -- Base ---------------------------------------------------------------------

class AICapabilityException(AIException):
    """Base exception for A9 Enterprise Capability Platform (AI-1400)."""

    def __init__(self, message: str = "Capability error", code: str = "AI-1400") -> None:
        super().__init__(message, code=code)


# -- Registry exceptions (AI-1401 - AI-1405) ----------------------------------

class AICapabilityNotFoundError(AICapabilityException):
    """Capability not found in the registry (AI-1401)."""
    def __init__(self, message: str = "Capability not found") -> None:
        super().__init__(message, code="AI-1401")


class AICapabilityAlreadyExistsError(AICapabilityException):
    """Capability already registered (AI-1402)."""
    def __init__(self, message: str = "Capability already exists") -> None:
        super().__init__(message, code="AI-1402")


class AICapabilityDisabledError(AICapabilityException):
    """Capability exists but is disabled (AI-1403)."""
    def __init__(self, message: str = "Capability is disabled") -> None:
        super().__init__(message, code="AI-1403")


class AICapabilityVersionError(AICapabilityException):
    """Capability version conflict or incompatibility (AI-1404)."""
    def __init__(self, message: str = "Capability version error") -> None:
        super().__init__(message, code="AI-1404")


class AICapabilityRegistrationError(AICapabilityException):
    """General capability registration failure (AI-1405)."""
    def __init__(self, message: str = "Capability registration failed") -> None:
        super().__init__(message, code="AI-1405")


# -- Execution exceptions (AI-1410 - AI-1414) ---------------------------------

class AICapabilityExecutionException(AICapabilityException):
    """Base exception for capability execution failures (AI-1410)."""
    def __init__(self, message: str = "Capability execution error", code: str = "AI-1410") -> None:
        super().__init__(message, code=code)


class AICapabilityTimeoutError(AICapabilityExecutionException):
    """Capability execution exceeded the allowed timeout (AI-1411)."""
    def __init__(self, message: str = "Capability execution timed out") -> None:
        super().__init__(message, code="AI-1411")


class AICapabilityRetryExhaustedError(AICapabilityExecutionException):
    """All retry attempts exhausted (AI-1412)."""
    def __init__(self, message: str = "Retry attempts exhausted") -> None:
        super().__init__(message, code="AI-1412")


class AICapabilityValidationError(AICapabilityExecutionException):
    """Capability input or output validation failed (AI-1413)."""
    def __init__(self, message: str = "Capability validation failed") -> None:
        super().__init__(message, code="AI-1413")


class AICapabilityResultError(AICapabilityExecutionException):
    """Capability produced an invalid result (AI-1414)."""
    def __init__(self, message: str = "Capability result invalid") -> None:
        super().__init__(message, code="AI-1414")


# -- Authorization exceptions (AI-1420 - AI-1424) -----------------------------

class AICapabilityAuthorizationException(AICapabilityException):
    """Base exception for capability authorization failures (AI-1420)."""
    def __init__(self, message: str = "Capability authorization error", code: str = "AI-1420") -> None:
        super().__init__(message, code=code)


class AICapabilityPermissionDeniedError(AICapabilityAuthorizationException):
    """Principal does not have permission to execute the capability (AI-1421)."""
    def __init__(self, message: str = "Capability permission denied") -> None:
        super().__init__(message, code="AI-1421")


class AICapabilityPolicyViolationError(AICapabilityAuthorizationException):
    """Execution violates a capability policy (AI-1422)."""
    def __init__(self, message: str = "Capability policy violated") -> None:
        super().__init__(message, code="AI-1422")


class AICapabilityQuotaExceededError(AICapabilityAuthorizationException):
    """Execution quota exceeded for the principal (AI-1423)."""
    def __init__(self, message: str = "Capability quota exceeded") -> None:
        super().__init__(message, code="AI-1423")


class AICapabilityRateLimitError(AICapabilityAuthorizationException):
    """Execution rate limit reached (AI-1424)."""
    def __init__(self, message: str = "Capability rate limit reached") -> None:
        super().__init__(message, code="AI-1424")


# -- Connector exceptions (AI-1430 - AI-1433) ---------------------------------

class AIConnectorException(AICapabilityException):
    """Base exception for connector failures (AI-1430)."""
    def __init__(self, message: str = "Connector error", code: str = "AI-1430") -> None:
        super().__init__(message, code=code)


class AIConnectorNotFoundError(AIConnectorException):
    """Connector not found in the registry (AI-1431)."""
    def __init__(self, message: str = "Connector not found") -> None:
        super().__init__(message, code="AI-1431")


class AIConnectorConnectionError(AIConnectorException):
    """Connector failed to establish connection (AI-1432)."""
    def __init__(self, message: str = "Connector connection failed") -> None:
        super().__init__(message, code="AI-1432")


class AIConnectorTimeoutError(AIConnectorException):
    """Connector operation timed out (AI-1433)."""
    def __init__(self, message: str = "Connector timed out") -> None:
        super().__init__(message, code="AI-1433")


# -- Skill exceptions (AI-1440 - AI-1442) -------------------------------------

class AISkillException(AICapabilityException):
    """Base exception for skill failures (AI-1440)."""
    def __init__(self, message: str = "Skill error", code: str = "AI-1440") -> None:
        super().__init__(message, code=code)


class AISkillNotFoundError(AISkillException):
    """Skill not found in the registry (AI-1441)."""
    def __init__(self, message: str = "Skill not found") -> None:
        super().__init__(message, code="AI-1441")


class AISkillExecutionError(AISkillException):
    """Skill execution failed (AI-1442)."""
    def __init__(self, message: str = "Skill execution failed") -> None:
        super().__init__(message, code="AI-1442")


# -- Audit exception (AI-1450) ------------------------------------------------

class AICapabilityAuditException(AICapabilityException):
    """Capability audit system error (AI-1450)."""
    def __init__(self, message: str = "Capability audit error") -> None:
        super().__init__(message, code="AI-1450")
