# ARCH-006 Learning Loop Verification
**Verifies that the learning system closes the signal → execution → outcome → learning loop**

---

## Loop Architecture

```
Signal Generation              Execution                Learning
─────────────────              ─────────────────────    ────────────────────────────
EquityScannerAI.scan()    →   OrderManager.execute()  →  paper_trades.csv
  TradeSignal{symbol,          OrderRecord{order_id,       {symbol, entry_px, exit_px,
  confidence, entry,           entry, stop, target,         qty, strategy, pnl,
  stop, target, qty,           strategy, status}            status=CLOSED}
  strategy}
                                        │
                                        ▼
                               TradeMonitor.check_all()    (every 5 min)
                               ├── Checks LTP vs stop_loss
                               ├── Checks LTP vs target
                               └── om.close_position() → CSV CLOSED row
                                        │
                                        ▼
                               EOD Learning Cycle (15:35)
                               _do_eod_learning()
                               ├── Reads today's CLOSED trades from CSV
                               ├── LearningEngine.update(trade_record)
                               │   └── Writes to market_behavior.db
                               ├── StrategyPerformanceTracker.record()
                               │   ├── win_rate = wins / total_trades
                               │   └── auto_disable if win_rate < 40%
                               └── RegimeStrategyMap.update()
                                   └── regime → strategy mapping update
```

---

## Loop Closure Verification

### Phase 1: Signal → Execution
- **Verified**: `OrderManager.execute()` creates `OrderRecord` with all signal fields
- **Verified**: Entry price, stop, target, strategy name all persisted to CSV
- **Verified**: Paper trades written to `data/paper_trades.csv` (append-only)

### Phase 2: Execution → Outcome
- **Verified**: `TradeMonitor.check_all()` runs every 5 min via `_do_monitor()`
- **Verified**: SL breach → `om.close_position()` → CLOSED row in CSV with exit_px, pnl
- **Verified**: Target hit → same path
- **Verified**: `_do_monitor()` now also calls `reconcile_partial_fills()` (ARCH-006 fix)

### Phase 3: Outcome → Learning
- **Verified**: `_do_eod_learning()` scheduled at 15:35 daily
- **Verified**: Reads CLOSED trades from today's CSV (handles post-restart zero-count via EOD fix)
- **Verified**: `LearningEngine.update()` writes outcomes to `market_behavior.db`
- **Verified**: `StrategyPerformanceTracker.record()` accumulates win/loss/pnl

### Phase 4: Learning → Next Cycle
- **Verified**: `KnowledgeBaseEngine` reads `market_behavior.db` for evidence assessment
- **Verified**: KBE evidence state feeds KDA decision (KNOWLEDGE_BUY/SELL/HOLD)
- **Verified**: `StrategyPerformanceTracker` auto-disables strategies with win_rate < 40%
- **Verified**: `RegimeStrategyMap` feeds regime→strategy weights to MetaLearning

---

## Gaps and Limitations

### Gap 1: ResearchCoordinator Not Connected
- **Status**: `ResearchCoordinator` 8-stage pipeline exists and is tested (190 tests)
- **Impact**: Advanced research synthesis not feeding back to StrategyLab
- **Risk**: LOW — standard learning loop (LearningEngine → KBE) is active
- **Action**: Connect in a separate audit after pilot produces ≥50 live trades

### Gap 2: knowledge_pattern_miner and knowledge_feedback_loop are DEAD_ORPHAN
- **Status**: Modules exist but not called in production
- **Impact**: Pattern mining and feedback not automated
- **Risk**: LOW — manual research still possible via scripts
- **Action**: KEEP_RESEARCH — do not wire into production without validation audit

### Gap 3: rejection_tracker writes but KBE reads from different table
- **Status**: rejection_tracker.py writes to `rejections` table; KBE reads from `market_behavior`
- **Impact**: Rejection history not feeding back
- **Risk**: LOW — KBE uses live signal evidence, not rejection history in production
- **Action**: DEPRECATE rejection_tracker in next cycle

### Gap 4: OIOS DifferentialResearch weekly output not consumed
- **Status**: Runs weekly, produces analysis; not read by any production component
- **Impact**: Research artifact only
- **Risk**: ZERO — OIOS is observation-only
- **Action**: KEEP_RESEARCH — wire output to ResearchCoordinator in future

---

## Learning Loop Quality: ADEQUATE FOR PILOT

The core loop (Signal → Execution → Outcome → LearningEngine → KBE → KDA) closes correctly. Advanced research modules are intentionally disconnected for the pilot phase to maintain safety. The pilot target of ≥50 trades will provide sufficient signal to evaluate loop quality before connecting advanced research.

---

*Generated: ARCH-006 Final Pre-Live Closure | Commit: pending*
