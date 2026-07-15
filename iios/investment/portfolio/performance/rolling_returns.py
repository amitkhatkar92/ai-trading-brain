"""iios/investment/portfolio/performance/rolling_returns.py

Rolling window return analysis.
"""
from __future__ import annotations

import math
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class RollingReturnWindow:
    """A single rolling window result."""
    window_label:  str
    window_size:   int
    returns:       tuple          # tuple[float, ...]
    avg_return:    float = 0.0
    min_return:    float = 0.0
    max_return:    float = 0.0
    win_rate:      float = 0.0
    best_period:   int   = 0
    worst_period:  int   = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "window_label": self.window_label,
            "window_size":  self.window_size,
            "avg_return":   round(self.avg_return, 4),
            "min_return":   round(self.min_return, 4),
            "max_return":   round(self.max_return, 4),
            "win_rate":     round(self.win_rate, 4),
        }


@dataclass(frozen=True)
class RollingReturns:
    """Collection of rolling window analyses across multiple window sizes."""

    result_id:    str                     = field(default_factory=lambda: str(uuid.uuid4()))
    portfolio_id: str                     = ""
    n_periods:    int                     = 0
    windows:      tuple                   = field(default_factory=tuple)  # tuple[RollingReturnWindow,...]
    # Most recent rolling return for each window size
    latest_1m:    Optional[float]         = None
    latest_3m:    Optional[float]         = None
    latest_6m:    Optional[float]         = None
    latest_12m:   Optional[float]         = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "n_periods":  self.n_periods,
            "latest_1m":  round(self.latest_1m, 4) if self.latest_1m is not None else None,
            "latest_3m":  round(self.latest_3m, 4) if self.latest_3m is not None else None,
            "latest_6m":  round(self.latest_6m, 4) if self.latest_6m is not None else None,
            "latest_12m": round(self.latest_12m, 4) if self.latest_12m is not None else None,
            "windows":    [w.to_dict() for w in self.windows],
        }


def compute_rolling_returns(
    returns:      List[float],
    portfolio_id: str = "",
    windows:      Optional[List[int]] = None,
) -> RollingReturns:
    """
    Compute rolling compound returns for standard window sizes.

    ``returns`` = list of period (e.g. monthly) returns.
    ``windows`` = list of window sizes in the same period unit.
    """
    if windows is None:
        windows = [1, 3, 6, 12, 24, 36]

    n = len(returns)
    if n == 0:
        return RollingReturns(portfolio_id=portfolio_id)

    window_results: List[RollingReturnWindow] = []
    latest: Dict[int, float] = {}

    for ws in windows:
        if ws > n:
            continue
        roll = _rolling_compound(returns, ws)
        if not roll:
            continue
        avg = sum(roll) / len(roll)
        pos = sum(1 for r in roll if r > 0)
        wr  = pos / len(roll)
        bp  = roll.index(max(roll))
        wp  = roll.index(min(roll))
        window_results.append(RollingReturnWindow(
            window_label  = f"{ws}p",
            window_size   = ws,
            returns       = tuple(round(r, 6) for r in roll),
            avg_return    = round(avg, 6),
            min_return    = round(min(roll), 6),
            max_return    = round(max(roll), 6),
            win_rate      = round(wr, 4),
            best_period   = bp,
            worst_period  = wp,
        ))
        latest[ws] = roll[-1] if roll else 0.0

    return RollingReturns(
        portfolio_id = portfolio_id,
        n_periods    = n,
        windows      = tuple(window_results),
        latest_1m    = latest.get(1),
        latest_3m    = latest.get(3),
        latest_6m    = latest.get(6),
        latest_12m   = latest.get(12),
    )


def _rolling_compound(returns: List[float], window: int) -> List[float]:
    """List of compounded returns over rolling ``window``-period windows."""
    result = []
    for i in range(window - 1, len(returns)):
        compound = 1.0
        for j in range(i - window + 1, i + 1):
            compound *= (1.0 + returns[j])
        result.append(compound - 1.0)
    return result
