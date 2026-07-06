"""
tests/unit/infrastructure/test_serialization.py
===============================================
Tests for the iios.infrastructure.serialization subpackage.
"""

from __future__ import annotations

import dataclasses
import datetime
import pytest

from iios.infrastructure.serialization import (
    JsonSerializer, YamlSerializer, TomlSerializer,
    SerializerRegistry, get_serializer_registry, reset_serializer_registry,
)
from iios.infrastructure.infrastructure_exceptions import SerializationError, DeserializationError


@dataclasses.dataclass
class SampleDC:
    name: str
    value: int


class TestJsonSerializer:
    def setup_method(self):
        self.ser = JsonSerializer()

    def test_serialize_dict(self):
        text = self.ser.serialize({"a": 1, "b": [1, 2, 3]})
        assert '"a"' in text
        assert "1" in text

    def test_serialize_datetime(self):
        dt = datetime.datetime(2026, 5, 1, 9, 30)
        text = self.ser.serialize({"ts": dt})
        assert "2026-05-01" in text

    def test_serialize_dataclass(self):
        obj = SampleDC(name="RELIANCE", value=2850)
        text = self.ser.serialize(obj)
        assert "RELIANCE" in text

    def test_deserialize(self):
        obj = self.ser.deserialize('{"x": 42}')
        assert obj == {"x": 42}

    def test_deserialize_invalid_raises(self):
        with pytest.raises(DeserializationError):
            self.ser.deserialize("{invalid json}")

    def test_deserialize_to_dataclass(self):
        obj = self.ser.deserialize('{"name": "RELIANCE", "value": 2850}', SampleDC)
        assert obj.name == "RELIANCE"
        assert obj.value == 2850

    def test_serialize_bytes(self):
        raw = self.ser.serialize_bytes({"k": "v"})
        assert isinstance(raw, bytes)

    def test_deserialize_bytes(self):
        obj = self.ser.deserialize_bytes(b'{"k": "v"}')
        assert obj == {"k": "v"}

    def test_serialize_with_indent(self):
        text = self.ser.serialize({"a": 1}, indent=2)
        assert "\n" in text


class TestYamlSerializer:
    def setup_method(self):
        self.ser = YamlSerializer()

    def test_available_flag(self):
        # Just verifying the flag exists; may be True or False
        assert isinstance(YamlSerializer.is_available(), bool)

    def test_serialize_deserialize_when_available(self):
        if not YamlSerializer.is_available():
            pytest.skip("PyYAML not installed")
        text = self.ser.serialize({"x": 1, "y": [2, 3]})
        obj = self.ser.deserialize(text)
        assert obj["x"] == 1
        assert obj["y"] == [2, 3]

    def test_raises_when_unavailable(self, monkeypatch):
        # Simulate unavailability
        import iios.infrastructure.serialization.yaml_serializer as mod
        original = mod._YAML_AVAILABLE
        mod._YAML_AVAILABLE = False
        with pytest.raises(SerializationError, match="PyYAML"):
            self.ser.serialize({"x": 1})
        mod._YAML_AVAILABLE = original


class TestTomlSerializer:
    def setup_method(self):
        self.ser = TomlSerializer()

    def test_available_flags(self):
        assert isinstance(TomlSerializer.read_available(), bool)
        assert isinstance(TomlSerializer.write_available(), bool)

    def test_serialize_deserialize_when_available(self):
        if not TomlSerializer.read_available() or not TomlSerializer.write_available():
            pytest.skip("TOML libs not installed")
        data = {"name": "IIOS", "version": 2}
        text = self.ser.serialize(data)
        obj = self.ser.deserialize(text)
        assert obj["name"] == "IIOS"


class TestSerializerRegistry:
    def setup_method(self):
        reset_serializer_registry()

    def teardown_method(self):
        reset_serializer_registry()

    def test_register_and_get(self):
        reg = get_serializer_registry()
        ser = JsonSerializer()
        reg.register("json", ser)
        assert reg.get("json") is ser

    def test_register_duplicate_raises(self):
        reg = get_serializer_registry()
        reg.register("json", JsonSerializer())
        with pytest.raises(SerializationError):
            reg.register("json", JsonSerializer())

    def test_register_with_override(self):
        reg = get_serializer_registry()
        reg.register("json", JsonSerializer())
        reg.register("json", JsonSerializer(), allow_override=True)

    def test_names(self):
        reg = get_serializer_registry()
        reg.register("json", JsonSerializer())
        assert "json" in reg.names()

    def test_singleton(self):
        r1 = get_serializer_registry()
        r2 = get_serializer_registry()
        assert r1 is r2
