"""
audit — DTA-038 continuous self-audit layer.

Public API
----------
  get_trace_manager()   → TraceManager  — per-process singleton
  get_dta038_manager()  → DTA038Manager — top-level facade

SAFETY
------
• All public functions swallow every exception.
• Zero effect on trading decisions, thresholds, or execution.
• Storage is append-only under data/audit/dta038/.
"""
from audit.dta038_trace import get_trace_manager
from audit.dta038_manager import get_dta038_manager, DTA038Manager
from audit.dta038_models import (
    CandidateTrace, CycleAudit, Hypothesis, StageResult,
    StageStatus, HypothesisStatus, AnomalyKind, AnomalyRecord,
    CycleQuestion, SelfQuestioningReport,
)

__all__ = [
    "get_trace_manager",
    "get_dta038_manager",
    "DTA038Manager",
    "CandidateTrace",
    "CycleAudit",
    "Hypothesis",
    "StageResult",
    "StageStatus",
    "HypothesisStatus",
    "AnomalyKind",
    "AnomalyRecord",
    "CycleQuestion",
    "SelfQuestioningReport",
]
