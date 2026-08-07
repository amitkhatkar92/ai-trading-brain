"""
DTA-001 — Decision Traceability Audit

Public API:
    from decision_tracer import run_dta
    result = run_dta("RELIANCE")
"""
from .dta_runner    import run_dta
from .dta_collector import collect_trace, TraceBundle
from .dta_analyzer  import analyze, DTAAudit
from .dta_reporter  import write_report, generate_report

__all__ = [
    "run_dta",
    "collect_trace",
    "analyze",
    "write_report",
    "generate_report",
    "TraceBundle",
    "DTAAudit",
]
