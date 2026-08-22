# Pre-Live Production Call Graph
**Generated:** 2026-08-22  
**Purpose:** Authoritative production call graph tracing every execution-path transition with actual call sites.

---

## 1. Scheduler Loop

```
main.py → brain.start_scheduler()
  └── orchestrator/master_orchestrator.py:6540  start_scheduler()
        └── schedule library every().day.at("09:45"/"10:30"/"11:30"/"13:00"/"14:00"/"15:00")
              .do(self._guarded_cycle)

        Scheduler event loop (line 6714):
          _run() thread:
            while not self._halt:
              try:
                sched_lib.run_pending()   # calls _guarded_cycle at each slot
              except Exception as _exc:
                log.error("[Scheduler] Exception in run_pending — continuing: ...")
                # ← Scheduler NEVER dies on exception (line 6714–6724)
```

## 2. _guarded_cycle → run_full_cycle

```
_guarded_cycle (line 6466):
  if self._is_market_session():   # line 6162 — NSE hours 09:15–15:30 IST
    self.run_full_cycle()          # line 6469
  else:
    log.debug("Outside market session — cycle skipped.")
```

## 3. run_full_cycle — 17-Layer Pipeline

```
run_full_cycle (line 680):
  ├── Guard: self._halt → return early
  ├── Guard: time < 09:45 IST → return early (ExecWindowGuard L2)
  ├── Guard: kill_switch active → return early
  │
  ├── L1  GlobalIntelligence      global_data_ai.fetch()            ~17ms
  ├── L2  MarketIntelligence      market_intelligence.analyse()     ~19ms
  ├── L3  MetaLearning            meta_learning.analyse()
  ├── L4  OpportunityEngine       opportunity_engine.scan()
  │       └── equity_scanner_ai.scan() → List[TradeSignal]
  │
  │   [KDA Shadow — per signal, line ~1050]
  │   run_knowledge_shadow(signal, market_ctx, strategy_info)
  │     └── knowledge_authority/knowledge_decision_pipeline.py
  │           ├── HBE: get_behaviour_profile(symbol, direction, regime)
  │           ├── KFE: analyse_record(kfe_record, pool) → AngleView
  │           ├── KDA: evaluate(observation, angle_view, behaviour, ...)
  │           │     → kda_record (decision: KNOWLEDGE_BUY/SELL/HOLD/WAIT)
  │           └── Ledger: _ledger.record(kda_record)   [append-only JSONL]
  │
  │   [KNOWLEDGE_HOLD filter, line 1069]
  │   if _kda_dec2 == "KNOWLEDGE_HOLD":
  │       continue   # signal dropped — StrategyLab never sees it
  │
  ├── L5  StrategyLab             strategy_lab.generate_signals()
  ├── L6  CapitalRiskEngine       capital_risk_engine.allocate()    (line 1197)
  │         ├── _compute_deployable_capital(snapshot, portfolio)
  │         ├── _strategy_budget(sig.strategy_name, deployable)
  │         ├── _size_position(sig, budget)
  │         │     → qty = min(risk_amount / sl_distance, budget / entry_price)
  │         │     risk_amount = budget × MAX_RISK_PER_TRADE_PCT (0.25%)
  │         └── sig.quantity = qty
  │
  ├── L7  RiskControl             risk_manager_ai.evaluate()
  ├── L8  MarketSimulation        monte_carlo.simulate()
  │
  ├── L9  RiskGuardian            risk_guardian.evaluate()          (line 1436)
  │         ├── VIX > 45  → BLOCK (kill-switch)
  │         ├── daily_loss > MAX_DRAWDOWN_PCT (10%) → BLOCK
  │         └── On BLOCK: self._halt = True → all future cycles skip
  │
  │   [RiskGuardian check, line 1450]
  │   if guardian_decision.action == "BLOCK":
  │       log.critical("RiskGuardian BLOCK — halting cycle")
  │       return   # ← exits run_full_cycle; no execution
  │
  ├── L10 DebateAndDecision       _run_debate_and_decide(signal, snapshot) (line 1564)
  │         ├── 5-agent debate
  │         ├── DecisionEngine threshold 6.5
  │         └── → DecisionRecord (confidence_score, position_size_modifier)
  │
  ├── L11 ExecutionEngine         order_manager.execute(signal, decision) (line 3001)
  │         ├── Gate: _symbol_has_open_position(symbol) → duplicate guard
  │         ├── Gate: _dup_guard_reentry_check(symbol, score, entry_price)
  │         ├── Gate: signal freshness (SignalFreshnessGate)
  │         ├── Gate: time < 09:45 IST → rejected (ExecutionWindowBlock)
  │         ├── qty = int(signal.quantity × decision.position_size_modifier)
  │         ├── Gate: qty × entry_price > 15% capital → rejected
  │         ├── Gate: total_exposure > 85% capital → rejected
  │         ├── Price integrity: price_integrity_validator.validate(symbol, price)
  │         ├── _place_entry_with_retry(signal, qty, zone_price)
  │         │     └── _broker_place(symbol, direction, qty, price)
  │         │           ├── if not self._broker → returns SIM_{...} [paper safe]
  │         │           ├── Resolve symbol → DHAN_SECURITY_MAP[symbol]
  │         │           └── self._broker.place_order(security_id, ...) [live]
  │         │
  │         └── _place_stop_loss(signal, qty, order_id)   ← FIXED (P1)
  │               ├── if not self._broker → returns SIM_SL_{symbol} [paper]
  │               └── self._broker.place_sl_order(symbol, ...) [live]
  │                     → STOP_LOSS order on exchange (added 2026-08-22)
  │
  ├── L12 TradeMonitoring         trade_monitor.check_all(live_prices)
  │       [runs every 5 min in background: _do_monitor → _five_min_tasks]
  │         ├── Fetch live prices (Dhan primary, yfinance fallback)
  │         ├── SL hit? → order_manager.close_position(order_id, exit_px, "STOP_HIT")
  │         ├── Target hit? → order_manager.close_position(order_id, exit_px, "TARGET_HIT")
  │         └── EOD? → order_manager.close_position(order_id, exit_px, "EOD_CLOSE")
  │
  ├── L13 LearningSystem          [EOD: _do_eod_learning]
  │         ├── learning_engine.learn(trades)
  │         └── meta_learning.record_result()
  │
  ├── L14 PerformanceAnalytics    [drawdown, WFT]
  ├── L15 ResearchLab             [promotion gates]
  ├── L16 ValidationEngine        [6-stage pipeline]
  └── L17 ControlTower            [telemetry, Streamlit, EventBus]
```

## 4. EOD Knowledge Update

```
run_eod_learning (line ~3654 → task_queue):
  ├── run_eod_knowledge_update(trading_date)
  │     └── knowledge_decision_pipeline._eod_impl()
  │           ├── KDAOutcomeEngine.evaluate()   — fills outcome for each decision
  │           ├── KDAComparativeAnalyzer.compare()
  │           └── KDAAuthorityReporter.generate_report()
  └── _do_eod_learning()
        ├── learning_engine.learn(trades)
        └── meta_learning.record_result()
```

## 5. Key Safety Gates (in execution order)

| Gate | Location | Condition | Effect |
|---|---|---|---|
| KNOWLEDGE_HOLD | orchestrator L1069 | n_contradict≥3 > n_support | Signal dropped before StrategyLab |
| RiskGuardian BLOCK | orchestrator L1436–1450 | VIX>45 or DD>10% | `run_full_cycle` aborted |
| ExecutionWindowBlock | order_manager L481 | time < 09:45 IST | Order rejected (Layer 3) |
| SignalFreshnessGate | order_manager L471 | signal stale | Order rejected (Layer 2) |
| PAPER_TRADING | order_manager L332 | `_paper_mode=True` | `_broker` not set → all orders SIM |
| LIVE_TRADING_AUTHORIZED | order_manager L332 | env absent or ≠ "true" | Logs error, routes to SIM |
| DhanBroker._connected | dhan_broker.py L51 | `not self._connected` | Returns SIM_DHAN_* ID |
| Capital/trade guard | order_manager L702–725 | >15% capital OR >85% total | Order rejected |
| Pre-order price guard | order_manager L735 | price outside band | Order rejected |
| Duplicate guard | order_manager L519–527 | same symbol open | Order rejected or smart-swap |

## 6. Call Site Index

| Symbol | File | Line |
|---|---|---|
| `_guarded_cycle` | master_orchestrator.py | 6466 |
| `run_full_cycle` | master_orchestrator.py | 680 |
| `run_knowledge_shadow` | master_orchestrator.py | ~1050 |
| `KNOWLEDGE_HOLD filter` | master_orchestrator.py | 1069 |
| `capital_risk_engine.allocate` | master_orchestrator.py | 1197 |
| `risk_guardian.evaluate` | master_orchestrator.py | 1436 |
| `_run_debate_and_decide` | master_orchestrator.py | 1564 |
| `order_manager.execute` | master_orchestrator.py | 3001 |
| `_place_entry_with_retry` | order_manager.py | ~805–814 |
| `_broker_place` | order_manager.py | 1982 |
| `_place_stop_loss` | order_manager.py | 1966 |
| `DhanBroker.place_order` | dhan_broker.py | 51 |
| `DhanBroker.place_sl_order` | dhan_broker.py | ~91 (added 2026-08-22) |
| `_do_monitor` | master_orchestrator.py | 3308 |
| `run_eod_knowledge_update` | master_orchestrator.py | ~5792 |
| `start_scheduler loop` | master_orchestrator.py | 6714 |
