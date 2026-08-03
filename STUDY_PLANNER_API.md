# StudyPlanner — Public API Reference

**ARS Phase 2D**  
**Module:** `autonomous_research.study_planner`  
**Import:** `from autonomous_research import StudyPlanner`

---

## Class: `StudyPlanner`

Scientific experiment design engine.

### Constructor

```python
StudyPlanner(
    knowledge_provider:  KnowledgeProvider,
    hypothesis_registry: Optional[HypothesisRegistry]   = None,
    gap_detector:        Optional[GapDetector]           = None,
    roadmap_manager:     Optional[RoadmapManager]        = None,
    evidence_validator:  Optional[EvidenceValidator]     = None,
    config:              Optional[StudyPlannerConfig]    = None,
)
```

| Parameter | Required | Purpose |
|-----------|----------|---------|
| `knowledge_provider` | ✅ | Symbol metadata and study listings |
| `hypothesis_registry` | Optional | Required for `create_from_hypothesis()` |
| `gap_detector` | Optional | Enables gap reference validation in `validate_dependencies()` |
| `roadmap_manager` | Optional | Reserved for roadmap context |
| `evidence_validator` | Optional | Reserved for quality context |
| `config` | Optional | Override all defaults and thresholds |

---

### Methods

#### `create_plan(...) → StudyPlan`

Create a plan from explicit parameters.

```python
plan = planner.create_plan(
    title="Momentum Edge Validation",
    study_type=StudyType.EDGE_VALIDATION,
    scientific_question="Does momentum persist in TRENDING_UP regime?",
    objective="Validate momentum edge using 2-year OOS period.",
    background="Prior study found momentum Sharpe 1.2 in-sample.",
    supporting_evidence=["FINDING-001", "EDGE-042"],
    related_hypotheses=["HYP-012"],
    related_gaps=["GAP-003"],
    risk_class=RiskClass.MEDIUM,            # optional; default from study_type
    estimated_knowledge_gain=0.65,
    source_gap_id="GAP-003",
    source_hypothesis_id="HYP-012",
)
```

All parameters except `title`, `study_type`, `scientific_question` are optional.

#### `create_from_gap(gap: KnowledgeGap) → StudyPlan`

Create a plan that addresses a `KnowledgeGap`.

- Automatically maps `gap.category` → `study_type`
- Sets `source_gap_id`, `supporting_evidence`, `related_gaps`
- Sets `estimated_knowledge_gain` from `gap.estimated_knowledge_gain`

#### `create_from_hypothesis(hypothesis_id: str) → StudyPlan`

Create a plan to validate a `ScientificHypothesis`.

- Requires `hypothesis_registry` at construction
- Maps `hypothesis.classification` → `study_type`
- Sets `scientific_question` from `hypothesis.research_question`
- Sets `background` from `hypothesis.description`

Raises `StudyPlannerError` if no registry was provided.  
Raises `StudyPlanNotFoundError` if hypothesis not found.

#### `create_from_entry(entry: RoadmapEntry) → StudyPlan`

Create a plan from a prioritized `RoadmapEntry`.

- Title from `entry.recommended_study_title`
- Objective from `entry.recommended_approach`
- Sets `source_entry_id` and `source_gap_id`
- `estimated_knowledge_gain` from `entry.knowledge_gain_estimate.total_gain`

#### `list_plans(status=None, study_type=None) → List[StudyPlan]`

Return all stored plans, optionally filtered by status or study type.

```python
all_plans   = planner.list_plans()
draft_plans = planner.list_plans(status=PlanStatus.DRAFT)
replay_plans = planner.list_plans(study_type=StudyType.HISTORICAL_REPLAY)
```

#### `get_plan(plan_id: str) → StudyPlan`

Return a specific plan.  
Raises `StudyPlanNotFoundError` if not found.

#### `latest_plans(n=10) → List[StudyPlan]`

Return the N most recently created plans, newest first.

#### `validate_dependencies(plan_id: str) → List[str]`

Validate all dependencies of a plan. Returns issue strings (empty = no issues).

Checks: missing plan references, missing gap references, missing hypothesis
references, circular dependency chains.

Raises `StudyPlanNotFoundError` if plan_id does not exist.

#### `estimate_cost(plan_id: str) → ExecutionEstimate`

Return the execution estimate for a plan.  
Raises `StudyPlanNotFoundError` if not found.

#### `portfolio() → StudyPortfolio`

Return an aggregate portfolio view of all current plans.

#### `statistics() → PlanningStatistics`

Return aggregate statistics for all plans in this session.

---

## Class: `StudyPlannerConfig`

```python
@dataclass
class StudyPlannerConfig:
    default_date_lookback_days:   int       = 504    # ~2 trading years
    default_oos_split:            float     = 0.20
    default_walk_forward_windows: int       = 5
    default_cv_folds:             int       = 5
    default_min_win_rate:         float     = 0.50
    default_min_sharpe:           float     = 0.80
    default_max_drawdown:         float     = 0.15
    default_min_observations:     int       = 100
    max_symbols_per_plan:         int       = 50
    cost_per_compute_hour_usd:    float     = 0.50
    storage_mb_per_symbol_year:   float     = 10.0
    class_b_study_types:          List[StudyType] = [META_LEARNING, CUSTOM]
    class_b_risk_threshold:       RiskClass = HIGH
```

---

## Data Model Reference

### `StudyPlan`

| Field | Type | Description |
|-------|------|-------------|
| `plan_id` | `str` | `SP-{sha256[:8]}` — deterministic |
| `study_type` | `StudyType` | One of 10 study types |
| `title` | `str` | Human-readable study title |
| `objective` | `str` | What the study will achieve |
| `scientific_question` | `str` | Exact question to be answered |
| `background` | `str` | Context, prior evidence, motivation |
| `supporting_evidence` | `List[str]` | Evidence IDs from KP |
| `related_hypotheses` | `List[str]` | Hypothesis IDs |
| `related_gaps` | `List[str]` | Gap IDs |
| `dataset_requirements` | `List[DatasetRequirement]` | ≥ 1 required dataset |
| `validation_plan` | `ValidationPlan` | Full validation protocol |
| `tasks` | `List[StudyTask]` | Exactly 5 ordered tasks |
| `execution_estimate` | `ExecutionEstimate` | Hours, cost, storage |
| `dependencies` | `List[StudyDependency]` | Pre-requisite plans/gaps |
| `risk_class` | `RiskClass` | LOW / MEDIUM / HIGH |
| `approval_class` | `ApprovalClass` | CLASS_A / CLASS_B |
| `status` | `PlanStatus` | DRAFT / READY / APPROVED / SUPERSEDED |
| `expected_outputs` | `List[str]` | Artifacts produced |
| `success_criteria` | `List[str]` | Measurable targets |
| `acceptance_criteria` | `List[str]` | Promotion gates |
| `estimated_knowledge_gain` | `float` | 0.0–1.0 |
| `source_gap_id` | `Optional[str]` | Originating gap |
| `source_hypothesis_id` | `Optional[str]` | Originating hypothesis |
| `source_entry_id` | `Optional[str]` | Originating roadmap entry |
| `created_at` | `datetime` | Creation timestamp |

### `DatasetRequirement`

| Field | Type | Description |
|-------|------|-------------|
| `name` | `str` | Dataset identifier |
| `symbols` | `List[str]` | Required tickers |
| `date_start` | `Optional[str]` | ISO start date |
| `date_end` | `Optional[str]` | ISO end date |
| `regimes` | `List[str]` | Required market regimes |
| `sectors` | `List[str]` | Required sectors |
| `feature_groups` | `List[str]` | Required feature sets |
| `min_observations` | `int` | Minimum rows |
| `notes` | `str` | Additional requirements |

### `ValidationPlan`

| Field | Type | Description |
|-------|------|-------------|
| `methodology` | `str` | Human description |
| `walk_forward_windows` | `int` | Number of WF windows |
| `oos_split` | `float` | Holdout fraction |
| `cross_validation_folds` | `int` | CV folds |
| `success_criteria` | `List[str]` | Measurable targets |
| `acceptance_criteria` | `List[str]` | Gates that must pass |
| `metrics` | `List[str]` | Metrics to track |
| `min_win_rate` | `float` | Minimum acceptable win rate |
| `min_sharpe` | `float` | Minimum acceptable Sharpe |
| `max_drawdown` | `float` | Maximum acceptable drawdown |

### `ExecutionEstimate`

| Field | Type | Description |
|-------|------|-------------|
| `data_fetch_hours` | `float` | Data acquisition time |
| `compute_hours` | `float` | Core computation time |
| `analysis_hours` | `float` | Analysis and reporting time |
| `total_hours` | `float` | Sum of above three |
| `compute_cost_usd` | `float` | Rough cloud cost |
| `storage_mb` | `float` | Estimated storage |
| `parallelizable` | `bool` | Can tasks run in parallel? |
| `compute_intensity` | `str` | "LOW" / "MEDIUM" / "HIGH" |
| `breakdown` | `Dict` | Formula components documented |

### `StudyTask`

| Field | Type | Description |
|-------|------|-------------|
| `task_id` | `str` | `T01` through `T05` |
| `title` | `str` | Task name |
| `description` | `str` | What this task does |
| `inputs` | `List[str]` | Required artifact names |
| `outputs` | `List[str]` | Produced artifact names |
| `estimated_hours` | `float` | Hours for this task |
| `order` | `int` | 1-based sequential order |

### `StudyDependency`

| Field | Type | Description |
|-------|------|-------------|
| `depends_on_plan_id` | `Optional[str]` | Another plan to complete first |
| `depends_on_gap_id` | `Optional[str]` | A gap to close first |
| `depends_on_hypothesis_id` | `Optional[str]` | A hypothesis to validate first |
| `reason` | `str` | Why this dependency exists |
| `is_blocking` | `bool` | True → plan cannot start until resolved |

### `StudyPortfolio`

| Field | Type | Description |
|-------|------|-------------|
| `plans` | `List[StudyPlan]` | All current plans |
| `total_plans` | `int` | Count |
| `by_study_type` | `Dict[str, int]` | Per-type counts |
| `by_approval_class` | `Dict[str, int]` | Per-class counts |
| `by_risk_class` | `Dict[str, int]` | Per-risk counts |
| `by_status` | `Dict[str, int]` | Per-status counts |
| `total_compute_hours` | `float` | Sum across all plans |
| `total_knowledge_gain` | `float` | Sum across all plans |
| `class_b_plans` | `List[str]` | plan_ids needing explicit approval |
| `built_at` | `datetime` | Build timestamp |

### `PlanningStatistics`

| Field | Type | Description |
|-------|------|-------------|
| `total_plans_created` | `int` | All plans in this session |
| `by_study_type` | `Dict[str, int]` | StudyType.value → count |
| `by_approval_class` | `Dict[str, int]` | ApprovalClass.value → count |
| `by_risk_class` | `Dict[str, int]` | RiskClass.value → count |
| `avg_knowledge_gain` | `float` | Mean estimated_knowledge_gain |
| `avg_compute_hours` | `float` | Mean total_hours |
| `class_b_fraction` | `float` | Fraction of CLASS_B plans |
| `built_at` | `datetime` | Statistics generation timestamp |

---

## Enumerations

### `StudyType`
```python
HISTORICAL_REPLAY  REGIME_ANALYSIS    EDGE_VALIDATION    PATTERN_MINING
DNA_DISCOVERY      SECTOR_RESEARCH    CROSS_VALIDATION   META_LEARNING
FEATURE_IMPORTANCE CUSTOM
```

### `ApprovalClass`
```python
CLASS_A  # routine review
CLASS_B  # explicit Scientific Director approval
```

### `PlanStatus`
```python
DRAFT       # created; not yet dependency-validated
READY       # dependencies resolved; execution-ready
APPROVED    # Scientific Director approved
SUPERSEDED  # a newer plan covers this work
```

### `RiskClass`
```python
LOW    MEDIUM    HIGH
```

---

## Exceptions

| Exception | When raised |
|-----------|-------------|
| `StudyPlannerError` | Base; missing registry for hypothesis lookup |
| `StudyPlanNotFoundError` | plan_id or hypothesis_id not found |

---

## Quick Examples

```python
from autonomous_research import (
    KnowledgeProvider, HypothesisRegistry, GapDetector, StudyPlanner,
    StudyType, GapCategory, GapSeverity, GapStatus, KnowledgeGap,
)
from datetime import datetime

kp     = KnowledgeProvider()
reg    = HypothesisRegistry(kp)
gd     = GapDetector(kp)
sp     = StudyPlanner(kp, hypothesis_registry=reg, gap_detector=gd)

# Create a plan from scratch
plan = sp.create_plan(
    title="Nifty Momentum Edge Q2 2026",
    study_type=StudyType.EDGE_VALIDATION,
    scientific_question="Does Nifty momentum edge persist in TRENDING_UP regime?",
)
print(f"Plan: {plan.plan_id} | {plan.approval_class.value}")

# Create a plan from a gap
gap = KnowledgeGap(
    gap_id="GAP-001",
    category=GapCategory.VALIDATION_GAP,
    ...
)
plan2 = sp.create_from_gap(gap)

# Validate dependencies
issues = sp.validate_dependencies(plan.plan_id)
print("Issues:", issues)  # [] if clean

# Portfolio overview
port = sp.portfolio()
print(f"Total plans: {port.total_plans}")
print(f"CLASS_B plans: {port.class_b_plans}")

# Statistics
stats = sp.statistics()
print(f"Avg knowledge gain: {stats.avg_knowledge_gain:.2f}")
print(f"CLASS_B fraction:   {stats.class_b_fraction:.0%}")
```

```python
# Lenient config for rapid prototyping
cfg = StudyPlannerConfig(
    default_date_lookback_days=126,   # 6 months
    default_min_observations=50,
    class_b_study_types=[],           # no types auto-classified as CLASS_B
    class_b_risk_threshold=RiskClass.HIGH,
)
sp2 = StudyPlanner(kp, config=cfg)
```
