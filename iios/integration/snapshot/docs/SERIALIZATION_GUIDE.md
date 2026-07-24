# Serialization Guide

## Overview

`IntegrationSnapshot` and all its summary objects implement `to_dict()` and
`from_dict()` for full round-trip serialization to JSON-safe Python dicts.

## to_dict()

Returns a JSON-safe `Dict[str, Any]` with all enum values serialized to their
string `.value`, tuples serialized to lists, and nested objects recursively
serialized.

```python
import json
from iios.integration.snapshot import IntegrationSnapshotFactory

snapshot = IntegrationSnapshotFactory.create_enterprise_snapshot(
    integration_session_id  = "sess-001",
    integration_workflow_id = "wf-001",
    enterprise_session_id   = "ent-001",
)

d    = snapshot.to_dict()
json_str = json.dumps(d, indent=2)
```

## from_dict()

Reconstructs an `IntegrationSnapshot` from a previously serialized dict.  All
string values are converted back to their enum types.  Missing optional fields
receive safe defaults.

```python
# Direct class method
snap2 = IntegrationSnapshot.from_dict(d)

# Via factory (adds error handling)
from iios.integration.snapshot import IntegrationSnapshotFactory
snap3 = IntegrationSnapshotFactory.from_dict(d)
```

`IntegrationSnapshotFactory.from_dict()` raises `SnapshotSerializationError`
on invalid input.

## Individual summary objects

Each summary object also has `to_dict()` and can be constructed directly:

```python
from iios.integration.snapshot import ConnectivitySummary

cs = ConnectivitySummary(
    active_integrations        = 5,
    registered_connectors      = 3,
    registered_adapters        = 4,
    protocols_enabled          = 7,
    connection_pool_status     = "healthy",
    authentication_status      = "active",
    authorization_status       = "active",
    security_status            = "secure",
    compliance_status          = "compliant",
    overall_integration_health = "healthy",
)
d = cs.to_dict()
```

## SnapshotMetadata serialization

```python
from iios.integration.snapshot import SnapshotMetadata

meta = SnapshotMetadata.create(
    environment       = "production",
    source_components = ["integration_services_engine"],
    correlation_ids   = ["corr-001"],
    tags              = {"team": "platform", "region": "ap-south-1"},
)

d     = meta.to_dict()
meta2 = SnapshotMetadata.from_dict(d)
```

## Bundle serialization

`IntegrationSnapshotBundle` is mutable but also exposes `to_dict()` which
serializes the entire bundle including all contained snapshots:

```python
from iios.integration.snapshot import IntegrationSnapshotBundle

bundle = IntegrationSnapshotBundle("session-snapshots", max_size=20)
bundle.add(snap1)
bundle.add(snap2)

d = bundle.to_dict()
# d["snapshots"] is a list of snapshot dicts
```

## Handling unknown enum values

When deserializing snapshots from external sources or older schema versions,
unknown enum values fall back to `UNKNOWN` (where defined) or raise
`ValueError`.  Production consumers should wrap `from_dict()` in a
try/except block:

```python
from iios.integration.snapshot import (
    IntegrationSnapshotFactory,
    SnapshotSerializationError,
)

try:
    snap = IntegrationSnapshotFactory.from_dict(raw_dict)
except SnapshotSerializationError as exc:
    logger.error(f"Failed to deserialize snapshot: {exc}")
```

## Thread safety

`to_dict()` and `from_dict()` are pure functions operating on immutable
objects.  They are safe to call concurrently from any thread without
additional synchronization.
