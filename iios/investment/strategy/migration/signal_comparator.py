"""iios/investment/strategy/migration/signal_comparator.py
Fine-grained comparison of strategy signal parameters.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class SignalField(str, Enum):
    """Fields that define a strategy's signal contract."""
    DIRECTION        = "direction"
    STOP_LOSS_PCT    = "stop_loss_pct"
    TARGET_MULTIPLIER = "target_multiplier"
    MIN_RR           = "min_rr"
    MAX_LOSS_PCT     = "max_loss_pct"
    BASE_STRATEGY    = "base_strategy"
    CATEGORY         = "category"


@dataclass(frozen=True)
class FieldComparison:
    """Result for a single field's comparison."""
    field:             SignalField
    legacy_value:      Any
    adapted_value:     Any
    match:             bool
    tolerance_applied: float
    deviation:         float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "field":             self.field.value,
            "legacy_value":      self.legacy_value,
            "adapted_value":     self.adapted_value,
            "match":             self.match,
            "tolerance":         self.tolerance_applied,
            "deviation":         round(self.deviation, 6),
        }


@dataclass(frozen=True)
class SignalComparison:
    """Comparison of all signal fields between legacy and adapted strategy."""
    strategy_id:       str
    strategy_name:     str
    field_comparisons: List[FieldComparison]
    overall_match:     bool
    match_rate:        float
    mismatched_fields: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy_id":       self.strategy_id,
            "strategy_name":     self.strategy_name,
            "overall_match":     self.overall_match,
            "match_rate":        round(self.match_rate, 4),
            "mismatched_fields": self.mismatched_fields,
            "fields":            [f.to_dict() for f in self.field_comparisons],
        }


_FLOAT_TOLERANCE = 1e-6


def _compare_field(
    signal_field:  SignalField,
    legacy_val:    Any,
    adapted_val:   Any,
    tolerance:     float = _FLOAT_TOLERANCE,
) -> FieldComparison:
    """Compare two field values and return a FieldComparison."""
    if isinstance(legacy_val, float) and isinstance(adapted_val, float):
        deviation = abs(legacy_val - adapted_val)
        match = deviation <= tolerance
    elif legacy_val is None and adapted_val is None:
        deviation = 0.0
        match = True
    else:
        deviation = 0.0
        match = str(legacy_val).strip().lower() == str(adapted_val).strip().lower()

    return FieldComparison(
        field=signal_field,
        legacy_value=legacy_val,
        adapted_value=adapted_val,
        match=match,
        tolerance_applied=tolerance,
        deviation=deviation if isinstance(deviation, float) else 0.0,
    )


class SignalComparator:
    """
    Compares legacy strategy signal parameters against adapter output.
    Reports per-field deviations and an overall match assessment.
    """

    def compare(
        self,
        strategy_id:   str,
        strategy_name: str,
        legacy_params: Dict[str, Any],
        adapted_params: Dict[str, Any],
        tolerance:     float = _FLOAT_TOLERANCE,
    ) -> SignalComparison:
        """
        Compare legacy and adapted parameter dicts field-by-field.

        Args:
            strategy_id:    ID of the strategy being compared.
            strategy_name:  Name of the strategy.
            legacy_params:  Dict from legacy metadata (e.g. min_rr, stop_loss_pct).
            adapted_params: Dict from adapter.get_risk_params() / definition.
            tolerance:      Float equality tolerance.

        Returns:
            SignalComparison with per-field and overall match results.
        """
        comparisons: List[FieldComparison] = []

        field_mappings = {
            SignalField.MIN_RR:           ("min_rr", "min_rr"),
            SignalField.MAX_LOSS_PCT:      ("max_loss_pct", "max_loss_pct"),
            SignalField.STOP_LOSS_PCT:     ("stop_loss_pct", "stop_loss_pct"),
            SignalField.TARGET_MULTIPLIER: ("target_multiplier", "target_multiplier"),
            SignalField.DIRECTION:         ("direction", "direction"),
            SignalField.CATEGORY:          ("category", "category"),
            SignalField.BASE_STRATEGY:     ("base_strategy", "base_strategy"),
        }

        for signal_f, (legacy_key, adapted_key) in field_mappings.items():
            l_val = legacy_params.get(legacy_key)
            a_val = adapted_params.get(adapted_key)
            if l_val is None and a_val is None:
                continue    # field absent on both sides — skip
            cmp = _compare_field(signal_f, l_val, a_val, tolerance)
            comparisons.append(cmp)

        total   = len(comparisons)
        matched = sum(1 for c in comparisons if c.match)
        rate    = matched / total if total > 0 else 1.0
        mismatched = [c.field.value for c in comparisons if not c.match]

        return SignalComparison(
            strategy_id=strategy_id,
            strategy_name=strategy_name,
            field_comparisons=comparisons,
            overall_match=len(mismatched) == 0,
            match_rate=rate,
            mismatched_fields=mismatched,
        )
