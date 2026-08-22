# ARCHITECTURE_ACTUAL_CURRENT.md
## AI Trading Brain — Verified Call Graph
### Generated: 2026-08-22 | ARCH-001 Section A
### Basis: Direct code trace of master_orchestrator.py + all callee files

---

## PRODUCTION INTRADAY CALL GRAPH

```
run_full_cycle()
│
├── ExecutionWindowGuard (L2) — blocks before 09:45 IST
├── EmergencyKillSwitch — is_trading_enabled()
├── CandidateFreshnessAudit — observational only
├── DeltaRefreshShadow.run_shadow_audit() — observational only
├── OrderManager.check_and_expire_stale_limits() — expires context-invalid LIMIT orders
├── OrderManager.attempt_all_reentries() — re-places expired limits when context is valid
├── OrderManager.attempt_aet_confirmations() — deferred CONFIRMATION orders
│
├── STEP 0: GlobalIntelligence.run()
│   └── GlobalDataAI.fetch() — 5-min cache + background pre-warm
│       INPUT: Dhan/yfinance — S&P, Nikkei, bonds, FX
│       OUTPUT: GlobalSnapshot, last_distortion
│       DECISION EFFECT: distortion flags can suppress/cap later decisions
│       READS KNOWLEDGE: No
│       WRITES KNOWLEDGE: No
│
├── STEP 0.5: Distortion alert publication (EventBus)
│
├── STEP 1: _run_market_intelligence(premarket_bias)
│   ├── MarketDataAI.fetch() — raw indices/VIX/breadth/PCR
│   ├── DataIntegrityEngine.run() — gate: aborts on hard validation error
│   ├── MarketRegimeAI.classify() — BULL_TRENDING/SIDEWAYS/BEAR_TRENDING/VOLATILE
│   ├── SectorRotationAI.analyse() — sector flows and leaders
│   ├── LiquidityAI.analyse() — liquidity metrics
│   ├── EventDetectionAI.scan() — earnings/RBI/expiry
│   └── Returns: MarketSnapshot (regime, vix, breadth, pcr, indices, events)
│       READS KNOWLEDGE: No
│       WRITES KNOWLEDGE: No
│
├── STEP 1.3: RegimeProbabilityModel.compute(snapshot)
│   OUTPUT: RegimeProbabilities (soft weights across 4 regimes)
│   READS KNOWLEDGE: No
│   WRITES KNOWLEDGE: No
│
├── STEP 1.5: MetaLearningEngine.predict(snapshot, all_strats)
│   ├── Reads: data/meta_learning_model.pkl (k-NN model, warm after N trades)
│   ├── Blends: ML weights (80%) + MRPM (20%) when model warm
│   └── Calls: MetaStrategyController.set_ml_weights(blended)
│       OUTPUT: strategy weight allocation
│       READS KNOWLEDGE: No (reads ML model, not KDA/HBE/KFE)
│       WRITES KNOWLEDGE: No
│
├── STEP 2: _run_opportunity_engine(snapshot, odm_directive)
│   ├── EquityScannerAI.scan() — technical + fundamental scoring
│   │   ├── Reads: data/daily_candidates.json (prepared universe)
│   │   ├── Reads: yfinance/Dhan OHLCV + indicators
│   │   ├── WRITES: signal.expected_move_pct, _obs_candidate_score, _obs_regime (MOP-RC001)
│   │   └── Calls: MOP-RC001-observer.record_signal_observation() — append-only JSONL
│   ├── PIG enrichment (if pig_adapter): pig_enrich_signals() — institutional DNA
│   ├── OptionsOpportunityGenerator.scan() — CALL/PUT/spread signals
│   └── ArbitrageAI.scan() — arb signals
│       OUTPUT: List[TradeSignal] (equity + options + arb)
│       READS KNOWLEDGE: No (scanner does not read KDA/HBE/KFE/KLP)
│       WRITES KNOWLEDGE: MOP-RC001 JSONL (observation telemetry only)
│
├── KLP-001 (SHADOW): get_klp_evaluator().evaluate_and_record(signals, snapshot)
│   ├── Computes KNOWLEDGE_RESEARCH_SCORE_v1 per signal
│   ├── Selects top-5 (knowledge_selected=True)
│   └── WRITES: data/klp/KLP_YYYY-MM-DD.jsonl (KNOWLEDGE_OBSERVATION events)
│       READS KNOWLEDGE: No
│       WRITES KNOWLEDGE: Yes (append-only)
│       DECISION EFFECT: None (shadow/observational only)
│
├── STEP 3: _run_strategy_lab(signals, snapshot)
│   ├── Reads: BACKTEST_CACHE (in-memory backtest quality scores)
│   ├── Reads: StrategyHealthMonitor.get_disabled_strategies() — runtime health
│   ├── Reads: StrategyPerformanceTracker.get_disabled_set() — win-rate disabled
│   ├── StrategyGeneratorAI.assign_strategy() — assigns strategy name to signal
│   ├── StrategyEvolutionAI.apply_evolved_params() — applies evolved parameters
│   └── BacktestingAI.filter_by_backtest() — quality gate filter
│       OUTPUT: List[TradeSignal] (filtered, strategy-assigned)
│       CAN REJECT: Yes — backtest gate, SHM disabled, PerfTracker disabled
│       MODIFIES: strategy_name, evolved parameters
│       READS KNOWLEDGE: Indirectly — StrategyPerformanceTracker fed by LearningEngine
│       WRITES KNOWLEDGE: No
│
├── KLP-001 annotate (SHADOW): get_klp_evaluator().annotate_strategy_outcome()
│   └── WRITES: data/klp/KLP_YYYY-MM-DD.jsonl (STRATEGY_ANNOTATION events)
│
├── KDA-003 SHADOW: knowledge_pipeline.run_knowledge_shadow(sig, market_ctx, strategy_info)
│   │   Runs for ALL original scanner signals (approved AND rejected by StrategyLab)
│   │   strategy_info contains strategy_pass=True/False, strategy_name, status
│   ├── KnowledgeDecisionPipeline._shadow_impl()
│   │   ├── HBE.get_behaviour_profile() — hierarchical empirical evidence
│   │   ├── KFE.analyse_record() — 16-angle multi-source fusion
│   │   ├── KDA.evaluate() — shadow decision (KNOWLEDGE_BUY/SELL/WAIT/HOLD/EXIT)
│   │   └── KDALedger.record() — append-only, dedup-protected
│   └── WRITES: data/klp/kda/kda_decisions_YYYY-MM-DD.jsonl
│       DECISION EFFECT: None (shadow_only=True, execution_authority=False)
│       broker_calls=0, orders=0
│
├── STEP 3.5: CapitalRiskEngine.allocate(enriched_signals, snapshot, portfolio)
│   ├── Reads: portfolio positions (open count, heat)
│   └── OUTPUT: List[TradeSignal] (capped to max-position limit)
│       CAN REJECT: Yes — max-position limit
│       READS KNOWLEDGE: No
│
├── STEP 4: _run_risk_control(cre_signals, snapshot)
│   ├── RiskManagerAI.filter_with_heat_split(signals)
│   │   ├── Checks: confidence ≥ 6.0, R:R ≥ 2.0, stop defined, heat budget
│   │   ├── NEW (KDA-003): get_rejection_tracker().ingest_rejection() on each rejection
│   │   └── CAN REJECT: Yes — confidence, R:R, heat, duplicate, stop distance
│   ├── PortfolioAllocationAI.size_positions() — position sizing
│   └── StressTestAI.validate() — stress scenarios
│       OUTPUT: List[TradeSignal] (risk-filtered, sized)
│       WRITES KNOWLEDGE: rejection_audit.db (via RejectionTracker) — feeds KFE
│
├── STEP 4b (conditional): Options fast-path
│   └── OptionsRiskEngine → OptionsOrderManager (separate from equity path)
│
├── STEP 4.5: MarketSimulation.run(approved_signals, snapshot)
│   └── 14 Monte Carlo scenarios, stability threshold
│       CAN REJECT: Yes — simulation stability threshold
│
├── STEP 5: RiskGuardian.evaluate(sim_result.approved_trades, snapshot, portfolio)
│   ├── Kill switch: VIX > 45 → block ALL
│   ├── Kill switch: daily_loss > 2% → block ALL
│   └── CAN REJECT: Yes — hard stop on portfolio-level triggers
│       READS KNOWLEDGE: No
│
├── STEP 5.5: CorrelationEngine.reduce_correlation(signals_as_dicts)
│   └── Decorrelates by sector (max 1 per sector by default)
│       CAN REJECT: Yes — sector correlation limit
│
├── STEP 5.5b: SmartExecutionEngine.filter_trades(trades, vix, drawdown_factor)
│   └── Position sizing, exposure cap, VIX-adjusted allocation
│       CAN REJECT: Yes — exposure cap, VIX penalty
│
├── STEP 6: Debate loop — for each signal in signals_for_debate:
│   └── _run_debate_and_decide(signal, snapshot)
│       ├── MultiAgentDebate.run(signal, snapshot)
│       │   ├── TechnicalAnalystAI   (weight 0.30) — R:R evaluation
│       │   ├── MacroAnalystAI       (weight 0.20) — regime + event risk
│       │   ├── RiskDebateAI         (weight 0.25) — VIX + position risk
│       │   ├── SentimentAI          (weight 0.15) — news + options sentiment
│       │   └── RegimeDebateAI       (weight 0.10) — regime compatibility
│       │   INPUTS: TradeSignal + MarketSnapshot ONLY
│       │   READS KDA/KFE/HBE: No (confirmed)
│       ├── PIG vote injection (if pig_adapter) — institutional DNA
│       ├── DecisionEngine.decide(signal, votes, snapshot)
│       │   ├── Aggregates 5-6 votes into confidence score
│       │   ├── VIX-adaptive threshold: 6.5–6.9
│       │   ├── Asymmetry bonus (high R:R lowers threshold)
│       │   └── READS KDA: No (confirmed)
│       └── MarketTruthGovernor (post-decision)
│           ├── EQUITY_SYNTHETIC → hard block (decision.approved = False)
│           ├── EQUITY_CRITICAL  → downgrade FULL→PARTIAL, cap 50%
│           └── OPTIONS_SYNTHETIC → soft cap 60% (never hard block)
│               MODIFIES: position_size_modifier, approved, trade_type
│
└── OrderManager.execute(signal, decision, context)
    ├── Checks: PAPER_TRADING flag
    ├── Writes: data/paper_trades.csv (OPEN event)
    └── Returns: OrderRecord
        WRITES: paper trade log only (no live broker in PAPER mode)
```

---

## PRODUCTION EOD CALL GRAPH

```
run_eod_learning() [15:35 IST]
└── _do_eod_learning() [via TaskQueue → LearningEngine worker]
    │
    ├── TradeMonitor.get_closed_trades() + CSV recovery (paper_trades.csv)
    │
    ├── LearningEngine.learn(trades)
    │   ├── LearningGate filter (close_reason classification)
    │   ├── StrategyHealthMonitor.record_trade() per verified trade
    │   └── WRITES: data/learning_db.json (per-strategy win rate / expectancy)
    │
    ├── OIOS live_observations ingest (analysis.live_observation_collector)
    │
    ├── PerformanceEvaluator.record_trade() per trade
    │
    ├── StrategyPerformanceTracker.record_trade() per trade
    │   └── WRITES: in-memory stats (used by StrategyLab next cycle to disable)
    │
    ├── RegimeStrategyMap.record() per trade
    │
    ├── MetaLearning.record_result() + retrain_if_due()
    │   └── Updates: data/meta_learning_model.pkl
    │
    ├── ValidationEngine.validate() (if official_trades >= 30)
    │
    ├── EdgeDiscovery.run_discovery_cycle(snapshot)
    │
    ├── DailyAISelfEvaluator.evaluate()
    │
    ├── EODOperationalRetrospective
    │
    ├── MarketLearningCoordinator.run_learning_pipeline(trades)
    │   ├── AMLS — autonomous market learning
    │   ├── DRE (DNA Reinforcement Engine)
    │   └── PIG adapter refresh
    │
    ├── KSL-001 (gated on shadow file existence — local machine only)
    │   └── knowledge_feedback_loop_001.run_loop()
    │       Stages: ingest→classify→detect patterns→generate RQs→prioritize→proposals
    │
    ├── KLP-002: get_klp_outcome_engine().fill_pending_outcomes()
    │   ├── Reads: data/klp/KLP_*.jsonl pending KNOWLEDGE_OBSERVATIONs
    │   ├── Fetches: T+1..T+5 daily OHLCV (yfinance)
    │   └── WRITES: data/klp/KLP_*.jsonl (OUTCOME_UPDATE events)
    │
    ├── KDA-003 EOD: knowledge_pipeline.run_eod_knowledge_update()
    │   ├── HBE reload (picks up KLP-002 outcomes)
    │   ├── KFE pool reload (picks up new rejection records)
    │   ├── KDA Outcome Engine: evaluate() per decision (T+1..T+20 bars)
    │   ├── KDA Comparative: compare() — KDA vs strategy decision
    │   ├── KDA Authority Reporter: generate_report() + save()
    │   └── WRITES: data/klp/kda/kda_authority_validation.json
    │
    └── KLP→KSL bridge: knowledge_feedback_loop_001.run_klp_loop()
        ├── Ingests completed KLP outcomes → evidence_ledger (idempotent)
        ├── Mines patterns (5 detectors)
        ├── Generates research questions
        └── WRITES: knowledge_evidence_ledger.jsonl, research_question_queue.jsonl
```

---

## COMPONENT ATTRIBUTE TABLE

| # | File | Class/Function | Caller | Can Reject? | Modifies Entry? | Modifies Target? | Modifies Stop? | Modifies Confidence? | Modifies Direction? | Modifies Size? | Makes Final Decision? | Reads History? | Reads Knowledge? | Writes Persistent? |
|---|------|---------------|--------|-------------|-----------------|-----------------|----------------|---------------------|---------------------|-----------------|----------------------|----------------|-----------------|-------------------|
| 1 | global_intelligence/global_data_ai.py | GlobalDataAI.fetch() | run_full_cycle | No | No | No | No | No | No | No | No | No (cached) | No | data/global_snapshot.json |
| 2 | market_intelligence/market_data_ai.py | MarketDataAI.fetch() | _run_market_intelligence | No | No | No | No | No | No | No | No | No | No | No |
| 3 | market_intelligence/market_data_ai.py | DataIntegrityEngine.run() | _run_market_intelligence | Yes (abort) | No | No | No | No | No | No | No | No | No | No |
| 4 | market_intelligence/market_regime_ai.py | MarketRegimeAI.classify() | _run_market_intelligence | No | No | No | No | No | No | No | No | No | No | No |
| 5 | meta_learning/meta_learning_engine.py | MetaLearningEngine.predict() | run_full_cycle | No | No | No | No | No | No | Yes (weights) | No | Yes (ML model) | No | No |
| 6 | opportunity_engine/equity_scanner_ai.py | EquityScannerAI.scan() | _run_opportunity_engine | No | Yes (entry) | Yes (target) | Yes (stop) | Yes | Yes | No | No | Yes (OHLCV) | No | MOP-RC001 JSONL |
| 7 | opportunity_engine/klp_evaluator.py | KLPEvaluator.evaluate_and_record() | run_full_cycle | No | No | No | No | No | No | No | No | No | No | KLP JSONL |
| 8 | strategy_lab/strategy_generator_ai.py | StrategyGeneratorAI.assign_strategy() | _run_strategy_lab | Yes | No | No | No | No | No | No | No | Yes (evolved_strategies.json) | Indirect | No |
| 9 | strategy_lab/backtesting_ai.py | BacktestingAI.filter_by_backtest() | _run_strategy_lab | Yes | No | No | No | No | No | No | No | Yes (BACKTEST_CACHE) | No | No |
| 10 | knowledge_authority/knowledge_decision_pipeline.py | KnowledgeDecisionPipeline.run_knowledge_shadow() | run_full_cycle | No (shadow) | No | No | No | No | No | No | No | Yes (HBE/KFE) | Yes (KDA/KFE) | KDA ledger JSONL |
| 11 | risk_control/capital_risk_engine.py | CapitalRiskEngine.allocate() | run_full_cycle | Yes | No | No | No | No | No | Yes | No | No | No | No |
| 12 | risk_control/risk_manager_ai.py | RiskManagerAI.filter_with_heat_split() | _run_risk_control | Yes | No | No | No | No | No | No | No | No | No | rejection_audit.db |
| 13 | risk_control/portfolio_allocation_ai.py | PortfolioAllocationAI.size_positions() | _run_risk_control | Yes | No | No | No | No | No | Yes | No | No | No | No |
| 14 | risk_control/stress_test_ai.py | StressTestAI.validate() | _run_risk_control | Yes | No | No | No | No | No | No | No | No | No | No |
| 15 | market_simulation/simulation_engine.py | SimulationEngine.run() | run_full_cycle | Yes | No | No | No | No | No | No | No | No | No | No |
| 16 | risk_guardian/risk_guardian.py | RiskGuardian.evaluate() | run_full_cycle | Yes (ALL) | No | No | No | No | No | No | No | No | No | No |
| 17 | debate_system/multi_agent_debate.py | MultiAgentDebate.run() | _run_debate_and_decide | Soft (votes) | No | No | No | No | No | No | No | No | No | No |
| 18 | decision_ai/decision_engine.py | DecisionEngine.decide() | _run_debate_and_decide | Yes | No | No | No | No | No | Yes (modifier) | Yes | No | No | No |
| 19 | data_feeds/data_feed_manager.py | MarketTruthGovernor | _run_debate_and_decide | Yes | No | No | No | No | No | Yes | Yes (post-decision) | No | No | No |
| 20 | execution_engine/order_manager.py | OrderManager.execute() | _run_debate_and_decide | Yes (PAPER check) | No | No | No | No | No | No | Yes (final) | No | No | paper_trades.csv |

---

## TARGET DETERMINATION (Ownership)

| Parameter | Where Set | Method |
|-----------|-----------|--------|
| Entry price | EquityScannerAI.scan() | Technical levels + ATR |
| Target price | EquityScannerAI.scan() | ATR-multiple from entry |
| Stop loss | EquityScannerAI.scan() | ATR-multiple below entry |
| Direction (BUY/SELL) | EquityScannerAI.scan() | Trend direction logic |
| Confidence (0–10) | EquityScannerAI.scan() | Composite scoring |
| R:R ratio | EquityScannerAI.scan() | Computed from entry/stop/target |
| Strategy name | StrategyGeneratorAI.assign_strategy() | Strategy matching |
| Position size | PortfolioAllocationAI + SmartExecutionEngine | Portfolio heat rules |
| Knowledge target | KDA (shadow only, not production) | Empirical move distribution |
| Knowledge stop | KDA (shadow only, not production) | Empirical loss distribution |

---

## KEY SAFETY OBSERVATIONS

1. **PAPER_TRADING** enforced at OrderManager.execute() — never bypassed
2. **broker_calls = 0** for all knowledge components (KDA, HBE, KFE, KLP)
3. **KDA remains SHADOW_ONLY** — no decision authority in production path
4. **RiskGuardian** is a hard kill switch — cannot be bypassed by any upstream component
5. **Debate agents** receive only TradeSignal + MarketSnapshot — no knowledge output
6. **DecisionEngine** receives only votes + signal + snapshot — no knowledge output
