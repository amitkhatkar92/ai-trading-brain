# OPS04B — Governance Violation Forensic Report

**Classification:** Evidence Collection / Root Cause Analysis  
**Status:** CLOSED — Root cause determined  
**Subject:** DRREDDY BUY at 09:10:17 on 2026-06-18 (governance window opens 09:45)  
**Date of Report:** 2026-06-19  
**Investigator:** Copilot (evidence collection only — no code modified)

---

## STEP 1 — Trade Identity

| Field | Value |
|---|---|
| **Symbol** | DRREDDY |
| **Strategy** | Momentum_Retest |
| **Entry Timestamp** | 2026-06-18T09:10:17.131141 IST |
| **Entry Price** | ₹1,269.50 |
| **Order ID** | `SIM_DRREDDY_BUY_Q856_P1272.22_1781754016515` |
| **Quantity** | 856 |
| **Stop Loss** | ₹1,228.64 |
| **Target** | ₹1,371.65 |
| **R:R** | 2.5 |
| **Decision Score** | 7.73 |
| **Cycle ID** | Not recorded in ct_cycles |
| **Decision Event** | `decision.approved` at 2026-06-18T09:10:16.236238 |
| **Minutes early** | 34 min 43 sec before governance window (09:45) |

**Governance window**: 09:45 IST  
**Violation magnitude**: trade entered 34 min 43 sec before governance window opens

---

## STEP 2 — Decision Path Trace

The complete path from signal to execution for this trade, with timestamps from `ct_events` and `system_logs`:

| Stage | Timestamp | Event | Details |
|---|---|---|---|
| **Opportunity** | 09:10:14.034 | `opportunity.equity.found` | symbol=DRREDDY, setup=`mean_reversion_bounce`, confidence=7.05 |
| **Strategy Map** | (internal) | StrategyGenerator | setup `mean_reversion_bounce` → strategy `Momentum_Retest` (see `strategy_generator_ai.py` line 279–282) |
| **Debate** | (internal) | `multi_agent_debate.py` | 5-agent vote |
| **Decision** | 09:10:16.236 | `decision.approved` | strategy=Momentum_Retest, score=7.73, votes=TechnicalAnalystAI:9.0 / MacroAnalystAI:6.52 / RiskDebateAI:7.5 / SentimentAI:7.0 / RegimeDebateAI:8.0 |
| **Risk** | (internal) | RiskGuardian | Passed (no kill-switch, no drawdown halt) |
| **Execution** | 09:10:17.111 | `execution.order.placed` | BUY qty=856 entry=1272.22 sl=1228.64 tgt=1371.65 rr=2.5 |
| **Logged** | 09:10:17.131 | `TRADE_OPENED` system_log | symbol=DRREDDY strategy=Momentum_Retest |

**Total latency** — opportunity to execution: **~3 seconds**

### Opportunity Source
The opportunity was detected via the `first_opportunity_scan` deep scan that fires at **09:10** (MarketMonitor slot). The opportunity scanner (`equity_scanner_ai.py` line 1386, 1931) classified the setup as `mean_reversion_bounce`. The strategy generator (`strategy_generator_ai.py` lines 279–282) mapped `mean_reversion_bounce` at a range boundary with moderate confidence to `Momentum_Retest`.

At 09:20:32 a second `decision.approved` for DRREDDY/Momentum_Retest was emitted with identical score and votes — this was the `strategy_evaluation` deep scan at 09:20 re-running the cycle. By 09:20, DRREDDY was already in the portfolio; the duplicate was rejected by the max-positions check.

At 09:45:06 a third opportunity was found (confidence 6.0 — below the 6.5 decision threshold) — this would have been the correct governance-window entry point had DRREDDY not already been open.

---

## STEP 3 — Governance Rules: All Files Enforcing Time Restrictions

### 3a. Scheduler Time Slots

| File | Line | Function / Constant | Value | Effect |
|---|---|---|---|---|
| `config.py` | 93 | `SCHEDULE["market_open_regime"]` | `"09:05"` | Regime scan only — no execution |
| `config.py` | 96 | `SCHEDULE["trade_decision"]` | `"09:45"` | First scheduler slot that calls `_guarded_cycle()` |
| `orchestrator/master_orchestrator.py` | 5334 | `sched_lib.every().day.at(SCHEDULE["trade_decision"]).do(self._guarded_cycle)` | 09:45 | Only path enforcing the 09:45 governance window |
| `orchestrator/master_orchestrator.py` | 5336–5342 | `sched_lib.every().day.at(...).do(self._guarded_cycle)` | 10:30, 11:30, 13:00, 14:00, 15:00 | All subsequent full cycles go through `_guarded_cycle` |

### 3b. _guarded_cycle — The Only Execution Time Gate

```python
# orchestrator/master_orchestrator.py  line 5248
def _guarded_cycle(self) -> None:
    """Run a full cycle only during market hours; log a skip otherwise."""
    if self._is_market_session():
        self.run_full_cycle()
    else:
        log.debug("[Orchestrator] Outside market session — cycle skipped.")
```

```python
# orchestrator/master_orchestrator.py  lines 4990–5004
def _is_market_session(self) -> bool:
    ...
    # NSE hours: 09:15–15:30 IST
    market_open  = now.replace(hour=9,  minute=15, second=0, microsecond=0)
    market_close = now.replace(hour=15, minute=32, second=0, microsecond=0)
    return market_open <= now <= market_close
```

**Critical observation:** `_is_market_session()` gates on **09:15**, not 09:45. Even if the deep scan path went through `_guarded_cycle`, it would not block at 09:10 (pre-15), 09:20, or 09:30 entries. The 09:45 rule is enforced only by the scheduler not scheduling any slot before 09:45 — but the deep scan path bypasses the scheduler entirely.

### 3c. Deep Scan Slots (MarketMonitor)

```python
# market_intelligence/market_monitor.py  line 301
{
    "09:05": "market_open_regime",       # regime only
    "09:10": "first_opportunity_scan",   # ← triggers run_full_cycle()
    "09:20": "strategy_evaluation",      # ← triggers run_full_cycle()
    "10:30": "mid_morning_scan",
    "11:30": "mid_session_scan",
    "13:00": "afternoon_scan",
    "14:00": "early_afternoon_scan",
    "15:00": "closing_analysis",
}
```

### 3d. _on_deep_scan — Routes first_opportunity_scan to run_full_cycle

```python
# orchestrator/master_orchestrator.py  line 477
def _on_deep_scan(self, scan_name: str) -> None:
    ...
    if actual_name == "market_open_regime":
        # Re-run regime classification with fresh data only
        raw = self.market_data_ai.fetch()
        self.market_regime_ai.classify(raw)
    elif actual_name in ("first_opportunity_scan", "strategy_evaluation",
                       "mid_morning_scan", ...):
        # Submits run_full_cycle() directly — no time gate
        self.task_queue.submit_to(
            "MasterOrchestrator",
            self.run_full_cycle,
            priority=Priority.HIGH,
            description=f"deep_scan:{actual_name}:{scan_id}",
        )
```

### 3e. Learning-Layer Time Enforcement (Non-Blocking — Scoring Only)

| File | Line | Enforcement |
|---|---|---|
| `learning_system/daily_self_evaluation.py` | 106 | Comment: "Valid intraday trading window 09:45–14:30 IST" |
| `learning_system/daily_self_evaluation.py` | 761 | Scores trade as -2 pts for pre-09:45 entry |
| `learning_system/daily_self_evaluation.py` | 953 | `-2 pts: Each trade entered before 09:45` |
| `learning_system/daily_self_evaluation.py` | 984 | Log: `"(window starts 09:45)"` |
| `learning_system/daily_self_evaluation.py` | 1094 | Warning after session review |

**These checks only score/penalize after the fact — they do not block execution.**

### 3f. Audit Patches (Not Yet Applied)

| File | Patch Type | Status |
|---|---|---|
| `deploy_forensic_audits.py` lines 80–130 | `[ExecutionWindowAudit]` — log-only observe-and-alert when order placed before 09:45 | **Not applied to VPS order_manager.py** |
| `governance_quarantine_patches.py` lines 1–70 | `[ExecutionWindowBlock]` — return None (reject order) before 09:45 | **Not applied** |

Confirmed: VPS `order_manager.py` contains none of `ExecutionWindowAudit`, `exec_win_open`, `_EXEC_WINDOW`, or `minutes_early`.

---

## STEP 4 — Execution Gate Verification

**Was the time-window check executed?**

**NO**

The time-window check was NOT executed for the DRREDDY trade.

**Why it was skipped:**

The trade was triggered by the `first_opportunity_scan` deep scan at 09:10. This path flows:

```
MarketMonitor 09:10 tick
  → _on_deep_scan("first_opportunity_scan#...")
    → task_queue.submit_to("MasterOrchestrator", self.run_full_cycle, ...)
      → run_full_cycle()
        → [no time gate]
        → OpportunityEngine.scan()
        → DebateSystem.deliberate()
        → DecisionEngine.evaluate()
        → OrderManager.place_order()
          → [no entry-time check in order_manager]
          → SIM_DRREDDY_BUY placed at 09:10:17
```

The `_guarded_cycle()` wrapper — the only function that calls `_is_market_session()` — was NOT in this call stack. `_guarded_cycle()` is invoked exclusively by the `schedule` library at 09:45, 10:30, 11:30, 13:00, 14:00, and 15:00. The deep scan path submits `run_full_cycle()` directly, completely bypassing `_guarded_cycle()`.

`run_full_cycle()` itself contains no time-of-day gate. Its only guards are:
- `if self._halt:` — manual halt flag
- `if not is_trading_enabled():` — emergency kill switch

Neither was active at 09:10 on 2026-06-18.

The `ExecutionWindowAudit` patch (`deploy_forensic_audits.py`) which would have added a logging-only time check to `order_manager.py` was authored but **never applied to the VPS**. The `ExecutionWindowBlock` patch (`governance_quarantine_patches.py`) which would have blocked the order was also **never applied**.

---

## STEP 5 — Root Cause

### Classification: **F — Execution Path Bypass**

### Evidence

The 09:45 governance window is enforced by one mechanism: the `schedule` library fires `_guarded_cycle()` at 09:45 (and later slots). `_guarded_cycle()` calls `_is_market_session()` first, then `run_full_cycle()` only if within session.

The MarketMonitor deep scan path is a **parallel execution route** that bypasses `_guarded_cycle()`. It was designed as an "opening window scan" for opportunity detection, but it calls `run_full_cycle()` — the same function that executes trades — without any time restriction beyond the kill switch.

The architectural intent recorded in comments and logs is:
- Deep scans at 09:05/09:10/09:20 = "opening window only" (observation)
- Full cycles at 09:45+ = trade execution window

The implementation does not match the intent. Both paths call `run_full_cycle()`, which produces identical outcomes including trade execution. The distinction between "deep scan" (observation) and "full cycle" (execution) was intended but not implemented as a code-level constraint.

This is not a timezone error (all timestamps are IST, correctly aligned). Not a scheduler misfire (MarketMonitor correctly fired at 09:10). Not a manual override. Not a strategy exemption (`Momentum_Retest` has no time-window bypass). It is purely an execution path that lacks a time gate.

---

## STEP 6 — Scope: All Violations in Last 60 Trading Days

Data source: `system_logs.TRADE_OPENED` + `ct_events.execution.order.placed`

### 6a. Trades at 09:10 IST (first_opportunity_scan window)

All trades before 09:15 (pre-market): entry via deep scan `first_opportunity_scan`

| Date | Symbol | Strategy | Order ID |
|---|---|---|---|
| 2026-04-20 09:10:13 | NIFTY | Bull_Call_Spread | SIM_NIFTY_SELL_43 |
| 2026-04-21 09:10:24 | COALINDIA | Mean_Reversion | SIM_COALINDIA_BUY_4486_1776742824681 |
| 2026-04-23 09:10:23 | TATASTEEL | Mean_Reversion | SIM_TATASTEEL_SELL_9305_1776915623021 |
| 2026-04-29 09:10:19 | RELIANCE | Momentum_Retest | SIM_RELIANCE_BUY_1698_1777434019325 |
| 2026-05-07 09:10:17 | NIFTY | Bull_Call_Spread | SIM_NIFTY_SELL_43 |
| 2026-05-12 09:10:08 | HINDALCO | Momentum_Retest | SIM_HINDALCO_BUY_2049 |
| 2026-05-13 09:10:27 | TATAMOTORS | Momentum_Retest | SIM_TATAMOTORS_BUY_1043 |
| 2026-05-14 09:10:11 | TATASTEEL | EDG_MOMENT_100_EE0005 | SIM_TATASTEEL_BUY_9245_1778730010611 |
| 2026-06-03 09:10:38 | MRF | Mean_Reversion | SIM_MRF_BUY_Q12_P124975.20_1780458037986 |
| **2026-06-18 09:10:17** | **DRREDDY** | **Momentum_Retest** | **SIM_DRREDDY_BUY_Q856_P1272.22_1781754016515** |

**Count: 10 trades at 09:10** — all pre-market (before NSE 09:15 open)

### 6b. Trades at 09:20 IST (strategy_evaluation window)

Post-market-open (after 09:15) but pre-governance window (before 09:45): entry via deep scan `strategy_evaluation`

| Date | Symbol | Strategy | Order ID |
|---|---|---|---|
| 2026-04-24 09:20:33 | NTPC | Momentum_Retest | SIM_NTPC_BUY_4927_1777002633179 |
| 2026-06-09 09:20:29 | MRF | Mean_Reversion | SIM_MRF_BUY_Q12_P123071.60_1780977028612 |
| 2026-06-09 09:20:29 | DLF | Mean_Reversion | SIM_DLF_BUY_Q2672_P562.60_1780977029062 |

**Count: 3 trades at 09:20** — post-open, pre-governance

### 6c. Summary

| Window | Count | Method |
|---|---|---|
| 09:00–09:14 (pre-NSE-open) | **10** | `first_opportunity_scan` → `run_full_cycle()` |
| 09:15–09:44 (post-open, pre-governance) | **3** | `strategy_evaluation` → `run_full_cycle()` |
| **Total violations** | **13** | Both deep scan routes |

**First violation:** 2026-04-20 (oldest in 60-day window — the pattern predates the current investigation by 8+ weeks)  
**Last violation:** 2026-06-18 (DRREDDY — subject of this forensic)

### 6d. Strategy Distribution of Violations

| Strategy | Count |
|---|---|
| Mean_Reversion | 5 |
| Momentum_Retest | 5 |
| Bull_Call_Spread (NIFTY options) | 2 |
| EDG_MOMENT_100_EE0005 | 1 |

No strategy-specific exemption pattern — violations occur across all strategies. Confirms the bypass is systemic, not strategy-specific.

---

## STEP 7 — Recurrence Risk

**HIGH — this is an active, ongoing systemic issue.**

The MarketMonitor fires `first_opportunity_scan` at 09:10 and `strategy_evaluation` at 09:20 every trading day. Both currently invoke `run_full_cycle()` with no time gate. Without a code change, every trading day has the potential for pre-governance entries if:
- Any stock scores above the decision threshold (6.5) in the 09:10 or 09:20 scan
- No position in that stock is already open
- The kill switch is not active

The violation has already occurred on **10 of the 42+ trading days** in the 60-day window (roughly 24% of trading days). The rate is not declining — DRREDDY on 2026-06-18 is the most recent instance.

---

## Complete Evidence Timeline

| Time (IST) | Event | Source |
|---|---|---|
| 2026-06-16 18:51:56 | Last SYSTEM_START before Jun 18. System ran continuously through Jun 18. | `system_logs` |
| 2026-06-18 09:10:00 | MarketMonitor tick: 09:10 slot fires `first_opportunity_scan` | `market_monitor.py` schedule |
| 2026-06-18 09:10:00 | `_on_deep_scan("first_opportunity_scan#...")` called | `master_orchestrator.py` line 477 |
| 2026-06-18 09:10:00 | `task_queue.submit_to("MasterOrchestrator", self.run_full_cycle, ...)` | `master_orchestrator.py` line 513 |
| 2026-06-18 09:10:14.034 | `opportunity.equity.found` — DRREDDY, `mean_reversion_bounce`, confidence=7.05 | `ct_events` |
| 2026-06-18 09:10:16.236 | `decision.approved` — DRREDDY, Momentum_Retest, score=7.73 | `ct_events` |
| 2026-06-18 09:10:17.111 | `execution.order.placed` — DRREDDY BUY, 856 qty, entry=1272.22 | `ct_events` |
| 2026-06-18 09:10:17.131 | `TRADE_OPENED` — DRREDDY Momentum_Retest | `system_logs` |
| 2026-06-18 09:15:00 | NSE market opens | (governance) |
| 2026-06-18 09:20:32.619 | Second `decision.approved` — DRREDDY Momentum_Retest, same score 7.73 | `ct_events` — duplicate, rejected by max-positions |
| 2026-06-18 09:45:06.461 | Third opportunity — DRREDDY `mean_reversion_bounce`, confidence=6.0 (below threshold) | `ct_events` — no execution |
| 2026-06-18 09:45 | Governance window opens — `_guarded_cycle()` scheduled here | `start_scheduler` line 5334 |

---

## Summary Answer to Each Forensic Question

| Question | Answer |
|---|---|
| **Why did DRREDDY enter at 09:10?** | MarketMonitor fired `first_opportunity_scan` at 09:10, which called `run_full_cycle()` directly via `_on_deep_scan`. No time gate exists in this path. |
| **Was the time-window check executed?** | **NO** — the check is only in `_guarded_cycle()` which was not in the call stack |
| **What path bypassed governance?** | `_on_deep_scan("first_opportunity_scan")` → `task_queue.submit_to(..., run_full_cycle, ...)` → full trading pipeline |
| **What is the root cause?** | **Category F — Execution Path Bypass**: `first_opportunity_scan` (09:10) and `strategy_evaluation` (09:20) deep scans call `run_full_cycle()` without the time guard imposed by `_guarded_cycle()` |
| **Is this unique to DRREDDY?** | **No** — 13 violations across 42+ trading days in the 60-day window |
| **Is this unique to Momentum_Retest?** | **No** — Mean_Reversion, Bull_Call_Spread, and EDG_MOMENT_100_EE0005 also appear in violation list |
| **Recurrence risk?** | **HIGH** — fires every trading day without fix |
| **Was there a patch to block this?** | Yes — `deploy_forensic_audits.py` (log-only) and `governance_quarantine_patches.py` (blocking) were authored but **never applied** |

---

*Report produced from: `ct_events`, `ct_decisions`, `system_logs` (trading_brain.db), `control_tower.db`, source code audit of `master_orchestrator.py`, `market_monitor.py`, `order_manager.py`, `config.py`, `daily_self_evaluation.py`, `deploy_forensic_audits.py`, `governance_quarantine_patches.py`. No code was modified during this investigation.*
