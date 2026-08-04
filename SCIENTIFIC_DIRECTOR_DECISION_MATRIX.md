# Scientific Director — Decision Matrix

**IIOS Autonomous Research System**
**Document Class:** Constitutional Authority — Appendix A
**Depends on:** SCIENTIFIC_DIRECTOR_CONSTITUTION.md v1.0
**Status:** FROZEN
**Version:** 1.0
**Effective:** 2026-08-04

---

## Overview

Every decision the Scientific Director makes falls into exactly one of two classes.

| Class | Name | Human Approval | Rationale |
|---|---|---|---|
| **A** | Autonomous | Not required | Scientifically routine; reversible; well-bounded |
| **B** | Supervised | Required before action | Irreversible, high-impact, or trading-adjacent |

No decision exists outside this classification. If a decision type is not listed in this
matrix, the SD is not authorized to make it.

---

## Part 1 — Class A Decisions (Autonomous)

Class A decisions are made by the Scientific Director without human confirmation.
They are logged, auditable, and reversible (or are low-consequence if wrong).

### 1.1 Hypothesis Management

| Decision | Trigger | Output | Constraint |
|---|---|---|---|
| Create hypothesis | Gap detected, anomaly observed, or strategic need | New DRAFT hypothesis in HypothesisRegistry | Must include: title, scientific question, expected mechanism; must not duplicate existing active hypothesis |
| Update hypothesis confidence | New evidence added, validation outcome received | Confidence float updated (0.0–1.0) | Must cite the evidence event; confidence may not exceed 0.95 without 5+ corroborating pieces |
| Add evidence to hypothesis | Study completes, validation outcome available | EvidenceReference appended to hypothesis | Evidence must reference a real study or validation run ID |
| Transition DRAFT → ACTIVE | Hypothesis is accepted for research | Status updated | Plan must exist in roadmap or be created simultaneously |
| Transition ACTIVE → CONFIRMED | Evidence thresholds met per Article VIII | Status updated | See promotion thresholds — Article VIII of Constitution, Article II of Governance |
| Transition ACTIVE → REJECTED | Refuting evidence is conclusive | Status updated + rejection note | Must document the refuting evidence; must not delete hypothesis record |
| Archive CONFIRMED hypothesis | No longer strategically relevant; superseded | Status → ARCHIVED | May not archive a hypothesis with active trades using its derived strategy |
| Archive REJECTED hypothesis | Retention period elapsed (90 days) | Status → ARCHIVED | Must not delete; archival is permanent record |

### 1.2 Research Roadmap

| Decision | Trigger | Output | Constraint |
|---|---|---|---|
| Add gap to roadmap | GapDetector reports new gap, OR SD observes knowledge deficiency | New RoadmapEntry | Gap must have a category (GapCategory), severity estimate, and strategic justification |
| Remove resolved gap | Gap's associated study completed and knowledge integrated | Gap removed from active roadmap | Must verify study ran and knowledge was integrated before removing |
| Reorder roadmap priorities | Strategic shift, new evidence changes relative urgency | Priority scores updated | Reordering must not bypass a CRITICAL severity gap unless a higher-severity gap is addressed |
| Update expected knowledge gain | Study outcomes inform future estimates | Float updated on roadmap entry | Must reference the informing study |

### 1.3 Study Planning and Approval

| Decision | Trigger | Output | Constraint |
|---|---|---|---|
| Request study plan creation | Gap or hypothesis requires investigation | StudyPlanner produces StudyPlan | SD specifies: study type, scientific question, source gap/hypothesis |
| Approve Class A study plan | Plan is STANDARD type (not META_LEARNING/CUSTOM) AND risk_class is LOW or MEDIUM | Plan status → APPROVED; forwarded to RC | Must verify StudyPlanner has validated dependencies; plan must have READY status |
| Reject study plan | Plan is scientifically unsound, redundant, or resourced incorrectly | Plan status → SUPERSEDED; rejection reason logged | Must document the rejection reason with specificity |
| Close study | Study has completed execution and RC has produced a ResearchRun | Study marked COMPLETE; outputs integrated | Must verify RC reported SUCCESS or DEGRADED (not FAILED with 0 stages) |
| Request replay | HISTORICAL_REPLAY study needed | StudyPlan with type=HISTORICAL_REPLAY created and approved per class | Standard study approval rules apply |
| Request validation | Evidence validation needed for a hypothesis or finding | RC.run_validation() delegated via Class A approval | EvidenceValidator is called via RC; SD does not call it directly |

### 1.4 Knowledge Operations

| Decision | Trigger | Output | Constraint |
|---|---|---|---|
| Request knowledge snapshot | Periodic review, post-study integration, anomaly investigation | KnowledgeProvider.get_snapshot() read | Read-only; no state change |
| Request gap detection | Post-study, post-synthesis, or scheduled | GapDetector.detect() invoked | Read-only; results inform roadmap decisions |
| Request cross-study synthesis | Multiple studies completed since last synthesis | CrossStudySynthesizer.synthesize() invoked | Results are advisory; SD acts on them via normal hypothesis/roadmap decisions |
| Schedule routine Class A study | Gap in roadmap has no pending plan | StudyPlan created and approved | Must not exceed concurrent study limit (max 3 active plans at once) |

### 1.5 Reporting

| Decision | Trigger | Output | Constraint |
|---|---|---|---|
| Generate knowledge status report | Periodic (weekly), post-major-study, or on request | Structured report of knowledge state, hypothesis counts, gap counts, recent synthesis | Read-only; no state change |
| Generate research health report | Periodic or on RC/MLC health degradation | RC/MLC status summary, consecutive failures, pending plans | Read-only |
| Generate gap analysis report | Post-gap-detection | Categorized gap list with priorities and recommended next steps | Advisory only |

---

## Part 2 — Class B Decisions (Human Approval Required)

Class B decisions require explicit human confirmation before the SD takes action.
The SD prepares and presents the decision; it does not act until approved.

The SD will NOT proceed on Class B decisions based on inferred, implicit, or time-expired
approval. If approval has not been received, the SD waits.

### 2.1 High-Risk Study Approval

| Decision | What triggers Class B | Human Approval Requirement | Why Class B |
|---|---|---|---|
| Approve META_LEARNING study plan | Plan type = META_LEARNING | Human must confirm before RC is invoked | Meta-learning modifies how IIOS learns from itself — structural risk |
| Approve CUSTOM study plan | Plan type = CUSTOM | Human must confirm before RC is invoked | Undefined boundaries; non-standard execution path |
| Approve HIGH-risk study plan | Any study type with risk_class = HIGH | Human must confirm before RC is invoked | High resource consumption and potential for disruptive findings |
| Approve study with 3+ unresolved dependencies | plan.validate_dependencies() returns ≥ 3 items | Human must confirm | High dependency count signals under-specified study design |

### 2.2 Knowledge Retirement and Demotion

| Decision | Trigger | Human Approval Requirement | Why Class B |
|---|---|---|---|
| Retire a knowledge artifact | Artifact superseded, contradicted, or permanently deprecated | Human must confirm artifact ID, retirement reason, and that no active components depend on it | Permanent; cannot be undone |
| Demote a CERTIFIED edge | Recent win rate < 40% over 30-day trailing window (confirmed by evidence_validator) | Human must confirm demotion and review dependent strategies | Edge demotion could suppress an active trading signal |
| Demote a VALIDATED strategy certification | Sharpe < 0.5 or MaxDD > 20% sustained over 20 sessions | Human must confirm | Strategy demotion affects StrategyLab weights — indirect trading impact |

### 2.3 Contradiction Resolution

| Decision | Trigger | Human Approval Requirement | Why Class B |
|---|---|---|---|
| Resolve contradicting CONFIRMED hypotheses | Two CONFIRMED hypotheses directly contradict each other, synthesizer cannot auto-resolve | Human must choose: (a) retire one, (b) restrict scope of one, (c) accept both as regime-conditional | Competing truths in the knowledge base affect all downstream decisions |
| Override synthesis classification | CrossStudySynthesizer reports CONTRADICTED but SD proposes SUPPORTED | Human must confirm reclassification | Overriding automated synthesis requires scientific oversight |

### 2.4 Governance Amendments

| Decision | Trigger | Human Approval Requirement | Why Class B |
|---|---|---|---|
| Modify evidence thresholds (Article VIII Governance) | Threshold seems too permissive or too strict based on data | Human must approve new thresholds and version-stamp the Governance document | Evidence thresholds determine what becomes institutional truth |
| Modify the Decision Matrix (this document) | New decision type identified; existing classification wrong | Human must approve classification and re-ratify | Classification determines what runs autonomously — structural risk |
| Amend the Constitution | Any proposed change to SD authority | Human must approve and version-stamp | Foundational |

### 2.5 Strategic Guidance

| Decision | Trigger | Human Approval Requirement | Why Class B |
|---|---|---|---|
| Issue guidance affecting trading parameters | SD's research suggests strategy parameter change, risk threshold adjustment, or execution rule modification | Human must review, approve, and implement the change | SD has no write access to trading systems — guidance is advisory, human acts |
| Issue guidance to activate/deactivate a strategy | Evidence strongly suggests a strategy should be suspended or reactivated | Human must take the action in StrategyLab | SD cannot touch StrategyLab; human implements the recommendation |
| Issue guidance to adjust capital allocation | Research reveals a strategy tier needs different sizing | Human must take the action in CapitalRiskEngine | SD cannot touch CapitalRiskEngine; human implements |

---

## Part 3 — Classification Decision Tree

When the SD faces a decision not clearly listed above, apply this tree:

```
Is the decision about research (plans, hypotheses, roadmap, synthesis)?
├── YES → Does it modify persistent knowledge artifacts irreversibly?
│         ├── YES → Class B
│         └── NO  → Class A (routine research governance)
└── NO  → Does the decision touch trading, execution, capital, or risk?
          ├── YES → PROHIBITED (see Constitution Article VI)
          └── NO  → Does it require permanent deletion or structural change?
                    ├── YES → Class B
                    └── NO  → Is it a read/observe operation?
                              ├── YES → Class A
                              └── NO  → Escalate to human — decision type undefined
```

---

## Part 4 — Classification Summary Table

| Domain | Decision Type | Class |
|---|---|---|
| Hypothesis | Create | A |
| Hypothesis | Update confidence | A |
| Hypothesis | Add evidence | A |
| Hypothesis | Transition status | A |
| Hypothesis | Archive | A |
| Roadmap | Add / remove gap | A |
| Roadmap | Reorder priorities | A |
| Study | Create plan (via StudyPlanner) | A |
| Study | Approve (Class A plan) | A |
| Study | Reject | A |
| Study | Close | A |
| Study | Approve (Class B plan — META/CUSTOM/HIGH) | B |
| Knowledge | Snapshot | A |
| Knowledge | Gap detection | A |
| Knowledge | Synthesis | A |
| Knowledge | Retire artifact | B |
| Knowledge | Demote certified edge | B |
| Contradiction | Resolve unresolvable contradiction | B |
| Governance | Modify evidence thresholds | B |
| Governance | Amend Decision Matrix | B |
| Governance | Amend Constitution | B |
| Guidance | Issue non-trading advisory | A |
| Guidance | Issue trading-parameter guidance | B |
| Trading | Any action | PROHIBITED |
| Execution | Any action | PROHIBITED |
| Capital/Risk | Any action | PROHIBITED |
| Strategy | Any action | PROHIBITED |

---

## Part 5 — Audit Requirements

Every Class A decision must be logged with:
- Timestamp
- Decision type
- Input state (what triggered it)
- Output state (what changed)
- Rationale (one-line scientific justification)

Every Class B decision must additionally include:
- Human approval reference (timestamp, approver identity)
- Options presented
- Option selected and why
- Expected outcome

Class B decisions are not logged until approval is received. Pending Class B decisions
are tracked separately as "awaiting human decision."
