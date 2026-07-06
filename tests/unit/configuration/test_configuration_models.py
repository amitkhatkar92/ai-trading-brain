"""
tests/unit/configuration/test_configuration_models.py
=======================================================
Unit tests for configuration dataclass models.
"""

from __future__ import annotations

import pytest
from iios.configuration.configuration_models import (
    AIConfiguration,
    DatabaseConfiguration,
    DecisionConfiguration,
    ExecutionConfiguration,
    IIOSConfiguration,
    LoggingConfiguration,
    NotificationConfiguration,
    PortfolioConfiguration,
    RiskConfiguration,
    SecurityConfiguration,
    SystemConfiguration,
    MonitoringConfiguration,
    StrategyConfiguration,
)


# ---------------------------------------------------------------------------
# SystemConfiguration
# ---------------------------------------------------------------------------


class TestSystemConfiguration:
    def test_defaults(self):
        cfg = SystemConfiguration()
        assert cfg.env == "development"
        assert cfg.paper_trading is True
        assert cfg.layers == 17
        assert cfg.debug is False
        assert cfg.timezone == "Asia/Kolkata"
        assert cfg.market == "NSE"

    def test_mutation(self):
        cfg = SystemConfiguration()
        cfg.env = "production"
        assert cfg.env == "production"


# ---------------------------------------------------------------------------
# RiskConfiguration — architecture invariants
# ---------------------------------------------------------------------------


class TestRiskConfiguration:
    def test_certified_vix_threshold(self):
        cfg = RiskConfiguration()
        assert cfg.vix_threshold == 45.0

    def test_certified_daily_loss_pct(self):
        cfg = RiskConfiguration()
        assert cfg.daily_loss_pct == 0.02

    def test_certified_max_drawdown(self):
        cfg = RiskConfiguration()
        assert cfg.max_drawdown_pct == 0.15

    def test_custom_values(self):
        cfg = RiskConfiguration(vix_threshold=50.0)
        assert cfg.vix_threshold == 50.0


# ---------------------------------------------------------------------------
# DecisionConfiguration — architecture invariants
# ---------------------------------------------------------------------------


class TestDecisionConfiguration:
    def test_certified_threshold(self):
        cfg = DecisionConfiguration()
        assert cfg.decision_threshold == 6.5

    def test_certified_debate_agents(self):
        cfg = DecisionConfiguration()
        assert cfg.debate_agents == 5


# ---------------------------------------------------------------------------
# DatabaseConfiguration
# ---------------------------------------------------------------------------


class TestDatabaseConfiguration:
    def test_defaults(self):
        cfg = DatabaseConfiguration()
        assert cfg.path == "data/iios.db"
        assert cfg.wal_mode is True
        assert cfg.timeout_seconds == 30.0
        assert cfg.max_connections == 5

    def test_custom_path(self):
        cfg = DatabaseConfiguration(path=":memory:")
        assert cfg.path == ":memory:"


# ---------------------------------------------------------------------------
# ExecutionConfiguration
# ---------------------------------------------------------------------------


class TestExecutionConfiguration:
    def test_defaults(self):
        cfg = ExecutionConfiguration()
        assert cfg.broker_primary == "dhan"
        assert cfg.broker_fallback == "yahoo"
        assert cfg.live_trading_enabled is False
        assert cfg.paper_trades_path == "data/paper_trades.csv"

    def test_dhan_fields_default_empty(self):
        cfg = ExecutionConfiguration()
        assert cfg.dhan_client_id == ""
        assert cfg.dhan_access_token == ""


# ---------------------------------------------------------------------------
# MonitoringConfiguration
# ---------------------------------------------------------------------------


class TestMonitoringConfiguration:
    def test_defaults(self):
        cfg = MonitoringConfiguration()
        assert cfg.streamlit_port == 8501
        assert cfg.dashboard_enabled is True
        assert cfg.telemetry_enabled is True


# ---------------------------------------------------------------------------
# LoggingConfiguration
# ---------------------------------------------------------------------------


class TestLoggingConfiguration:
    def test_defaults(self):
        cfg = LoggingConfiguration()
        assert cfg.level == "INFO"
        assert "logs/" in cfg.file
        assert cfg.console_enabled is True
        assert cfg.file_enabled is True
        assert cfg.sensitive_redaction is True


# ---------------------------------------------------------------------------
# NotificationConfiguration
# ---------------------------------------------------------------------------


class TestNotificationConfiguration:
    def test_defaults(self):
        cfg = NotificationConfiguration()
        assert cfg.enabled is False
        assert cfg.telegram_bot_token == ""
        assert cfg.telegram_chat_id == ""
        assert isinstance(cfg.telegram_whitelist_ids, list)


# ---------------------------------------------------------------------------
# PortfolioConfiguration
# ---------------------------------------------------------------------------


class TestPortfolioConfiguration:
    def test_defaults(self):
        cfg = PortfolioConfiguration()
        assert cfg.initial_capital == 100_000.0
        assert cfg.max_positions == 5
        assert cfg.max_sector_exposure_pct == 0.30
        assert cfg.min_cash_reserve_pct == 0.10


# ---------------------------------------------------------------------------
# SecurityConfiguration
# ---------------------------------------------------------------------------


class TestSecurityConfiguration:
    def test_defaults(self):
        cfg = SecurityConfiguration()
        assert cfg.encryption_enabled is False
        assert cfg.audit_logging is True
        assert cfg.key_rotation_days == 30


# ---------------------------------------------------------------------------
# StrategyConfiguration
# ---------------------------------------------------------------------------


class TestStrategyConfiguration:
    def test_defaults(self):
        cfg = StrategyConfiguration()
        assert cfg.max_active_strategies == 10
        assert cfg.min_signal_rr_ratio == 1.5
        assert cfg.evolution_enabled is True
        assert cfg.continuous_scan is False


# ---------------------------------------------------------------------------
# AIConfiguration
# ---------------------------------------------------------------------------


class TestAIConfiguration:
    def test_defaults(self):
        cfg = AIConfiguration()
        assert cfg.knn_neighbors == 5
        assert cfg.min_win_rate == 0.50
        assert cfg.min_sharpe_ratio == 0.80
        assert cfg.max_drawdown == 0.15
        assert cfg.auto_disable_losing_strategies is True


# ---------------------------------------------------------------------------
# IIOSConfiguration (root)
# ---------------------------------------------------------------------------


class TestIIOSConfiguration:
    def test_sections_present(self):
        cfg = IIOSConfiguration()
        assert isinstance(cfg.system, SystemConfiguration)
        assert isinstance(cfg.risk, RiskConfiguration)
        assert isinstance(cfg.decision, DecisionConfiguration)
        assert isinstance(cfg.execution, ExecutionConfiguration)

    def test_get_dotted_key(self):
        cfg = IIOSConfiguration()
        assert cfg.get("risk.vix_threshold") == 45.0
        assert cfg.get("decision.decision_threshold") == 6.5
        assert cfg.get("system.paper_trading") is True

    def test_get_missing_key(self):
        cfg = IIOSConfiguration()
        assert cfg.get("does_not_exist", "fallback") == "fallback"

    def test_set_dotted_key(self):
        cfg = IIOSConfiguration()
        cfg.set("system.env", "production")
        assert cfg.system.env == "production"

    def test_set_invalid_section_raises(self):
        cfg = IIOSConfiguration()
        with pytest.raises(KeyError):
            cfg.set("nonexistent.field", 99)

    def test_set_invalid_field_raises(self):
        cfg = IIOSConfiguration()
        with pytest.raises(KeyError):
            cfg.set("risk.nonexistent_field", 99)

    def test_to_dict_keys(self):
        cfg = IIOSConfiguration()
        d = cfg.to_dict()
        assert "risk" in d
        assert "decision" in d
        assert "system" in d
        assert "execution" in d

    def test_sections_list(self):
        cfg = IIOSConfiguration()
        sections = cfg.sections()
        assert "risk" in sections
        assert "system" in sections
        assert "decision" in sections
        assert "metadata" not in sections

    def test_defaults_class_method(self):
        cfg = IIOSConfiguration.defaults()
        assert isinstance(cfg, IIOSConfiguration)
        assert cfg.system.layers == 17
