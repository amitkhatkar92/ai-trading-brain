"""
model_tier.py -- iios.ai.model_management.core
================================================
:class:`ModelTier` — cost/quality tier of a model.

A2 Model Management — Phase 3, Module 2
"""
from __future__ import annotations

from enum import Enum


class ModelTier(str, Enum):
    """Cost / quality tier classification."""
    BUDGET     = "budget"
    STANDARD   = "standard"
    PREMIUM    = "premium"
    ENTERPRISE = "enterprise"
