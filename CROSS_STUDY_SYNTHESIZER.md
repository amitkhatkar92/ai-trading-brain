# Cross-Study Synthesizer
## ARS Phase 1.3 — Scientific Knowledge Synthesis Engine

**Status:** IMPLEMENTED ✅  
**Module:** `autonomous_research/cross_study_synthesizer.py`  
**Tests:** 40/40 pass  

---

## What This Module Is

The CrossStudySynthesizer is the **scientific literature-review engine** of
IIOS. It reads all completed research studies, all findings, all certifications,
all hypotheses, and all edges — and synthesizes them into coherent, traceable
scientific knowledge.

Its output is **synthesized scientific knowledge**, not document summaries.

The distinction matters: summaries repeat what individual studies say.
Synthesis compares what multiple studies say, identifies where they agree, where
they contradict, how strong the combined evidence is, and what can be concluded
with what confidence.

---

## What This Module Is NOT

The synthesizer has **zero authority over research or production systems**. It
explicitly does not:

| Prohibited action | Why |
|---|---|
| Generate hypotheses | Scientific Director's responsibility |
| Execute research or studies | Replay infrastructure's responsibility |
| Modify hypotheses | HypothesisRegistry is the only writer |
| Modify studies or findings | KnowledgeProvider is read-only |
| Change evidence | Evidence is immutable once recorded |
| Rewrite reports | Reports are source documents |
| Resolve contradictions automatically | Contradictions require human judgment |

Pure analysis only.

---

## Architecture Position

```
ScientificDirector (consumer)
    ↓ reads synthesis reports
CrossStudySynthesizer  ← THIS MODULE
    ↓ reads knowledge (read-only)
KnowledgeProvider
    ↓ reads (optionally)
HypothesisRegistry
    ↓ reads from
data/ stores (SQLite, JSON)
```

---

## Synthesis Process

For every finding group:

```
1. Group findings by (FindingClassification, metric)
2. For each group:
   a. Count source studies
   b. Detect contradictions (same metric, different studies, diverging values)
   c. Count supporting vs contradicting studies
   d. Collect related edges (name match)
   e. Collect related certifications (passed certs)
   f. Collect related knowledge metrics
   g. Collect related hypotheses (via origin_study or evidence references)
   h. Calculate synthesis confidence (documented formula)
   i. Assign SynthesisClassification
   j. Build EvidenceChain (full provenance)
   k. Produce SynthesizedFinding
3. Discover relationships across all knowledge types
4. Build consensus blocks by FindingClassification category
5. Produce SynthesisReport with statistics
```

---

## Classification Rules

Every synthesized conclusion receives exactly one of:

| Classification | Criteria |
|---|---|
| CONFIRMED | conf ≥ 0.85 AND n_supporting ≥ 3 AND n_contradicting = 0 |
| VERIFIED | conf ≥ 0.75 AND n_supporting ≥ 2 AND n_contradicting = 0 |
| SUPPORTED | conf ≥ 0.60 AND n_supporting ≥ 2 AND n_contradicting = 0 |
| PARTIAL | single study (any confidence) OR supporters > contradictors |
| CONTRADICTED | n_contradicting ≥ n_supporting |
| UNRESOLVED | multi-study, none of the above conditions met |
| INSUFFICIENT_EVIDENCE | n_findings = 0 or n_studies = 0 |

---

## Confidence Model

Confidence is calculated from six documented components:

$$
\text{confidence} = \sum_{\text{components}} - \text{contradiction\_penalty}
$$

| Component | Formula | Range |
|---|---|---|
| study_agreement | (n_supporting / n_studies) × 0.50 | 0.00 – 0.50 |
| finding_confidence | avg_per_finding_confidence × 0.20 | 0.00 – 0.20 |
| study_count_bonus | min(0.12, (n_studies − 1) × 0.03) | 0.00 – 0.12 |
| certification_bonus | min(0.10, n_certs × 0.05) | 0.00 – 0.10 |
| regime_diversity | min(0.08, (n_regimes − 1) × 0.04) | 0.00 – 0.08 |
| contradiction_penalty | −min(0.30, n_contradicting × 0.15) | −0.30 – 0.00 |

Maximum possible confidence: 1.00 (capped).  
Zero studies always produces confidence = 0.0.

Every `SynthesizedFinding.confidence_breakdown` records each component's
contribution so the result is always reproducible.

---

## Contradiction Detection

Two findings contradict each other when:

1. They are from **different** studies
2. They cover the **same regime** (or both unspecified)
3. One of:
   - Numeric values have **opposite signs** → `CONFLICTING_DIRECTION`
   - Numeric values diverge by **>40% relative** → `CONFLICTING_VALUES`
   - Lift values have opposite signs → `CONFLICTING_DIRECTION`

Contradictions are **never resolved automatically**. Every `ContradictionRecord`
carries `auto_resolved = False`. The Scientific Director must decide what to do.

---

## Relationship Discovery

The synthesizer discovers six types of relationships automatically:

| Type | Discovery mechanism |
|---|---|
| STUDY_TO_FINDING | Every finding has `study_id` — direct mapping |
| FINDING_TO_FINDING | Two findings from different studies in the same group |
| FINDING_TO_EDGE | Finding metric substring matches edge name or description |
| FINDING_TO_METRIC | `KnowledgeMetric.metric_id` references finding_id |
| HYPOTHESIS_TO_FINDING | Hypothesis.supporting_evidence contains finding_id |
| HYPOTHESIS_TO_STUDY | Hypothesis.origin_study matches a study_id |
| EDGE_TO_CERTIFICATION | Active edges associated with passed certifications |
| STUDY_TO_STUDY | Studies with overlapping date-range context |

All relationships are one-directional and stored with a confidence score.
No inference is made beyond what the data directly supports.

---

## Knowledge Consolidation

Findings with the same `(FindingClassification, metric)` key are merged into a
single `SynthesizedFinding`. The merged record retains:
- All `source_study_ids` (no study is hidden)
- All `source_finding_ids` (no finding is hidden)
- Full `EvidenceChain` linking to every related layer

No information is discarded during consolidation.

---

## Evidence Chain

Every `SynthesizedFinding` carries an `EvidenceChain` with six layers:

```
EvidenceChain
├── root_study_ids      — originating studies
├── finding_ids         — constituent findings
├── edge_ids            — correlated trading edges
├── metric_ids          — correlated knowledge metrics
├── hypothesis_ids      — hypotheses referencing this evidence
└── cert_ids            — relevant certifications
```

`completeness` = fraction of non-empty layers (0.0–1.0).  
A chain with studies + findings + edges + certs has completeness = 0.667 (4/6).

---

## Synthesis Statistics

`statistics()` returns:

| Field | Meaning |
|---|---|
| total_findings_processed | Raw findings ingested from KP |
| total_synthesized_findings | Number of consolidated groups produced |
| total_relationships | Relationships across all types |
| total_contradictions | Contradiction pairs detected |
| by_classification | Count per SynthesisClassification |
| by_finding_type | Count per FindingClassification |
| avg_synthesis_confidence | Mean confidence across all findings |
| edges_correlated | Unique edges appearing in any finding |
| certifications_correlated | Unique certs appearing in any finding |
| synthesis_duration_ms | Wall-clock time for full synthesis |

---

## Performance (observed on current IIOS data)

| Metric | Value |
|---|---|
| Studies processed | 3 |
| Findings processed | 24 |
| Synthesized findings | 6 (groups) |
| Relationships discovered | 55 |
| Synthesis duration | ~22ms |

---

## Four Scientific Accountability Questions

**Q1: Can every synthesized conclusion be traced to original evidence?**

YES. Every `SynthesizedFinding` carries `source_study_ids`, `source_finding_ids`,
and a full `EvidenceChain` with six layers (study → finding → edge → metric →
hypothesis → certification).

**Q2: Can contradictions always be identified?**

YES. `_detect_contradictions()` compares all finding pairs within each group
across different studies. Contradictions are flagged by value divergence (>40%)
or direction conflict (opposite signs). Every `ContradictionRecord` has
`auto_resolved = False`.

**Q3: Can duplicated findings be consolidated without losing provenance?**

YES. Findings with the same `(classification, metric)` key merge into one
`SynthesizedFinding` that retains all `source_study_ids` and
`source_finding_ids`. The `evidence_count` field counts the raw total.

**Q4: Is every synthesized conclusion reproducible?**

YES. Given the same KP data, `synthesize()` always produces identical output
(verified by T-30 idempotency test). The confidence formula is fully documented
in `confidence_breakdown` for every finding — the calculation can be reproduced
independently from the recorded components alone.
