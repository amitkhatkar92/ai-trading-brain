"""iios/execution/brokers/broker_exceptions.py"""
from __future__ import annotations


# ── Base ──────────────────────────────────────────────────────────────────────

class BrokerFrameworkError(Exception):
    """BAF-000 — root for all broker framework errors."""
    error_code: str = "BAF-000"

    def __init__(self, message: str = "", code: str = "") -> None:
        super().__init__(message)
        self.message = message
        self.code    = code or self.__class__.error_code


# ── Broker lifecycle ──────────────────────────────────────────────────────────

class BrokerError(BrokerFrameworkError):
    """BAF-010 — generic broker error."""
    error_code = "BAF-010"


class BrokerNotFoundError(BrokerError):
    """BAF-011 — no adapter registered under the given broker_id."""
    error_code = "BAF-011"


class BrokerAlreadyExistsError(BrokerError):
    """BAF-012 — adapter already registered and overwrite=False."""
    error_code = "BAF-012"


class BrokerNotConnectedError(BrokerError):
    """BAF-013 — adapter exists but is not connected."""
    error_code = "BAF-013"


class BrokerConnectionFailedError(BrokerError):
    """BAF-014 — adapter failed to establish a connection."""
    error_code = "BAF-014"


# ── Adapter loading ───────────────────────────────────────────────────────────

class AdapterError(BrokerFrameworkError):
    """BAF-020 — adapter-level errors."""
    error_code = "BAF-020"


class AdapterLoadFailedError(AdapterError):
    """BAF-021 — adapter class could not be instantiated."""
    error_code = "BAF-021"


class InvalidAdapterError(AdapterError):
    """BAF-022 — class does not subclass BaseBrokerAdapter."""
    error_code = "BAF-022"


# ── Authentication ────────────────────────────────────────────────────────────

class BrokerAuthenticationError(BrokerFrameworkError):
    """BAF-030 — root authentication error."""
    error_code = "BAF-030"


class AuthenticationFailedError(BrokerAuthenticationError):
    """BAF-031 — credentials rejected."""
    error_code = "BAF-031"


class AuthenticationExpiredError(BrokerAuthenticationError):
    """BAF-032 — session / token has expired."""
    error_code = "BAF-032"


class InsufficientPermissionsError(BrokerAuthenticationError):
    """BAF-033 — authenticated but lacks required scope/permission."""
    error_code = "BAF-033"


# ── Capabilities ──────────────────────────────────────────────────────────────

class BrokerCapabilityError(BrokerFrameworkError):
    """BAF-040 — root capability error."""
    error_code = "BAF-040"


class CapabilityNotSupportedError(BrokerCapabilityError):
    """BAF-041 — broker does not support the requested capability."""
    error_code = "BAF-041"


class CapabilityUnavailableError(BrokerCapabilityError):
    """BAF-042 — capability exists but is temporarily unavailable."""
    error_code = "BAF-042"


# ── Requests / responses ──────────────────────────────────────────────────────

class BrokerRequestError(BrokerFrameworkError):
    """BAF-050 — invalid or malformed request."""
    error_code = "BAF-050"


class RequestTimeoutError(BrokerRequestError):
    """BAF-051 — request timed out before a response was received."""
    error_code = "BAF-051"


class RateLimitedError(BrokerRequestError):
    """BAF-052 — broker returned a rate-limit error."""
    error_code = "BAF-052"


class BrokerResponseError(BrokerFrameworkError):
    """BAF-060 — invalid or unparseable broker response."""
    error_code = "BAF-060"


class ResponseParseFailedError(BrokerResponseError):
    """BAF-061 — could not deserialise the raw broker payload."""
    error_code = "BAF-061"


# ── Connection ────────────────────────────────────────────────────────────────

class BrokerConnectionError(BrokerFrameworkError):
    """BAF-070 — transport-level connection errors."""
    error_code = "BAF-070"


class ConnectionTimeoutError(BrokerConnectionError):
    """BAF-071 — TCP/TLS handshake timed out."""
    error_code = "BAF-071"


class ConnectionRefusedError(BrokerConnectionError):
    """BAF-072 — remote host actively refused the connection."""
    error_code = "BAF-072"


class CircuitOpenError(BrokerConnectionError):
    """BAF-073 — circuit breaker is open; no calls are allowed."""
    error_code = "BAF-073"


# ── Registry ──────────────────────────────────────────────────────────────────

class BrokerRegistryError(BrokerFrameworkError):
    """BAF-080 — registry errors."""
    error_code = "BAF-080"


class BrokerRegistryOverflowError(BrokerRegistryError):
    """BAF-081 — registry has reached its maximum capacity."""
    error_code = "BAF-081"


# ── Manager / engine ──────────────────────────────────────────────────────────

class BrokerManagerError(BrokerFrameworkError):
    """BAF-090 — manager-level errors."""
    error_code = "BAF-090"


class BrokerManagerNotInitializedError(BrokerManagerError):
    """BAF-091 — manager used before initialisation."""
    error_code = "BAF-091"


class BrokerEngineAlreadyRunningError(BrokerManagerError):
    """BAF-092 — engine started twice."""
    error_code = "BAF-092"
