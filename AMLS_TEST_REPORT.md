# AMLS Test Report — MLS Phase 6

**Date:** 2026-08-04  
**Suite:** `test_amls.py`  
**Result:** **125 / 125 PASS**  

---

## Summary

| Category | Tests | Passed | Failed |
|---|---|---|---|
| T001–T010 PipelineState | 10 | 10 | 0 |
| T011–T020 PipelineStage | 10 | 10 | 0 |
| T021–T030 MLSPipelineRun | 10 | 10 | 0 |
| T031–T040 PipelineTelemetry | 10 | 10 | 0 |
| T041–T050 PipelineStatistics | 10 | 10 | 0 |
| T051–T060 AMLSConfig | 10 | 10 | 0 |
| T061–T075 Calendar / Trading Day | 15 | 15 | 0 |
| T076–T085 AMLS Init / Initial State | 10 | 10 | 0 |
| T086–T095 SKIPPED Runs | 10 | 10 | 0 |
| T096–T105 Successful Pipeline | 10 | 10 | 0 |
| T106–T115 Failure Recovery | 10 | 10 | 0 |
| T116–T125 Retry / Stats / Thread Safety | 10 | 10 | 0 |
| **TOTAL** | **125** | **125** | **0** |

---

## Test Coverage by Requirement

### Trading-day detection

| Test | Requirement | Status |
|---|---|---|
| T061 | Monday is a trading day | ✅ |
| T062 | Saturday is not a trading day | ✅ |
| T063 | Sunday is not a trading day | ✅ |
| T064 | NSE holiday is not a trading day | ✅ |
| T065 | Weekday without holiday is trading day | ✅ |
| T070 | Diwali Day 1 blocked | ✅ |
| T071 | Diwali Day 2 blocked | ✅ |
| T072 | Day after Diwali allowed (Thu) | ✅ |

### Weekend handling

| Test | Requirement | Status |
|---|---|---|
| T062 | Saturday never runs | ✅ |
| T063 | Sunday never runs | ✅ |
| T073 | Sunday run produces SKIPPED | ✅ |
| T086 | Saturday run state is SKIPPED | ✅ |
| T087 | Saturday run has single SKIPPED stage | ✅ |
| T088 | Stage inside Saturday run is SKIPPED | ✅ |

### Holiday handling

| Test | Requirement | Status |
|---|---|---|
| T064 | Holiday from config blocks run | ✅ |
| T068 | Custom holiday from AMLSConfig blocks run | ✅ |
| T074 | Holiday run state is SKIPPED | ✅ |
| T075 | Skipped holiday run recorded in history | ✅ |
| T089 | Holiday SKIPPED state | ✅ |
| T090 | Holiday run recorded in last_run() | ✅ |

### Force override

| Test | Requirement | Status |
|---|---|---|
| T066 | force_run=True ignores holiday | ✅ |
| T067 | force=True on Saturday bypasses calendar | ✅ |
| T092 | force=True on holiday day not SKIPPED | ✅ |

### Retry policy

| Test | Requirement | Status |
|---|---|---|
| T116 | max_retries=0 → no retry | ✅ |
| T117 | max_retries=2 → 2 retries tracked | ✅ |
| T118 | Retry succeeds on 2nd attempt | ✅ |
| T119 | retry_count=1 when success on 2nd attempt | ✅ |

### Failure recovery

| Test | Requirement | Status |
|---|---|---|
| T106 | Snapshot failure → FAILED or PARTIAL state | ✅ |
| T107 | Snapshot stage FAILED | ✅ |
| T108 | Classify SKIPPED after snapshot failure | ✅ |
| T109 | generate_report always runs | ✅ |
| T110 | Failure captured in telemetry | ✅ |
| T111 | Failure stage_name correct | ✅ |
| T112 | Classify failure → discover SKIPPED | ✅ |
| T113 | Discover failure → consensus SKIPPED | ✅ |
| T114 | IDR complete failure → IDR stage FAILED | ✅ |
| T115 | PIG refresh still runs after IDR failure | ✅ |

### Partial execution

| Test | Requirement | Status |
|---|---|---|
| T106 | Mixed stage results → FAILED or PARTIAL | ✅ |
| T109 | generate_report always produces telemetry | ✅ |
| T110 | Telemetry captures all failures | ✅ |

### Pipeline telemetry

| Test | Requirement | Status |
|---|---|---|
| T097 | Telemetry generated on every successful run | ✅ |
| T098 | telemetry.success True on SUCCESS | ✅ |
| T099 | knowledge_generated True when DNA found | ✅ |
| T100 | dna_updated True when library refreshed | ✅ |
| T101 | repository_writes count accurate | ✅ |
| T102 | gateway_refreshed True when adapter present | ✅ |
| T094 | Telemetry None for SKIPPED runs | ✅ |

### Repository refresh

| Test | Requirement | Status |
|---|---|---|
| T101 | IDR.save() called once per ConsensusDNA | ✅ |
| T114 | All-fail IDR sync → stage FAILED | ✅ |

### Gateway refresh

| Test | Requirement | Status |
|---|---|---|
| T102 | PIGTradingAdapter.reload_library() called | ✅ |
| T103 | reload_library() called exactly once | ✅ |
| T115 | PIG refresh independent of IDR failure | ✅ |

### Concurrent safety

| Test | Requirement | Status |
|---|---|---|
| T125 | Three concurrent AMLS instances all succeed | ✅ |

---

## Final Questions — Verified

| Question | Result | Evidence |
|---|---|---|
| Can MLS execute without human intervention? | **YES** | run_pipeline() fully automated; integrates into orchestrator scheduler |
| Can every stage recover independently? | **YES** | T106–T115: any stage failure caught; report always generated |
| Can every execution be audited? | **YES** | T097, T110: telemetry + history + report file per run |
| Can PIG always refresh after successful DNA updates? | **YES** | T102, T103: reload_library() called after Stage 4 success |

---

## Test Infrastructure

- **Framework:** Custom `TestResult` + `ok()` runner — no pytest dependency
- **Mocks:** `_StubObserver`, `_StubClassifier`, `_StubDiscovery`, `_StubConsensus`, `_StubIDR`, `_StubPIGAdapter` — all inline, no real MLS infrastructure required
- **Temp dirs:** Each test group uses `tempfile.mkdtemp()` for history file isolation
- **Retry speed:** `AMLSConfig(retry_delay_s=0.0)` eliminates sleep in tests
- **Calendar isolation:** `AMLSConfig(holidays=[])` ensures predictable trading-day detection
