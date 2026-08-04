# ResearchCoordinator Design Document

**IIOS Research Infrastructure — Phase 3A**
**Component:** `autonomous_research/research_coordinator.py`
**Status:** COMPLETE — 190/190 tests pass

---

## 1. Purpose

`ResearchCoordinator` (RC) is the single operational owner of all research *execution* in the IIOS Autonomous Research System (ARS).

It decides **HOW** to run approved research work. It never decides **WHAT** to research. Scientific Director owns scientific priorities; ResearchCoordinator owns the pipeline.

---

## 2. Architectural Position

```
Scientific Director
    │
    │  Approved StudyPlan
    ▼
ResearchCoordinator          ◄─ Phase 3A (this component)
    │
    ├── StudyPlanner          (validate plan, estimate cost)
    ├── KnowledgeProvider     (historical replay, knowledge snapshot)
    ├── EvidenceValidator     (quality gates)
    ├── HypothesisRegistry    (evidence integration)
    ├── CrossStudySynthesizer (cross-study synthesis)
    └── IDRRepository         (institutional DNA audit)
```

RC sits between the Scientific Director (who decides what to study) and the execution subsystems (who do the actual work).

---

## 3. Design Principles

### 3.1 Single Execution Owner
There is exactly one `ResearchCoordinator` instance per IIOS deployment. All research pipeline invocations go through it. No other component executes research pipelines.

### 3.2 Complete Delegation
Once the Scientific Director hands an approved `StudyPlan` to the RC, the Scientific Director can fully delegate and is done. RC handles everything from there.

### 3.3 Open Extension
New research modules (new stages, new study types) can be added to the RC pipeline without changing the Scientific Director interface. The RC absorbs new capabilities; the Scientific Director remains stable.

### 3.4 Knowledge Always Integrates
Every completed study, regardless of partial failures, produces a `ResearchRun` record. The knowledge integration stage captures the current knowledge snapshot. Synthesis always gets a chance to run. Knowledge grows continuously.

### 3.5 Strict Boundaries — What RC Never Does
| Prohibited | Owned by |
|---|---|
| Create hypotheses | HypothesisRegistry |
| Change research priorities | RoadmapManager |
| Modify the roadmap | RoadmapManager |
| Reject a scientific question | Scientific Director |
| Make trading decisions | RiskGuardian / DebateAndDecision |
| Generate new study plans | StudyPlanner |

---

## 4. Pipeline Architecture

The RC executes an **8-stage sequential pipeline** for every approved study:

```
Approved StudyPlan
        │
        ▼
┌─────────────────────────┐
│  Stage 1: study_plan    │  Validate dependencies; estimate cost
└────────────┬────────────┘
             │
        ▼
┌─────────────────────────┐
│  Stage 2: replay        │  Historical replay context (HISTORICAL_REPLAY only)
└────────────┬────────────┘
             │
        ▼
┌─────────────────────────┐
│  Stage 3: validation    │  EvidenceValidator quality gates
└────────────┬────────────┘
             │
        ▼
┌─────────────────────────┐
│  Stage 4: evidence_     │  Write evidence into HypothesisRegistry
│           integration   │  (only if plan has source_hypothesis_id)
└────────────┬────────────┘
             │
        ▼
┌─────────────────────────┐
│  Stage 5: knowledge_    │  Snapshot KnowledgeProvider state
│           integration   │
└────────────┬────────────┘
             │
        ▼
┌─────────────────────────┐
│  Stage 6: cross_study_  │  CrossStudySynthesizer.synthesize()
│           synthesis     │
└────────────┬────────────┘
             │
        ▼
┌─────────────────────────┐
│  Stage 7: repository_   │  IDR + edge-store audit
│           update        │
└────────────┬────────────┘
             │
        ▼
┌─────────────────────────┐
│  Stage 8: research_     │  Compile final report (ALWAYS runs)
│           report        │
└─────────────────────────┘
        │
        ▼
    ResearchRun
```

### 4.1 Stage Isolation
Every stage is wrapped in `try/except`. A failure in stage N does **not** abort stages N+1..8. Stage 8 (`research_report`) runs unconditionally.

### 4.2 Stage States
Each stage produces one of five states:
- `SUCCESS` — completed normally
- `FAILED` — exception was raised and captured
- `SKIPPED` — disabled by config flag **or** precondition not met (e.g. replay skipped for non-HISTORICAL_REPLAY study types)
- `RUNNING` — in progress (transient)
- `WAITING` — not yet started (transient)

### 4.3 Pipeline Health
Health is derived from stage outcomes after the run:

| Condition | Health |
|---|---|
| All enabled stages succeed | `HEALTHY` |
| At least one fails, at least one succeeds | `DEGRADED` |
| All enabled stages fail | `FAILED` |
| No run has been executed | `NO_DATA` |

---

## 5. Failure Policy

- **Partial completion is valid.** A `ResearchRun` with `DEGRADED` health still contains all the evidence and knowledge from the stages that succeeded.
- **Telemetry is always produced.** Even a fully-failed run has a complete `ResearchTelemetry` record.
- **History is always updated.** Every `run_research()` call adds an entry to the in-memory history.
- **No hard crash.** RC never re-raises exceptions from individual stages. The caller always receives a `ResearchRun`.

---

## 6. Key Design Decisions

### 6.1 Replay Stage is Conditional
The `replay` stage only runs for `HISTORICAL_REPLAY` study types. For all other types, it is `SKIPPED` with a reason. This avoids wasting time on irrelevant data loading.

### 6.2 Evidence Integration Requires a Linked Hypothesis
The `evidence_integration` stage only runs if the `StudyPlan.source_hypothesis_id` is set **and** the hypothesis exists in the registry. Plans without a hypothesis source still produce a `ResearchRun`; the evidence stage is `SKIPPED` with a clear reason.

### 6.3 dry_run Mode
When `RCConfig.dry_run=True`:
- No writes to `HypothesisRegistry.add_evidence()` occur
- No history is persisted to disk
- All stage logic still executes (reads, queries, synthesis)
- Useful for validation runs and testing without side effects

### 6.4 History Persistence
Run history is stored as a JSON array at `RCConfig.history_path`. The file is written after every non-dry-run execution. History is capped at `RCConfig.max_history_runs` entries (default: 90).

### 6.5 Thread Safety
All internal state mutations (`_history`, `_consecutive_failures`, etc.) are protected by a `threading.Lock()`.

---

## 7. Module Dependencies

| Dependency | Usage |
|---|---|
| `StudyPlanner` | `validate_dependencies()`, `estimate_cost()` |
| `EvidenceValidator` | `validate_hypothesis()`, `validate_finding()`, `validate()`, `statistics()` |
| `HypothesisRegistry` | `get()`, `add_evidence()` |
| `KnowledgeProvider` | `get_snapshot()`, `get_warnings()`, `list_studies()`, `list_edges()`, `get_replay_summary()` |
| `CrossStudySynthesizer` | `synthesize()` |
| `IDRRepository` | `statistics()`, `list_active()` |

All dependencies are **optional** (injected via constructor, default `None`). Missing dependencies cause the corresponding stages to be `SKIPPED`, not `FAILED`.

---

## 8. Files Created

| File | Purpose |
|---|---|
| `autonomous_research/rc_models.py` | Pure data models: `ResearchStage`, `ResearchRun`, `ResearchTelemetry`, `ResearchSummary`, `RCStatus`, `ResearchHealth`, `ResearchStageState`, `RCError`, `RCStageError`, `make_rc_run_id()`, stage name constants |
| `autonomous_research/rc_config.py` | `RCConfig` dataclass with per-stage toggles and `dry_run` flag |
| `autonomous_research/research_coordinator.py` | `ResearchCoordinator` class — full 8-stage pipeline |
| `autonomous_research/__init__.py` | Updated — RC symbols added to exports and `__all__` |
| `test_rc.py` | 190 tests, T001–T190 |

---

## 9. Answers to Design Questions

**Q1: Is there a single owner of research execution?**
Yes. `ResearchCoordinator` is the sole owner. It is the only entry point to the research pipeline.

**Q2: Can the Scientific Director delegate completely?**
Yes. The Scientific Director produces an approved `StudyPlan` and calls `rc.run_research(plan)`. From that point, no further Scientific Director involvement is required.

**Q3: Can new research modules be added without changing Scientific Director?**
Yes. New stages, new study types, or new execution backends are added to `ResearchCoordinator`. The Scientific Director interface (`StudyPlan`) is unchanged.

**Q4: Can every completed study automatically update institutional knowledge?**
Yes. Stage 5 (`knowledge_integration`) captures a full `KnowledgeProvider` snapshot. Stage 6 (`cross_study_synthesis`) synthesizes across all studies. Stage 4 (`evidence_integration`) writes evidence into `HypothesisRegistry`. All three run automatically on every `run_research()` call.
