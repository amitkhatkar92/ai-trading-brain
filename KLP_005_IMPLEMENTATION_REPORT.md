# KLP-005: Knowledge Evidence Integration & Data Integrity
## Implementation Report

**Date:** 2026-08-22  
**Commit:** TBD (deploy pending)  
**Tests:** 54/54 ✅ (new) + 107/107 KLP-004 regression ✅ + 150/150 KLP-002/003 ✅  
**Safety:** broker_calls=0, orders=0, PAPER_TRADING unchanged

---

## Executive Summary

KLP-005 closes 12 evidence-integrity and data-reliability gaps identified after
the KLP-004 (Knowledge Fusion) deployment. The key findings from VPS investigation:

1. `ct_decisions` is empty after 2026-08-05 because signals die at RiskControl
   (`risk_approved=0` every cycle since) — this is correct behaviour in a
   `range_market` regime where `RR < 2.0` for momentum signals. **Not a bug.**
2. All 470 KLP JSONL records have `obs_id`. **No issue.**
3. `regime_probability_history.json` had 2 extra bytes `}]` appended after
   500 valid records. **Repaired on VPS; prevented by atomic write going forward.**
4. `market_behavior.db` (1,560 market leader records) was not connected to the
   Knowledge Fusion pipeline. **Now integrated.**

---

## Changes By Part

### PART 1 — ct_decisions Observability Gap

**Root cause confirmed:** All signals after 2026-08-05 fail `MIN_RR_RATIO=2.0`
in RiskManagerAI. The `range_market` regime caps target potential, producing
RR < 2.0 across all momentum strategies. This is correct risk gate behaviour.

**Fix applied (additive, no interface change):**

| File | Change |
|---|---|
| `control_tower/telemetry_logger.py` | Added `risk_rejection_summary TEXT` column to `ct_cycles` schema |
| `control_tower/telemetry_logger.py` | `_init_db()` runs idempotent `ALTER TABLE` migration for existing DBs |
| `control_tower/telemetry_logger.py` | New `RISK_CHECK_FAILED` event handler stores rejection_summary JSON |
| `orchestrator/master_orchestrator.py` | `RISK_CHECK_FAILED` publish now includes `rejection_summary` dict with `rr/heat/other/total_in/total_out` counts |

**Query to diagnose rejection cause going forward:**
```sql
SELECT started_at, regime, risk_approved, risk_rejection_summary
FROM ct_cycles
WHERE risk_approved = 0
ORDER BY started_at DESC LIMIT 20;
```

### PART 2 — obs_id Integrity

**Finding:** All 470 VPS KLP records have `obs_id`. **No action required.**

### PART 3 — Regime History Repair + Atomic Write

**Root cause:** `regime_probability_history.json` had 2-byte corruption tail
`}]` at position 223419 (file size 223421).

**Fix applied:**

| File | Change |
|---|---|
| `market_intelligence/regime_probability_model.py` | New `_load_regime_history()` — reads file, auto-recovers from corrupt tail by scanning backwards for last valid `]` |
| `market_intelligence/regime_probability_model.py` | New `_atomic_write_regime_history()` — writes to `.tmp` file, calls `os.fsync`, then `os.replace` (rename) atomically |
| `market_intelligence/regime_probability_model.py` | `_append_history()` refactored to use both helpers |
| `scripts/repair_regime_history.py` | One-shot repair script — ran on VPS, recovered 500 records, wrote `.bak` |

**Repair result on VPS:** 500 records recovered, file verified valid JSON ✓

### PART 4 — market_behavior.db Adapter

**New file:** `opportunity_engine/knowledge_fusion/market_behavior_adapter.py`

Read-only adapter joining `market_leaders_daily + market_leader_outcomes` on
`leader_id`. Key features:
- `load_market_leader_records(db_path, limit)` → `List[MarketLeaderRecord]`
- `.NS`/`.BO` suffix stripped from symbol field
- `outcome_available=True` when `return_1d` or `return_5d` is not null
- `get_sector_leader_stats(sector, leader_type)` — aggregates win rate, return stats, outcome class histogram
- `get_symbol_leader_stats(symbol)` — per-symbol leader appearance statistics
- `MarketLeaderRecord` is a frozen dataclass (immutable, hashable)
- Returns `[]` when DB absent (graceful degradation)

**Data coverage:** 1,560 market leader records, 2026-06-19 to present

### PARTS 5-10 — Six New KFE Analysis Angles

`KnowledgeFusionEngine.analyse_record()` upgraded from **10 angles** to **16 angles**.

| Angle | Part | Description |
|---|---|---|
| STOCK | A (KLP-004) | Same symbol + direction outcome history |
| MARKET | B | Same regime context |
| SECTOR | C | Same sector + direction + regime |
| VOLATILITY | D | Same VIX bucket |
| DIRECTION | E | All records same direction |
| MAGNITUDE | F | Expected vs actual move distribution |
| TIME | G | T+N horizon statistics |
| RISK | H | Stop probability, adverse excursion |
| SELECTION | I | Selected vs rejected outcome comparison |
| COUNTERFACTUAL | J | What happened to rejected candidates |
| **LEADER_OUTCOME** | **K (KLP-005 PART 5)** | Market leader outcome patterns from market_behavior.db |
| **SOURCE_QUALITY** | **L (PART 6)** | Evidence quality weighting (outcome-linked vs context-only) |
| **RECENCY** | **M (PART 7)** | Exponential decay ESS (half-life=90d) |
| **REDUNDANCY** | **N (PART 8)** | Cross-source corroboration (distinct dates × agreement) |
| **CONTRADICTION** | **O (PART 9)** | Formalizes contradiction detection as confidence modifier |
| **OOS_VALIDATION** | **P (PART 10)** | Out-of-sample validation quality score |

**Source inventory:** `build_source_inventory()` now includes `MARKET_BEHAVIOR_DB`
(1,560 records, `is_outcome_linked=True`, availability determined at runtime).

### PART 11 — Tests

New file: `tests/test_klp_005.py`  
54 tests (T001–T054) covering all parts:
- T001–T008: PART 1 (ct_cycles column, migration, orchestrator payload)
- T009–T015: PART 3 (regime history repair, atomic write, corruption recovery)
- T016–T027: PART 4 (adapter load, NS stripping, outcome_available, stats)
- T028–T031: PART 5 (LEADER_OUTCOME angle)
- T032–T034: PART 6 (SOURCE_QUALITY angle)
- T035–T037: PART 7 (RECENCY angle)
- T038–T040: PART 8 (REDUNDANCY angle)
- T041–T043: PART 9 (CONTRADICTION angle)
- T044–T046: PART 10 (OOS_VALIDATION angle)
- T047–T054: Integration (16 angles present, safety contract, inventory)

### PART 12 — This Report

---

## Interface Stability Guarantee

All public interfaces unchanged:

| Interface | Status |
|---|---|
| `KnowledgeFusionEngine.analyse_record()` | ✅ Signature unchanged; returns 16 angles vs 10 (additive) |
| `KnowledgeFusionEngine.run_fusion()` | ✅ Returns same dict shape |
| `build_source_inventory()` | ✅ Returns longer list (additive) |
| `RegimeProbabilityModel._append_history()` | ✅ External signature unchanged |
| `TelemetryLogger` | ✅ No public interface changes |
| `MasterOrchestrator` | ✅ No interface changes |

---

## Regression Test Results

| Test Suite | Pass | Total | Status |
|---|---|---|---|
| test_klp_005.py (new) | 54 | 54 | ✅ |
| test_klp_004_knowledge_fusion.py | 107 | 107 | ✅ |
| test_klp_003_hbe.py | 76 | 76 | ✅ |
| test_klp_002_outcome_tracking.py | 74 | 74 | ✅ |
| test_final_knowledge_led_c2_001.py | 74 | 74 | ✅ |
| test_final_trading_architecture_shadow_001.py | 74 | 74 | ✅ |
| test_knowledge_parallel_layer.py | 74 | 74 | ✅ |
| test_mover_discovery_v3.py | 74 | 74 | ✅ |

---

## VPS Actions Completed

| Action | Status |
|---|---|
| regime_probability_history.json repaired (500 valid records) | ✅ Done |
| Backup saved as `.bak` | ✅ Done |
| File verified as valid JSON | ✅ Done |

---

## Known Limitations / Out of Scope for KLP-005

1. **rejection_audit.db absent on VPS** — `KnowledgeFusionEngine` gracefully handles absent DB. Backfilling from local copy is a separate task.
2. **range_market RR gate** — The `MIN_RR_RATIO=2.0` blocking all signals is documented. Tuning this threshold is out of scope per the change policy (protected module).
3. **LEADER_OUTCOME angle with empty DB** — Returns INSUFFICIENT gracefully when `market_behavior.db` absent. This is correct.
4. **REDUNDANCY angle** — Uses distinct trading dates as diversity proxy. When all corroborating records share one date (synthetic data), diversity=0. This is correct behaviour — same-date records are not independent.
