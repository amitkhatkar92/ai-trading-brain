"""
sandy/sandy_mcp_server.py
=============================
Self-Learning Ecosystem Phase 7c: VS Code chat/MCP surface for Sandy.

Exposes SandySupervisor's read-only query interface (built and tested in
Phase 7a/7b) as an MCP (Model Context Protocol) server, so VS Code's
chat/agent surface can query Sandy directly, alongside the existing
Telegram integration ("hi sandy", "sandy report", etc.).

Run manually:
    python sandy/sandy_mcp_server.py

Configured in .vscode/mcp.json as a local stdio server.

Dependency: `mcp` (pip install mcp) -- a LOCAL DEV TOOL ONLY, listed in
requirements-dev.txt. Deliberately NOT added to requirements.txt: the
production Docker image never needs this; it exists purely so this
repo's own developer can query Sandy from VS Code chat.

Safety contract: read-only. Every tool below only ever calls
SandySupervisor's own existing, already-tested, read-only methods
(poll_all_agents/answer/daily_digest) -- never mutates any agent's
state, never touches execution_engine/order_manager/broker/risk_control.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mcp.server.mcpserver import MCPServer

from sandy import get_sandy_supervisor

server = MCPServer(
    name="sandy",
    description=(
        "Sandy -- Master Meta-Learning Supervisor for the ai_trading_brain "
        "self-learning ecosystem. Read-only: reports on every self-learning "
        "agent's status, never trades, never mutates agent state."
    ),
)


@server.tool()
def ask_sandy(query: str) -> str:
    """
    Ask Sandy a fixed-keyword question about the self-learning agents.
    Recognised forms: "hi sandy" / "sandy", "sandy report",
    "sandy status <name>", "sandy help". Anything else gets Sandy's
    standard "didn't recognise that" fallback -- same behavior as Telegram.
    """
    return get_sandy_supervisor().answer(query)


@server.tool()
def sandy_daily_digest() -> str:
    """Full, current status digest of every self-learning agent (same content as Sandy's EOD Telegram push)."""
    return get_sandy_supervisor().daily_digest()


@server.tool()
def sandy_health_snapshot() -> Dict[str, Any]:
    """
    Structured (non-text) snapshot: one entry per agent with
    name/category/stage/trend/evidence_count/issues/summary. Useful for
    programmatic follow-up questions rather than the formatted text reports.
    """
    reports = get_sandy_supervisor().poll_all_agents()
    return {name: r.to_dict() for name, r in reports.items()}


if __name__ == "__main__":
    server.run(transport="stdio")
