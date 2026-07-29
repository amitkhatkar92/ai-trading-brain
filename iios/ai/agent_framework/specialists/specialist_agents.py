"""
specialist_agents.py -- iios.ai.agent_framework.specialists
=============================================================
Registration placeholders for the 14 specialist AI agents.

Each class:
* Inherits :class:`BaseAIAgent`.
* Defines a ``AGENT_TYPE`` and ``DESCRIPTION`` class variable.
* Provides a ``create_spec()`` factory that returns a valid :class:`AgentSpec`.
* Raises :class:`NotImplementedError` from ``execute_task()`` — specialist
  logic lives in dedicated modules, NOT here.

DO NOT add trading logic here.
DO NOT add investment decision logic here.

A5 AI Agent Framework — Phase 3, Module 5
"""
from __future__ import annotations

import time
from typing import ClassVar

from ..base.base_agent           import BaseAIAgent
from ..core.agent_capabilities   import AgentCapabilities, AgentCapability, CapabilityType
from ..core.agent_identity       import AgentIdentity
from ..core.agent_permissions    import AgentPermission, AgentPermissions, PermissionLevel
from ..core.agent_spec           import AgentSpec
from ..engine.agent_execution_context import AgentExecutionContext
from ..engine.agent_task         import AgentResult, AgentTask


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _read_only_permissions() -> AgentPermissions:
    """READ on market_data; no write/execute grants."""
    return AgentPermissions.create(
        AgentPermission.create("market_data", PermissionLevel.READ),
        AgentPermission.create("knowledge",   PermissionLevel.READ),
    )


def _analyst_capabilities(*extra: CapabilityType) -> AgentCapabilities:
    types = [CapabilityType.ANALYSIS, CapabilityType.RESEARCH] + list(extra)
    return AgentCapabilities.create(
        *[AgentCapability.create(t, t.value.title()) for t in types]
    )


def _placeholder_execute(
    agent: BaseAIAgent,
    task:  AgentTask,
    context: AgentExecutionContext,
) -> AgentResult:
    return AgentResult.failure(
        task,
        f"{agent.__class__.__name__} is a placeholder — implement in a specialist module.",
        time.time(),
    )


# ---------------------------------------------------------------------------
# 1. Market Analyst
# ---------------------------------------------------------------------------

class MarketAnalystAgent(BaseAIAgent):
    """Analyses overall market conditions, regime, and trend direction."""

    AGENT_TYPE:  ClassVar[str] = "MarketAnalystAgent"
    DESCRIPTION: ClassVar[str] = (
        "Analyses market conditions, trends, and regime detection."
    )

    @classmethod
    def create_spec(cls) -> AgentSpec:
        identity = AgentIdentity.create(
            agent_name = "MarketAnalyst",
            agent_type = cls.AGENT_TYPE,
        )
        return AgentSpec.create(
            identity    = identity,
            description = cls.DESCRIPTION,
            capabilities = _analyst_capabilities(CapabilityType.CLASSIFICATION),
            permissions  = _read_only_permissions(),
        )

    def execute_task(self, task: AgentTask, context: AgentExecutionContext) -> AgentResult:
        return _placeholder_execute(self, task, context)


# ---------------------------------------------------------------------------
# 2. Technical Analyst
# ---------------------------------------------------------------------------

class TechnicalAnalystAgent(BaseAIAgent):
    """Analyses price charts and technical indicators."""

    AGENT_TYPE:  ClassVar[str] = "TechnicalAnalystAgent"
    DESCRIPTION: ClassVar[str] = (
        "Analyses price charts, technical indicators, and signal generation."
    )

    @classmethod
    def create_spec(cls) -> AgentSpec:
        identity = AgentIdentity.create(
            agent_name = "TechnicalAnalyst",
            agent_type = cls.AGENT_TYPE,
        )
        return AgentSpec.create(
            identity    = identity,
            description = cls.DESCRIPTION,
            capabilities = _analyst_capabilities(CapabilityType.PREDICTION),
            permissions  = _read_only_permissions(),
        )

    def execute_task(self, task: AgentTask, context: AgentExecutionContext) -> AgentResult:
        return _placeholder_execute(self, task, context)


# ---------------------------------------------------------------------------
# 3. Fundamental Analyst
# ---------------------------------------------------------------------------

class FundamentalAnalystAgent(BaseAIAgent):
    """Analyses company financials, valuation, and earnings."""

    AGENT_TYPE:  ClassVar[str] = "FundamentalAnalystAgent"
    DESCRIPTION: ClassVar[str] = (
        "Analyses company financials, valuations, and fundamental quality."
    )

    @classmethod
    def create_spec(cls) -> AgentSpec:
        identity = AgentIdentity.create(
            agent_name = "FundamentalAnalyst",
            agent_type = cls.AGENT_TYPE,
        )
        return AgentSpec.create(
            identity    = identity,
            description = cls.DESCRIPTION,
            capabilities = _analyst_capabilities(CapabilityType.RECOMMENDATION),
            permissions  = _read_only_permissions(),
        )

    def execute_task(self, task: AgentTask, context: AgentExecutionContext) -> AgentResult:
        return _placeholder_execute(self, task, context)


# ---------------------------------------------------------------------------
# 4. Macro Analyst
# ---------------------------------------------------------------------------

class MacroAnalystAgent(BaseAIAgent):
    """Analyses macro-economic conditions and central bank policy."""

    AGENT_TYPE:  ClassVar[str] = "MacroAnalystAgent"
    DESCRIPTION: ClassVar[str] = (
        "Analyses macro-economic indicators, interest rates, and global policy."
    )

    @classmethod
    def create_spec(cls) -> AgentSpec:
        identity = AgentIdentity.create(
            agent_name = "MacroAnalyst",
            agent_type = cls.AGENT_TYPE,
        )
        return AgentSpec.create(
            identity    = identity,
            description = cls.DESCRIPTION,
            capabilities = _analyst_capabilities(CapabilityType.REASONING),
            permissions  = _read_only_permissions(),
        )

    def execute_task(self, task: AgentTask, context: AgentExecutionContext) -> AgentResult:
        return _placeholder_execute(self, task, context)


# ---------------------------------------------------------------------------
# 5. News Analyst
# ---------------------------------------------------------------------------

class NewsAnalystAgent(BaseAIAgent):
    """Parses and classifies financial news for event signals."""

    AGENT_TYPE:  ClassVar[str] = "NewsAnalystAgent"
    DESCRIPTION: ClassVar[str] = (
        "Parses financial news, extracts events, and classifies impact."
    )

    @classmethod
    def create_spec(cls) -> AgentSpec:
        identity = AgentIdentity.create(
            agent_name = "NewsAnalyst",
            agent_type = cls.AGENT_TYPE,
        )
        return AgentSpec.create(
            identity    = identity,
            description = cls.DESCRIPTION,
            capabilities = _analyst_capabilities(
                CapabilityType.CLASSIFICATION,
                CapabilityType.SUMMARIZATION,
            ),
            permissions = _read_only_permissions(),
        )

    def execute_task(self, task: AgentTask, context: AgentExecutionContext) -> AgentResult:
        return _placeholder_execute(self, task, context)


# ---------------------------------------------------------------------------
# 6. Sentiment Analyst
# ---------------------------------------------------------------------------

class SentimentAnalystAgent(BaseAIAgent):
    """Measures market sentiment from social and news sources."""

    AGENT_TYPE:  ClassVar[str] = "SentimentAnalystAgent"
    DESCRIPTION: ClassVar[str] = (
        "Measures market sentiment from social media, news, and options flow."
    )

    @classmethod
    def create_spec(cls) -> AgentSpec:
        identity = AgentIdentity.create(
            agent_name = "SentimentAnalyst",
            agent_type = cls.AGENT_TYPE,
        )
        return AgentSpec.create(
            identity    = identity,
            description = cls.DESCRIPTION,
            capabilities = _analyst_capabilities(CapabilityType.CLASSIFICATION),
            permissions  = _read_only_permissions(),
        )

    def execute_task(self, task: AgentTask, context: AgentExecutionContext) -> AgentResult:
        return _placeholder_execute(self, task, context)


# ---------------------------------------------------------------------------
# 7. Risk Analyst
# ---------------------------------------------------------------------------

class RiskAnalystAgent(BaseAIAgent):
    """Evaluates portfolio and trade-level risk metrics."""

    AGENT_TYPE:  ClassVar[str] = "RiskAnalystAgent"
    DESCRIPTION: ClassVar[str] = (
        "Evaluates VaR, drawdown, volatility, and concentration risk."
    )

    @classmethod
    def create_spec(cls) -> AgentSpec:
        identity = AgentIdentity.create(
            agent_name = "RiskAnalyst",
            agent_type = cls.AGENT_TYPE,
        )
        return AgentSpec.create(
            identity    = identity,
            description = cls.DESCRIPTION,
            capabilities = _analyst_capabilities(
                CapabilityType.REASONING,
                CapabilityType.PREDICTION,
            ),
            permissions = AgentPermissions.create(
                AgentPermission.create("market_data",  PermissionLevel.READ),
                AgentPermission.create("portfolio",    PermissionLevel.READ),
                AgentPermission.create("risk_metrics", PermissionLevel.READ),
            ),
        )

    def execute_task(self, task: AgentTask, context: AgentExecutionContext) -> AgentResult:
        return _placeholder_execute(self, task, context)


# ---------------------------------------------------------------------------
# 8. Portfolio Analyst
# ---------------------------------------------------------------------------

class PortfolioAnalystAgent(BaseAIAgent):
    """Analyses portfolio composition, allocation, and performance."""

    AGENT_TYPE:  ClassVar[str] = "PortfolioAnalystAgent"
    DESCRIPTION: ClassVar[str] = (
        "Analyses portfolio allocation, factor exposure, and attribution."
    )

    @classmethod
    def create_spec(cls) -> AgentSpec:
        identity = AgentIdentity.create(
            agent_name = "PortfolioAnalyst",
            agent_type = cls.AGENT_TYPE,
        )
        return AgentSpec.create(
            identity    = identity,
            description = cls.DESCRIPTION,
            capabilities = _analyst_capabilities(
                CapabilityType.RECOMMENDATION,
                CapabilityType.PLANNING,
            ),
            permissions = AgentPermissions.create(
                AgentPermission.create("market_data", PermissionLevel.READ),
                AgentPermission.create("portfolio",   PermissionLevel.READ),
            ),
        )

    def execute_task(self, task: AgentTask, context: AgentExecutionContext) -> AgentResult:
        return _placeholder_execute(self, task, context)


# ---------------------------------------------------------------------------
# 9. Compliance Analyst
# ---------------------------------------------------------------------------

class ComplianceAnalystAgent(BaseAIAgent):
    """Audits trades and positions against compliance rules."""

    AGENT_TYPE:  ClassVar[str] = "ComplianceAnalystAgent"
    DESCRIPTION: ClassVar[str] = (
        "Audits trades and positions against regulatory and internal rules."
    )

    @classmethod
    def create_spec(cls) -> AgentSpec:
        identity = AgentIdentity.create(
            agent_name = "ComplianceAnalyst",
            agent_type = cls.AGENT_TYPE,
        )
        return AgentSpec.create(
            identity    = identity,
            description = cls.DESCRIPTION,
            capabilities = _analyst_capabilities(CapabilityType.CLASSIFICATION),
            permissions  = AgentPermissions.create(
                AgentPermission.create("market_data", PermissionLevel.READ),
                AgentPermission.create("portfolio",   PermissionLevel.READ),
                AgentPermission.create("audit_log",   PermissionLevel.READ),
            ),
        )

    def execute_task(self, task: AgentTask, context: AgentExecutionContext) -> AgentResult:
        return _placeholder_execute(self, task, context)


# ---------------------------------------------------------------------------
# 10. Research Analyst
# ---------------------------------------------------------------------------

class ResearchAnalystAgent(BaseAIAgent):
    """Produces deep-research reports on securities and sectors."""

    AGENT_TYPE:  ClassVar[str] = "ResearchAnalystAgent"
    DESCRIPTION: ClassVar[str] = (
        "Produces in-depth research reports on securities, sectors, and themes."
    )

    @classmethod
    def create_spec(cls) -> AgentSpec:
        identity = AgentIdentity.create(
            agent_name = "ResearchAnalyst",
            agent_type = cls.AGENT_TYPE,
        )
        return AgentSpec.create(
            identity    = identity,
            description = cls.DESCRIPTION,
            capabilities = _analyst_capabilities(
                CapabilityType.SUMMARIZATION,
                CapabilityType.RECOMMENDATION,
            ),
            permissions = _read_only_permissions(),
        )

    def execute_task(self, task: AgentTask, context: AgentExecutionContext) -> AgentResult:
        return _placeholder_execute(self, task, context)


# ---------------------------------------------------------------------------
# 11. Options Analyst
# ---------------------------------------------------------------------------

class OptionsAnalystAgent(BaseAIAgent):
    """Analyses options chains, Greeks, and implied volatility."""

    AGENT_TYPE:  ClassVar[str] = "OptionsAnalystAgent"
    DESCRIPTION: ClassVar[str] = (
        "Analyses options chains, implied volatility, Greeks, and strategies."
    )

    @classmethod
    def create_spec(cls) -> AgentSpec:
        identity = AgentIdentity.create(
            agent_name = "OptionsAnalyst",
            agent_type = cls.AGENT_TYPE,
        )
        return AgentSpec.create(
            identity    = identity,
            description = cls.DESCRIPTION,
            capabilities = _analyst_capabilities(
                CapabilityType.PREDICTION,
                CapabilityType.RECOMMENDATION,
            ),
            permissions = _read_only_permissions(),
        )

    def execute_task(self, task: AgentTask, context: AgentExecutionContext) -> AgentResult:
        return _placeholder_execute(self, task, context)


# ---------------------------------------------------------------------------
# 12. Crypto Analyst
# ---------------------------------------------------------------------------

class CryptoAnalystAgent(BaseAIAgent):
    """Analyses cryptocurrency markets and on-chain metrics."""

    AGENT_TYPE:  ClassVar[str] = "CryptoAnalystAgent"
    DESCRIPTION: ClassVar[str] = (
        "Analyses crypto markets, on-chain metrics, and DeFi activity."
    )

    @classmethod
    def create_spec(cls) -> AgentSpec:
        identity = AgentIdentity.create(
            agent_name = "CryptoAnalyst",
            agent_type = cls.AGENT_TYPE,
        )
        return AgentSpec.create(
            identity    = identity,
            description = cls.DESCRIPTION,
            capabilities = _analyst_capabilities(CapabilityType.CLASSIFICATION),
            permissions  = _read_only_permissions(),
        )

    def execute_task(self, task: AgentTask, context: AgentExecutionContext) -> AgentResult:
        return _placeholder_execute(self, task, context)


# ---------------------------------------------------------------------------
# 13. Audit Agent
# ---------------------------------------------------------------------------

class AuditAgent(BaseAIAgent):
    """Audits agent behaviour, decisions, and framework integrity."""

    AGENT_TYPE:  ClassVar[str] = "AuditAgent"
    DESCRIPTION: ClassVar[str] = (
        "Audits agent decisions, framework events, and compliance trails."
    )

    @classmethod
    def create_spec(cls) -> AgentSpec:
        identity = AgentIdentity.create(
            agent_name = "AuditAgent",
            agent_type = cls.AGENT_TYPE,
        )
        return AgentSpec.create(
            identity    = identity,
            description = cls.DESCRIPTION,
            capabilities = AgentCapabilities.create(
                AgentCapability.create(CapabilityType.ANALYSIS,       "Audit Analysis"),
                AgentCapability.create(CapabilityType.CLASSIFICATION,  "Event Classification"),
                AgentCapability.create(CapabilityType.SUMMARIZATION,   "Audit Summarization"),
            ),
            permissions = AgentPermissions.create(
                AgentPermission.create("audit_log",   PermissionLevel.READ),
                AgentPermission.create("event_bus",   PermissionLevel.READ),
                AgentPermission.create("agent_registry", PermissionLevel.READ),
            ),
        )

    def execute_task(self, task: AgentTask, context: AgentExecutionContext) -> AgentResult:
        return _placeholder_execute(self, task, context)


# ---------------------------------------------------------------------------
# 14. Learning Agent
# ---------------------------------------------------------------------------

class LearningAgent(BaseAIAgent):
    """Learns from past decisions and improves strategy parameters."""

    AGENT_TYPE:  ClassVar[str] = "LearningAgent"
    DESCRIPTION: ClassVar[str] = (
        "Learns from historical decisions, updates strategy weights, "
        "and improves framework parameters over time."
    )

    @classmethod
    def create_spec(cls) -> AgentSpec:
        identity = AgentIdentity.create(
            agent_name = "LearningAgent",
            agent_type = cls.AGENT_TYPE,
        )
        return AgentSpec.create(
            identity    = identity,
            description = cls.DESCRIPTION,
            capabilities = AgentCapabilities.create(
                AgentCapability.create(CapabilityType.REASONING,      "Learning Reasoning"),
                AgentCapability.create(CapabilityType.PREDICTION,     "Outcome Prediction"),
                AgentCapability.create(CapabilityType.RECOMMENDATION, "Strategy Tuning"),
            ),
            permissions = AgentPermissions.create(
                AgentPermission.create("market_data",  PermissionLevel.READ),
                AgentPermission.create("trade_history", PermissionLevel.READ),
                AgentPermission.create("knowledge",    PermissionLevel.WRITE),
            ),
        )

    def execute_task(self, task: AgentTask, context: AgentExecutionContext) -> AgentResult:
        return _placeholder_execute(self, task, context)


# ---------------------------------------------------------------------------
# Registry of all specialist classes (used by gateway + tests)
# ---------------------------------------------------------------------------

ALL_SPECIALIST_CLASSES = [
    MarketAnalystAgent,
    TechnicalAnalystAgent,
    FundamentalAnalystAgent,
    MacroAnalystAgent,
    NewsAnalystAgent,
    SentimentAnalystAgent,
    RiskAnalystAgent,
    PortfolioAnalystAgent,
    ComplianceAnalystAgent,
    ResearchAnalystAgent,
    OptionsAnalystAgent,
    CryptoAnalystAgent,
    AuditAgent,
    LearningAgent,
]
