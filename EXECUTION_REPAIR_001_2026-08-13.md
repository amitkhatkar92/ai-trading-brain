# EXECUTION_REPAIR_001 — Execution Path Defect Repair
**Date:** 2026-08-13  
**Status:** READY_FOR_REVIEW  
**Scope:** `execution_engine/order_manager.py` — `_broker_place()` only  
**VPS deployment:** NONE — local implementation only  
**Production restart:** NONE  

---

## Executive Summary

Two execution-path defects caused `trades_executed = 0` since the Dhan broker
connection was activated.  Both are now fixed in a single targeted change to
`_broker_place()`.  A third item (EB003 SL architecture) was investigated and
found to be the **intended design** — no code change required.

---

## Defect EB001 — Wrong keyword argument names

### Root cause
`_broker_place()` called `DhanBroker.place_order()` using keyword names from
the old Zerodha adapter:

```python
# BEFORE (broken)
return self._broker.place_order(
    symbol=symbol, exchange="NSE",       # ← DhanBroker has no these params
    transaction_type=direction, quantity=qty,
    price=price, order_type=order_type,
)
```

`DhanBroker.place_order()` signature (unchanged):

```python
def place_order(self, security_id: str, exchange_segment: str,
                transaction_type: str, quantity: int,
                price: float = 0.0, order_type: str = "MARKET",
                product_type: str = "INTRADAY") -> Optional[str]:
```

### Consequence
Python raised `TypeError: unexpected keyword argument 'symbol'` on every
call.  The exception was caught silently by `_place_entry_with_retry()`'s
`try/except Exception`, retried 3 times, and discarded.  All approved signals
produced `ORDER_PLACED` never fired; `trades_executed = 0` in ControlTower DB.

---

## Defect EB002 — No NSE ticker → Dhan security_id translation

### Root cause
`_broker_place()` passed the raw NSE ticker (e.g. `"RELIANCE"`) directly to
`DhanBroker.place_order()` as `security_id`.  The Dhan API requires a numeric
security ID (e.g. `"2885"` for RELIANCE).  No symbol-to-ID translation existed
in the execution path.

The authoritative mapping `DHAN_SECURITY_MAP` in `data_feeds/dhan_feed.py`
already covered all 38 current scanner symbols but was never consulted by
`_broker_place()`.

---

## Fix — `_broker_place()` (single method, 14 lines changed)

```python
# AFTER (fixed) — execution_engine/order_manager.py  _broker_place()
def _broker_place(self, symbol: str, direction: str,
                   qty: int, price: float,
                   order_type: str = "LIMIT") -> Optional[str]:
    if not self._broker:
        log.info("[OrderManager] [SIM-%s] %s %s qty=%d @ %.2f",
                 order_type, direction, symbol, qty, price)
        import time as _t
        _ms = _t.time_ns() // 1_000_000
        return f"SIM_{symbol}_{direction}_Q{qty}_P{price:.2f}_{_ms}"
    # Resolve NSE ticker → Dhan (security_id, exchange_segment)  ← NEW
    from data_feeds.dhan_feed import DHAN_SECURITY_MAP as _DSM
    _sym = symbol.upper().replace(".NS", "").replace(".BO", "")
    _meta = _DSM.get(_sym)
    if not _meta:
        log.error(
            "[OrderManager] [MISSING_DHAN_MAPPING] symbol=%s not in DHAN_SECURITY_MAP"
            " — order blocked. Add entry to data_feeds/dhan_feed.py.",
            symbol,
        )
        return None
    return self._broker.place_order(
        security_id      = _meta["security_id"],   # ← correct kwarg
        exchange_segment = _meta["segment"],        # ← correct kwarg
        transaction_type = direction,
        quantity         = qty,
        price            = price,
        order_type       = order_type,
    )
```

**Design choices:**
- `DHAN_SECURITY_MAP` is imported inline (lazy) to avoid circular imports at
  module load time — consistent with the existing `import time as _t` pattern
  in the same method.
- `.NS` / `.BO` suffix stripping mirrors `DhanFeed._lookup()` exactly.
- Unknown symbol returns `None` (not raise) — consistent with retry contract:
  `_place_entry_with_retry` interprets `None` as transient failure and retries.
  After 3 retries it emits `[MISSING_DHAN_MAPPING]` 3 times in the log,
  providing a clear diagnostic.
- SIM path (`if not self._broker`) is unchanged — paper mode unaffected.

**Close path also fixed:** `close_position()` → `_broker_place(order_type="MARKET")` —
the same method is used for SL-triggered MARKET exits, so both entry and close
paths are corrected by this single change.

---

## EB003 — SL Architecture (investigation, no code change)

### Finding: software SL is the INTENDED architecture

| Fact | Detail |
|---|---|
| `DhanBroker` methods | `place_order`, `cancel_order`, `get_positions`, `get_portfolio` — **no `place_sl_order`** |
| `_place_stop_loss()` | `if hasattr(self._broker, "place_sl_order"):` — always False for DhanBroker |
| `_place_stop_loss()` return | Always `None` for DhanBroker |
| `sl_order_id` on OrderRecord | Always `""` — expected, not a defect |
| Primary SL mechanism | `TradeMonitor.check_all()` — software tick loop comparing LTP vs `order.stop_loss` |
| SL trigger action | `TradeMonitor._act()` → `order_manager.close_position()` → `_broker_place(MARKET)` |

**Verdict:** Exchange-side SL orders are aspirational; `TradeMonitor` software loop
is the production SL mechanism.  Entry succeeds even when `_place_stop_loss()`
returns `None`.  The position is protected by the software SL as long as
`TradeMonitor` is running.

### Acknowledged risk
If the `TradeMonitor` monitoring loop is not running (e.g. after an abnormal
restart before `check_all()` is called), open positions have no SL protection
until the loop resumes.  This is a pre-existing architectural risk unrelated to
EB001/EB002.

---

## Security-ID Mapping Coverage

| Scope | Count | Status |
|---|---|---|
| Current scanner symbols (`_BASE_WATCHLIST` + `_EXTENDED_WATCHLIST`) | 38 | ✅ 38/38 in `DHAN_SECURITY_MAP` |
| BHEL | Not in scanner | Absent from map — correct |
| PNB | Not in scanner | Absent from map — correct |

**BHEL/PNB absence root cause:** both are Nifty PSU/midcap stocks outside the
current trading universe.  Their NSE IDs are:
- BHEL: `security_id="438"`, exchange=NSE, series=EQ (from `security_id_list.csv`)
- PNB: `security_id="10666"`, exchange=NSE, series=EQ

**Safe addition path:** add to `DHAN_SECURITY_MAP` only when they are
simultaneously added to the scanner watchlist.

**Segment collision (ADANIENT / BANKNIFTY):** both carry `security_id="25"` in
the Dhan system but with different `segment` values (`NSE_EQ` vs `IDX_I`).  The
fix passes both `security_id` and `exchange_segment` so routing is unambiguous.

---

## Test Suite

### New: `test_execution_boundary_002.py` (16 tests)

| Test | Verifies |
|---|---|
| A — BHEL BUY patched map | Correct `security_id="438"`, `exchange_segment="NSE_EQ"` for BHEL |
| B — RELIANCE BUY live map | `security_id="2885"`, `exchange_segment="NSE_EQ"` |
| C — Unknown symbol | `MISSING_DHAN_MAPPING` log, 0 broker calls, returns `None` |
| D — qty=0 | ZeroQty guard blocks, 0 broker calls |
| E — Duplicate | DupGuard blocks second call, max 1 broker request |
| F — Entry + SL architecture | `stop_loss` set on OrderRecord, `sl_order_id=""`, 1 broker call (entry only) |
| G — Entry ok + SL returns None | execute() NOT aborted, software SL anchor populated |
| H — Broker unavailable | SIM path, `SIM_*` order_id, no real API call |
| I — stop_loss=0 | Position created (pre-existing gap documented) |
| J — Retry 3× | Exactly 3 broker calls, 2 sleeps |
| BHEL/PNB mapping | Confirmed absent from map, all 38 scanner symbols present |
| TATACONSUM/POWERGRID | Correct IDs verified |
| ADANIENT segment | `NSE_EQ` not `IDX_I` — segment collision correctly resolved |
| .NS suffix | Normalised to bare symbol before lookup |
| EB001 TypeErrror gone | Correct kwargs raise no TypeError |
| SAFETY sentinel | Real Dhan API never reached |

**Result: 16/16 PASS (0.45 s)**

### Updated: `test_execution_boundary_001.py` (15 tests)

Post-fix updates:
- Default signal symbol changed from `BHEL` (not in map) to `RELIANCE` (in map)
- `test_H_unknown_symbol_passes_through_execute` → `test_H_unknown_symbol_blocked_at_mapping_layer`  
  (old: asserted broker called; new: asserts broker NOT called, `None` returned)
- `test_INSTRUMENT_no_symbol_map_in_broker_place` → `test_INSTRUMENT_dhan_security_map_used_in_broker_place`  
  (old: documented gap; new: confirms fix present)
- `test_A` now validates `security_id=` and `exchange_segment=` kwargs; confirms absence of old wrong names

**Result: 15/15 PASS (0.52 s combined with EB002)**

### Regression: existing suites

| Suite | Pre-fix | Post-fix |
|---|---|---|
| `tests/test_frz001_journal.py` (8 tests) | 8 pass | 8 pass ✅ |
| `tests/test_governance_window.py` | 21 pass, **1 fail** (pre-existing) | 21 pass, 1 fail (unchanged) |
| `tests/test_aet.py` | 8 pass, **5 fail** (pre-existing) | 8 pass, 5 fail (unchanged) |
| `tests/test_orj001.py` (11 tests) | 11 pass | 11 pass ✅ |

The 6 pre-existing failures in `test_governance_window.py` and `test_aet.py`
are confirmed pre-existing via `git stash` + baseline run — not introduced by
this fix.

---

## Files Changed

| File | Change | Interfaces changed? |
|---|---|---|
| `execution_engine/order_manager.py` | `_broker_place()` body: add DHAN_SECURITY_MAP lookup; correct kwargs | No — signature unchanged |
| `test_execution_boundary_001.py` | Updated tests A, H, INSTRUMENT to reflect post-fix reality; changed default signal symbol | N/A (test file) |
| `test_execution_boundary_002.py` | NEW — 16 broker-spy tests (EB003 task) | N/A |
| `EXECUTION_REPAIR_001_2026-08-13.md` | NEW — this report | N/A |

**Files NOT modified:** `dhan_broker.py`, `dhan_feed.py`, `config.py`, all strategy files.

---

## Remaining Risks

1. **SL=0.0 signals:** `execute()` does not reject `stop_loss=0`. `TradeMonitor`
   never triggers close for positive LTP → position unprotected. Gate should
   exist in DecisionEngine (upstream). Documented in Test I.

2. **TradeMonitor must be running:** Software SL protection depends on the
   monitoring loop being active. If `TradeMonitor` is not started (e.g. partial
   startup), positions have no SL until it resumes.

3. **MISSING_DHAN_MAPPING on retry:** When an unmapped symbol hits `_broker_place`,
   `_place_entry_with_retry` retries 3 times — emitting the error log 3 times
   per signal.  The symbol will never succeed across retries (mapping is static),
   so the 3 retries are wasted.  Mitigation: check for `MISSING_DHAN_MAPPING` in
   orchestrator and skip retry, or add a pre-execution mapping check.  Not
   blocking for current scanner (all 38 symbols covered).

---

## Mandatory Safety Footer

```
Real Dhan orders:            0
Dhan write calls:            0
VPS deployment:              0
Production restart:          0
Production strategy changes: 0
```
