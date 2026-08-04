# System Inventory
## AR-001 Part 1: Complete Platform Module Catalogue

**Date:** 2026-08-04

---

## 1. Package Inventory (27 packages)

| # | Package | Layer | Primary Responsibility |
|---|---|---|---|
| 1 | `global_intelligence` | Layer 1 | Overnight global macro context (S&P, Nikkei, bonds, FX, sentiment) |
| 2 | `market_intelligence` | Layer 2 | NIFTY/BANKNIFTY regime, sector, liquidity, events |
| 3 | `market_learning` | Phases 1–5B | 8-phase market learning and DNA system |
| 4 | `meta_learning` | Layer 3 | k-NN strategy weight prediction |
| 5 | `opportunity_engine` | Layer 4 | Equity scanner, options, arbitrage |
| 6 | `strategy_lab` | Layer 5 | Strategy generation, evolution, backtest |
| 7 | `capital_risk_engine` | Layer 6 | Position sizing, liquidity, correlation |
| 8 | `risk_control` | Layer 7 | Pre-execution veto, portfolio allocation, stress |
| 9 | `market_simulation` | Layer 8 | Monte Carlo, 14 scenarios |
| 10 | `risk_guardian` | Layer 9 | Kill-switch (VIX>45, daily loss >2%) |
| 11 | `debate_system` | Layer 10 | 5-agent debate, threshold 6.5 |
| 12 | `decision_ai` | Layer 10 | Final order/skip decision |
| 13 | `execution_engine` | Layer 11 | Order lifecycle, paper journal, broker wrappers |
| 14 | `trade_monitoring` | Layer 12 | Live trade health, strategy health |
| 15 | `learning_system` | Layer 13 | EOD learning, win-rate tracking, self-evaluation |
| 16 | `performance` | Layer 14 | Sharpe, Sortino, drawdown, walk-forward |
| 17 | `research_lab` | Layer 15 | Promotion gates (WR ≥50%, Sharpe >0.8, DD <15%) |
| 18 | `validation_engine` | Layer 16 | 6-stage validation pipeline |
| 19 | `system_monitor` | Layer 17 | Per-layer latency, health monitoring |
| 20 | `control_tower` | Layer 17 | SQLite telemetry, Streamlit dashboard |
| 21 | `data_feeds` | Infrastructure | Feed router, fallback, integrity |
| 22 | `database` | Infrastructure | SQLite CRUD operations |
| 23 | `data_integrity` | Infrastructure | Validation, anomaly detection |
| 24 | `communication` | Infrastructure | EventBus, MessageRouter, TaskQueue |
| 25 | `models` | Infrastructure | Canonical data models |
| 26 | `utils` | Infrastructure | Helpers, logger, kill-switch, PID lock |
| 27 | `notifications` | Infrastructure | Telegram bot (13 commands) |
| — | `orchestrator` | Cross-cutting | 17-layer coordinator, scheduler |
| — | `edge_discovery` | Research | Edge discovery (not wired to trading) |
| — | `autonomous_research` | Research | ARS — roadmap, studies, hypotheses |
| — | `iios` | Future | IIOS framework skeleton |
| — | `analysis` | Tooling | 57 analytics and audit files |

---

## 2. AI Agent Inventory (62 agents)

### Layer 1 — Global Intelligence (7 agents)
| Agent | Class | Output |
|---|---|---|
| GlobalIntelligenceEngine | `GlobalIntelligenceEngine` | GlobalSnapshot |
| GlobalDataAI | `GlobalDataAI` | S&P/Nikkei/bonds/FX data |
| GlobalSentimentAI | `GlobalSentimentAI` | SentimentScore [-1,+1] |
| MacroSignalAI | `MacroSignalAI` | InflationRisk, LiquidityCondition |
| PremarketBiasAI | `PremarketBiasAI` | NiftyBias, overnight gap |
| CorrelationEngine | `CorrelationEngine` | CorrelationResult |
| MarketDistortionScanner | `MarketDistortionScanner` | DistortionResult, BehaviorOverrides |

### Layer 2 — Market Intelligence (7 agents)
| Agent | Class | Output |
|---|---|---|
| MarketMonitor | `MarketMonitor` | Continuous regime updates (30s) |
| MarketDataAI | `MarketDataAI` | Aggregated quotes |
| MarketRegimeAI | `MarketRegimeAI` | RegimeLabel (BULL/BEAR/RANGE/VOLATILE) |
| RegimeProbabilityModel | `RegimeProbabilityModel` | RegimeProbabilities |
| LiquidityAI | `LiquidityAI` | LiquidityScore |
| SectorRotationAI | `SectorRotationAI` | SectorRanking |
| EventDetectionAI | `EventDetectionAI` | EventTriggers |

### Layer 3 — Meta-Learning (6 agents)
| Agent | Class | Output |
|---|---|---|
| MetaLearningEngine | `MetaLearningEngine` | Strategy weights |
| RegimeStrategyMap | `RegimeStrategyMap` | Regime→strategy mapping |
| StrategyWeightPredictor | `StrategyWeightPredictor` | StrategyAllocation |
| MetaModel | `MetaModel` | k-NN neighbors |
| FeatureExtractor | `FeatureExtractor` | FeatureVector (6-dim) |
| TrainingEngine | `TrainingEngine` | Trained model state |

### Layer 4 — Opportunity Engine (4 agents)
| Agent | Class | Output |
|---|---|---|
| EquityScannerAI | `EquityScannerAI` | Breakout candidates |
| OptionsOpportunityAI | `OptionsOpportunityAI` | Options opportunities |
| ArbitrageAI | `ArbitrageAI` | Arb opportunities |
| CandidateStore | `CandidateStore` (SINGLETON) | Ranked candidate list |

### Layer 5 — Strategy Lab (4 agents)
| Agent | Class | Output |
|---|---|---|
| StrategyGeneratorAI | `StrategyGeneratorAI` | Strategy configs |
| StrategyEvolutionAI | `StrategyEvolutionAI` | Evolved variants |
| BacktestingAI | `BacktestingAI` | BacktestResult |
| MetaStrategyController | `MetaStrategyController` | Active strategy list |

### Layer 6 — Capital / Risk (6 agents)
| Agent | Class | Output |
|---|---|---|
| CapitalRiskEngine | `CapitalRiskEngine` | Position size, budget |
| LiquidityGuard | `LiquidityGuard` | PASS/REJECT with reason |
| RiskManagerAI | `RiskManagerAI` | PreExecution approval/veto |
| PortfolioAllocationAI | `PortfolioAllocationAI` | Portfolio balance |
| StressTestAI | `StressTestAI` | Stress result |
| SmartExecutionEngine | `SmartExecutionEngine` | Optimised order params |

### Layer 7 — Risk Control (1 agent)
| Agent | Class | Output |
|---|---|---|
| OptionsRiskEngine | `OptionsRiskEngine` (SINGLETON) | Greeks, PnL attribution |

### Layer 8 — Simulation (3 agents)
| Agent | Class | Output |
|---|---|---|
| SimulationEngine | `SimulationEngine` | MonteCarloResult |
| ScenarioGenerator | (inline) | 14 scenario set |
| StrategyResilienceAI | `StrategyResilienceAI` | ResilienceScore |

### Layer 9 — Risk Guardian (1 agent)
| Agent | Class | Output |
|---|---|---|
| FailSafeRiskGuardian | `FailSafeRiskGuardian` | GuardianDecision (GO/HALT) |

### Layer 10 — Debate & Decision (2 agents)
| Agent | Class | Output |
|---|---|---|
| MultiAgentDebate | `MultiAgentDebate` | Conviction score (0–10) |
| DecisionEngine | `DecisionEngine` | ORDER/SKIP with reason |

### Layer 11 — Execution (4 agents)
| Agent | Class | Output |
|---|---|---|
| OrderManager | `OrderManager` (SINGLETON) | OrderRecord |
| OptionsOrderManager | `OptionsOrderManager` (SINGLETON) | OptionsOrderRecord |
| ZerodhaBroker | `ZerodhaBroker` | Order fill confirmation |
| DhanBroker | `DhanBroker` | Order fill (+ fallback) |

### Layers 12–17 (12 agents)
| Agent | Class | Output |
|---|---|---|
| TradeMonitor | `TradeMonitor` | Position health |
| StrategyHealthMonitor | `StrategyHealthMonitor` | HealthStatus |
| LearningEngine | `LearningEngine` | Strategy weight mutations |
| StrategyPerformanceTracker | (SINGLETON) | WinRate, Sharpe, DD |
| OptionsPerformanceTracker | (SINGLETON) | Options stats |
| DailyAISelfEvaluator | `DailyAISelfEvaluator` | SelfEvalResult (A–F) |
| PerformanceEvaluator | `PerformanceEvaluator` | Sharpe, Sortino |
| ResearchLab | `ResearchLab` | Promotion gate result |
| ValidationEngine | Orchestrator | 6-stage ValidationReport |
| SystemMonitor | `SystemMonitor` | LayerTiming, HealthReport |
| EventBus | (SINGLETON) | Event dispatch |
| MessageRouter | (SINGLETON) | Agent messages |

### MLS Agents (8 phases)
| Phase | Agent | Output |
|---|---|---|
| 1 | MarketObserver | DailyMarketSnapshot, MarketObservation |
| 2 | PopulationClassifier | Population (WINNER/LOSER/NEUTRAL) |
| 3 | DNADiscoveryEngine | WinnerDNA, LoserDNA, DiscoveryReport |
| 4 | DNAConsensusEngine | ConsensusLibrary, ConsensusDNA |
| 5 | PMCIEngine | PMCIResult (pmci_score [0,1]) |
| 5A | MCIEngine | MarketContext (context_score [0,1]) |
| 5A.1 | CDSEngine | ContextualDNAScore, DNARelevance |
| 5B | CAPMCIEngine | CAPMCIResult (ca_pmci [0,1]) |

---

## 3. Scheduler Inventory

| Time (IST) | Job | Layer |
|---|---|---|
| 08:45 | `premarket_refiner` | Layer 4 |
| 09:05 | `market_open_regime` | Layer 2 |
| 09:10 | `first_opportunity_scan` | Layer 4 |
| 09:20 | `strategy_evaluation` | Layer 5 |
| 09:45 | `trade_decision` | Layer 10–11 |
| 10:30 | `mid_morning_scan` | Layers 2,4 |
| 11:30 | `mid_session_scan` | Layers 2,4 |
| 13:00 | `afternoon_scan` | Layers 2,4 |
| 14:00 | `early_afternoon_scan` | Layers 2,4 |
| 15:00 | `closing_analysis` | Layers 2,4,10 |
| 15:35 | `eod_learning` | Layer 13 |
| 16:45 | `post_market_scan` | Layer 4 |
| Sat 08:00 | `saturday_intelligence` | Weekend |
| Sun 09:00 | `sunday_intelligence` | Weekend |
| Continuous | `market_monitor` (30s) | Layer 2 |

---

## 4. Persistent Database Inventory (14 SQLite files)

| File | Primary Tables | Owner | Status |
|---|---|---|---|
| `trading_brain.db` | trades, positions, signals, orders | DBManager | Active |
| `control_tower.db` | events, layer_timings, health | SystemMonitor | Active |
| `options_audit.db` | options_trades, greeks, pnl | OptionsRiskEngine | Active |
| `trade_quality.db` | quality_scores, rejections | TradeClassifier | Active |
| `iios.db` | decisions, governance | IIOS framework | Active (skeleton) |
| `live_observations.db` | market_snapshots, ticks | MarketObserver | Active |
| `news_audit.db` | news_items, event_impacts | EventDetectionAI | Active |
| `recommendations.db` | recommendations, actions | ResearchLab | Active |
| `real_options_audit.db` | option_trades, exercises | OptionsOrderManager | Active |
| `replay.db` | replay_trades, scenarios | Replay engine | Active |
| `study002_replay.db` | study_trades, outcomes | AR Study 002 | Historical |
| `re001_replay.db` | replay_outcomes | RE001 | Historical |
| `strategy_performance.db` | strategy_performance | LearningSystem (legacy) | Legacy |
| `rejection_audit.db` | rejections, reasons | OpportunityEngine | Active |

---

## 5. Singleton Registry

| Singleton | Module | State |
|---|---|---|
| `get_performance_tracker()` | `learning_system.strategy_performance_tracker` | JSON + SQLite |
| `get_regime_strategy_map()` | `meta_learning.regime_strategy_map` | JSON |
| `get_telegram_bot()` | `notifications.telegram_bot` | In-memory |
| `get_feed_manager()` | `data_feeds.data_feed_manager` | In-memory |
| `CandidateStore` | `opportunity_engine.candidate_store` | JSON |
| `OrderManager` | `execution_engine.order_manager` | CSV + memory |
| `OptionsOrderManager` | `execution_engine.options_order_manager` | JSON + memory |
| `OptionsRiskEngine` | `risk_control.options_risk_engine` | In-memory |
| `OptionsPerformanceTracker` | `learning_system.options_performance_tracker` | JSON |
| `InvalidationTracker` | `opportunity_engine.invalidation_tracker` | JSON |
| `MarketDataRouter` | `data_feeds.market_data_router` | In-memory |
| `DataIntegrityTracker` | `data_feeds.data_integrity_tracker` | JSON |
| `FalseBreakoutTracker` | `data_feeds.false_breakout_tracker` | JSON |
| `ScalarNormalizationAudit` | `utils.scalar_audit` | JSON |
| `EventBus` | `communication.event_bus` | In-memory |
| `MessageRouter` | `communication.message_router` | In-memory |
| `AgentMemory` | `communication.agent_memory` | JSON |
| `TaskQueue` | `communication.task_queue` | In-memory |

Total: **18 singletons**
