"""iios/investment/strategy/evaluation/evaluation_input.py
EvaluationInput — everything needed to run a full strategy evaluation.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from iios.investment.strategy.evaluation.trade import Trade
from iios.investment.strategy.evaluation.equity_curve import EquityCurve


@dataclass
class EvaluationInput:
    """
    Single evaluation request.  All data must be supplied by the caller;
    the engine is a pure function over its inputs and holds no market state.
    """

    strategy_id: str
    strategy_name: str
    trades: List[Trade]
    equity_curve: EquityCurve

    # Benchmark curve is optional; metrics that require it (alpha, IR, beta)
    # will be set to 0.0 or None when absent.
    benchmark_curve: Optional[EquityCurve] = None

    # The period the strategy was observed / backtested over.
    evaluation_start: Optional[datetime] = None
    evaluation_end: Optional[datetime]   = None

    # Annualised risk-free rate (e.g. 0.06 for 6 %).
    risk_free_rate: float = 0.06

    # Number of trading days per year used for annualisation.
    periods_per_year: int = 252

    # Arbitrary key-value context carried through into the report.
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.evaluation_start is None and not self.equity_curve.is_empty():
            self.evaluation_start = self.equity_curve.points[0].timestamp
        if self.evaluation_end is None and not self.equity_curve.is_empty():
            self.evaluation_end = self.equity_curve.points[-1].timestamp

    # ── derived ─────────────────────────────────────────────────────────────

    @property
    def has_benchmark(self) -> bool:
        return (
            self.benchmark_curve is not None
            and not self.benchmark_curve.is_empty()
        )

    @property
    def has_trades(self) -> bool:
        return len(self.trades) > 0

    @property
    def winners(self) -> List[Trade]:
        return [t for t in self.trades if t.is_winner]

    @property
    def losers(self) -> List[Trade]:
        return [t for t in self.trades if t.is_loser]

    @property
    def duration_years(self) -> float:
        return self.equity_curve.duration_years

    @property
    def rf_per_period(self) -> float:
        """Risk-free rate per equity-curve period."""
        return self.risk_free_rate / self.periods_per_year
