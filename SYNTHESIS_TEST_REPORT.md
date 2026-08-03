# SYNTHESIS TEST REPORT
## ARS Phase 1.3 — CrossStudySynthesizer

**Date:** 2026-08-03 13:23:53  
**Tests:** 40 total | 40 passed | 0 failed | Pass rate: 100%  

---

## Synthesis Statistics (from live data)

| Metric | Value |
|---|---|
| Studies processed | 3 |
| Findings processed | 24 |
| Synthesized findings | 6 |
| Relationships discovered | 55 |
| Contradictions detected | 0 |
| Avg synthesis confidence | 0.696 |
| Edges correlated | 0 |
| Certifications correlated | 7 |
| Synthesis duration | 21.6ms |

### Classification breakdown

| Classification | Count |
|---|---|
| PARTIAL | 6 |

---

## Test Results

| Test | Status | Duration (ms) | Detail |
|---|---|---|---|
| T-01: Instantiation without registry | ✅ PASS | 0.0 | instantiated without registry |
| T-02: Instantiation with HypothesisRegistry | ✅ PASS | 0.1 | instantiated with registry |
| T-03: synthesize() returns SynthesisReport | ✅ PASS | 21.7 | report_id=SYN-20260803-132353-1433A9 |
| T-04: synthesized_findings is non-empty | ✅ PASS | 0.0 | 6 synthesized findings |
| T-05: Every synthesized finding traceable to source study | ✅ PASS | 0.0 | all 6 findings have study provenance |
| T-06: All synthesis confidences in [0.0, 1.0] | ✅ PASS | 0.0 | all 6 confidences in [0,1] |
| T-07: Confidence breakdown fully documented | ✅ PASS | 0.0 | all findings have documented confidence breakdown |
| T-08: All classifications are valid enum values | ✅ PASS | 0.0 | all 6 classifications valid |
| T-09: All 7 classification types defined in enum | ✅ PASS | 0.0 | all 7 classification types in enum |
| T-10: Relationships discovered (non-empty, multi-type) | ✅ PASS | 0.0 | 55 relationships, 4 types |
| T-11: STUDY_TO_FINDING relationships exist and are valid | ✅ PASS | 0.0 | 24 STUDY_TO_FINDING relationships |
| T-12: FINDING_TO_EDGE relationships valid when present | ✅ PASS | 0.0 | 0 FINDING_TO_EDGE relationships (may be 0) |
| T-13: FINDING_TO_METRIC relationships valid when present | ✅ PASS | 0.0 | 23 FINDING_TO_METRIC relationships |
| T-14: Contradictions — structure valid, never auto-resolved | ✅ PASS | 0.0 | 0 contradictions, none auto-resolved |
| T-15: _classify() unit tests — all 7 branches | ✅ PASS | 0.0 | all 7 _classify() cases pass |
| T-16: _calculate_confidence() unit tests | ✅ PASS | 0.0 | confidence model verified: 0.940 (full), 0.383 (contra) |
| T-17: _detect_contradictions() unit tests — 5 cases | ✅ PASS | 0.0 | all 5 contradiction detection cases pass |
| T-18: Duplicate consolidation — one SynthesizedFinding per group | ✅ PASS | 0.0 | 0 consolidated findings (cross-study, no duplicate SynthesizedFindings per gr... |
| T-19: EvidenceChain attached to every synthesized finding | ✅ PASS | 0.0 | all 6 findings have EvidenceChain |
| T-20: list_synthesized_findings() returns list | ✅ PASS | 0.0 | 6 findings returned |
| T-21: list_relationships() returns non-empty list | ✅ PASS | 0.0 | 55 relationships returned |
| T-22: list_contradictions() — none auto-resolved | ✅ PASS | 0.0 | 0 contradictions (never auto-resolved) |
| T-23: list_supported_hypotheses() without registry | ✅ PASS | 2.5 | 0 supported hypothesis IDs |
| T-24: list_supported_hypotheses() with real registry | ✅ PASS | 14.6 | 1 supported hypothesis IDs with real registry |
| T-25: list_unresolved() returns correct classifications | ✅ PASS | 0.0 | 0 unresolved / insufficient-evidence findings |
| T-26: list_by_classification() partitions correctly | ✅ PASS | 0.0 | list_by_classification() partitions correctly |
| T-27: statistics() all required fields present | ✅ PASS | 0.0 | studies=3, findings=24 |
| T-28: get_summary() returns non-empty report | ✅ PASS | 0.0 | summary: 255 chars |
| T-29: synthesize(force=True) refreshes cache | ✅ PASS | 5.0 | cache hit OK, force refresh OK (new id: SYN-20260803-132) |
| T-30: Synthesis is idempotent across two independent instances | ✅ PASS | 26.3 | synthesis is deterministic (idempotent) |
| T-31: Thread safety — 8 concurrent synthesize() calls | ✅ PASS | 16.4 | 8 threads → same report, 0 errors |
| T-32: KnowledgeProvider stores not modified during synthesis | ✅ PASS | 13.0 | 3 KP data files unchanged after synthesis |
| T-33: Consensus blocks non-empty and valid | ✅ PASS | 0.0 | 6 consensus blocks |
| T-34: SynthesisReport.to_dict() serialises correctly | ✅ PASS | 0.1 | SynthesisReport serialised: 8 top-level keys |
| T-35: SynthesizedFinding.to_dict() serialises correctly | ✅ PASS | 0.0 | SynthesizedFinding serialisation OK |
| T-36: Regime coverage tracked correctly | ✅ PASS | 0.0 | 0 findings with regime coverage |
| T-37: All relationship IDs are unique | ✅ PASS | 0.0 | 55 unique relationship IDs |
| T-38: ContradictionRecord structure and serialisation | ✅ PASS | 0.0 | ContradictionRecord serialises correctly, auto_resolved=False |
| T-39: EvidenceChain completeness scoring | ✅ PASS | 0.0 | EvidenceChain completeness scoring correct |
| T-40: statistics.by_classification sums to total | ✅ PASS | 0.0 | classification totals consistent: 6 |

---

## Failures

*No failures.*

---

## Coverage Summary

| Category | Tests |
|---|---|
| Instantiation | T-01, T-02 |
| synthesize() correctness | T-03, T-04 |
| Full provenance | T-05 |
| Confidence model | T-06, T-07, T-16 |
| Classification coverage | T-08, T-09, T-15 |
| Relationship discovery | T-10, T-11, T-12, T-13 |
| Contradiction detection | T-14, T-17 |
| Duplicate consolidation | T-18 |
| Evidence chain | T-19, T-39 |
| Query API | T-20–T-26 |
| Statistics | T-27, T-40 |
| get_summary() | T-28 |
| Cache management | T-29 |
| Idempotency | T-30 |
| Thread safety | T-31 |
| Read-only verification | T-32 |
| Consensus blocks | T-33 |
| Serialisation | T-34, T-35, T-38 |
| Regime coverage | T-36 |
| Relationship ID uniqueness | T-37 |

---

## Final Accountability Questions

**Q1: Can every synthesized conclusion be traced to original evidence?**
YES. Every `SynthesizedFinding` carries `source_study_ids`, `source_finding_ids`,
and a full `EvidenceChain` with study, finding, edge, metric, hypothesis, and
certification layers.

**Q2: Can contradictions always be identified?**
YES. `_detect_contradictions()` compares findings within each group by numeric
value divergence (>40%) and direction conflict (opposite signs). All
ContradictionRecords have `auto_resolved=False` — contradictions are never silently
resolved.

**Q3: Can duplicated findings be consolidated without losing provenance?**
YES. Findings with the same `(classification, metric)` key are merged into one
`SynthesizedFinding` that retains all `source_study_ids` and `source_finding_ids`.
No information is discarded.

**Q4: Is every synthesized conclusion reproducible?**
YES. Given the same KnowledgeProvider data, `synthesize()` always produces the
same findings, same classifications, and same relationships. The confidence
formula is fully documented in `confidence_breakdown` for every finding.

---

*Generated by test_cross_study_synthesizer.py | 2026-08-03 13:23:53*