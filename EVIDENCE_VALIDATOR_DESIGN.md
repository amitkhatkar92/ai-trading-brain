# EvidenceValidator — Design Document

**ARS Phase 2C**  
**Module:** `autonomous_research/evidence_validator.py`  
**Status:** Complete (61/61 tests passing)

---

## 1. Purpose

EvidenceValidator is the independent scientific quality assurance layer of ARS.

Before any research recommendation, synthesized finding, hypothesis confirmation,
or roadmap proposal can be accepted by the Scientific Director, it must pass
through EvidenceValidator.

EvidenceValidator does **not** create knowledge.  It validates knowledge quality.

Every validation decision is fully traceable: every input, every rule evaluated,
every piece of evidence consulted, every gate result, the composite score, and
the final outcome are recorded and returnable.

The Scientific Director can trust validated outputs without rechecking evidence.
Every failed gate is explained in plain English.  Every decision can be reproduced.

---

## 2. Architecture

```
EvidenceValidator
    │
    ├── reads from: KnowledgeProvider (studies, findings, edges, certifications)
    ├── reads from: CrossStudySynthesizer (synthesized findings, contradictions)
    ├── reads from: HypothesisRegistry (hypothesis evidence)
    ├── reads from: RoadmapManager (optional, for context)
    │
    ├── validate_finding(finding_id)      → EvidenceValidation
    ├── validate_hypothesis(hypothesis_id) → EvidenceValidation
    ├── validate_roadmap_entry(entry)      → EvidenceValidation
    │
    ├── statistics()      → ValidationStatistics
    └── latest_results()  → List[EvidenceValidation]
```

**Read-only contract:** EvidenceValidator never modifies any knowledge store,
hypothesis, roadmap entry, or finding.  The only side-effect is appending to
an in-memory history list.

---

## 3. Ten Quality Gates

Each gate is evaluated independently and contributes to the composite quality
score.  All thresholds are configurable via `EvidenceValidatorConfig`.  No
threshold is hardcoded.

| Gate ID  | Name | What It Measures | Critical by Default |
|----------|------|-----------------|---------------------|
| G-EV-01  | Sample Size | `n_observations ≥ min_observations` | No |
| G-EV-02  | Replication | independent studies ≥ min_corroborating_studies | No |
| G-EV-03  | Temporal Coverage | date span ≥ min_temporal_coverage_days | No |
| G-EV-04  | Regime Coverage | distinct regimes ≥ min_regime_count | No |
| G-EV-05  | Sector Coverage | distinct sectors ≥ min_sector_diversity | No |
| G-EV-06  | Walk-Forward Consistency | wf_consistency ≥ min_walk_forward_pass_rate | No |
| G-EV-07  | Out-of-Sample Validation | oos_win_rate ≥ min_oos_win_rate | No |
| G-EV-08  | Contradiction Check | contradiction_ratio ≤ max_contradiction_ratio | **Yes** |
| G-EV-09  | Certification Status | passed_certs ≥ min_certification_count | No |
| G-EV-10  | Evidence Freshness | days_old ≤ max_evidence_staleness_days | No |

### Gate Statuses

| Status | Meaning | Score Contribution |
|--------|---------|-------------------|
| PASSED | Condition met | Full gate weight |
| FAILED | Condition not met | Zero weight |
| SKIPPED | Applicable but data unavailable | Half gate weight (neutral) |
| INAPPLICABLE | Gate not relevant for this subject type | Excluded from score |

---

## 4. Quality Score Formula

```
applicable_gates = [g for g in gates if g.status != INAPPLICABLE]
earned  = sum(weight for PASSED) + sum(weight × 0.5 for SKIPPED)
total   = sum(weight for PASSED + FAILED + SKIPPED)
score   = earned / total   (0.0 if total == 0)
```

SKIPPED gates receive half credit because the absence of data is not evidence
of failure — but it is also not evidence of success.

---

## 5. Outcome Determination

```
if any critical gate FAILED:
    → FAILED ("critical gate failure: <name>")

elif score ≥ passed_threshold (default 0.80):
    → PASSED

elif score ≥ passed_with_obs_threshold (default 0.60):
    → PASSED_WITH_OBSERVATIONS (observations list populated)

else:
    → FAILED ("quality score below minimum threshold")
```

Default thresholds:
- `passed_threshold = 0.80`
- `passed_with_obs_threshold = 0.60`

---

## 6. Subject-Type Gate Applicability

| Gate | Finding | Hypothesis | RoadmapEntry |
|------|---------|------------|--------------|
| G-EV-01 Sample Size | ✓ | ✓ | ✓ |
| G-EV-02 Replication | ✓ | ✓ | ✓ |
| G-EV-03 Temporal | ✓ | ✓ | ✓ |
| G-EV-04 Regime | ✓ | ✓ | ✓ |
| G-EV-05 Sector | ✓ | ✓ | ✓ |
| G-EV-06 Walk-Forward | ✓ | ✓ | INAPPLICABLE |
| G-EV-07 OOS | ✓ | ✓ | INAPPLICABLE |
| G-EV-08 Contradiction | ✓ | ✓ | ✓ (special logic for CONTRADICTION_GAP) |
| G-EV-09 Certification | ✓ | ✓ | ✓ |
| G-EV-10 Freshness | ✓ | ✓ | ✓ (gap creation date) |

---

## 7. CONTRADICTION_GAP Special Logic

For a `RoadmapEntry` with `gap.category == CONTRADICTION_GAP`:

The gap _documents_ an existing contradiction.  The contradiction gate (G-EV-08)
checks whether the contradiction is _sufficiently documented_ (not whether it
exists):

```
if len(gap.supporting_evidence) ≥ 2:
    contradiction_ratio = 0.0   → G-EV-08 PASSES
else:
    contradiction_ratio = 1.0   → G-EV-08 FAILS (critical)
```

This correctly flags under-evidenced contradiction claims while passing
well-documented ones.

---

## 8. Traceability Contract

Every `EvidenceValidation` record contains:

| Field | What It Records |
|-------|----------------|
| `subject_type` + `subject_id` | What was validated |
| `subject_summary` | One-line description |
| `rules_evaluated` | Gate IDs that were applied (non-INAPPLICABLE) |
| `evidence_used` | IDs of all studies / findings / certs consulted |
| `gate_results` | One `GateResult` per gate, with actual value, threshold, explanation |
| `quality_score.breakdown` | All formula components documented |
| `outcome` | PASSED / PASSED_WITH_OBSERVATIONS / FAILED |
| `outcome_explanation` | Full explanation of the decision |
| `observations` | Non-empty for PASSED_WITH_OBSERVATIONS |
| `validated_at` | Timestamp |

No question from the Scientific Director about a validation decision can go
unanswered from the EvidenceValidation record alone.

---

## 9. Determinism

`validation_id` is deterministic: `EV-{type_prefix}-{sha256(subject_id)[:8]}`.
Same subject → same validation_id across runs.

Gate threshold comparisons use Python float arithmetic.  Within a single run
on unchanged data, gate statuses are deterministic.

---

## 10. Thread Safety

All writes to `self._history` are protected by `threading.Lock()`.
Concurrent calls to `validate_finding()`, `validate_hypothesis()`,
`validate_roadmap_entry()`, `statistics()`, and `latest_results()` are safe.

---

## 11. Final Questions

**1. Can every validation decision be reproduced?**
Yes — the `EvidenceValidation` record contains all inputs, evidence, gate
results, score formula components, and the decision rationale.

**2. Can every failed gate be explained?**
Yes — `GateResult.explanation` provides a human-readable sentence including
actual value, threshold, and pass/fail status for every gate.

**3. Does EvidenceValidator duplicate any existing capability?**
No.  KnowledgeProvider reads data.  CrossStudySynthesizer synthesizes across
studies.  GapDetector identifies knowledge gaps.  RoadmapManager prioritizes
gaps.  EvidenceValidator is the quality gate layer — it verifies that evidence
meets scientific standards before influencing future decisions.  This is a
distinct responsibility.

**4. Can Scientific Director trust validated outputs without rechecking evidence?**
Yes — that is the precise design goal.  A PASSED validation means all 10 quality
gates evaluated the available evidence and the composite score exceeded the
`passed_threshold`.  The record contains every piece of evidence that was
consulted.
