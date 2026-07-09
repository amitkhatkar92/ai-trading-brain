"""iios/investment/workflow/investment_workflow.py
Abstract InvestmentWorkflow base + NoOpWorkflow built-in.
"""
from __future__ import annotations

import time
from abc import ABC, abstractmethod

from iios.investment.investment_constants import (
    AnalysisStatus,
    AssetClass,
    IntelligenceType,
)
from iios.investment.models.investment_analysis import InvestmentAnalysis
from iios.investment.models.investment_context_model import InvestmentContext
from iios.investment.models.investment_request import InvestmentRequest


class InvestmentWorkflow(ABC):
    """
    Abstract base for all investment analysis workflows.

    Each workflow represents one domain-specific analysis step.
    Concrete implementations are registered with InvestmentRegistry
    and invoked by WorkflowExecutor.
    """

    @property
    @abstractmethod
    def workflow_id(self) -> str: ...

    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    def intelligence_type(self) -> IntelligenceType:
        return IntelligenceType.MARKET

    @property
    def supported_asset_classes(self) -> list[AssetClass]:
        """Empty list means all asset classes are supported."""
        return []

    @property
    def priority(self) -> int:
        """Lower priority value → runs earlier."""
        return 0

    def supports(self, asset_class: AssetClass) -> bool:
        supported = self.supported_asset_classes
        return not supported or asset_class in supported

    @abstractmethod
    def execute(
        self,
        request: InvestmentRequest,
        context: InvestmentContext,
    ) -> InvestmentAnalysis:
        """Run the workflow; return a completed InvestmentAnalysis."""

    def to_dict(self) -> dict:
        return {
            "workflow_id":            self.workflow_id,
            "name":                   self.name,
            "intelligence_type":      self.intelligence_type.value,
            "supported_asset_classes": [c.value for c in self.supported_asset_classes],
            "priority":               self.priority,
        }


# ── Built-in ──────────────────────────────────────────────────────────────────

class NoOpWorkflow(InvestmentWorkflow):
    """
    Pass-through workflow — returns an empty completed analysis.
    Used as the default when no domain workflows are registered.
    """

    @property
    def workflow_id(self) -> str:
        return "noop"

    @property
    def name(self) -> str:
        return "No-Op"

    @property
    def intelligence_type(self) -> IntelligenceType:
        return IntelligenceType.CUSTOM

    def execute(
        self,
        request: InvestmentRequest,
        context: InvestmentContext,
    ) -> InvestmentAnalysis:
        analysis = InvestmentAnalysis(
            request_id=request.request_id,
            workflow_id=self.workflow_id,
            intelligence_type=self.intelligence_type,
            asset_class=request.asset_class,
            symbols=list(request.symbols),
            confidence=1.0,
            findings={"noop": True},
        )
        analysis.mark_completed()
        return analysis
