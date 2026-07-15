"""iios/investment/workflow/workflow_types.py
Enumerations and constants for the Institutional Investment Workflow pipeline.
"""
from __future__ import annotations

from enum import Enum


class WorkflowStage(str, Enum):
    """Sequential pipeline stages in the Intelligence Layer."""
    INITIALIZED       = "initialized"
    MARKET            = "market"
    COMPANY           = "company"
    STRATEGY          = "strategy"
    DECISION          = "decision"
    PORTFOLIO         = "portfolio"
    PUBLISHED         = "published"
    FAILED            = "failed"
    CANCELLED         = "cancelled"


# Ordered stages used for progress tracking (excludes terminal states)
PIPELINE_STAGES: tuple[WorkflowStage, ...] = (
    WorkflowStage.MARKET,
    WorkflowStage.COMPANY,
    WorkflowStage.STRATEGY,
    WorkflowStage.DECISION,
    WorkflowStage.PORTFOLIO,
)

TERMINAL_STAGES: frozenset[WorkflowStage] = frozenset({
    WorkflowStage.PUBLISHED,
    WorkflowStage.FAILED,
    WorkflowStage.CANCELLED,
})


class PipelineEventType(str, Enum):
    """Events emitted by the workflow pipeline."""
    WORKFLOW_STARTED           = "workflow_started"
    STAGE_STARTED              = "stage_started"
    STAGE_COMPLETED            = "stage_completed"
    STAGE_RETRYING             = "stage_retrying"
    STAGE_FAILED               = "stage_failed"
    WORKFLOW_COMPLETED         = "workflow_completed"
    WORKFLOW_FAILED            = "workflow_failed"
    WORKFLOW_CANCELLED         = "workflow_cancelled"
    PORTFOLIO_SNAPSHOT_PUBLISHED = "portfolio_snapshot_published"


class StageStatus(str, Enum):
    """Result status of a single pipeline stage attempt."""
    PENDING   = "pending"
    RUNNING   = "running"
    COMPLETED = "completed"
    FAILED    = "failed"
    SKIPPED   = "skipped"


# ── Constants ─────────────────────────────────────────────────────────────────

WORKFLOW_VERSION: str = "1.0.0"

# Default retry / timeout parameters
DEFAULT_MAX_RETRIES:         int   = 2
DEFAULT_STAGE_TIMEOUT_SEC:   float = 30.0
DEFAULT_RETRY_DELAY_SEC:     float = 0.5
DEFAULT_MIN_QUALITY_MARKET:  float = 0.0   # no hard gate; warnings only
DEFAULT_MIN_QUALITY_COMPANY: float = 0.0
DEFAULT_MIN_QUALITY_STRATEGY: float = 0.0
DEFAULT_MIN_QUALITY_DECISION: float = 0.0
DEFAULT_MIN_QUALITY_PORTFOLIO: float = 0.0
