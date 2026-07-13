"""iios/investment/strategy/core/strategy_context.py
Strategy execution context — everything an institutional strategy
receives per evaluation cycle.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .strategy_configuration import StrategyConfiguration


@dataclass
class StrategyContext:
    """
    Runtime context injected into every strategy execution cycle.

    Carries references to upstream intelligence layers; all intelligence
    references are Optional so strategies remain independently testable.
    """
    strategy_id: str
    session_id: str
    configuration: StrategyConfiguration

    # Universe to evaluate
    symbols: List[str] = field(default_factory=list)

    # Upstream intelligence (injected by framework, all Optional)
    market_intelligence: Optional[Any] = None       # MarketIntelligenceSnapshot
    company_intelligence: Optional[Any] = None      # dict[ticker, CompanyIntelligenceSnapshot]

    # Layer integrations (all Optional)
    knowledge_layer: Optional[Any] = None
    decision_layer: Optional[Any] = None
    execution_layer: Optional[Any] = None
    research_framework: Optional[Any] = None
    historical_framework: Optional[Any] = None

    # Security / authorization context
    security_context: Optional[Dict[str, Any]] = None

    # Evaluation timestamp (as-of)
    as_of: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    # Extra key-value store for strategy-specific auxiliary data
    extras: Dict[str, Any] = field(default_factory=dict)

    # Execution mode flags
    is_live: bool = False
    is_paper: bool = True
    is_backtest: bool = False

    def get_extra(self, key: str, default: Any = None) -> Any:
        return self.extras.get(key, default)

    def set_extra(self, key: str, value: Any) -> None:
        self.extras[key] = value

    def get_company_intel(self, ticker: str) -> Optional[Any]:
        """Look up company intelligence for a specific ticker."""
        if isinstance(self.company_intelligence, dict):
            return self.company_intelligence.get(ticker)
        return None

    def param(self, key: str, default: Any = None) -> Any:
        """Shorthand for configuration.get()."""
        return self.configuration.get(key, default)

    def to_dict(self) -> dict:
        return {
            "strategy_id": self.strategy_id,
            "session_id": self.session_id,
            "symbols": self.symbols,
            "is_live": self.is_live,
            "is_paper": self.is_paper,
            "is_backtest": self.is_backtest,
            "as_of": self.as_of.isoformat(),
        }
