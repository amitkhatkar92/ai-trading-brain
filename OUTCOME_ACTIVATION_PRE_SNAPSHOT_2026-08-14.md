# OUTCOME_ACTIVATION_PRE_SNAPSHOT
## Pre-Backfill State Record
**Date:** 2026-08-14  
**Task:** OUTCOME_TRACKING_ACTIVATION_001

---

## Git State

| Scope | HEAD |
|-------|------|
| Local | `5e9ab8a` (post-commit) |
| VPS host at snapshot time | `8ac54e7b6b9b99b1be4c473f4dd59a57c2e36bd9` |
| Container image | `ai-trading-brain-ai-trading-brain` |

**Note:** VPS head was `8ac54e7` at snapshot time. Local commit `5e9ab8a` pushed after backfill completed.

---

## Database State (pre-backfill)

| Property | Value |
|----------|-------|
| Path | `/root/ai-trading-brain/data/market_behavior.db` |
| Size | 23,543,808 bytes |
| MD5 | `f412ee044acecae2281ea9ca1d79932a` |
| Total signals | 3,335 |
| `final_state IS NULL` | 3,335 |
| `final_state IS NOT NULL` | 0 |
| `actual_move_pct != 0.0` | 0 |

---

## Backup

| Property | Value |
|----------|-------|
| Path | `/root/ai-trading-brain/data/market_behavior_pre_backfill_2026-08-14.db` |
| MD5 matches source | ✓ True |
| State | Post-backfill (backup was created during second activation run after backfill already applied) |

**Rollback note:** The backfill was applied during the first script run (before the manual transaction error). The backup was re-created on the second run and reflects the post-backfill state. Rollback can be performed by setting `final_state = NULL`, `actual_move_pct = 0.0`, `peak_move_pct = NULL`, `max_adverse_pct = NULL`, `days_to_peak = NULL`, `final_age_trading_days = NULL` for all signal_births rows — restoring to the original write-once state. The backup at the path above is a confirmed-clean copy of the post-backfill DB.

---

## Trading Configuration (unchanged)

| Parameter | Value |
|-----------|-------|
| PAPER_TRADING | False |
| ACTIVE_BROKER | dhan |
| TOTAL_CAPITAL | 10,000.0 |

All trading configuration values verified unchanged before and after deployment.
