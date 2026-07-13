"""iios/investment/strategy/risk/risk_input.py
StrategyRiskInput — the canonical input DTO for the Risk Engine.
Populated from EvaluationEngine, OpportunityEngine, PortfolioEngine,
and Market Intelligence.  The Risk Engine never independently evaluates
markets or strategies.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class StrategyRiskInput:
    """
    Immutable snapshot of strategy characteristics used for risk evaluation.

    All evaluation metrics are pre-computed by upstream engines; the Risk
    Engine consumes them — it never re-evaluates strategies independently.
    """
    # ── identity ─────────────────────────────────────────────────────────────
    strategy_id:   str
    strategy_name: str

    # ── evaluation intelligence (from EvaluationEngine) ──────────────────────
    evaluation_score:  float   # 0–100
    sharpe_ratio:      float
    max_drawdown:      float   # 0–1  (e.g. 0.15 = 15%)
    win_rate:          float   # 0–1
    profit_factor:     float
    robustness_score:  float   # 0–1
    confidence_score:  float   # 0–100
    annualized_return: float   # e.g. 0.18 = 18%
    annualized_vol:    float   # e.g. 0.12 = 12%

    # ── capability profile ────────────────────────────────────────────────────
    asset_types:          List[str]  # ["equity", "options", "futures", …]
    sectors:              List[str]
    tags:                 List[str]  # ["momentum", "mean_reversion", …]
    supported_regimes:    List[str]  # ["trending", "sideways", "bull", "bear"]
    supported_timeframes: List[str]  # ["intraday", "daily", "weekly"]

    # ── market intelligence context (from Market Intelligence Engine) ─────────
    current_regime:           str = "unknown"  # "trending" | "sideways" | "bear" | …
    current_volatility_level: str = "normal"   # "low" | "normal" | "high" | "extreme"
    market_liquidity:         str = "normal"   # "low" | "normal" | "high"

    # ── portfolio context (from Portfolio Engine) ─────────────────────────────
    portfolio_weight:  float = 0.0   # fraction of portfolio capital allocated
    portfolio_size:    int   = 0     # total strategies in portfolio

    # ── opportunity context (from Opportunity Engine) ─────────────────────────
    opportunity_score: float = 0.0   # 0–100; higher = better matched opportunity

    # ── optional metadata ─────────────────────────────────────────────────────
    capital_allocated: float = 0.0   # absolute capital (informational)
    metadata:          Dict[str, Any] = field(default_factory=dict)
    evaluated_at:      datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def daily_vol(self) -> float:
        """Approximate daily volatility."""
        return self.annualized_vol / (252 ** 0.5)

    @property
    def regime_mismatch(self) -> bool:
        """True if current regime is not in the strategy's supported regimes."""
        return (
            self.current_regime not in ("unknown", "")
            and self.current_regime not in self.supported_regimes
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy_id":    self.strategy_id,
            "evaluation_score": self.evaluation_score,
            "sharpe_ratio":   self.sharpe_ratio,
            "max_drawdown":   self.max_drawdown,
            "annualized_vol": self.annualized_vol,
            "current_regime": self.current_regime,
            "current_volatility_level": self.current_volatility_level,
            "regime_mismatch": self.regime_mismatch,
        }
