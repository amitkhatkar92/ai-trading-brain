"""iios/investment/portfolio/core/portfolio_context.py

Framework-level runtime context for the Institutional Portfolio Framework.
This is different from the thread-local operational context in the parent
package; this context is the dependency-injection container that every
portfolio instance receives from the framework.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional, TYPE_CHECKING

# Deferred integration references are typed as Optional[Any] so that
# the framework has no hard dependency on the individual intelligence engines.
# Each engine injects its client at startup via PortfolioFramework.configure_integrations().


@dataclass
class IntegrationRefs:
    """
    Holds optional references to upstream intelligence engine clients.
    Any field may be None — portfolios check before use.
    """

    market_intelligence:   Optional[Any] = None   # MarketIntelligenceClient
    company_intelligence:  Optional[Any] = None   # CompanyIntelligenceClient
    strategy_intelligence: Optional[Any] = None   # StrategyIntelligenceClient
    decision_intelligence: Optional[Any] = None   # DecisionIntelligenceClient (IIOS DI engine)
    knowledge_layer:       Optional[Any] = None   # KnowledgeLayerClient
    historical_framework:  Optional[Any] = None   # HistoricalFrameworkClient
    audit_framework:       Optional[Any] = None   # AuditFrameworkClient
    execution_layer:       Optional[Any] = None   # ExecutionLayerClient

    def has(self, name: str) -> bool:
        return getattr(self, name, None) is not None

    def to_dict(self) -> dict[str, bool]:
        """Returns a connectivity map (name → bool)."""
        return {
            "market_intelligence":   self.market_intelligence   is not None,
            "company_intelligence":  self.company_intelligence  is not None,
            "strategy_intelligence": self.strategy_intelligence is not None,
            "decision_intelligence": self.decision_intelligence is not None,
            "knowledge_layer":       self.knowledge_layer       is not None,
            "historical_framework":  self.historical_framework  is not None,
            "audit_framework":       self.audit_framework       is not None,
            "execution_layer":       self.execution_layer       is not None,
        }


@dataclass
class PortfolioRuntimeContext:
    """
    Runtime dependency-injection container provided to every BasePortfolio
    instance.

    The framework constructs one shared context and passes it to every
    portfolio during creation.  Portfolios must not store a direct reference
    to the framework itself — only to this context.
    """

    # Framework services
    integrations:   IntegrationRefs = field(default_factory=IntegrationRefs)

    # Framework-level configuration
    environment:    str             = "production"  # production | paper | backtest
    log_level:      str             = "INFO"
    enable_audit:   bool            = True
    enable_events:  bool            = True
    enable_tracing: bool            = False

    # Concurrency settings
    max_concurrent_ops: int         = 8
    op_timeout_seconds: float       = 30.0

    # Caching
    enable_cache:       bool        = True
    cache_ttl_seconds:  float       = 300.0

    # Custom settings bag (arbitrary key-value pairs)
    settings:       dict[str, Any]  = field(default_factory=dict)

    def get_setting(self, key: str, default: Any = None) -> Any:
        return self.settings.get(key, default)

    def is_production(self) -> bool:
        return self.environment == "production"

    def is_paper(self) -> bool:
        return self.environment == "paper"

    def is_backtest(self) -> bool:
        return self.environment == "backtest"

    def to_dict(self) -> dict[str, Any]:
        return {
            "environment":        self.environment,
            "log_level":          self.log_level,
            "enable_audit":       self.enable_audit,
            "enable_events":      self.enable_events,
            "enable_tracing":     self.enable_tracing,
            "max_concurrent_ops": self.max_concurrent_ops,
            "op_timeout_seconds": self.op_timeout_seconds,
            "enable_cache":       self.enable_cache,
            "cache_ttl_seconds":  self.cache_ttl_seconds,
            "integrations":       self.integrations.to_dict(),
        }
