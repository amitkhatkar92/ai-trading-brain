"""iios/integration/history/compression/__init__.py

Lossless record-level compression utilities.
"""
from __future__ import annotations

import json
import zlib
from typing import Any

from iios.integration.history.history_constants import CompressionType


class DataCompressor:
    """
    Compresses and decompresses record payloads.

    Supports NONE (passthrough), ZLIB, and GZIP compression.
    Instances are stateless and thread-safe.
    """

    def compress(self, data: dict[str, Any], ctype: CompressionType) -> bytes:
        """Serialise ``data`` to bytes and optionally compress."""
        raw = json.dumps(data, default=str).encode("utf-8")
        if ctype == CompressionType.ZLIB:
            return zlib.compress(raw, level=6)
        if ctype == CompressionType.GZIP:
            import gzip
            return gzip.compress(raw, compresslevel=6)
        return raw   # CompressionType.NONE

    def decompress(self, payload: bytes, ctype: CompressionType) -> dict[str, Any]:
        """Decompress ``payload`` and deserialise to dict."""
        if ctype == CompressionType.ZLIB:
            raw = zlib.decompress(payload)
        elif ctype == CompressionType.GZIP:
            import gzip
            raw = gzip.decompress(payload)
        else:
            raw = payload
        return json.loads(raw.decode("utf-8"))

    def compress_bytes(self, data: bytes, ctype: CompressionType) -> bytes:
        if ctype == CompressionType.ZLIB:
            return zlib.compress(data, level=6)
        if ctype == CompressionType.GZIP:
            import gzip
            return gzip.compress(data, compresslevel=6)
        return data

    def decompress_bytes(self, payload: bytes, ctype: CompressionType) -> bytes:
        if ctype == CompressionType.ZLIB:
            return zlib.decompress(payload)
        if ctype == CompressionType.GZIP:
            import gzip
            return gzip.decompress(payload)
        return payload

    def estimate_ratio(self, data: bytes, ctype: CompressionType) -> float:
        """Return compressed / uncompressed length ratio (lower = better)."""
        if not data:
            return 1.0
        compressed = self.compress_bytes(data, ctype)
        return len(compressed) / len(data)
