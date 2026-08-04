# Autonomous Market Learning Scheduler — Design Document

**Version:** 1.0  
**Date:** 2026-08-04  
**Scope:** MLS Phase 6  
**Status:** IMPLEMENTED — 125/125 tests passing  

---

## 1. Purpose

AMLS is the operational heartbeat of MLS.

Institutional knowledge shall refresh automatically after every trading day.
No manual execution required.

AMLS **orchestrates** — it never learns, discovers, or computes DNA.
Every computation is delegated to the existing MLS modules it coordinates.

---

## 2. Architecture

### 2.1 Position in the MLS Stack

```
MLS Phase 1  MarketObserver          ← data capture
MLS Phase 2  PopulationClassifier    ← classification
MLS Phase 3  DNADiscoveryEngine      ← discovery
MLS Phase 4  DNAConsensusEngine      ← consensus
R-013        IDRRepository           ← persistence
R-001        PlatformIntelligenceGateway ← query
─────────────────────────────────────────────────────
MLS Phase 6  AutonomousMarketLearningScheduler  ← THIS
```

AMLS sits above all MLS modules.  It does not extend any of them.

### 2.2 Reuse Policy

AMLS reuses **only** the following modules:
- `MarketObserver` (Phase 1)
- `PopulationClassifier` (Phase 2)
- `DNADiscoveryEngine` (Phase 3)
- `DNAConsensusEngine` (Phase 4)
- `IDRRepository` (R-013)
- `PlatformIntelligenceGateway` (R-001, via PIGTradingAdapter)
- `KnowledgeProvider` (ARS Phase 1.1, for downstream ARS queries)

No MLS logic is duplicated in AMLS.

---

## 3. Default Execution Flow

```
09:15 IST  ── Stage 1: snapshot_capture ──────────────────────────
             MarketObserver.capture(market_snapshot)
             OR load today's snapshot from disk (post-close fallback)
             Persists: data/mls/snapshots/MLS-SNAP-{YYYYMMDD}.json

15:35 IST  ── Stage 2: population_classify ────────────────────────
             PopulationClassifier.classify(dms)
             Persists: data/mls/classifications/{YYYY-MM-DD}.json

15:38 IST  ── Stage 3: dna_discover ───────────────────────────────
             DNADiscoveryEngine.discover(dms, classification)
             Persists: data/mls/dna/MLS-DNA-{YYYYMMDD}.json

15:41 IST  ── Stage 4: dna_consensus ──────────────────────────────
             DNAConsensusEngine.update(report)
             Persists: data/mls/consensus/library.json

15:43 IST  ── Stage 5: idr_sync ───────────────────────────────────
             IDRRepository.save(idr_record) for each ConsensusDNA
             Persists: data/mls/institutional_dna.db

15:44 IST  ── Stage 6: pig_refresh ────────────────────────────────
             PIGTradingAdapter.reload_library()  (if adapter present)
             Hot-reloads library.json without container restart

15:45 IST  ── Stage 7: generate_report ────────────────────────────
             PipelineTelemetry written
             Persists: data/mls/amls/reports/AMLS-{YYYYMMDD}.json
             ALWAYS runs — even if all earlier stages failed
```

All timings are advisory for scheduling.  `run_pipeline()` executes all
stages sequentially on demand, regardless of wall-clock time.

---

## 4. Execution Policy

### 4.1 Stage Independence

Every stage is wrapped by `_execute_stage()` which:
- Catches all exceptions
- Records failure in `PipelineFailure`
- Returns a `PipelineStage` with either SUCCESS or FAILED state
- Never propagates exceptions to the caller

Downstream stages check whether their required inputs exist:
- If the upstream stage failed, they produce a SKIPPED stage
- `generate_report` always runs, even when all upstream stages failed

### 4.2 Dependency Chain

```
snapshot_capture
  └─ success → population_classify
                └─ success → dna_discover
                              └─ success → dna_consensus
                                            └─ success → idr_sync
                                                          │
                                                          └─ pig_refresh  (independent)
                                                               │
                                                          generate_report  (always)
```

If `snapshot_capture` fails, stages 2–4 are SKIPPED.  Stages 6–7 still run.

### 4.3 Retry Policy

Default: `max_retries=2`, `retry_delay_s=10.0`

Retry uses exponential backoff: `delay = retry_delay_s × 2^(attempt-1)`

- Attempt 1: immediate
- Retry 1:   10s delay
- Retry 2:   20s delay
- After max_retries: stage marked FAILED

All retry parameters are configurable in `AMLSConfig`.

### 4.4 IDR Sync Behaviour

- Each `ConsensusDNA` record is converted to `InstitutionalDNA` and saved individually.
- Per-record failures are logged but do not abort the stage.
- If **all** records fail, the stage raises `RuntimeError` → FAILED.
- If some records succeed, the stage reports `written` count and succeeds.

---

## 5. Pipeline States

| State   | Meaning |
|---------|---------|
| WAITING | Scheduled but not yet started |
| RUNNING | Currently executing |
| SUCCESS | All 6 substantive stages completed successfully |
| FAILED  | All non-skipped stages failed, or critical failure |
| SKIPPED | Non-trading day, or upstream dependency unavailable |
| PARTIAL | Some stages succeeded, some failed |

State transitions:
```
WAITING → RUNNING → SUCCESS
                 → FAILED
                 → PARTIAL
         → SKIPPED  (calendar gate)
```

---

## 6. Calendar Logic

Trading day detection (in order):
1. `force=True` or `AMLSConfig.force_run=True` → bypass all checks
2. `skip_weekends=True` and weekday ≥ 5 (Sat/Sun) → SKIPPED
3. `date_str in AMLSConfig.holidays` → SKIPPED
4. Otherwise → trading day

Default holiday list matches `config.py NSE_HOLIDAYS` (FY2026-27).
Override by passing `AMLSConfig(holidays=[...])`.

---

## 7. Data Directories

| Directory | Contents | Written By |
|-----------|----------|------------|
| `data/mls/snapshots/` | `DailyMarketSnapshot` JSON files | Stage 1 |
| `data/mls/classifications/` | `ClassificationResult` JSON files | Stage 2 |
| `data/mls/dna/` | `DiscoveryReport` JSON files | Stage 3 |
| `data/mls/consensus/library.json` | `ConsensusLibrary` | Stage 4 |
| `data/mls/institutional_dna.db` | SQLite IDR | Stage 5 |
| `data/mls/amls/reports/` | `PipelineTelemetry` JSON files | Stage 7 |
| `data/mls/amls/history.json` | `MLSPipelineRun` list (90 days) | After every run |

---

## 8. Thread Safety

- `AutonomousMarketLearningScheduler` maintains a `threading.Lock` for all
  state mutations (`_current_run`, `_history`).
- History reads are thread-safe via the same lock.
- Stage functions are stateless functions — thread-safe by design.
- History file writes use `os.replace()` for atomic disk operations.

---

## 9. Observability

### Log markers

| Marker | Meaning |
|--------|---------|
| `[AMLS] Starting pipeline` | run_pipeline() begins |
| `[AMLS] Snapshot captured` | MarketObserver.capture() succeeded |
| `[AMLS] Snapshot loaded from disk` | Disk fallback used |
| `[AMLS] Classification done` | PopulationClassifier completed |
| `[AMLS] DNA discovery done` | DNADiscoveryEngine completed |
| `[AMLS] Consensus updated` | DNAConsensusEngine updated library |
| `[AMLS] IDR sync complete` | IDRRepository synced |
| `[AMLS] PIG adapter library reloaded` | Hot-reload complete |
| `[AMLS] Pipeline complete` | Full run summary |
| `[AMLS] Stage X FAILED` | Stage failed after all retries |

---

## 10. Orchestrator Integration Guide

### Option A: Single EOD call (recommended)

```python
# In MasterOrchestrator._do_eod_learning() at 16:45:
run = self.amls.run_pipeline(date=today)
log.info("[AMLS] EOD run: state=%s duration=%.0fms",
         run.state.value, run.total_duration_ms or 0)
```

When `run_pipeline()` is called without a `market_snapshot`, Stage 1
loads today's snapshot from disk (written at 09:15 by the orchestrator's
pre-market cycle).

### Option B: Split snapshot + EOD pipeline

```python
# At 09:15 in pre-market slot:
self.amls.run_stage("snapshot_capture",
                    context={"market_snapshot": snapshot})

# At 15:35 in EOD slot (loads snapshot from disk):
run = self.amls.run_pipeline()
```

### Suggested schedule additions

```python
# config.py SCHEDULE additions:
SCHEDULE = {
    ...existing entries...
    "amls_pipeline": "15:35",   # Post-close MLS pipeline
}
```

---

## 11. Final Questions — Answered

| Question | Answer |
|----------|--------|
| Can MLS execute without human intervention? | **YES** — AMLS runs `run_pipeline()` automatically post-close when integrated into the orchestrator scheduler. |
| Can every stage recover independently? | **YES** — Every stage is wrapped in `_execute_stage()`. A failed stage is recorded and the pipeline continues. `generate_report` always runs. |
| Can every execution be audited? | **YES** — Every run produces: `MLSPipelineRun` in history, `PipelineTelemetry` in `data/mls/amls/reports/`, structured log lines for each stage. |
| Can PIG always refresh after successful DNA updates? | **YES** — Stage 6 (`pig_refresh`) calls `PIGTradingAdapter.reload_library()`. It runs whenever Stage 4 produced a library. PIG uses the hot-reloaded library on the very next query call. |
