"""
model_configuration.py -- iios.ai.model_management.configuration
==================================================================
:class:`ModelConfiguration` — per-model runtime configuration.

A2 Model Management — Phase 3, Module 2
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ModelConfiguration:
    """Per-model runtime settings."""
    model_id:                 str
    max_requests_per_minute:  int   = 60
    timeout_ms:               int   = 30_000
    retry_count:              int   = 3
    enabled:                  bool  = True

    def with_timeout(self, timeout_ms: int) -> "ModelConfiguration":
        return ModelConfiguration(
            model_id=self.model_id,
            max_requests_per_minute=self.max_requests_per_minute,
            timeout_ms=timeout_ms,
            retry_count=self.retry_count,
            enabled=self.enabled,
        )
