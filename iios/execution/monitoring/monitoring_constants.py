"""iios/execution/monitoring/monitoring_constants.py"""
from __future__ import annotations

from enum import Enum


class ExecutionRecordStatus(str, Enum):
    PENDING          = "pending"
    SUBMITTED        = "submitted"
    ACCEPTED         = "accepted"
    PARTIALLY_FILLED = "partially_filled"
    FULLY_FILLED     = "fully_filled"
    CANCELLED        = "cancelled"
    REJECTED         = "rejected"
    EXPIRED          = "expired"
    FAILED           = "failed"
    UNKNOWN          = "unknown"


class ExecutionEventType(str, Enum):
    ORDER_SUBMITTED       = "order_submitted"
    ORDER_ACCEPTED        = "order_accepted"
    ORDER_PARTIALLY_FILLED = "order_partially_filled"
    ORDER_FULLY_FILLED    = "order_fully_filled"
    ORDER_CANCELLED       = "order_cancelled"
    ORDER_REJECTED        = "order_rejected"
    ORDER_EXPIRED         = "order_expired"
    ORDER_MODIFIED        = "order_modified"
    EXECUTION_STARTED     = "execution_started"
    EXECUTION_COMPLETED   = "execution_completed"
    EXECUTION_FAILED      = "execution_failed"
    FILL_RECEIVED         = "fill_received"
    LATENCY_RECORDED      = "latency_recorded"


class FillType(str, Enum):
    PARTIAL  = "partial"
    COMPLETE = "complete"


class LatencyPhase(str, Enum):
    SUBMISSION      = "submission"
    ACKNOWLEDGEMENT = "acknowledgement"
    FIRST_FILL      = "first_fill"
    COMPLETE_FILL   = "complete_fill"
    TOTAL           = "total"
    ROUND_TRIP      = "round_trip"


class ReconciliationStatus(str, Enum):
    PENDING     = "pending"
    IN_PROGRESS = "in_progress"
    MATCHED     = "matched"
    DISCREPANT  = "discrepant"
    FAILED      = "failed"
    SKIPPED     = "skipped"


class DiscrepancyType(str, Enum):
    MISSING_INTERNAL = "missing_internal"
    MISSING_EXTERNAL = "missing_external"
    QUANTITY_MISMATCH = "quantity_mismatch"
    PRICE_MISMATCH    = "price_mismatch"
    STATUS_MISMATCH   = "status_mismatch"
    TIMING_MISMATCH   = "timing_mismatch"
    DUPLICATE         = "duplicate"
    UNKNOWN           = "unknown"


class EntityType(str, Enum):
    ORDER     = "order"
    TRADE     = "trade"
    POSITION  = "position"
    CASH      = "cash"
    PORTFOLIO = "portfolio"


class AuditEventType(str, Enum):
    ORDER_CREATED            = "order_created"
    ORDER_SUBMITTED          = "order_submitted"
    ORDER_MODIFIED           = "order_modified"
    ORDER_CANCELLED          = "order_cancelled"
    ORDER_FILLED             = "order_filled"
    ORDER_REJECTED           = "order_rejected"
    EXECUTION_STARTED        = "execution_started"
    EXECUTION_COMPLETED      = "execution_completed"
    EXECUTION_FAILED         = "execution_failed"
    FILL_RECEIVED            = "fill_received"
    RECONCILIATION_STARTED   = "reconciliation_started"
    RECONCILIATION_COMPLETED = "reconciliation_completed"
    DISCREPANCY_DETECTED     = "discrepancy_detected"
    ALERT_TRIGGERED          = "alert_triggered"
    SYSTEM_EVENT             = "system_event"


class AlertSeverity(str, Enum):
    CRITICAL = "critical"
    HIGH     = "high"
    MEDIUM   = "medium"
    LOW      = "low"
    INFO     = "info"


class AlertStatus(str, Enum):
    ACTIVE       = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED     = "resolved"
    SUPPRESSED   = "suppressed"


class SLAStatus(str, Enum):
    WITHIN_SLA = "within_sla"
    BREACHED   = "breached"
    AT_RISK    = "at_risk"
    NO_DATA    = "no_data"


class MonitoringStatus(str, Enum):
    INITIALIZING = "initializing"
    ACTIVE       = "active"
    PAUSED       = "paused"
    STOPPING     = "stopping"
    STOPPED      = "stopped"
    ERROR        = "error"


# ── Engine metadata ───────────────────────────────────────────────────────────

MONITORING_ENGINE_VERSION   = "1.0.0"
MONITORING_ENGINE_SYSTEM_ID = "iios:execution:monitoring:engine"

# ── Thresholds & limits ───────────────────────────────────────────────────────

DEFAULT_LATENCY_SLA_MS              = 5_000.0
DEFAULT_FILL_SLA_SEC                = 300.0
DEFAULT_HIGH_LATENCY_THRESHOLD_MS   = 1_000.0
DEFAULT_REJECTION_RATE_THRESHOLD    = 0.05       # 5%
DEFAULT_RECONCILIATION_TOLERANCE    = 0.01       # 1% / 1 unit
DEFAULT_MAX_AUDIT_EVENTS            = 100_000
DEFAULT_MAX_ALERTS                  = 10_000
DEFAULT_MAX_EXECUTION_RECORDS       = 50_000
DEFAULT_MAX_FILL_RECORDS            = 200_000
AUDIT_HASH_ALGORITHM                = "sha256"
LATENCY_PERCENTILES                 = (50, 75, 90, 95, 99)

# ── Terminal statuses ─────────────────────────────────────────────────────────

TERMINAL_EXECUTION_STATUSES = frozenset({
    ExecutionRecordStatus.FULLY_FILLED,
    ExecutionRecordStatus.CANCELLED,
    ExecutionRecordStatus.REJECTED,
    ExecutionRecordStatus.EXPIRED,
    ExecutionRecordStatus.FAILED,
})
