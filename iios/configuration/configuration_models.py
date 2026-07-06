"""
iios/configuration/configuration_models.py
============================================
Dataclass models for every IIOS configuration section.

Each section maps to one layer (or group of related layers) in the 17-layer
IIOS pipeline. All fields carry sensible defaults that match the certified
architecture constants from IIOS-FCR-001.

Models are intentionally plain dataclasses — no Pydantic dependency.
Validation is performed separately by ``ConfigurationValidator``.

Architecture Reference: IIOS-CIS-001 INFRA-CFG-001
Foundation: IIOS-FCR-001 (CERTIFIED)
"""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from typing import Any, Optional

__all__ = [
    "SystemConfiguration",
    "InfrastructureConfiguration",
    "DatabaseConfiguration",
    "KnowledgeConfiguration",
    "OntologyConfiguration",
    "AIConfiguration",
    "ObservationConfiguration",
    "ReasoningConfiguration",
    "DecisionConfiguration",
    "StrategyConfiguration",
    "PortfolioConfiguration",
    "RiskConfiguration",
    "ExecutionConfiguration",
    "MonitoringConfiguration",
    "LoggingConfiguration",
    "NotificationConfiguration",
    "SecurityConfiguration",
    "PluginConfiguration",
    "IIOSConfiguration",
    "ConfigurationMetadata",
]


# ---------------------------------------------------------------------------
# Metadata
# ---------------------------------------------------------------------------


@dataclass
class ConfigurationMetadata:
    """Metadata attached to a loaded configuration snapshot."""

    version: int = 0
    loaded_at: float = field(default_factory=time.monotonic)
    loaded_at_wall: str = ""         # ISO-8601 string
    sources: list[str] = field(default_factory=list)
    environment: str = "development"
    checksum: str = ""               # SHA-256 of serialized config
    run_id: str = ""


# ---------------------------------------------------------------------------
# System Configuration (cross-cutting)
# ---------------------------------------------------------------------------


@dataclass
class SystemConfiguration:
    """Cross-cutting system settings."""

    env: str = "development"
    paper_trading: bool = True       # Must remain True until SYSTEM_CERTIFIED
    layers: int = 17                 # Invariant: FC-RULE-001
    debug: bool = False
    timezone: str = "Asia/Kolkata"   # NSE/BSE timezone
    market: str = "NSE"
    cycle_interval_seconds: float = 60.0
    startup_timeout_seconds: float = 120.0


# ---------------------------------------------------------------------------
# Infrastructure Configuration
# ---------------------------------------------------------------------------


@dataclass
class InfrastructureConfiguration:
    """Infrastructure service settings (DI, lifecycle, observability)."""

    service_registry_enabled: bool = True
    di_container_enabled: bool = True
    health_check_interval_seconds: float = 30.0
    health_check_timeout_seconds: float = 10.0
    max_startup_retries: int = 3
    startup_retry_delay_seconds: float = 5.0
    graceful_shutdown_timeout_seconds: float = 30.0
    thread_pool_size: int = 4
    event_bus_enabled: bool = True
    event_bus_queue_size: int = 1000


# ---------------------------------------------------------------------------
# Database Configuration
# ---------------------------------------------------------------------------


@dataclass
class DatabaseConfiguration:
    """SQLite database settings."""

    path: str = "data/iios.db"
    wal_mode: bool = True
    synchronous: str = "NORMAL"
    cache_size_kb: int = 32_000      # 32 MB page cache
    timeout_seconds: float = 30.0
    max_connections: int = 5
    backup_enabled: bool = False
    backup_interval_hours: int = 24
    backup_path: str = "data/backups/"
    schema_version: int = 1


# ---------------------------------------------------------------------------
# Knowledge Configuration (Layer 2 + knowledge base)
# ---------------------------------------------------------------------------


@dataclass
class KnowledgeConfiguration:
    """Knowledge base settings."""

    enabled: bool = True
    cache_ttl_seconds: int = 3600
    symbols_file: str = "resources/symbols/nse_symbols.csv"
    sector_map_file: str = "resources/symbols/sector_map.yaml"
    index_symbols: list[str] = field(
        default_factory=lambda: ["NIFTY", "BANKNIFTY", "^NSEI", "^NSEBANK"]
    )
    market_hours_open: str = "09:15"
    market_hours_close: str = "15:30"
    pre_market_open: str = "09:00"


# ---------------------------------------------------------------------------
# Ontology Configuration
# ---------------------------------------------------------------------------


@dataclass
class OntologyConfiguration:
    """Market ontology settings."""

    enabled: bool = True
    entity_cache_size: int = 10_000
    relationship_depth: int = 3
    auto_update: bool = True
    update_interval_hours: int = 1


# ---------------------------------------------------------------------------
# AI Configuration (Layers 1-3, 13-16)
# ---------------------------------------------------------------------------


@dataclass
class AIConfiguration:
    """AI/ML subsystem settings."""

    # MetaLearning (Layer 3) — k-NN predictor
    knn_neighbors: int = 5
    knn_feature_window: int = 20
    regime_lookback_days: int = 60
    regime_update_interval_seconds: int = 300

    # Strategy performance tracking (Layer 13)
    min_win_rate: float = 0.50       # CERTIFIED_WIN_RATE_MIN
    min_sharpe_ratio: float = 0.80   # CERTIFIED_SHARPE_MIN
    max_drawdown: float = 0.15       # CERTIFIED_MAX_DRAWDOWN
    auto_disable_losing_strategies: bool = True
    auto_disable_consecutive_losses: int = 5
    performance_window_days: int = 30

    # Walk-forward testing (Layer 14)
    wft_in_sample_days: int = 252    # 1 trading year
    wft_out_sample_days: int = 63    # 1 trading quarter
    wft_min_oos_trades: int = 20

    # Research Lab gates (Layer 15)
    promotion_win_rate: float = 0.50
    promotion_sharpe: float = 0.80
    promotion_max_dd: float = 0.15
    promotion_min_trades: int = 30


# ---------------------------------------------------------------------------
# Observation Configuration
# ---------------------------------------------------------------------------


@dataclass
class ObservationConfiguration:
    """Market observation / data feed settings."""

    primary_feed: str = "dhan"
    fallback_feed: str = "yahoo"
    quote_cache_ttl_seconds: int = 5
    history_cache_ttl_seconds: int = 60
    max_symbols_per_request: int = 100
    request_timeout_seconds: float = 8.0
    retry_attempts: int = 3
    retry_delay_seconds: float = 1.0
    options_chain_enabled: bool = True
    continuous_scan_interval_seconds: int = 30


# ---------------------------------------------------------------------------
# Reasoning Configuration (Layers 1-3)
# ---------------------------------------------------------------------------


@dataclass
class ReasoningConfiguration:
    """Reasoning layer settings."""

    global_intelligence_cache_ttl_seconds: int = 300    # 5 min
    global_intelligence_sla_ms: int = 5_000            # Warn threshold
    global_intelligence_crit_ms: int = 12_000          # Critical threshold
    market_intelligence_sla_ms: int = 2_000
    market_intelligence_crit_ms: int = 5_000
    meta_learning_sla_ms: int = 2_000
    opportunity_scan_threshold: float = 0.6             # Min signal quality


# ---------------------------------------------------------------------------
# Decision Configuration (Layer 10)
# ---------------------------------------------------------------------------


@dataclass
class DecisionConfiguration:
    """Layer 10 DebateAndDecision settings.

    CRITICAL: decision_threshold and debate_agents are architecture-invariant.
    Changing them requires Architecture Council approval (FC-RULE-017).
    """

    decision_threshold: float = 6.5      # FC-RULE-017 — INVARIANT
    debate_agents: int = 5               # INVARIANT — exactly 5
    debate_timeout_seconds: float = 10.0
    consensus_required: bool = False
    confidence_weights: list[float] = field(
        default_factory=lambda: [0.2, 0.2, 0.2, 0.2, 0.2]
    )
    cooldown_seconds: int = 60           # Min gap between decisions on same symbol
    max_concurrent_decisions: int = 3


# ---------------------------------------------------------------------------
# Strategy Configuration (Layers 4-5)
# ---------------------------------------------------------------------------


@dataclass
class StrategyConfiguration:
    """Strategy lab and scanning settings."""

    max_active_strategies: int = 10
    min_signal_rr_ratio: float = 1.5     # Minimum reward:risk
    evolution_enabled: bool = True
    evolution_generations: int = 50
    evolution_population_size: int = 20
    backtest_lookback_days: int = 252
    continuous_scan: bool = False
    scan_interval_seconds: int = 30
    scan_symbols_per_cycle: int = 50
    options_enabled: bool = True
    futures_enabled: bool = False
    intraday_enabled: bool = True
    swing_enabled: bool = False


# ---------------------------------------------------------------------------
# Portfolio Configuration
# ---------------------------------------------------------------------------


@dataclass
class PortfolioConfiguration:
    """Portfolio allocation settings."""

    initial_capital: float = 100_000.0
    max_positions: int = 5
    max_sector_exposure_pct: float = 0.30
    max_single_position_pct: float = 0.20
    min_cash_reserve_pct: float = 0.10
    rebalance_threshold_pct: float = 0.05
    rebalance_interval_days: int = 7


# ---------------------------------------------------------------------------
# Risk Configuration (Layers 6-9)
# ---------------------------------------------------------------------------


@dataclass
class RiskConfiguration:
    """Risk management settings.

    CRITICAL: vix_threshold and daily_loss_pct are architecture-invariant.
    Changing them requires Architecture Council approval (FC-RULE-018).
    """

    # Kill switch thresholds — INVARIANT (FC-RULE-018)
    vix_threshold: float = 45.0          # FC-RULE-018 — INVARIANT
    daily_loss_pct: float = 0.02         # FC-RULE-018 — 2% daily drawdown limit

    # Position sizing (Layer 6)
    max_risk_per_trade_pct: float = 0.01  # 1% per trade
    kelly_fraction: float = 0.25          # Fractional Kelly
    atr_multiplier: float = 2.0           # ATR-based stop distance

    # Stress testing (Layer 7-8)
    stress_scenarios: int = 14
    monte_carlo_simulations: int = 10_000
    monte_carlo_confidence: float = 0.95

    # Portfolio risk
    max_portfolio_var_pct: float = 0.05   # 5% Value-at-Risk
    max_portfolio_cvar_pct: float = 0.08  # 8% Conditional VaR
    max_drawdown_pct: float = 0.15        # Layer 9 secondary kill

    # Correlation limits
    max_correlation: float = 0.70         # Max cross-position correlation


# ---------------------------------------------------------------------------
# Execution Configuration (Layers 11-12)
# ---------------------------------------------------------------------------


@dataclass
class ExecutionConfiguration:
    """Order execution and broker settings."""

    broker_primary: str = "dhan"
    broker_fallback: str = "yahoo"        # Data fallback only
    dhan_client_id: str = ""
    dhan_access_token: str = ""           # Daily rotating token
    paper_trades_path: str = "data/paper_trades.csv"
    live_trading_enabled: bool = False    # Must remain False until SYSTEM_CERTIFIED
    order_timeout_seconds: float = 30.0
    max_slippage_pct: float = 0.005       # 0.5% max slippage
    use_limit_orders: bool = True
    limit_order_buffer_pct: float = 0.001 # 0.1% buffer from market price
    max_orders_per_minute: int = 10
    duplicate_order_window_seconds: int = 60


# ---------------------------------------------------------------------------
# Monitoring Configuration (Layer 17)
# ---------------------------------------------------------------------------


@dataclass
class MonitoringConfiguration:
    """Layer 17 ControlTower / dashboard settings."""

    dashboard_enabled: bool = True
    streamlit_port: int = 8501
    streamlit_host: str = "0.0.0.0"
    telemetry_enabled: bool = True
    metrics_interval_seconds: int = 10
    alert_on_layer_crit: bool = True
    retain_metrics_days: int = 30
    event_bus_enabled: bool = True


# ---------------------------------------------------------------------------
# Logging Configuration
# ---------------------------------------------------------------------------


@dataclass
class LoggingConfiguration:
    """Logging settings."""

    level: str = "INFO"
    file: str = "logs/iios.log"
    rotation: str = "1 day"
    retention: str = "7 days"
    format: str = "%(asctime)s %(levelname)-8s %(name)-40s %(message)s"
    date_format: str = "%Y-%m-%dT%H:%M:%S"
    console_enabled: bool = True
    file_enabled: bool = True
    json_enabled: bool = False           # Structured JSON logs
    sensitive_redaction: bool = True


# ---------------------------------------------------------------------------
# Notification Configuration
# ---------------------------------------------------------------------------


@dataclass
class NotificationConfiguration:
    """Telegram bot and alert settings."""

    enabled: bool = False
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    telegram_whitelist_ids: list[str] = field(default_factory=list)
    alert_on_trade: bool = True
    alert_on_kill_switch: bool = True
    alert_on_strategy_disable: bool = True
    alert_on_daily_summary: bool = True
    daily_summary_time: str = "15:35"    # After NSE close
    rate_limit_per_minute: int = 10


# ---------------------------------------------------------------------------
# Security Configuration
# ---------------------------------------------------------------------------


@dataclass
class SecurityConfiguration:
    """Security and secrets settings."""

    encryption_enabled: bool = False     # Requires cryptography package
    secrets_backend: str = "env"         # env | file | vault
    secrets_file: str = ".secrets"
    key_rotation_days: int = 30
    audit_logging: bool = True
    audit_file: str = "logs/audit.log"
    allowed_environments: list[str] = field(
        default_factory=lambda: ["development", "testing", "production"]
    )
    require_https: bool = False          # Enforce for production


# ---------------------------------------------------------------------------
# Plugin Configuration
# ---------------------------------------------------------------------------


@dataclass
class PluginConfiguration:
    """Optional plugin settings."""

    enabled: bool = False
    plugin_dir: str = "plugins/"
    auto_discover: bool = True
    plugins: list[str] = field(default_factory=list)
    plugin_timeout_seconds: float = 10.0


# ---------------------------------------------------------------------------
# Root Configuration (aggregates all sections)
# ---------------------------------------------------------------------------


@dataclass
class IIOSConfiguration:
    """Root configuration object — contains all 17 section configurations.

    This is the single object distributed to all IIOS subsystems.
    It is immutable after construction: call ``replace()`` to produce a
    modified copy.
    """

    system:         SystemConfiguration         = field(default_factory=SystemConfiguration)
    infrastructure: InfrastructureConfiguration = field(default_factory=InfrastructureConfiguration)
    database:       DatabaseConfiguration       = field(default_factory=DatabaseConfiguration)
    knowledge:      KnowledgeConfiguration      = field(default_factory=KnowledgeConfiguration)
    ontology:       OntologyConfiguration       = field(default_factory=OntologyConfiguration)
    ai:             AIConfiguration             = field(default_factory=AIConfiguration)
    observation:    ObservationConfiguration    = field(default_factory=ObservationConfiguration)
    reasoning:      ReasoningConfiguration      = field(default_factory=ReasoningConfiguration)
    decision:       DecisionConfiguration       = field(default_factory=DecisionConfiguration)
    strategy:       StrategyConfiguration       = field(default_factory=StrategyConfiguration)
    portfolio:      PortfolioConfiguration      = field(default_factory=PortfolioConfiguration)
    risk:           RiskConfiguration           = field(default_factory=RiskConfiguration)
    execution:      ExecutionConfiguration      = field(default_factory=ExecutionConfiguration)
    monitoring:     MonitoringConfiguration     = field(default_factory=MonitoringConfiguration)
    logging:        LoggingConfiguration        = field(default_factory=LoggingConfiguration)
    notification:   NotificationConfiguration   = field(default_factory=NotificationConfiguration)
    security:       SecurityConfiguration       = field(default_factory=SecurityConfiguration)
    plugin:         PluginConfiguration         = field(default_factory=PluginConfiguration)
    metadata:       ConfigurationMetadata       = field(default_factory=ConfigurationMetadata)

    # ─────────────────────────────────────────────────────────────────────────
    # Convenience accessors
    # ─────────────────────────────────────────────────────────────────────────

    def get(self, key: str, default: Any = None) -> Any:
        """Get a value by dotted key (e.g. ``"risk.vix_threshold"``)."""
        parts = key.split(".", 1)
        section_name = parts[0]
        field_name = parts[1] if len(parts) > 1 else None
        section = getattr(self, section_name, None)
        if section is None:
            return default
        if field_name is None:
            return section
        return getattr(section, field_name, default)

    def set(self, key: str, value: Any) -> None:
        """Set a value by dotted key. Mutates the section in-place."""
        parts = key.split(".", 1)
        if len(parts) != 2:
            raise ValueError(f"Key must be dotted (section.field), got: {key!r}")
        section_name, field_name = parts
        section = getattr(self, section_name, None)
        if section is None:
            raise KeyError(f"Unknown configuration section: {section_name!r}")
        if not hasattr(section, field_name):
            raise KeyError(f"Unknown field {field_name!r} in section {section_name!r}")
        setattr(section, field_name, value)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a nested dictionary (uses dataclasses.asdict)."""
        return asdict(self)

    def sections(self) -> list[str]:
        """Return all section names."""
        return [
            f.name for f in self.__dataclass_fields__.values()
            if f.name != "metadata"
        ]

    @classmethod
    def defaults(cls) -> "IIOSConfiguration":
        """Return a configuration populated entirely with certified defaults."""
        return cls()
