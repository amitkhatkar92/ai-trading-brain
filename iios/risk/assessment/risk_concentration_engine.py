"""
risk_concentration_engine.py — iios.risk.assessment
=====================================================
Concentration analysis engine — HHI, top-N, and diversification metrics.

C11 Risk Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from .constants import DEFAULT_MAX_CONCENTRATION, VERSION
from .exceptions import RiskCalculationError


class ConcentrationResult:
    """Concentration analysis results."""
    __slots__ = ("hhi", "effective_n", "top_position_weight",
                 "top_3_weight", "max_position_id",
                 "is_concentrated", "threshold_used")

    def __init__(
        self,
        hhi:               float,
        effective_n:       float,
        top_position_weight: float,
        top_3_weight:      float,
        max_position_id:   str,
        is_concentrated:   bool,
        threshold_used:    float,
    ) -> None:
        self.hhi                 = hhi
        self.effective_n         = effective_n
        self.top_position_weight = top_position_weight
        self.top_3_weight        = top_3_weight
        self.max_position_id     = max_position_id
        self.is_concentrated     = is_concentrated
        self.threshold_used      = threshold_used

    def to_dict(self) -> Dict[str, Any]:
        return {
            "hhi":                  self.hhi,
            "effective_n":          self.effective_n,
            "top_position_weight":  self.top_position_weight,
            "top_3_weight":         self.top_3_weight,
            "max_position_id":      self.max_position_id,
            "is_concentrated":      self.is_concentrated,
            "threshold_used":       self.threshold_used,
        }


class RiskConcentrationEngine:
    """
    Concentration analysis engine.

    Computes the Herfindahl-Hirschman Index (HHI), effective number of
    positions, and top-N concentration metrics.

    All methods are pure functions.
    """

    VERSION: str = VERSION

    # ------------------------------------------------------------------
    # HHI
    # ------------------------------------------------------------------

    def calculate_hhi(self, positions: Dict[str, float]) -> float:
        """
        Herfindahl-Hirschman Index.

        HHI = Σ w_i² where weights are normalised to sum to 1.

        Range: 1/N (perfectly diversified) to 1.0 (single position).
        Returns 0.0 for empty portfolios.
        """
        if not positions:
            return 0.0
        total = sum(abs(w) for w in positions.values())
        if total == 0:
            return 0.0
        normalized = [abs(w) / total for w in positions.values()]
        return sum(n ** 2 for n in normalized)

    def calculate_effective_n(self, positions: Dict[str, float]) -> float:
        """
        Effective number of positions = 1 / HHI.

        An equally-weighted N-position portfolio has HHI = 1/N,
        so effective_N = N.  Concentrated portfolios have effective_N → 1.
        """
        hhi = self.calculate_hhi(positions)
        return 1.0 / hhi if hhi > 0 else float(len(positions))

    # ------------------------------------------------------------------
    # Top-N concentration
    # ------------------------------------------------------------------

    def top_n_weight(
        self,
        positions: Dict[str, float],
        n:         int = 3,
    ) -> float:
        """
        Sum of the top-N position weights (normalised to 1).
        """
        if not positions:
            return 0.0
        total = sum(abs(w) for w in positions.values())
        if total == 0:
            return 0.0
        sorted_weights = sorted((abs(w) / total for w in positions.values()), reverse=True)
        return sum(sorted_weights[:n])

    def largest_position(
        self,
        positions: Dict[str, float],
    ) -> Tuple[str, float]:
        """Return (position_id, normalised_weight) of the largest position."""
        if not positions:
            return ("", 0.0)
        total = sum(abs(w) for w in positions.values())
        if total == 0:
            return ("", 0.0)
        max_id = max(positions, key=lambda k: abs(positions[k]))
        return (max_id, abs(positions[max_id]) / total)

    # ------------------------------------------------------------------
    # Full concentration result
    # ------------------------------------------------------------------

    def analyse(
        self,
        positions:  Dict[str, float],
        threshold:  float = DEFAULT_MAX_CONCENTRATION,
    ) -> ConcentrationResult:
        """
        Full concentration analysis.

        Parameters
        ----------
        positions :
            Map of position_id → weight (can be negative for shorts).
        threshold :
            Single-position concentration limit.
            Default: :data:`~.constants.DEFAULT_MAX_CONCENTRATION`.
        """
        hhi          = self.calculate_hhi(positions)
        eff_n        = self.calculate_effective_n(positions)
        top_3        = self.top_n_weight(positions, 3)
        max_id, max_w = self.largest_position(positions)

        return ConcentrationResult(
            hhi                  = hhi,
            effective_n          = eff_n,
            top_position_weight  = max_w,
            top_3_weight         = top_3,
            max_position_id      = max_id,
            is_concentrated      = max_w > threshold,
            threshold_used       = threshold,
        )
