# SCIENTIFIC DIRECTOR — ARCHITECTURE
## ARS Phase 0 Design Document

**Status:** FROZEN  
**Phase:** 0 — Architecture Design (no production code)  
**Date:** 2026-08-03  
**Basis:** ARS_ARCHITECTURE_AUDIT.md + ARS_REUSE_ANALYSIS.md + full source code analysis of 23 IIOS modules

---

## PART 1 — Responsibilities

The Scientific Director is the autonomous research coordinator for the IIOS platform. It owns the research lifecycle from knowledge gap identification through validated finding integration. It does NOT own any trading decision.

### 1.1 Primary Responsibilities

| # | Responsibility | Precise Scope |
|---|---|---|
| R-01 | **Read completed studies** | Load `data/study*.json`, `data/re*.json`, `data/ars_study_*.json` into working memory. Assess completeness and quality. |
| R-02 | **Read knowledge stores** | Read `learning_db.json`, `strategy_performance.json`, `discovered_edges.json`, `regime_probability_history.json`, `evolved_strategies.json` (read-only). Build unified knowledge snapshot. |
| R-03 | **Monitor research quality** | Evaluate completed studies for minimum sample size, WF pass rate, statistical significance, economic significance. Flag low-quality findings. |
| R-04 | **Identify knowledge gaps** | Detect: regimes with <30% win rate and no assigned study, feature spaces not yet analysed, patterns with degrading confidence, temporal gaps in historical coverage. |
| R-05 | **Prioritise research** | Score open hypotheses by: expected information gain, study cost, dependency order, urgency (is live trading currently impacted?). Maintain a ranked agenda. |
| R-06 | **Generate hypotheses** | Translate each knowledge gap into a specific, testable, falsifiable hypothesis. Register in HypothesisRegistry. |
| R-07 | **Plan studies** | For each approved hypothesis: select data source, feature set, validation method, minimum confidence threshold, expected output format. |
| R-08 | **Assign work to existing modules** | Delegate to: EdgeDiscoveryEngine (pattern mining), study_executor (complex pipelines), ValidationEngine (promotion gating), ResearchLab (sandbox), performance/ (WF testing). |
| R-09 | **Integrate results** | Collect completed study outputs. Apply EvidenceValidator quality gates. If passing: update `ars_knowledge_base.json`. If failing: mark hypothesis INCONCLUSIVE or NEEDS_MORE_DATA. |
| R-10 | **Update research roadmap** | Mark each hypothesis TESTED / PROMOTED / REJECTED / INCONCLUSIVE. Generate follow-up hypotheses if warranted. Publish `STUDY_COMPLETE` EventBus event. |
| R-11 | **Generate research reports** | Produce structured Markdown report for each completed study (following Study 2A report format). |
| R-12 | **Propose platform guidance** | Translate validated findings into actionable parameter proposals for human review. Write to `data/ars_proposals/`. Never apply automatically. |

### 1.2 Responsibility Boundary

```
┌─────────────────────────────────────────────────────┐
│             SCIENTIFIC DIRECTOR OWNS                 │
│                                                      │
│  Research agenda  ← Read knowledge                  │
│  Gap detection    ← Analyse performance              │
│  Hypotheses       ← Generate from gaps              │
│  Study plans      ← Design before execution         │
│  Delegation       ← Assign to existing modules      │
│  Quality gates    ← Validate study results          │
│  Knowledge base   ← Synthesise findings             │
│  Proposals        ← Propose (never apply)           │
│  Roadmap          ← Track research progress         │
└─────────────────────────────────────────────────────┘

        ↑ OUTPUT only. Never crosses this line. ↑

┌─────────────────────────────────────────────────────┐
│          EXISTING IIOS MODULES OWN (unchanged)      │
│                                                      │
│  Trade execution   → ExecutionEngine                │
│  Strategy logic    → StrategyLab + ResearchLab      │
│  Risk enforcement  → RiskGuardian                   │
│  Live decisions    → DecisionEngine                 │
│  Pattern mining    → EdgeDiscoveryEngine            │
│  Validation        → ValidationEngine               │
│  Position sizing   → CapitalRiskEngine              │
│  Model training    → MetaLearning                   │
│  Historical data   → replay.db                      │
└─────────────────────────────────────────────────────┘
```

---

## PART 2 — Non-Responsibilities

These are explicitly prohibited. If any implementation step requires the Scientific Director to cross these boundaries, the design is wrong and must be reconsidered before writing code.

| # | Prohibited Action | Reason | Owner |
|---|---|---|---|
| NR-01 | Execute or approve trades | Trading decisions follow a separate pipeline with its own kill-switch | ExecutionEngine + RiskGuardian |
| NR-02 | Modify strategies directly | Strategies are promoted through a 6-stage validation pipeline — the Director feeds that pipeline, never bypasses it | ValidationEngine → StrategyLab |
| NR-03 | Change risk thresholds | Kill-switch conditions are intentional and load-bearing | risk_guardian/ (PROTECTED) |
| NR-04 | Retrain AI models | k-NN meta model, debate agent weights, and decision thresholds are calibrated and stable | meta_learning/, debate_system/ |
| NR-05 | Modify platform architecture | Architecture changes require explicit human instruction per ARCHITECTURE.md | Human + change pipeline |
| NR-06 | Write to historical databases | `data/replay.db` and all raw market data are immutable. Research findings never corrupt source data | replay.db (READ-ONLY) |
| NR-07 | Self-approve Class B decisions | No autonomous system may approve its own proposals for live trading impact | Human gate (mandatory) |
| NR-08 | Deploy code | Code changes follow: commit → push → VPS deploy with health check | Human + git + docker |
| NR-09 | Change capital allocation | Position sizing parameters are owned by CapitalRiskEngine | CapitalRiskEngine |
| NR-10 | Disable or enable live trading | Only RiskGuardian circuit breakers or human intervention may stop trading | risk_guardian/ + main.py |
| NR-11 | Write to evolved_strategies.json directly | Strategies reach this file only through the ResearchLab → ValidationEngine promotion pipeline | validation_engine/ |
| NR-12 | Modify debate agent weights | TechnicalAnalystAI, MacroAnalystAI, RiskDebateAI weights are calibrated | debate_system/ (PROTECTED) |
| NR-13 | Modify DecisionEngine thresholds | VIX-adaptive thresholds are intentional, hand-tuned | decision_ai/ (PROTECTED) |
| NR-14 | Approve findings without evidence | Every promoted finding must pass EvidenceValidator before entering KnowledgeBase | EvidenceValidator (required) |
| NR-15 | Run studies during market hours | Research tasks run at Priority.LOW; they must not compete with critical cycle resources | TaskQueue scheduling policy |

---

## PART 4 — Decision Flow (Research Lifecycle)

```
════════════════════════════════════════════════════
  STEP 1 — KNOWLEDGE STATE
════════════════════════════════════════════════════
  KnowledgeProvider reads:
    • learning_db.json             (strategy win rates by regime)
    • strategy_performance.json    (per-strategy metrics)
    • discovered_edges.json        (active pattern confidence)
    • regime_probability_history.json (regime frequency)
    • ars_knowledge_base.json      (prior ARS findings)
    • data/study*.json             (all completed study results)
  
  Output: KnowledgeSnapshot (immutable read-only view)

════════════════════════════════════════════════════
  STEP 2 — GAP DETECTION
════════════════════════════════════════════════════
  GapDetector analyses KnowledgeSnapshot:
    • Performance gaps:  regimes where win_rate < 30%
    • Coverage gaps:     feature spaces with no study assigned
    • Temporal gaps:     regimes unstudied in last 90 days
    • Degradation gaps:  pattern confidence drop >15%
    • Contradiction gaps: study results that conflict

  Output: List[KnowledgeGap] (each gap: type, severity, regime, evidence)

════════════════════════════════════════════════════
  STEP 3 — HYPOTHESIS GENERATION
════════════════════════════════════════════════════
  For each KnowledgeGap (above severity threshold):
    HypothesisProvider.generate(gap) → Hypothesis
    HypothesisProvider.register(h)   → HypothesisID

  Each Hypothesis contains:
    • Specific, falsifiable question
    • Expected finding (null hypothesis)
    • Minimum evidence required for promotion
    • Data requirements
    • Estimated study cost
    • Dependency on prior hypotheses

  Output: List[Hypothesis] registered in HypothesisRegistry

════════════════════════════════════════════════════
  STEP 4 — PRIORITY SCORING
════════════════════════════════════════════════════
  RoadmapManager.prioritize(hypotheses):
    Score = w1 * expected_info_gain
          + w2 * urgency_score       (live trading impacted?)
          + w3 * dependency_score    (unblocks other hypotheses?)
          - w4 * estimated_cost      (data + compute hours)
          - w5 * redundancy_score    (similar study already done?)

  Output: Ranked List[Hypothesis]

════════════════════════════════════════════════════
  STEP 5 — STUDY PLANNING
════════════════════════════════════════════════════
  StudyPlanner.plan(hypothesis):
    • Select data source (replay.db window, date range, regime filter)
    • Select feature set (existing feature extractors)
    • Select validation method (WF / MC / cross-market / sensitivity)
    • Set minimum confidence, minimum sample size, minimum lift
    • Classify: Class A or Class B

  StudyPlanner.estimate_cost(plan):
    • Data rows to process
    • Estimated wall-clock time
    • Memory requirements

  Output: StudyPlan (complete specification, no ambiguity)

════════════════════════════════════════════════════
  STEP 6 — GOVERNANCE GATE
════════════════════════════════════════════════════
  If StudyPlan.governance_class == Class.A:
    → Proceed directly to Step 7
    → Log: STUDY_SCHEDULED event

  If StudyPlan.governance_class == Class.B:
    → Generate PROPOSAL_*.md in data/ars_proposals/
    → Publish APPROVAL_REQUIRED event
    → WAIT for human approval file (APPROVED_*.md)
    → If REJECTED_*.md found → mark hypothesis DEFERRED
    → Do NOT proceed until approval confirmed

════════════════════════════════════════════════════
  STEP 7 — EXECUTION (via existing IIOS modules)
════════════════════════════════════════════════════
  ResearchCoordinator.delegate(plan):
    Pattern mining   → EdgeDiscoveryEngine.mine(config)
    Complex pipeline → study_executor.run(plan)
    Validation only  → ValidationEngine.validate(candidate)
    Sandbox test     → ResearchLab.run_experiment(config)
    WF test only     → WalkForwardTester.test(strategy, data)

  All tasks submitted to TaskQueue at Priority.LOW
  Scientific Director does NOT execute algorithms directly

════════════════════════════════════════════════════
  STEP 8 — EVIDENCE VALIDATION
════════════════════════════════════════════════════
  EvidenceValidator.validate(result, plan):
    ✓ Minimum sample size met?           (configurable, default: n ≥ 100)
    ✓ WF pass rate acceptable?           (default: ≥ 60% windows)
    ✓ Statistical significance?          (p < 0.05 on key metrics)
    ✓ Economic significance?             (lift ≥ 1.3 over base rate)
    ✓ Out-of-sample performance?         (OOS within 20% of IS)
    ✓ No data snooping / lookahead?      (temporal integrity check)

  If ALL pass → ValidationVerdict.ACCEPT
  If any fail  → ValidationVerdict.REJECT with specific reason

════════════════════════════════════════════════════
  STEP 9 — KNOWLEDGE UPDATE
════════════════════════════════════════════════════
  If ACCEPT:
    CrossStudySynthesizer.add_finding(result)
    Update ars_knowledge_base.json
    HypothesisRegistry.update(id, PROMOTED, evidence)
    Publish KNOWLEDGE_UPDATED event

  If REJECT:
    HypothesisRegistry.update(id, REJECTED | INCONCLUSIVE, reason)
    If INCONCLUSIVE: generate follow-up hypothesis
    Do NOT update knowledge base

════════════════════════════════════════════════════
  STEP 10 — ROADMAP UPDATE + PROPOSALS
════════════════════════════════════════════════════
  RoadmapManager.update(hypothesis, verdict)
  RoadmapManager.add_followup(hypothesis, followup_list)

  If any actionable platform guidance found:
    Generate GUIDANCE_PROPOSAL_*.md in data/ars_proposals/
    Publish PLATFORM_GUIDANCE_PROPOSED event
    ⚠️  Do NOT apply any guidance automatically

  ResearchReportGenerator.generate(result, plan, verdict)
  → Produces RESEARCH_REPORT_*.md following Study 2A format

  Publish STUDY_COMPLETE event with report path
════════════════════════════════════════════════════
```

---

## PART 7 — Success Metrics (KPIs)

### 7.1 Research Quality KPIs

| KPI | Definition | Target | Measurement |
|---|---|---|---|
| **Knowledge Gain Rate** | New validated facts entering ars_knowledge_base.json per month | ≥ 3/month | Count of PROMOTED findings per calendar month |
| **False Hypothesis Rate** | Hypotheses rejected (not inconclusive) after full study / total hypotheses tested | < 40% | Count from HypothesisRegistry |
| **Study Success Rate** | Studies completing with actionable (PROMOTED) findings / total studies run | ≥ 60% | Count from study_results |
| **Research Efficiency** | Compute hours per validated finding | Decreasing trend | Wall-clock time logged per study |

### 7.2 Coverage KPIs

| KPI | Definition | Target | Measurement |
|---|---|---|---|
| **Gap Coverage** | Known gaps with ≥1 assigned study / total known gaps | ≥ 80% | GapDetector vs. HypothesisRegistry |
| **Regime Coverage** | Trading regimes with ≥1 validated finding / total distinct regimes observed | ≥ 70% | Cross-reference regime_probability_history with knowledge_base |
| **Feature Coverage** | Feature dimensions with measured importance / total available features | ≥ 90% | Study 2A measured 20/35; target: all 35 measured |

### 7.3 Knowledge Stability KPIs

| KPI | Definition | Target | Measurement |
|---|---|---|---|
| **Knowledge Stability** | Findings surviving 3+ months without contradiction | ≥ 70% | Age of findings in knowledge_base |
| **Contradiction Rate** | Cross-study contradictions detected per month | 0 (ideally) | CrossStudySynthesizer.detect_contradictions() |
| **Finding Longevity** | Average age of an active (non-contradicted) finding in knowledge_base | ≥ 6 months | Timestamp tracking |

### 7.4 Governance KPIs (Zero Tolerance)

| KPI | Definition | Target |
|---|---|---|
| **Human Gate Bypass Rate** | Class B studies executed without explicit human approval | **0%** |
| **Protected Module Modification Rate** | Any write to protected module during ARS cycle | **0%** |
| **Live System Side-Effect Rate** | Any unplanned modification to live trading state | **0%** |
| **Data Integrity Rate** | Writes to replay.db or paper_trades.csv | **0%** |

### 7.5 Research ROI (Quarterly)

Measured as: Change in platform win rate and expectancy attributable to strategies or parameters derived from ARS-validated findings.

Baseline: Platform win rate and expectancy as of ARS inception date.  
Target: Measurable improvement within 3 months of first Class A cycle.

---

## Summary: What the Scientific Director IS

```
Scientific Director = Thin coordination layer that:
  1. Reads what the platform knows
  2. Identifies what the platform doesn't know
  3. Generates specific testable questions
  4. Plans how to answer them (using existing tools)
  5. Delegates execution (never executes itself)
  6. Validates the answers
  7. Stores validated knowledge
  8. Proposes (never applies) improvements
  9. Updates the research roadmap
```

**Total new logic in Scientific Director core: ~400 LOC**  
**Total reused/delegated logic: ~18,000 LOC**

---

*Scientific Director Architecture | ARS Phase 0 | Frozen 2026-08-03*
