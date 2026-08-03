# GAP_DETECTOR_DESIGN.md — ARS Phase 2A

## Purpose

`GapDetector` is the scientific observation layer of the Autonomous Research System.
It continuously analyses the complete IIOS knowledge base and identifies statistically
significant gaps that require future research.

GapDetector **only observes**.  It never plans, prioritises, executes, or writes.

---

## Architecture

```
KnowledgeProvider ─────────────────┐
                                   ├──► GapDetector.detect()
HypothesisRegistry ────────────────┤         │
                                   │         │  10 detection rules
CrossStudySynthesizer ─────────────┘         │
                                             ▼
                                   List[KnowledgeGap]
                                   + GapStatistics
                                   = GapDetectionReport
```

GapDetector consumes the three Phase 1 foundation modules exclusively.
No direct JSON access.  No duplicated parsing.  No duplicated synthesis logic.

---

## Gap Categories (10)

| Category | Rule | Description |
|---|---|---|
| `DATA_GAP` | R-GD-01 | Study has fewer observations than the minimum required |
| `EVIDENCE_GAP` | R-GD-02 | Synthesized finding is corroborated by too few studies |
| `REGIME_GAP` | R-GD-03 | Known market regime has insufficient research findings |
| `SECTOR_GAP` | R-GD-04 | Sector has sparse feature-database coverage |
| `TEMPORAL_GAP` | R-GD-05 | Most recent study exceeds the maximum allowed age |
| `VALIDATION_GAP` | R-GD-06 | CANDIDATE edges lack walk-forward validation metrics |
| `CONTRADICTION_GAP` | R-GD-07 | Conflicting findings detected by CrossStudySynthesizer |
| `CONFIDENCE_GAP` | R-GD-08 | Synthesized finding confidence below the minimum threshold |
| `KNOWLEDGE_GAP` | R-GD-09 | Hypothesis has been open longer than the maximum allowed age |
| `COVERAGE_GAP` | R-GD-10 | FindingClassification has zero findings across all studies |

All ten categories are defined in `GapCategory(str, Enum)` and designed for future
extension without breaking existing consumers.

---

## Detection Rules

All rules are **deterministic** (no AI, no randomness), **configurable** (all
thresholds in `GapDetectorConfig`), and **traceable** (each gap documents its
`rule_id`, `rule_parameters`, and `supporting_evidence`).

### R-GD-01 — DATA_GAP
**Trigger:** `study.n_observations < GapDetectorConfig.min_study_observations`

**Severity calculation:**

| Condition | Severity |
|---|---|
| `n < threshold ÷ 3` | CRITICAL |
| `n < threshold ÷ 2` | HIGH |
| `n < threshold` | MEDIUM |

**Evidence:** study_id, n_observations value

---

### R-GD-02 — EVIDENCE_GAP
**Trigger:** `synthesized_finding.supporting_study_count < min_corroborating_studies`

Consumes `CrossStudySynthesizer.synthesize()` output.

**Severity calculation:**

| Condition | Severity |
|---|---|
| `count == 0` | HIGH |
| `count < min_corroborating_studies` | MEDIUM |

**Evidence:** synthesis_id, source study IDs

---

### R-GD-03 — REGIME_GAP
**Trigger:** Known regime (from `GapDetectorConfig.known_regimes`) has fewer than
`min_findings_per_regime` findings across all studies.

Cross-references `KnowledgeProvider.get_regime_history()` to determine whether
the regime was actually observed in live data.

**Severity calculation:**

| Condition | Severity | Confidence |
|---|---|---|
| count == 0 AND observed in history | HIGH | 1.0 |
| count == 0 AND not observed | MEDIUM | 0.7 |
| count < minimum but > 0 | MEDIUM | 1.0 |

**Evidence:** `regime:{name}`, finding_count, history_observations

---

### R-GD-04 — SECTOR_GAP
**Trigger:** Feature database has a sector with fewer than `min_sector_observations`
observations, or no sector metadata at all.

Reads all FeatureRecord objects via `KnowledgeProvider.list_features(limit=None)`.

**Severity calculation:**

| Condition | Severity |
|---|---|
| Zero sector-tagged observations in entire database | HIGH (one summary gap) |
| Sector count < minimum | MEDIUM per sector |

**Evidence:** `sector:{name}`, observation count

---

### R-GD-05 — TEMPORAL_GAP
**Trigger:** Newest study (by `executed_at`) is older than `max_study_age_days`.

One gap maximum per detection run (for the newest study only).

**Severity calculation:**

| Condition | Severity |
|---|---|
| No dated studies | CRITICAL |
| age > 3 × threshold | CRITICAL |
| age > 2 × threshold | HIGH |
| age > threshold | MEDIUM |

**Evidence:** study_id of newest study, `age_days:{n}`

---

### R-GD-06 — VALIDATION_GAP
**Trigger:** CANDIDATE edges (status == CANDIDATE) that lack both `oos_win_rate`
and `wf_consistency` validation metrics, grouped by edge category.

One gap per category-group.  Age computed from `EdgeRecord.created_at` or
`last_tested` (whichever is available).

**Severity calculation:**

| Condition | Severity |
|---|---|
| oldest_age is None (no age metadata) | HIGH |
| oldest_age > 2 × max_edge_unvalidated_days | HIGH |
| else | MEDIUM |

**Evidence:** edge_ids (up to 10 per gap)

---

### R-GD-07 — CONTRADICTION_GAP
**Trigger:** One gap per `ContradictionRecord` in `CrossStudySynthesizer.synthesize()`.

Contradictions are never auto-resolved by the Synthesizer, so every contradiction
that exists at synthesis time is surfaced as a gap.

**Severity calculation mirrors `ContradictionRecord.severity`:**

| Condition | Severity |
|---|---|
| severity > contradiction_high_threshold (default 0.70) | HIGH |
| severity > contradiction_medium_threshold (default 0.40) | MEDIUM |
| severity ≤ medium threshold | LOW |

**Evidence:** contradiction_id, finding_a_id, finding_b_id

---

### R-GD-08 — CONFIDENCE_GAP
**Trigger:** `synthesized_finding.synthesis_confidence < min_synthesis_confidence`

Consumes `CrossStudySynthesizer.synthesize()` output.

**Severity calculation:**

| Condition | Severity |
|---|---|
| confidence < confidence_critical_threshold (default 0.30) | CRITICAL |
| confidence < confidence_high_threshold (default 0.45) | HIGH |
| confidence < min_synthesis_confidence (default 0.60) | MEDIUM |

**Evidence:** synthesis_id, `confidence:{value}`

---

### R-GD-09 — KNOWLEDGE_GAP
**Trigger:** Open hypothesis (status in OPEN_STATUSES) has been open for more than
`max_hypothesis_open_days`.

Severity mirrors `HypothesisPriority`:

| Priority | Severity |
|---|---|
| CRITICAL | CRITICAL |
| HIGH | HIGH |
| MEDIUM | MEDIUM |
| LOW / EXPLORATORY | LOW |

**Evidence:** hypothesis_id, `age_days:{n}`, `status:{value}`

---

### R-GD-10 — COVERAGE_GAP
**Trigger:** A `FindingClassification` value (excluding UNKNOWN) has zero findings
across all studies.

Severity: always HIGH.  Fires one gap per missing classification.

**Evidence:** `classification:{value}`, `studies_checked:{n}`

---

## Severity Levels

| Level | Estimated Knowledge Gain | Meaning |
|---|---|---|
| CRITICAL | 0.90 | Blocks reliable research; requires immediate attention |
| HIGH | 0.70 | Significant gap affecting result quality |
| MEDIUM | 0.50 | Noticeable gap; address in next research cycle |
| LOW | 0.20 | Minor gap; background research interest |

---

## Gap Identity

Every `KnowledgeGap` has a **deterministic `gap_id`**:

```
G-{category[:4]}-{rule_id}-{sha256(category:rule_id:source_key)[:8]}
```

Running `detect()` on unchanged data always produces the same `gap_id` values.
This enables stable references in downstream components.

---

## Traceability Guarantees

Every `KnowledgeGap` guarantees:

1. **`supporting_evidence`** — non-empty list of IDs or descriptors identifying the
   exact evidence that triggered the gap.
2. **`related_studies`** — all study IDs relevant to this gap.
3. **`related_hypotheses`** — all hypothesis IDs relevant to this gap.
4. **`related_findings`** — all finding IDs relevant to this gap.
5. **`severity_rationale`** — human-readable string explaining exactly why this
   severity level was assigned.
6. **`rule_id`** — the exact rule that produced this gap (e.g., `R-GD-03`).
7. **`rule_parameters`** — the `GapDetectorConfig` values active when the rule fired.

---

## Thread Safety

`GapDetector.detect()` is protected by `threading.Lock()`.  Concurrent calls are
serialised.  All `list_*()` methods are lock-free (they operate on immutable
snapshot from the last detection run).

---

## Read-Only Contract

GapDetector **never**:
- Creates, updates, or archives hypotheses
- Modifies studies, findings, edges, or metrics
- Writes to any file or database
- Calls any write method on KnowledgeProvider, HypothesisRegistry, or CrossStudySynthesizer

---

## Final Answers

**Q1: Can every detected gap be traced to evidence?**
Yes.  Every `KnowledgeGap` has a non-empty `supporting_evidence` list, a
`severity_rationale`, a `rule_id`, and `rule_parameters`.  Verified by T-22 through T-26.

**Q2: Can every gap be reproduced?**
Yes.  `gap_id` is a deterministic SHA-256 hash of `(category, rule_id, source_key)`.
Given the same underlying data, detect() always produces the same gap_ids.
Verified by T-37.

**Q3: Does GapDetector duplicate any existing IIOS capability?**
No.  It consumes outputs from the three foundation modules without re-implementing
any parsing, synthesis, or validation logic.  All synthesis logic remains in
CrossStudySynthesizer; all persistence in HypothesisRegistry; all data access in
KnowledgeProvider.

**Q4: Can the Scientific Director safely depend on GapDetector?**
Yes.  GapDetector is read-only, thread-safe, deterministic, and fully traceable.
The SD can call `detect()` at any frequency without risk of state corruption.
The `detect(force=False)` cache pattern ensures minimal I/O overhead.
