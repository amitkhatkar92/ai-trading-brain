# iios.services

> **Status:** PLACEHOLDER -- Foundation certified. Wave 3 pending.

## Purpose
Background services -- Scheduler, 30s MarketMonitor, EOD workflow, pre-market initialization, continuous monitoring

## IIOS Role

| Field | Value |
|-------|-------|
| Layer | SERVICES |
| Wave | 3 |
| Owner | Platform |
| Architecture Reference | IIOS-ARC-001, IIOS-BSS-001 |
| Foundation | IIOS-FCR-001 |

## Responsibilities
Defined in **IIOS-ARC-001, IIOS-BSS-001**.

## Dependencies

- `iios.core`
- `iios.infrastructure.platform`
- `iios.market`
- `iios.infrastructure`

## Planned Submodules

- `iios.services.scheduler_service`
- `iios.services.market_monitor_service`
- `iios.services.eod_service`
- `iios.services.pre_market_service`
- `iios.services.background_runner`

## Future Roadmap
See [`future_work.md`](future_work.md).

---
_IIOS-FCR-001 Foundation Certified_
