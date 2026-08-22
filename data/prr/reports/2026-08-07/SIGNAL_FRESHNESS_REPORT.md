# SIGNAL_FRESHNESS_REPORT — 2026-08-07
_Generated: 2026-08-07 15:22:19 | PRR-001 Phase 3_

## Summary

| Status | Count | % |
|--------|-------|---|
| FRESH (0–5 trading days) | 0 | 0.0% |
| WEAKENING (6–15 days) | 0 | 0.0% |
| EXPIRED (15+ days) | 0 | 0.0% |
| **Blocked from execution** | **0** | |

Total signals checked: **0**
Oldest blocked: **0.0 trading days**

## Governance Rule

| Age | Status | Action |
|-----|--------|--------|
| 0–5 trading days | FRESH | Execute normally |
| 6–15 trading days | WEAKENING | Execute with warning; entry thesis may have changed |
| >15 trading days | EXPIRED | **BLOCKED** — never executed |

## Implementation

Signal freshness is enforced in `execution_engine/order_manager.py` via
`is_signal_expired()` from `production_readiness.ph3_signal_freshness`.
