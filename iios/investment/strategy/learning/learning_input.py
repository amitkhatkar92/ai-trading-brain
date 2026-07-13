"""iios/investment/strategy/learning/learning_input.py
LearningObservation — the primary input DTO for the Learning Engine.

Bundles intelligence from all upstream engines into a single observation:
  • Strategy Evaluation Intelligence
  • Strategy Opportunity Intelligence
  • Strategy Portfolio Intelligence
  • Strategy Risk Intelligence
  • Market Intelligence Integration
  • Company / Asset Intelligence Integration

The Learning Engine does NOT generate these values — it consumes them.
"""
from __future__ import annotations

import math
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple


@dataclass(frozen=True)
class LearningObservation:
    """
    Single point-in-time observation of a strategy across all intelligence layers.
    Immutable — created once per evaluation cycle and appended to history.
    """
    strategy_id:   str
    strategy_name: str
    observation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    observed_at:   datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    # ── from Evaluation Engine ────────────────────────────────────────────────
    evaluation_score:  float = 0.0    # 0-100; higher = better
    sharpe_ratio:      float = 0.0
    max_drawdown:      float = 0.0    # 0-1 fraction
    win_rate:          float = 0.0    # 0-1 fraction
    profit_factor:     float = 0.0
    robustness_score:  float = 0.0    # 0-1 fraction
    confidence_score:  float = 0.0    # 0-100
    annualized_return: float = 0.0
    annualized_vol:    float = 0.0

    # ── from Opportunity Engine ───────────────────────────────────────────────
    opportunity_score: float = 0.0    # 0-100

    # ── from Portfolio Engine ─────────────────────────────────────────────────
    portfolio_weight: float = 0.0
    portfolio_size:   int   = 0

    # ── from Risk Engine ──────────────────────────────────────────────────────
    risk_score:    float = 0.0    # 0-100; 0=safe, 100=dangerous
    risk_grade:    str   = "?"
    health_status: str   = "unknown"

    # ── Market Intelligence ───────────────────────────────────────────────────
    current_regime:           str = "unknown"
    current_volatility_level: str = "normal"
    market_liquidity:         str = "normal"

    # ── Strategy Capabilities ─────────────────────────────────────────────────
    asset_types:           Tuple[str, ...] = ()
    sectors:               Tuple[str, ...] = ()
    tags:                  Tuple[str, ...] = ()
    supported_regimes:     Tuple[str, ...] = ()
    supported_timeframes:  Tuple[str, ...] = ()

    # ── Trade outcomes (optional — available post-execution) ──────────────────
    trade_count:   int   = 0
    winning_trades: int  = 0
    losing_trades:  int  = 0
    avg_win_size:   float = 0.0    # fraction of capital
    avg_loss_size:  float = 0.0    # fraction of capital (positive value)
    largest_win:    float = 0.0
    largest_loss:   float = 0.0

    # ── Notes / labels from upstream engines ─────────────────────────────────
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def regime_mismatch(self) -> bool:
        if not self.supported_regimes or self.current_regime == "unknown":
            return False
        return self.current_regime not in self.supported_regimes

    @property
    def win_loss_ratio(self) -> float:
        """Average win / average loss; 0 if no losses on record."""
        if self.avg_loss_size <= 0.0:
            return 0.0
        return self.avg_win_size / self.avg_loss_size

    @property
    def daily_vol(self) -> float:
        return self.annualized_vol / math.sqrt(252.0)

    @property
    def is_profitable(self) -> bool:
        return self.annualized_return > 0.0

    @property
    def has_trade_data(self) -> bool:
        return self.trade_count > 0

    @property
    def composite_quality(self) -> float:
        """Quick composite of evaluation × (1 - risk/100) for comparative ranking."""
        return self.evaluation_score * (1.0 - self.risk_score / 100.0)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy_id":       self.strategy_id,
            "observation_id":    self.observation_id,
            "observed_at":       self.observed_at.isoformat(),
            "evaluation_score":  self.evaluation_score,
            "sharpe_ratio":      self.sharpe_ratio,
            "max_drawdown":      self.max_drawdown,
            "win_rate":          self.win_rate,
            "risk_score":        self.risk_score,
            "risk_grade":        self.risk_grade,
            "health_status":     self.health_status,
            "opportunity_score": self.opportunity_score,
            "current_regime":    self.current_regime,
            "regime_mismatch":   self.regime_mismatch,
            "composite_quality": round(self.composite_quality, 2),
        }
