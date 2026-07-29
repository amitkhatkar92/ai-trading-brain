"""
runtime_settings.py -- iios.ai.model_management.configuration
===============================================================
:class:`RuntimeSettings` — global defaults for the A2 module.

A2 Model Management — Phase 3, Module 2
"""
from __future__ import annotations

from dataclasses import dataclass

from ..core.model_tier import ModelTier


@dataclass
class RuntimeSettings:
    """Global runtime defaults for Model Management."""
    default_timeout_ms:          int       = 30_000
    max_retries:                 int       = 3
    default_tier:                ModelTier = ModelTier.STANDARD
    enable_failover:             bool      = True
    health_check_interval_s:     int       = 60
    failure_threshold:           int       = 3    # consecutive failures → UNAVAILABLE
