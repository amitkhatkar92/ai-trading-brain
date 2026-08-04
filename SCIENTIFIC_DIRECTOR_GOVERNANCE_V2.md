# Scientific Director — Knowledge Governance V2

**IIOS Autonomous Research System**
**Document Class:** Constitutional Authority — Appendix B
**Depends on:** SCIENTIFIC_DIRECTOR_CONSTITUTION.md v1.0
**Status:** FROZEN
**Version:** 2.0
**Effective:** 2026-08-04

---

## Overview

This document defines the complete lifecycle of every knowledge artifact in IIOS.
It specifies the exact conditions under which each artifact may be:
- **Promoted** (elevated to a higher confidence/authority tier)
- **Demoted** (downgraded due to contradicting or weakened evidence)
- **Retired** (permanently removed from active institutional knowledge)

These rules are binding on the Scientific Director. No promotion, demotion, or
retirement may occur unless the criteria in this document are satisfied.

---

## Part I — Knowledge Artifact Taxonomy

IIOS maintains six categories of knowledge artifact:

| Artifact | Definition | Owner |
|---|---|---|
| **Hypothesis** | A testable scientific claim about market behaviour | HypothesisRegistry |
| **Finding** | An empirical observation extracted from a completed study | KnowledgeProvider (studies) |
| **Edge** | A consistently profitable asymmetry confirmed across multiple studies | KnowledgeProvider (edges) |
| **Strategy** | An edge expressed as a full trading rule set that has been backtested and certified | StrategyLab + KnowledgeProvider |
| **Pattern** | A recurring market structure identified by the pattern miner | KnowledgeProvider (features/patterns) |
| **Metric** | A calibrated performance indicator with established baseline and thresholds | KnowledgeProvider (metrics) |

All six artifact types are governed by this document. The Scientific Director governs
Hypotheses, Findings, Edges, and Patterns directly. Strategies and Metrics are governed
in coordination with StrategyLab and ControlTower respectively, but the SD holds veto
authority over promotion into institutional knowledge.

---

## Part II — Hypothesis Lifecycle

### 2.1 States

```
DRAFT ──► ACTIVE ──► CONFIRMED
   │          │
   │          └──► REJECTED
   │
   └──► (discarded — never persisted if not accepted)

CONFIRMED ──► ARCHIVED (Class A — when no longer strategic)
REJECTED  ──► ARCHIVED (Class A — after 90-day retention)
CONFIRMED ──► UNDER_REVIEW (Class B — when contradicting evidence arrives)
UNDER_REVIEW ──► CONFIRMED (Class A — if review resolves in hypothesis's favour)
UNDER_REVIEW ──► REJECTED  (Class A — if review refutes hypothesis)
```

### 2.2 DRAFT → ACTIVE

**Conditions (all must be met):**
1. Hypothesis has a clear, falsifiable scientific question.
2. Hypothesis has an expected mechanism (why should this be true?).
3. Hypothesis does not duplicate an existing ACTIVE or CONFIRMED hypothesis (checked
   via HypothesisRegistry.search()).
4. A research path exists: either a RoadmapEntry exists for this hypothesis OR one will
   be created simultaneously.

**Who approves:** Class A — Scientific Director autonomous.

### 2.3 ACTIVE → CONFIRMED

**Conditions (ALL must be met):**

| Gate | Requirement | Source |
|---|---|---|
| Evidence count | ≥ 3 independent evidence pieces | HypothesisRegistry.get_evidence_chain() |
| Quality score | ≥ 0.70 (weighted average across evidence) | EvidenceValidator.validate_hypothesis() |
| Replication count | ≥ 2 independent studies corroborating | ResearchRun records |
| Temporal coverage | ≥ 90 calendar days of data | StudyPlan dataset_requirements |
| Regime coverage | ≥ 2 distinct market regimes represented | KnowledgeProvider.get_regime_history() |
| Validation outcome | PASSED or PASSED_WITH_OBSERVATIONS | EvidenceValidator.validate_hypothesis() |
| Contradiction check | No unresolved contradictions with CONFIRMED hypotheses | CrossStudySynthesizer.list_contradictions() |
| Walk-forward | ≥ 60% of WF windows consistent with hypothesis | ValidationPlan.walk_forward_windows |

**Who approves:** Class A — Scientific Director autonomous if all 8 gates pass.

**Important:** A hypothesis created and immediately confirmed by the same study that
generated it is invalid (conflict of interest). At least one independent corroboration
is required after the originating study.

### 2.4 ACTIVE → REJECTED

**Conditions (any one sufficient):**

1. Refuting evidence: ≥ 2 independent studies that directly contradict the hypothesis
   with quality_score ≥ 0.65.
2. Logical invalidation: the expected mechanism is provably impossible given confirmed
   knowledge.
3. No evidence after 180 days ACTIVE with no study assigned.
4. Explicit rejection by human operator.

**Who approves:** Class A — Scientific Director autonomous. Documents reason in
rejection_note field.

### 2.5 CONFIRMED → UNDER_REVIEW

**Trigger:** CrossStudySynthesizer reports a CONFIRMED hypothesis is contradicted by
new evidence with quality_score ≥ 0.60 from a study completed after the original
confirmation date.

**Who triggers:** Scientific Director (Class A detection; Class B resolution).

**During UNDER_REVIEW:** The hypothesis remains in the knowledge base. Systems that use
its derived edges or strategies are flagged but not suspended. The SD has 30 days to
resolve before human escalation is mandatory.

### 2.6 CONFIRMED → ARCHIVED

**Conditions (all must be met):**
1. Hypothesis has been CONFIRMED for ≥ 90 days.
2. No active study references this hypothesis.
3. No active trades use a strategy derived from this hypothesis (check via StrategyLab).
4. A more specific or comprehensive hypothesis supersedes it (referenced by ID).

**Who approves:** Class A — Scientific Director autonomous.

---

## Part III — Finding Lifecycle

### 3.1 States

```
RAW ──► VALIDATED ──► CERTIFIED ──► ARCHIVED
    │
    └──► CONTRADICTED
```

### 3.2 RAW → VALIDATED

A RAW finding is any observation extracted from a study. It becomes VALIDATED when:

| Gate | Requirement |
|---|---|
| Sample size | ≥ 30 trade observations (statistical minimum) |
| Study quality | Parent study ResearchRun.health = HEALTHY |
| EvidenceValidator | validate_finding() returns PASSED or PASSED_WITH_OBSERVATIONS |

**Who approves:** Class A — Scientific Director autonomous.

### 3.3 VALIDATED → CERTIFIED

A finding achieves CERTIFIED status when it has been independently replicated:

| Gate | Requirement |
|---|---|
| Corroboration | ≥ 2 independent studies both VALIDATED this finding |
| Quality score | Weighted average quality_score ≥ 0.75 |
| Temporal span | ≥ 180 calendar days across all corroborating studies |
| No contradiction | Not listed in CrossStudySynthesizer.list_contradictions() as CONTRADICTED |
| Regime breadth | ≥ 2 distinct regimes across corroborating studies |

**Who approves:** Class A — Scientific Director autonomous.

### 3.4 CERTIFIED → CONTRADICTED

A CERTIFIED finding becomes CONTRADICTED when:
- A subsequent study of equal or higher quality directly refutes it.
- CrossStudySynthesizer classifies it as CONTRADICTED.

**Resolution:** The SD investigates (Class A) and either:
(a) Accepts the contradiction and demotes to CONTRADICTED.
(b) Commissions a cross-validation study (Class A/B depending on risk class).
(c) Proposes human review (Class B if the finding underpins a certified edge).

### 3.5 CERTIFIED → ARCHIVED

**Conditions:** Finding has been superseded by a more precise CERTIFIED finding that
covers the same market phenomenon with higher evidence quality.

**Who approves:** Class B — human confirmation required if the finding underpins a
certified edge or active strategy. Class A otherwise.

---

## Part IV — Edge Lifecycle

### 4.1 States

```
CANDIDATE ──► VALIDATED ──► DEPRECATED
                  │
                  └──► RETIRED (Class B)
```

### 4.2 CANDIDATE → VALIDATED

An edge candidate becomes VALIDATED when it passes the full six-gate research
certification pipeline:

| Gate | Minimum Threshold | How Measured |
|---|---|---|
| Win rate | ≥ 50% | BacktestEngine: total wins / total trades |
| Sharpe ratio | > 0.8 | BacktestEngine: annualised risk-adjusted return |
| Max drawdown | < 15% | BacktestEngine: peak-to-trough on equity curve |
| Walk-forward consistency | ≥ 60% of windows profitable | WalkForwardTest: windows_profitable / total_windows |
| OOS confirmation | Win rate ≥ 50% on reserved OOS period | BacktestEngine: OOS partition |
| Regime robustness | Positive expectancy in ≥ 2 regimes | RegimeRobustnessTest |

**All six gates must pass.** No partial validation. An edge that passes 5/6 gates is
a CANDIDATE — it is not VALIDATED.

**Replication requirement:** Must be validated in ≥ 2 independent study runs conducted
at least 30 calendar days apart.

**Who approves:** Class A — Scientific Director autonomous if all criteria met and
verified by EvidenceValidator.

### 4.3 VALIDATED → DEPRECATED

An edge becomes DEPRECATED (automatically monitored, not immediately removed) when:

| Trigger | Threshold |
|---|---|
| Trailing 30-day win rate | < 40% |
| Trailing 30-day Sharpe | < 0.3 |
| Trailing 30-day max drawdown | > 20% |
| Sustained contradiction | CrossStudySynthesizer classifies edge finding as CONTRADICTED for ≥ 14 consecutive days |

**On DEPRECATED:** The edge is flagged in the knowledge base. The Scientific Director
generates a Class B escalation to the human operator recommending either:
(a) Suspension of associated strategies pending investigation.
(b) Commission of a cross-validation study.
(c) Full retirement.

**Who triggers:** Class A — SD detects automatically. Class B — human decides outcome.

### 4.4 DEPRECATED → RETIRED

An edge may only be RETIRED when:

1. Human operator approves retirement (Class B).
2. No active trades are using a strategy derived from this edge.
3. A study has been commissioned and completed investigating the deprecation.
4. The deprecation cause is understood and documented.

**Who approves:** Class B only.

---

## Part V — Pattern Lifecycle

### 5.1 States

```
DISCOVERED ──► SCREENED ──► VALIDATED ──► ARCHIVED
```

### 5.2 DISCOVERED → SCREENED

A pattern discovered by PatternMiner is promoted to SCREENED when:
- Statistical significance: p-value ≤ 0.05 on discovery dataset.
- Sample size: ≥ 50 occurrences in discovery window.

### 5.3 SCREENED → VALIDATED

| Gate | Requirement |
|---|---|
| OOS confirmation | Pattern observed in ≥ 30 reserved OOS occurrences |
| Regime coverage | Observed in ≥ 2 distinct regimes |
| Recency | ≥ 10 occurrences in trailing 90 days |
| Non-redundancy | Not a near-duplicate of an existing VALIDATED pattern (cosine similarity < 0.85) |

**Who approves:** Class A — Scientific Director autonomous.

---

## Part VI — Replication Requirements (Summary)

| Artifact | Minimum Independent Studies | Minimum Temporal Gap Between Studies | Minimum Regime Coverage |
|---|---|---|---|
| Hypothesis → CONFIRMED | 2 | 30 calendar days | 2 regimes |
| Finding → CERTIFIED | 2 | 30 calendar days | 2 regimes |
| Edge → VALIDATED | 2 | 30 calendar days | 2 regimes |
| Pattern → VALIDATED | 1 (OOS is the replication) | N/A (OOS window) | 2 regimes |
| Strategy → CERTIFIED | 2 backtest periods + 1 OOS | 60 calendar days between backtest periods | 2 regimes |

A single large study split into sub-periods does NOT count as two independent studies.
Independence requires:
1. Different date windows (non-overlapping).
2. Different study runs (separate RC executions).
3. Ideally: different analyst agents or study types producing corroborating evidence.

---

## Part VII — Evidence Thresholds

These thresholds govern EvidenceValidator gate requirements. They apply to all promotion
decisions. Modification requires Class B (human approval).

### 7.1 Statistical Thresholds

| Threshold | Value | Applies to |
|---|---|---|
| Minimum observations (statistical significance) | 30 trades | All artifacts |
| Minimum observations (for CERTIFIED) | 100 trades total across studies | Finding, Edge |
| p-value for significance | ≤ 0.05 | Pattern discovery |
| Effect size (Cohen's d minimum) | ≥ 0.20 | Edge win-rate claims |

### 7.2 Temporal Thresholds

| Threshold | Value | Applies to |
|---|---|---|
| Minimum temporal coverage for CONFIRMED | 90 calendar days | Hypothesis |
| Minimum temporal coverage for CERTIFIED | 180 calendar days | Finding, Edge |
| Recency requirement (pattern) | ≥ 10 occurrences in trailing 90 days | Pattern |
| Staleness threshold | 365 calendar days since last corroboration | All (triggers review) |
| Under-review resolution deadline | 30 days | Hypothesis UNDER_REVIEW |

### 7.3 Quality Score Thresholds

| Threshold | Value | Gate |
|---|---|---|
| Hypothesis CONFIRMED minimum | 0.70 | EvidenceValidator.validate_hypothesis() |
| Finding CERTIFIED minimum | 0.75 | EvidenceValidator.validate_finding() |
| Edge VALIDATED minimum | 0.75 | Composite across all six gates |
| Contradiction trigger | ≥ 0.60 refuting quality | CrossStudySynthesizer detection |

### 7.4 Walk-Forward Thresholds

| Threshold | Value | Applies to |
|---|---|---|
| Walk-forward windows (minimum) | 6 windows | Edge, Strategy |
| Profitable windows (minimum %) | 60% | Edge, Strategy |
| OOS win rate (minimum) | 50% | Edge, Strategy |
| OOS period (minimum length) | 90 calendar days | Edge, Strategy |

### 7.5 Regime Coverage Thresholds

| Threshold | Value | Applies to |
|---|---|---|
| Minimum distinct regimes | 2 | Hypothesis, Finding, Edge, Pattern |
| Preferred regime coverage | 3 (BULL, BEAR, SIDEWAYS) | Edge, Strategy |
| Regime-conditional finding | 1 regime minimum with ≥ 30 occurrences | Finding (regime-scoped) |

---

## Part VIII — Contradiction Resolution Framework

### 8.1 Contradiction Detection

Contradictions are detected by CrossStudySynthesizer when two CERTIFIED/CONFIRMED
artifacts produce opposing conclusions about the same market phenomenon with a relative
divergence ≥ 40%.

CrossStudySynthesizer classifies contradictions into:
- **DIRECT**: Same phenomenon, opposite sign (bullish vs bearish)
- **SCOPE**: Same phenomenon, different regimes (only contradictory if scope is same)
- **TEMPORAL**: Same phenomenon, different time periods (earlier may be stale)
- **MEASUREMENT**: Same phenomenon, different metrics (methodological, not scientific)

### 8.2 Resolution Priority

| Contradiction Type | SD Action | Approval Class |
|---|---|---|
| SCOPE | Add regime-condition to one artifact | Class A |
| TEMPORAL | Retire the older artifact if staleness criteria met | Class A (if stale) / Class B (if not stale) |
| MEASUREMENT | Commission a cross-validation study | Class A/B depending on risk class |
| DIRECT | Escalate to human — cannot be resolved autonomously | Class B mandatory |

### 8.3 During Contradiction

While a DIRECT contradiction is active and unresolved:
- Both conflicting artifacts retain their current status.
- Both are marked with a `contradiction_flag`.
- Systems using derived strategies from either artifact are notified but not halted.
- The SD generates a Class B escalation within 48 hours of detection.

### 8.4 Resolution Outcomes

A contradiction is resolved when the human operator approves one of:
(a) **Retire one artifact** — the weaker evidence is retired; the stronger stands.
(b) **Restrict scope** — both artifacts are valid but apply to different regimes/conditions.
(c) **Commission resolution study** — a CROSS_VALIDATION study is approved and executed.
(d) **Accept conditional truth** — both artifacts are accepted as regime-conditional.

---

## Part IX — Governance Change Protocol

### 9.1 Threshold Modification

Evidence thresholds (Part VII) may only be changed when:
1. ≥ 30 promotion decisions have been made under current thresholds.
2. Statistical analysis shows thresholds are systematically too permissive or too strict.
3. A proposal document is written with data-backed justification.
4. Human operator approves (Class B).

### 9.2 New Artifact Type

A new artifact type may only be added when:
1. A use case exists that none of the six current types can serve.
2. The full lifecycle (states, promotion, demotion, retirement) is defined in this
   document before any implementation begins.
3. Human operator approves the new lifecycle definition.

### 9.3 Version History

| Version | Date | Change |
|---|---|---|
| 1.0 | Pre-2026-08-04 | Original governance document |
| 2.0 | 2026-08-04 | Frozen with full lifecycle definitions, replication requirements, evidence thresholds, contradiction resolution framework |
