# iios.database

> **Status:** PLACEHOLDER -- Foundation certified. Wave 2 pending.

## Purpose
Database abstraction -- SQLite query builder, connection pool, parameterized queries (OWASP-compliant, no SQL injection)

## IIOS Role

| Field | Value |
|-------|-------|
| Layer | DATABASE |
| Wave | 2 |
| Owner | Platform |
| Architecture Reference | IIOS-CIS-001 INFRA-STG-001 |
| Foundation | IIOS-FCR-001 |

## Responsibilities
Defined in **IIOS-CIS-001 INFRA-STG-001**.

## Dependencies

- `iios.core`
- `iios.config`

## Planned Submodules

- `iios.database.sqlite_adapter`
- `iios.database.query_builder`
- `iios.database.connection_pool`
- `iios.database.migration_runner`
- `iios.database.schema_validator`

## Future Roadmap
See [`future_work.md`](future_work.md).

---
_IIOS-FCR-001 Foundation Certified_
