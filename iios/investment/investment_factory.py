"""iios/investment/investment_factory.py
Factory helpers for creating investment objects without boilerplate.
"""
from __future__ import annotations

from typing import Callable

from iios.investment.investment_constants import (
    AssetClass,
    IntelligenceType,
    InvestmentObjective,
    RiskProfile,
    TimeHorizon,
)
from iios.investment.models.investment_analysis import InvestmentAnalysis
from iios.investment.models.investment_context_model import InvestmentContext
from iios.investment.models.investment_request import InvestmentRequest
from iios.investment.models.investment_result import InvestmentResult
from iios.investment.models.investment_session import InvestmentSession
from iios.investment.workflow.investment_workflow import InvestmentWorkflow, NoOpWorkflow


class InvestmentFactory:

    @staticmethod
    def make_request(
        symbols:      list[str],
        asset_class:  AssetClass         = AssetClass.EQUITY,
        objective:    InvestmentObjective = InvestmentObjective.GROWTH,
        time_horizon: TimeHorizon         = TimeHorizon.MEDIUM_TERM,
        risk_profile: RiskProfile         = RiskProfile.MODERATE,
        market:       str                 = "",
        currency:     str                 = "",
        intelligence_types: list[IntelligenceType] | None = None,
        **metadata,
    ) -> InvestmentRequest:
        return InvestmentRequest(
            asset_class=asset_class,
            symbols=symbols,
            objective=objective,
            time_horizon=time_horizon,
            risk_profile=risk_profile,
            market=market,
            currency=currency,
            intelligence_types=intelligence_types or [],
            metadata=metadata,
        )

    @staticmethod
    def make_context(
        request:    InvestmentRequest,
        session_id: str = "",
    ) -> InvestmentContext:
        return InvestmentContext(
            session_id=session_id,
            request_id=request.request_id,
            asset_class=request.asset_class,
            symbols=list(request.symbols),
        )

    @staticmethod
    def make_session(name: str = "", source_id: str = "") -> InvestmentSession:
        return InvestmentSession(name=name, source_id=source_id)

    @staticmethod
    def make_noop_workflow() -> NoOpWorkflow:
        return NoOpWorkflow()

    @staticmethod
    def make_function_workflow(
        workflow_id:       str,
        name:              str,
        fn:                Callable[[InvestmentRequest, InvestmentContext], InvestmentAnalysis],
        intelligence_type: IntelligenceType = IntelligenceType.CUSTOM,
        priority:          int              = 0,
    ) -> InvestmentWorkflow:
        """Create a workflow from a plain function — useful for tests and quick prototyping."""

        class _FunctionWorkflow(InvestmentWorkflow):
            @property
            def workflow_id(self) -> str: return workflow_id

            @property
            def name(self) -> str: return name

            @property
            def intelligence_type(self) -> IntelligenceType: return intelligence_type

            @property
            def priority(self) -> int: return priority

            def execute(
                self,
                request: InvestmentRequest,
                context: InvestmentContext,
            ) -> InvestmentAnalysis:
                return fn(request, context)

        return _FunctionWorkflow()
