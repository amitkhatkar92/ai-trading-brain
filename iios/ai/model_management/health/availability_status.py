"""
availability_status.py -- iios.ai.model_management.health
===========================================================
:class:`AvailabilityStatus` — current availability state of a model.

A2 Model Management — Phase 3, Module 2
"""
from __future__ import annotations

from enum import Enum


class AvailabilityStatus(str, Enum):
    """Current health/availability state of a registered AI model."""
    AVAILABLE   = "available"
    DEGRADED    = "degraded"
    UNAVAILABLE = "unavailable"
    UNKNOWN     = "unknown"
