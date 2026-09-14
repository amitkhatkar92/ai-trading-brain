"""
STATUS: DISCONNECTED from live trading (zero references in master_orchestrator.py) — see ARCHITECTURE.md §13.
NOTE: internal modules renamed dta_*.py -> dtrace_*.py (Plan B Phase 2, 2026-09-14) to remove the
collision with this repo's "DTA-XXX" ticket/incident naming convention.

DTA-001 — Decision Traceability Audit

Public API:
    from decision_tracer import run_dta
    result = run_dta("RELIANCE")
"""
from .dtrace_runner    import run_dta
from .dtrace_collector import collect_trace, TraceBundle
from .dtrace_analyzer  import analyze, DTAAudit
from .dtrace_reporter  import write_report, generate_report

__all__ = [
    "run_dta",
    "collect_trace",
    "analyze",
    "write_report",
    "generate_report",
    "TraceBundle",
    "DTAAudit",
]
