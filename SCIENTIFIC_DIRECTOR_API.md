# Scientific Director — API Reference

**Phase 3C | IIOS Research Infrastructure**

---

## Query API

### `daily_review() -> ScientificReview`

Execute a daily scientific review. Observes KP, GD, RM, RC, MLC, and
HypothesisRegistry. Generates hypotheses for actionable gaps. Auto-approves
Class A study plans.

```python
review = sd.daily_review()
print(review.health.value)         # "HEALTHY" | "DEGRADED" | "BLIND"
print(len(review.observations))    # number of observations
print(len(review.decisions))       # number of decisions
print(review.summary)              # human-readable summary
```

---

### `weekly_review() -> ScientificReview`

All daily observations plus CrossStudySynthesizer state.

---

### `monthly_review() -> ScientificReview`

All weekly observations plus IDR state.

---

### `evaluate_platform() -> ScientificReview`

Comprehensive health review of all components (daily + weekly + monthly scope).

---

### `approve_study(plan_id: str) -> ScientificDecision`

Load a plan from StudyPlanner and classify it.

- **CLASS_A** → auto-approved, delegated to ResearchCoordinator
- **CLASS_B** → pending, `requires_human_approval=True`

```python
decision = sd.approve_study("plan-001")

if decision.decision_type == DecisionType.APPROVE_STUDY_CLASS_A:
    print("Study approved — RC executing")
elif decision.decision_type == DecisionType.APPROVE_STUDY_CLASS_B_PENDING:
    print("Human approval required")
elif decision.decision_type == DecisionType.REJECT_STUDY:
    print("Plan not found")
```

---

### `reject_study(plan_id: str, reason: str) -> ScientificDecision`

Reject a plan with a documented scientific reason.

```python
decision = sd.reject_study("plan-002", "insufficient validation evidence")
```

---

### `roadmap() -> ScientificRoadmap`

Return the prioritised research roadmap.

```python
rm = sd.roadmap()
print(rm.total_entries)
print(rm.critical_gaps)
print(rm.next_priority_title)
print(rm.next_priority_score)
print(rm.pending_plans)
```

---

### `status() -> ScientificHealth`

Return the current operational health of the SD.

```python
h = sd.status()
print(h.health.value)                  # "HEALTHY" | "DEGRADED" | "BLIND" | "NO_DATA"
print(h.last_review_date)
print(h.total_reviews)
print(h.hypotheses_proposed)
print(h.gaps_open)
print(h.gaps_critical)
print(h.knowledge_completeness)        # 0.0–1.0
print(h.rc_health)
print(h.mlc_health)
print(h.consecutive_review_failures)
```

---

## Output Models

### `ScientificReview`

| Field | Type | Description |
|---|---|---|
| `review_id` | str | `"sd-review-{date}-{uuid8}"` |
| `review_type` | ReviewType | DAILY / WEEKLY / MONTHLY / PLATFORM |
| `date` | str | ISO date "YYYY-MM-DD" |
| `observations` | List[ScientificObservation] | What was observed |
| `decisions` | List[ScientificDecision] | What was decided |
| `recommendations` | List[ScientificRecommendation] | What is advised |
| `health` | SDHealth | HEALTHY / DEGRADED / BLIND |
| `summary` | str | Human-readable summary |
| `duration_ms` | float | Review duration in milliseconds |
| `timestamp` | str | ISO-8601 start time |

---

### `ScientificDecision`

| Field | Type | Description |
|---|---|---|
| `decision_id` | str | `"sd-dec-{uuid8}"` |
| `decision_type` | DecisionType | What type of decision |
| `decision_class` | DecisionClass | CLASS_A or CLASS_B |
| `observations` | List[ScientificObservation] | Evidence for this decision |
| `reasoning` | ScientificReasoning | How the SD reasoned |
| `decision_text` | str | What was decided |
| `delegation_target` | str | Who executes |
| `expected_outcome` | str | What should happen |
| `confidence` | float | 0.0–1.0 |
| `timestamp` | str | ISO-8601 |
| `requires_human_approval` | bool | True for CLASS_B |
| `approved_by_human` | Optional[bool] | None if pending |

---

### `ScientificObservation`

| Field | Type | Description |
|---|---|---|
| `observation_id` | str | `"sd-obs-{uuid8}"` |
| `component` | str | e.g. "GapDetector" |
| `metric` | str | e.g. "open_gaps" |
| `value` | Any | Observed value |
| `interpretation` | str | What it means |
| `significance` | SignificanceLevel | HIGH / MEDIUM / LOW / INFORMATIONAL |
| `timestamp` | str | ISO-8601 |

---

### `ScientificReasoning`

| Field | Type | Description |
|---|---|---|
| `knowledge_completeness` | float | 0.0–1.0 |
| `evidence_quality` | float | 0.0–1.0 |
| `research_value` | float | 0.0–1.0 |
| `expected_information_gain` | float | 0.0–1.0 |
| `scientific_risk` | str | "LOW" / "MEDIUM" / "HIGH" |
| `research_cost` | str | "LOW" / "MEDIUM" / "HIGH" |
| `strategic_alignment` | float | 0.0–1.0 |
| `rationale` | str | Free-text explanation |

---

### `ScientificHealth`

| Field | Type | Description |
|---|---|---|
| `health` | SDHealth | HEALTHY / DEGRADED / BLIND / NO_DATA |
| `last_review_id` | Optional[str] | Last review ID |
| `last_review_date` | Optional[str] | Last review date |
| `last_review_type` | Optional[str] | Last review type |
| `total_reviews` | int | Journal entry count |
| `hypotheses_proposed` | int | From HypothesisRegistry |
| `hypotheses_active` | int | With APPROVED status |
| `gaps_open` | int | From GapDetector |
| `gaps_critical` | int | CRITICAL severity only |
| `studies_pending` | int | From StudyPlanner |
| `knowledge_completeness` | float | 0.0–1.0 |
| `rc_health` | str | RC pipeline health |
| `mlc_health` | str | MLC pipeline health |
| `consecutive_review_failures` | int | Failure streak |
| `detail` | str | Human-readable note |

---

### `ScientificRoadmap`

| Field | Type | Description |
|---|---|---|
| `entries` | List | Raw RoadmapEntry objects |
| `total_entries` | int | Total roadmap size |
| `critical_gaps` | int | Count with CRITICAL severity |
| `high_gaps` | int | Count with HIGH severity |
| `medium_gaps` | int | Count with MEDIUM severity |
| `low_gaps` | int | Count with LOW severity |
| `pending_plans` | int | Plans awaiting execution |
| `next_priority_id` | Optional[str] | Top priority gap ID |
| `next_priority_title` | Optional[str] | Top priority study title |
| `next_priority_score` | float | Priority score 0.0–1.0 |
| `generated_at` | str | ISO-8601 generation time |

---

## Enumerations

### `ReviewType`
`DAILY | WEEKLY | MONTHLY | PLATFORM | STUDY_REVIEW | AD_HOC`

### `DecisionType`
`CREATE_HYPOTHESIS | UPDATE_ROADMAP | APPROVE_STUDY_CLASS_A | APPROVE_STUDY_CLASS_B_PENDING | REJECT_STUDY | CLOSE_STUDY | ESCALATE_HUMAN | ARCHIVE_HYPOTHESIS | PROMOTE_HYPOTHESIS | DEFER | OBSERVE`

### `DecisionClass`
`CLASS_A | CLASS_B`

### `SDHealth`
`HEALTHY | DEGRADED | BLIND | NO_DATA`

### `SignificanceLevel`
`HIGH | MEDIUM | LOW | INFORMATIONAL`

### `UrgencyLevel`
`HIGH | MEDIUM | LOW`

---

## Errors

| Exception | When |
|---|---|
| `SDError` | Base SD error |
| `SDObservationError` | Observation failed with `component` + `reason` |

---

## ID Utilities

```python
from autonomous_research import make_review_id, make_decision_id, make_observation_id, make_recommendation_id

make_review_id()          # "sd-review-2025-01-15-a1b2c3d4"
make_decision_id()        # "sd-dec-e5f6a7b8"
make_observation_id()     # "sd-obs-c9d0e1f2"
make_recommendation_id()  # "sd-rec-a3b4c5d6"
```
