# ARCH-006 Live Execution Call Graph
**Verified against source code — line citations are approximate for orientation**

---

## Entry Point: MasterOrchestrator._guarded_cycle()

```
_guarded_cycle()                                    [orchestrator ~L6466]
└── run_full_cycle()                                [orchestrator ~L3000]
    │
    ├── [Layer 1] GlobalIntelligence.run()           GlobalSnapshot (17ms cached)
    ├── [Layer 2] MarketIntelligence.run()           MarketSnapshot (19ms cached)
    │
    ├── [KDA Shadow] run_knowledge_shadow()          [orchestrator ~L1050]
    │   ├── KnowledgeDecisionPipeline.run_shadow()
    │   │   ├── KnowledgeBaseEngine.assess()        evidence state
    │   │   ├── HorizonBoundaryEngine.compute()     horizon P50
    │   │   └── KnowledgeForwardEngine.project()    forward projection
    │   └── Returns: {kda_decision, ess, evidence_state, horizon_p50}
    │       ├── KNOWLEDGE_BUY  → signal enters production
    │       ├── KNOWLEDGE_SELL → signal enters production
    │       └── KNOWLEDGE_HOLD → signal blocked (continue) [orchestrator ~L54339]
    │
    ├── [Layer 3] MetaLearning.run()                 strategy weights
    │
    ├── [Layer 4] OpportunityEngine.scan()           candidate signals
    │   └── EquityScannerAI.scan()
    │       ├── Reads: GlobalSnapshot, MarketSnapshot
    │       ├── Computes: momentum, volume, regime filters
    │       ├── Attaches: _obs_candidate_score, _obs_regime (MOP-RC-001)
    │       └── Returns: List[TradeSignal]
    │
    ├── [Layer 5] StrategyLab.evaluate()             strategy assignment
    │
    ├── [Layer 6] CapitalRiskEngine.allocate()       [capital_risk_engine.py ~L199]
    │   ├── _compute_deployable_capital()            regime exposure × total capital
    │   ├── _compute_position_size()                 risk_per_trade ÷ ATR
    │   │   └── Uses: MAX_RISK_PER_TRADE_PCT=0.0025, MAX_CAPITAL_PER_TRADE_PCT=15%
    │   ├── Drops: qty=0 signals (RELIANCE, SBIN at ₹10k capital)
    │   ├── Caps: MAX_POSITIONS=3 (auto-scaled from TOTAL_CAPITAL=10000)
    │   └── Returns: List[TradeSignal] (qty>0 only, ≤3 signals)
    │
    ├── [Layer 7] RiskControl.evaluate()             portfolio risk check
    │
    ├── [Layer 8] MarketSimulation.run()             Monte Carlo
    │
    ├── [Layer 9] RiskGuardian.evaluate()            KILL-SWITCH [orchestrator ~L1436]
    │   ├── VIX > 45  → BLOCK (all signals dropped)
    │   ├── Daily loss > 2% → BLOCK
    │   └── Returns: GuardianDecision{action=BLOCK|ALLOW}
    │
    ├── [Layer 10] DebateAndDecision._run_debate()   [orchestrator ~L1564]
    │   ├── 5-agent debate (Bull, Bear, Risk, Technical, Macro)
    │   ├── DecisionEngine threshold: 6.5
    │   └── Returns: Decision{confidence_score, position_size_modifier}
    │
    └── [Layer 11] OrderManager.execute()            [orchestrator ~L3001]
        ├── _symbol_has_open_position()              duplicate guard
        ├── _dup_guard_reentry_check()               2% zone guard
        ├── qty = signal.quantity × decision.modifier
        ├── qty ≤ 0 → return None (no broker call)
        ├── _place_entry_with_retry()                [order_manager.py ~L420]
        │   ├── PAPER mode → SIM_{symbol}_{direction}_{ts}
        │   └── LIVE mode  → DhanBroker.place_order()
        │       └── _connected=False → SIM_DHAN_{ts}
        │
        └── _place_stop_loss()                       [order_manager.py ~L480]
            ├── PAPER mode → SIM_SL_{symbol}_{direction}
            └── LIVE mode  → DhanBroker.place_sl_order()
                └── _connected=False → SIM_SL_{symbol}_{direction}
```

---

## Monitoring Loop (every 5 minutes)

```
_do_monitor()                                       [orchestrator ~L3308]
├── TradeMonitor.check_all()                        SL/TP software check
├── StrategyHealthMonitor.run()
├── _persist_monitor_ts()
└── OrderManager.reconcile_partial_fills()          [ARCH-006 FIX — wired in]
    ├── PAPER mode → return []
    ├── For each open order:
    │   ├── broker.get_order_status(order_id)
    │   ├── filled_qty < rec.quantity → PARTIAL FILL
    │   │   ├── rec.quantity = filled_qty
    │   │   ├── broker.cancel_order(rec.sl_order_id)   [cancel stale SL]
    │   │   ├── broker.place_sl_order(..., qty=filled)  [new SL for filled qty]
    │   │   └── rec.sl_order_id = new_sl_id
    │   └── filled_qty >= rec.quantity → full fill, no-op
    └── Returns: [order_ids_reconciled]
```

---

## Safety Layers (ordered, all must pass)

| # | Gate | Failure → | Code Location |
|---|---|---|---|
| 1 | `KNOWLEDGE_HOLD` | signal dropped | orchestrator ~L54339 |
| 2 | `CRE qty=0` | signal dropped | capital_risk_engine.py ~L199 |
| 3 | `CRE MAX_POSITIONS=3` | excess signals dropped | capital_risk_engine.py |
| 4 | `RiskGuardian BLOCK` | all signals dropped | risk_guardian.py |
| 5 | `Debate score < 6.5` | signal rejected | decision_engine.py |
| 6 | `_symbol_has_open_position` | execute returns None | order_manager.py |
| 7 | `PAPER_TRADING=true` | SIM_ prefix | order_manager.py ~L412 |
| 8 | `LIVE_TRADING_AUTHORIZED absent` | force paper | order_manager.py ~L335 |
| 9 | `DhanBroker._connected=False` | SIM_DHAN_ prefix | dhan_broker.py |

All 9 safety layers are active in the current VPS deployment.

---

*Generated: ARCH-006 Final Pre-Live Closure | Commit: pending*
