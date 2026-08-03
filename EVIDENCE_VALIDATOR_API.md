# EvidenceValidator — Public API Reference

**ARS Phase 2C**  
**Module:** `autonomous_research.evidence_validator`  
**Import:** `from autonomous_research import EvidenceValidator`

---

## Class: `EvidenceValidator`

Scientific evidence quality gate engine.

### Constructor

```python
EvidenceValidator(
    knowledge_provider:  KnowledgeProvider,
    hypothesis_registry: Optional[HypothesisRegistry]    = None,
    synthesizer:         Optional[CrossStudySynthesizer]  = None,
    gap_detector:        Optional[GapDetector]            = None,
    roadmap_manager:     Optional[RoadmapManager]         = None,
    config:              Optional[EvidenceValidatorConfig] = None,
)
```

| Parameter | Required | Purpose |
|-----------|----------|---------|
| `knowledge_provider` | ✅ | Source of studies, findings, edges, certifications |
| `hypothesis_registry` | Optional | Required for `validate_hypothesis()` |
| `synthesizer` | Optional | Enables replication count and contradiction ratio via synthesis |
| `gap_detector` | Optional | Reserved for future gap-specific validation |
| `roadmap_manager` | Optional | Reserved for roadmap context |
| `config` | Optional | Override default thresholds and weights |

---

### Methods

#### `validate(subject_id, subject_type="finding") → EvidenceValidation`

Generic dispatcher.

```python
result = ev.validate(finding_id, subject_type="finding")
result = ev.validate(hypothesis_id, subject_type="hypothesis")
```

- `subject_type="finding"` → calls `validate_finding()`
- `subject_type="hypothesis"` → calls `validate_hypothesis()`
- For roadmap entries: use `validate_roadmap_entry(entry)` directly
- Raises `EvidenceValidatorError` for unknown subject_type

#### `validate_finding(finding_id: str) → EvidenceValidation`

Validate evidence quality of a raw `Finding` from KnowledgeProvider.

- All 10 gates evaluated
- G-EV-06 / G-EV-07 are SKIPPED if no correlated edge with metrics is found
- Contradiction ratio computed from CrossStudySynthesizer if available; otherwise
  uses direct `ContradictionRecord` count

Raises `ValidationSubjectNotFoundError` if finding_id is not in KP.

#### `validate_hypothesis(hypothesis_id: str) → EvidenceValidation`

Validate the evidence quality supporting a `ScientificHypothesis`.

- Requires `hypothesis_registry` at construction time
- Sample size from supporting STUDY evidence references
- Replication = number of supporting studies
- Contradiction ratio from synthesis contradictions involving supporting findings,
  or `max(0, 1 - hypothesis.confidence)` as a proxy if no synthesizer

Raises `EvidenceValidatorError` if no registry was provided.  
Raises `ValidationSubjectNotFoundError` if hypothesis_id is not found.

#### `validate_roadmap_entry(entry: RoadmapEntry) → EvidenceValidation`

Validate the evidence behind a `RoadmapEntry` recommendation.

- G-EV-06 (Walk-Forward) and G-EV-07 (OOS) are INAPPLICABLE
- Special G-EV-08 logic for CONTRADICTION_GAP entries (see Design doc §7)
- Freshness based on gap creation date

#### `statistics() → ValidationStatistics`

Return aggregate statistics across all validations in this session.

Returns a `ValidationStatistics` with zero counts if no validations have
been performed.

#### `latest_results(n=10) → List[EvidenceValidation]`

Return the N most recent validation results, newest first.

---

## Class: `EvidenceValidatorConfig`

All thresholds and weights, configurable with no hardcoded values.

```python
@dataclass
class EvidenceValidatorConfig:
    # G-EV-01: minimum observation count
    min_observations: int = 100

    # G-EV-02: minimum independent corroborating studies
    min_corroborating_studies: int = 2

    # G-EV-03: minimum temporal span (days)
    min_temporal_coverage_days: int = 90

    # G-EV-04: minimum distinct market regimes
    min_regime_count: int = 2

    # G-EV-05: minimum distinct sectors
    min_sector_diversity: int = 2

    # G-EV-06: minimum walk-forward consistency (0–1)
    min_walk_forward_pass_rate: float = 0.60

    # G-EV-07: minimum OOS win rate (0–1)
    min_oos_win_rate: float = 0.55

    # G-EV-08: maximum contradiction fraction (CRITICAL gate)
    max_contradiction_ratio: float = 0.30

    # G-EV-09: minimum passed certifications
    min_certification_count: int = 1

    # G-EV-10: maximum evidence age (days)
    max_evidence_staleness_days: int = 180

    # Outcome thresholds
    passed_threshold:          float = 0.80
    passed_with_obs_threshold: float = 0.60

    # Gate weights (relative; normalized internally)
    gate_weights: Dict[str, float] = {
        "G-EV-01": 1.0, "G-EV-02": 1.5, "G-EV-03": 1.0,
        "G-EV-04": 1.0, "G-EV-05": 0.5, "G-EV-06": 1.5,
        "G-EV-07": 1.0, "G-EV-08": 2.0, "G-EV-09": 1.0,
        "G-EV-10": 1.0,
    }

    # Critical gates: any FAILED critical gate forces FAILED outcome
    critical_gates: List[str] = ["G-EV-08"]
```

---

## Data Model Reference

### `EvidenceValidation`

Primary output of all validate_*() methods.

| Field | Type | Description |
|-------|------|-------------|
| `validation_id` | `str` | `EV-{F\|H\|R}-{sha256[:8]}` — deterministic |
| `subject_type` | `str` | `"finding"`, `"hypothesis"`, `"roadmap_entry"` |
| `subject_id` | `str` | ID of the validated subject |
| `subject_summary` | `str` | One-line description |
| `validated_at` | `datetime` | Validation timestamp |
| `gate_results` | `List[GateResult]` | 10 gate results (always) |
| `quality_score` | `EvidenceQualityScore` | Composite score with breakdown |
| `outcome` | `ValidationOutcome` | PASSED / PASSED_WITH_OBSERVATIONS / FAILED |
| `outcome_explanation` | `str` | Full explanation of decision |
| `observations` | `List[str]` | Non-empty for PASSED_WITH_OBSERVATIONS |
| `evidence_used` | `List[str]` | IDs of evidence consulted |
| `rules_evaluated` | `List[str]` | Gate IDs evaluated (non-INAPPLICABLE) |
| `validator_version` | `str` | `"1.0"` |

### `GateResult`

One quality gate evaluation.

| Field | Type | Description |
|-------|------|-------------|
| `gate_id` | `str` | `"G-EV-01"` through `"G-EV-10"` |
| `name` | `str` | Human-readable gate name |
| `status` | `GateStatus` | PASSED / FAILED / SKIPPED / INAPPLICABLE |
| `actual_value` | `Optional[Any]` | Measured value (None if SKIPPED/INAPPLICABLE) |
| `threshold` | `Optional[Any]` | Required value (None if INAPPLICABLE) |
| `explanation` | `str` | Plain-English reasoning |
| `is_critical` | `bool` | True → one FAILED forces FAILED outcome |
| `weight` | `float` | Contribution weight |

### `EvidenceQualityScore`

Composite quality score.

| Field | Type | Description |
|-------|------|-------------|
| `total` | `float` | 0.0–1.0 composite score |
| `gate_scores` | `Dict[str, float]` | Per-gate contribution |
| `applicable_gates` | `int` | Count of non-INAPPLICABLE gates |
| `passed_gates` | `int` | Count with status PASSED |
| `failed_gates` | `int` | Count with status FAILED |
| `skipped_gates` | `int` | Count with status SKIPPED |
| `breakdown` | `Dict[str, Any]` | All formula components documented |

### `ValidationStatistics`

Session aggregate statistics.

| Field | Type | Description |
|-------|------|-------------|
| `total_validations_run` | `int` | All validations in this session |
| `by_outcome` | `Dict[str, int]` | ValidationOutcome.value → count |
| `by_subject_type` | `Dict[str, int]` | subject_type → count |
| `avg_quality_score` | `float` | Mean quality score |
| `most_failed_gate` | `Optional[str]` | Gate ID most frequently FAILED |
| `most_passed_gate` | `Optional[str]` | Gate ID most frequently PASSED |
| `built_at` | `datetime` | Statistics generation timestamp |

---

## Enumerations

### `ValidationOutcome`
```python
PASSED                   = "PASSED"
PASSED_WITH_OBSERVATIONS = "PASSED_WITH_OBSERVATIONS"
FAILED                   = "FAILED"
```

### `GateStatus`
```python
PASSED       = "PASSED"       # condition met
FAILED       = "FAILED"       # condition not met
SKIPPED      = "SKIPPED"      # applicable, data unavailable
INAPPLICABLE = "INAPPLICABLE" # gate not relevant for subject type
```

---

## Exceptions

| Exception | When raised |
|-----------|-------------|
| `EvidenceValidatorError` | Base; missing registry, unknown subject_type |
| `ValidationSubjectNotFoundError` | finding_id / hypothesis_id not found |

---

## Quick Examples

```python
from autonomous_research import (
    KnowledgeProvider, CrossStudySynthesizer, EvidenceValidator
)

kp  = KnowledgeProvider()
syn = CrossStudySynthesizer(kp)
ev  = EvidenceValidator(kp, synthesizer=syn)

# Validate a finding
result = ev.validate_finding("F-001")
print(f"Outcome: {result.outcome.value}")
print(f"Score:   {result.quality_score.total:.0%}")
for gate in result.gate_results:
    print(f"  [{gate.status.value:12s}] {gate.name}: {gate.explanation}")
for obs in result.observations:
    print(f"  ⚠ {obs}")

# Validate a roadmap entry
from autonomous_research import RoadmapManager, GapDetector
gd    = GapDetector(kp, synthesizer=syn)
rm    = RoadmapManager(kp, gap_detector=gd)
rm.build()
entry = rm.get_next_study()
r     = ev.validate_roadmap_entry(entry)
print(f"Roadmap entry: {r.outcome.value} (score={r.quality_score.total:.0%})")

# Session statistics
stats = ev.statistics()
print(f"Validated: {stats.total_validations_run}")
print(f"Most failed gate: {stats.most_failed_gate}")
```

```python
# Lenient config for early-stage research
lenient = EvidenceValidatorConfig(
    min_observations=50,
    min_corroborating_studies=1,
    min_regime_count=1,
    min_certification_count=0,
    passed_threshold=0.60,
    passed_with_obs_threshold=0.40,
)
ev_lenient = EvidenceValidator(kp, config=lenient)
```
