"""iios/investment/models/investment_result.py
InvestmentResult — aggregate output of the full investment pipeline.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field

from iios.investment.investment_constants import AnalysisStatus
from iios.investment.models.investment_analysis import InvestmentAnalysis


@dataclass
class InvestmentResult:
    """Aggregate result of running all workflows against one InvestmentRequest."""

    result_id:          str                    = field(default_factory=lambda: str(uuid.uuid4()))
    request_id:         str                    = ""
    session_id:         str                    = ""
    analyses:           list[InvestmentAnalysis] = field(default_factory=list)
    overall_confidence: float                  = 0.0
    summary:            dict                   = field(default_factory=dict)
    status:             AnalysisStatus         = AnalysisStatus.PENDING
    succeeded:          bool                   = True
    errors:             list[str]              = field(default_factory=list)
    warnings:           list[str]              = field(default_factory=list)
    duration_ms:        float                  = 0.0
    created_at:         float                  = field(default_factory=time.time)

    @property
    def completed_analyses(self) -> list[InvestmentAnalysis]:
        return [a for a in self.analyses if a.status == AnalysisStatus.COMPLETED]

    @property
    def failed_analyses(self) -> list[InvestmentAnalysis]:
        return [a for a in self.analyses if a.status == AnalysisStatus.FAILED]

    def to_dict(self) -> dict:
        return {
            "result_id":          self.result_id,
            "request_id":         self.request_id,
            "session_id":         self.session_id,
            "analysis_count":     len(self.analyses),
            "completed":          len(self.completed_analyses),
            "failed":             len(self.failed_analyses),
            "overall_confidence": self.overall_confidence,
            "summary":            self.summary,
            "status":             self.status.value,
            "succeeded":          self.succeeded,
            "errors":             self.errors,
            "warnings":           self.warnings,
            "duration_ms":        self.duration_ms,
            "created_at":         self.created_at,
        }
