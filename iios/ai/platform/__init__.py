"""
iios.ai.platform
================
IIOS AI Platform Bootstrap — F0.1 Critical Architecture Resolution.

Resolves R-001 from the Enterprise Design Review:
  "No platform-level bootstrap or lifecycle manager — ten gateways must
   be individually started with no dependency order enforcement."

Public API
----------
IIOSBootstrap             — main bootstrap entry point
PlatformLifecycleManager  — unified lifecycle operations
PlatformDescriptor        — immutable platform descriptor
PlatformRegistry          — thread-safe platform store
PlatformRegistryError     — registry error
StartupCoordinator        — dependency-ordered startup + circular-dep detection
ShutdownCoordinator       — reverse-order shutdown
HealthCoordinator         — aggregated health
PlatformStatus            — platform-wide status snapshot
PlatformPhase             — lifecycle phase enum
PlatformStartupResult     — result of one platform operation
PlatformDependency        — explicit dependency declaration type
StartupOrder              — resolved dependency order
CircularDependencyError   — raised when dependency graph has a cycle

Layer:       AI PLATFORM BOOTSTRAP
Resolves:    Enterprise Design Review R-001
Version:     1.0.0
Status:      implemented
"""
from __future__ import annotations

from .health_coordinator         import HealthCoordinator
from .iios_bootstrap             import IIOSBootstrap
from .gateway_protocol           import GatewayProtocol
from .platform_lifecycle_manager import PlatformLifecycleManager
from .platform_registry          import PlatformRegistry, PlatformRegistryError
from .platform_types             import (
    PlatformDependency,
    PlatformDescriptor,
    PlatformPhase,
    PlatformStartupResult,
    PlatformStatus,
    StartupOrder,
)
from .shutdown_coordinator       import ShutdownCoordinator
from .startup_coordinator        import CircularDependencyError, StartupCoordinator

__version__    = "1.0.0"
__status__     = "implemented"
__resolves__   = "R-001"
FREEZE_VERSION = "1.0.0"
FREEZE_DATE    = "2026-08-01"

__all__ = [
    # Entry point
    "IIOSBootstrap",
    # Protocol
    "GatewayProtocol",
    # Lifecycle
    "PlatformLifecycleManager",
    # Registry
    "PlatformRegistry",
    "PlatformRegistryError",
    # Types
    "PlatformDescriptor",
    "PlatformDependency",
    "PlatformPhase",
    "PlatformStartupResult",
    "PlatformStatus",
    "StartupOrder",
    # Coordinators
    "StartupCoordinator",
    "ShutdownCoordinator",
    "HealthCoordinator",
    # Errors
    "CircularDependencyError",
]
