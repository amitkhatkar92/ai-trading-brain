"""
tests/unit/infrastructure/test_storage.py
==========================================
Tests for the iios.infrastructure.storage subpackage.
"""

from __future__ import annotations

import pathlib
import tempfile
import pytest

from iios.infrastructure.storage import (
    LocalStorage, JsonStorage, BinaryStorage, CompressedStorage,
)
from iios.infrastructure.infrastructure_exceptions import StorageError


@pytest.fixture
def tmp_root(tmp_path):
    return str(tmp_path / "store")


class TestLocalStorage:
    def test_write_and_read(self, tmp_root):
        store = LocalStorage(tmp_root)
        store.write("file.bin", b"hello world")
        assert store.read("file.bin") == b"hello world"

    def test_read_missing_raises(self, tmp_root):
        store = LocalStorage(tmp_root)
        with pytest.raises(StorageError):
            store.read("nonexistent")

    def test_delete(self, tmp_root):
        store = LocalStorage(tmp_root)
        store.write("x.bin", b"data")
        assert store.delete("x.bin")
        assert not store.exists("x.bin")

    def test_delete_missing(self, tmp_root):
        store = LocalStorage(tmp_root)
        assert not store.delete("nonexistent")

    def test_exists(self, tmp_root):
        store = LocalStorage(tmp_root)
        store.write("a.bin", b"1")
        assert store.exists("a.bin")
        assert not store.exists("b.bin")

    def test_list(self, tmp_root):
        store = LocalStorage(tmp_root)
        store.write("a.bin", b"1")
        store.write("b.bin", b"2")
        keys = store.list()
        assert len(keys) == 2

    def test_list_prefix(self, tmp_root):
        store = LocalStorage(tmp_root)
        store.write("sub/a.bin", b"1")
        store.write("other/b.bin", b"2")
        keys = store.list("sub")
        assert all("sub" in k for k in keys)

    def test_overwrite_false_raises(self, tmp_root):
        store = LocalStorage(tmp_root)
        store.write("x.bin", b"original")
        with pytest.raises(StorageError):
            store.write("x.bin", b"new", overwrite=False)

    def test_path_traversal_blocked(self, tmp_root):
        store = LocalStorage(tmp_root)
        with pytest.raises(StorageError):
            store.write("../../etc/passwd", b"hack")

    def test_metadata(self, tmp_root):
        store = LocalStorage(tmp_root)
        store.write("x.bin", b"data")
        meta = store.metadata("x.bin")
        assert meta.key == "x.bin"
        assert meta.size_bytes == 4
        assert meta.checksum is not None

    def test_write_returns_metadata(self, tmp_root):
        store = LocalStorage(tmp_root)
        meta = store.write("x.bin", b"abc")
        assert meta.size_bytes == 3


class TestJsonStorage:
    def test_write_and_read(self, tmp_root):
        store = JsonStorage(tmp_root)
        store.write("config", {"key": "value", "num": 42})
        obj = store.read("config")
        assert obj == {"key": "value", "num": 42}

    def test_list(self, tmp_root):
        store = JsonStorage(tmp_root)
        store.write("a", {"x": 1})
        store.write("b", {"y": 2})
        keys = store.list()
        assert "a" in keys and "b" in keys

    def test_delete(self, tmp_root):
        store = JsonStorage(tmp_root)
        store.write("k", {"v": 1})
        assert store.delete("k")
        assert not store.exists("k")

    def test_read_missing_raises(self, tmp_root):
        store = JsonStorage(tmp_root)
        with pytest.raises(StorageError):
            store.read("nonexistent")


class TestBinaryStorage:
    def test_write_and_read(self, tmp_root):
        store = BinaryStorage(tmp_root)
        store.write("img.png", b"\x89PNG\r\n\x1a\n")
        assert store.read("img.png").startswith(b"\x89PNG")

    def test_exists(self, tmp_root):
        store = BinaryStorage(tmp_root)
        store.write("x", b"data")
        assert store.exists("x")


class TestCompressedStorage:
    def test_roundtrip(self, tmp_root):
        store = CompressedStorage(tmp_root)
        original = b"a" * 1000  # highly compressible
        store.write("blob", original)
        assert store.read("blob") == original

    def test_compressed_file_smaller(self, tmp_root):
        store = CompressedStorage(tmp_root)
        data = b"x" * 10_000
        store.write("big", data)
        compressed_path = pathlib.Path(tmp_root) / "big.gz"
        assert compressed_path.stat().st_size < len(data)

    def test_delete_and_exists(self, tmp_root):
        store = CompressedStorage(tmp_root)
        store.write("k", b"data")
        assert store.exists("k")
        store.delete("k")
        assert not store.exists("k")
