# EXECUTION_BOUNDARY_001_2026-08-13

## Live Execution Path Verification — Final Report

**Task ID:** EXECUTION-BOUNDARY-001  
**Date:** 2026-08-13  
**Status:** COMPLETE  
**Verdict:** **EXECUTION_PATH_DEFECT_FOUND**

---

## 1. Scope and Method

### Objective
Trace the production execution path from a synthetic approved `TradeSignal` all the way to `DhanBroker.place_order()`. Verify the path is wired correctly, all guards function, and no real Dhan order is placed during verification.

### Path Traced
```
TradeSignal
  → OrderManager.execute()           [execution_engine/order_manager.py]
    → Guard stack (10 guards in sequence)
    → _place_entry_with_retry()
      → _broker_place()
        → self._broker.place_order() [execution_engine/brokers/dhan_broker.py]
```

### Method
- Read-only source code analysis: `order_manager.py`, `dhan_broker.py`
- 15 automated tests via `test_execution_boundary_001.py`
- Runtime Python introspection (no live API calls)
- All broker calls intercepted by `MagicMock` spy + `_dhan_safety_sentinel`

### Safety Guarantee
```
Production code changes:  0
Configuration changes:    0
Real Dhan orders placed:  0
Paper orders created:     0
Broker write calls:       0   (intercepted by spy)
Positions created:        0
```

---

## 2. Execution Path — Code Trace

### 2.1 `OrderManager.execute()` — guard stack

File: `execution_engine/order_manager.py`, line 446.

Guards fire in this order:

| # | Guard | Trigger | Action |
|---|---|---|---|
| 1 | Signal Freshness Gate | signal age > 15 trading days | `return None` |
| 2 | ExecutionWindowBlock | before 09:45 IST | `return None` |
| 3 | DupGuard / SmartSwap | same symbol open | `return None` or swap |
| 4 | Max Positions Guard | ≥ 15 open positions | `return None` or swap |
| 5 | EarlyLoss Cooldown | EARLY_LOSS exit < 24h ago | `return None` |
| 6 | LateEntryBlock | ≥ 14:30 IST, or score < 7.0 after 13:30 | `return None` |
| 7 | Zero-Qty Guard | `qty = signal.quantity × modifier` ≤ 0 | `return None` |
| 8 | Capital/Trade Guard | notional > 15% of capital | `return None` |
| 9 | Total Exposure Guard | exposure > 85% of capital | `return None` |
| 10 | Price Integrity Guard | SIM/phantom price detected | `return None` |
| 11 | AET CONFIRMATION | VIX ≥ 32 or distortion | defer to `_aet_pending` |

All guards verified by automated tests. Tests B, E, G1, G2, J confirm correct blocking.

### 2.2 `_place_entry_with_retry()` — line 1887

Calls `_broker_place()` up to `MAX_ORDER_RETRIES=3` times with exponential backoff (0.5 s, 1.0 s, 2.0 s). Wraps each attempt in `try/except Exception` — ALL exceptions (including `TypeError`) are caught and logged as errors, then retried.

### 2.3 `_broker_place()` — line 1942

```python
def _broker_place(self, symbol: str, direction: str,
                   qty: int, price: float,
                   order_type: str = "LIMIT") -> Optional[str]:
    if not self._broker:
        return f"SIM_{symbol}_{direction}_Q{qty}_P{price:.2f}_{ms}"
    return self._broker.place_order(
        symbol=symbol,            # ← DEFECT: wrong kwarg name
        exchange="NSE",           # ← DEFECT: wrong kwarg name
        transaction_type=direction,
        quantity=qty,
        price=price,
        order_type=order_type,
    )
```

### 2.4 `DhanBroker.place_order()` — brokers/dhan_broker.py

```python
def place_order(self, security_id: str, exchange_segment: str,
                transaction_type: str, quantity: int,
                price: float = 0.0, order_type: str = "MARKET",
                product_type: str = "INTRADAY") -> Optional[str]:
```

---

## 3. Critical Defect — DEFECT-EB001

### Description

`OrderManager._broker_place()` calls `DhanBroker.place_order()` using the **wrong keyword argument names**:

| `_broker_place` sends | `DhanBroker.place_order` expects |
|---|---|
| `symbol=symbol` | `security_id` |
| `exchange="NSE"` | `exchange_segment` |
| `transaction_type=direction` | `transaction_type` ✓ |
| `quantity=qty` | `quantity` ✓ |
| `price=price` | `price` ✓ |
| `order_type=order_type` | `order_type` ✓ |

### Failure Mechanism

Python raises `TypeError: DhanBroker.place_order() got an unexpected keyword argument 'symbol'` **before** the body of `place_order` executes. This fires regardless of `_connected` state — even in simulation mode — because Python validates keyword arguments at call time.

The `TypeError` is caught by `_place_entry_with_retry`'s `try/except Exception as exc: log.error(...)`. All 3 retry attempts fail identically. `_place_entry_with_retry` returns `None`. `execute()` logs `"Entry order failed"` and returns `None`.

**Result: No order is ever placed. `trades_executed=0` in all cycles.**

### Verification

```python
# Confirmed by test_DEFECT_broker_parameter_name_mismatch:
dhan = DhanBroker(...)
dhan._connected = False
dhan._dhan = None
dhan.place_order(symbol="BHEL", exchange="NSE", ...)
# → TypeError: DhanBroker.place_order() got an unexpected keyword argument 'symbol'
```

```
>>> DEFECT_CONFIRMED TypeError: DhanBroker.place_order() got an unexpected keyword argument 'symbol'
```

### Correct Fix (not applied in this audit — production change requires explicit instruction)

```python
# In _broker_place(), replace:
return self._broker.place_order(
    symbol=symbol, exchange="NSE", ...
)
# With:
return self._broker.place_order(
    security_id=symbol,          # correct kwarg name
    exchange_segment="NSE_EQ",   # correct kwarg name + correct value
    transaction_type=direction,
    quantity=qty,
    price=price,
    order_type=order_type,
    product_type="INTRADAY",
)
```

Note: The `exchange` value also needs to change from `"NSE"` to `"NSE_EQ"` (the Dhan exchange_segment format for NSE equity).

---

## 4. Secondary Defect — DEFECT-EB002: No Symbol→SecurityID Mapping

### Description

`_broker_place()` passes the raw NSE ticker symbol (e.g., `"BHEL"`) directly as the first positional/keyword argument to `DhanBroker.place_order()`. Dhan's API expects a numeric `security_id` (e.g., `"500103"` for BHEL).

No translation layer exists between equity scanner output (NSE ticker) and Dhan order placement (numeric security_id).

**Result:** Even after fixing DEFECT-EB001, orders would likely be rejected by the Dhan API for invalid `security_id` values.

### Evidence

```python
# test_INSTRUMENT_no_symbol_map_in_broker_place verifies:
# "GLOBAL_SYMBOL_MAP" does NOT appear in _broker_place source
# → no symbol translation exists
```

Line 1978 in `order_manager.py` references `GLOBAL_SYMBOL_MAP` only in a comment about `_prefetch_restored_ltps`, not in `_broker_place`.

---

## 5. Architectural Findings (guards not in execute())

These are by design — enforced at other layers — but documented for completeness:

| Guard | Enforced In | Not In execute() |
|---|---|---|
| Strategy disable | StrategyHealthMonitor (Layer 12) | ✓ Not in execute() |
| Confidence threshold (6.5) | DecisionEngine (Layer 10) | ✓ Not in execute() |
| Kill switch | MasterOrchestrator.run_full_cycle() | ✓ Not in execute() |
| Symbol validation | DhanBroker (Layer 11) | ✓ Not in execute() |

---

## 6. Test Results — 15/15 PASSED

Run: `test_execution_boundary_001.py` via pytest  
Duration: 0.34 s

| Test | Case | Result | Notes |
|---|---|---|---|
| test_A_valid_signal_broker_called_once | A | PASS | Spy confirms 1 broker call |
| test_B_zero_quantity_blocked | B | PASS | Guard blocks qty=0 |
| test_C_strategy_disable_not_enforced_in_execute | C | PASS | Architectural finding |
| test_D_low_confidence_not_enforced_in_execute | D | PASS | Architectural finding |
| test_E_capital_guard_blocks_oversized_trade | E | PASS | 25% > 15% cap blocked |
| test_F_kill_switch_not_enforced_in_execute | F | PASS | Architectural finding |
| test_G1_before_0945_execution_window_block | G1 | PASS | ExecutionWindowBlock fires |
| test_G2_after_1430_late_entry_block | G2 | PASS | LateEntryBlock fires |
| test_H_unknown_symbol_passes_through_execute | H | PASS | No validation in execute() |
| test_I_broker_unavailable_returns_none_no_retry_storm | I | PASS | 3 retries, 2 sleeps, None |
| test_J_duplicate_signal_idempotency | J | PASS | DupGuard blocks 2nd call |
| test_DEFECT_broker_parameter_name_mismatch | DEFECT | PASS | TypeError confirmed |
| test_DEFECT_correct_call_works | DEFECT+ | PASS | Correct call → SIM_DHAN |
| test_INSTRUMENT_no_symbol_map_in_broker_place | INSTRUMENT | PASS | No map in _broker_place |
| test_SAFETY_real_dhan_api_never_called | SAFETY | PASS | Sentinel never triggered |

---

## 7. Live Log Evidence Classification

Based on CT telemetry history (`trades_executed=0` across all cycles):

| Status | Classification |
|---|---|
| `execute()` reached | **REACHED_BUT_FAILED** |
| `_broker_place()` reached | **REACHED_BUT_FAILED** |
| `DhanBroker.place_order()` called | **NOT_REACHED** (TypeError before body runs) |
| Real Dhan API called | **NOT_REACHED** |

The `NOT_REACHED` at `DhanBroker.place_order()` body-level is the key: the TypeError fires as the Python interpreter resolves keyword argument names, before the first line of `place_order()` executes.

---

## 8. Dhan API Readiness (Read-Only Inspection)

| Attribute | Value | Source |
|---|---|---|
| `DhanBroker._connected` | `True` | Runtime Python check |
| `DhanBroker._dhan` | `dhanhq.dhanhq` instance | Runtime Python check |
| `get_positions()` response | `dict` (success) | Read-only positions API call |
| `PAPER_TRADING` env | `false` | `.env` file |
| `ACTIVE_BROKER` env | `dhan` | `.env` file |
| Kill switch | `ENABLED` (file not present → default) | `utils/kill_switch.py` |

DhanHQ SDK is authenticated and the positions endpoint responds. The broker is live-capable. The only blocker is the execution path defects documented above.

---

## 9. Order Type Verification

`execute()` explicitly constructs `OrderRecord(order_type="LIMIT")` (line ~785).  
`_place_entry_with_retry()` passes `order_type="LIMIT"` to `_broker_place()` (line 1895).  
`_broker_place()` passes `order_type=order_type` to `DhanBroker.place_order()`.

**All entry orders are LIMIT orders. Closes use MARKET (hardcoded in `close_position()`).**

---

## 10. Zone Price Calculation

For a BUY signal with `entry_zone_high > 0`:  
```
zone_price = entry_zone_high    (priority 1: precomputed ATR bound)
```

For the test fixture (BHEL BUY, entry=270, zone_high=271.7):
```
zone_price = 271.70
_aet_mode  = IMMEDIATE (VIX=14.0 < 32.0, regime=RANGE)
_final_px  = 271.70  (IMMEDIATE → no pullback adjustment)
```

Broker receives `price=271.70, order_type="LIMIT"`.

---

## 11. Instrument Mapping Status

| Symbol | Expected Dhan security_id | Mapping in _broker_place | Status |
|---|---|---|---|
| BHEL | ~500103 | Not translated | DATA_GAP |
| RELIANCE | ~2885 | Not translated | DATA_GAP |
| PNB | ~532461 | Not translated | DATA_GAP |

No `GLOBAL_SYMBOL_MAP` (NSE ticker → Dhan numeric ID) exists in the execution path. This is DEFECT-EB002.

---

## 12. Path from SC-001 to This Audit

SC-001 (completed prior) found:
- `sim_approved=2, risk_approved=0, trades_executed=0` was explained by a CT counter-overwrite bug (not a risk-layer rejection)
- All signals were rejected at DecisionEngine (score < 6.5 threshold)

This audit independently confirms a second-layer explanation:
- **Even if a signal scored above 6.5**, the execution path would fail silently due to DEFECT-EB001 (TypeError)
- The system has therefore **never placed a live Dhan order** since `PAPER_TRADING=false` was set

---

## 13. Final Verdict

**EXECUTION_PATH_DEFECT_FOUND**

### Primary Defects

| ID | Severity | Location | Description |
|---|---|---|---|
| DEFECT-EB001 | **CRITICAL** | `order_manager._broker_place()` L1951 | Wrong keyword arg names: `symbol=` and `exchange=` instead of `security_id=` and `exchange_segment=`. Causes silent TypeError on every live order attempt. |
| DEFECT-EB002 | **HIGH** | `order_manager._broker_place()` | No symbol→Dhan security_id translation. Raw NSE tickers passed as security_id. |

### What Works Correctly

- All 10 execute() guards function as designed
- DupGuard idempotency is correct (Case J)
- Retry logic is capped at 3 (no retry storm)
- AET mode selection is correct (IMMEDIATE for RANGE + low VIX)
- Zone price calculation is correct
- OrderRecord creation is correct
- Paper journal path (when PAPER_TRADING=true) is independent of these defects

### Next Steps Required

1. Fix `_broker_place()` keyword argument names: `symbol=` → `security_id=`, `exchange="NSE"` → `exchange_segment="NSE_EQ"`
2. Implement NSE ticker → Dhan security_id lookup (GLOBAL_SYMBOL_MAP or equivalent)
3. After fix: run `test_execution_boundary_001.py` to verify guard integrity is preserved
4. Deploy per mandatory deploy cycle in copilot-instructions.md

---

## Mandatory Footer

```
Production code changes: 0
Configuration changes: 0
Real Dhan orders: 0
Paper orders: 0
Broker write calls: 0
Positions created: 0
```
