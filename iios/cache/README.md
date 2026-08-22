# iios.cache

> **Status:** PLACEHOLDER -- Foundation certified. Wave 2 pending.

## Purpose
Cache service -- in-memory TTL/LRU cache, GlobalDataAI 5-min cache, quote cache 10s TTL

## IIOS Role

| Field | Value |
|-------|-------|
| Layer | CACHE |
| Wave | 2 |
| Owner | Platform |
| Architecture Reference | IIOS-CIS-001 INFRA-CAC-001 |
| Foundation | IIOS-FCR-001 |

## Responsibilities
Defined in **IIOS-CIS-001 INFRA-CAC-001**.

## Dependencies

- `iios.core`
- `iios.infrastructure.communication`

## Planned Submodules

- `iios.cache.cache_service`
- `iios.cache.ttl_cache`
- `iios.cache.lru_cache`
- `iios.cache.cache_manager`
- `iios.cache.cache_stats`

## Future Roadmap
See [`future_work.md`](future_work.md).

---
_IIOS-FCR-001 Foundation Certified_
