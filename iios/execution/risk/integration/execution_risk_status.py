"""iios/execution/risk/integration/execution_risk_status.py
==================================================
SubsystemStatus — status enum for the integration subsystem.

C6 Execution Intelligence — Phase 4, Module 6
"""
from __future__ import annotations

from enum import Enum


class SubsystemStatus(str, Enum):
    """
    Operational status of the Execution Risk Integration subsystem.

    UNINITIALIZED — engine created but initialize()/start() not called
    INITIALIZING  — initialize() in progress
    INITIALIZED   — initialized but not started
    RUNNING       — fully operational; evaluate() accepts requests
    DEGRADED      — running but one or more components are unhealthy
    STOPPING      — stop() in progress
    STOPPED       — stopped; can be restarted
    FAILED        — irrecoverable failure
    SHUTDOWN      — permanently shut down (terminal)
    """
    UNINITIALIZED = "uninitialized"
    INITIALIZING  = "initializing"
    INITIALIZED   = "initialized"
    RUNNING       = "running"
    DEGRADED      = "degraded"
    STOPPING      = "stopping"
    STOPPED       = "stopped"
    FAILED        = "failed"
    SHUTDOWN      = "shutdown"
