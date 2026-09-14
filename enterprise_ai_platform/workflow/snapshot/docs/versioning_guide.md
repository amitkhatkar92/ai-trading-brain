# Versioning Guide

## Snapshot Version

Every `WorkflowSnapshot` carries two version strings:

| Field | Value | Location |
|---|---|---|
| `snapshot_version` | `"1.0"` | `WorkflowSnapshot.snapshot_version` |
| `framework_version` | `"c16-1.0"` | `WorkflowSnapshotMetadata.framework_version` |
| `build_version` | `"c16-m5"` | `WorkflowSnapshotMetadata.build_version` |

These are set automatically by the builder and metadata factory.  Do not
override them unless you are introducing a planned schema change.

---

## Schema Evolution Policy

### Backwards-Compatible Changes (minor bump: 1.0 → 1.1)

- Adding new **optional** fields to `WorkflowSnapshot` with sensible defaults
- Adding new enum values to `SnapshotStatus`, `SnapshotEventType`, etc.
- Adding new properties to `WorkflowSnapshot`
- New factory convenience methods in `WorkflowSnapshotFactory`

### Breaking Changes (major bump: 1.0 → 2.0)

- Renaming or removing fields from `WorkflowSnapshot`
- Changing the type of existing fields
- Removing enum values
- Changing the ID prefix constants
- Changing `to_dict()` key names

---

## ID Prefix Registry

| Object | Prefix | Example |
|---|---|---|
| `WorkflowSnapshot` | `wsnap-` | `wsnap-a3f9c12e8b4d` |
| `WorkflowSnapshotBundle` | `wbndl-` | `wbndl-c84f1a9d3e2b` |
| `WorkflowSnapshotEvent` | `wsevt-` | `wsevt-7d4e2a1c` |
| `WorkflowSnapshotMetadata` | `wsmeta-` | `wsmeta-1b9e7c3d5f2a` |

Prefixes are defined in `constants.py` as `PREFIX_*` constants.  Always use
the constants — never hardcode the prefix strings in application code.

---

## Version Constants (constants.py)

```python
VERSION           = "1.0.0"      # Package semantic version
BUILD_VERSION     = "c16-m5"     # Module build identifier
SNAPSHOT_VERSION  = "1.0"        # Schema version on every snapshot
FRAMEWORK_VERSION = "c16-1.0"    # IIOS framework version
```

---

## Compatibility Checklist

When adding a new field to `WorkflowSnapshot`:

1. Give it a default value (`field(default="")` or `field(default=0)`)
2. Add it to `to_dict()` in `workflow_snapshot.py`
3. Update `snapshot_schema_guide.md` with the field reference
4. Add at least one test in `test_workflow_snapshot_m5.py`
5. Consider whether `WorkflowSnapshotValidation` needs a new check
6. Update `SNAPSHOT_VERSION` if the change is breaking
