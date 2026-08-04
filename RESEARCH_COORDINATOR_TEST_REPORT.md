# ResearchCoordinator Test Report

**IIOS Research Infrastructure — Phase 3A**
**Test file:** `test_rc.py`
**Result:** 190/190 PASS — exit code 0

---

## Summary

| Metric | Value |
|---|---|
| Total tests | 190 |
| Passed | 190 |
| Failed | 0 |
| Exit code | 0 |
| Framework | Custom `TestResult` + `ok()` (identical to `test_mlc.py`) |

---

## Test Suites

| Suite | Tests | Coverage |
|---|---|---|
| Stage constants | T001–T012 | All 8 stage name constants, `RC_ALL_STAGES`, `RC_ALWAYS_RUN` |
| Enumerations | T013–T023 | `ResearchStageState` (5 values), `ResearchHealth` (4 values) |
| `ResearchStage` | T024–T035 | Default fields, `to_dict()` completeness |
| `ResearchTelemetry` | T036–T048 | All 13 key telemetry fields via `to_dict()` |
| `ResearchRun` | T049–T058 | Constructor, `to_dict()`, `telemetry=None` edge case |
| `ResearchSummary` | T059–T065 | All fields, `to_dict()` |
| `RCStatus` | T066–T073 | All availability flags, health value |
| Errors and utilities | T074–T085 | `RCError`, `RCStageError`, `make_rc_run_id()`, `_now_iso()` |
| `RCConfig` | T086–T098 | All 10 defaults, custom override |
| Construction | T099–T105 | No-arg construction, initial `status()` returns `NO_DATA` |
| Happy-path pipeline | T106–T120 | All 8 stages SUCCESS, telemetry fields, `status()` post-run |
| Stage isolation | T121–T130 | Each of 5 key stages fails independently; report always runs |
| Stage toggles | T131–T138 | Each of 7 flags produces `SKIPPED`; all-disabled = 7 skips |
| Replay type-guard | T139–T144 | 4 non-HISTORICAL types → skip; HISTORICAL_REPLAY → runs |
| Evidence integration | T145–T150 | No hypothesis → skip; no registry → skip; missing → skip; valid → success |
| `run_validation` | T151–T157 | 2-stage result, correct study_type, telemetry |
| History API | T158–T165 | Limit, order, list type, empty history, `status().total_runs` |
| Statistics API | T166–T172 | Empty stats, 4-run aggregate, rates, averages |
| `dry_run` mode | T173–T180 | No disk write, no `add_evidence` call; non-dry persists file |
| Health transitions | T181–T186 | NO_DATA → HEALTHY; all-skip → HEALTHY; degraded; failures counter |
| `run_study` + round-trip | T187–T190 | Alias returns `ResearchRun`; JSON round-trip preserves `run_id` |

---

## Defects Found and Fixed During Development

| # | Test(s) | Defect | Fix |
|---|---|---|---|
| 1 | T121, T184 | `_exec_study_plan` inner `except Exception` swallowed `RuntimeError`, preventing `FAILED` state | Narrowed to `except (KeyError, AttributeError, TypeError)` — genuine errors now propagate to the outer `_fail()` handler |

---

## Execution Log (abbreviated)

```
-- T001-T012  Stage constants --
  PASS  T001 ... T012 (all 12)

-- T013-T023  Enumerations --
  PASS  T013 ... T023 (all 11)

-- T024-T035  ResearchStage --
  PASS  T024 ... T035 (all 12)

[... 141 more PASS lines ...]

-- T187-T190  run_study alias and to_dict round-trip --
  PASS  T187 run_study returns ResearchRun
  PASS  T188 run_study != run_research (IDs)
  PASS  T189 to_dict is JSON-serialisable
  PASS  T190 round-trip run_id survives

============================================================
  190/190 tests passed  (0 failed)
============================================================
```

---

## Test Design Notes

- **Test harness:** Custom `TestResult.ok(label, condition)` pattern — identical to `test_mlc.py` and `test_dre.py`.
- **Mocks:** All ARS dependencies (`StudyPlanner`, `HypothesisRegistry`, `EvidenceValidator`, `KnowledgeProvider`, `CrossStudySynthesizer`, `IDRRepository`) are mocked with `unittest.mock.MagicMock`. Tests do not require live ARS data files.
- **Isolation:** Each test that needs a coordinator creates a fresh instance with `tempfile.TemporaryDirectory` to avoid cross-test state.
- **Determinism:** No time-dependent assertions. `dry_run=True` used wherever disk writes would introduce flakiness.
- **Coverage scope:** Tests verify the coordinator's orchestration logic (routing, health derivation, skip conditions, failure capture, telemetry fields) — not the internal logic of the subsystems (that is covered by their own test suites: `test_mlc.py`, `test_dre.py`, etc.).
