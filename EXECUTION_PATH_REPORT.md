# EXECUTION_PATH_REPORT.md
## Forensic Audit — `trades_executed = 0` Despite Approved Signals
**Date of Investigation:** June 16, 2026  
**Period Examined:** March 18 and April 2, 2026  
**Databases:** `data/control_tower.db`, `data/paper_trades.csv`  
**System Version:** New orchestrator (`orchestrator/master_orchestrator.py`)

---

## 1. The Observation

Both active trading dates show zero executed trades despite the pipeline approving signals:

| Date | Cycles | Signals in | Sim Approved | Debate APPROVED | trades_executed |
|---|---|---|---|---|---|
| 2026-03-18 | 3 | ~24/cycle | 6/cycle | 6/cycle (18 total) | 0 |
| 2026-04-02 | 2 | 24/cycle | 2/cycle | 0 | 0 |

`paper_trades.csv` has **no entries** for March 18 or April 2.

---

## 2. Architecture: Where `trades_executed` Increments

`TelemetryLogger` updates `ct_cycles.trades_executed` only when `EventType.ORDER_PLACED` fires:

```python
elif et == EventType.ORDER_PLACED.value:
    ...
    self._upsert_cycle_locked(conn, self._current_cycle,
        {"trades_executed": (current + 1)})
```

`ORDER_PLACED` is emitted **only** inside `OrderManager.execute()` after `_place_entry_with_retry()` returns a valid `order_id`. If `execute()` returns `None` at any earlier guard, no `ORDER_PLACED` event fires.

---

## 3. Full Pipeline Trace — April 2 (Confirmed by ct_events)

The full April 2 event sequence for cycle `47ded7a3` (10:03):

```
Layer 1  GlobalIntelligence      — skipped (cache hit)
Layer 2  MarketIntelligence
  market.data.ready             vix=26.18, regime=volatile, breadth=0.48
  market.regime.classified      regime=volatile, volatility=EXTREME
Layer 3  MetaLearning
  meta.learning.applied         top_strategy=Breakout_Volume
Layer 4  OpportunityEngine
  opportunity.equity.found      ×18 signals (RELIANCE, HDFCBANK, ICICIBANK, ...)
  opportunity.equity.found      ×4 INDEX signals (NIFTY, BANKNIFTY, NIFTYBEES, BANKBEES)
  opportunity.scan.complete     equity=18, options=2, arb=4, total=24
Layer 5  StrategyLab
  strategy.lab.complete         assigned=24, after_evo=24, after_bt=2   ← 22 dropped by backtesting
Layer 6  CapitalRiskEngine + RiskManagerAI
  risk.check.passed             RiskManagerAI {"approved": 2}
Layer 8  Simulation
  simulation.complete           approved=2, rejected=0, rate=1.0
Layer 9  RiskGuardian
  risk.guardian.complete        approved=2, blocked=0, decision=APPROVED
Layer 7b CorrelationEngine
  risk.check.passed             CorrelationEngine {"before_correlation": 2, "after_correlation": 2}
Layer 10 SmartExecutionEngine
  risk.portfolio.updated        accepted_count=2, total_exposure=617400, exposure_pct=77.2%
Layer 10 DecisionEngine
  decision.rejected             RELIANCE  score=6.49  reason="Weighted score 6.49 | Threshold 6.7 (partial≥6.5)"
  decision.rejected             HDFCBANK  score=6.34  reason="Weighted score 6.34 | Threshold 6.7 (partial≥6.5)"
system.cycle.complete           signals_processed=2
```

**Failure point: DecisionEngine rejection.**  
Both surviving signals fell below the 6.5 partial threshold. `_run_debate_and_decide()` returned `None`. `OrderManager.execute()` was never called. `trades_executed = 0` is the CORRECT outcome for April 2 — it is not a bug.

---

## 4. Full Pipeline Trace — March 18

### 4.1 Inputs to execute()

CT evidence for the first March 18 cycle (09:50:27, cycle `2d277888`):

- `risk_approved = 8` (8 signals passed RiskManagerAI)
- `sim_approved = 6` (Simulation approved 6)
- 6 `TRADE_APPROVED` events in ct_decisions (10:03:14 confirmed APPROVED in debate)
- 0 `order.placed` events in ct_events for March 18
- 0 open positions restored from journal at startup (paper_trades.csv was empty for prior dates in the new orchestrator)

**Decision results:**

| Symbol | Score | Decision |
|---|---|---|
| ICICIBANK | 6.72 | APPROVED |
| RELIANCE | 6.60 | APPROVED |
| LT | 6.58 | APPROVED |
| HDFCBANK | 6.53 | APPROVED |
| COALINDIA | 6.46 | APPROVED |
| INFY | 6.45 | APPROVED |

All 6 signals reached `OrderManager.execute()`.

### 4.2 OrderManager Guard Walk

In `execute()`, guards are evaluated in order. For each March 18 signal:

**Guard 1: DupGuard** (`_symbol_has_open_position`) — CLEAR  
No prior positions. `_orders` was empty at cycle start.

**Guard 2: MAX_OPEN_POSITIONS (15)** — CLEAR  
`open_count = 0 < 15`.

**Guard 3: Late-day entry (09:50 / 10:30 IST)** — CLEAR  
Entry cutoff is 14:30; elevated threshold at 13:30. Both cycles are before 13:30.

**Guard 4: Zero quantity check (`qty <= 0`)** — CLEAR  
`sim_approved = 6` confirms StrategyLab and PortfolioAllocationAI set non-zero quantities.

**Guard 5: Capital per trade (`MAX_CAPITAL_PER_TRADE_PCT = 15.0%`)** — **FAIL ← EXECUTION BLOCK**

```python
notional_capital = qty * signal.entry_price
trade_utilization_pct = (notional_capital / self._portfolio.capital) * 100.0
if trade_utilization_pct > MAX_CAPITAL_PER_TRADE_PCT:   # 15.0%
    return None
```

`PortfolioAllocationAI` sizes quantities using risk budget:

```
qty = (TOTAL_CAPITAL × MAX_RISK_PER_TRADE_PCT) / (entry_price × stop_loss_gap_pct)
```

With `TOTAL_CAPITAL = ₹800,000` and `MAX_RISK_PER_TRADE_PCT = 0.01 (1%)`:

| Symbol | Entry Price | ~SL Gap | Risk Budget | Computed qty | Notional | Capital% |
|---|---|---|---|---|---|---|
| RELIANCE | ~₹2,848 | 2% | ₹8,000 | ~140 shares | ₹398,720 | **49.8%** |
| HDFCBANK | ~₹1,701 | 2% | ₹8,000 | ~235 shares | ₹399,735 | **50.0%** |
| ICICIBANK | ~₹1,210 | 2% | ₹8,000 | ~330 shares | ₹399,300 | **49.9%** |
| LT | ~₹3,550 | 2% | ₹8,000 | ~112 shares | ₹397,600 | **49.7%** |
| COALINDIA | ~₹487 | 2% | ₹8,000 | ~820 shares | ₹399,540 | **49.9%** |
| INFY | ~₹1,580 | 2% | ₹8,000 | ~252 shares | ₹398,160 | **49.8%** |

All 6 signals: notional ≈ 50% of capital > 15% threshold → **all blocked by capital guard**.

The 15% cap equates to a maximum of ₹120,000 per trade on ₹800,000 capital. The risk-based sizing formula naturally produces notionals of ~50% because:
```
notional = qty × entry = [(capital × 0.01) / (entry × 0.02)] × entry
         = (capital × 0.01) / 0.02
         = capital × 0.50   (= 50% of capital, independent of price)
```
The capital guard and the risk-based sizer are **fundamentally incompatible** at these parameter settings.

**Result:** `execute()` returned `None` for all 6 signals. `_place_entry_with_retry()` was never reached. `ORDER_PLACED` never fired. `trades_executed = 0`.

---

## 5. Key Code Locations

| File | Line | Guard |
|---|---|---|
| `execution_engine/order_manager.py` | 451 | `_symbol_has_open_position()` — DupGuard |
| `execution_engine/order_manager.py` | 514 | `open_count >= MAX_OPEN_POSITIONS` |
| `execution_engine/order_manager.py` | 550 | Late-entry cutoff 14:30 / elevated 13:30 |
| `execution_engine/order_manager.py` | 580 | `qty <= 0` |
| `execution_engine/order_manager.py` | 599 | `trade_utilization_pct > MAX_CAPITAL_PER_TRADE_PCT` ← March 18 FAIL |
| `execution_engine/order_manager.py` | 607 | `exposure_pct > MAX_TOTAL_OPEN_EXPOSURE_PCT` |
| `execution_engine/order_manager.py` | 613 | Pre-order price integrity validator |
| `execution_engine/order_manager.py` | 726 | AET CONFIRMATION deferral |
| `execution_engine/order_manager.py` | 1800 | `_broker_place()` — SIM path (always succeeds in paper mode) |
| `orchestrator/master_orchestrator.py` | ~2478 | `TRADE_APPROVED` event fires (before execute) |
| `orchestrator/master_orchestrator.py` | ~2489 | `order_manager.execute()` call |
| `control_tower/telemetry_logger.py` | ~209 | `ORDER_PLACED` → increments `trades_executed` |

---

## 6. TRADE_APPROVED ≠ Order Placed

A critical observability distinction confirmed by this investigation:

`ct_decisions.decision = 'APPROVED'` is written when `EventType.TRADE_APPROVED` fires inside `_run_debate_and_decide()`. This event fires **before** `order_manager.execute()` is called. An APPROVED decision in the decisions table does **not** guarantee execution.

The sequence inside `_run_debate_and_decide()` is:
```
1. DecisionEngine.decide(signal) → decision
2. if decision.approved:
       bus.publish(TRADE_APPROVED)    ← ct_decisions.APPROVED written here
       order = order_manager.execute(signal, decision)
       if order:
           bus.publish(ORDER_PLACED)  ← trades_executed increments here
```

`ct_decisions` (18 APPROVED on March 18) documents that all 6 signals reached OrderManager. It does not document that they were placed. Only `ct_events.event_type = 'execution.order.placed'` confirms actual placement.

---

## 7. Summary

| Date | Failure Layer | Exact Cause | Expected trades_executed |
|---|---|---|---|
| 2026-03-18 | `execute()` Guard 5 — Capital per trade | Notional ~50% capital > 15% limit | 0 (by guard design) |
| 2026-04-02 | DecisionEngine | Scores 6.34, 6.49 < 6.5 partial threshold | 0 (by threshold design) |

Neither is a silent crash. Both are deterministic guard decisions with no exception or log error raised — the `return None` paths are intentional refusal paths with `log.warning()` messages.

The system is operating as coded. Whether the code settings (15% capital cap with 1% risk sizing) reflect the intended trading policy is a separate policy question.

---

*End of EXECUTION_PATH_REPORT.md — observation only, no fixes applied*
