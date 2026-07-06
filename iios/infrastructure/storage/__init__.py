"""
iios/infrastructure/storage/__init__.py
"""

from __future__ import annotations

from .local_storage import LocalStorage
from .json_storage import JsonStorage
from .binary_storage import BinaryStorage
from .compressed_storage import CompressedStorage

__all__ = [
    "LocalStorage",
    "JsonStorage",
    "BinaryStorage",
    "CompressedStorage",
]
