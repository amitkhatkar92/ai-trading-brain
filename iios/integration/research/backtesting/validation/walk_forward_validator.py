"""validation/walk_forward_validator.py — Walk-forward validation splits."""
from __future__ import annotations

from typing import Any

from iios.integration.research.backtesting.backtest_constants import DEFAULT_WALK_FORWARD_FOLDS
from iios.integration.research.backtesting.backtest_exceptions import WalkForwardError


class WalkForwardWindow:
    """A single in-sample / out-of-sample window."""

    def __init__(
        self,
        fold:       int,
        is_start:   float,
        is_end:     float,
        oos_start:  float,
        oos_end:    float,
    ) -> None:
        self.fold      = fold
        self.is_start  = is_start
        self.is_end    = is_end
        self.oos_start = oos_start
        self.oos_end   = oos_end

    def to_dict(self) -> dict[str, Any]:
        return {
            "fold":      self.fold,
            "is_start":  self.is_start,
            "is_end":    self.is_end,
            "oos_start": self.oos_start,
            "oos_end":   self.oos_end,
            "is_duration":  self.is_end  - self.is_start,
            "oos_duration": self.oos_end - self.oos_start,
        }


class WalkForwardValidator:
    """
    Generates walk-forward windows from a list of BarEvent timestamps.

    Uses a rolling / anchored approach: each fold's OOS window begins
    immediately after its IS window; the next fold's IS window starts
    at the same point (anchored) or slides forward (rolling).
    """

    def generate_windows(
        self,
        timestamps:    list[float],
        n_folds:       int = DEFAULT_WALK_FORWARD_FOLDS,
        oos_fraction:  float = 0.2,
        anchored:      bool = False,
    ) -> list[WalkForwardWindow]:
        """
        Generate walk-forward windows.

        timestamps   – sorted list of bar timestamps
        n_folds      – number of windows to produce
        oos_fraction – fraction of each fold window used as OOS
        anchored     – if True, IS always starts from the first bar

        Algorithm: divide n into (n_folds + 1) segments.
        The first segment forms the initial IS warm-up.
        Each subsequent segment is the OOS window for one fold;
        its IS window is everything (or one segment) before it.
        """
        if not timestamps:
            raise WalkForwardError("timestamps list is empty")
        if n_folds < 1:
            raise WalkForwardError("n_folds must be >= 1")
        if not (0.0 < oos_fraction < 1.0):
            raise WalkForwardError("oos_fraction must be between 0 and 1 (exclusive)")

        n          = len(timestamps)
        # OOS window size: divide total data across (n_folds+1) segments
        oos_n      = max(1, n // (n_folds + 1))
        is_min_n   = oos_n  # minimum IS size = 1 OOS window

        windows: list[WalkForwardWindow] = []
        for fold in range(n_folds):
            oos_start_idx = is_min_n + fold * oos_n
            oos_end_idx   = oos_start_idx + oos_n - 1

            if oos_end_idx >= n:
                break

            if anchored:
                is_start_idx = 0
            else:
                is_start_idx = max(0, oos_start_idx - is_min_n)

            is_end_idx = oos_start_idx - 1

            windows.append(WalkForwardWindow(
                fold      = fold,
                is_start  = timestamps[is_start_idx],
                is_end    = timestamps[is_end_idx],
                oos_start = timestamps[oos_start_idx],
                oos_end   = timestamps[oos_end_idx],
            ))

        return windows


    def efficiency(self, is_sharpe: float, oos_sharpe: float) -> float:
        """
        WFE = OOS_Sharpe / IS_Sharpe.

        A ratio above 0.5 indicates the strategy has not severely overfit.
        """
        if is_sharpe == 0:
            return 0.0
        return oos_sharpe / is_sharpe
