# Synthesis API Reference
## ARS Phase 1.3 — CrossStudySynthesizer

**Module:** `autonomous_research.cross_study_synthesizer.CrossStudySynthesizer`  
**Import:**
```python
from autonomous_research import CrossStudySynthesizer, KnowledgeProvider
```

---

## Construction

```python
CrossStudySynthesizer(
    knowledge_provider: KnowledgeProvider,
    hypothesis_registry: Optional[HypothesisRegistry] = None,
)
```

`knowledge_provider` is required. `hypothesis_registry` is optional — when
provided, hypotheses are correlated against synthesized findings.

The synthesizer is stateless until `synthesize()` is first called.  The result
is then cached in memory.

---

## Primary Method

### `synthesize()`

```python
def synthesize(force: bool = False) -> SynthesisReport
```

Run (or return cached) full synthesis.

- First call: runs the full pipeline (~20ms on current data).
- Subsequent calls: returns cached result.
- `force=True`: discards cache and re-runs from scratch.

Returns a `SynthesisReport` with all findings, relationships, contradictions,
consensus blocks, and statistics.

---

## Query Methods

### `list_synthesized_findings()`

```python
def list_synthesized_findings() -> List[SynthesizedFinding]
```

All synthesized finding groups from the last synthesis run.

---

### `list_relationships()`

```python
def list_relationships() -> List[KnowledgeRelationship]
```

All discovered knowledge relationships across all types.

---

### `list_contradictions()`

```python
def list_contradictions() -> List[ContradictionRecord]
```

All detected contradictions.  `auto_resolved` is always `False`.

---

### `list_supported_hypotheses()`

```python
def list_supported_hypotheses() -> List[str]
```

Hypothesis IDs that appear in at least one synthesized finding's
`related_hypothesis_ids`.  Requires `hypothesis_registry` to return
non-empty results.

---

### `list_unresolved()`

```python
def list_unresolved() -> List[SynthesizedFinding]
```

Findings with classification `UNRESOLVED` or `INSUFFICIENT_EVIDENCE`.

---

### `list_by_classification()`

```python
def list_by_classification(
    classification: SynthesisClassification
) -> List[SynthesizedFinding]
```

Filter findings by synthesis classification.  The union across all
classifications equals `list_synthesized_findings()`.

---

### `get_summary()`

```python
def get_summary() -> str
```

Human-readable text summary of the synthesis results.  Includes study count,
finding count, classification breakdown, top contradictions, and warnings.

---

### `statistics()`

```python
def statistics() -> SynthesisStatistics
```

Aggregate statistics from the last synthesis run.

---

## Model Reference

### `SynthesisReport`

Top-level output of `synthesize()`.

| Field | Type | Description |
|---|---|---|
| `report_id` | `str` | `SYN-{YYYYMMDD}-{HHMMSS}-{6char}` |
| `synthesized_at` | `datetime` | Synthesis timestamp |
| `synthesized_findings` | `List[SynthesizedFinding]` | All synthesized groups |
| `relationships` | `List[KnowledgeRelationship]` | All discovered relationships |
| `contradictions` | `List[ContradictionRecord]` | All detected contradictions |
| `consensus_blocks` | `List[KnowledgeConsensus]` | Consensus by FindingClassification |
| `statistics` | `SynthesisStatistics` | Aggregate statistics |
| `warnings` | `List[str]` | Non-fatal warnings from the run |

---

### `SynthesizedFinding` — all fields

| Field | Type | Description |
|---|---|---|
| `synthesis_id` | `str` | Deterministic `SYN-{CLS}-{hash}` |
| `title` | `str` | Human-readable label |
| `classification` | `SynthesisClassification` | Final synthesis verdict |
| `finding_classification` | `FindingClassification` | KP finding type |
| `metric` | `str` | Feature / metric name |
| `regime` | `Optional[str]` | Single regime (if group is regime-specific) |
| `description` | `str` | Representative description |
| `source_study_ids` | `List[str]` | All contributing studies |
| `source_finding_ids` | `List[str]` | All contributing finding IDs |
| `related_edge_ids` | `List[str]` | Correlated edges |
| `related_hypothesis_ids` | `List[str]` | Correlated hypotheses |
| `related_metric_ids` | `List[str]` | Correlated KnowledgeMetric IDs |
| `related_cert_ids` | `List[str]` | Relevant certifications |
| `synthesis_confidence` | `float` | 0.0–1.0 |
| `confidence_breakdown` | `Dict[str, float]` | Per-component breakdown |
| `evidence_count` | `int` | Raw finding count in group |
| `supporting_study_count` | `int` | Studies supporting the finding |
| `contradicting_study_count` | `int` | Studies contradicting it |
| `regime_coverage` | `List[str]` | All regimes represented |
| `sector_coverage` | `List[str]` | All sectors represented |
| `time_coverage` | `Optional[Dict[str, str]]` | `{"start": ..., "end": ...}` |
| `contradiction_ids` | `List[str]` | IDs of detected contradictions |
| `evidence_chain` | `Optional[EvidenceChain]` | Full provenance chain |
| `synthesized_at` | `datetime` | Synthesis timestamp |

---

### `KnowledgeRelationship`

| Field | Type | Description |
|---|---|---|
| `relationship_id` | `str` | `REL-{type}-{8hash}` |
| `relationship_type` | `RelationshipType` | One of 8 types |
| `from_id` | `str` | Source entity ID |
| `from_type` | `str` | `STUDY \| FINDING \| EDGE \| HYPOTHESIS \| METRIC \| CERTIFICATION` |
| `to_id` | `str` | Target entity ID |
| `to_type` | `str` | Same enum as from_type |
| `description` | `str` | Human-readable description |
| `confidence` | `float` | 0.0–1.0 |
| `discovered_at` | `datetime` | Discovery timestamp |

**Relationship types:**

| Type | Source → Target |
|---|---|
| STUDY_TO_FINDING | Study → Finding it produced |
| FINDING_TO_FINDING | Cross-study findings on same metric |
| FINDING_TO_EDGE | Finding metric overlaps edge name |
| FINDING_TO_METRIC | Finding is source of a KnowledgeMetric |
| HYPOTHESIS_TO_FINDING | Hypothesis cites finding as evidence |
| HYPOTHESIS_TO_STUDY | Hypothesis originated from study |
| EDGE_TO_CERTIFICATION | Active edge associated with certification |
| STUDY_TO_STUDY | Studies with overlapping time context |

---

### `ContradictionRecord`

| Field | Type | Description |
|---|---|---|
| `contradiction_id` | `str` | `CON-{8hash}` |
| `contradiction_type` | `ContradictionType` | One of 5 types |
| `finding_a_id` | `str` | First finding |
| `study_a_id` | `str` | First study |
| `finding_b_id` | `str` | Second finding |
| `study_b_id` | `str` | Second study (always different from study_a) |
| `metric` | `str` | The metric on which they contradict |
| `value_a` | `Any` | Value from study A |
| `value_b` | `Any` | Value from study B |
| `description` | `str` | Human-readable explanation |
| `severity` | `float` | 0.0–1.0 |
| `auto_resolved` | `bool` | Always `False` |
| `detected_at` | `datetime` | Detection timestamp |

**Contradiction types:**

| Type | Trigger |
|---|---|
| CONFLICTING_VALUES | Same metric, values diverge >40% relative |
| CONFLICTING_DIRECTION | Same metric, opposite signs |
| CONFLICTING_REGIME | Same regime, incompatible conclusions |
| CONFLICTING_FINDINGS | Qualitatively incompatible findings |
| CONFLICTING_METRIC | Same metric_id, different numeric values |

---

### `EvidenceChain`

| Field | Type | Description |
|---|---|---|
| `chain_id` | `str` | `CHN-{8hash}` |
| `root_study_ids` | `List[str]` | Originating studies |
| `finding_ids` | `List[str]` | All constituent findings |
| `edge_ids` | `List[str]` | Correlated edges |
| `metric_ids` | `List[str]` | Correlated metrics |
| `hypothesis_ids` | `List[str]` | Correlated hypotheses |
| `cert_ids` | `List[str]` | Relevant certifications |
| `description` | `str` | Human-readable chain summary |
| `completeness` | `float` | Fraction of non-empty layers (0.0–1.0) |

---

### `SynthesisClassification` enum

| Value | Meaning |
|---|---|
| `CONFIRMED` | ≥3 studies, conf≥0.85, zero contradictions |
| `VERIFIED` | ≥2 studies, conf≥0.75, zero contradictions |
| `SUPPORTED` | ≥2 studies, conf≥0.60, zero contradictions |
| `PARTIAL` | Single source or supporters > contradictors |
| `CONTRADICTED` | Contradictors ≥ supporters |
| `UNRESOLVED` | Multi-study, inconclusive |
| `INSUFFICIENT_EVIDENCE` | Zero studies or zero findings |

---

### `SynthesisStatistics`

```python
SynthesisStatistics(
    total_findings_processed: int,
    total_synthesized_findings: int,
    total_relationships: int,
    total_contradictions: int,
    by_classification: Dict[str, int],
    by_finding_type: Dict[str, int],
    avg_synthesis_confidence: float,
    avg_evidence_count: float,
    studies_processed: int,
    edges_correlated: int,
    hypotheses_correlated: int,
    certifications_correlated: int,
    metrics_correlated: int,
    synthesis_duration_ms: float,
    synthesized_at: datetime,
)
```

---

## Full Usage Example

```python
from autonomous_research import (
    KnowledgeProvider, HypothesisRegistry, CrossStudySynthesizer,
)
from autonomous_research.synthesis_models import SynthesisClassification

kp  = KnowledgeProvider()
reg = HypothesisRegistry(knowledge_provider=kp)
syn = CrossStudySynthesizer(knowledge_provider=kp, hypothesis_registry=reg)

# Run synthesis
report = syn.synthesize()

# Print summary
print(syn.get_summary())

# All findings by classification
confirmed = syn.list_by_classification(SynthesisClassification.CONFIRMED)
partial   = syn.list_by_classification(SynthesisClassification.PARTIAL)
print(f"Confirmed: {len(confirmed)}, Partial: {len(partial)}")

# Contradictions (never auto-resolved)
for c in syn.list_contradictions():
    print(f"CONTRADICTION: {c.metric} — {c.description}")
    assert c.auto_resolved is False

# Evidence chain for first finding
if report.synthesized_findings:
    sf = report.synthesized_findings[0]
    chain = sf.evidence_chain
    print(f"Evidence chain completeness: {chain.completeness:.0%}")
    print(f"  Studies:  {chain.root_study_ids}")
    print(f"  Findings: {chain.finding_ids}")
    print(f"  Edges:    {chain.edge_ids}")

# Supported hypotheses (requires hypothesis_registry)
hyp_ids = syn.list_supported_hypotheses()
print(f"Supported hypotheses: {hyp_ids}")

# Statistics
stats = syn.statistics()
print(f"Synthesis took {stats.synthesis_duration_ms:.1f}ms")
print(f"Classification breakdown: {stats.by_classification}")

# Force refresh
report_v2 = syn.synthesize(force=True)
assert report_v2.report_id != report.report_id   # new run, new ID
```
