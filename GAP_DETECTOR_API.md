# GAP_DETECTOR_API.md — ARS Phase 2A

## Import

```python
from autonomous_research import (
    GapDetector,
    GapDetectorConfig,
    GapCategory,
    GapSeverity,
    GapStatus,
    KnowledgeGap,
    GapDetectionReport,
    GapStatistics,
    GapDetectorError,
    DetectionError,
)
```

---

## Construction

```python
GapDetector(
    knowledge_provider:  KnowledgeProvider,
    hypothesis_registry: Optional[HypothesisRegistry]  = None,
    synthesizer:         Optional[CrossStudySynthesizer] = None,
    config:              Optional[GapDetectorConfig]   = None,
)
```

All three dependencies are optional.  When omitted:
- Without `hypothesis_registry`: R-GD-09 (KNOWLEDGE_GAP) does not fire.
- Without `synthesizer`: R-GD-02 (EVIDENCE_GAP), R-GD-07 (CONTRADICTION_GAP), and
  R-GD-08 (CONFIDENCE_GAP) do not fire.

---

## Configuration

```python
GapDetectorConfig(
    # R-GD-01 DATA_GAP
    min_study_observations:         int   = 100,

    # R-GD-02 EVIDENCE_GAP
    min_corroborating_studies:       int   = 2,

    # R-GD-03 REGIME_GAP
    known_regimes:                   tuple = ("TREND", "RANGE", "VOLATILE", "BEAR"),
    min_findings_per_regime:         int   = 1,

    # R-GD-04 SECTOR_GAP
    min_sector_observations:         int   = 20,

    # R-GD-05 TEMPORAL_GAP
    max_study_age_days:              int   = 90,

    # R-GD-06 VALIDATION_GAP
    max_edge_unvalidated_days:       int   = 30,

    # R-GD-07 CONTRADICTION_GAP
    contradiction_high_threshold:    float = 0.70,
    contradiction_medium_threshold:  float = 0.40,

    # R-GD-08 CONFIDENCE_GAP
    min_synthesis_confidence:        float = 0.60,
    confidence_critical_threshold:   float = 0.30,
    confidence_high_threshold:       float = 0.45,

    # R-GD-09 KNOWLEDGE_GAP
    max_hypothesis_open_days:        int   = 90,
)
```

---

## Public Methods

### `detect(force: bool = False) → GapDetectionReport`

Run all 10 detection rules.  Returns a `GapDetectionReport`.

- Cached after first call.  Subsequent calls return the same report.
- Pass `force=True` to re-run from scratch (also re-runs `synthesizer.synthesize(force=True)`).
- Thread-safe.

```python
report = gd.detect()
print(f"Total gaps: {report.statistics.total_gaps}")
print(f"Critical:   {report.statistics.critical_count}")
```

---

### `list_all() → List[KnowledgeGap]`

Return all gaps from the last detection run.  Returns `[]` before first `detect()`.

```python
gaps = gd.list_all()
```

---

### `list_open() → List[KnowledgeGap]`

Return gaps with `status == GapStatus.OPEN`.

```python
open_gaps = gd.list_open()
```

---

### `list_by_category(category: GapCategory) → List[KnowledgeGap]`

Return gaps matching a specific category.

```python
regime_gaps = gd.list_by_category(GapCategory.REGIME_GAP)
coverage_gaps = gd.list_by_category(GapCategory.COVERAGE_GAP)
```

---

### `list_by_severity(severity: GapSeverity) → List[KnowledgeGap]`

Return gaps at a specific severity level.

```python
critical = gd.list_by_severity(GapSeverity.CRITICAL)
high     = gd.list_by_severity(GapSeverity.HIGH)
```

---

### `list_by_study(study_id: str) → List[KnowledgeGap]`

Return gaps whose `related_studies` list includes the given `study_id`.

```python
gaps = gd.list_by_study("study002a")
```

---

### `list_by_hypothesis(hypothesis_id: str) → List[KnowledgeGap]`

Return gaps whose `related_hypotheses` list includes the given `hypothesis_id`.

```python
gaps = gd.list_by_hypothesis("H2026-08-001")
```

---

### `statistics() → GapStatistics`

Return aggregate statistics from the last detection run.  Returns zero stats before
first `detect()`.

```python
stats = gd.statistics()
print(stats.total_gaps)
print(stats.by_category)   # Dict[str, int]
print(stats.by_severity)   # Dict[str, int]
print(stats.rules_fired)   # Dict[str, int]  rule_id → count
```

---

## KnowledgeGap Fields

| Field | Type | Description |
|---|---|---|
| `gap_id` | str | Deterministic ID: `G-{cat[:4]}-{rule_id}-{hash[:8]}` |
| `category` | GapCategory | Which of the 10 categories |
| `title` | str | Short human-readable title |
| `description` | str | Full description with evidence context |
| `severity` | GapSeverity | LOW / MEDIUM / HIGH / CRITICAL |
| `severity_rationale` | str | Exact explanation of the severity assignment |
| `confidence` | float | 0.0–1.0: certainty this is a real gap |
| `status` | GapStatus | OPEN (always, from detect()) |
| `supporting_evidence` | List[str] | IDs and descriptors of triggering evidence |
| `related_studies` | List[str] | Relevant study_ids |
| `related_hypotheses` | List[str] | Relevant hypothesis_ids |
| `related_findings` | List[str] | Relevant finding_ids |
| `recommended_action` | str | Plain-English action the SD should take |
| `estimated_knowledge_gain` | float | 0.20 / 0.50 / 0.70 / 0.90 by severity |
| `rule_id` | str | Which rule fired (R-GD-01 through R-GD-10) |
| `rule_parameters` | Dict[str, Any] | Config values active when rule fired |
| `created_at` | datetime | Detection timestamp |

---

## GapDetectionReport Fields

| Field | Type |
|---|---|
| `report_id` | str (`GDR-{hex8}`) |
| `detected_at` | datetime |
| `gaps` | List[KnowledgeGap] |
| `statistics` | GapStatistics |
| `warnings` | List[str] |

Both `GapDetectionReport` and `KnowledgeGap` implement `to_dict()` for JSON serialisation.

---

## GapStatistics Fields

| Field | Type |
|---|---|
| `total_gaps` | int |
| `open_gaps` | int |
| `by_category` | Dict[str, int] |
| `by_severity` | Dict[str, int] |
| `critical_count` | int |
| `high_count` | int |
| `detection_duration_ms` | float |
| `detected_at` | datetime |
| `rules_fired` | Dict[str, int] |

---

## Usage Examples

### Full pipeline

```python
kp  = KnowledgeProvider()
reg = HypothesisRegistry(knowledge_provider=kp)
syn = CrossStudySynthesizer(knowledge_provider=kp, hypothesis_registry=reg)
gd  = GapDetector(kp, reg, syn)

report = gd.detect()

# Print all CRITICAL gaps
for gap in gd.list_by_severity(GapSeverity.CRITICAL):
    print(f"[{gap.rule_id}] {gap.title}")
    print(f"  Rationale: {gap.severity_rationale}")
    print(f"  Evidence:  {gap.supporting_evidence}")
    print(f"  Action:    {gap.recommended_action}")
```

### Custom thresholds

```python
cfg = GapDetectorConfig(
    min_study_observations=500,     # stricter data quality
    max_study_age_days=30,          # fresher knowledge required
    min_corroborating_studies=3,    # higher corroboration bar
)
gd = GapDetector(kp, reg, syn, config=cfg)
report = gd.detect()
```

### Scientific Director integration

```python
def observe_gaps(gd: GapDetector) -> List[KnowledgeGap]:
    """Called by the Scientific Director at the start of each research cycle."""
    report = gd.detect(force=True)    # always refresh
    return report.gaps                 # read-only; SD must not mutate these
```

---

## Exceptions

| Exception | When raised |
|---|---|
| `GapDetectorError` | Base class for all GapDetector exceptions |
| `DetectionError` | Unexpected failure in a detection rule (subclass of GapDetectorError) |

Detection failures in individual rules are caught internally and added to
`GapDetectionReport.warnings`, so a single rule failure never aborts the
entire detection run.

---

## Enumerations

### GapCategory
`DATA_GAP`, `EVIDENCE_GAP`, `REGIME_GAP`, `SECTOR_GAP`, `TEMPORAL_GAP`,
`VALIDATION_GAP`, `CONTRADICTION_GAP`, `CONFIDENCE_GAP`, `KNOWLEDGE_GAP`,
`COVERAGE_GAP`

### GapSeverity
`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`

### GapStatus
`OPEN`, `ACKNOWLEDGED`, `CLOSED`
