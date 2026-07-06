"""
iios/infrastructure/serialization/toml_serializer.py
=====================================================
TOML serializer (Python 3.11+ stdlib tomllib for reads; tomli-w for writes).
"""

from __future__ import annotations

from typing import Any

from ..infrastructure_exceptions import SerializationError, DeserializationError

__all__ = ["TomlSerializer"]

try:
    import tomllib as _tomllib  # Python 3.11+
    _READ_AVAILABLE = True
except ImportError:
    try:
        import tomli as _tomllib  # type: ignore[no-redef]
        _READ_AVAILABLE = True
    except ImportError:
        _READ_AVAILABLE = False

try:
    import tomli_w as _tomli_w
    _WRITE_AVAILABLE = True
except ImportError:
    _WRITE_AVAILABLE = False


class TomlSerializer:
    """TOML serializer with graceful degradation."""

    def serialize(self, data: dict[str, Any]) -> str:
        if not _WRITE_AVAILABLE:
            raise SerializationError(
                "tomli-w is not installed. Run: pip install tomli-w",
                code="INF-SER-020",
            )
        try:
            return _tomli_w.dumps(data)  # type: ignore[union-attr]
        except Exception as exc:
            raise SerializationError(
                f"TOML serialization failed: {exc}", code="INF-SER-020"
            ) from exc

    def deserialize(self, text: str) -> dict[str, Any]:
        if not _READ_AVAILABLE:
            raise DeserializationError(
                "tomllib/tomli is not installed. Upgrade to Python 3.11+",
                code="INF-SER-021",
            )
        try:
            return _tomllib.loads(text)  # type: ignore[union-attr]
        except Exception as exc:
            raise DeserializationError(
                f"TOML deserialization failed: {exc}", code="INF-SER-021"
            ) from exc

    def serialize_bytes(self, data: dict[str, Any]) -> bytes:
        if not _WRITE_AVAILABLE:
            raise SerializationError(
                "tomli-w is not installed. Run: pip install tomli-w",
                code="INF-SER-020",
            )
        return _tomli_w.dumps(data).encode("utf-8")  # type: ignore[union-attr]

    def deserialize_bytes(self, data: bytes) -> dict[str, Any]:
        if not _READ_AVAILABLE:
            raise DeserializationError(
                "tomllib/tomli is not installed.", code="INF-SER-021"
            )
        return _tomllib.loads(data.decode("utf-8"))  # type: ignore[union-attr]

    @staticmethod
    def read_available() -> bool:
        return _READ_AVAILABLE

    @staticmethod
    def write_available() -> bool:
        return _WRITE_AVAILABLE
