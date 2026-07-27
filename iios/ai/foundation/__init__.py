"""
iios.ai.foundation
==================
A1 -- AI Foundation.

The foundation layer provides the shared contracts, base infrastructure,
and lifecycle mixin that every other AI Platform module (A2-A10) depends on.

Primary public entry point
--------------------------
Use AIFoundationGateway as the sole public interface::

    from iios.ai.foundation.gateway import AIFoundationGateway

    gw = AIFoundationGateway()
    gw.initialize()
    gw.start()
    health = gw.health()
    snap   = gw.snapshot()
    gw.stop()

Module layers
-------------
M1  lifecycle/   -- AILifecycleAwareMixin + foundation session management
M4  adapters/    -- AIProvider abstraction, configuration, token management
M5  snapshot/    -- Immutable state captures
M6  gateway/     -- AIFoundationGateway (sole public interface)

A1 AI Foundation -- Phase 3, Module 1
"""
from __future__ import annotations

from .gateway.ai_foundation_gateway import AIFoundationGateway

__all__ = ["AIFoundationGateway"]
