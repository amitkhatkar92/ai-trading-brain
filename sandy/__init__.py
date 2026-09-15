"""
sandy — Phase 7 "Sandy" Master Meta-Learning Supervisor.

Pure oversight agent: polls every self-learning agent/phase built in this
project (Phases 1-6 plus baseline loops) via their own existing read-only
accessors, classifies activity trend, and answers fixed-keyword queries
with a template-based summary. Never trades, never mutates another
agent's state or decision logic -- see sandy_supervisor.py's module
docstring for the full governance contract.

Public API:
    SandySupervisor       — core class
    get_sandy_supervisor  — module-level singleton accessor
    AgentHealthReport     — per-agent status model

Quick start:
    from sandy import get_sandy_supervisor
    sandy = get_sandy_supervisor()
    print(sandy.answer("hi sandy"))
    print(sandy.daily_digest())
"""
from .sandy_models import AgentHealthReport
from .sandy_supervisor import SandySupervisor, get_sandy_supervisor

__all__ = [
    "AgentHealthReport",
    "SandySupervisor",
    "get_sandy_supervisor",
]
