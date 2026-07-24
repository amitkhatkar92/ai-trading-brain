# Snapshot Schema Guide

## Overview

The `IntegrationSnapshot` is a flat, fully-serializable frozen dataclass.
All summary objects within it are also frozen dataclasses.

## Top-level schema

```json
{
  "snapshot_id":              "snap-<12-hex>",
  "integration_session_id":  "<string>",
  "integration_workflow_id": "<string>",
  "enterprise_session_id":   "<string>",
  "integration_version":     "1.0.0",
  "framework_version":       "1.0.0",
  "snapshot_version":        "1.0.0",
  "integration_scope":       "enterprise",
  "integration_type":        "full",
  "lifecycle_state":         "active",
  "governance_state":        "compliant",
  "connectivity_state":      "connected",
  "status":                  "published",
  "snapshot_timestamp":      "2026-07-24T00:00:00+00:00",
  "created_at":              "2026-07-24T00:00:00+00:00",
  "updated_at":              "2026-07-24T00:00:00+00:00",
  "connectivity_summary":    { ... },
  "connector_summary":       { ... },
  "adapter_summary":         { ... },
  "protocol_summary":        { ... },
  "service_summary":         { ... },
  "security_summary":        { ... },
  "audit_summary":           { ... },
  "statistics_summary":      { ... },
  "metadata":                { ... }
}
```

## Enum values

### SnapshotStatus
`draft` | `published` | `archived` | `expired`

### SnapshotScope
`component` | `subsystem` | `enterprise` | `global` | `internal`

### SnapshotIntegrationType
`rest_api` | `messaging` | `streaming` | `websocket` | `database` | `file` | `event_stream` | `enterprise` | `full`

### LifecycleState
`created` | `initializing` | `active` | `paused` | `resuming` | `completed` | `failed` | `archived` | `unknown`

### GovernanceState
`compliant` | `non_compliant` | `under_review` | `exempt` | `pending` | `unknown`

### ConnectivityState
`connected` | `degraded` | `disconnected` | `partial` | `unknown`

## Summary schemas

### connectivity_summary
```json
{
  "active_integrations":        0,
  "registered_connectors":      0,
  "registered_adapters":        0,
  "protocols_enabled":          0,
  "connection_pool_status":     "unknown",
  "authentication_status":      "unknown",
  "authorization_status":       "unknown",
  "security_status":            "unknown",
  "compliance_status":          "unknown",
  "overall_integration_health": "unknown"
}
```

### connector_summary
```json
{
  "connector_count":        0,
  "connector_types":        [],
  "connector_availability": 0.0,
  "connector_health":       "unknown",
  "connector_versions":     {}
}
```

### adapter_summary
```json
{
  "adapter_count":       0,
  "adapter_types":       [],
  "adapter_versions":    {},
  "compatibility_status": "unknown"
}
```

### protocol_summary
```json
{
  "rest":                "unknown",
  "graphql":             "unknown",
  "grpc":                "unknown",
  "websocket":           "unknown",
  "kafka":               "unknown",
  "rabbitmq":            "unknown",
  "redis_streams":       "unknown",
  "database_connectors": "unknown",
  "webhook_services":    "unknown",
  "file_transfer":       "unknown",
  "protocol_health":     "unknown"
}
```

### service_summary
```json
{
  "requests_processed": 0,
  "responses_received": 0,
  "messages_published": 0,
  "messages_consumed":  0,
  "events_processed":   0,
  "retries":            0,
  "failures":           0,
  "average_latency_ms": 0.0,
  "throughput_rps":     0.0
}
```

### security_summary
```json
{
  "authentication_providers": 0,
  "authorization_providers":  0,
  "certificates":             0,
  "secrets":                  0,
  "encryption_status":        "unknown",
  "credential_health":        "unknown"
}
```

### audit_summary
```json
{
  "governance_version":         "1.0.0",
  "connector_registry_version": "1.0.0",
  "protocol_registry_version":  "1.0.0",
  "validation_summary":         "not validated",
  "audit_trail":                []
}
```

### statistics_summary
```json
{
  "processing_duration_ms": 0.0,
  "snapshot_size_bytes":    0,
  "connector_count":        0,
  "adapter_count":          0,
  "protocol_count":         0,
  "connection_count":       0
}
```

### metadata
```json
{
  "environment":       "production",
  "framework_version": "1.0.0",
  "build_version":     "1.0.0",
  "source_components": [],
  "correlation_ids":   [],
  "trace_ids":         [],
  "tags":              {},
  "generated_at":      "2026-07-24T00:00:00+00:00"
}
```

## Serialization

```python
# To dict (JSON-safe)
d = snapshot.to_dict()

# From dict
snapshot = IntegrationSnapshot.from_dict(d)

# Via factory (with error handling)
from iios.integration.snapshot import IntegrationSnapshotFactory
snapshot = IntegrationSnapshotFactory.from_dict(d)
```
