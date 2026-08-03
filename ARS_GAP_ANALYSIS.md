# ARS GAP ANALYSIS
## Genuinely Missing Capabilities — Only What Does Not Already Exist

**Constraint:** This document lists ONLY capabilities with zero or near-zero existing coverage.  
Capabilities that partially exist are listed with their existing coverage and the true gap.  
No existing module is proposed for replacement.

---

## Methodology

For each gap: 
1. Confirmed the capability does not exist in any existing module (source code checked)
2. Confirmed no existing module can satisfy the requirement without new code
3. Identified the closest existing module for context
4. Quantified the gap precisely

---

## Gap 1 — Autonomous Research Agenda Management

**Gap Name:** ResearchDirectorAI  
**Coverage today:** 0%

**What's missing:**  
No component in IIOS decides WHAT to research next, WHY, or WHEN. Research is entirely manual (an engineer writes and runs a study script). The platform has no mechanism to:
- Observe its own performance deficits and generate research questions
- Prioritize competing research hypotheses
- Sequence studies logically (Study 2A builds on Study 002 findings)
- Recognize when a finding is actionable vs. inconclusive

**Closest existing module:** `orchestrator/weekend_intelligence.py`  
It coordinates weekend activities but doesn't generate or prioritize research questions.

**Specific capabilities missing:**
1. `generate_research_questions(performance_state, existing_knowledge) → List[Hypothesis]`  
   — Looks at: current strategy win rates by regime, underperforming time periods, unexploited patterns in discovery queue
2. `prioritize_hypotheses(hypotheses, constraints) → List[Hypothesis]`  
   — Ranks by: expected information gain, study cost, dependency on prior studies
3. `select_next_study(agenda) → Study`  
   — Picks next study to run based on available data and computational budget
4. `evaluate_finding(study_result) → ActionableInsight | NeedsMoreWork | Inconclusive`  
   — Interprets a completed study's findings into platform guidance

**Required new component:** `autonomous_research/research_director.py`  
**Estimated LOC:** ~400  
**Classification:** NEW (no existing foundation)

---

## Gap 2 — Hypothesis Registry

**Gap Name:** HypothesisRegistry  
**Coverage today:** ~10%

**What partially exists:**  
`iios/knowledge/graph/knowledge_graph.py` — an enterprise knowledge graph framework exists but is in the enterprise IIOS framework (`iios/`), completely disconnected from the trading brain's research pipeline. It has no entries related to research hypotheses or study findings.

`data/discovered_edges.json` — tracks discovered trading edges but only for market patterns, not research hypotheses or their lifecycle.

**What's missing:**  
No single registry tracks:
- Open research questions with their source (e.g., "Why does win rate drop to 22% in TRENDING_DOWN?")
- Study assignments (which study is testing which hypothesis)
- Finding status: OPEN / ACTIVE / TESTED / PROMOTED / REJECTED / INCONCLUSIVE
- Evidence chain: which studies contributed to a finding
- Contradictions between studies

**Specific capabilities missing:**
1. `register(hypothesis: Hypothesis) → HypothesisID`
2. `update_status(id, status, evidence_refs)`
3. `get_open_hypotheses() → List[Hypothesis]`
4. `get_by_regime(regime) → List[Hypothesis]`
5. `detect_contradictions() → List[Contradiction]`
6. `get_evidence_chain(id) → List[StudyRef]`

**Required new component:** `autonomous_research/hypothesis_registry.py` + `data/ars_hypothesis_registry.json`  
**Estimated LOC:** ~250  
**Classification:** NEW (existing knowledge_graph is in wrong layer and incompatible schema)

---

## Gap 3 — Performance-Triggered Research

**Gap Name:** PerformanceTrigger  
**Coverage today:** ~20%

**What partially exists:**  
`learning_system/learning_engine.py` — fires `STRATEGY_DISABLED` events when a strategy underperforms.  
`meta_learning/regime_strategy_map.py` — tracks win rates per regime.  
`learning_system/daily_self_evaluation.py` — runs daily self-audit checks.

None of these trigger ARS research. The LearningEngine knows a strategy is underperforming but doesn't ask "why?" or initiate a study.

**What's missing:**  
A component that:
- Monitors live system performance continuously (not just EOD)
- Detects specific degradation patterns that warrant research (e.g., win rate <30% for 5+ sessions in regime X)
- Translates degradation signals into specific research questions
- Prioritizes urgent research (strategy failed in live trading) vs. exploratory research

**Degradation patterns to monitor:**
```
strategy_win_rate[strategy][regime] < 30% for N consecutive sessions
regime_performance[regime]["avg_r"] < 0.0 for M sessions  
pattern_confidence[pattern] degraded > 15% vs. discovery confidence
market_regime shifts > 2x per week (instability → research trigger)
sector conviction consistently near 0 (breadth failure)
```

**Required new component:** `autonomous_research/performance_trigger.py`  
**Estimated LOC:** ~150  
**Classification:** EXTEND (requires 3 new hooks in LearningEngine, RegimeStrategyMap, and MetaLearning — but the trigger logic itself is new)

---

## Gap 4 — Cross-Study Knowledge Synthesis

**Gap Name:** CrossStudySynthesizer  
**Coverage today:** 0%

**What's missing:**  
Studies 001, 001A, 002, 2A have been executed and produced `data/study*.json` result files. None of these findings have been synthesized into:
- A unified platform knowledge base
- Cross-study contradictions analysis (e.g., RE001A showed 0.8% threshold works; Study 2A shows 1.0% is natural breakpoint — do these conflict?)
- Actionable signals to the live trading system (Study 2A found atr_14 > 0.029 is a Winner DNA marker — this is NOT currently used as a filter in OpportunityEngine)
- Research recommendations for subsequent studies

**Specific capabilities missing:**
1. `load_study_results(study_id) → StudyResult`
2. `synthesize(study_results: List[StudyResult]) → KnowledgeBase`
3. `detect_contradictions(kb: KnowledgeBase) → List[Contradiction]`
4. `extract_actionable_insights(kb) → List[PlatformGuidance]`
5. `generate_next_study_recommendations(kb) → List[StudyHypothesis]`
6. `update_platform_filters(insights)` — proposes (but does NOT automatically apply) updates to OpportunityEngine parameters

**Note on "update_platform_filters":** This must propose, not apply. Any parameter change to a live system must go through the human approval gate and the ARCHITECTURE.md change policy.

**Required new component:** `autonomous_research/knowledge_synthesizer.py` + `data/ars_knowledge_base.json`  
**Estimated LOC:** ~300  
**Classification:** NEW (no existing foundation)

---

## Gap 5 — Autonomous Research Scheduling

**Gap Name:** ResearchScheduler  
**Coverage today:** ~30%

**What partially exists:**  
`orchestrator/master_orchestrator.py` — has a 10-slot daily scheduler for trading activities. Has `_do_eod_learning()` which triggers EdgeDiscovery.  
`orchestrator/weekend_intelligence.py` — weekend-specific coordinator.  
`communication/task_queue.py` — can schedule tasks at Priority.LOW.

**What's missing:**  
No autonomous calendar that:
- Defines a regular research cadence (weekly DNA update, monthly cross-study synthesis, quarterly strategy evolution)
- Tracks which studies are due vs. complete vs. overdue
- Prevents over-scheduling (no more than 1 heavy computation study per weekend)
- Adapts schedule based on market events (suppress research during high-VIX periods, schedule diagnostic studies after strategy failures)

**Schedule template needed:**
```
Daily  (EOD, Priority.LOW):      PerformanceTrigger check
Weekly (Saturday 10:00):         EdgeDiscovery run + DNA pattern update
Monthly (1st Saturday):          Cross-study synthesis + KnowledgeBase update
Quarterly (first month-end):     Full regime study, strategy evolution run
On-demand (triggered):           Diagnostic study when performance drops
```

**Required new component:** `autonomous_research/research_scheduler.py` + `data/ars_research_schedule.json`  
**Estimated LOC:** ~200  
**Classification:** EXTEND (uses existing TaskQueue + MasterOrchestrator scheduler; adds research-specific calendar logic)

---

## Gap 6 — Automated Research Report Generation

**Gap Name:** ResearchReportGenerator  
**Coverage today:** ~60%

**What partially exists:**  
6 study report documents were generated in Study 2A (WINNER_DNA_REPORT.md, FEATURE_IMPORTANCE_REPORT.md, etc.) but were written manually by analyzing `study002a_results.json`. The format and content structure are well-established but not automated.

**What's missing:**  
A component that:
- Reads `ars_study_*.json` results
- Applies report templates established in Studies 001–2A
- Generates structured Markdown reports automatically
- Tracks which reports exist vs. are pending
- Publishes `STUDY_COMPLETE` events with report paths

**Required new component:** `autonomous_research/report_generator.py`  
**Estimated LOC:** ~200  
**Classification:** NEW (trivial: template-based generation from existing JSON schema)

---

## Summary: True Gap Inventory

| Gap | Name | LOC | Classification |
|---|---|---|---|
| 1 | ResearchDirectorAI | ~400 | NEW |
| 2 | HypothesisRegistry | ~250 | NEW |
| 3 | PerformanceTrigger | ~150 | EXTEND |
| 4 | CrossStudySynthesizer | ~300 | NEW |
| 5 | ResearchScheduler | ~200 | EXTEND |
| 6 | ResearchReportGenerator | ~200 | NEW |
| **Total** | | **~1,500** | |

Plus minor extensions to 6 existing modules: ~165 LOC.

**Grand total new/modified code: ~1,665 LOC** in a ~150,000 LOC codebase = **~1.1% of codebase**.

---

## What Is NOT a Gap (Common Misperceptions)

| Perceived Gap | Reality | Evidence |
|---|---|---|
| "We need a new feature extraction system" | Already exists | `edge_discovery/feature_extractor.py` + `study002a_pipeline.py` |
| "We need to build walk-forward testing" | Already exists (production) | `performance/walk_forward_tester.py` |
| "We need Monte Carlo simulation" | Already exists (1,000 runs, integrated) | `market_simulation/simulation_engine.py` |
| "We need a strategy promotion pipeline" | Already exists (6-stage, protected) | `validation_engine/` |
| "We need a pattern miner" | Already exists (sklearn DT, integrated) | `edge_discovery/pattern_miner.py` |
| "We need a learning system" | Already exists (EOD, automated) | `learning_system/` |
| "We need a research sandbox" | Already exists | `research_lab/research_lab.py` |
| "We need statistical significance tests" | Already exists (wrapped in study002a) | `study002a_pipeline.py` (scipy, sklearn) |
| "We need cluster analysis" | Already exists (wrapped in study002a) | `study002a_pipeline.py` (KMeans) |
| "We need a research data store" | Convention established, 4+ result files exist | `data/study*.json`, `data/re001*.json` |

---

*ARS Gap Analysis | 2026-08-03 | Only genuine gaps listed*
