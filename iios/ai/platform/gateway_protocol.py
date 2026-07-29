"""
gateway_protocol.py -- iios.ai.platform.gateway_protocol
==========================================================
:class:`GatewayProtocol` — formal structural Protocol for all AI Platform
M6 gateway objects.

Resolves AUD-I-001 from the F1 Architecture Audit:
  "Bootstrap duck-typed protocol not captured as a formal Protocol."

Any class satisfying this Protocol can be registered with the Platform
Bootstrap without importing from any AI module, preserving the star-topology
isolation guarantee (A2-A10 depend on A1 only, zero cross-imports).

Runtime checking via ``isinstance(gw, GatewayProtocol)`` is supported.

Layer:   AI PLATFORM BOOTSTRAP
Resolves: F1 AUD-I-001
Version: 1.0.0
Status:  stable
"""
from __future__ import annotations

from typing import Any, Dict, Protocol, runtime_checkable


@runtime_checkable
class GatewayProtocol(Protocol):
    """
    Structural protocol satisfied by every IIOS AI Platform M6 gateway.

    Minimum required surface
    ------------------------
    Class attributes (metadata)::

        SYSTEM_ID   : str   — unique dotted id, e.g. "iios:ai:foundation:gateway"
        VERSION     : str   — semver string,     e.g. "1.0.0"
        MODULE_ID   : str   — short module code, e.g. "A1"
        MODULE_NAME : str   — human name,         e.g. "AI Foundation"

    Instance methods::

        start()    → None
        stop()     → None
        restart()  → None
        health()   → Dict[str, Any]
        status()   → Dict[str, Any]
        snapshot() → Any

    Usage::

        from iios.ai.platform import GatewayProtocol

        def register(gw: GatewayProtocol) -> None:
            assert isinstance(gw, GatewayProtocol)   # runtime check
            ...
    """

    # ── Mandatory class-level metadata ────────────────────────────────────────

    SYSTEM_ID  : str
    VERSION    : str
    MODULE_ID  : str
    MODULE_NAME: str

    # ── Mandatory lifecycle methods ───────────────────────────────────────────

    def start(self) -> None:
        """Start the gateway (idempotent)."""
        ...

    def stop(self) -> None:
        """Stop the gateway and release resources."""
        ...

    def restart(self) -> None:
        """Stop then start the gateway."""
        ...

    def health(self) -> Dict[str, Any]:
        """Return structured health dict (status, latency, counts)."""
        ...

    def status(self) -> Dict[str, Any]:
        """Return structured status dict (phase, uptime, version)."""
        ...

    def snapshot(self) -> Any:
        """Return immutable point-in-time state snapshot."""
        ...
