# Versioning Guide — C14 M5

## Version fields

| Field | Controlled by | Semantics |
|---|---|---|
| `snapshot_version` | Caller / auto | Identifies the schema revision used to build this snapshot |
| `knowledge_version` | Caller | Version of the underlying knowledge artifact set |
| `framework_version` | System constant | IIOS framework version (`FRAMEWORK_VERSION = "1.0.0"`) |
| `schema_version` | System constant | Snapshot dict schema (`SCHEMA_VERSION = "1.0"`) |
| `version_tag` | Caller / auto | DRAFT / RELEASE / STABLE / DEPRECATED |
| `content_hash` | Builder (SHA-256) | Integrity fingerprint of the snapshot content |

## SnapshotVersionTag usage

| Tag | When to use |
|---|---|
| `DRAFT` | Snapshot is under construction; not suitable for downstream consumption |
| `RELEASE` | Snapshot is complete and ready for integration testing |
| `STABLE` | Snapshot has passed validation and is approved for production use |
| `DEPRECATED` | Snapshot has been superseded by a newer version |

## SnapshotState lifecycle

```
BUILDING → VALIDATING → BUILT → PUBLISHED → EXPIRED → ARCHIVED
                          ↑
                     also valid end-state
```

## Content hash stability

The `content_hash` field is a SHA-256 digest of the canonical dict
(all fields except `content_hash` and `schema_version`).

For a given set of inputs, the hash is stable across:
- Python process restarts
- `to_dict()` → `from_dict()` round-trips
- JSON serialization / deserialization

**The hash changes** if any of the following change:
- Any summary field value
- snapshot_id, session IDs
- knowledge_version, framework_version, snapshot_version
- Timestamps

## History and deduplication

`KnowledgeSnapshotHistory` stores all versions of a session's snapshots in
insertion order (bounded by `max_history`).

To get the most recent snapshot for a session:
```python
latest = history.latest_for_session("sess-abc123")
```

To compare two versions of the same knowledge:
```python
versions = history.by_session("sess-abc123")
before   = versions[-2]
after    = versions[-1]
print(before.content_hash == after.content_hash)   # False if knowledge changed
```
