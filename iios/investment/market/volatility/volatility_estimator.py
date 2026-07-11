"""iios/investment/market/volatility/volatility_estimator.py
Pluggable volatility estimator framework.

Any object satisfying the VolatilityEstimator Protocol can be registered
with InstitutionalVolatilityIntelligenceEngine.  Built-in estimators live in
this package but are never hardwired into the core engine logic.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional, Protocol, runtime_checkable

from iios.investment.market.volatility.models import VolatilityEstimate

if TYPE_CHECKING:
    from iios.investment.market.structure.models import Bar


@runtime_checkable
class VolatilityEstimator(Protocol):
    """Structural protocol that every volatility estimator must satisfy."""

    @property
    def name(self) -> str:
        """Unique human-readable name, used as the dictionary key in results."""
        ...

    @property
    def required_bars(self) -> int:
        """Minimum number of bars required to produce an estimate."""
        ...

    def estimate(self, bars: "List[Bar]") -> "Optional[VolatilityEstimate]":
        """
        Compute a volatility estimate from the provided bar series.

        Parameters
        ----------
        bars:
            Ordered sequence of OHLCV bars (oldest first).  The estimator
            may use any or all of them; it is the caller's responsibility to
            pass at least ``required_bars`` bars.

        Returns
        -------
        VolatilityEstimate or None
            Returns None when the input is insufficient (< required_bars) or
            when the data is degenerate (e.g. all prices identical).
        """
        ...
