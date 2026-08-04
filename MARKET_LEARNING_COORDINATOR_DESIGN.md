# Market Learning Coordinator — Design Document

**Date:** 2026-08-04  
**Commit baseline:** `ebb8dc9` (O-002 DRE)  
**Status:** COMPLETE — 160/160 tests pass

---

## 1. Purpose

`MarketLearningCoordinator` (MLC) is the single orchestration layer for every
market-learning activity in IIOS. It replaces the ad-hoc AMLS call that
existed directly in `MasterOrchestrator._do_eod_learning()` and adds the
missing DRE production wiring, resolving observation **O-ADD-001** from
Platform Certification V2.

---

## 2. Responsibility Boundary

### MLC owns:
- EOD learning pipeline execution order
- AMLS invocation (market DNA learning)
- DRE invocation (trade-outcome reinforcement)
- IDR integrity check after writes
- PIG library refresh after IDR update
- Per-run telemetry collection
- Auditable run history on disk

### MLC does NOT own:
- DNA discovery, consensus, classification algorithms
- PMCI, CDS, or CA-PMCI scoring logic
- Strategy learning algorithms
- Trading decisions or risk rules
- Any IDR write except via DRE

---

## 3. Architecture

```
MasterOrchestrator._do_eod_learning()
        │
        │  trades = get_closed_trades()
        │
        ▼
MarketLearningCoordinator.run_learning_pipeline(trades)
        │
        ├── Stage 1: Strategy Learning    → LearningEngine.learn(trades)
        ├── Stage 2: AMLS Pipeline        → AMLS.run_pipeline()
        │                                    Stages: snapshot→classify→discover
        │                                             →consensus→IDR→PIG→report
        ├── Stage 3: DNA Reinforcement    → DRE.process_batch(items)
        │                                    trade outcomes → IDR confidence updates
        ├── Stage 4: IDR Refresh          → IDRRepository.statistics()
        ├── Stage 5: PIG Refresh          → PIGTradingAdapter.reload_library()
        │                                    (skipped if AMLS already refreshed)
        └── Stage 6: Learning Summary     → always runs
                │
                ▼
        LearningRun (returned to orchestrator)
```

---

## 4. Failure Policy

Every stage is wrapped in an independent `try / except Exception`. A failed
stage records its error in `LearningStage.error`, sets its status to `FAILED`,
and the pipeline continues to the next stage. The final health is:

| Condition | Health |
|---|---|
| All stages succeeded (or SKIPPED) | `HEALTHY` |
| One or more stages FAILED | `DEGRADED` |

`FAILED` health is reserved for future use. The pipeline always returns a
`LearningRun` — callers must never assume success.

---

## 5. O-ADD-001 Resolution

Observation O-ADD-001 stated:
> `DNAReinforcementEngine` exists (200/200 tests) but has no production call site
> in `_do_eod_learning()`.

**Resolution:** MLC's Stage 3 (DNA Reinforcement) calls `self._dre.process_batch(items)`.
MasterOrchestrator now instantiates `DRE` inside the MLC constructor block and
delegates all reinforcement to the coordinator. DRE is not directly wired into
`MasterOrchestrator` — MLC is the only owner.

---

## 6. DRE Integration Detail

MLC's `_run_dre_stage()` builds the DRE batch from closed trades and PIG results:

```
for trade in trades:
    pi = pig_results.get(trade.order_id)   # PlatformIntelligence at decision time
    if pi is None → skip (O-ADD-003: PMCI not yet persisted at execution)
    pmci = pi.pmci_result
    if pmci is None → skip
    items.append((trade, pmci, ca_pmci, cds))

dre.process_batch(items)
```

**O-ADD-003 note:** `pig_results` is currently passed as an empty dict
(`{}`) by the orchestrator because PMCI results are not yet persisted at
execution time. When O-ADD-003 is resolved (store PMCI per trade at decision
time), the DRE stage will process real reinforcements without any code changes
in MLC. The wiring is complete; only the data feed is missing.

---

## 7. PIG Refresh Deduplication

AMLS Stage 6 already calls `PIGTradingAdapter.reload_library()` when it runs.
MLC's Stage 5 (PIG Refresh) checks `tel.gateway_refresh` from the AMLS stage
and skips its own reload if AMLS already refreshed. This prevents a double
reload of the consensus library on the same EOD cycle.

---

## 8. History Persistence

- Path: `data/mls/mlc/history.json`
- Format: JSON array of `LearningRun.to_dict()` records
- Write: atomic (`tmp` → `os.replace`) after every pipeline run
- Cap: `MLCConfig.max_history_runs = 90` (oldest entries evicted)
- Thread-safe: `_lock` protects both in-memory list and disk write

---

## 9. Coordinator Readiness Update

The addition of MLC resolves all three `MarketLearningCoordinator` readiness
items from `COORDINATOR_READINESS.md`:

| Requirement | Was | Now |
|---|---|---|
| DNA persistence | ⚠️ | ✅ IDR Repository |
| Scheduler slot | ⚠️ | ✅ AMLS via MLC |
| Integration with trading | ❌ | ✅ PIG wired |

**MarketLearningCoordinator: IMPLEMENTED (was 9/10 ready → 10/10).**

---

## 10. Files Changed

| File | Change |
|---|---|
| `market_learning/mlc_models.py` | Existing — data models for MLC |
| `market_learning/mlc_config.py` | Existing — MLCConfig with stage toggles |
| `market_learning/market_learning_coordinator.py` | Existing — coordinator implementation |
| `market_learning/__init__.py` | Added MLC exports to package |
| `orchestrator/master_orchestrator.py` | `__init__`: replaced AMLS block with MLC block; `_do_eod_learning`: replaced AMLS call with `mlc.run_learning_pipeline(trades)` |
| `test_mlc.py` | 160/160 tests |
