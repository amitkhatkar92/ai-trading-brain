# HYPOTHESIS REGISTRY TEST REPORT
## ARS Phase 1.2 — Scientific Hypothesis Registry

**Date:** 2026-08-03 13:02:09  
**Total tests:** 40  
**Passed:** 40  
**Failed:** 0  
**Pass rate:** 100%  

---

## Test Results

| Test | Status | Duration (ms) | Detail |
|---|---|---|---|
| T-01: Instantiation | ✅ PASS | 0.1 | instantiated with empty store |
| T-02: create_hypothesis() — valid study evidence | ✅ PASS | 6.3 | created H2026-08-001 |
| T-03: Hypothesis ID format and uniqueness | ✅ PASS | 6.0 | IDs: H2026-08-001, H2026-08-002 |
| T-04: Full lifecycle PROPOSED → CONFIRMED | ✅ PASS | 13.3 | Full lifecycle complete: 8 events |
| T-05: Rejection lifecycle path | ✅ PASS | 11.2 | rejection path: PROPOSED → UNDER_REVIEW → REJECTED → ARCHIVED |
| T-06: Revival path REJECTED → PROPOSED | ✅ PASS | 7.7 | revival path: REJECTED → PROPOSED |
| T-07: Invalid transitions raise InvalidTransitionError | ✅ PASS | 3.6 | 3 invalid transitions correctly blocked |
| T-08: ARCHIVED is terminal | ✅ PASS | 7.7 | ARCHIVED terminal status confirmed |
| T-09: All statuses covered in transition table | ✅ PASS | 0.0 | all 9 statuses covered in transition table |
| T-10: add_evidence() — valid FINDING reference | ✅ PASS | 7.1 | FINDING evidence re001a.platform_snapshot attached |
| T-11: add_evidence() — valid EDGE reference | ✅ PASS | 19.5 | EDGE evidence EDG_COMPOS_86_EE0001 attached |
| T-12: Invalid evidence raises InvalidEvidenceError | ✅ PASS | 3.3 | invalid STUDY reference correctly rejected |
| T-13: EXTERNAL evidence bypasses validation | ✅ PASS | 5.3 | EXTERNAL evidence accepted without validation |
| T-14: Duplicate evidence_id is idempotent | ✅ PASS | 2.9 | duplicate evidence_id skipped (idempotent) |
| T-15: add_note() appends timestamped notes | ✅ PASS | 7.1 | 2 notes appended |
| T-16: Empty note raises RegistryValidationError | ✅ PASS | 3.1 | empty note correctly rejected |
| T-17: get() returns None for unknown ID | ✅ PASS | 0.1 | get(unknown) → None |
| T-18: get_or_raise() raises HypothesisNotFoundError | ✅ PASS | 0.1 | get_or_raise(unknown) → HypothesisNotFoundError |
| T-19: list_all() ordered by creation date | ✅ PASS | 6.3 | 3 hypotheses in creation order |
| T-20: list_by_status() filter | ✅ PASS | 6.3 | PROPOSED=1, UNDER_REVIEW=1 |
| T-21: list_by_priority() filter | ✅ PASS | 5.4 | HIGH=1, LOW=1 |
| T-22: list_open() excludes terminal states | ✅ PASS | 9.4 | 1 open, 1 archived correctly excluded |
| T-23: list_confirmed() and list_rejected() | ✅ PASS | 18.4 | 1 confirmed, 1 rejected |
| T-24: list_by_study() filter | ✅ PASS | 3.5 | 1 hypotheses linked to study002a |
| T-25: search() keyword matching | ✅ PASS | 4.7 | 'atr'=1, 'momentum'=1 |
| T-26: search() is case-insensitive | ✅ PASS | 2.8 | case-insensitive search confirmed |
| T-27: statistics() returns complete metrics | ✅ PASS | 7.3 | total=2, open=2 |
| T-28: Decision history is append-only | ✅ PASS | 6.4 | 3 decision events recorded |
| T-29: Persistence — save/reload round-trip | ✅ PASS | 6.4 | save → reload round-trip verified |
| T-30: Backup file created before overwrite | ✅ PASS | 5.0 | backup created at registry.json.bak |
| T-31: Concurrent access — thread-safety | ✅ PASS | 33.8 | 10 concurrent creates, 0 errors, 10 unique IDs |
| T-32: Empty title raises RegistryValidationError | ✅ PASS | 0.1 | empty title rejected |
| T-33: Out-of-range confidence raises RegistryValidationError | ✅ PASS | 0.1 | all out-of-range confidence values rejected |
| T-34: set_validation_result requires RUNNING status | ✅ PASS | 3.2 | set_validation_result on non-RUNNING correctly rejected |
| T-35: get_evidence_chain() returns full chain | ✅ PASS | 18.9 | evidence chain: ['study002a', 'EDG_COMPOS_86_EE0001'] |
| T-36: get_decision_history() returns isolated copy | ✅ PASS | 3.3 | decision history copy is isolated from original |
| T-37: update_confidence() records event | ✅ PASS | 4.9 | confidence updated and event recorded |
| T-38: Duplicate title — warning only, not error | ✅ PASS | 4.9 | duplicate title allowed with warning (not an error) |
| T-39: Registry does not modify KP stores | ✅ PASS | 5.0 | KnowledgeProvider stores unchanged |
| T-40: archive() convenience method | ✅ PASS | 7.9 | archive() convenience method works |

---

## Failures

*No failures.*

---

## Coverage Summary

| Test Category | Tests |
|---|---|
| Lifecycle — full happy path | T-04 |
| Lifecycle — rejection path | T-05 |
| Lifecycle — revival path | T-06 |
| Invalid transitions | T-07, T-08 |
| Transition table completeness | T-09 |
| Evidence — valid FINDING | T-10 |
| Evidence — valid EDGE | T-11 |
| Evidence — invalid reference | T-12 |
| Evidence — EXTERNAL bypass | T-13 |
| Evidence — idempotent add | T-14 |
| Notes — append-only | T-15, T-16 |
| get() / get_or_raise() | T-17, T-18 |
| list_all() order | T-19 |
| list_by_status() | T-20 |
| list_by_priority() | T-21 |
| list_open() | T-22 |
| list_confirmed() / list_rejected() | T-23 |
| list_by_study() | T-24 |
| search() | T-25, T-26 |
| statistics() | T-27 |
| Decision history append-only | T-28 |
| Persistence (save/reload) | T-29 |
| Backup file creation | T-30 |
| Concurrent access | T-31 |
| Validation — empty fields | T-32 |
| Validation — confidence range | T-33 |
| Validation — set_validation_result | T-34 |
| get_evidence_chain() | T-35 |
| get_decision_history() isolation | T-36 |
| update_confidence() | T-37 |
| Duplicate title warning | T-38 |
| Read-only KP constraint | T-39 |
| archive() convenience | T-40 |

---

*Generated by test_hypothesis_registry.py | 2026-08-03 13:02:09*