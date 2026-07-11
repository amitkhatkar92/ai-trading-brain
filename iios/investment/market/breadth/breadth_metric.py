"""iios/investment/market/breadth/breadth_metric.py
Pluggable breadth metric protocol.

Any class satisfying BreadthMetric can be registered with the engine and
will be called on each UniverseSnapshot.  Built-in metrics are provided in
this package but are never hardwired into core engine logic.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional, Protocol, runtime_checkable

from iios.investment.market.breadth.models import BreadthMetricValue

if TYPE_CHECKING:
    from iios.investment.market.breadth.models import SecurityObservation


@runtime_checkable
class BreadthMetric(Protocol):
    """Structural protocol for stateless per-universe breadth metrics."""

    @property
    def name(self) -> str:
        """Unique metric name used as the dictionary key in results."""
        ...

    @property
    def required_observations(self) -> int:
        """Minimum number of securities needed to compute a meaningful result."""
        ...

    def compute(
        self, observations: "List[SecurityObservation]"
    ) -> "Optional[BreadthMetricValue]":
        """
        Compute the metric from a universe of security observations.

        Returns None if there are fewer than ``required_observations``
        securities or the input is otherwise insufficient.
        """
        ...
