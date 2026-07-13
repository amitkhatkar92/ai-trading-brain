"""iios/investment/strategy/portfolio/portfolio_strategy.py
PortfolioStrategy — the representation of a strategy as seen by the
Portfolio Engine.  Populated from EvaluationEngine and OpportunityEngine
outputs; the Portfolio Engine does NOT independently evaluate strategies.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class PortfolioStrategy:
    """
    Lightweight view of a strategy for portfolio construction purposes.
    All evaluation metrics come from upstream engines.
    """
    strategy_id:      str
    strategy_name:    str

    # ── evaluation metrics (from EvaluationEngine) ───────────────────────────
    evaluation_score:  float   # 0–100
    sharpe_ratio:      float
    max_drawdown:      float   # 0–1
    win_rate:          float   # 0–1
    profit_factor:     float
    robustness_score:  float   # 0–1
    confidence_score:  float   # 0–100
    annualized_return: float   # e.g. 0.18 = 18%
    annualized_vol:    float   # e.g. 0.12 = 12%

    # ── capability profile ────────────────────────────────────────────────────
    asset_types:           List[str]  # ["equity", "options"]
    sectors:               List[str]  # preferred sectors; empty = all
    tags:                  List[str]  # ["momentum", "trend", "mean_reversion"]
    supported_regimes:     List[str]
    supported_timeframes:  List[str]

    # ── approval ──────────────────────────────────────────────────────────────
    approval_status:  str  # "approved" | "conditional" | "rejected"

    # ── optional ─────────────────────────────────────────────────────────────
    min_capital:  float = 0.0
    metadata:     Dict[str, Any] = field(default_factory=dict)

    @property
    def is_eligible(self) -> bool:
        return self.approval_status in ("approved", "conditional")

    @property
    def risk_adjusted_score(self) -> float:
        """Single sortable quality metric."""
        dd_pen = max(0.0, 1.0 - self.max_drawdown / 0.30)
        return self.evaluation_score * 0.50 + self.sharpe_ratio * 20.0 * 0.30 + dd_pen * 100.0 * 0.20

    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy_id":     self.strategy_id,
            "strategy_name":   self.strategy_name,
            "evaluation_score": self.evaluation_score,
            "sharpe_ratio":    self.sharpe_ratio,
            "max_drawdown":    self.max_drawdown,
            "win_rate":        self.win_rate,
            "profit_factor":   self.profit_factor,
            "robustness_score": self.robustness_score,
            "confidence_score": self.confidence_score,
            "approval_status":  self.approval_status,
        }
