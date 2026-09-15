"""
tests/test_sandy_mcp_server.py
==================================
Self-Learning Ecosystem Phase 7c — Sandy VS Code chat/MCP surface.

T01  ask_sandy(query) delegates to SandySupervisor.answer(query)
T02  sandy_daily_digest() delegates to SandySupervisor.daily_digest()
T03  sandy_health_snapshot() returns a dict keyed by agent name, each
     value shaped like AgentHealthReport.to_dict()
T04  Exactly 3 tools are registered on the MCP server: ask_sandy,
     sandy_daily_digest, sandy_health_snapshot
T05  Never imports execution_engine/order_manager/broker/risk_control/dhan_feed
T06  .vscode/mcp.json is valid JSON and points at sandy_mcp_server.py
"""
from __future__ import annotations

import asyncio
import json
import os
from unittest.mock import MagicMock, patch

import pytest

import sandy.sandy_mcp_server as mcp_mod


class TestToolDelegation:
    def test_T01_ask_sandy_delegates(self):
        with patch("sandy.sandy_mcp_server.get_sandy_supervisor") as mock_get:
            mock_get.return_value.answer.return_value = "reply text"
            result = mcp_mod.ask_sandy("hi sandy")
        mock_get.return_value.answer.assert_called_once_with("hi sandy")
        assert result == "reply text"

    def test_T02_daily_digest_delegates(self):
        with patch("sandy.sandy_mcp_server.get_sandy_supervisor") as mock_get:
            mock_get.return_value.daily_digest.return_value = "digest text"
            result = mcp_mod.sandy_daily_digest()
        mock_get.return_value.daily_digest.assert_called_once()
        assert result == "digest text"

    def test_T03_health_snapshot_shape(self):
        from sandy.sandy_models import AgentHealthReport
        fake_report = AgentHealthReport(name="X", category="SELF_LEARNING_PHASE", stage="ACTIVE")
        with patch("sandy.sandy_mcp_server.get_sandy_supervisor") as mock_get:
            mock_get.return_value.poll_all_agents.return_value = {"X": fake_report}
            result = mcp_mod.sandy_health_snapshot()
        assert result == {"X": fake_report.to_dict()}


class TestServerRegistration:
    def test_T04_exactly_three_tools_registered(self):
        tools = asyncio.run(mcp_mod.server.list_tools())
        names = {t.name for t in tools}
        assert names == {"ask_sandy", "sandy_daily_digest", "sandy_health_snapshot"}


class TestSafetyContract:
    def test_T05_no_forbidden_imports(self):
        src_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "sandy", "sandy_mcp_server.py",
        )
        src = open(src_path, encoding="utf-8").read()
        for forbidden in ("execution_engine", "order_manager", "dhan_feed", "broker", "risk_control"):
            assert f"import {forbidden}" not in src, f"forbidden import found: {forbidden}"
            assert f"from {forbidden}" not in src, f"forbidden import found: {forbidden}"


class TestMcpJsonConfig:
    def test_T06_mcp_json_valid_and_wired(self):
        mcp_json_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            ".vscode", "mcp.json",
        )
        with open(mcp_json_path, encoding="utf-8") as f:
            config = json.load(f)
        assert "sandy" in config["servers"]
        entry = config["servers"]["sandy"]
        assert entry["type"] == "stdio"
        assert any("sandy_mcp_server.py" in a for a in entry["args"])
