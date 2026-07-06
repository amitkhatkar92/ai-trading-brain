"""
iios/infrastructure/serialization/yaml_serializer.py
=====================================================
YAML serializer (requires PyYAML; degrades gracefully if absent).
"""

from __future__ import annotations

from typing import Any

from ..infrastructure_exceptions import SerializationError, DeserializationError

__all__ = ["YamlSerializer"]

try:
    import yaml as _yaml
    _YAML_AVAILABLE = True
except ImportError:
    _YAML_AVAILABLE = False


class YamlSerializer:
    """YAML serializer backed by PyYAML (optional dependency).

    Falls back to raising ``SerializationError`` with a helpful message
    if PyYAML is not installed.
    """

    def _check(self) -> None:
        if not _YAML_AVAILABLE:
            raise SerializationError(
                "PyYAML is not installed. Run: pip install pyyaml",
                code="INF-SER-010",
            )

    def serialize(self, data: Any, default_flow_style: bool = False) -> str:
        self._check()
        try:
            return _yaml.dump(data, default_flow_style=default_flow_style, allow_unicode=True)
        except Exception as exc:
            raise SerializationError(
                f"YAML serialization failed: {exc}", code="INF-SER-010"
            ) from exc

    def deserialize(self, text: str, loader: Any = None) -> Any:
        self._check()
        try:
            return _yaml.safe_load(text)
        except _yaml.YAMLError as exc:
            raise DeserializationError(
                f"YAML deserialization failed: {exc}", code="INF-SER-011"
            ) from exc

    def serialize_bytes(self, data: Any) -> bytes:
        return self.serialize(data).encode("utf-8")

    def deserialize_bytes(self, data: bytes) -> Any:
        return self.deserialize(data.decode("utf-8"))

    @staticmethod
    def is_available() -> bool:
        return _YAML_AVAILABLE
