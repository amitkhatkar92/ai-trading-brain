"""
STATUS: PARTIALLY ACTIVE (2026-09-15) — dtrace_scheduler.py now runs this
automatically once per day (see orchestrator/master_orchestrator.py's EOD
loop); still zero references in any LIVE trading/decision path — output is
diagnostic/observability only, never read back into a future decision.
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
from .dtrace_scheduler import run_daily_trace_batch, get_last_run_summary, get_run_history

__all__ = [
    "run_dta",
    "collect_trace",
    "analyze",
    "write_report",
    "generate_report",
    "TraceBundle",
    "DTAAudit",
]
