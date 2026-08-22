# iios.integrations

> **Status:** PLACEHOLDER -- Foundation certified. Wave 2 pending.

## Purpose
External integrations -- Dhan broker (data API + orders, 451 fallback), Yahoo Finance fallback, GLOBAL_SYMBOL_MAP

## IIOS Role

| Field | Value |
|-------|-------|
| Layer | INTEGRATIONS |
| Wave | 2 |
| Owner | Platform |
| Architecture Reference | IIOS-ARC-001 Layer 11, IIOS-RCS-001 |
| Foundation | IIOS-FCR-001 |

## Responsibilities
Defined in **IIOS-ARC-001 Layer 11, IIOS-RCS-001**.

## Dependencies

- `iios.core`
- `iios.infrastructure.communication`
- `iios.security`
- `iios.config`

## Planned Submodules

- `iios.integrations.dhan_feed`
- `iios.integrations.dhan_broker`
- `iios.integrations.yahoo_feed`
- `iios.integrations.base_broker`
- `iios.integrations.feed_manager`
- `iios.integrations.global_symbol_map`

## Future Roadmap
See [`future_work.md`](future_work.md).

---
_IIOS-FCR-001 Foundation Certified_
