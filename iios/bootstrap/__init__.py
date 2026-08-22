"""
iios.bootstrap
==============
IIOS Bootstrap Engine — complete 45-stage platform initialization.

This package implements the System Bootstrap Specification (IIOS-BSS-001).
It is the authoritative entry point for starting the IIOS platform.

Public API
----------
BootstrapEngine     — main orchestrator (call .start() to initialize IIOS)
LifecycleManager    — lifecycle state machine (pause / resume / stop / shutdown)
ShutdownManager     — graceful component teardown
StartupContext      — context object accumulated across all stages
SystemPhase         — lifecycle phase enum
get_system_state()  — global SystemState singleton factory

Typical usage::

    from iios.bootstrap import BootstrapEngine

    engine = BootstrapEngine()
    context = engine.start()          # runs all 45 stages
    # ... IIOS is now in SystemPhase.RUNNING ...
    engine.shutdown()                 # graceful teardown

Architecture Reference: IIOS-BSS-001
Layer: BOOTSTRAP  |  Wave: 2  |  Owner: Platform
Foundation: IIOS-FCR-001 (CERTIFIED)
"""

from .bootstrap_engine import BootstrapEngine
from .configuration_loader import ConfigurationLoader, ConfigurationSnapshot
from .dependency_loader import DependencyLoader, DependencyReport, DependencyTier
from .environment_loader import EnvironmentLoader, EnvironmentSnapshot
from .lifecycle_manager import LifecycleError, LifecycleManager
from .module_loader import ModuleLoadError, ModuleLoader
from .repository_validator import RepositoryReport, RepositoryValidator
from .service_loader import ServiceLoader, ServiceRegistry, ServiceReport
from .shutdown_manager import ShutdownManager, ShutdownReport
from .startup_context import StartupContext
from .startup_manager import StartupManager, StartupManagerConfig
from .startup_state import (
    BootstrapError,
    BootstrapStage,
    ShutdownError,
    StageStatus,
    StartupStageResult,
    SystemPhase,
    ValidationFinding,
    ValidationSeverity,
    is_valid_transition,
)
from .startup_validator import StartupValidator, ValidationReport
from .system_state import SystemState, get_system_state

__version__ = "0.1.0"
__status__  = "implemented"
__wave__    = 2
__layer__   = "BOOTSTRAP"
__owner__   = "Platform"
__foundation__ = "IIOS-FCR-001"

__all__ = [
    # Engine
    "BootstrapEngine",
    # Lifecycle
    "LifecycleManager",
    "LifecycleError",
    # Shutdown
    "ShutdownManager",
    "ShutdownReport",
    # Startup
    "StartupManager",
    "StartupManagerConfig",
    "StartupContext",
    # Validation
    "StartupValidator",
    "ValidationReport",
    # State / phase
    "SystemPhase",
    "SystemState",
    "get_system_state",
    "is_valid_transition",
    # Result types
    "BootstrapStage",
    "BootstrapError",
    "ShutdownError",
    "StageStatus",
    "StartupStageResult",
    "ValidationFinding",
    "ValidationSeverity",
    # Loaders (individual use)
    "RepositoryValidator",
    "RepositoryReport",
    "EnvironmentLoader",
    "EnvironmentSnapshot",
    "ConfigurationLoader",
    "ConfigurationSnapshot",
    "DependencyLoader",
    "DependencyReport",
    "DependencyTier",
    "ModuleLoader",
    "ModuleLoadError",
    "ServiceLoader",
    "ServiceRegistry",
    "ServiceReport",
]

