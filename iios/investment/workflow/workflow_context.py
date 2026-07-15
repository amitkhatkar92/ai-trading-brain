"""iios/investment/workflow/workflow_context.py
WorkflowParameters and WorkflowEngines — dependency-injected configuration
and engine references for the Institutional Investment Workflow.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from iios.investment.workflow.workflow_types import (
    DEFAULT_MAX_RETRIES,
    DEFAULT_MIN_QUALITY_COMPANY,
    DEFAULT_MIN_QUALITY_DECISION,
    DEFAULT_MIN_QUALITY_MARKET,
    DEFAULT_MIN_QUALITY_PORTFOLIO,
    DEFAULT_MIN_QUALITY_STRATEGY,
    DEFAULT_RETRY_DELAY_SEC,
    DEFAULT_STAGE_TIMEOUT_SEC,
)


@dataclass(frozen=True)
class WorkflowParameters:
    """
    Immutable configuration governing pipeline execution thresholds,
    retry behaviour, and quality gates.

    All thresholds are in [0.0, 1.0] unless otherwise noted.
    """

    # ── Retry ─────────────────────────────────────────────────────────────────
    max_retries:       int   = DEFAULT_MAX_RETRIES
    retry_delay_sec:   float = DEFAULT_RETRY_DELAY_SEC
    stage_timeout_sec: float = DEFAULT_STAGE_TIMEOUT_SEC

    # ── Quality gates (pipeline does not block on these; they add warnings) ──
    min_quality_market:   float = DEFAULT_MIN_QUALITY_MARKET
    min_quality_company:  float = DEFAULT_MIN_QUALITY_COMPANY
    min_quality_strategy: float = DEFAULT_MIN_QUALITY_STRATEGY
    min_quality_decision: float = DEFAULT_MIN_QUALITY_DECISION
    min_quality_portfolio: float = DEFAULT_MIN_QUALITY_PORTFOLIO

    # ── Publishing ────────────────────────────────────────────────────────────
    publish_portfolio_snapshot: bool = True

    # ── Stage skip flags (for partial pipelines or testing) ──────────────────
    skip_company_stage:  bool = False
    skip_strategy_stage: bool = False
    skip_decision_stage: bool = False

    def __post_init__(self) -> None:
        if self.max_retries < 0:
            raise ValueError("max_retries must be >= 0")
        if self.retry_delay_sec < 0.0:
            raise ValueError("retry_delay_sec must be >= 0.0")
        if self.stage_timeout_sec <= 0.0:
            raise ValueError("stage_timeout_sec must be > 0.0")

    def to_dict(self) -> dict:
        return {
            "max_retries":             self.max_retries,
            "retry_delay_sec":         self.retry_delay_sec,
            "stage_timeout_sec":       self.stage_timeout_sec,
            "min_quality_market":      self.min_quality_market,
            "min_quality_company":     self.min_quality_company,
            "min_quality_strategy":    self.min_quality_strategy,
            "min_quality_decision":    self.min_quality_decision,
            "min_quality_portfolio":   self.min_quality_portfolio,
            "publish_portfolio_snapshot": self.publish_portfolio_snapshot,
            "skip_company_stage":      self.skip_company_stage,
            "skip_strategy_stage":     self.skip_strategy_stage,
            "skip_decision_stage":     self.skip_decision_stage,
        }


@dataclass
class WorkflowEngines:
    """
    Container for the five Integration Engine references injected into the
    Institutional Investment Workflow.

    All attributes accept ``None``; the orchestrator will create default
    instances only when the attribute is ``None`` at first use.

    The workflow NEVER accesses sub-engines directly through these references —
    only the public integration-engine API.
    """

    market_engine:   Any = None   # MarketIntelligenceIntegrationEngine
    company_engine:  Any = None   # CompanyIntelligenceIntegrationEngine
    strategy_engine: Any = None   # StrategyIntelligenceIntegrationEngine
    decision_engine: Any = None   # DecisionIntelligenceIntegrationEngine
    portfolio_engine: Any = None  # PortfolioIntelligenceIntegrationEngine

    # Optional event callback: (event_type: str, payload: dict) -> None
    event_callback: Optional[Callable[[str, dict], None]] = field(
        default=None, compare=False,
    )

    def ensure_defaults(self) -> None:
        """Lazily instantiate any engine that was left as None."""
        if self.market_engine is None:
            from iios.investment.market.integration.market_intelligence_integration_engine import (
                MarketIntelligenceIntegrationEngine,
            )
            self.market_engine = MarketIntelligenceIntegrationEngine()

        if self.company_engine is None:
            from iios.investment.company.integration.company_intelligence_integration_engine import (
                CompanyIntelligenceIntegrationEngine,
            )
            self.company_engine = CompanyIntelligenceIntegrationEngine()

        if self.strategy_engine is None:
            from iios.investment.strategy.integration.strategy_intelligence_integration_engine import (
                StrategyIntelligenceIntegrationEngine,
            )
            eng = StrategyIntelligenceIntegrationEngine()
            eng.start()
            self.strategy_engine = eng

        if self.decision_engine is None:
            from iios.investment.decision.integration.decision_intelligence_integration_engine import (
                DecisionIntelligenceIntegrationEngine,
            )
            eng = DecisionIntelligenceIntegrationEngine()
            eng.start()
            self.decision_engine = eng

        if self.portfolio_engine is None:
            from iios.investment.portfolio.integration.portfolio_intelligence_integration_engine import (
                PortfolioIntelligenceIntegrationEngine,
            )
            eng = PortfolioIntelligenceIntegrationEngine()
            eng.start()
            self.portfolio_engine = eng
