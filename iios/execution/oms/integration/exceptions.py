"""iios/execution/oms/integration/exceptions.py
==================================================
Exception hierarchy for the OMS Integration layer.

Error Codes
-----------
OI-000  OMSIntegrationError         — base
OI-001  OMSNotInitializedError       — engine not yet initialized
OI-002  OMSComponentMissingError     — required component not registered
OI-003  OMSComponentNotRunningError  — component not in RUNNING state
OI-004  OMSValidationError           — cross-component validation failure
OI-005  OMSSnapshotError             — snapshot generation failed
OI-006  OMSQueryError                — query routing failed
OI-007  OMSStateError                — OMS state transition violation
OI-008  OMSRegistryCapacityError     — component registry at capacity
OI-009  ComponentRegistrationError   — component failed to register
OI-010  OMSInitializationError       — initialization sequence failed

C6 Execution Intelligence — Phase 2, Module 6
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from iios.common.errors.exceptions import IIOSError


class OMSIntegrationError(IIOSError):
    """Base for all OMS Integration errors."""
    DEFAULT_CODE = "OI-000"


class OMSNotInitializedError(OMSIntegrationError):
    """Engine has not been initialized — call initialize() first."""
    DEFAULT_CODE = "OI-001"


class OMSComponentMissingError(OMSIntegrationError):
    """A required OMS component is not registered."""
    DEFAULT_CODE = "OI-002"

    def __init__(
        self,
        component_type: str,
        *,
        code:           str = "OI-002",
        context:        Optional[Dict[str, Any]] = None,
        correlation_id: str = "",
    ) -> None:
        super().__init__(
            f"Required OMS component '{component_type}' is not registered",
            code=code, context=context, correlation_id=correlation_id,
        )
        self.component_type = component_type


class OMSComponentNotRunningError(OMSIntegrationError):
    """An OMS component is registered but not running."""
    DEFAULT_CODE = "OI-003"

    def __init__(
        self,
        component_type: str,
        *,
        code:           str = "OI-003",
        context:        Optional[Dict[str, Any]] = None,
        correlation_id: str = "",
    ) -> None:
        super().__init__(
            f"OMS component '{component_type}' is not running",
            code=code, context=context, correlation_id=correlation_id,
        )
        self.component_type = component_type


class OMSValidationError(OMSIntegrationError):
    """Cross-component validation failed."""
    DEFAULT_CODE = "OI-004"

    def __init__(
        self,
        message:        str,
        *,
        errors:         tuple[str, ...] = (),
        code:           str = "OI-004",
        context:        Optional[Dict[str, Any]] = None,
        correlation_id: str = "",
    ) -> None:
        super().__init__(message, code=code, context=context,
                         correlation_id=correlation_id)
        self.errors = errors


class OMSSnapshotError(OMSIntegrationError):
    """Snapshot generation failed."""
    DEFAULT_CODE = "OI-005"


class OMSQueryError(OMSIntegrationError):
    """Query could not be routed or executed."""
    DEFAULT_CODE = "OI-006"

    def __init__(
        self,
        query_type:     str,
        reason:         str = "",
        *,
        code:           str = "OI-006",
        context:        Optional[Dict[str, Any]] = None,
        correlation_id: str = "",
    ) -> None:
        super().__init__(
            f"Query '{query_type}' failed: {reason}",
            code=code, context=context, correlation_id=correlation_id,
        )
        self.query_type = query_type
        self.reason     = reason


class OMSStateError(OMSIntegrationError):
    """Invalid OMS state transition."""
    DEFAULT_CODE = "OI-007"

    def __init__(
        self,
        current_state: str,
        attempted:     str,
        *,
        code:           str = "OI-007",
        context:        Optional[Dict[str, Any]] = None,
        correlation_id: str = "",
    ) -> None:
        super().__init__(
            f"Cannot transition OMS from '{current_state}' for '{attempted}'",
            code=code, context=context, correlation_id=correlation_id,
        )
        self.current_state = current_state
        self.attempted     = attempted


class OMSRegistryCapacityError(OMSIntegrationError):
    """Component registry is full."""
    DEFAULT_CODE = "OI-008"


class ComponentRegistrationError(OMSIntegrationError):
    """Component failed to register in the OMS."""
    DEFAULT_CODE = "OI-009"

    def __init__(
        self,
        component_type: str,
        reason:         str = "",
        *,
        code:           str = "OI-009",
        context:        Optional[Dict[str, Any]] = None,
        correlation_id: str = "",
    ) -> None:
        super().__init__(
            f"Failed to register component '{component_type}': {reason}",
            code=code, context=context, correlation_id=correlation_id,
        )
        self.component_type = component_type
        self.reason         = reason


class OMSInitializationError(OMSIntegrationError):
    """OMS initialization sequence failed."""
    DEFAULT_CODE = "OI-010"

    def __init__(
        self,
        reason: str = "",
        *,
        errors:         tuple[str, ...] = (),
        code:           str = "OI-010",
        context:        Optional[Dict[str, Any]] = None,
        correlation_id: str = "",
    ) -> None:
        super().__init__(
            f"OMS initialization failed: {reason}",
            code=code, context=context, correlation_id=correlation_id,
        )
        self.errors = errors
