# enterprise_ai_platform.integrations

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

- `enterprise_ai_platform.core`
- `enterprise_ai_platform.infrastructure.communication`
- `enterprise_ai_platform.security`
- `enterprise_ai_platform.config`

## Planned Submodules

- `enterprise_ai_platform.integrations.dhan_feed`
- `enterprise_ai_platform.integrations.dhan_broker`
- `enterprise_ai_platform.integrations.yahoo_feed`
- `enterprise_ai_platform.integrations.base_broker`
- `enterprise_ai_platform.integrations.feed_manager`
- `enterprise_ai_platform.integrations.global_symbol_map`

## Future Roadmap
See [`future_work.md`](future_work.md).

---
_IIOS-FCR-001 Foundation Certified_
