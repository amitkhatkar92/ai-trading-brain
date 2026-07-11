"""iios/investment/market/sector_rotation/rotation_detector.py
Detects sector rotation by comparing rank history.
"""
from __future__ import annotations

from collections import deque
from typing import Dict, List, Optional, Tuple

from iios.investment.market.sector_rotation.models import (
    CapitalFlowProfile,
    RotationSignal,
    RotationStrength,
    RotationType,
    SectorPerformance,
)
from iios.investment.market.sector_rotation.rotation_classifier import classify_rotation
from iios.investment.market.sector_rotation.sector_taxonomy import SectorTaxonomy

_MIN_RANK_CHANGE  = 2    # sectors must move at least N positions
_MIN_BARS_CONFIRM = 3    # bars before flagging "confirmed"


def _build_rank_map(
    sector_perfs: Dict[str, SectorPerformance]
) -> Dict[str, int]:
    """Return sector → rank (1 = best) ordered by momentum_score."""
    ranked = sorted(
        sector_perfs.values(),
        key=lambda p: p.momentum_score,
        reverse=True,
    )
    return {p.sector: i + 1 for i, p in enumerate(ranked)}


class RotationDetector:
    """Compares current sector rankings with historical rankings to detect
    capital rotation events."""

    def __init__(
        self,
        taxonomy: SectorTaxonomy,
        history_window: int = 20,
        min_rank_change: int = _MIN_RANK_CHANGE,
        confirm_bars: int = _MIN_BARS_CONFIRM,
    ) -> None:
        self._taxonomy      = taxonomy
        self._rank_history: deque[Dict[str, int]] = deque(maxlen=history_window)
        self._min_rank_chg  = min_rank_change
        self._confirm_bars  = confirm_bars
        self._active_signal: Optional[RotationSignal] = None
        self._signal_age:    int = 0

    def update(
        self,
        sector_perfs: Dict[str, SectorPerformance],
        capital_flows: Dict[str, CapitalFlowProfile],
    ) -> Optional[RotationSignal]:
        """Return a :class:`RotationSignal` if rotation is detected, else None."""
        current_ranks = _build_rank_map(sector_perfs)
        signal        = None

        if self._rank_history:
            prev_ranks = self._rank_history[-1]
            rising, falling = self._compute_movers(current_ranks, prev_ranks)

            if rising or falling:
                flow_disp = _flow_dispersion(capital_flows)
                rot_type, strength, confidence = classify_rotation(
                    rising, falling, self._taxonomy, flow_disp
                )

                if rot_type is not RotationType.NO_ROTATION:
                    # Increment age if same type, else reset
                    if (
                        self._active_signal is not None
                        and self._active_signal.rotation_type is rot_type
                    ):
                        self._signal_age += 1
                    else:
                        self._signal_age = 1

                    confirmed = self._signal_age >= self._confirm_bars
                    signal = RotationSignal(
                        rotation_type=rot_type,
                        strength=strength,
                        from_sectors=falling,
                        to_sectors=rising,
                        confidence=confidence,
                        bars_active=self._signal_age,
                        confirmed=confirmed,
                        description=self._describe(rot_type, rising, falling),
                    )
                    self._active_signal = signal
                else:
                    self._signal_age    = 0
                    self._active_signal = None

        self._rank_history.append(current_ranks)
        return signal

    def current_ranks(self) -> Optional[Dict[str, int]]:
        return dict(self._rank_history[-1]) if self._rank_history else None

    def rank_changes(self, lookback: int = 5) -> Dict[str, int]:
        """sector → rank improvement (positive = better rank now)."""
        if len(self._rank_history) < 2:
            return {}
        ref   = self._rank_history[max(0, len(self._rank_history) - lookback - 1)]
        curr  = self._rank_history[-1]
        return {
            sector: ref.get(sector, len(curr)) - rank
            for sector, rank in curr.items()
        }

    # ── internal helpers ──────────────────────────────────────────────────────

    def _compute_movers(
        self,
        current: Dict[str, int],
        previous: Dict[str, int],
    ) -> Tuple[List[str], List[str]]:
        rising:  List[str] = []
        falling: List[str] = []
        for sector, rank in current.items():
            prev_rank = previous.get(sector, rank)
            delta     = prev_rank - rank   # positive = improved rank
            if delta >= self._min_rank_chg:
                rising.append(sector)
            elif delta <= -self._min_rank_chg:
                falling.append(sector)
        return rising, falling

    @staticmethod
    def _describe(
        rot_type: RotationType, rising: List[str], falling: List[str]
    ) -> str:
        to_str   = ", ".join(rising[:3])  or "none"
        from_str = ", ".join(falling[:3]) or "none"
        return f"{rot_type.value}: into [{to_str}] from [{from_str}]"


def _flow_dispersion(flows: Dict[str, CapitalFlowProfile]) -> float:
    if len(flows) < 2:
        return 0.0
    signals = [f.net_flow_signal for f in flows.values()]
    mean    = sum(signals) / len(signals)
    var     = sum((x - mean) ** 2 for x in signals) / len(signals)
    return var ** 0.5
