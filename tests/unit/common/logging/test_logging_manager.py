"""tests/unit/common/logging/test_logging_manager.py
Unit tests for LoggingManager and get_logger().
"""
from __future__ import annotations

import io
import logging
from typing import List

import pytest

from iios.common.logging.logging_manager import (
    LoggingConfig,
    LoggingManager,
    get_logger,
    _level_int,
)
from iios.common.logging.structured_logger import StructuredLogger


@pytest.fixture(autouse=True)
def reset_manager():
    """Tear down after each test to avoid cross-test state."""
    yield
    LoggingManager.shutdown()
    # Remove all handlers from root logger that may have been added
    root = logging.getLogger()
    root.handlers.clear()


# ── _level_int helper ─────────────────────────────────────────────────────────

class TestLevelInt:

    def test_debug(self):    assert _level_int("DEBUG")    == logging.DEBUG
    def test_info(self):     assert _level_int("INFO")     == logging.INFO
    def test_warning(self):  assert _level_int("WARNING")  == logging.WARNING
    def test_error(self):    assert _level_int("ERROR")    == logging.ERROR
    def test_critical(self): assert _level_int("CRITICAL") == logging.CRITICAL

    def test_case_insensitive(self):
        assert _level_int("info") == logging.INFO
        assert _level_int("Debug") == logging.DEBUG

    def test_invalid_raises(self):
        with pytest.raises(ValueError, match="Unknown log level"):
            _level_int("INVALID")


# ── LoggingConfig ─────────────────────────────────────────────────────────────

class TestLoggingConfig:

    def test_defaults(self):
        cfg = LoggingConfig()
        assert cfg.level       == "INFO"
        assert cfg.console     is True
        assert cfg.json_console is False
        assert cfg.log_file    is None
        assert cfg.compress    is True
        assert cfg.backup_count == 10
        assert cfg.max_bytes   == 50 * 1024 * 1024

    def test_root_level_int(self):
        cfg = LoggingConfig(level="WARNING")
        assert cfg.root_level_int() == logging.WARNING

    def test_custom_values(self):
        cfg = LoggingConfig(level="DEBUG", json_console=True, console=False)
        assert cfg.level == "DEBUG"
        assert cfg.json_console is True
        assert cfg.console is False


# ── configure ─────────────────────────────────────────────────────────────────

class TestConfigure:

    def test_configure_sets_root_level(self):
        LoggingManager.configure(LoggingConfig(level="WARNING", console=False))
        assert logging.getLogger().level == logging.WARNING

    def test_configure_adds_console_handler(self):
        LoggingManager.configure(LoggingConfig(level="INFO", console=True))
        assert len(LoggingManager.handlers()) > 0

    def test_configure_no_console(self):
        LoggingManager.configure(LoggingConfig(console=False))
        # handlers managed by LoggingManager should be empty when console=False
        assert len(LoggingManager.handlers()) == 0

    def test_configure_applies_level_overrides(self):
        LoggingManager.configure(LoggingConfig(
            console=False,
            level_overrides={"iios.test.override": "DEBUG"},
        ))
        assert logging.getLogger("iios.test.override").level == logging.DEBUG

    def test_configure_silences_third_party(self):
        LoggingManager.configure(LoggingConfig(
            console=False,
            silence_third_party=True,
        ))
        assert logging.getLogger("urllib3").level == logging.WARNING
        assert logging.getLogger("requests").level == logging.WARNING

    def test_configure_idempotent(self):
        cfg = LoggingConfig(console=False)
        LoggingManager.configure(cfg)
        LoggingManager.configure(cfg)
        # Should not raise; handler count should not grow unboundedly
        assert len(LoggingManager.handlers()) == 0

    def test_default_config(self):
        LoggingManager.default_config()
        assert LoggingManager._initialized is True


# ── get_logger registry ───────────────────────────────────────────────────────

class TestGetLogger:

    def test_returns_structured_logger(self):
        sl = LoggingManager.get_logger("test.manager.get")
        assert isinstance(sl, StructuredLogger)

    def test_same_name_returns_same_instance(self):
        a = LoggingManager.get_logger("test.manager.same")
        b = LoggingManager.get_logger("test.manager.same")
        assert a is b

    def test_different_engine_id_returns_different_instance(self):
        a = LoggingManager.get_logger("test.manager.diff", engine_id="E1")
        b = LoggingManager.get_logger("test.manager.diff", engine_id="E2")
        assert a is not b

    def test_module_level_get_logger(self):
        sl = get_logger("test.module_level", engine_id="ENG-1")
        assert isinstance(sl, StructuredLogger)
        assert sl.engine_id == "ENG-1"

    def test_registered_loggers_returns_copy(self):
        LoggingManager.get_logger("test.reg.a")
        LoggingManager.get_logger("test.reg.b")
        registry = LoggingManager.registered_loggers()
        assert isinstance(registry, dict)
        # Modifying the copy doesn't affect internal state
        registry.clear()
        assert len(LoggingManager.registered_loggers()) >= 2


# ── set_level / get_level ─────────────────────────────────────────────────────

class TestLevelManagement:

    def test_set_level_changes_underlying_logger(self):
        LoggingManager.set_level("iios.level.test", "DEBUG")
        assert logging.getLogger("iios.level.test").level == logging.DEBUG

    def test_get_level_returns_name(self):
        logging.getLogger("iios.level.test2").setLevel(logging.ERROR)
        level = LoggingManager.get_level("iios.level.test2")
        assert level == "ERROR"

    def test_set_all_levels(self):
        LoggingManager.configure(LoggingConfig(console=False, level="INFO"))
        _ = LoggingManager.get_logger("iios.all.levels")
        LoggingManager.set_all_levels("DEBUG")
        assert logging.getLogger().level == logging.DEBUG


# ── add / remove handlers ─────────────────────────────────────────────────────

class TestHandlerManagement:

    def test_add_handler_appends(self):
        LoggingManager.configure(LoggingConfig(console=False))
        initial_count = len(LoggingManager.handlers())
        custom = logging.StreamHandler(io.StringIO())
        LoggingManager.add_handler(custom)
        assert len(LoggingManager.handlers()) == initial_count + 1

    def test_remove_handler(self):
        LoggingManager.configure(LoggingConfig(console=False))
        custom = logging.StreamHandler(io.StringIO())
        LoggingManager.add_handler(custom)
        LoggingManager.remove_handler(custom)
        assert custom not in LoggingManager.handlers()

    def test_remove_handler_not_in_list_does_not_raise(self):
        LoggingManager.configure(LoggingConfig(console=False))
        unregistered = logging.StreamHandler(io.StringIO())
        # Should not raise
        LoggingManager.remove_handler(unregistered)


# ── shutdown ──────────────────────────────────────────────────────────────────

class TestShutdown:

    def test_shutdown_clears_registry(self):
        LoggingManager.configure(LoggingConfig(console=False))
        LoggingManager.get_logger("iios.shutdown.test")
        LoggingManager.shutdown()
        assert LoggingManager.registered_loggers() == {}

    def test_shutdown_clears_initialized_flag(self):
        LoggingManager.configure(LoggingConfig(console=False))
        LoggingManager.shutdown()
        assert LoggingManager._initialized is False
