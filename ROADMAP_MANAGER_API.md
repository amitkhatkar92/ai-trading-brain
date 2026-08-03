# RoadmapManager — Public API Reference

**ARS Phase 2B**  
**Module:** `autonomous_research.roadmap_manager`  
**Import:** `from autonomous_research import RoadmapManager`

---

## Class: `RoadmapManager`

Scientific research prioritization engine.

### Constructor

```python
RoadmapManager(
    knowledge_provider:  KnowledgeProvider,
    hypothesis_registry: Optional[HypothesisRegistry]    = None,
    synthesizer:         Optional[CrossStudySynthesizer]  = None,
    gap_detector:        Optional[GapDetector]            = None,
    config:              Optional[RoadmapManagerConfig]   = None,
    state_path:          Optional[Path]                   = None,
)
```

| Parameter | Required | Purpose |
|-----------|----------|---------|
| `knowledge_provider` | ✅ | Source of truth for all knowledge |
| `hypothesis_registry` | Optional | For future KNOWLEDGE_GAP enhanced analysis |
| `synthesizer` | Optional | Reserved for cross-study synthesis queries |
| `gap_detector` | Optional | Used when `build(gaps=None)` is called |
| `config` | Optional | Override default weights and thresholds |
| `state_path` | Optional | Override default `data/ars_roadmap_state.json` |

---

### Methods

#### `build(gaps=None, force=False) → ResearchRoadmap`

Build and cache the research roadmap.

```python
roadmap = rm.build()           # use gap_detector (must be set)
roadmap = rm.build(gaps=gaps)  # use provided list
roadmap = rm.build(force=True) # re-build even if cached
```

- Returns cached roadmap on subsequent calls (unless `force=True`)
- Raises `RoadmapBuildError` if `gaps=None` and no `gap_detector` was set
- Persists first-seen timestamps to `state_path` for debt tracking

#### `list_entries() → List[RoadmapEntry]`

Return all entries sorted by rank (rank=1 = highest priority).
Returns `[]` before first `build()`.

#### `top_priorities(n=None) → List[RoadmapEntry]`

Return the top N entries by priority.
Defaults to `config.default_top_n` (default: 5).

#### `get_next_study() → Optional[RoadmapEntry]`

Return the single highest-priority entry (rank=1).
Returns `None` if no roadmap has been built or roadmap is empty.

#### `portfolio() → ResearchPortfolio`

Return portfolio balance analysis from the last build.
Returns an empty `ResearchPortfolio` before first `build()`.

#### `statistics() → RoadmapStatistics`

Return aggregate statistics from the last build.
Returns a zero-valued `RoadmapStatistics` before first `build()`.

---

## Class: `RoadmapManagerConfig`

All RoadmapManager configuration, with documented defaults.

```python
@dataclass
class RoadmapManagerConfig:
    w_knowledge_gain:        float = 0.30   # weight for knowledge gain score
    w_research_debt:         float = 0.25   # weight for research debt score
    w_scientific_importance: float = 0.25   # weight for scientific importance
    w_cost_efficiency:       float = 0.10   # weight for cost efficiency
    w_urgency:               float = 0.10   # weight for urgency

    debt_half_life_days:     int   = 90     # days for age_debt to reach 1.0

    portfolio_allocation:    Dict[str, float] = {  # target fractions per StudyCategory
        "WINNER_DNA":      0.20,
        "MARKET_REGIMES":  0.25,
        "SECTOR_RESEARCH": 0.15,
        "VALIDATION":      0.20,
        "RISK":            0.10,
        "EXPLORATION":     0.10,
    }

    portfolio_imbalance_threshold: float = 0.10  # flag if > 10% off-target
    default_top_n:                 int   = 5     # default for top_priorities()
```

---

## Data Model Reference

### `ResearchRoadmap`

Top-level output of `build()`.

| Field | Type | Description |
|-------|------|-------------|
| `roadmap_id` | `str` | `RM-{uuid4[:8].upper}` — unique per build |
| `built_at` | `datetime` | Build timestamp |
| `entries` | `List[RoadmapEntry]` | Sorted by rank (rank=1 first) |
| `portfolio` | `ResearchPortfolio` | Balance analysis |
| `statistics` | `RoadmapStatistics` | Aggregate statistics |
| `warnings` | `List[str]` | Build warnings (e.g. empty gaps) |

### `RoadmapEntry`

One prioritized study recommendation.

| Field | Type | Description |
|-------|------|-------------|
| `entry_id` | `str` | `RE-{sha256(gap_id)[:8]}` — deterministic |
| `gap` | `KnowledgeGap` | Source gap (unmodified) |
| `knowledge_gain_estimate` | `KnowledgeGainEstimate` | Full gain analysis |
| `cost_estimate` | `ResearchCostEstimate` | Full cost analysis |
| `debt` | `ResearchDebt` | Full debt analysis |
| `priority_score` | `float` | 0.0–1.0; higher = more urgent |
| `priority_breakdown` | `Dict` | All formula components documented |
| `study_category` | `StudyCategory` | Portfolio bucket |
| `status` | `RoadmapEntryStatus` | PENDING or DEFERRED |
| `rank` | `int` | 1-based; 1 = highest priority |
| `recommended_study_title` | `str` | Human-readable study title |
| `recommended_approach` | `str` | One-line methodology suggestion |
| `created_at` | `datetime` | Build timestamp |

### `KnowledgeGainEstimate`

| Field | Type | Description |
|-------|------|-------------|
| `total_gain` | `float` | 0.0–1.0; final computed gain |
| `scientific_importance` | `float` | From gap severity |
| `evidence_gap_size` | `float` | How much evidence is missing |
| `current_confidence` | `float` | Gap's current confidence level |
| `expected_confidence_improvement` | `float` | Post-study confidence increase |
| `expected_new_findings` | `int` | Estimated number of new findings |
| `coverage_increase` | `float` | Regime/sector coverage added |
| `novelty` | `float` | Unexplored territory score |
| `historical_impact` | `float` | Proxy from `gap.estimated_knowledge_gain` |
| `reuse_potential` | `float` | How broadly findings will be reused |
| `uncertainty_reduction` | `float` | Expected uncertainty removed |
| `breakdown` | `Dict` | All 9 components + weights documented |

### `ResearchCostEstimate`

| Field | Type | Description |
|-------|------|-------------|
| `total_cost` | `float` | 0.0–1.0; higher = more expensive |
| `historical_days_required` | `int` | Required data lookback (days) |
| `replay_duration_estimate_hours` | `float` | Expected compute time |
| `implementation_effort` | `float` | Relative development effort |
| `dependencies` | `List[str]` | Gap/hypothesis IDs to resolve first |
| `risk` | `float` | Execution risk |
| `breakdown` | `Dict` | All components + weights documented |

### `ResearchDebt`

| Field | Type | Description |
|-------|------|-------------|
| `total_debt` | `float` | 0.0–1.0; accumulated urgency |
| `base_debt` | `float` | From severity (CRITICAL=1.00, LOW=0.25) |
| `age_debt` | `float` | Proportional to time since first seen |
| `contradiction_debt` | `float` | +0.30 for CONTRADICTION_GAP |
| `expiry_debt` | `float` | +0.20 for TEMPORAL_GAP |
| `accumulation_rationale` | `str` | Human-readable explanation |
| `breakdown` | `Dict` | All 4 components + weights documented |

### `ResearchPortfolio`

| Field | Type | Description |
|-------|------|-------------|
| `total_entries` | `int` | Total entries in roadmap |
| `allocation` | `Dict[str, int]` | Count per StudyCategory |
| `target_allocation` | `Dict[str, float]` | Configured target fractions |
| `actual_fraction` | `Dict[str, float]` | Actual fractions (sums to 1.0) |
| `balance_score` | `float` | 0.0–1.0; higher = better balanced |
| `imbalanced_categories` | `List[str]` | Categories beyond threshold |
| `recommendations` | `List[str]` | Plain-English rebalancing suggestions |

### `RoadmapStatistics`

| Field | Type | Description |
|-------|------|-------------|
| `total_entries` | `int` | Total entries in roadmap |
| `pending_entries` | `int` | Entries with PENDING status |
| `avg_priority_score` | `float` | Mean priority score |
| `avg_knowledge_gain` | `float` | Mean knowledge gain |
| `avg_cost` | `float` | Mean cost |
| `avg_debt` | `float` | Mean research debt |
| `by_gap_category` | `Dict[str, int]` | Count per GapCategory |
| `by_severity` | `Dict[str, int]` | Count per GapSeverity |
| `by_study_category` | `Dict[str, int]` | Count per StudyCategory |
| `top_priority_entry_id` | `Optional[str]` | entry_id of rank=1 entry |
| `total_research_debt` | `float` | Sum of all debt scores |
| `build_duration_ms` | `float` | Build time in milliseconds |
| `built_at` | `datetime` | Build timestamp |

---

## Enumerations

### `StudyCategory`
```python
WINNER_DNA      = "WINNER_DNA"
MARKET_REGIMES  = "MARKET_REGIMES"
SECTOR_RESEARCH = "SECTOR_RESEARCH"
VALIDATION      = "VALIDATION"
RISK            = "RISK"
EXPLORATION     = "EXPLORATION"
```

### `RoadmapEntryStatus`
```python
PENDING  = "PENDING"   # default for all new entries
DEFERRED = "DEFERRED"  # reserved for future use
```

---

## Exceptions

| Exception | When raised |
|-----------|-------------|
| `RoadmapBuildError` | `build(gaps=None)` without a `gap_detector` |
| `RoadmapManagerError` | Base class; catch for any RoadmapManager error |

---

## Quick Example

```python
from autonomous_research import (
    KnowledgeProvider, GapDetector, RoadmapManager
)

kp  = KnowledgeProvider()
gd  = GapDetector(kp)
rm  = RoadmapManager(kp, gap_detector=gd)

roadmap    = rm.build()
next_study = rm.get_next_study()

print(f"Roadmap {roadmap.roadmap_id}: {len(roadmap.entries)} studies")
print(f"Next: [{next_study.rank}] {next_study.recommended_study_title}")
print(f"  Approach: {next_study.recommended_approach}")
print(f"  Priority: {next_study.priority_score:.3f}")
print(f"  Portfolio balance: {roadmap.portfolio.balance_score:.2%}")

for rec in roadmap.portfolio.recommendations:
    print(f"  → {rec}")
```
