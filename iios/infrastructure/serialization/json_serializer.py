"""
iios/infrastructure/serialization/json_serializer.py
=====================================================
JSON serialization with datetime and dataclass support.
"""

from __future__ import annotations

import dataclasses
import datetime
import json
from typing import Any

from ..infrastructure_exceptions import SerializationError, DeserializationError

__all__ = ["JsonSerializer"]


class _ExtendedEncoder(json.JSONEncoder):
    def default(self, obj: Any) -> Any:
        if isinstance(obj, (datetime.datetime, datetime.date)):
            return obj.isoformat()
        if isinstance(obj, datetime.timedelta):
            return obj.total_seconds()
        if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
            return dataclasses.asdict(obj)
        if hasattr(obj, "__dict__"):
            return obj.__dict__
        return super().default(obj)


class JsonSerializer:
    """JSON serializer with extended type support."""

    def serialize(self, data: Any, indent: int = 0) -> str:
        try:
            return json.dumps(data, cls=_ExtendedEncoder, indent=indent or None)
        except (TypeError, ValueError) as exc:
            raise SerializationError(
                f"JSON serialization failed: {exc}",
                code="INF-SER-001",
            ) from exc

    def deserialize(self, text: str, target_type: Any = None) -> Any:
        try:
            obj = json.loads(text)
        except json.JSONDecodeError as exc:
            raise DeserializationError(
                f"JSON deserialization failed: {exc}",
                code="INF-SER-002",
            ) from exc
        if target_type is not None and dataclasses.is_dataclass(target_type):
            try:
                return target_type(**obj)
            except TypeError as exc:
                raise DeserializationError(str(exc), code="INF-SER-002") from exc
        return obj

    def serialize_bytes(self, data: Any) -> bytes:
        return self.serialize(data).encode("utf-8")

    def deserialize_bytes(self, data: bytes) -> Any:
        return self.deserialize(data.decode("utf-8"))
