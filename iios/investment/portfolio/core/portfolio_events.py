"""iios/investment/portfolio/core/portfolio_events.py

Event type definitions for the Institutional Portfolio Framework.
Events are immutable frozen dataclasses dispatched through EventDispatcher.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class PortfolioEventType(str, Enum):
    """All event types emitted by the portfolio framework."""

    # Lifecycle events
    PORTFOLIO_REGISTERED     = "portfolio_registered"
    PORTFOLIO_INITIALIZED    = "portfolio_initialized"
    PORTFOLIO_READY          = "portfolio_ready"
    PORTFOLIO_CONSTRUCTED    = "portfolio_constructed"
    PORTFOLIO_ACTIVATED      = "portfolio_activated"
    PORTFOLIO_PAUSED         = "portfolio_paused"
    PORTFOLIO_RESUMED        = "portfolio_resumed"
    PORTFOLIO_ARCHIVED       = "portfolio_archived"
    PORTFOLIO_FAILED         = "portfolio_failed"

    # Operational events
    PORTFOLIO_UPDATED        = "portfolio_updated"
    PORTFOLIO_REBALANCED     = "portfolio_rebalanced"
    PORTFOLIO_EVALUATED      = "portfolio_evaluated"
    PORTFOLIO_MONITORED      = "portfolio_monitored"
    PORTFOLIO_PUBLISHED      = "portfolio_published"

    # Configuration events
    CONFIGURATION_LOADED     = "configuration_loaded"
    CONFIGURATION_UPDATED    = "configuration_updated"

    # Allocation events
    ALLOCATION_CHANGED       = "allocation_changed"
    POSITION_ADDED           = "position_added"
    POSITION_REMOVED         = "position_removed"
    POSITION_UPDATED         = "position_updated"

    # Alert events
    RISK_ALERT               = "risk_alert"
    PERFORMANCE_ALERT        = "performance_alert"
    DRAWDOWN_ALERT           = "drawdown_alert"
    CONCENTRATION_ALERT      = "concentration_alert"

    # Framework events
    FRAMEWORK_STARTED        = "framework_started"
    FRAMEWORK_STOPPED        = "framework_stopped"
    FRAMEWORK_DEGRADED       = "framework_degraded"

    @property
    def is_alert(self) -> bool:
        return self in (
            PortfolioEventType.RISK_ALERT,
            PortfolioEventType.PERFORMANCE_ALERT,
            PortfolioEventType.DRAWDOWN_ALERT,
            PortfolioEventType.CONCENTRATION_ALERT,
        )

    @property
    def is_lifecycle(self) -> bool:
        return self.value.startswith("portfolio_") and self not in (
            PortfolioEventType.PORTFOLIO_UPDATED,
            PortfolioEventType.PORTFOLIO_REBALANCED,
            PortfolioEventType.PORTFOLIO_EVALUATED,
            PortfolioEventType.PORTFOLIO_MONITORED,
            PortfolioEventType.PORTFOLIO_PUBLISHED,
        )


class EventPriority(str, Enum):
    """Dispatch priority for event handlers."""

    CRITICAL = "critical"   # Dispatched before NORMAL handlers
    NORMAL   = "normal"
    LOW      = "low"        # Background / analytics consumers


# ---------------------------------------------------------------------------
# Base event
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PortfolioEvent:
    """
    Base immutable event emitted by the portfolio framework.
    All concrete events inherit from this class.
    """

    event_id:     str              = field(default_factory=lambda: str(uuid.uuid4()))
    event_type:   PortfolioEventType = PortfolioEventType.PORTFOLIO_UPDATED
    portfolio_id: str              = ""
    source:       str              = "framework"
    priority:     EventPriority    = EventPriority.NORMAL
    emitted_at:   float            = field(default_factory=time.time)
    payload:      dict[str, Any]   = field(default_factory=dict)
    correlation_id: str            = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id":      self.event_id,
            "event_type":    self.event_type.value,
            "portfolio_id":  self.portfolio_id,
            "source":        self.source,
            "priority":      self.priority.value,
            "emitted_at":    self.emitted_at,
            "payload":       dict(self.payload),
            "correlation_id":self.correlation_id,
        }


# ---------------------------------------------------------------------------
# Concrete event types
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PortfolioRegisteredEvent(PortfolioEvent):
    event_type:  PortfolioEventType = PortfolioEventType.PORTFOLIO_REGISTERED
    domain:      str = ""
    class_name:  str = ""


@dataclass(frozen=True)
class PortfolioInitializedEvent(PortfolioEvent):
    event_type:      PortfolioEventType = PortfolioEventType.PORTFOLIO_INITIALIZED
    profile_name:    str = ""
    environment:     str = ""


@dataclass(frozen=True)
class PortfolioReadyEvent(PortfolioEvent):
    event_type:  PortfolioEventType = PortfolioEventType.PORTFOLIO_READY


@dataclass(frozen=True)
class PortfolioConstructedEvent(PortfolioEvent):
    event_type:      PortfolioEventType = PortfolioEventType.PORTFOLIO_CONSTRUCTED
    position_count:  int = 0
    initial_nav:     float = 0.0


@dataclass(frozen=True)
class PortfolioActivatedEvent(PortfolioEvent):
    event_type:  PortfolioEventType = PortfolioEventType.PORTFOLIO_ACTIVATED


@dataclass(frozen=True)
class PortfolioPausedEvent(PortfolioEvent):
    event_type:  PortfolioEventType = PortfolioEventType.PORTFOLIO_PAUSED
    reason:      str = ""


@dataclass(frozen=True)
class PortfolioResumedEvent(PortfolioEvent):
    event_type:  PortfolioEventType = PortfolioEventType.PORTFOLIO_RESUMED


@dataclass(frozen=True)
class PortfolioArchivedEvent(PortfolioEvent):
    event_type:  PortfolioEventType = PortfolioEventType.PORTFOLIO_ARCHIVED
    reason:      str = ""


@dataclass(frozen=True)
class PortfolioFailedEvent(PortfolioEvent):
    event_type:  PortfolioEventType = PortfolioEventType.PORTFOLIO_FAILED
    error:       str = ""
    traceback:   str = ""
    priority:    EventPriority = EventPriority.CRITICAL


@dataclass(frozen=True)
class PortfolioUpdatedEvent(PortfolioEvent):
    event_type:  PortfolioEventType = PortfolioEventType.PORTFOLIO_UPDATED
    change_type: str = ""
    version:     int = 0


@dataclass(frozen=True)
class PortfolioRebalancedEvent(PortfolioEvent):
    event_type:       PortfolioEventType = PortfolioEventType.PORTFOLIO_REBALANCED
    trigger:          str = ""
    trades_generated: int = 0


@dataclass(frozen=True)
class ConfigurationLoadedEvent(PortfolioEvent):
    event_type:   PortfolioEventType = PortfolioEventType.CONFIGURATION_LOADED
    profile_name: str = ""


@dataclass(frozen=True)
class AllocationChangedEvent(PortfolioEvent):
    event_type:      PortfolioEventType = PortfolioEventType.ALLOCATION_CHANGED
    symbol:          str   = ""
    old_weight:      float = 0.0
    new_weight:      float = 0.0
    change_reason:   str   = ""


@dataclass(frozen=True)
class RiskAlertEvent(PortfolioEvent):
    event_type:    PortfolioEventType = PortfolioEventType.RISK_ALERT
    alert_type:    str = ""
    threshold:     float = 0.0
    current_value: float = 0.0
    severity:      str = "warning"
    priority:      EventPriority = EventPriority.CRITICAL


@dataclass(frozen=True)
class PerformanceAlertEvent(PortfolioEvent):
    event_type:    PortfolioEventType = PortfolioEventType.PERFORMANCE_ALERT
    metric:        str = ""
    threshold:     float = 0.0
    current_value: float = 0.0
    severity:      str = "warning"


@dataclass(frozen=True)
class FrameworkStartedEvent(PortfolioEvent):
    event_type:        PortfolioEventType = PortfolioEventType.FRAMEWORK_STARTED
    portfolio_id:      str = "framework"
    framework_version: str = ""


@dataclass(frozen=True)
class FrameworkStoppedEvent(PortfolioEvent):
    event_type:   PortfolioEventType = PortfolioEventType.FRAMEWORK_STOPPED
    portfolio_id: str = "framework"
    uptime_seconds: float = 0.0
