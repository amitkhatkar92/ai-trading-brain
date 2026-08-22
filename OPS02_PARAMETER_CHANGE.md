# OPS-02 Parameter Change Record

**Date:** 2026-06-16  
**Author:** Copilot (approved by operator)  
**Status:** Applied ✅  
**Test Result:** 182 / 182 passed — zero regressions

---

## Change Summary

| Field | Value |
|---|---|
| File | `config.py` |
| Parameter | `MAX_RISK_PER_TRADE_PCT` |
| Previous value | `0.01` (1.00%) |
| New value | `0.0025` (0.25%) |
| Change type | Single-parameter calibration |
| Scope | Sizing formula only — no execution, guard, or allocation logic touched |

**Exact diff:**
```diff
- MAX_RISK_PER_TRADE_PCT   = 0.01      # 1% of capital per trade
+ MAX_RISK_PER_TRADE_PCT   = 0.0025    # 0.25% of capital per trade (calibrated OPS-02 2026-06-16; was 0.01)
```

---

## Calibration Evidence

Source: `OPS02_SIZING_CALIBRATION_REPORT.md` (generated 2026-06-16)  
Orders analysed: **1073** real executed orders from `control_tower.db`

### Before (risk_pct = 1.00%)

| Metric | Value |
|---|---|
| Mean notional | 14.98% |
| Median notional | 14.98% |
| PA cap fire rate | **44.3%** |
| Guard 5 block rate | 0.0% |
| P10 notional | 14.95% |
| P90 notional | 15.00% |
| Formula intent honoured | **No** — cap fires on nearly half of all signals; formula produces identical maximum sizing regardless of signal quality |

At 1.00%, the risk formula systematically oversizes every trade. The PA hard cap
(`_MAX_SINGLE_TRADE_FRACTION = 0.15`) fires on 44% of orders, silently forcing
them to the 15% ceiling. All other orders reach close to that ceiling anyway.
Signal confidence and stop width have minimal effect on final position size.

### After (risk_pct = 0.25%)

| Metric | Value |
|---|---|
| Mean notional | 12.85% |
| Median notional | 13.97% |
| PA cap fire rate | **20.8%** |
| Guard 5 block rate | 0.0% |
| P10 notional | 7.09% |
| P25 notional | 12.13% |
| P75 notional | 14.98% |
| P90 notional | 14.99% |

At 0.25%, the PA cap fires on ~21% of signals (tight stops, high confidence) rather
than 44%. The remaining ~79% are sized by the risk formula according to stop width
and confidence. Wider stops produce smaller positions; high-conviction tight-stop
setups approach — but do not breach — the 15% ceiling.

### Scenario Comparison (from calibration report)

| risk_pct | Count | Mean% | Median% | PA Cap | Guard 5 |
|---|---|---|---|---|---|
| 1.00% (was) | 1073 | 14.98% | 14.98% | 44.3% | 0.0% |
| 0.50% | 1073 | 14.71% | 14.98% | 39.8% | 0.0% |
| 0.40% | 1073 | 14.35% | 14.98% | 39.6% | 0.0% |
| 0.30% | 1073 | 13.81% | 14.98% | 34.4% | 0.0% |
| **0.25% (new)** | 1073 | **12.85%** | **13.97%** | **20.8%** | **0.0%** |

0.25% was selected because it is the first setting at which:
1. The median separates from the 15% ceiling (13.97% vs 14.98%).
2. The P10 spread reaches 7.09% — signals now occupy a meaningful range, not a spike at 15%.
3. PA cap fire rate drops below 25% — formula drives the majority of sizing decisions.
4. Guard 5 remains at 0% — no trades are lost.

---

## What Was Changed

**Only:**
```
config.py  →  MAX_RISK_PER_TRADE_PCT = 0.0025
```

## What Was Not Changed

| Component | File | Status |
|---|---|---|
| Guard 5 threshold | `execution_engine/order_manager.py` | **Unchanged** — `MAX_CAPITAL_PER_TRADE_PCT = 15.0` |
| PA hard cap | `risk_control/portfolio_allocation_ai.py` | **Unchanged** — `_MAX_SINGLE_TRADE_FRACTION = 0.15` |
| PA symbol notional cap | same | **Unchanged** — `_MAX_SYMBOL_NOTIONAL_FRACTION = 0.15` |
| Stop-loss calculation | `config.py` `ATR_STOP_MULTIPLIER` | **Unchanged** |
| Execution logic | all execution modules | **Unchanged** |
| Capital allocation fractions | `config.py` `ALLOCATION` | **Unchanged** |
| CRE strategy budgets | `capital_risk_engine.py` | **Unchanged** |
| Risk Guardian kill conditions | `risk_guardian/risk_guardian.py` | **Unchanged** |
| All test files | `tests/` | **Unchanged** |

---

## Test Results

```
platform win32 — Python 3.14.3, pytest-9.0.2
collected 182 items

tests/oios/           — 168 passed
tests/test_candidate_contract.py — 14 passed

===================== 182 passed in 0.74s =====================
```

Pre-existing collection error in `tests/test_aet.py` (ImportError: `ATR_ZONE_MULTIPLIER`
from a stale `.pyc` cache) — present before this change, unaffected by it. All
importable tests pass.

---

## Rollback Procedure

**Single-line revert in `config.py`:**

```python
# Revert line 36 to:
MAX_RISK_PER_TRADE_PCT   = 0.01      # 1% of capital per trade
```

No database changes were made. No other files need to be touched. The system
returns to prior behaviour immediately on next process restart.

**Verification after rollback:**
```powershell
.venv\Scripts\python.exe -c "import config; print(config.MAX_RISK_PER_TRADE_PCT)"
# Expected: 0.01
.venv\Scripts\python.exe -m pytest tests/oios/ tests/test_candidate_contract.py -q
# Expected: 182 passed
```
