"""iios/investment/models/investment_analysis.py
InvestmentAnalysis — output from a single workflow stage / domain engine.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field

from iios.investment.investment_constants import (
    AnalysisStatus,
    AssetClass,
    IntelligenceType,
)


@dataclass
class InvestmentAnalysis:
    """Result produced by one InvestmentWorkflow execution."""

    analysis_id:       str             = field(default_factory=lambda: str(uuid.uuid4()))
    request_id:        str             = ""
    workflow_id:       str             = ""
    intelligence_type: IntelligenceType = IntelligenceType.MARKET
    asset_class:       AssetClass      = AssetClass.EQUITY
    symbols:           list[str]       = field(default_factory=list)
    confidence:        float           = 0.0      # 0..1
    evidence:          list[dict]      = field(default_factory=list)
    findings:          dict            = field(default_factory=dict)
    status:            AnalysisStatus  = AnalysisStatus.PENDING
    errors:            list[str]       = field(default_factory=list)
    duration_ms:       float           = 0.0
    created_at:        float           = field(default_factory=time.time)
    completed_at:      float | None    = None

    def mark_completed(self, confidence: float | None = None) -> None:
        self.status       = AnalysisStatus.COMPLETED
        self.completed_at = time.time()
        if confidence is not None:
            self.confidence = confidence

    def mark_failed(self, error: str = "") -> None:
        self.status       = AnalysisStatus.FAILED
        self.completed_at = time.time()
        if error:
            self.errors.append(error)

    def to_dict(self) -> dict:
        return {
            "analysis_id":       self.analysis_id,
            "request_id":        self.request_id,
            "workflow_id":       self.workflow_id,
            "intelligence_type": self.intelligence_type.value,
            "asset_class":       self.asset_class.value,
            "symbols":           self.symbols,
            "confidence":        self.confidence,
            "findings":          self.findings,
            "status":            self.status.value,
            "errors":            self.errors,
            "duration_ms":       self.duration_ms,
            "created_at":        self.created_at,
            "completed_at":      self.completed_at,
        }
