# Hypothesis Registry API Reference
## ARS Phase 1.2

**Module:** `autonomous_research.hypothesis_registry.HypothesisRegistry`  
**Import:**
```python
from autonomous_research import HypothesisRegistry, KnowledgeProvider
```

---

## Construction

```python
HypothesisRegistry(
    knowledge_provider: KnowledgeProvider,
    registry_path: Optional[Path] = None,   # default: data/ars_hypothesis_registry.json
)
```

The registry loads its persisted state on construction. If the file does not
exist it starts empty. The `KnowledgeProvider` instance is used to validate
evidence references — it is injected, not owned.

---

## Write Methods

### `create_hypothesis()`

```python
def create_hypothesis(
    title: str,
    research_question: str,
    description: str,
    origin: str,
    priority: HypothesisPriority,
    classification: HypothesisClassification,
    knowledge_gap: str,
    expected_knowledge_gain: str,
    validation_method: str,
    supporting_evidence: Optional[Sequence[EvidenceReference]] = None,
    origin_study: Optional[str] = None,
    created_by: str = "system",
    confidence: float = 0.5,
    required_data: Optional[Dict[str, Any]] = None,
    dependencies: Optional[Sequence[str]] = None,   # other hypothesis IDs
    notes: Optional[Sequence[str]] = None,
) -> ScientificHypothesis
```

Creates and persists a new hypothesis in `PROPOSED` status.

**Raises:**
- `RegistryValidationError` — if `title`, `research_question`, `description`,
  or `knowledge_gap` are empty, or `confidence` is outside [0.0, 1.0]
- `InvalidEvidenceError` — if any evidence reference cannot be resolved

---

### `update_status()`

```python
def update_status(
    hypothesis_id: str,
    new_status: HypothesisStatus,
    actor: str,
    reason: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> ScientificHypothesis
```

Transitions the hypothesis to a new lifecycle status.

**Raises:**
- `HypothesisNotFoundError`
- `InvalidTransitionError` — if the transition is not in `VALID_TRANSITIONS`

---

### `add_evidence()`

```python
def add_evidence(
    hypothesis_id: str,
    evidence: EvidenceReference,
    actor: str = "system",
) -> ScientificHypothesis
```

Attaches a validated evidence reference. Duplicate `evidence_id` is silently
ignored (idempotent). Records a `DecisionEvent`.

**Raises:**
- `HypothesisNotFoundError`
- `InvalidEvidenceError` — if the evidence cannot be resolved in KP (except EXTERNAL type)

---

### `add_note()`

```python
def add_note(
    hypothesis_id: str,
    note: str,
    author: str = "system",
) -> ScientificHypothesis
```

Appends a timestamped note. Notes are append-only.

**Raises:**
- `HypothesisNotFoundError`
- `RegistryValidationError` — if note is empty or whitespace-only

---

### `set_validation_result()`

```python
def set_validation_result(
    hypothesis_id: str,
    result: ValidationResult,
    actor: str = "system",
) -> ScientificHypothesis
```

Records the outcome of a validation study. The hypothesis must be in `RUNNING`
status. Records a `DecisionEvent` with the verdict.

**Raises:**
- `HypothesisNotFoundError`
- `RegistryValidationError` — if status is not `RUNNING`

---

### `update_confidence()`

```python
def update_confidence(
    hypothesis_id: str,
    confidence: float,        # 0.0–1.0
    actor: str,
    reason: str,
) -> ScientificHypothesis
```

Updates the prior confidence estimate. Records a `DecisionEvent` with old/new
confidence in metadata.

**Raises:**
- `HypothesisNotFoundError`
- `RegistryValidationError` — if confidence is outside [0.0, 1.0]

---

### `archive()`

```python
def archive(
    hypothesis_id: str,
    actor: str,
    reason: str,
) -> ScientificHypothesis
```

Convenience wrapper for `update_status(ARCHIVED)`. Validates that the current
status allows archiving.

---

## Read Methods

### `get()`

```python
def get(hypothesis_id: str) -> Optional[ScientificHypothesis]
```

Returns the hypothesis or `None` if not found. No exception.

---

### `get_or_raise()`

```python
def get_or_raise(hypothesis_id: str) -> ScientificHypothesis
```

**Raises:** `HypothesisNotFoundError`

---

### `list_all()`

```python
def list_all() -> List[ScientificHypothesis]
```

All hypotheses ordered by creation date (oldest first).

---

### `list_by_status()`

```python
def list_by_status(status: HypothesisStatus) -> List[ScientificHypothesis]
```

---

### `list_by_priority()`

```python
def list_by_priority(priority: HypothesisPriority) -> List[ScientificHypothesis]
```

---

### `list_by_origin()`

```python
def list_by_origin(origin: str) -> List[ScientificHypothesis]
```

Case-insensitive partial match on the `origin` field.

---

### `list_by_study()`

```python
def list_by_study(study_id: str) -> List[ScientificHypothesis]
```

Returns hypotheses that reference `study_id` in `origin_study` or as a STUDY
evidence reference.

---

### `list_open()`

```python
def list_open() -> List[ScientificHypothesis]
```

All hypotheses with a non-terminal status:
`{PROPOSED, UNDER_REVIEW, APPROVED, PLANNED, RUNNING, VALIDATED}`

---

### `list_confirmed()` / `list_rejected()`

```python
def list_confirmed() -> List[ScientificHypothesis]
def list_rejected() -> List[ScientificHypothesis]
```

---

### `get_evidence_chain()`

```python
def get_evidence_chain(hypothesis_id: str) -> List[EvidenceReference]
```

Returns a copy of all evidence references attached to the hypothesis.

---

### `get_decision_history()`

```python
def get_decision_history(hypothesis_id: str) -> List[DecisionEvent]
```

Returns an isolated copy of the decision history. Mutations to the returned
list do not affect the stored hypothesis.

---

### `search()`

```python
def search(keyword: str) -> List[ScientificHypothesis]
```

Case-insensitive keyword search across `title`, `description`,
`research_question`, `knowledge_gap`, and `notes`.

---

### `statistics()`

```python
def statistics() -> Dict[str, Any]
```

Returns:

```python
{
    "total": int,
    "open": int,
    "confirmed": int,
    "rejected": int,
    "archived": int,
    "by_status": Dict[str, int],
    "by_priority": Dict[str, int],
    "by_classification": Dict[str, int],
    "confirmation_rate": Optional[float],   # None if no tested hypotheses
    "avg_evidence_count": float,
    "registry_version": str,
    "last_updated": str,
}
```

---

## Model Reference

### `ScientificHypothesis` — all fields

| Field | Type | Description |
|---|---|---|
| `hypothesis_id` | `str` | Unique ID, format `H{YYYY}-{MM}-{NNN:03d}` |
| `title` | `str` | Short human-readable title |
| `research_question` | `str` | The precise question being investigated |
| `description` | `str` | Detailed description |
| `origin` | `str` | What triggered this hypothesis |
| `origin_study` | `Optional[str]` | Study ID that first surfaced the gap |
| `created_at` | `datetime` | Creation timestamp |
| `created_by` | `str` | Actor who created it |
| `priority` | `HypothesisPriority` | CRITICAL / HIGH / MEDIUM / LOW / EXPLORATORY |
| `confidence` | `float` | Prior confidence 0.0–1.0 |
| `status` | `HypothesisStatus` | Current lifecycle status |
| `classification` | `HypothesisClassification` | Type of gap/finding |
| `supporting_evidence` | `List[EvidenceReference]` | Validated evidence chain |
| `knowledge_gap` | `str` | What we don't know |
| `expected_knowledge_gain` | `str` | What we'll learn if validated |
| `required_data` | `Dict[str, Any]` | Data requirements for validation |
| `dependencies` | `List[str]` | Other hypothesis IDs this depends on |
| `validation_method` | `str` | How it will be validated |
| `validation_result` | `Optional[ValidationResult]` | Set when RUNNING |
| `decision_history` | `List[DecisionEvent]` | Append-only audit trail |
| `last_reviewed` | `Optional[datetime]` | Last status-change timestamp |
| `notes` | `List[str]` | Append-only timestamped notes |

### `EvidenceReference` fields

| Field | Type |
|---|---|
| `evidence_id` | `str` |
| `evidence_type` | `EvidenceType` |
| `description` | `str` |
| `added_at` | `datetime` |
| `added_by` | `str` |

### `ValidationResult` fields

| Field | Type |
|---|---|
| `validated_at` | `datetime` |
| `validated_by` | `str` |
| `verdict` | `str` — `PASS` / `FAIL` / `INCONCLUSIVE` |
| `findings` | `List[str]` |
| `study_ids` | `List[str]` |
| `metrics` | `Dict[str, Any]` |
| `notes` | `str` |

---

## Enumerations

### `HypothesisStatus`
`PROPOSED | UNDER_REVIEW | APPROVED | PLANNED | RUNNING | VALIDATED | CONFIRMED | REJECTED | ARCHIVED`

### `HypothesisPriority`
`CRITICAL | HIGH | MEDIUM | LOW | EXPLORATORY`

### `HypothesisClassification`
`PERFORMANCE_GAP | COVERAGE_GAP | TEMPORAL_GAP | DEGRADATION | CONTRADICTION | EXPLORATORY | MANUAL`

### `EvidenceType`
`STUDY | FINDING | EDGE | METRIC | CERTIFICATION | STRATEGY | EXTERNAL`

---

## Exception Hierarchy

```
RegistryError
├── HypothesisNotFoundError
├── DuplicateHypothesisError
├── InvalidTransitionError(from_status, to_status)
├── InvalidEvidenceError
└── RegistryValidationError
```

`InvalidTransitionError` includes both the from-status and the full list of
allowed targets in its message.

---

## Full Usage Example

```python
from autonomous_research import (
    KnowledgeProvider, HypothesisRegistry,
    HypothesisStatus, HypothesisPriority, HypothesisClassification,
    EvidenceReference, EvidenceType, ValidationResult,
)
from datetime import datetime

kp  = KnowledgeProvider()
reg = HypothesisRegistry(knowledge_provider=kp)

# 1. Create
h = reg.create_hypothesis(
    title="ATR > 0.029 separates winners in TRENDING_DOWN",
    research_question="Does ATR > 0.029 at entry predict profitable trades in TRENDING_DOWN?",
    description="Stage-3 ranking shows ATR in top-5 features. Hypothesis: threshold at 0.029.",
    origin="study002a stage3_ranking analysis",
    priority=HypothesisPriority.HIGH,
    classification=HypothesisClassification.PERFORMANCE_GAP,
    knowledge_gap="Unknown whether ATR threshold separates winners from losers in TRENDING_DOWN",
    expected_knowledge_gain="Validated ATR threshold for TRENDING_DOWN entry filter",
    validation_method="Walk-forward decision-tree on replay.db, 70/30 OOS split",
    supporting_evidence=[
        EvidenceReference(
            evidence_id="study002a",
            evidence_type=EvidenceType.STUDY,
            description="Source study with stage3 ranking",
            added_at=datetime.now(),
            added_by="scientific_director",
        )
    ],
    origin_study="study002a",
    created_by="scientific_director",
    confidence=0.68,
)

# 2. Lifecycle
reg.update_status(h.hypothesis_id, HypothesisStatus.UNDER_REVIEW,
                  actor="analyst", reason="Ready for review")
reg.update_status(h.hypothesis_id, HypothesisStatus.APPROVED,
                  actor="lead", reason="Approved for scheduling")
reg.update_status(h.hypothesis_id, HypothesisStatus.PLANNED,
                  actor="system", reason="Study scheduled week 2026-W33")
reg.update_status(h.hypothesis_id, HypothesisStatus.RUNNING,
                  actor="system", reason="Walk-forward study started")

# 3. Record result
reg.set_validation_result(h.hypothesis_id, ValidationResult(
    validated_at=datetime.now(),
    validated_by="replay_engine",
    verdict="PASS",
    findings=["ATR > 0.029 confirmed: lift 2.7x over baseline"],
    study_ids=["study003a"],
    metrics={"lift": 2.7, "confidence": 0.74, "n_obs": 94},
    notes="18-week OOS validation, consistent across 3 regimes",
))

reg.update_status(h.hypothesis_id, HypothesisStatus.VALIDATED,
                  actor="system", reason="Study complete")
reg.update_status(h.hypothesis_id, HypothesisStatus.CONFIRMED,
                  actor="analyst", reason="Evidence sufficient for production")

# 4. Query
print(reg.statistics())
print(f"Confirmed: {len(reg.list_confirmed())}")
print(f"Evidence chain: {[e.evidence_id for e in reg.get_evidence_chain(h.hypothesis_id)]}")
```
