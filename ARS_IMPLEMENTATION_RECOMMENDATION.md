# ARS IMPLEMENTATION RECOMMENDATION
## How to Build the Autonomous Research System

**Decision basis:** Full architectural audit of 23 IIOS modules (see ARS_ARCHITECTURE_AUDIT.md).  
**Principle:** Maximum reuse. ARS is a thin coordination layer — not a new AI system.

---

## 1. Recommended Architecture

### 1.1 Directory Structure

```
autonomous_research/
├── __init__.py                         # Exports: ARS, ResearchDirectorAI
├── research_director.py                # NEW (~400 LOC) — Master coordinator
├── hypothesis_registry.py              # NEW (~250 LOC) — Tracks open questions
├── performance_trigger.py              # NEW (~150 LOC) — Fires on degradation
├── research_scheduler.py               # NEW (~200 LOC) — Autonomous calendar
├── knowledge_synthesizer.py            # NEW (~300 LOC) — Cross-study synthesis
├── report_generator.py                 # NEW (~200 LOC) — Automated reports
├── data_loader.py                      # WRAP (study002a _extract_features_from_db)
├── statistics.py                       # WRAP (study002a RF/MI/Cohen's d/MWU)
├── pattern_discovery.py                # WRAP (study002a DT DNA discovery)
├── cluster_analysis.py                 # WRAP (study002a KMeans)
└── study_executor.py                   # WRAP (study002_pipeline 7-stage orchestration)
```

**Total new LOC:** ~1,500  
**Total wrapper LOC:** ~580 (wrapping ~18,000 existing LOC)  
**Total component count:** 11 files  

---

### 1.2 Component Specifications

#### ResearchDirectorAI — The Brain

```python
# autonomous_research/research_director.py

class ResearchDirectorAI:
    """
    Master coordinator for autonomous research.
    Reads platform state → generates hypotheses → schedules studies → 
    evaluates findings → proposes platform improvements.
    
    Communication: EventBus (publishes STUDY_SCHEDULED, HYPOTHESIS_REGISTERED)
    Storage: data/ars_research_agenda.json
    Scheduling: Delegated to ResearchScheduler
    Never: Modifies trading logic, bypasses RiskGuardian, touches evolved_strategies.json
    """
    
    def generate_research_questions(self) -> List[Hypothesis]:
        """
        Reads: learning_db.json, strategy_performance.json, 
               regime_probability_history.json, discovered_edges.json
        Computes: performance gaps by regime, unexploited patterns, 
                  declining strategy groups
        Returns: List of specific, testable hypotheses ranked by priority
        """
    
    def check_agenda(self) -> Optional[Study]:
        """
        Called by MasterOrchestrator._do_ars_research() at EOD.
        Returns the highest-priority ready study, or None.
        """
    
    def evaluate_finding(self, study_result: StudyResult) -> ActionableInsight:
        """
        Interprets completed study result.
        Routes to: knowledge_synthesizer (if actionable)
                   hypothesis_registry (status update)
                   report_generator (always)
        """
```

---

#### HypothesisRegistry — The Memory

```python
# autonomous_research/hypothesis_registry.py

@dataclass
class Hypothesis:
    id: str                            # e.g., "H2026-08-001"
    question: str                      # e.g., "Why does win rate drop in TRENDING_DOWN after 13:00?"
    source: HypothesisSource           # PERFORMANCE_TRIGGER | MANUAL | CROSS_STUDY
    status: HypothesisStatus           # OPEN | ACTIVE | TESTED | PROMOTED | REJECTED
    regime: Optional[str]              # Regime context if applicable
    priority: int                      # 1 (highest) – 5 (lowest)
    created: datetime
    study_ids: List[str]               # Studies assigned to test this hypothesis
    evidence: List[StudyFinding]       # Findings from completed studies
    notes: str

class HypothesisRegistry:
    """
    Persists to: data/ars_hypothesis_registry.json
    Thread-safe: uses file-level lock
    """
    def register(self, h: Hypothesis) -> str
    def update(self, id: str, status: HypothesisStatus, evidence: StudyFinding)
    def get_open(self, regime: str = None) -> List[Hypothesis]
    def detect_contradictions(self) -> List[Tuple[Hypothesis, Hypothesis, str]]
    def get_evidence_chain(self, id: str) -> List[StudyFinding]
```

---

#### PerformanceTrigger — The Watchdog

```python
# autonomous_research/performance_trigger.py

class PerformanceTrigger:
    """
    Monitors live platform performance.
    On degradation: registers a Hypothesis and notifies ResearchDirectorAI.
    
    Hooks into:
    - LearningEngine.register_research_trigger()  (new hook, ~20 LOC)
    - EventBus subscription: STRATEGY_DISABLED, LEARNING_COMPLETE
    
    Degradation thresholds:
    - win_rate < 30% for 5+ sessions in a regime → MEDIUM priority
    - win_rate < 20% for 3+ sessions in a regime → HIGH priority  
    - 3 consecutive losses in any strategy → MEDIUM priority
    - Strategy disabled (RiskGuardian kill) → HIGH priority
    - Regime_mismatch: predicted vs actual regime > 40% of sessions → MEDIUM
    """
    
    def on_learning_complete(self, report: LearningReport):
        degradations = self._detect_degradations(report)
        for d in degradations:
            h = Hypothesis(source=HypothesisSource.PERFORMANCE_TRIGGER, ...)
            self.registry.register(h)
            self.director.notify_new_hypothesis(h)
```

---

#### CrossStudySynthesizer — The Integrator

```python
# autonomous_research/knowledge_synthesizer.py

class CrossStudySynthesizer:
    """
    Reads all study result files → synthesizes into unified knowledge base.
    Detects contradictions, extracts actionable platform guidance.
    
    Input: data/study*.json, data/re*.json, data/ars_study_*.json
    Output: data/ars_knowledge_base.json
    
    NEVER automatically applies findings to live system.
    ALWAYS generates proposals for human review.
    """
    
    def synthesize_all(self) -> KnowledgeBase
    def extract_actionable_insights(self) -> List[PlatformGuidance]
    def detect_contradictions(self) -> List[Contradiction]
    def generate_next_study_recommendations(self) -> List[Hypothesis]
    def propose_parameter_updates(self) -> List[ParameterProposal]
    # ParameterProposal is output to a markdown file for human review, not applied
```

---

#### ResearchScheduler — The Calendar

```python
# autonomous_research/research_scheduler.py

class ResearchScheduler:
    """
    Manages the autonomous research calendar.
    Runs within existing MasterOrchestrator scheduler slots.
    
    Built-in schedule:
    - EOD (daily):  PerformanceTrigger check, agenda refresh
    - Saturday:     EdgeDiscovery + DNA pattern update  
    - 1st Saturday: Cross-study synthesis + KnowledgeBase update
    - Quarterly:    Full regime study + strategy evolution run
    - On-demand:    Triggered by PerformanceTrigger on HIGH priority
    
    Constraints:
    - Max 1 heavy computation study per weekend
    - No research during VIX > 35 (system resources reserved for trading)
    - No research if any container is UNHEALTHY
    """
    
    def get_due_studies(self) -> List[ScheduledStudy]
    def is_compute_available(self) -> bool
    def mark_complete(self, study_id: str)
    def defer(self, study_id: str, reason: str)
```

---

### 1.3 Integration Map

```
MasterOrchestrator (EXTEND — ~30 LOC)
    _do_eod_learning()          → existing (unchanged)
    _do_ars_research()          → NEW: calls research_director.check_agenda()
                                        if due study: queues to TaskQueue Priority.LOW
    start_scheduler()           → add 1 slot: Saturday 10:00 → weekend ARS cycle

WeekendIntelligenceEngine (EXTEND — ~50 LOC)
    run_weekend_analysis()      → existing (unchanged)  
    run_ars_research_cycle()    → NEW: calls research_scheduler.get_due_studies()
                                        executes each via study_executor

LearningEngine (EXTEND — ~20 LOC)
    learn()                     → existing (unchanged)
    register_research_trigger() → NEW: accepts callback fn; fires on degradation

EventBus (EXTEND events.py — ~20 LOC)
    existing events             → unchanged
    RESEARCH_SCHEDULED          → NEW
    HYPOTHESIS_REGISTERED       → NEW
    STUDY_COMPLETE              → NEW
    KNOWLEDGE_PROMOTED          → NEW
    PLATFORM_GUIDANCE_PROPOSED  → NEW
```

---

## 2. Protected Modules — Zero Modification

These modules must NEVER be modified for ARS:

| Module | Reason |
|---|---|
| `risk_guardian/risk_guardian.py` | Kill-switch logic — any modification risks real money loss |
| `validation_engine/` | 6-stage promotion pipeline — ARS submits TO it, never modifies it |
| `strategy_lab/evolved_strategies/` | Earned through live evolution — ARS proposes new candidates, never modifies existing |
| `debate_system/` | Calibrated weights — modifying any weight affects all live trades |
| `decision_ai/decision_engine.py` | Calibrated thresholds — VIX-adaptive logic is stable |
| `meta_learning/meta_model.py` | Trained k-NN model — ARS queries it, never retrains from ARS pipelines |
| `data/replay.db` | Primary historical store — ARS reads only, never writes |
| `data/paper_trades.csv` | Live trade journal — ARS reads only |
| `data/control_tower.db` | Audit trail — ARS events auto-logged via wildcard, no direct write |

---

## 3. Implementation Phasing

### Phase 1 — Data Foundation (1–2 sessions)
**Goal:** Make study findings accessible to the platform

| Task | Deliverable | Risk |
|---|---|---|
| Create `autonomous_research/` package | `__init__.py` | None |
| Extract `_extract_features_from_db()` from `study002a_pipeline.py` to `data_loader.py` | Importable function | Low (original script unchanged) |
| Extract statistical methods from `study002a_pipeline.py` to `statistics.py` | Importable functions | Low |
| Create `HypothesisRegistry` | `hypothesis_registry.py` + `data/ars_hypothesis_registry.json` | None |
| Manually seed registry with 5–10 hypotheses from Study 2A findings | JSON file | None |

**Test:** Import all new modules, verify registry CRUD works.

---

### Phase 2 — Performance Trigger (1 session)
**Goal:** Platform automatically detects when research is needed

| Task | Deliverable | Risk |
|---|---|---|
| Add `register_research_trigger()` hook to `LearningEngine` | 20 LOC in learning_engine.py | Low |
| Build `PerformanceTrigger` | `performance_trigger.py` | None |
| Subscribe PerformanceTrigger to EventBus `LEARNING_COMPLETE` event | 5 LOC | None |
| Add new event types to `communication/events.py` | ~20 LOC | None |

**Test:** Simulate degraded win rate in test mode → confirm hypothesis auto-registered.

---

### Phase 3 — Research Scheduler (1 session)
**Goal:** Autonomous research calendar

| Task | Deliverable | Risk |
|---|---|---|
| Build `ResearchScheduler` | `research_scheduler.py` | None |
| Add `run_ars_research_cycle()` to `WeekendIntelligenceEngine` | ~50 LOC | Low |
| Add `_do_ars_research()` to `MasterOrchestrator` | ~30 LOC | Low |
| Register 1 new scheduler slot (Saturday 10:00) | 3 LOC in start_scheduler() | Low |

**Test:** Run `--paper` mode, trigger a manual weekend research cycle, confirm it schedules without blocking.

---

### Phase 4 — Research Director (1–2 sessions)
**Goal:** Automated research question generation

| Task | Deliverable | Risk |
|---|---|---|
| Build `ResearchDirectorAI` core | `research_director.py` | Medium (new logic) |
| Build `StudyExecutor` (wrapper over study002_pipeline) | `study_executor.py` | Low |
| Wire ResearchDirector → HypothesisRegistry → ResearchScheduler | Integration | Medium |
| First live test: ResearchDirector generates 3 hypotheses from learning_db | Hypotheses in registry | Low |

**Test:** Run `python -m autonomous_research.research_director` in dry-run mode → confirm it reads platform state and generates hypotheses without modifying any data.

---

### Phase 5 — Knowledge Synthesis (1 session)
**Goal:** Cross-study synthesis and actionable guidance generation

| Task | Deliverable | Risk |
|---|---|---|
| Build `CrossStudySynthesizer` | `knowledge_synthesizer.py` | Low |
| Run synthesis on all existing studies (001, 001A, 002, 2A) | `data/ars_knowledge_base.json` | None |
| Extract platform guidance from Study 2A findings | `data/ars_platform_guidance.md` | None |
| Human review of platform guidance (REQUIRED before any integration) | Review meeting | None |

**Test:** Run synthesizer → confirm output JSON is well-formed, guidance list is non-empty, no live system files modified.

---

### Phase 6 — Report Generation (0.5 sessions)
**Goal:** Automated report generation for all future studies

| Task | Deliverable | Risk |
|---|---|---|
| Build `ResearchReportGenerator` | `report_generator.py` | None |
| Generate retrospective reports for Study 001, 001A (validation) | Markdown reports | None |
| Wire to `STUDY_COMPLETE` EventBus event | 5 LOC | None |

---

## 4. First Implementation Recommendation

If implementing today, start with:

1. **Create `data/ars_hypothesis_registry.json`** — seed with Study 2A findings as initial hypotheses. Zero code risk, immediate value.

2. **Extract `_extract_features_from_db()`** from `study002a_pipeline.py` into `autonomous_research/data_loader.py`. This is the most-reused function in future research — making it importable is the highest-value-per-line-of-code change.

3. **Build `HypothesisRegistry`** (250 LOC) — simple JSON CRUD. Testable in isolation. Provides the memory backbone for all future ARS activity.

Only after these three steps are stable should Phase 2–6 proceed.

---

## 5. ARS Data Flow (Complete)

```
                    Platform Performance Data
                           │
                           ▼
              PerformanceTrigger detects degradation
                           │
                           ▼
              HypothesisRegistry.register(new_h)
                           │
                           ▼
              ResearchDirectorAI.prioritize_agenda()
                           │
                           ▼
              ResearchScheduler.schedule(study, time)
                           │
                           ▼
              TaskQueue (Priority.LOW, non-blocking)
                           │
                           ▼
              StudyExecutor → wraps study002_pipeline OR
                              EdgeDiscoveryEngine (existing)
                           │
                           ▼
              ValidationEngine (6-stage: unchanged)
                           │
                           ▼
              CrossStudySynthesizer → KnowledgeBase
                           │
                           ▼
              ResearchReportGenerator → Markdown report
                           │
                           ▼
              HypothesisRegistry.update(status=TESTED)
                           │
                           ▼
              EventBus → STUDY_COMPLETE
                           │
                           ▼
              ControlTower logs (auto, via wildcard)
                           │
                           ▼
              Human review of platform_guidance.md
                           │
                           ▼
              (Human decision) Apply guidance → normal change pipeline
```

---

## 6. Decision Criteria Summary

| Decision | Recommendation | Rationale |
|---|---|---|
| New module vs. extension | New `autonomous_research/` package | Separation of concerns; doesn't disrupt trading |
| Algorithm source | Reuse study002a_pipeline.py | Tested, working, uses same data schema |
| Promotion pipeline | Reuse validation_engine/ unchanged | 6-stage is calibrated and protected |
| Pattern mining | Reuse edge_discovery/pattern_miner.py | Production-integrated, battle-tested |
| Knowledge storage | New `ars_*.json` files | Isolated from live system stores |
| Integration point | EventBus + TaskQueue | Non-blocking; existing infrastructure |
| Human gate | Required before applying any finding | Change policy compliance |

---

## 7. Expected Benefits After Full Implementation

| Metric | Before ARS | After ARS |
|---|---|---|
| Time to detect performance degradation | End of day (manual review) | Real-time (automated PerformanceTrigger) |
| Research cadence | Ad-hoc (when engineer writes study) | Systematic (weekly pattern mining, monthly synthesis) |
| Hypothesis tracking | None | Structured registry with evidence chain |
| Cross-study synthesis | None (4+ studies unintegrated) | Automated weekly synthesis |
| Finding-to-live-system time | Manual (multi-week) | Automated pipeline → human gate → deploy |
| Research knowledge accumulation | Flat (each study standalone) | Compound (each study builds on synthesis) |

---

*ARS Implementation Recommendation | 2026-08-03 | Architecture-first design*
