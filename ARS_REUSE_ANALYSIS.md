# ARS REUSE ANALYSIS
## Maximum Reuse Design — Which Existing Modules ARS Should Orchestrate

**Principle:** Build ARS as a thin orchestration layer. Every algorithm that already works should be reused, not duplicated.

---

## 1. Reuse Strategy

ARS must NOT:
- Reimplement feature extraction (already done in 2 places)
- Reimplement walk-forward testing (already in 2 places)
- Reimplement pattern mining (already in edge_discovery)
- Reimplement strategy testing (already in validation_engine)
- Reimplement knowledge storage formats (already established)
- Modify any protected module

ARS MUST:
- Consume existing module outputs
- Schedule existing research methods
- Bridge findings from standalone scripts into live system
- Add only the missing orchestration layer

---

## 2. Module-by-Module Reuse Decision

### 2.1 FULL REUSE — No Modification

| Module | Reuse Mode | ARS Use |
|---|---|---|
| `data/replay.db` | Read-only | Primary data source for all research studies |
| `validation_engine/` | Call existing API | Gate any new pattern or strategy before promotion |
| `market_simulation/simulation_engine.py` | Call existing API | Stress-test any pattern found by ARS |
| `performance/walk_forward_tester.py` | Call existing API | Validate any research finding temporally |
| `performance/drawdown_analyzer.py` | Call existing API | Risk profile any promoted strategy |
| `communication/event_bus.py` | Subscribe + publish | ARS publishes RESEARCH_COMPLETE, HYPOTHESIS_TESTED events |
| `communication/task_queue.py` | Submit tasks | ARS queues research tasks at Priority.LOW (non-blocking) |
| `communication/agent_memory.py` | Read/write own memory | ARS maintains its own AgentMemory for research state |
| `control_tower/telemetry_logger.py` | Passive (no change) | Will auto-log ARS events via wildcard subscription |
| `meta_learning/meta_model.py` | Call existing API | ARS can query optimal strategy weights for any regime |
| `learning_system/learning_engine.py` | Read output only | ARS reads `learning_db.json` to identify underperforming strategies |
| `research_lab/research_lab.py` | Call existing API | ARS uses ResearchLab as sandbox for new concepts |
| `risk_guardian/` | Read output only | ARS never bypasses RiskGuardian; observes its state for research triggers |
| `global_intelligence/` | Read output only | ARS reads GlobalSnapshot for regime context in research |
| `system_monitor/` | Read output only | ARS reads HealthReport to detect system degradation (triggers diagnostic research) |

### 2.2 EXTEND EXISTING — Minimal Additions

| Module | Extension Type | What to Add | Lines |
|---|---|---|---|
| `orchestrator/weekend_intelligence.py` | New method | `run_ars_research_cycle()` — delegates to ResearchDirectorAI | ~50 |
| `orchestrator/master_orchestrator.py` | New EOD step | `_do_ars_research()` — after existing `_do_eod_learning()` | ~30 |
| `learning_system/learning_engine.py` | New hook | `register_research_trigger(fn)` — fire when WR drops below threshold | ~20 |
| `meta_learning/regime_strategy_map.py` | New query | `get_underperforming_regimes()` → List[RegimeLabel] | ~30 |
| `communication/events.py` | New event types | `RESEARCH_SCHEDULED`, `HYPOTHESIS_REGISTERED`, `STUDY_COMPLETE`, `KNOWLEDGE_PROMOTED` | ~20 |
| `edge_discovery/edge_discovery_engine.py` | New callback | `on_discovery_complete(fn)` — notify ARS when new edge found | ~15 |

**Total extension lines: ~165 LOC**

### 2.3 WRAP STANDALONE SCRIPTS — Integration Bridge

These scripts contain production-quality research algorithms. ARS should not rewrite them. Instead, extract their core logic into importable functions:

| Script | Algorithm to Extract | Target Module | Lines |
|---|---|---|---|
| `study002a_pipeline.py` | `compute_feature_statistics()` | `autonomous_research/statistics.py` | Extract ~80 lines |
| `study002a_pipeline.py` | `rank_features()` (RF + MI + Cohen's d) | `autonomous_research/statistics.py` | Extract ~60 lines |
| `study002a_pipeline.py` | `discover_dna_patterns()` (DT + WF) | `autonomous_research/pattern_discovery.py` | Extract ~120 lines |
| `study002a_pipeline.py` | `cluster_winners()` (KMeans) | `autonomous_research/cluster_analysis.py` | Extract ~80 lines |
| `study002a_pipeline.py` | `feature_decile_analysis()` | `autonomous_research/statistics.py` | Extract ~60 lines |
| `study002a_pipeline.py` | `_extract_features_from_db()` | `autonomous_research/data_loader.py` | Extract ~150 lines |
| `historical_replay.py` | `run_replay()` | `autonomous_research/data_loader.py` | Extract interface ~30 lines |
| `study002_pipeline.py` | 7-stage pipeline orchestration | `autonomous_research/study_executor.py` | Extract interface ~50 lines |

**Strategy:** Move these functions into `autonomous_research/` modules. Original scripts become thin wrappers that call the new importable functions. This preserves all existing tests and functionality.

### 2.4 NEW COMPONENTS — Genuinely Required

These five components have no existing equivalent:

| Component | File | Primary Responsibility | LOC Estimate |
|---|---|---|---|
| `ResearchDirectorAI` | `autonomous_research/research_director.py` | Generates research agenda from platform state; prioritizes hypotheses | ~400 |
| `HypothesisRegistry` | `autonomous_research/hypothesis_registry.py` | Tracks all research questions: OPEN/ACTIVE/TESTED/PROMOTED/REJECTED | ~250 |
| `PerformanceTrigger` | `autonomous_research/performance_trigger.py` | Monitors live performance → fires research tasks on degradation | ~150 |
| `CrossStudySynthesizer` | `autonomous_research/knowledge_synthesizer.py` | Integrates multi-study findings into a unified knowledge base | ~300 |
| `ResearchScheduler` | `autonomous_research/research_scheduler.py` | Autonomous calendar: daily/weekly/monthly research cycles | ~200 |
| `ResearchReportGenerator` | `autonomous_research/report_generator.py` | Assembles findings into structured Markdown reports | ~200 |

**Total new LOC: ~1,500**

---

## 3. Reuse Architecture Diagram

```
┌──────────────────────────────────────────────────────────────────┐
│              AUTONOMOUS RESEARCH SYSTEM (ARS)                     │
│                                                                    │
│  ┌─────────────────────┐    ┌──────────────────────────────────┐ │
│  │  ResearchDirectorAI │    │        ResearchScheduler         │ │
│  │  (NEW — ~400 LOC)   │◄──►│        (NEW — ~200 LOC)         │ │
│  └──────────┬──────────┘    └──────────────┬───────────────────┘ │
│             │                               │                      │
│  ┌──────────▼──────────┐    ┌──────────────▼───────────────────┐ │
│  │  HypothesisRegistry │    │        PerformanceTrigger        │ │
│  │  (NEW — ~250 LOC)   │    │        (NEW — ~150 LOC)          │ │
│  └──────────┬──────────┘    └──────────────┬───────────────────┘ │
│             │                               │                      │
│  ┌──────────▼───────────────────────────────▼───────────────────┐ │
│  │              StudyExecutor (WRAP study002_pipeline.py)        │ │
│  │              DataLoader (WRAP historical_replay.py)           │ │
│  │              Statistics (WRAP study002a statistics)           │ │
│  │              PatternDiscovery (WRAP study002a DT discovery)   │ │
│  │              ClusterAnalysis (WRAP study002a KMeans)          │ │
│  └──────────────────────────────┬────────────────────────────────┘ │
│                                  │                                 │
│  ┌───────────────────────────────▼────────────────────────────┐   │
│  │               CrossStudySynthesizer (NEW ~300 LOC)          │   │
│  └───────────────────────────────┬────────────────────────────┘   │
│                                  │                                 │
│  ┌───────────────────────────────▼────────────────────────────┐   │
│  │            ResearchReportGenerator (NEW ~200 LOC)           │   │
│  └─────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘

             ┌───────────────────────────────────────┐
             │        EXISTING MODULES (UNCHANGED)    │
             ├───────────────────────────────────────┤
             │  validation_engine/  — full reuse      │
             │  market_simulation/  — full reuse      │
             │  performance/        — full reuse      │
             │  edge_discovery/     — full reuse      │
             │  learning_system/    — full reuse      │
             │  meta_learning/      — full reuse      │
             │  research_lab/       — full reuse      │
             │  communication/      — full reuse      │
             │  control_tower/      — full reuse      │
             │  data/replay.db      — full reuse      │
             └───────────────────────────────────────┘
```

---

## 4. Reuse Efficiency Metrics

| Metric | Value |
|---|---|
| Existing relevant modules fully reused | 15 |
| Existing modules extended (minimally) | 6 |
| Standalone scripts wrapped (not rewritten) | 5 |
| Genuinely new components | 6 |
| Estimated new LOC | ~1,500 |
| Estimated reused / wrapped LOC | ~18,000 |
| **Reuse ratio** | **~92%** |
| New code % of total ARS | **~8%** |

---

## 5. Integration Touch Points

ARS integrates with IIOS exclusively through these interfaces:

| Interface | Direction | Method |
|---|---|---|
| `communication/event_bus.get_bus()` | Bidirectional | ARS subscribes to `LEARNING_COMPLETE`, `EDGE_DISCOVERED`; publishes `STUDY_COMPLETE`, `HYPOTHESIS_REGISTERED` |
| `communication/task_queue.get_task_queue()` | Submit only | ARS submits research tasks at Priority.LOW; never at CRITICAL/HIGH |
| `communication/agent_memory.get_memory("ResearchDirectorAI")` | Read/write | ARS stores its own research state |
| `data/` JSON stores | Read mostly | ARS reads `learning_db.json`, `strategy_performance.json`, `discovered_edges.json`; writes only to `ars_*.json` |
| `data/replay.db` | Read-only | ARS never writes to replay databases |
| `orchestrator/master_orchestrator.py` | Called by | MasterOrchestrator calls `ars.run_research_cycle()` during EOD |
| `validation_engine/` | ARS calls | ARS passes any promoted pattern through existing 6-stage pipeline |
| `research_lab/research_lab.py` | ARS calls | ARS uses sandbox for experimental testing |

**ARS writes exclusively to:**
- `data/ars_hypothesis_registry.json`
- `data/ars_research_schedule.json`
- `data/ars_study_*.json` (research results)
- `data/ars_knowledge_base.json` (synthesized findings)

---

## 6. Critical Non-Duplication Rules

1. **Feature extraction:** ARS uses `_extract_features_from_db()` from `study002a_pipeline.py` wrapped into `autonomous_research/data_loader.py`. Not reimplemented.

2. **Pattern mining:** ARS uses `edge_discovery/pattern_miner.py` directly. `study002a_pipeline.py`'s DT discovery is wrapped as a higher-level alternative.

3. **Strategy testing:** ARS calls `validation_engine/` exclusively. No separate backtesting.

4. **Walk-forward:** ARS calls `performance/walk_forward_tester.py`. Not reimplemented.

5. **Promotion:** ARS submits any discovered strategy to `research_lab/research_lab.py` → `validation_engine/`. Never bypasses the promotion pipeline.

6. **Knowledge storage:** ARS writes to `ars_*.json` files only. Never modifies `learning_db.json`, `evolved_strategies.json`, or `strategy_performance.json` directly.

---

*ARS Reuse Analysis | 2026-08-03 | Designed for maximum code reuse*
