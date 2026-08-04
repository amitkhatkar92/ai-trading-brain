# AI Agent Audit
## AR-001 Part 6: Complete Agent Inventory — Responsibilities, Consumers, Overlaps

**Date:** 2026-08-04

---

## 1. Audit Scope

Every AI agent and engine in the platform is audited against four criteria:

| Criterion | Question |
|---|---|
| **Responsibility** | Is the agent's responsibility single and clear? |
| **Consumer** | Is there at least one confirmed consumer of the agent's output? |
| **Overlap** | Does the agent duplicate work performed by another agent? |
| **Integration** | Is the agent wired into the production trading path? |

Legend: ✅ = met | ⚠️ = partial | ❌ = not met

---

## 2. Layer-by-Layer Agent Audit

### Layer 1 — Global Intelligence

| Agent | Single Responsibility | Has Consumer | No Overlap | In Prod Path |
|---|---|---|---|---|
| `GlobalIntelligenceEngine` | ✅ Orchestrates L1 | ✅ Orchestrator reads | ✅ | ✅ |
| `GlobalDataAI` | ✅ Fetches global data | ✅ GlobalIntelligenceEngine | ✅ | ✅ |
| `GlobalSentimentAI` | ✅ Sentiment scoring | ✅ GlobalIntelligenceEngine | ✅ | ✅ |
| `MacroSignalAI` | ✅ Macro indicators | ✅ GlobalIntelligenceEngine | ✅ | ✅ |
| `PremarketBiasAI` | ✅ Overnight gap | ✅ GlobalIntelligenceEngine | ✅ | ✅ |
| `CorrelationEngine` (L1) | ⚠️ Same as L6 and L7 copies | ✅ GlobalIntelligenceEngine | ❌ (3 copies) | ✅ |
| `MarketDistortionScanner` | ✅ Anomaly detection | ⚠️ Output stored but unclear if consumed | ✅ | ⚠️ |

### Layer 2 — Market Intelligence

| Agent | Single Responsibility | Has Consumer | No Overlap | In Prod Path |
|---|---|---|---|---|
| `MarketMonitor` | ✅ 30s continuous scan | ✅ Feeds orchestrator | ✅ | ✅ |
| `MarketDataAI` | ✅ Quote aggregation | ✅ Multiple consumers | ✅ | ✅ |
| `MarketRegimeAI` | ✅ Regime classification | ✅ MetaLearning + OpportunityEngine | ✅ | ✅ |
| `RegimeProbabilityModel` | ✅ Confidence weighting | ⚠️ Unclear if DecisionEngine uses probability | ✅ | ⚠️ |
| `LiquidityAI` | ✅ Volume/spread analysis | ✅ CapitalRiskEngine | ✅ | ✅ |
| `SectorRotationAI` | ✅ Sector ranking | ✅ OpportunityEngine | ✅ | ✅ |
| `EventDetectionAI` | ✅ Calendar monitoring | ⚠️ Output to news_audit.db but trade impact unclear | ✅ | ⚠️ |

### Layer 3 — Meta-Learning

| Agent | Single Responsibility | Has Consumer | No Overlap | In Prod Path |
|---|---|---|---|---|
| `MetaLearningEngine` | ✅ k-NN weight predictor | ✅ MetaStrategyController | ✅ | ✅ |
| `RegimeStrategyMap` | ✅ Regime→weight mapping | ✅ Orchestrator reads | ✅ | ✅ |
| `StrategyWeightPredictor` | ✅ k-NN prediction | ✅ MetaLearningEngine | ✅ | ✅ |
| `MetaModel` | ✅ Feature space | ✅ StrategyWeightPredictor | ✅ | ✅ |
| `FeatureExtractor` | ✅ Signal extraction | ✅ MetaModel | ⚠️ May re-derive regime | ✅ |
| `TrainingEngine` | ✅ Offline training | ⚠️ Training not triggered in production scheduler | ✅ | ⚠️ |

**Observation:** `TrainingEngine` is not in any scheduled job. Meta-learning
model parameters are static after last training run unless training is triggered
manually or via weekend intelligence cycle.

### Layer 4 — Opportunity Engine

| Agent | Single Responsibility | Has Consumer | No Overlap | In Prod Path |
|---|---|---|---|---|
| `EquityScannerAI` | ✅ Breakout detection | ✅ CandidateStore | ✅ | ✅ |
| `OptionsOpportunityAI` | ✅ Options scoring | ✅ OptionsOrderManager | ✅ | ✅ |
| `ArbitrageAI` | ✅ Stat arb | ⚠️ Uncertain if results flow to execution | ✅ | ⚠️ |
| `CandidateStore` | ✅ Lifecycle management | ✅ CapitalRiskEngine + DecisionEngine | ✅ | ✅ |
| `OpportunityDensityMonitor` | ✅ Budget enforcement | ✅ Scanner | ✅ | ✅ |

### Layer 5 — Strategy Lab

| Agent | Single Responsibility | Has Consumer | No Overlap | In Prod Path |
|---|---|---|---|---|
| `StrategyGeneratorAI` | ✅ Strategy generation | ✅ MetaStrategyController | ✅ | ✅ |
| `StrategyEvolutionAI` | ✅ Genetic evolution | ✅ Produces evolved_strategies.json | ✅ | ⚠️ Evolution runs not scheduled |
| `BacktestingAI` | ✅ Backtest engine | ✅ ResearchLab + ValidationEngine | ⚠️ (3 WFT impls) | ✅ |
| `MetaStrategyController` | ✅ Strategy selection | ✅ CapitalRiskEngine | ✅ | ✅ |

**Observation:** Strategy evolution is not on the production scheduler.
The system uses pre-evolved strategies. New evolution requires manual trigger.

### Layers 6–9 — Risk Layers

| Agent | Single Responsibility | Has Consumer | No Overlap | In Prod Path |
|---|---|---|---|---|
| `CapitalRiskEngine` | ✅ Per-strategy sizing | ✅ RiskManagerAI | ✅ | ✅ |
| `LiquidityGuard` | ✅ ADV checks | ✅ CapitalRiskEngine | ✅ | ✅ |
| `RiskManagerAI` | ✅ Pre-exec veto | ✅ DecisionEngine | ✅ | ✅ |
| `PortfolioAllocationAI` | ✅ Multi-strategy balance | ✅ CapitalRiskEngine | ✅ | ✅ |
| `StressTestAI` | ✅ Pre-exec stress | ✅ RiskManagerAI | ⚠️ (overlaps SimulationEngine) | ✅ |
| `SmartExecutionEngine` | ✅ Execution optimisation | ✅ OrderManager | ✅ | ✅ |
| `OptionsRiskEngine` | ✅ Options Greeks/PnL | ✅ OptionsOrderManager | ✅ | ✅ |
| `SimulationEngine` | ✅ MC simulation | ✅ Orchestrator | ✅ | ✅ |
| `FailSafeRiskGuardian` | ✅ Final kill-switch | ✅ Orchestrator | ✅ | ✅ |

### Layers 10–11 — Decision & Execution

| Agent | Single Responsibility | Has Consumer | No Overlap | In Prod Path |
|---|---|---|---|---|
| `MultiAgentDebate` | ✅ 5-agent conviction | ✅ DecisionEngine | ✅ | ✅ |
| `DecisionEngine` | ✅ ORDER/SKIP | ✅ OrderManager | ✅ | ✅ |
| `OrderManager` | ✅ Order lifecycle | ✅ Brokers | ✅ | ✅ |
| `OptionsOrderManager` | ✅ Options orders | ✅ Brokers | ✅ | ✅ |

### Layers 12–17 — Monitoring, Learning, Validation

| Agent | Single Responsibility | Has Consumer | No Overlap | In Prod Path |
|---|---|---|---|---|
| `TradeMonitor` | ✅ Live position health | ✅ Orchestrator | ✅ | ✅ |
| `StrategyHealthMonitor` | ✅ Strategy health | ✅ LearningEngine | ✅ | ✅ |
| `LearningEngine` | ✅ Weight mutation | ✅ RegimeStrategyMap | ✅ | ✅ |
| `StrategyPerformanceTracker` | ✅ Win rate tracking | ✅ LearningEngine | ✅ | ✅ |
| `DailyAISelfEvaluator` | ✅ Performance grading | ✅ TelegramBot reports | ✅ | ✅ |
| `PerformanceEvaluator` | ✅ Sharpe/DD metrics | ✅ ResearchLab + ValidationEngine | ✅ | ✅ |
| `ResearchLab` | ✅ Promotion gates | ✅ StrategyLab | ✅ | ✅ |
| `ValidationEngine` | ✅ 6-stage validation | ✅ ResearchLab | ✅ | ✅ |
| `SystemMonitor` | ✅ Latency tracking | ✅ Orchestrator | ✅ | ✅ |

---

## 3. MLS Agents Audit

| Agent | Single Responsibility | Has Consumer | No Overlap | In Prod Path |
|---|---|---|---|---|
| `MarketObserver` | ✅ Daily observation | ✅ PopulationClassifier | ✅ | ❌ Not scheduled |
| `PopulationClassifier` | ✅ Winner/loser labels | ✅ DNADiscoveryEngine | ✅ | ❌ Not scheduled |
| `DNADiscoveryEngine` | ✅ Pattern discovery | ✅ DNAConsensusEngine | ✅ | ❌ Not scheduled |
| `DNAConsensusEngine` | ✅ Consensus library | ✅ CDSEngine | ✅ | ❌ Not scheduled |
| `PMCIEngine` | ✅ Probabilistic context | ❌ No trading consumer | ✅ | ❌ |
| `MCIEngine` | ✅ Market context index | ✅ PMCIEngine + CDSEngine | ✅ | ❌ Not scheduled |
| `CDSEngine` | ✅ Contextual DNA score | ❌ No trading consumer | ✅ | ❌ |
| `CAPMCIEngine` | ✅ Context-adjusted PMCI | ❌ No trading consumer | ✅ | ❌ |

**Critical finding:** All 8 MLS agents produce valid output but **none are
integrated into the production trading schedule.** GAP-001 in KNOWLEDGE_FLOW_REVIEW.md.

---

## 4. Research & Auxiliary Agents

| Agent | Purpose | In Prod Path | Action |
|---|---|---|---|
| `EdgeDiscoveryEngine` | Market edge discovery | ❌ | See GAP-002 |
| `EdgeRankingEngine` | Edge ranking | ❌ | See GAP-002 |
| `RoadmapManager` | AR roadmap | ❌ | See GAP-003 |
| `StudyPlanner` | Study scheduling | ❌ | See GAP-003 |
| `HypothesisRegistry` | Hypothesis tracking | ❌ | See GAP-003 |
| `EvidenceValidator` | Evidence validation | ❌ | See GAP-003 |
| `GapDetector` | Knowledge gaps | ❌ | See GAP-003 |
| `KnowledgeProvider` | Knowledge synthesis | ❌ | See GAP-003 |
| `WeekendIntelligenceEngine` | Weekend deep cycles | ✅ Weekend schedule | ✅ |

---

## 5. Summary Statistics

| Metric | Value |
|---|---|
| Total agents inventoried | 62 |
| Agents fully integrated (prod path) | 44 |
| Agents partially integrated | 8 |
| Agents isolated (no prod path) | 10 |
| Agents with confirmed consumer | 54 |
| Agents with suspected orphan output | 8 |
| Duplicate responsibility (CorrelationEngine) | 3 |
