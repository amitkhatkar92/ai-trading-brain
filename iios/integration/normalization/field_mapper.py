"""iios/integration/normalization/field_mapper.py

Maps provider-specific field names to canonical schema fields.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from iios.integration.integration_exceptions import FieldMappingError


@dataclass
class FieldMapping:
    """Declares how to map one source field to a canonical target field."""

    source_field:  str
    target_field:  str
    required:      bool = False
    transform:     Any  = None      # Optional callable(value) → value
    default:       Any  = None


class FieldMapper:
    """
    Applies a set of FieldMappings to a raw provider record dict,
    producing a canonical-schema dict.

    Unmapped fields are dropped unless *pass_unknown* is True.
    """

    def __init__(
        self,
        mappings:     list[FieldMapping],
        pass_unknown: bool = False,
    ) -> None:
        self._mappings     = {m.source_field: m for m in mappings}
        self._pass_unknown = pass_unknown

    def add_mapping(self, mapping: FieldMapping) -> None:
        self._mappings[mapping.source_field] = mapping

    def map(self, source: dict[str, Any]) -> dict[str, Any]:
        """Apply mappings to *source* and return canonical dict."""
        result: dict[str, Any] = {}
        missing_required: list[str] = []

        for src_field, mapping in self._mappings.items():
            value = source.get(src_field, mapping.default)
            if value is None and mapping.required:
                missing_required.append(src_field)
                continue
            if value is not None and mapping.transform:
                try:
                    value = mapping.transform(value)
                except Exception as exc:
                    raise FieldMappingError(
                        f"Transform failed for field '{src_field}': {exc}"
                    ) from exc
            if value is not None:
                result[mapping.target_field] = value

        if missing_required:
            raise FieldMappingError(
                f"Required fields missing: {missing_required}"
            )

        if self._pass_unknown:
            for k, v in source.items():
                if k not in self._mappings:
                    result[k] = v

        return result

    def mapped_fields(self) -> list[str]:
        return list(self._mappings.keys())

    @staticmethod
    def build_identity(fields: list[str]) -> "FieldMapper":
        """Create a mapper that passes listed fields through unchanged."""
        return FieldMapper([FieldMapping(f, f) for f in fields])
