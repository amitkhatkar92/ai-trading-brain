# Snapshot Schema Guide

## WorkflowSnapshot Field Reference

### Identity Fields

| Field | Type | Prefix | Description |
|---|---|---|---|
| `snapshot_id` | str | `wsnap-` | Unique snapshot identifier |
| `snapshot_version` | str | — | Schema version (`"1.0"`) |
| `workflow_id` | str | — | Parent workflow identifier |
| `workflow_session_id` | str | — | Session that spawned this execution |
| `workflow_execution_id` | str | — | Execution run identifier |
| `enterprise_session_id` | str | — | Enterprise correlation scope |
| `workflow_name` | str | — | Human-readable workflow name |
| `workflow_category` | str | — | Category tag (e.g. "financial") |
| `workflow_type` | str | — | Type tag (e.g. "approval") |
| `correlation_id` | str | — | Cross-system correlation |
| `trace_id` | str | — | Distributed trace identifier |

### Status Fields

| Field | Type | Default | Values |
|---|---|---|---|
| `snapshot_status` | SnapshotStatus | PENDING | PENDING / VALID / INVALID / PUBLISHED / SUPERSEDED / ARCHIVED |
| `execution_status` | ExecutionStatus | COMPLETED | PENDING / QUEUED / RUNNING / PAUSED / COMPLETED / FAILED / TIMED_OUT / CANCELLED |
| `governance_decision` | GovernanceDecision | NOT_EVALUATED | APPROVED / REJECTED / PENDING / BLOCKED / … (10 values) |
| `lifecycle_state` | LifecycleState | COMPLETED | CREATED / INITIALISING / ACTIVE / PAUSED / COMPLETED / FAILED / ARCHIVED / TERMINATED |
| `health_status` | WorkflowHealthStatus | UNKNOWN | HEALTHY / DEGRADED / FAILED / UNKNOWN — **computed, not settable** |

### Workflow Progress

| Field | Type | Description |
|---|---|---|
| `priority` | int | Scheduling priority (0 = lowest) |
| `execution_mode` | str | e.g. "sequential", "parallel" |
| `current_step` | str | Active step label |
| `completed_steps` | int | Steps already finished |
| `remaining_steps` | int | Steps not yet started |
| `total_steps` | int | Total step count |
| `execution_progress` | float | 0.0 – 1.0 |

### Execution Timings

| Field | Type | Unit |
|---|---|---|
| `execution_duration_ms` | float | milliseconds |
| `queue_time_ms` | float | milliseconds |
| `scheduling_time_ms` | float | milliseconds |
| `execution_time_ms` | float | milliseconds |
| `retry_count` | int | — |
| `timeout_count` | int | — |
| `compensation_count` | int | — |
| `checkpoint_count` | int | — |
| `recovery_status` | str | — |

### Resource Summary

| Field | Type | Description |
|---|---|---|
| `allocated_resources` | int | Total resources reserved |
| `active_resources` | int | Currently in use |
| `released_resources` | int | Already freed |
| `resource_utilization` | float | 0.0 – 1.0 |

### Dependency Summary

| Field | Type | Description |
|---|---|---|
| `resolved_dependencies` | int | Successfully resolved |
| `pending_dependencies` | int | Not yet resolved |
| `dependency_health` | str | "healthy" / "degraded" / "failed" |

### Governance Summary

| Field | Type | Description |
|---|---|---|
| `policy_version` | str | Policy schema version |
| `approval_status` | str | Current approval stage |
| `compliance_status` | str | Compliance check result |
| `security_status` | str | Security scan result |
| `risk_status` | str | Risk assessment result |
| `governance_notes` | List[str] | Free-form governance log |

### Audit & Misc

| Field | Type | Description |
|---|---|---|
| `validation_summary` | List[str] | Validation step results |
| `execution_summary` | List[str] | Key execution events |
| `audit_trail` | List[str] | Ordered audit entries |
| `metadata` | WorkflowSnapshotMetadata | Versioning and environment metadata |
| `extra` | Dict[str, Any] | Extension data — unvalidated |
| `snapshot_timestamp` | str | ISO-8601 UTC snapshot time |
| `created_at` | str | ISO-8601 UTC creation time |
| `updated_at` | str | ISO-8601 UTC last update time |

---

## WorkflowSnapshotMetadata Field Reference

| Field | Type | Prefix | Description |
|---|---|---|---|
| `metadata_id` | str | `wsmeta-` | Unique metadata identifier |
| `snapshot_version` | str | — | `"1.0"` |
| `framework_version` | str | — | `"c16-1.0"` |
| `build_version` | str | — | `"c16-m5"` |
| `environment` | str | — | `"production"` / `"staging"` / … |
| `correlation_id` | str | — | Cross-system correlation |
| `trace_id` | str | — | Distributed trace |
| `source_components` | Tuple[str] | — | Contributing M1–M4 modules |
| `tags` | Dict[str, str] | — | Free-form labels |
| `extra` | Dict[str, Any] | — | Extension data |
| `created_at` | str | — | ISO-8601 UTC |
