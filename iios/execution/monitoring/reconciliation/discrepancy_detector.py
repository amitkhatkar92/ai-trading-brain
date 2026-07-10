"""iios/execution/monitoring/reconciliation/discrepancy_detector.py"""
from __future__ import annotations

import math
from typing import Any

from iios.execution.monitoring.monitoring_constants import (
    AlertSeverity,
    DEFAULT_RECONCILIATION_TOLERANCE,
    DiscrepancyType,
)
from iios.execution.monitoring.reconciliation.reconciliation_result import Discrepancy


class DiscrepancyDetector:
    """
    Compares two record dicts (internal vs external) field by field
    and returns a list of Discrepancy objects.

    No broker-specific logic.  Field names must be normalised by
    the caller before comparison.
    """

    def __init__(self, tolerance: float = DEFAULT_RECONCILIATION_TOLERANCE) -> None:
        self._tolerance = tolerance

    # ── Public API ────────────────────────────────────────────────────────────

    def detect(
        self,
        internal: dict[str, Any] | None,
        external: dict[str, Any] | None,
        fields_to_compare: list[str] | None = None,
    ) -> list[Discrepancy]:
        if internal is None and external is None:
            return []
        if internal is None:
            return [Discrepancy(
                discrepancy_type=DiscrepancyType.MISSING_INTERNAL,
                field_name="_record",
                external_value=external,
                severity=AlertSeverity.HIGH,
                description="Internal record is missing",
            )]
        if external is None:
            return [Discrepancy(
                discrepancy_type=DiscrepancyType.MISSING_EXTERNAL,
                field_name="_record",
                internal_value=internal,
                severity=AlertSeverity.MEDIUM,
                description="External record is missing",
            )]
        all_keys = fields_to_compare or list(set(internal) | set(external))
        discrepancies: list[Discrepancy] = []
        for key in all_keys:
            iv = internal.get(key)
            ev = external.get(key)
            disc = self._compare_field(key, iv, ev)
            if disc:
                discrepancies.append(disc)
        return discrepancies

    def detect_duplicates(
        self,
        records: list[dict[str, Any]],
        id_field: str = "order_id",
    ) -> list[Discrepancy]:
        """Find duplicate entries by *id_field* in *records*."""
        seen:   dict[str, int] = {}
        result: list[Discrepancy] = []
        for rec in records:
            rid = rec.get(id_field, "")
            if rid in seen:
                result.append(Discrepancy(
                    discrepancy_type=DiscrepancyType.DUPLICATE,
                    field_name=id_field,
                    internal_value=rid,
                    external_value=rid,
                    severity=AlertSeverity.HIGH,
                    description=f"Duplicate {id_field}='{rid}' detected",
                ))
            seen[rid] = seen.get(rid, 0) + 1
        return result

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _compare_field(
        self, field: str, iv: Any, ev: Any
    ) -> Discrepancy | None:
        if iv is None and ev is None:
            return None
        if iv is None:
            return Discrepancy(
                discrepancy_type=DiscrepancyType.MISSING_INTERNAL,
                field_name=field,
                internal_value=iv,
                external_value=ev,
                severity=AlertSeverity.HIGH,
                description=f"Field '{field}' present in external but missing internally",
            )
        if ev is None:
            return Discrepancy(
                discrepancy_type=DiscrepancyType.MISSING_EXTERNAL,
                field_name=field,
                internal_value=iv,
                external_value=ev,
                severity=AlertSeverity.MEDIUM,
                description=f"Field '{field}' present internally but missing externally",
            )
        if isinstance(iv, (int, float)) and isinstance(ev, (int, float)):
            return self._compare_numeric(field, float(iv), float(ev))
        if iv != ev:
            dtype = (
                DiscrepancyType.STATUS_MISMATCH
                if "status" in field.lower()
                else DiscrepancyType.UNKNOWN
            )
            return Discrepancy(
                discrepancy_type=dtype,
                field_name=field,
                internal_value=iv,
                external_value=ev,
                severity=AlertSeverity.MEDIUM,
                description=f"Field '{field}' mismatch: {iv!r} vs {ev!r}",
            )
        return None

    def _compare_numeric(
        self, field: str, iv: float, ev: float
    ) -> Discrepancy | None:
        if iv == 0.0 and ev == 0.0:
            return None
        max_val = max(abs(iv), abs(ev), 1e-10)
        rel_diff = abs(iv - ev) / max_val
        if rel_diff <= self._tolerance:
            return None
        dtype = (
            DiscrepancyType.QUANTITY_MISMATCH
            if "qty" in field.lower() or "quantity" in field.lower()
            else DiscrepancyType.PRICE_MISMATCH
            if "price" in field.lower()
            else DiscrepancyType.UNKNOWN
        )
        return Discrepancy(
            discrepancy_type=dtype,
            field_name=field,
            internal_value=iv,
            external_value=ev,
            severity=AlertSeverity.HIGH,
            description=f"Numeric mismatch on '{field}': {iv} vs {ev} (diff={rel_diff:.4%})",
        )
