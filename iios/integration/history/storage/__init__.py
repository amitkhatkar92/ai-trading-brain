"""iios/integration/history/storage/__init__.py"""
from iios.integration.history.storage.storage_backend import StorageBackend, InMemoryStorageBackend

__all__ = ["StorageBackend", "InMemoryStorageBackend"]
