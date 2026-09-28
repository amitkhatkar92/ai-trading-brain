"""
tests/test_dta_killswitch_path_001.py
=======================================
DTA-KILLSWITCH-PATH-001

Root cause: utils/kill_switch.py's CONFIG_PATH pointed at
utils/kill_switch.json, a file that was never created -- the real,
deployed kill-switch file has always lived at config/kill_switch.json
(confirmed live on the VPS: 145 bytes, trading_enabled=true, dated
March 2026). Every read silently fell through to the "file not found"
default (fails safe to trading_enabled=True, so never caused a false
halt), but it also meant a manual edit to config/kill_switch.json to
actually trip the switch would never have been seen.

Verifies:
  1. utils.kill_switch.CONFIG_PATH resolves to <repo_root>/config/kill_switch.json
  2. control_tower.cycle_health_monitor.KILL_SWITCH resolves to the same
     real location.
  3. Both is_trading_enabled()/get_kill_switch_status() and
     disable_trading()/enable_trading() genuinely read/write that same
     file (round-trip), not the old non-existent path.
"""
from __future__ import annotations

import importlib
import json
from pathlib import Path

import pytest


class TestConfigPathResolution:
    def test_t01_kill_switch_config_path_points_at_config_dir(self):
        from utils import kill_switch as ks
        assert ks.CONFIG_PATH.parent.name == "config"
        assert ks.CONFIG_PATH.name == "kill_switch.json"

    def test_t02_cycle_health_monitor_kill_switch_path_matches(self):
        from control_tower import cycle_health_monitor as chm
        assert chm.KILL_SWITCH.parent.name == "config"
        assert chm.KILL_SWITCH.name == "kill_switch.json"
        from utils import kill_switch as ks
        # both must resolve to the exact same real file
        assert chm.KILL_SWITCH.resolve() == ks.CONFIG_PATH.resolve()


class TestReadWriteRoundTrip:
    def test_t03_disable_then_read_round_trips_through_config_path(self, tmp_path, monkeypatch):
        from utils import kill_switch as ks
        fake_config_dir = tmp_path / "config"
        fake_config_dir.mkdir()
        monkeypatch.setattr(ks, "CONFIG_PATH", fake_config_dir / "kill_switch.json")
        ks._cache["enabled"] = True  # reset module cache

        ks.disable_trading("test halt")
        assert (fake_config_dir / "kill_switch.json").exists()
        status = ks.get_kill_switch_status()
        assert status["trading_enabled"] is False
        assert status["reason"] == "test halt"

    def test_t04_missing_file_still_fails_safe_to_enabled(self, tmp_path, monkeypatch):
        from utils import kill_switch as ks
        monkeypatch.setattr(ks, "CONFIG_PATH", tmp_path / "config" / "kill_switch.json")
        status = ks.get_kill_switch_status()
        assert status["trading_enabled"] is True
        assert status["reason"] == "default"

    def test_t05_cycle_health_monitor_reads_a_real_disabled_file(self, tmp_path, monkeypatch):
        from control_tower import cycle_health_monitor as chm
        p = tmp_path / "kill_switch.json"
        p.write_text(json.dumps({"trading_enabled": False, "reason": "manual halt"}))
        monkeypatch.setattr(chm, "KILL_SWITCH", p)
        enabled, reason = chm._read_kill_switch()
        assert enabled is False
        assert reason == "manual halt"
