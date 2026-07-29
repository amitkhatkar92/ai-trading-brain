"""
connector_interface.py -- iios.ai.capability.connectors
=========================================================
Interfaces for future external-service connectors.

Defines:
  - ConnectorType  — enumeration of supported connector categories
  - ConnectorStatus — lifecycle states
  - ConnectorDescriptor — provider-independent connector definition
  - BaseConnector  — abstract interface every connector must implement
  - ConnectorRegistry — thread-safe store for connector instances

Connector categories
--------------------
MARKET_DATA, BROKER_API, NEWS_SERVICE, EMAIL, CALENDAR,
FILE_STORAGE, DATABASE, CLOUD_STORAGE, HTTP_SERVICE, CUSTOM

A9 Enterprise Capability Platform — Phase 3, Module 9
"""
from __future__ import annotations

import threading
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

from ..exceptions.capability_exceptions import (
    AIConnectorNotFoundError,
    AIConnectorConnectionError,
)


class ConnectorType(str, Enum):
    """High-level category of an external-service connector."""
    MARKET_DATA   = "market_data"
    BROKER_API    = "broker_api"
    NEWS_SERVICE  = "news_service"
    EMAIL         = "email"
    CALENDAR      = "calendar"
    FILE_STORAGE  = "file_storage"
    DATABASE      = "database"
    CLOUD_STORAGE = "cloud_storage"
    HTTP_SERVICE  = "http_service"
    CUSTOM        = "custom"


class ConnectorStatus(str, Enum):
    """Lifecycle status of a connector instance."""
    DISCONNECTED = "disconnected"
    CONNECTING   = "connecting"
    CONNECTED    = "connected"
    ERROR        = "error"
    DISABLED     = "disabled"


@dataclass(frozen=True)
class ConnectorDescriptor:
    """Immutable, provider-independent connector definition."""

    connector_id:   str
    name:           str
    connector_type: ConnectorType
    version:        str
    description:    str
    auth_required:  bool
    endpoint:       str       # logical endpoint identifier, not a live URL

    @classmethod
    def create(
        cls,
        name:           str,
        connector_type: ConnectorType = ConnectorType.CUSTOM,
        version:        str           = "1.0.0",
        description:    str           = "",
        auth_required:  bool          = True,
        endpoint:       str           = "",
    ) -> "ConnectorDescriptor":
        return cls(
            connector_id   = str(uuid.uuid4()),
            name           = name,
            connector_type = connector_type,
            version        = version,
            description    = description,
            auth_required  = auth_required,
            endpoint       = endpoint,
        )


class BaseConnector(ABC):
    """
    Abstract base class for all enterprise connectors.

    Subclasses implement the five abstract methods; the platform never
    invokes external APIs — it only works through this interface.
    """

    def __init__(self, descriptor: ConnectorDescriptor) -> None:
        self._descriptor = descriptor
        self._status     = ConnectorStatus.DISCONNECTED

    @property
    def connector_id(self) -> str:
        return self._descriptor.connector_id

    @property
    def descriptor(self) -> ConnectorDescriptor:
        return self._descriptor

    @property
    def status(self) -> ConnectorStatus:
        return self._status

    @abstractmethod
    def connect(self) -> None:
        """Establish connection to the external service."""

    @abstractmethod
    def disconnect(self) -> None:
        """Close connection to the external service."""

    @abstractmethod
    def is_connected(self) -> bool:
        """Return True when the connector has an active connection."""

    @abstractmethod
    def ping(self) -> bool:
        """Lightweight health check; return True on success."""

    @abstractmethod
    def invoke(self, method: str, params: Dict[str, Any]) -> Any:
        """
        Invoke a method on the external service.

        Parameters
        ----------
        method:
            Logical method name (e.g. "get_quote", "send_email").
        params:
            Method parameters.

        Returns
        -------
        Any
            Provider-specific response payload.
        """


class ConnectorRegistry:
    """Thread-safe registry of :class:`BaseConnector` instances."""

    def __init__(self) -> None:
        self._lock:  threading.Lock                    = threading.Lock()
        self._store: Dict[str, BaseConnector]           = {}

    def register(self, connector: BaseConnector) -> None:
        with self._lock:
            self._store[connector.connector_id] = connector

    def deregister(self, connector_id: str) -> None:
        with self._lock:
            if connector_id not in self._store:
                raise AIConnectorNotFoundError(f"Connector '{connector_id}' not found")
            del self._store[connector_id]

    def get(self, connector_id: str) -> BaseConnector:
        with self._lock:
            c = self._store.get(connector_id)
        if c is None:
            raise AIConnectorNotFoundError(f"Connector '{connector_id}' not found")
        return c

    def get_optional(self, connector_id: str) -> Optional[BaseConnector]:
        with self._lock:
            return self._store.get(connector_id)

    def list_connectors(
        self,
        connector_type: Optional[ConnectorType] = None,
    ) -> List[BaseConnector]:
        with self._lock:
            connectors = list(self._store.values())
        if connector_type is not None:
            connectors = [c for c in connectors if c.descriptor.connector_type == connector_type]
        return connectors

    def count(self) -> int:
        with self._lock:
            return len(self._store)
