# RISK_BLOCK_REPORT.md
## Forensic Audit — `risk_approved = 0` Anomaly
**Date of Investigation:** June 16, 2026  
**Period Examined:** March 18 – April 2, 2026 (last two active trading days)  
**Databases:** `data/control_tower.db` (ct_cycles, ct_events), `data/paper_trades.csv`  
**Verdict:** `risk_approved = 0` is a **TELEMETRY OVERWRITE BUG**, not a real risk block.

---

## 1. The Observation

`ct_cycles` for every recorded cycle shows:

| Cycle Date | Cycle ID | risk_approved | sim_approved | trades_executed |
|---|---|---|---|---|
| 2026-03-18 | `2d277888-8c1` | 8 | 6 | 0 |
| 2026-03-18 | `757562ad-183` | 8 | 6 | 0 |
| 2026-03-18 | `1ea15c15-2f6` | 8 | 6 | 0 |
| 2026-04-02 | `5e048698-...` | 0 | 2 | 0 |
| 2026-04-02 | `47ded7a3-...` | 0 | 2 | 0 |

The surface reading suggests risk control blocked signals on April 2. The March 18 cycles correctly show `risk_approved = 8`.

---

## 2. Root Cause — Two RISK_CHECK_PASSED Events, One Overwrites

The `TelemetryLogger` (`control_tower/telemetry_logger.py`) subscribes to `EventType.RISK_CHECK_PASSED` and updates `ct_cycles.risk_approved` each time it fires:

```python
elif et == EventType.RISK_CHECK_PASSED.value:
    self._upsert_cycle_locked(conn, self._current_cycle,
        {"risk_approved": payload.get("approved", 0)})
```

The pipeline fires **two** `RISK_CHECK_PASSED` events per cycle — from different agents:

### Event 1 — RiskManagerAI (correct payload)
Fired at Layer 7 (`_run_risk_control`):
```
ts: 2026-04-02T10:03:14
source_agent: RiskManagerAI
payload: {"approved": 2}
```
→ TelemetryLogger sets `ct_cycles.risk_approved = 2`.

### Event 2 — CorrelationEngine (missing `approved` key)
Fired at Layer 7 (`_run_correlation_engine`, after Simulation and RiskGuardian):
```
ts: 2026-04-02T10:03:14
source_agent: CorrelationEngine
payload: {"before_correlation": 2, "after_correlation": 2, "sector_breakdown": {"ENERGY": 1, "BANK": 1}}
```
→ TelemetryLogger: `payload.get("approved", 0)` = **0**  
→ **OVERWRITES** `ct_cycles.risk_approved` with `0`.

### Why March 18 was unaffected
On March 18, the `CorrelationEngine` event was NOT fired (CorrelationEngine either wasn't wired yet or did not publish in that code version). Only `RiskManagerAI` fired, setting `risk_approved = 8` correctly.

---

## 3. Proof That Risk Control Was Not the Actual Block

The `sim_approved` counter increments when `SimulationEngine` processes its input. `SimulationEngine` only receives signals that have passed `RiskManagerAI` and `PortfolioAllocationAI`. Therefore:

- `sim_approved = 2` (April 2) **proves** 2 signals reached Simulation successfully.
- `risk_approved = 0` in the same row is a column update overwrite, not a signal count.
- The signals that passed Simulation (`RELIANCE`, `HDFCBANK`) were subsequently **rejected by DecisionEngine** (scores 6.49 and 6.34 below the 6.5 partial threshold), not by risk control.

Cross-reference ct_events for cycle `47ded7a3` (April 2):
```
[114986] risk.check.passed  RiskManagerAI      {"approved": 2}       ← correct
[114987] simulation.complete SimulationEngine   {"approved": 2, "rejected": 0}
[114988] risk.guardian.complete RiskGuardian    {"approved": 2, "blocked": 0}
[114989] risk.check.passed  CorrelationEngine   {"before_correlation": 2, ...}  ← overwrites
[114991] decision.rejected  DecisionEngine      {"symbol": "RELIANCE",  "score": 6.49}
[114992] decision.rejected  DecisionEngine      {"symbol": "HDFCBANK",  "score": 6.34}
```

Signals passed **every** risk layer. The pipeline ended at DecisionEngine rejection, not risk.

---

## 4. Exact Wiring Defect

**File:** `control_tower/telemetry_logger.py`  
**Behaviour:** `_upsert_cycle_locked` is called with `{"risk_approved": payload.get("approved", 0)}` for **every** `RISK_CHECK_PASSED` event. The SQL UPSERT replaces the previous value. The last writer wins.

**File:** `orchestrator/master_orchestrator.py`  
**Location:** `_run_correlation_engine()` method  
**Defect:** `CorrelationEngine` fires `EventType.RISK_CHECK_PASSED` with a payload that does not include an `approved` key. The `after_correlation` field is present but is not named `approved`.

The current code in `_run_correlation_engine()` contains:
```python
self.bus.publish(SystemEvent(
    event_type=EventType.RISK_CHECK_PASSED,
    source_agent="CorrelationEngine",
    payload={
        "before_correlation": len(approved_signals),
        "after_correlation": len(decorrelated_signals),
        "sector_breakdown": {...},
    },
))
```
Note: `"approved": len(decorrelated_signals)` exists in the current file but was absent in the code version that ran the March-April 2026 cycles. The overwrite behaviour has since been masked but not eliminated (TelemetryLogger still overwrites on second event).

---

## 5. Impact Assessment

| Dashboard / Monitoring View | Shows | Reality |
|---|---|---|
| Cycles table `risk_approved` (April 2) | 0 | 2 (RiskManagerAI passed 2 signals) |
| Streamlit dashboard risk pass rate | 0% | ~100% for that session |
| Alerting on `risk_approved = 0` | Would fire | False positive |

No trading capital was protected or endangered by this bug. It is a **metrics accuracy defect** only.

---

## 6. Distinguishing Normal vs. Bugged Cycles

| Indicator | `risk_approved > 0` | `risk_approved = 0` |
|---|---|---|
| CorrelationEngine event present? | No | Yes |
| `sim_approved` > 0? | — | Yes (if signals passed) |
| Actual risk block? | — | No — check DecisionEngine |

On March 18, `risk_approved = 8` and `sim_approved = 6` because CorrelationEngine did not fire a second event. The single `RiskManagerAI {"approved": 8}` event stood unchanged.

---

*End of RISK_BLOCK_REPORT.md — observation only, no fixes applied*
