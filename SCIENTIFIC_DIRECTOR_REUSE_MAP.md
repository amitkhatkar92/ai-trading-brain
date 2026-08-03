# SCIENTIFIC DIRECTOR — REUSE MAP
## Every Responsibility Mapped to Existing IIOS Module

**Principle:** If it already works, reuse it. New code only for what is genuinely missing.  
**Evidence basis:** Full source code analysis of 23 IIOS modules (ARS_ARCHITECTURE_AUDIT.md).

---

## Reading Guide

| Column | Meaning |
|---|---|
| **Responsibility** | Scientific Director responsibility (R-01 through R-12) |
| **Existing Module** | Exact Python file and class that satisfies this requirement |
| **Interaction** | How ARS interacts (READ / CALL_API / SUBSCRIBE / EXTEND / WRAP) |
| **Inputs** | What ARS provides to the existing module |
| **Outputs** | What ARS receives back |
| **New Code Required** | LOC of new code needed (0 = full reuse, >0 = wrapper or extension) |
| **Confidence** | Evidence confidence: HIGH (source code verified) / MEDIUM (inferred) |

---

## R-01 — Read Completed Studies

| Item | Detail |
|---|---|
| **Responsibility** | Load all study result JSON files. Assess completeness. Build unified study index. |
| **Existing Module** | `data/study002_results.json`, `data/study002a_results.json`, `data/re001a_results.json` (established JSON convention) |
| **Interaction** | READ — `json.load()` only |
| **Inputs** | File paths (scanned from `data/` directory) |
| **Outputs** | `StudyResult` objects (typed from existing JSON schema) |
| **New Code Required** | ~80 LOC — `KnowledgeProvider._load_study_result()` (thin reader, no logic) |
| **Confidence** | HIGH — 3 result files exist with consistent schema |

**Reuse Decision:** Build a thin reader. Do not reprocess the data. Study results are the ground truth.

---

## R-02 — Read Knowledge Stores

| Item | Detail |
|---|---|
| **Responsibility** | Build unified KnowledgeSnapshot from all platform knowledge stores. |
| **Existing Modules** | `data/learning_db.json` (LearningEngine), `data/strategy_performance.json` (StrategyPerformanceTracker), `data/discovered_edges.json` (EdgeDiscoveryEngine), `data/regime_probability_history.json` (RegimeProbabilityModel), `data/evolved_strategies.json` (StrategyLab) |
| **Interaction** | READ — json.load() only. Never write to these files. |
| **Inputs** | None (reads from disk) |
| **Outputs** | `KnowledgeSnapshot` (aggregation of all stores) |
| **New Code Required** | ~150 LOC — `KnowledgeProvider.get_snapshot()` aggregation logic |
| **Confidence** | HIGH — all 5 files verified in source code |

**Reuse Decision:** Read-only consumers of LearningEngine and StrategyPerformanceTracker output files. No API call needed.

---

## R-03 — Monitor Research Quality

| Item | Detail |
|---|---|
| **Responsibility** | Evaluate completed studies for quality before promoting findings. |
| **Existing Modules** | `performance/walk_forward_tester.py` (WFT pass rate), `validation_engine/` (6-stage gates), `study002a_pipeline.py` (MWU significance, already implemented) |
| **Interaction** | CALL_API — `WalkForwardTester.evaluate()`, WRAP — study002a `_compute_significance()` |
| **Inputs** | `StudyResult`, `StudyPlan.min_evidence` spec |
| **Outputs** | `ValidationVerdict` (ACCEPT / REJECT / INCONCLUSIVE) |
| **New Code Required** | ~200 LOC — `EvidenceValidator` (thin wrapper, calls existing methods; adds temporal integrity check) |
| **Confidence** | HIGH — WFT and MWU both verified in source |

**Reuse Decision:** EvidenceValidator delegates to existing validation logic. The temporal integrity check (no lookahead) is new because it's ARS-specific.

---

## R-04 — Identify Knowledge Gaps

| Item | Detail |
|---|---|
| **Responsibility** | Detect regimes with poor performance, unexplored feature spaces, degrading pattern confidence. |
| **Existing Modules** | `learning_system/strategy_performance_tracker.py` (tracks win rate by strategy), `meta_learning/regime_strategy_map.py` (tracks win rate by regime), `edge_discovery/edge_discovery_engine.py` (tracks pattern confidence) |
| **Interaction** | READ — consume their output JSON files. The gap detection logic itself is new. |
| **Inputs** | `KnowledgeSnapshot` |
| **Outputs** | `List[KnowledgeGap]` |
| **New Code Required** | ~250 LOC — `GapDetector` class (reads existing data, applies gap thresholds — logic is new) |
| **Confidence** | HIGH — all source data files verified |

**Reuse Decision:** GapDetector reads the outputs of existing modules. The decision logic (what constitutes a gap) is new, but the underlying data comes entirely from existing infrastructure.

---

## R-05 — Prioritise Research

| Item | Detail |
|---|---|
| **Responsibility** | Score and rank open hypotheses. Maintain prioritised agenda. |
| **Existing Modules** | `communication/task_queue.py` (Priority enum: CRITICAL > HIGH > NORMAL > LOW) — provides the priority infrastructure |
| **Interaction** | REUSE concept — scientific priority scoring is new logic, but uses TaskQueue's priority scheme |
| **Inputs** | `List[Hypothesis]`, `KnowledgeSnapshot` |
| **Outputs** | Ranked `List[Hypothesis]` |
| **New Code Required** | ~150 LOC — `RoadmapManager.prioritize()` — scoring formula is new |
| **Confidence** | MEDIUM — priority scheme design is new, but no existing equivalent needed |

**Reuse Decision:** Priority scoring is genuinely new logic (no existing equivalent). ~150 LOC is justified — it's the core intelligence of the scheduler.

---

## R-06 — Generate Hypotheses

| Item | Detail |
|---|---|
| **Responsibility** | Translate knowledge gaps into specific, testable hypotheses. |
| **Existing Modules** | `communication/agent_memory.py` (stores hypothesis state per-agent), `edge_discovery/pattern_miner.py` (provides pattern candidate templates to inform hypotheses) |
| **Interaction** | INSPIRED BY — EdgeDiscovery's candidate generation pattern; AgentMemory stores hypothesis registry |
| **Inputs** | `KnowledgeGap` |
| **Outputs** | `Hypothesis` (with question, null_hypothesis, min_evidence, data_requirements) |
| **New Code Required** | ~200 LOC — `HypothesisProvider.generate()` — translation rules from gap type to hypothesis template |
| **Confidence** | HIGH — gap types are well-defined; hypothesis templates can be codified |

**Reuse Decision:** The HypothesisProvider uses AgentMemory for persistence (REUSE). The generation logic is new but follows established EdgeDiscovery pattern-candidate patterns.

---

## R-07 — Plan Studies

| Item | Detail |
|---|---|
| **Responsibility** | Convert hypothesis to complete study plan. Check data availability. |
| **Existing Modules** | `study002a_pipeline.py::_extract_features_from_db()` (data availability check), `edge_discovery/feature_extractor.py` (available feature names), `data/replay.db` (row count query for feasibility) |
| **Interaction** | WRAP — feasibility check calls existing feature extractor to confirm features exist |
| **Inputs** | `Hypothesis` |
| **Outputs** | `StudyPlan` |
| **New Code Required** | ~200 LOC — `StudyPlanner.plan()` + `estimate_cost()` + `assess_feasibility()` |
| **Confidence** | HIGH — feature names and data schema are known |

**Reuse Decision:** StudyPlanner queries existing data sources for feasibility. Planning logic is new (no equivalent exists).

---

## R-08 — Assign Work to Existing Modules

| Item | Detail |
|---|---|
| **Responsibility** | Delegate study execution to the correct existing module. Submit to TaskQueue. |
| **Existing Modules** | `communication/task_queue.py` (task submission), `edge_discovery/edge_discovery_engine.py` (pattern mining), `validation_engine/` (promotion gating), `research_lab/research_lab.py` (sandbox), `performance/walk_forward_tester.py` (WF-only tests), `study_executor.py` (complex pipelines — to be built as wrapper) |
| **Interaction** | CALL_API — ResearchCoordinator calls existing module APIs; submits tasks to TaskQueue |
| **Inputs** | `StudyPlan` |
| **Outputs** | `ScheduledStudy` with execution_id |
| **New Code Required** | ~150 LOC — `ResearchCoordinator.delegate()` routing logic + ~100 LOC `study_executor.py` (wrapper over study002_pipeline) |
| **Confidence** | HIGH — all target module APIs verified |

**Reuse Decision:** ResearchCoordinator is a router — it calls existing APIs. ~150 LOC routing logic + ~100 LOC wrapper = ~250 LOC total, all integration code, zero new algorithms.

---

## R-09 — Integrate Results

| Item | Detail |
|---|---|
| **Responsibility** | Collect study results, validate quality, update knowledge base. |
| **Existing Modules** | `EvidenceValidator` (new — calls existing WFT, MWU), `data/ars_knowledge_base.json` (output target — new file, established JSON convention) |
| **Interaction** | CALL internal EvidenceValidator, then WRITE to ars_knowledge_base.json |
| **Inputs** | `StudyResult`, `StudyPlan` |
| **Outputs** | Updated `ars_knowledge_base.json`, `ValidationVerdict` |
| **New Code Required** | ~100 LOC — `CrossStudySynthesizer.add_finding()` + `update_knowledge_base()` |
| **Confidence** | HIGH — knowledge base schema follows established study result patterns |

**Reuse Decision:** The knowledge base update is ~100 LOC of JSON management. The validation uses EvidenceValidator (R-03 above).

---

## R-10 — Update Research Roadmap

| Item | Detail |
|---|---|
| **Responsibility** | Mark hypotheses, generate follow-ups, update agenda. |
| **Existing Modules** | `communication/event_bus.py` (publish STUDY_COMPLETE), `control_tower/` (auto-logs via wildcard) |
| **Interaction** | PUBLISH events via EventBus, WRITE to ars_hypothesis_registry.json |
| **Inputs** | `Hypothesis`, `ValidationVerdict` |
| **Outputs** | Updated HypothesisRegistry, `STUDY_COMPLETE` event |
| **New Code Required** | ~100 LOC — `RoadmapManager.update()` + `add_followup()` |
| **Confidence** | HIGH — EventBus API confirmed, registry JSON schema designed |

**Reuse Decision:** EventBus is fully reused (zero new code). ControlTower auto-captures. Roadmap state management is ~100 LOC JSON CRUD.

---

## R-11 — Generate Research Reports

| Item | Detail |
|---|---|
| **Responsibility** | Produce structured Markdown reports following Study 2A format. |
| **Existing Modules** | Study 2A report format (WINNER_DNA_REPORT.md, FEATURE_IMPORTANCE_REPORT.md etc.) — templates already proven |
| **Interaction** | WRAP — codify existing Study 2A report structure as templates |
| **Inputs** | `StudyResult`, `StudyPlan`, `ValidationVerdict` |
| **Outputs** | Markdown report file in `data/ars_proposals/RESEARCH_REPORT_*.md` |
| **New Code Required** | ~200 LOC — `ResearchReportGenerator` (template rendering from existing report format) |
| **Confidence** | HIGH — 6 study reports verified as templates |

**Reuse Decision:** Templates are codified from existing reports. Pure string templating, no new logic.

---

## R-12 — Propose Platform Guidance

| Item | Detail |
|---|---|
| **Responsibility** | Translate validated findings into actionable parameter proposals for human review. |
| **Existing Modules** | `data/ars_proposals/` (output target — new directory), EventBus `PLATFORM_GUIDANCE_PROPOSED` (new event type) |
| **Interaction** | WRITE proposal file, PUBLISH EventBus event |
| **Inputs** | `List[StudyFinding]` (validated), `KnowledgeSnapshot` |
| **Outputs** | `GUIDANCE_PROPOSAL_*.md` file, EventBus event |
| **New Code Required** | ~100 LOC — `CrossStudySynthesizer.propose_guidance()` — template-based proposal generation |
| **Confidence** | HIGH — proposal format is well-defined by governance model |

**Reuse Decision:** Pure template generation. Governance file protocol is simple. Zero trading logic.

---

## Summary: New Code per Responsibility

| # | Responsibility | Component | New LOC | Reuse % |
|---|---|---|---|---|
| R-01 | Read completed studies | KnowledgeProvider (partial) | 80 | 95% |
| R-02 | Read knowledge stores | KnowledgeProvider (bulk) | 150 | 95% |
| R-03 | Monitor research quality | EvidenceValidator | 200 | 80% |
| R-04 | Identify knowledge gaps | GapDetector | 250 | 70% |
| R-05 | Prioritise research | RoadmapManager.prioritize() | 150 | 50% |
| R-06 | Generate hypotheses | HypothesisProvider | 200 | 60% |
| R-07 | Plan studies | StudyPlanner | 200 | 70% |
| R-08 | Assign work to existing modules | ResearchCoordinator + study_executor | 250 | 85% |
| R-09 | Integrate results | CrossStudySynthesizer (partial) | 100 | 90% |
| R-10 | Update roadmap | RoadmapManager.update() + followup | 100 | 90% |
| R-11 | Generate research reports | ResearchReportGenerator | 200 | 80% |
| R-12 | Propose platform guidance | CrossStudySynthesizer.propose() | 100 | 90% |
| — | ScientificDirector (coordinator) | research_director.py | 200 | — |
| — | HypothesisRegistry (persistence) | hypothesis_registry.py | 150 | 90% |
| — | ResearchScheduler (calendar) | research_scheduler.py | 200 | 70% |
| **Total** | | | **~2,330** | **~80%** |

**Reused/leveraged logic (existing codebase): ~15,000+ LOC**

---

## Reuse Dependency Graph

```
ScientificDirector
  │
  ├── KnowledgeProvider
  │     └── READS: learning_db.json, strategy_performance.json,
  │                discovered_edges.json, regime_probability_history.json,
  │                evolved_strategies.json, study*.json (ALL EXISTING)
  │
  ├── GapDetector
  │     └── READS: KnowledgeProvider output (0 new data sources)
  │
  ├── HypothesisProvider
  │     ├── USES: AgentMemory (existing communication/)
  │     └── WRITES: ars_hypothesis_registry.json (new file, existing format)
  │
  ├── StudyPlanner
  │     ├── READS: replay.db row counts (existing)
  │     └── READS: feature_extractor feature list (existing)
  │
  ├── ResearchCoordinator
  │     ├── CALLS: EdgeDiscoveryEngine (existing)
  │     ├── CALLS: ValidationEngine (existing)
  │     ├── CALLS: ResearchLab (existing)
  │     ├── CALLS: WalkForwardTester (existing)
  │     ├── CALLS: study_executor (wrapper over study002a, new thin wrapper)
  │     └── SUBMITS: TaskQueue Priority.LOW (existing)
  │
  ├── EvidenceValidator
  │     ├── CALLS: WalkForwardTester (existing)
  │     └── WRAPS: study002a MWU significance (existing)
  │
  ├── RoadmapManager
  │     ├── READS: HypothesisProvider (above)
  │     └── PUBLISHES: EventBus (existing)
  │
  └── CrossStudySynthesizer
        ├── READS: All study results (existing)
        ├── WRITES: ars_knowledge_base.json (new file)
        └── PUBLISHES: EventBus (existing)
```

---

## Zero-Reuse Anti-Pattern (What We Will NOT Do)

| Anti-Pattern | Why Forbidden |
|---|---|
| Rebuild WalkForwardTester | `performance/walk_forward_tester.py` is production-tested with real capital |
| Rebuild feature extractor | Two working implementations already exist |
| Rebuild pattern miner | `edge_discovery/pattern_miner.py` is integrated, validated, and battle-tested |
| Rebuild Monte Carlo | `market_simulation/simulation_engine.py` has 14 named scenarios |
| Rebuild strategy testing | `validation_engine/` 6-stage pipeline is calibrated and protected |
| Rebuild knowledge storage | Established JSON convention with 4+ result files |
| Rebuild EventBus | `communication/event_bus.py` is the backbone of inter-agent coordination |
| Rebuild TaskQueue | `communication/task_queue.py` has per-agent workers and priority scheduling |

---

*Scientific Director Reuse Map | ARS Phase 0 | Frozen 2026-08-03*
