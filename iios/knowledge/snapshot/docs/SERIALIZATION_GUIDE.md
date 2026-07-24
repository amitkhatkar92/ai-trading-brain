# Serialization Guide — C14 M5

## to_dict / from_dict

All snapshot objects support lossless dict round-trips:

```python
d        = snapshot.to_dict()
snapshot2 = KnowledgeSnapshot.from_dict(d)
assert snapshot.content_hash == snapshot2.content_hash
```

All sub-dataclasses (`KnowledgeSummary`, `GraphSummary`, etc.) also support
`to_dict()` and `from_dict()`.

## JSON

```python
json_str  = snapshot.to_json(indent=2)
snapshot2 = KnowledgeSnapshot.from_json(json_str)
```

JSON is UTF-8 encoded and uses Python's built-in `json` module.

## Store serialization

```python
from iios.knowledge.snapshot import KnowledgeSnapshotStore

store = KnowledgeSnapshotStore()
store.put(snapshot)

# Export all to list of dicts (e.g. for database persistence)
records = store.export_all()

# Import from dicts (e.g. after loading from database)
count = store.import_all(records)
```

## Bundle serialization

```python
# Compact (no nested snapshot data)
d_compact = bundle.to_dict()

# Full (includes all snapshot dicts)
d_full = bundle.to_full_dict()
```

## Content hash verification

Always verify integrity after deserialization:

```python
snapshot2 = KnowledgeSnapshot.from_dict(d)
assert snapshot2.verify_integrity(), "Snapshot integrity check failed"
```

`verify_integrity()` recomputes the SHA-256 hash of the canonical content
and compares it to the stored `content_hash`.

## Tuple fields

All tuple fields are serialized as JSON arrays and restored as tuples
by `from_dict()`.  This preserves the frozen dataclass contract.

## Nested dict fields

`SnapshotAudit.validation_summary` and `audit_trail` are serialized
as-is (dict and list respectively).  They must be JSON-serializable.
