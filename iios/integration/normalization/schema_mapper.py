"""iios/integration/normalization/schema_mapper.py

Maps provider-specific record dicts to canonical DataRecord payloads.
A SchemaMapper is registered per (provider_id, DataCategory) pair.
"""
from __future__ import annotations

import abc
import threading
from typing import Any

from iios.integration.integration_exceptions import SchemaMapperNotFoundError
from iios.integration.core.data_record import DataRecord
from iios.integration.normalization.field_mapper import FieldMapper


class SchemaMapper(abc.ABC):
    """
    Abstract mapper from raw provider payload dict → canonical payload dict.
    """

    @property
    @abc.abstractmethod
    def provider_id(self) -> str: ...

    @property
    @abc.abstractmethod
    def category(self) -> str: ...

    @abc.abstractmethod
    def map_payload(self, raw: dict[str, Any]) -> dict[str, Any]:
        """Return canonical payload dict for *raw*."""

    def map_record(self, record: DataRecord) -> DataRecord:
        """Apply mapping to a DataRecord's payload in place (returns new record)."""
        import copy
        new = copy.copy(record)
        new.payload = self.map_payload(record.payload)
        return new

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider_id": self.provider_id,
            "category":    self.category,
        }


class SimpleSchemaMapper(SchemaMapper):
    """
    A SchemaMapper built from a FieldMapper.
    """

    def __init__(
        self,
        provider_id_: str,
        category_:    str,
        field_mapper: FieldMapper,
    ) -> None:
        self._provider_id = provider_id_
        self._category    = category_
        self._mapper      = field_mapper

    @property
    def provider_id(self) -> str:
        return self._provider_id

    @property
    def category(self) -> str:
        return self._category

    def map_payload(self, raw: dict[str, Any]) -> dict[str, Any]:
        return self._mapper.map(raw)


class SchemaMapperRegistry:
    """
    Global registry of SchemaMappers, keyed by (provider_id, category).

    Thread-safe.
    """

    def __init__(self) -> None:
        self._mappers: dict[tuple[str, str], SchemaMapper] = {}
        self._lock    = threading.RLock()

    def register(self, mapper: SchemaMapper) -> None:
        key = (mapper.provider_id, mapper.category)
        with self._lock:
            self._mappers[key] = mapper

    def get(self, provider_id: str, category: str) -> SchemaMapper:
        key = (provider_id, category)
        with self._lock:
            m = self._mappers.get(key)
        if m is None:
            raise SchemaMapperNotFoundError(
                f"No schema mapper for provider='{provider_id}' category='{category}'"
            )
        return m

    def has(self, provider_id: str, category: str) -> bool:
        with self._lock:
            return (provider_id, category) in self._mappers

    def all_mappers(self) -> list[SchemaMapper]:
        with self._lock:
            return list(self._mappers.values())

    def statistics(self) -> dict[str, Any]:
        with self._lock:
            return {"registered_mappers": len(self._mappers)}
