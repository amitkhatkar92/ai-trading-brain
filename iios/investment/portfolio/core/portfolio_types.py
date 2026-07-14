"""iios/investment/portfolio/core/portfolio_types.py

Framework-level type enumerations for the Institutional Portfolio Framework.
These extend and compose with the base enums in portfolio_constants.py.
"""
from __future__ import annotations

from enum import Enum


class PortfolioLifecycleState(str, Enum):
    """States in the institutional portfolio lifecycle state machine."""

    REGISTERED  = "registered"   # Class registered with framework
    INITIALIZED = "initialized"  # Instance created, config loaded
    READY       = "ready"        # Validated, prepared, ready to construct
    CONSTRUCTED = "constructed"  # Portfolio constructed with initial positions
    ACTIVE      = "active"       # Live, accepting orders/updates
    MONITORING  = "monitoring"   # Active monitoring mode
    REBALANCED  = "rebalanced"   # Post-rebalance checkpoint
    PAUSED      = "paused"       # Suspended temporarily
    ARCHIVED    = "archived"     # Closed and archived (terminal)
    FAILED      = "failed"       # Unrecoverable error (terminal)

    @property
    def is_terminal(self) -> bool:
        return self in (PortfolioLifecycleState.ARCHIVED, PortfolioLifecycleState.FAILED)

    @property
    def is_operational(self) -> bool:
        return self in (
            PortfolioLifecycleState.ACTIVE,
            PortfolioLifecycleState.MONITORING,
            PortfolioLifecycleState.REBALANCED,
        )

    @property
    def accepts_orders(self) -> bool:
        return self in (
            PortfolioLifecycleState.ACTIVE,
            PortfolioLifecycleState.MONITORING,
        )


class PortfolioDomain(str, Enum):
    """Nine canonical portfolio domains managed by IIOS."""

    LONG_TERM    = "long_term"    # Long-Term Investment Portfolio
    SWING        = "swing"        # Swing Trading Portfolio
    INTRADAY     = "intraday"     # Intraday Portfolio
    ETF          = "etf"          # ETF Portfolio
    DIVIDEND     = "dividend"     # Dividend Portfolio
    OPTIONS      = "options"      # Options Portfolio
    FUTURES      = "futures"      # Futures Portfolio
    CRYPTO       = "crypto"       # Crypto Portfolio
    MULTI_ASSET  = "multi_asset"  # Multi-Asset Portfolio
    CUSTOM       = "custom"       # Custom / experimental

    @property
    def default_horizon_days(self) -> int:
        _map = {
            "long_term":   1825,   # 5 years
            "swing":       14,
            "intraday":    1,
            "etf":         365,
            "dividend":    365,
            "options":     30,
            "futures":     90,
            "crypto":      180,
            "multi_asset": 365,
            "custom":      365,
        }
        return _map.get(self.value, 365)


class PortfolioCapability(str, Enum):
    """Capabilities that a portfolio implementation may declare."""

    LONG_POSITIONS          = "long_positions"
    SHORT_POSITIONS         = "short_positions"
    LEVERAGE                = "leverage"
    DERIVATIVES             = "derivatives"
    MULTI_CURRENCY          = "multi_currency"
    MULTI_BROKER            = "multi_broker"
    MULTI_CUSTODIAN         = "multi_custodian"
    FRACTIONAL_SHARES       = "fractional_shares"
    INTRADAY_REBALANCING    = "intraday_rebalancing"
    TAX_LOSS_HARVESTING     = "tax_loss_harvesting"
    DIVIDEND_REINVESTMENT   = "dividend_reinvestment"
    DYNAMIC_ALLOCATION      = "dynamic_allocation"
    AI_GOVERNANCE           = "ai_governance"
    STREAMING_POSITIONS     = "streaming_positions"
    AUDIT_TRAIL             = "audit_trail"
    INSTITUTIONAL_GRADE     = "institutional_grade"


class FrameworkStatus(str, Enum):
    """Operational status of the PortfolioFramework itself."""

    INITIALIZING = "initializing"
    RUNNING      = "running"
    DEGRADED     = "degraded"
    STOPPED      = "stopped"

    @property
    def is_accepting(self) -> bool:
        return self in (FrameworkStatus.RUNNING, FrameworkStatus.DEGRADED)


class ValidationOutcome(str, Enum):
    """Result of portfolio configuration or input validation."""

    PASSED   = "passed"
    WARNING  = "warning"
    FAILED   = "failed"

    @property
    def is_blocking(self) -> bool:
        return self == ValidationOutcome.FAILED


class PublishChannel(str, Enum):
    """Channels through which portfolio events are published."""

    INTERNAL   = "internal"   # In-process event bus
    AUDIT      = "audit"      # Audit framework
    EXECUTION  = "execution"  # Execution layer
    MONITORING = "monitoring" # Monitoring / dashboard
    KNOWLEDGE  = "knowledge"  # Knowledge layer
    EXTERNAL   = "external"   # External consumers (webhooks, streams)


class PortfolioVersion(str, Enum):
    """Versioning scheme used by portfolio templates."""

    V1 = "v1"
    V2 = "v2"
    V3 = "v3"

    @classmethod
    def latest(cls) -> "PortfolioVersion":
        return cls.V3
