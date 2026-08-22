# iios.storage

> **Status:** PLACEHOLDER -- Foundation certified. Wave 2 pending.

## Purpose
Storage service -- SQLite adapter, WAL mode, transaction management, data retention, backup

## IIOS Role

| Field | Value |
|-------|-------|
| Layer | STORAGE |
| Wave | 2 |
| Owner | Platform |
| Architecture Reference | IIOS-CIS-001 INFRA-STG-001 |
| Foundation | IIOS-FCR-001 |

## Responsibilities
Defined in **IIOS-CIS-001 INFRA-STG-001**.

## Dependencies

- `iios.core`
- `iios.database`
- `iios.infrastructure`

## Planned Submodules

- `iios.storage.storage_service`
- `iios.storage.sqlite_storage`
- `iios.storage.storage_schema`
- `iios.storage.data_retention`
- `iios.storage.backup_service`

## Future Roadmap
See [`future_work.md`](future_work.md).

---
_IIOS-FCR-001 Foundation Certified_
