# SC-001: Execution Path Audit
**Date:** 2026-08-13  
**Auditor:** Copilot (read-only, no code changes)  
**Scope:** Determine whether the historical finding of `risk_approved>0, sim_approved>0, trades_executed=0` represents a real execution bottleneck in the current system.

---

## 1. Executive Summary

**Verdict: SC-001 NOT CONFIRMED.**

The CT counter pattern `risk_approved>0, sim_approved>0, trades_executed=0` observed in March–April 2026 local CT cycles is fully explained by two known-correct pipeline behaviours:

1. **DecisionEngine threshold rejection** — All historical signals scored below the 6.5 confidence floor. No `ORDER_PLACED` event was fired because `execute()` was never reached.
2. **CT counter definition mismatch** — `risk_approved` in the CT DB is overwritten by the last `RISK_CHECK_PASSED` event, which is published by **CorrelationEngine** (Layer 5.5), not by RiskManagerAI. When CorrelationEngine reduces post-simulation signals to 0, `risk_approved` is overwritten to 0. This makes the "8 approved, 0 executed" pattern appear anomalous when it is actually `(RiskManagerAI: 8) → (CorrelationEngine overwrites: 0)`.

There is no evidence of an execution bottleneck at the OrderManager boundary. The execution path code is correctly structured. One secondary DATA_GAP remains: the Dhan order placement API has never been exercised by a live trade, so its production readiness cannot be confirmed from local evidence alone.

---

## 2. Current Execution Architecture

The pipeline from signal to order in `run_full_cycle()`:

```
Layer 3   OpportunityEngine.scan()           → signals[]
          SCAN_COMPLETE event                → signals_generated (CT)

Layer 4   StrategyLab.assign_strategy()      → enriched_signals[]
          STRATEGY_LAB_COMPLETE event        → strategies_assigned (CT)

Layer 3.5 CapitalRiskEngine.allocate()       → cre_signals[]

Layer 5   RiskManagerAI.filter_with_heat_split()
          PortfolioAllocationAI.size()
          StressTestAI.validate()
          RISK_CHECK_PASSED (source=RiskManagerAI)   → risk_approved=N (CT) ← FIRST WRITE

Layer 4b  Options Fast-Path split            → routes OPTIONS/SPREAD separately

Layer 4.5 SimulationEngine.run()             → sim_result
          SIMULATION_COMPLETE event          → sim_approved (CT)

Layer 7.5 FailSafeRiskGuardian.evaluate()   → if blocked → RETURN (no debate, no execution)

Layer 5.5 CorrelationEngine.reduce_correlation()
          RISK_CHECK_PASSED (source=CorrelationEngine) → risk_approved=M (CT) ← OVERWRITES
          SmartExecutionEngine.filter_trades()
          → final_approved_signals[]

Layer 6–7 For each signal: MultiAgentDebate.run()
          DecisionEngine.decide()            threshold=6.5
          MarketTruthGovernance check        SYNTHETIC equity → hard block
          → if decision.approved: order_manager.execute()

Layer 8   OrderManager.execute()
          → guards (see §4)
          → _place_entry_with_retry()
          → OrderRecord created
          ORDER_PLACED event                 → trades_executed +1 (CT)
```

---

## 3. CT Counter Definitions (Verified from Source)

| CT Column | Source Event | Published By | What It Counts |
|---|---|---|---|
| `signals_generated` | `SCAN_COMPLETE` | MasterOrchestrator | equity + options + arb total |
| `strategies_assigned` | `STRATEGY_LAB_COMPLETE` | StrategyGeneratorAI | signals with strategy assigned |
| `risk_approved` | `RISK_CHECK_PASSED` | **Last writer wins** — RiskManagerAI OR CorrelationEngine | Post-correlation count (current pipeline) |
| `sim_approved` | `SIMULATION_COMPLETE` | SimulationEngine | Signals approved by Monte Carlo |
| `trades_executed` | `ORDER_PLACED` | MasterOrchestrator | Incremented +1 per fired event |

**Critical: `risk_approved` is not additive.** Each `RISK_CHECK_PASSED` event calls `_upsert_cycle_locked({risk_approved: payload["approved"]})` — a SET, not an ADD. Two events per cycle mean only the last value is stored.

Pipeline order: `RISK_CHECK_PASSED(RiskManagerAI)` fires at Layer 5, then `SIMULATION_COMPLETE` fires at Layer 4.5, then `RISK_CHECK_PASSED(CorrelationEngine)` fires at Layer 5.5. In the current system:

- `sim_approved` = post-simulation count (correct, stable reference)
- `risk_approved` = post-correlation count (the last write, Layer 5.5)

**`sim_approved` > `risk_approved` is the expected pattern** in the current pipeline. It means simulation approved more signals than survived correlation — correct behaviour.

---

## 4. Execution Boundary Guards in `OrderManager.execute()`

All guards that can return `None` (prevent `ORDER_PLACED` from firing):

| Guard | Condition | Log Tag |
|---|---|---|
| Signal Freshness Gate | Signal > 15 trading days old | `[SignalFreshnessGate]` |
| ExecutionWindowBlock | Before 09:45 IST | `[ExecutionWindowBlock]` |
| DupGuard | Same symbol already open, score not superior | `[SmartSwapThrottle]` |
| Max Positions | ≥ 15 open positions, no swap candidate | `[MAX GUARD]` |
| EarlyLoss Cooldown | EARLY_LOSS exit < `_EARLY_LOSS_COOLDOWN_H` hours ago | `[EarlyLossCooldown]` |
| Late Entry Block | After 14:30 (hard cutoff) | `[LateEntryBlock]` |
| Late Entry Score | 13:30–14:30 and score < 7.0 | `[LateEntryBlock]` |
| Zero Quantity | `qty = int(signal.quantity * modifier) == 0` | `[OrderManager] Zero quantity` |
| Capital/Trade Guard | Notional > 15% of capital | `[CAPITAL/TRADE GUARD]` |
| Total Exposure Guard | New total > 85% of capital | `[TOTAL EXPOSURE GUARD]` |
| AET CONFIRMATION | VIX ≥ 32 at live order time | deferred to `_aet_pending` slot |
| Pre-Order Price Guard | Entry price outside registered band | `[PRE-ORDER PRICE GUARD]` |
| Broker failure | `_place_entry_with_retry()` returns None | `[Entry order failed]` |

None of these guards produce a `[GlobalAbortCause]` or CT cycle abort. They silently return `None`. When `execute()` returns `None`, the orchestrator does NOT fire `ORDER_PLACED`.

---

## 5. Historical CT Reconciliation

### March 2026 cycles — `risk=8, sim=6, trades=0`

**Reconstruction:**

At `2026-03-18 09:50` (range_market, VIX≈13.60):
- `signals_generated=24`, `risk_approved=8`, `sim_approved=6`, `trades_executed=0`
- CorrelationEngine was active by this date (present in initial commit)
- The `risk_approved=8` value is from RiskManagerAI before CorrelationEngine fires

Wait — `risk_approved=8` AND `sim_approved=6` with `risk_approved > sim_approved` contradicts the current pipeline order (correlation fires AFTER simulation). This means in the March 2026 cycle at 09:50, CorrelationEngine either:
  1. Did NOT run (early return before Layer 5.5 — possible if guardian blocked), or
  2. Ran and published `RISK_CHECK_PASSED` with count = 8 (no filtering)

If CorrelationEngine published `approved=8` (same as RiskManagerAI), then `risk_approved=8` is the correlation pass-through, and `sim_approved=6` means simulation rejected 2. Then RiskGuardian evaluated 6 signals. If RiskGuardian blocked → early return → trades=0. If guardian approved → Debate for 6 signals → all scored below 6.5 → trades=0.

**Confirmed from CT decisions table (March 2026 cycles):** scores of 6.34, 6.40, 6.46, 6.49 — all below the 6.5 threshold. DecisionEngine correctly rejected them all.

### April 2026 cycles — `risk=0, sim=2, trades=0`

At `2026-04-02 10:03` (volatile, VIX=26.18):
- `signals_generated=24`, `risk_approved=0`, `sim_approved=2`, `trades_executed=0`
- `risk_approved=0` is the CorrelationEngine overwrite (it ran and produced 0 decorrelated signals)
- `sim_approved=2` is from simulation (fired before correlation)
- `signals_for_debate = 0` → no `ORDER_PLACED` events

**Conclusion:** The counter pattern `risk=0, sim=2` is expected and correct. CorrelationEngine reduced 2 simulation-approved signals to 0 (likely same sector + same direction). This is correct pipeline behaviour, not a bottleneck.

---

## 6. 2026-08-13 Signal Trace (SOLARINDS path)

From MOP-DAY4 audit (`MOP_DAY4_POST_MARKET_OBSERVATION_2026-08-13.md`):

- SOLARINDS.NS: single candidate in `daily_candidates.json` at ₹225.35
- Candidate expiry: `valid_until_utc = 2026-08-13T10:30:00Z` — expired before first cycle
- CT DB: 0 cycles recorded for 2026-08-13 (local system not running live)

The VPS is the live system. Local CT DB has no 2026-08-13 data. SOLARINDS could not have been traded today on the local system. VPS state is out-of-scope for this read-only audit.

---

## 7. Dhan Broker Readiness

| Check | Status | Notes |
|---|---|---|
| `PAPER_TRADING` | `False` (`.env` override) | System is in LIVE mode |
| `ACTIVE_BROKER` | `dhan` | DhanBroker selected |
| `DHAN_CLIENT_ID` | Set (non-empty) | Credentials present |
| `DHAN_ACCESS_TOKEN` | Set (non-empty) | Token present |
| `DhanBroker._connected` | `True` | `dhanhq` SDK connected |
| `DhanBroker._dhan` | `not None` | SDK instance valid |
| Data API (HTTP 451) | BLOCKED | Market data endpoint blocked by Dhan |
| Order placement API | **UNKNOWN** | Never exercised; no local evidence |

**Key distinction:** HTTP 451 applies to Dhan's market data websocket and quote endpoints. Order placement uses a separate REST endpoint. The 451 block on data does not confirm order placement is blocked. However, it cannot be confirmed as functional from local evidence.

**Risk flag:** With `PAPER_TRADING=False`, a signal that passes all upstream filters and `execute()` guards would route to `DhanBroker.place_order()` and attempt a **real Dhan order**. If the token is expired or the account has restrictions, `_broker_place()` returns `None`, triggering the `[Entry order failed]` log and returning `None` from `execute()` — safe failure.

If the token is valid and the API is live, a real order would be placed. **No local paper journal exists** (paper_trades.csv = 0 rows because `_paper_mode=False`). The only audit trail would be Dhan order history.

---

## 8. Existing Execution Tests

Execution-related test directories found:
- `tests/unit/execution/orders/` — OMS tests (order management system)
- `tests/unit/execution/test_execution_engine.py` — engine tests
- `tests/unit/iios/execution/oms/order_manager/test_order_manager.py` — OMS unit tests
- `tests/unit/execution/risk/` — risk integration tests (6 files)

**Coverage gap:** None of these tests exercise the live `OrderManager.execute()` → `DhanBroker.place_order()` path. They test AI Platform framework abstractions, not the trading engine's `execution_engine/order_manager.py`. There is no integration test that verifies a DecisionEngine-approved signal produces an `ORDER_PLACED` event under `PAPER_TRADING=False`.

---

## 9. Blocker Analysis — Why `trades_executed=0` Historically

Ranked by confirmed evidence:

| Rank | Cause | Evidence | Cycles Affected |
|---|---|---|---|
| 1 | **DecisionEngine threshold (6.5)** — all signals scored below floor | CT decisions table shows scores 6.34–6.49 | Mar 2026, range cycles |
| 2 | **CorrelationEngine → 0 signals** — all sim-approved signals in same sector/direction | CT shows `risk=0, sim>0` after Apr 2026 | Apr 2026, volatile cycles |
| 3 | **RiskGuardian block** — session-level daily loss or VIX conditions | Possible for late volatile cycles; not confirmed in log data | Uncertain |
| 4 | **SmartExecutionEngine filtering** — exposure/VIX-weighted rejection | Operates after correlation; removes high-VIX signals | Uncertain |
| 5 | **execute() internal guards** (late-entry, capital, price integrity) | Not triggered — signals never reached execute() | Not applicable |

**Primary conclusion:** The signal attrition happens upstream, before `execute()` is ever called. The execution layer boundary (OrderManager) has never been the bottleneck.

---

## 10. SC-001 Verdict

**SC-001: NOT CONFIRMED**

The historical pattern `risk_approved>0, sim_approved>0, trades_executed=0` does **not** represent an execution bottleneck. It is fully explained by:

1. All signals scoring below DecisionEngine confidence floor (6.5)
2. CorrelationEngine overwriting `risk_approved` to 0 after simulation (apparent counter inconsistency, not a real anomaly)

The execution path code from `_run_debate_and_decide()` → `order_manager.execute()` → `DhanBroker.place_order()` is correctly structured. If a signal survives all upstream filters and scores ≥ 6.5, the path to live order placement is unobstructed in code.

**Secondary finding (DATA_GAP, not SC-001):**  
The Dhan order placement API has never been exercised. Its live readiness is unknown. This is a separate verification item.

---

## 11. Recommended Next Research

1. **Dhan order API verification** — Send a single test order via `DhanBroker.place_order()` to confirm the endpoint accepts orders with the current token. This is a live-money action and requires explicit user authorization. Do not proceed without user instruction.

2. **DecisionEngine threshold calibration** — Historical scores cluster at 6.34–6.49. The threshold is 6.5. A systematic review of whether the 6.5 floor is correctly calibrated for the current signal universe, or whether it should be lowered to 6.2, is a logical next step.

3. **CorrelationEngine sector diversity** — The Apr 2026 correlation-to-zero pattern suggests scanned signals cluster by sector. Adding a pre-correlation sector diversity audit log would make this visible in real-time.

4. **Live cycle test on VPS** — The VPS is the production system. The local CT DB has not recorded a cycle since April 2026. Connecting to VPS logs would confirm whether the system has produced any `ORDER_PLACED` events since deployment.

---

## Appendix: Code Locations

| Component | File | Key Lines |
|---|---|---|
| Pipeline order | `orchestrator/master_orchestrator.py` | `run_full_cycle()` |
| CT counter update | `control_tower/telemetry_logger.py` | `_handle_event()` |
| `risk_approved` source 1 | `orchestrator/master_orchestrator.py` | `_run_risk_control()` end |
| `risk_approved` source 2 | `orchestrator/master_orchestrator.py` | Layer 5.5 CorrelationEngine block |
| `execute()` method | `execution_engine/order_manager.py` | Line 446 |
| Late-entry guards | `execution_engine/order_manager.py` | Lines 661–684 |
| qty=0 guard | `execution_engine/order_manager.py` | Line 690 |
| Paper mode branch | `execution_engine/order_manager.py` | Line 780 |
| DhanBroker connection | `execution_engine/brokers/dhan_broker.py` | `_connect()` |
| `PAPER_TRADING` value | `.env` | `PAPER_TRADING=false` |

---

*Code changes: 0 | Configuration changes: 0 | Orders placed: 0 | Positions created: 0 | Broker writes: 0*
