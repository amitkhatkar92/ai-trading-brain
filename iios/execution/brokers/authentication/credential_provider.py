"""iios/execution/brokers/authentication/credential_provider.py

Secure credential retrieval interface.  Concrete providers inject credentials
from environment variables, vaults, encrypted files, or any secret store.
"""
from __future__ import annotations

import abc
import logging
import os
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class Credentials:
    """Credential payload delivered to an adapter's authenticate() call."""

    broker_id:    str             = ""
    api_key:      str             = ""
    api_secret:   str             = ""
    access_token: str             = ""
    refresh_token: str            = ""
    client_id:    str             = ""
    client_secret: str            = ""
    account_id:   str             = ""
    extra:        dict[str, Any]  = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialise without secrets."""
        return {
            "broker_id":   self.broker_id,
            "account_id":  self.account_id,
            "has_api_key": bool(self.api_key),
            "has_token":   bool(self.access_token),
            "extra_keys":  list(self.extra.keys()),
        }


class CredentialProvider(abc.ABC):
    """Abstract interface for obtaining credentials for a broker."""

    @abc.abstractmethod
    def get_credentials(self, broker_id: str) -> Credentials:
        """Return credentials for *broker_id*; raise if unavailable."""

    @abc.abstractmethod
    def has_credentials(self, broker_id: str) -> bool:
        """Return True if credentials are available for *broker_id*."""

    @abc.abstractmethod
    def rotate_credentials(self, broker_id: str, new_credentials: Credentials) -> None:
        """Replace credentials (e.g. after an OAuth rotation)."""


class EnvCredentialProvider(CredentialProvider):
    """
    Reads credentials from environment variables.

    Variable naming convention (all upper-cased):
        <BROKER_ID>_API_KEY
        <BROKER_ID>_API_SECRET
        <BROKER_ID>_ACCESS_TOKEN
        <BROKER_ID>_REFRESH_TOKEN
        <BROKER_ID>_CLIENT_ID
        <BROKER_ID>_CLIENT_SECRET
        <BROKER_ID>_ACCOUNT_ID
    """

    def __init__(self) -> None:
        self._overrides: dict[str, Credentials] = {}

    def _env(self, broker_id: str, suffix: str) -> str:
        key = f"{broker_id.upper()}_{suffix}"
        return os.environ.get(key, "")

    def get_credentials(self, broker_id: str) -> Credentials:
        if broker_id in self._overrides:
            return self._overrides[broker_id]
        creds = Credentials(
            broker_id=broker_id,
            api_key=self._env(broker_id, "API_KEY"),
            api_secret=self._env(broker_id, "API_SECRET"),
            access_token=self._env(broker_id, "ACCESS_TOKEN"),
            refresh_token=self._env(broker_id, "REFRESH_TOKEN"),
            client_id=self._env(broker_id, "CLIENT_ID"),
            client_secret=self._env(broker_id, "CLIENT_SECRET"),
            account_id=self._env(broker_id, "ACCOUNT_ID"),
        )
        return creds

    def has_credentials(self, broker_id: str) -> bool:
        if broker_id in self._overrides:
            return True
        creds = self.get_credentials(broker_id)
        return bool(creds.api_key or creds.access_token or creds.client_id)

    def rotate_credentials(self, broker_id: str, new_credentials: Credentials) -> None:
        logger.info("Rotating credentials for broker %s", broker_id)
        self._overrides[broker_id] = new_credentials


class InMemoryCredentialProvider(CredentialProvider):
    """Stores credentials in memory.  Suitable for tests and paper trading."""

    def __init__(self) -> None:
        self._store: dict[str, Credentials] = {}

    def register(self, credentials: Credentials) -> None:
        self._store[credentials.broker_id] = credentials

    def get_credentials(self, broker_id: str) -> Credentials:
        if broker_id not in self._store:
            return Credentials(broker_id=broker_id)
        return self._store[broker_id]

    def has_credentials(self, broker_id: str) -> bool:
        return broker_id in self._store

    def rotate_credentials(self, broker_id: str, new_credentials: Credentials) -> None:
        self._store[broker_id] = new_credentials
