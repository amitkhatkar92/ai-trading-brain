"""iios/investment/strategy/opportunity/strategy_candidate.py
StrategyCandidate — internal representation of a strategy available for matching.
Populated from EvaluationEngine outputs; Opportunity Engine does not evaluate strategies.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class StrategyCandidate:
    """
    A strategy registered with the Opportunity Engine for matching.

    Capability fields declare what the strategy supports.
    Evaluation fields come from the Strategy Evaluation Engine.
    The Opportunity Engine consumes these; it does not compute them.
    """
    strategy_id:   str
    strategy_name: str

    # ── capability declarations ──────────────────────────────────────────────
    asset_types:         List[str]  # ["equity", "options", "futures"]
    supported_timeframes: List[str]  # ["intraday","swing","positional"] or ["all"]
    supported_regimes:   List[str]  # ["bull","bear","sideways"] or ["all"]
    supported_directions: List[str] # ["long","short"] or ["both"]
    sectors:             List[str]  # preferred sectors; empty ⇒ all sectors
    tags:                List[str]  # ["momentum","breakout","mean_reversion"]

    # ── capital & risk constraints ───────────────────────────────────────────
    min_capital:           float  # minimum capital required (currency units)
    max_position_size:     float  # maximum position as fraction of capital (0–1)
    max_drawdown_tolerance: float  # max acceptable drawdown for this strategy (0–1)
    min_liquidity_score:   float  # minimum liquidity score required (0–1)

    # ── evaluation metrics (from EvaluationEngine) ───────────────────────────
    evaluation_score:  float  # 0–100
    sharpe_ratio:      float
    max_drawdown:      float  # realised max DD (0–1)
    win_rate:          float  # 0–1
    profit_factor:     float
    robustness_score:  float  # 0–1
    confidence_score:  float  # 0–100
    approval_status:   str    # "approved" | "conditional" | "rejected"

    # ── optional constraints ─────────────────────────────────────────────────
    min_volatility_regime: Optional[str] = None  # strategy requires at least this vol
    max_volatility_regime: Optional[str] = None  # strategy breaks above this vol
    metadata:              Dict[str, Any] = field(default_factory=dict)

    # ── capability checks ────────────────────────────────────────────────────

    def supports_regime(self, regime: str) -> bool:
        return "all" in self.supported_regimes or regime in self.supported_regimes

    def supports_timeframe(self, timeframe: str) -> bool:
        return "all" in self.supported_timeframes or timeframe in self.supported_timeframes

    def supports_direction(self, direction: str) -> bool:
        if direction == "neutral":
            return True
        return "both" in self.supported_directions or direction in self.supported_directions

    def supports_sector(self, sector: str) -> bool:
        return not self.sectors or sector in self.sectors

    def supports_asset_type(self, asset_type: str) -> bool:
        return asset_type in self.asset_types

    @property
    def is_approved(self) -> bool:
        return self.approval_status == "approved"

    @property
    def is_eligible(self) -> bool:
        return self.approval_status in ("approved", "conditional")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy_id":       self.strategy_id,
            "strategy_name":     self.strategy_name,
            "evaluation_score":  self.evaluation_score,
            "sharpe_ratio":      self.sharpe_ratio,
            "win_rate":          self.win_rate,
            "profit_factor":     self.profit_factor,
            "approval_status":   self.approval_status,
            "supported_timeframes": self.supported_timeframes,
            "supported_regimes":    self.supported_regimes,
            "supported_directions": self.supported_directions,
            "asset_types":       self.asset_types,
            "robustness_score":  self.robustness_score,
            "confidence_score":  self.confidence_score,
        }
