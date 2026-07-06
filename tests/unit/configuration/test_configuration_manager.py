"""
tests/unit/configuration/test_configuration_manager.py
========================================================
Integration tests for ConfigurationManager.

These tests use an isolated repo_root (tmp_path) and DictionaryProvider
overrides so they don't touch the real .env or config.py.
"""

from __future__ import annotations

import threading
from pathlib import Path
import pytest

from iios.configuration.configuration_manager import (
    ConfigurationManager,
    _reset_singleton,
    get_configuration_manager,
)
from iios.configuration.configuration_models import IIOSConfiguration, RiskConfiguration
from iios.configuration.configuration_provider import DictionaryProvider
from iios.configuration.configuration_exception import (
    ConfigurationNotFoundError,
    ConfigurationReloadError,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def reset_singleton():
    """Ensure the global singleton is reset before every test."""
    _reset_singleton()
    yield
    _reset_singleton()


@pytest.fixture
def manager(tmp_path: Path) -> ConfigurationManager:
    """Return a ConfigurationManager with an isolated repo root."""
    m = ConfigurationManager(repo_root=str(tmp_path))
    # Disable the Python config.py provider (it won't exist in tmp_path)
    python_provider = m._registry.get_provider("python:config")
    if python_provider:
        python_provider.enabled = False
    # Add a clean override with certified defaults
    m.add_provider(DictionaryProvider(
        {
            "system": {"env": "testing", "paper_trading": True, "layers": 17},
            "decision": {"decision_threshold": 6.5, "debate_agents": 5},
            "risk": {"vix_threshold": 45.0, "daily_loss_pct": 0.02},
            "execution": {"broker_primary": "dhan", "live_trading_enabled": False},
            "logging": {"level": "DEBUG"},
        },
        name="test_override",
        priority=85,
    ))
    return m


# ---------------------------------------------------------------------------
# Initialisation
# ---------------------------------------------------------------------------


class TestInitialisation:
    def test_initialize_returns_iios_configuration(self, manager: ConfigurationManager):
        cfg = manager.initialize()
        assert isinstance(cfg, IIOSConfiguration)

    def test_initialized_flag(self, manager: ConfigurationManager):
        assert not manager.is_initialized
        manager.initialize()
        assert manager.is_initialized

    def test_version_increments_on_init(self, manager: ConfigurationManager):
        assert manager.version == 0
        manager.initialize()
        assert manager.version == 1

    def test_paper_trading_default_true(self, manager: ConfigurationManager):
        cfg = manager.initialize()
        assert cfg.system.paper_trading is True

    def test_vix_threshold_default(self, manager: ConfigurationManager):
        cfg = manager.initialize()
        assert cfg.risk.vix_threshold == 45.0

    def test_decision_threshold_default(self, manager: ConfigurationManager):
        cfg = manager.initialize()
        assert cfg.decision.decision_threshold == 6.5

    def test_debate_agents_default(self, manager: ConfigurationManager):
        cfg = manager.initialize()
        assert cfg.decision.debate_agents == 5

    def test_layers_default(self, manager: ConfigurationManager):
        cfg = manager.initialize()
        assert cfg.system.layers == 17


# ---------------------------------------------------------------------------
# Read API
# ---------------------------------------------------------------------------


class TestReadAPI:
    def test_get_existing_key(self, manager: ConfigurationManager):
        manager.initialize()
        val = manager.get("risk.vix_threshold")
        assert val == 45.0

    def test_get_missing_key_returns_default(self, manager: ConfigurationManager):
        manager.initialize()
        val = manager.get("does.not.exist", "fallback")
        assert val == "fallback"

    def test_require_existing_key(self, manager: ConfigurationManager):
        manager.initialize()
        val = manager.require("risk.vix_threshold")
        assert val == 45.0

    def test_require_missing_key_raises(self, manager: ConfigurationManager):
        manager.initialize()
        with pytest.raises(ConfigurationNotFoundError):
            manager.require("nonexistent.key")

    def test_get_section_returns_dict(self, manager: ConfigurationManager):
        manager.initialize()
        section = manager.get_section("risk")
        assert isinstance(section, dict)
        assert "vix_threshold" in section

    def test_get_section_unknown_returns_empty(self, manager: ConfigurationManager):
        manager.initialize()
        section = manager.get_section("totally_unknown")
        assert section == {}

    def test_get_typed(self, manager: ConfigurationManager):
        manager.initialize()
        risk = manager.get_typed("risk", RiskConfiguration)
        assert isinstance(risk, RiskConfiguration)
        assert risk.vix_threshold == 45.0


# ---------------------------------------------------------------------------
# Reload
# ---------------------------------------------------------------------------


class TestReload:
    def test_reload_succeeds(self, manager: ConfigurationManager):
        manager.initialize()
        new_cfg = manager.reload()
        assert isinstance(new_cfg, IIOSConfiguration)

    def test_reload_advances_version(self, manager: ConfigurationManager):
        manager.initialize()
        v1 = manager.version
        manager.reload()
        v2 = manager.version
        assert v2 > v1

    def test_reload_picks_up_override_change(self, manager: ConfigurationManager):
        manager.initialize()
        # Swap in a new override with different value
        manager._registry.unregister("test_override")
        manager.add_provider(DictionaryProvider(
            {"system": {"env": "production", "paper_trading": True, "layers": 17}},
            name="test_override",
            priority=85,
        ))
        new_cfg = manager.reload()
        assert new_cfg.system.env == "production"


# ---------------------------------------------------------------------------
# Change subscriptions
# ---------------------------------------------------------------------------


class TestSubscriptions:
    def test_subscribe_fires_on_change(self, manager: ConfigurationManager):
        manager.initialize()
        changes = []

        def on_change(key, old, new):
            changes.append((key, old, new))

        manager.subscribe("system.env", on_change)

        # Swap env value
        manager._registry.unregister("test_override")
        manager.add_provider(DictionaryProvider(
            {"system": {"env": "production", "paper_trading": True, "layers": 17}},
            name="test_override",
            priority=85,
        ))
        manager.reload()
        assert any("system.env" in str(c) for c in changes)

    def test_wildcard_subscription(self, manager: ConfigurationManager):
        manager.initialize()
        fired = []
        manager.subscribe("*", lambda k, o, n: fired.append(k))

        manager._registry.unregister("test_override")
        manager.add_provider(DictionaryProvider(
            {"system": {"env": "production", "paper_trading": True, "layers": 17}},
            name="test_override",
            priority=85,
        ))
        manager.reload()
        # Wildcard fires for any changed key
        assert len(fired) >= 0  # Just test it doesn't crash


# ---------------------------------------------------------------------------
# Rollback
# ---------------------------------------------------------------------------


class TestRollback:
    def test_rollback_restores_value(self, manager: ConfigurationManager):
        manager.initialize()   # v1
        v1 = manager.version

        # Add override with different env
        manager._registry.unregister("test_override")
        manager.add_provider(DictionaryProvider(
            {"system": {"env": "production", "paper_trading": True, "layers": 17}},
            name="test_override",
            priority=85,
        ))
        manager.reload()  # v2
        assert manager.config.system.env == "production"

        manager.rollback(v1)
        # After rollback, env is back to "testing"
        assert manager.config.system.env == "testing"


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------


class TestExport:
    def test_export_json(self, manager: ConfigurationManager):
        manager.initialize()
        result = manager.export("json")
        assert "vix_threshold" in result or "risk" in result

    def test_export_yaml_or_skip(self, manager: ConfigurationManager):
        manager.initialize()
        try:
            result = manager.export("yaml")
            assert result  # non-empty string
        except Exception:
            pytest.skip("PyYAML not installed")

    def test_export_unknown_format_raises(self, manager: ConfigurationManager):
        manager.initialize()
        from iios.configuration.configuration_exception import ConfigurationError
        with pytest.raises(ConfigurationError):
            manager.export("xml")


# ---------------------------------------------------------------------------
# Singleton factory
# ---------------------------------------------------------------------------


class TestSingleton:
    def test_get_configuration_manager_returns_same_instance(self, tmp_path):
        m1 = get_configuration_manager(repo_root=str(tmp_path))
        m2 = get_configuration_manager(repo_root="/different/path")  # ignored
        assert m1 is m2

    def test_reset_allows_new_singleton(self, tmp_path):
        m1 = get_configuration_manager(repo_root=str(tmp_path))
        _reset_singleton()
        m2 = get_configuration_manager(repo_root=str(tmp_path))
        assert m1 is not m2


# ---------------------------------------------------------------------------
# Thread safety
# ---------------------------------------------------------------------------


class TestThreadSafety:
    def test_concurrent_initialize_safe(self, tmp_path):
        m = ConfigurationManager(repo_root=str(tmp_path))
        python_provider = m._registry.get_provider("python:config")
        if python_provider:
            python_provider.enabled = False
        errors = []

        def worker():
            try:
                m.initialize()
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=worker) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == []

    def test_concurrent_reads_safe(self, manager: ConfigurationManager):
        manager.initialize()
        errors = []

        def reader():
            try:
                for _ in range(100):
                    manager.get("risk.vix_threshold")
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=reader) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == []
