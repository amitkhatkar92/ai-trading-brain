"""iios/execution/context/execution_environment.py
==================================================
ExecutionEnvironmentDescriptor — immutable descriptor of the
deployment environment in which an execution runs.

C6 Execution Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from iios.execution.context.constants import ExecutionEnvironment, ExecutionMode


@dataclass(frozen=True)
class ExecutionEnvironmentDescriptor:
    """
    Immutable descriptor of the deployment and runtime environment.

    Attached to every ExecutionContext; consumed by validators, monitors,
    and risk systems to adjust behaviour based on environment.
    """

    descriptor_id:   str                  = field(default_factory=lambda: str(uuid.uuid4()))
    environment:     ExecutionEnvironment = ExecutionEnvironment.PRODUCTION
    execution_mode:  ExecutionMode        = ExecutionMode.PAPER

    # Runtime identity
    host:            str = ""   # hostname or container ID
    region:          str = ""   # deployment region (e.g. "ap-south-1")
    cluster:         str = ""   # Kubernetes cluster or pod name
    version:         str = ""   # deployed application version
    git_sha:         str = ""   # build provenance

    # Feature flags
    live_orders_enabled:     bool = False
    risk_checks_enabled:     bool = True
    audit_enabled:           bool = True
    dry_run:                 bool = True   # True unless LIVE mode

    created_at: float = field(default_factory=time.time)
    metadata:   dict[str, Any] = field(default_factory=dict)

    # ── Computed properties ───────────────────────────────────────────────────

    @property
    def is_production(self) -> bool:
        return self.environment == ExecutionEnvironment.PRODUCTION

    @property
    def is_live(self) -> bool:
        return self.execution_mode == ExecutionMode.LIVE

    @property
    def allows_live_orders(self) -> bool:
        return self.live_orders_enabled and self.is_live and self.is_production

    # ── Factory helpers ───────────────────────────────────────────────────────

    @classmethod
    def paper(cls, **kwargs: Any) -> "ExecutionEnvironmentDescriptor":
        return cls(
            environment    = ExecutionEnvironment.PRODUCTION,
            execution_mode = ExecutionMode.PAPER,
            dry_run        = True,
            **kwargs,
        )

    @classmethod
    def backtest(cls, **kwargs: Any) -> "ExecutionEnvironmentDescriptor":
        return cls(
            environment    = ExecutionEnvironment.TESTING,
            execution_mode = ExecutionMode.BACKTEST,
            dry_run        = True,
            **kwargs,
        )

    @classmethod
    def live(cls, **kwargs: Any) -> "ExecutionEnvironmentDescriptor":
        return cls(
            environment          = ExecutionEnvironment.PRODUCTION,
            execution_mode       = ExecutionMode.LIVE,
            live_orders_enabled  = True,
            dry_run              = False,
            **kwargs,
        )

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        return {
            "descriptor_id":         self.descriptor_id,
            "environment":           self.environment.value,
            "execution_mode":        self.execution_mode.value,
            "host":                  self.host,
            "region":                self.region,
            "version":               self.version,
            "live_orders_enabled":   self.live_orders_enabled,
            "risk_checks_enabled":   self.risk_checks_enabled,
            "audit_enabled":         self.audit_enabled,
            "dry_run":               self.dry_run,
            "is_production":         self.is_production,
            "is_live":               self.is_live,
            "allows_live_orders":    self.allows_live_orders,
        }

    def __repr__(self) -> str:
        return (
            f"ExecutionEnvironmentDescriptor("
            f"env={self.environment.value}, "
            f"mode={self.execution_mode.value}, "
            f"dry_run={self.dry_run})"
        )
