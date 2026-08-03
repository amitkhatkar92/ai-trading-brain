# GAP_DETECTOR_TEST_REPORT.md — ARS Phase 2A

## Test Run Summary

| Metric | Value |
|---|---|
| Total tests | 50 |
| Passed | 50 |
| Failed | 0 |
| Pass rate | 100% |
| Test file | `test_gap_detector.py` |

---

## Coverage Matrix

| Area | Tests | Status |
|---|---|---|
| Instantiation (full / no registry / no synthesizer) | T-01, T-02, T-03 | ✅ |
| `detect()` return structure | T-04, T-05 | ✅ |
| `detect()` caching | T-06, T-07 | ✅ |
| **Rule R-GD-01 DATA_GAP** | T-08, T-23 | ✅ |
| **Rule R-GD-02 EVIDENCE_GAP** | T-09, T-20, T-24 | ✅ |
| **Rule R-GD-03 REGIME_GAP** | T-10, T-25 | ✅ |
| **Rule R-GD-04 SECTOR_GAP** | T-11 | ✅ |
| **Rule R-GD-05 TEMPORAL_GAP** | T-12, T-18 | ✅ |
| **Rule R-GD-06 VALIDATION_GAP** | T-13 | ✅ |
| **Rule R-GD-07 CONTRADICTION_GAP** | T-14, T-21 | ✅ |
| **Rule R-GD-08 CONFIDENCE_GAP** | T-15 | ✅ |
| **Rule R-GD-09 KNOWLEDGE_GAP** | T-16, T-26, T-32 | ✅ |
| **Rule R-GD-10 COVERAGE_GAP** | T-17, T-19 | ✅ |
| **100% rule coverage** | All 10 rules exercised | ✅ |
| CRITICAL severity | T-18 | ✅ |
| HIGH severity | T-19 | ✅ |
| MEDIUM severity | T-20 | ✅ |
| LOW severity | T-21 | ✅ |
| **All 4 severity levels reachable** | T-18..T-21 | ✅ |
| Evidence traceability (all gaps) | T-22 | ✅ |
| DATA_GAP evidence | T-23 | ✅ |
| EVIDENCE_GAP evidence | T-24 | ✅ |
| REGIME_GAP evidence | T-25 | ✅ |
| KNOWLEDGE_GAP evidence | T-26 | ✅ |
| `list_all()` | T-27 | ✅ |
| `list_open()` | T-28 | ✅ |
| `list_by_category()` | T-29 | ✅ |
| `list_by_severity()` | T-30 | ✅ |
| `list_by_study()` | T-31 | ✅ |
| `list_by_hypothesis()` | T-32 | ✅ |
| `statistics()` structure | T-33 | ✅ |
| `by_category` sum consistency | T-34 | ✅ |
| `by_severity` sum consistency | T-35 | ✅ |
| `critical_count` / `high_count` accuracy | T-36 | ✅ |
| Deterministic gap_ids | T-37 | ✅ |
| `detect(force=True)` refresh | T-38 | ✅ |
| Config customisation | T-39, T-40 | ✅ |
| `rule_parameters` documentation | T-40 | ✅ |
| `rule_id` validation | T-41 | ✅ |
| KP read-only verification | T-42 | ✅ |
| Registry read-only verification | T-43 | ✅ |
| Synthesizer read-only verification | T-44 | ✅ |
| **Read-only verified** | T-42, T-43, T-44 | ✅ |
| Concurrent execution (8 threads) | T-45 | ✅ |
| Pre-detect() empty state | T-46, T-47 | ✅ |
| `to_dict()` round-trip | T-48, T-49 | ✅ |
| Backward compatibility | T-50 | ✅ |

---

## Live Detection Snapshot

Run against live IIOS knowledge base (2026-08-03):

| Metric | Value |
|---|---|
| Total gaps detected | 11 |
| Open gaps | 11 |
| Detection duration | 61.1 ms |
| Studies processed | 3 |
| Findings processed | 24 |
| Edges analysed | 259 |

### Gaps by category

| Category | Count |
|---|---|
| EVIDENCE_GAP | 6 |
| REGIME_GAP | 4 |
| COVERAGE_GAP | 1 |

### Gaps by severity

| Severity | Count |
|---|---|
| HIGH | 2 |
| MEDIUM | 9 |

### Rules fired

| Rule | Gaps |
|---|---|
| R-GD-02 EVIDENCE_GAP | 6 |
| R-GD-03 REGIME_GAP | 4 |
| R-GD-10 COVERAGE_GAP | 1 |

### Interpretation of live gaps

**EVIDENCE_GAP (6 gaps, MEDIUM):** All 6 synthesized findings are corroborated by
only 1 study, below the default minimum of 2. Each represents a research opportunity
to corroborate existing findings with a second independent study.

**REGIME_GAP (4 gaps, HIGH × 1, MEDIUM × 3):**
- VOLATILE regime — HIGH: observed in live market history but no research findings.
  Requires immediate attention.
- TREND, RANGE, BEAR — MEDIUM: no findings but not confirmed in current history data.

**COVERAGE_GAP (1 gap, HIGH):**
- `REGIME_PATTERN` classification has zero findings across all 3 studies.
  No study has ever investigated regime-specific pattern behaviour.

### Rules that did not fire (healthy state)

| Rule | Reason not fired |
|---|---|
| R-GD-01 DATA_GAP | All studies meet the default 100-observation threshold |
| R-GD-04 SECTOR_GAP | Feature database has adequate sector coverage |
| R-GD-05 TEMPORAL_GAP | Studies are within the 90-day freshness window |
| R-GD-06 VALIDATION_GAP | No unvalidated CANDIDATE edges meeting the age threshold |
| R-GD-07 CONTRADICTION_GAP | CrossStudySynthesizer detected 0 contradictions |
| R-GD-08 CONFIDENCE_GAP | All synthesized finding confidences ≥ 0.60 default |
| R-GD-09 KNOWLEDGE_GAP | Registry contains 0 hypotheses (none stalled) |

---

## Final Answers

**Q1: Can every detected gap be traced to evidence?**
Yes — T-22 confirms all 11 live gaps have non-empty `supporting_evidence`.
T-23 through T-26 verify category-specific evidence fields.

**Q2: Can every gap be reproduced?**
Yes — T-37 confirms gap_ids are deterministic.  Running `detect(force=True)` twice
on the same data produces identical `gap_id` sets.

**Q3: Does GapDetector duplicate any existing IIOS capability?**
No — GapDetector calls:
- `KP.list_studies()`, `list_findings()`, `list_edges()`, `list_features()`,
  `get_regime_history()` (read-only KP methods)
- `REG.list_open()` (read-only Registry method)
- `SYN.synthesize()` (consumes cached synthesis output, does not re-synthesize)

No parsing, synthesis, or validation logic is duplicated.

**Q4: Can the Scientific Director safely depend on GapDetector?**
Yes — T-42, T-43, T-44 verify complete read-only isolation.
T-45 confirms 8-thread concurrent safety.
The detection run takes 61 ms on live data with full synthesis, making it suitable
for every research cycle invocation.
