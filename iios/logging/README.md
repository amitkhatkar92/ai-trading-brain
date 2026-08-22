# iios.logging

> **Status:** PLACEHOLDER -- Foundation certified. Wave 2 pending.

## Purpose
Logging service -- daily rotation, structured JSON, sensitive data redaction, context propagation with trace_id

## IIOS Role

| Field | Value |
|-------|-------|
| Layer | LOGGING |
| Wave | 2 |
| Owner | Platform |
| Architecture Reference | IIOS-CIS-001 INFRA-LOG-001 |
| Foundation | IIOS-FCR-001 |

## Responsibilities
Defined in **IIOS-CIS-001 INFRA-LOG-001**.

## Dependencies

- `iios.core`
- `iios.infrastructure.observability`

## Planned Submodules

- `iios.logging.iios_logger`
- `iios.logging.log_formatter`
- `iios.logging.log_rotator`
- `iios.logging.log_redactor`
- `iios.logging.structured_logger`

## Future Roadmap
See [`future_work.md`](future_work.md).

---
_IIOS-FCR-001 Foundation Certified_
