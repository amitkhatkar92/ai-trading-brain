"""enterprise_ai_platform/common/logging/__init__.py
IIOS Common Logging Framework — public API.

All public symbols from the five sub-modules are re-exported here so
consumers only need a single import path:

    from enterprise_ai_platform.common.logging import (
        LoggingContext,
        LoggingManager, LoggingConfig, get_logger,
        StructuredLogger, JsonFormatter, TextFormatter,
        AuditLogger, AuditRecord, AuditEventType, get_audit_logger,
        PerformanceLogger, PerformanceRecord, get_performance_logger,
        LogRotationConfig,
        create_rotating_handler, create_timed_rotating_handler,
        configure_rotation,
    )
"""
from __future__ import annotations

from enterprise_ai_platform.common.logging.logging_context import LoggingContext

from enterprise_ai_platform.common.logging.structured_logger import (
    JsonFormatter,
    StructuredLogger,
    TextFormatter,
)

from enterprise_ai_platform.common.logging.logging_manager import (
    LoggingConfig,
    LoggingManager,
    get_logger,
)

from enterprise_ai_platform.common.logging.audit_logger import (
    AuditEventType,
    AuditLogger,
    AuditRecord,
    get_audit_logger,
)

from enterprise_ai_platform.common.logging.performance_logger import (
    PerformanceLogger,
    PerformanceRecord,
    get_performance_logger,
)

from enterprise_ai_platform.common.logging.log_rotation import (
    LogRotationConfig,
    configure_rotation,
    create_rotating_handler,
    create_timed_rotating_handler,
)

__all__ = [
    # Context
    "LoggingContext",
    # Structured logger
    "JsonFormatter",
    "StructuredLogger",
    "TextFormatter",
    # Manager
    "LoggingConfig",
    "LoggingManager",
    "get_logger",
    # Audit
    "AuditEventType",
    "AuditLogger",
    "AuditRecord",
    "get_audit_logger",
    # Performance
    "PerformanceLogger",
    "PerformanceRecord",
    "get_performance_logger",
    # Rotation
    "LogRotationConfig",
    "configure_rotation",
    "create_rotating_handler",
    "create_timed_rotating_handler",
]
