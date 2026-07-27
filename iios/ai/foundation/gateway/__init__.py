"""
iios.ai.foundation.gateway
===========================
A1 AI Foundation — M6 Gateway layer.

:class:`AIFoundationGateway` is the single public entry point for the
entire A1 AI Foundation module.  All A2–A10 modules import from here.

    >>> from iios.ai.foundation.gateway import AIFoundationGateway

A1 AI Foundation — Phase 3, Module 6
"""
from __future__ import annotations

from .ai_foundation_gateway import AIFoundationGateway

__all__ = ["AIFoundationGateway"]
