# StudyPlanner — Design Document

**ARS Phase 2D**  
**Module:** `autonomous_research/study_planner.py`  
**Status:** Complete (69/69 tests passing)

---

## 1. Purpose

StudyPlanner is the scientific experiment design engine of ARS.

It converts validated research priorities into fully specified, reproducible
study plans that can be approved and executed without additional planning.

StudyPlanner does not execute studies.  
StudyPlanner does not generate hypotheses.  
StudyPlanner does not modify knowledge.  
StudyPlanner does not change roadmaps.

The only state it maintains is an in-memory plan registry (thread-safe).

---

## 2. Position in the ARS Pipeline

```
GapDetector  →  RoadmapManager  →  EvidenceValidator  →  [StudyPlanner]
                                                               ↓
                                                      Scientific Director
                                                          approves plan
                                                               ↓
                                                    [execution by future module]
```

StudyPlanner is the last planning layer before execution.  A plan produced
here answers all four final questions before a study begins:

1. Can every study plan be reproduced?  
   **Yes** — plan_id is `SP-{sha256(study_type:title:source_key)[:8].upper()}`.

2. Can every required dataset be traced?  
   **Yes** — every `DatasetRequirement` names symbols, date range, regimes,
   sectors, feature groups, and minimum observations.

3. Can execution begin without additional planning?  
   **Yes** — every plan includes ordered tasks, a full validation protocol,
   an execution estimate, acceptance criteria, and a dependency list.

4. Can the Scientific Director approve directly from this plan?  
   **Yes** — every plan includes risk class, approval class, expected outputs,
   success criteria, and acceptance criteria.

---

## 3. Architecture

```
StudyPlanner
    │
    ├── reads from: KnowledgeProvider (symbol metadata, studies)
    ├── reads from: HypothesisRegistry (hypothesis details for create_from_hypothesis)
    ├── reads from: GapDetector (gap validation in validate_dependencies)
    ├── reads from: RoadmapManager (optional context)
    ├── reads from: EvidenceValidator (optional quality context)
    │
    ├── create_plan()              → StudyPlan
    ├── create_from_gap()          → StudyPlan
    ├── create_from_hypothesis()   → StudyPlan
    ├── create_from_entry()        → StudyPlan
    │
    ├── list_plans()               → List[StudyPlan]
    ├── get_plan()                 → StudyPlan
    ├── latest_plans()             → List[StudyPlan]
    ├── validate_dependencies()    → List[str]  (issues)
    ├── estimate_cost()            → ExecutionEstimate
    ├── portfolio()                → StudyPortfolio
    └── statistics()               → PlanningStatistics
```

---

## 4. Ten Study Types

| Type | Description | Default Risk | Parallelizable | Compute |
|------|-------------|-------------|---------------|---------|
| HISTORICAL_REPLAY | Replay over a historical date range | LOW | Yes | MEDIUM |
| DNA_DISCOVERY | Extract winner/loser DNA patterns | MEDIUM | No | LOW |
| REGIME_ANALYSIS | Regime-conditional behaviour analysis | MEDIUM | Yes | MEDIUM |
| SECTOR_RESEARCH | Sector-specific research | LOW | Yes | LOW |
| EDGE_VALIDATION | Validate or invalidate a trading edge | MEDIUM | Yes | LOW |
| CROSS_VALIDATION | Resolve contradictions via controlled comparison | HIGH | No | MEDIUM |
| FEATURE_IMPORTANCE | Rank feature contributions | MEDIUM | Yes | MEDIUM |
| PATTERN_MINING | Scan for new patterns | MEDIUM | Yes | HIGH |
| META_LEARNING | Learn from prior study results | HIGH | No | HIGH |
| CUSTOM | User-defined study | HIGH | No | MEDIUM |

---

## 5. Gap Category → Study Type Mapping

| Gap Category | Study Type |
|---|---|
| DATA_GAP | HISTORICAL_REPLAY |
| EVIDENCE_GAP | DNA_DISCOVERY |
| REGIME_GAP | REGIME_ANALYSIS |
| SECTOR_GAP | SECTOR_RESEARCH |
| TEMPORAL_GAP | HISTORICAL_REPLAY |
| VALIDATION_GAP | EDGE_VALIDATION |
| CONTRADICTION_GAP | CROSS_VALIDATION |
| CONFIDENCE_GAP | EDGE_VALIDATION |
| KNOWLEDGE_GAP | DNA_DISCOVERY |
| COVERAGE_GAP | REGIME_ANALYSIS |

---

## 6. Hypothesis Classification → Study Type Mapping

| HypothesisClassification | Study Type |
|---|---|
| PERFORMANCE_GAP | EDGE_VALIDATION |
| COVERAGE_GAP | REGIME_ANALYSIS |
| TEMPORAL_GAP | HISTORICAL_REPLAY |
| DEGRADATION | EDGE_VALIDATION |
| CONTRADICTION | CROSS_VALIDATION |
| EXPLORATORY | DNA_DISCOVERY |
| MANUAL | CUSTOM |

---

## 7. Approval Class Rules

```
if study_type in class_b_study_types:          → CLASS_B
elif risk_class >= class_b_risk_threshold:     → CLASS_B
else:                                          → CLASS_A
```

Default `class_b_study_types`: `[META_LEARNING, CUSTOM]`  
Default `class_b_risk_threshold`: `HIGH`

**CLASS_A:** routine review sufficient — HISTORICAL_REPLAY, DNA_DISCOVERY,
REGIME_ANALYSIS, SECTOR_RESEARCH, EDGE_VALIDATION, FEATURE_IMPORTANCE,
PATTERN_MINING (all with LOW/MEDIUM risk)

**CLASS_B:** explicit Scientific Director approval required — META_LEARNING,
CUSTOM, any study with HIGH risk (including CROSS_VALIDATION by default)

---

## 8. Plan ID Determinism

```python
plan_id = f"SP-{sha256(f'{study_type.value}:{title.strip()}:{source_key}').hexdigest()[:8].upper()}"
```

`source_key` = `source_gap_id or source_hypothesis_id or source_entry_id or ""`

Same study type + title + source → same plan_id across runs.

---

## 9. StudyPlan Structure

Each plan contains exactly:

| Section | Contents |
|---------|----------|
| Identity | plan_id, study_type, title, status |
| Scientific | objective, scientific_question, background |
| Evidence | supporting_evidence[], related_hypotheses[], related_gaps[] |
| Data | dataset_requirements[] (≥ 1 DatasetRequirement) |
| Validation | validation_plan (methodology, WF windows, OOS split, criteria) |
| Execution | tasks[] (exactly 5, ordered 1–5) |
| Resources | execution_estimate (hours, cost, storage, intensity) |
| Governance | risk_class, approval_class |
| Outcomes | expected_outputs[], success_criteria[], acceptance_criteria[] |
| Provenance | source_gap_id, source_hypothesis_id, source_entry_id |
| Metadata | created_at, estimated_knowledge_gain |
| Dependencies | dependencies[] (validated via validate_dependencies) |

---

## 10. Execution Estimate Formula

```
(data_fetch_hours, compute_hours, analysis_hours) = profile[study_type]
total_hours = data_fetch_hours + compute_hours + analysis_hours
compute_cost_usd = compute_hours * cost_per_compute_hour_usd
storage_mb = n_symbols * n_years * storage_mb_per_symbol_year
```

All parameters configurable via `StudyPlannerConfig`. No hardcoded values.

---

## 11. Dependency Validation

`validate_dependencies(plan_id)` performs three checks:

1. **Reference check** — every `depends_on_plan_id` must exist in the plan registry.
2. **Gap check** — if `gap_detector` is available, `depends_on_gap_id` must be in the current gap set.
3. **Hypothesis check** — if `hypothesis_registry` is available, `depends_on_hypothesis_id` must be in the registry.
4. **Cycle detection** — DFS traversal detects circular dependency chains.

Returns a list of issue strings. Empty list = no issues.

---

## 12. Thread Safety

All writes to `self._plans` are protected by `threading.Lock()`.  
Concurrent calls to all public methods are safe.

---

## 13. Final Questions

**1. Can every study plan be reproduced?**  
Yes — plan_id is deterministic; all parameters are documented in the record.

**2. Can every required dataset be traced?**  
Yes — `DatasetRequirement` contains all data specification: symbols, date
range, regimes, sectors, feature groups, min_observations, and notes.

**3. Can execution begin without additional planning?**  
Yes — every plan has ordered tasks, a validation protocol, acceptance
criteria, and an execution estimate. No information is missing.

**4. Can the Scientific Director approve directly from this plan?**  
Yes — approval_class, risk_class, expected_outputs, success_criteria,
and acceptance_criteria are all documented at creation time.
