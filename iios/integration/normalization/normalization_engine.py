"""iios/integration/normalization/normalization_engine.py

Applies all normalization steps to DataRecord objects.
"""
from __future__ import annotations

import logging
from typing import Any

from iios.integration.integration_constants import NormalizationStatus
from iios.integration.core.data_record import DataRecord
from iios.integration.normalization.schema_mapper import SchemaMapperRegistry
from iios.integration.normalization.timestamp_normalizer import TimestampNormalizer
from iios.integration.normalization.unit_converter import UnitConverter

logger = logging.getLogger(__name__)


class NormalizationResult:
    def __init__(self, records: list[DataRecord], status: NormalizationStatus, errors: list[str]) -> None:
        self.records = records
        self.status  = status
        self.errors  = errors


class NormalizationEngine:
    """
    Applies timestamp normalization, schema mapping, and unit conversion
    to a batch of DataRecord objects.

    Steps (all optional depending on configuration):
      1. Timestamp normalization — convert payload timestamp fields to UTC epoch
      2. Schema mapping        — apply provider→canonical field mapping
      3. Unit conversion       — normalise currencies / quantities if needed
    """

    def __init__(
        self,
        schema_registry:      SchemaMapperRegistry | None = None,
        timestamp_normalizer: TimestampNormalizer  | None = None,
        unit_converter:       UnitConverter        | None = None,
        timestamp_fields:     list[str]            | None = None,
    ) -> None:
        self._schema_registry  = schema_registry or SchemaMapperRegistry()
        self._ts_normalizer    = timestamp_normalizer or TimestampNormalizer()
        self._unit_converter   = unit_converter or UnitConverter()
        self._timestamp_fields = timestamp_fields or ["timestamp", "time", "date", "ts"]

    def normalize(self, record: DataRecord) -> DataRecord:
        """Normalize a single DataRecord. Returns a (possibly new) record."""
        import copy
        r = copy.copy(record)
        r.payload = dict(r.payload)

        # Step 1: Normalize timestamp in payload
        for tf in self._timestamp_fields:
            if tf in r.payload and r.payload[tf] is not None:
                try:
                    r.payload[tf] = self._ts_normalizer.normalize(r.payload[tf])
                except Exception:
                    pass  # log but do not drop

        # Step 2: Schema mapping
        if self._schema_registry.has(r.provider_id, r.category.value):
            mapper    = self._schema_registry.get(r.provider_id, r.category.value)
            r.payload = mapper.map_payload(r.payload)

        return r

    def normalize_batch(self, records: list[DataRecord]) -> list[DataRecord]:
        """Normalize a list of DataRecords; silently skip records that fail."""
        result = []
        for rec in records:
            try:
                result.append(self.normalize(rec))
            except Exception as exc:
                logger.warning("NormalizationEngine: skipping record %s: %s", rec.record_id, exc)
        return result

    def validate_batch(self, records: list[DataRecord]) -> NormalizationResult:
        """Try to normalize all records; return result with status."""
        normalized = []
        errors: list[str] = []
        for rec in records:
            try:
                normalized.append(self.normalize(rec))
            except Exception as exc:
                errors.append(str(exc))
        status = (
            NormalizationStatus.SUCCESS if not errors
            else NormalizationStatus.PARTIAL if normalized
            else NormalizationStatus.FAILED
        )
        return NormalizationResult(normalized, status, errors)

    # ── Accessors ─────────────────────────────────────────────────────────────

    @property
    def schema_registry(self) -> SchemaMapperRegistry:
        return self._schema_registry

    @property
    def unit_converter(self) -> UnitConverter:
        return self._unit_converter

    def statistics(self) -> dict[str, Any]:
        return self._schema_registry.statistics()
