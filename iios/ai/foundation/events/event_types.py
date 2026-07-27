"""
event_types.py -- iios.ai.foundation.events
============================================
Event type enumeration for the AI Foundation event framework.

A1 AI Foundation -- Phase 3, Provider Runtime
"""
from __future__ import annotations
from enum import Enum


class AIEventType(str, Enum):
    # Session lifecycle
    SESSION_STARTED          = "ai.session.started"
    SESSION_ENDED            = "ai.session.ended"
    SESSION_EXPIRED          = "ai.session.expired"
    SESSION_FAILED           = "ai.session.failed"

    # Execution lifecycle
    EXECUTION_STARTED        = "ai.execution.started"
    EXECUTION_COMPLETED      = "ai.execution.completed"
    EXECUTION_FAILED         = "ai.execution.failed"
    EXECUTION_CANCELLED      = "ai.execution.cancelled"
    EXECUTION_TIMED_OUT      = "ai.execution.timed_out"

    # Provider lifecycle
    PROVIDER_REGISTERED      = "ai.provider.registered"
    PROVIDER_DEREGISTERED    = "ai.provider.deregistered"
    PROVIDER_SELECTED        = "ai.provider.selected"
    PROVIDER_UNAVAILABLE     = "ai.provider.unavailable"
    PROVIDER_RECOVERED       = "ai.provider.recovered"
    PROVIDER_HEALTH_CHANGED  = "ai.provider.health_changed"

    # Retry lifecycle
    RETRY_STARTED            = "ai.retry.started"
    RETRY_COMPLETED          = "ai.retry.completed"
    RETRY_EXHAUSTED          = "ai.retry.exhausted"

    # Pipeline events
    PIPELINE_STAGE_STARTED   = "ai.pipeline.stage_started"
    PIPELINE_STAGE_COMPLETED = "ai.pipeline.stage_completed"
    PIPELINE_STAGE_FAILED    = "ai.pipeline.stage_failed"

    # Policy events
    POLICY_EVALUATED         = "ai.policy.evaluated"
    POLICY_BLOCKED           = "ai.policy.blocked"

    # Cost / budget events
    TOKEN_BUDGET_EXCEEDED    = "ai.cost.token_budget_exceeded"
    COST_THRESHOLD_EXCEEDED  = "ai.cost.threshold_exceeded"
