"""
GVA-001 — Growth Validator & Assessor

Public API:
    from growth_validator import run_gva
    result = run_gva()
"""
from .gva_runner import run_gva
from .gva_collector import collect_all, GVAEvidence
from .gva_metrics import compute_all, GrowthReport, Metric
from .gva_reporter import write_all_reports

__all__ = [
    "run_gva",
    "collect_all",
    "compute_all",
    "write_all_reports",
    "GVAEvidence",
    "GrowthReport",
    "Metric",
]
