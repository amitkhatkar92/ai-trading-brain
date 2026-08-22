# LIVE EXECUTION AUDIT
## LTR-001 — Phase 2

**Date:** 2026-08-06  
**Scope:** Full order lifecycle from signal generation through settlement  
**Auditor:** LTR-001 Certification Process

---

## 1. ORDER CREATION

### Signal-to-Order Pipeline

```
TradeSignal (from OpportunityEngine)
    ↓
CapitalRiskEngine.allocate()   — compute quantity
    ↓
RiskManagerAI.filter()         — per-trade risk gates
    ↓
DecisionEngine.decide()        — confidence threshold ≥ 6.8
    ↓
FailSafeRiskGuardian.evaluate() — portfolio circuit breakers
    ↓
OrderManager.execute()         — create OrderRecord
    ↓
Broker Adapter (paper/live)    — submit to exchange or paper journal
```

| Step | Verification | Status |
|------|-------------|--------|
| Signal validated for direction, symbol, prices | `TradeSignal` dataclass validation | ✅ |
| Quantity computed from risk formula | `CRE: qty = (capital × risk_pct) / SL_distance` | ✅ |
| Minimum R:R enforced | `MIN_RR_RATIO = 2.0` in `RiskManagerAI` | ✅ |
| Confidence floor enforced | `MIN_CONFIDENCE_SCORE = 6.8` | ✅ |
| Portfolio heat checked | `MAX_PORTFOLIO_RISK_PCT = 8.0%` | ✅ |
| Early entry blocked (< 09:45) | `_EXEC_WIN_OPEN_H = 9, _EXEC_WIN_OPEN_M = 45` | ✅ |
| Late entry blocked (> 14:30) | `_LATE_ENTRY_CUTOFF_H = 14, _LATE_ENTRY_CUTOFF_M = 30` | ✅ |
| Duplicate symbol rejected | `seen_symbols` set in filter loop | ✅ |

---

## 2. ORDER VALIDATION

### Pre-Execution Guards (Defence in Depth — 3 Layers)

| Layer | Location | Check |
|-------|----------|-------|
| Layer 1 | `master_orchestrator.py` — deep-scan handler | Suppresses task submission outside window |
| Layer 2 | `run_full_cycle()` / options fast-path | Skip full cycle when outside trading window |
| Layer 3 | `order_manager.execute()` | Hard block: `_EXEC_WIN_OPEN_H/M` check |

### AET (Adaptive Entry Timing)

Three timing modes selected per signal:
- `IMMEDIATE` — strong/neutral context
- `PULLBACK` — trending regime; price pushed deeper into zone
- `CONFIRMATION` — elevated VIX or distortion; deferred up to `AET_MAX_WAIT_CANDLES = 5`

| AET Validation | Implementation | Status |
|---------------|---------------|--------|
| VIX confirmation threshold | `AET_VIX_CONFIRM_THRESHOLD = 32.0` | ✅ |
| Pullback depth | `AET_PULLBACK_DIP_PCT = 0.10%` | ✅ |
| Max wait candles | `AET_MAX_WAIT_CANDLES = 5` | ✅ |
| Pending slot management | `_aet_pending` dict; checked every cycle | ✅ |

---

## 3. POSITION SIZING

| Rule | Value | Type | Status |
|------|-------|------|--------|
| Risk per trade | `MAX_RISK_PER_TRADE_PCT = 0.0025` | % of capital | ✅ |
| Max capital per trade | `MAX_CAPITAL_PER_TRADE_PCT = 15.0%` | % of capital | ✅ |
| Max total exposure | `MAX_TOTAL_OPEN_EXPOSURE_PCT = 85.0%` | % of capital | ✅ |
| Max concurrent positions | `MAX_OPEN_POSITIONS = 15` | Count | ✅ |
| Sizing formula | `qty = floor(risk_amount / stop_distance)` | Institutional | ✅ |
| Zero-quantity rejection | `qty = 0` signals dropped before execution | ✅ |
| ADV liquidity cap | `position_value ≤ ADV × 2%` | Ratio | ✅ |
| Volatility guard | `ATR% > 4.0%` → signal dropped | Ratio | ✅ |

---

## 4. CAPITAL RESERVATION

| Aspect | Implementation | Status |
|--------|---------------|--------|
| Portfolio capital model | `Portfolio(capital=TOTAL_CAPITAL)` | ✅ |
| Open exposure tracking | `portfolio.total_exposure` updated on each fill | ✅ |
| Available capital derivation | `capital - open_exposure` (implicit) | ✅ |
| CRE heat audit | `[CREPositionCountAudit]` log per cycle | ✅ |
| Rejection on heat cap | `_EXPOSURE_CAP` rejection with reason | ✅ |

---

## 5. PARTIAL FILLS

| Aspect | Implementation | Status |
|--------|---------------|--------|
| Status tracking | `OrderRecord.status`: SUBMITTED → PARTIALLY_FILLED → FILLED | ✅ |
| Fill price tracking | `OrderRecord.fill_price` | ✅ |
| Partial fill detection | Status in `("PENDING", "SUBMITTED", "PARTIALLY_FILLED")` | ✅ |
| Exposure adjustment | Portfolio exposure updated on each fill event | ✅ |

---

## 6. ORDER REJECTION

| Rejection Reason | Implementation | Status |
|-----------------|---------------|--------|
| RR below minimum | `RR_REJECTION` in `[RiskControlDecision]` | ✅ |
| Portfolio heat exceeded | `HEAT_REJECTION` | ✅ |
| Confidence below floor | `GOVERNANCE_REJECTION` (conf < 6.8) | ✅ |
| Duplicate symbol | Seen-symbols dedupe | ✅ |
| Liquidity below minimum | `LIQUIDITY_REJECTION` (ADV < 50Cr or capacity cap) | ✅ |
| Kill switch active | `FailSafeRiskGuardian` → all signals rejected | ✅ |
| Time window violation | Early/late entry hard block | ✅ |
| Exposure cap | `_MAX_POSITIONS` count limit | ✅ |
| EARLY_LOSS cooldown | 24-hour cooldown after adaptive early exit | ✅ |

---

## 7. ORDER CANCELLATION

| Cancellation Trigger | Implementation | Status |
|---------------------|---------------|--------|
| Limit order time expiry | `LIMIT_CANDLE_EXPIRY = 8 candles (40 min)` | ✅ |
| Regime change | Context-based: regime changed since signal creation | ✅ |
| Distortion event | `signal_distortion` flag on OrderRecord | ✅ |
| VIX spike | `signal_vix` vs current VIX comparison | ✅ |
| Manual cancel | `cancel_order()` via broker adapter | ✅ |
| AET timeout | `AET_MAX_WAIT_CANDLES` exceeded | ✅ |

---

## 8. PORTFOLIO REPLACEMENT (SMART-SWAP)

| Aspect | Implementation | Status |
|--------|---------------|--------|
| Pathway A (cross-signal swap) | Conviction ranking; lower-conviction replaced by higher | ✅ |
| Daily rotation throttle | At most 1 forced replacement per calendar day | ✅ |
| Same-symbol protection | `_SAME_ZONE_PCT` proximity check on re-entry | ✅ |
| TradeMonitor deregister | Replaced positions deregistered from monitoring | ✅ |
| Position count preservation | Swap does not increase open position count | ✅ |
| Position governor | `DD_REDUCE_FACTOR = 0.5` in drawdown tier | ✅ |

---

## 9. EMERGENCY EXIT

| Exit Type | Implementation | Status |
|-----------|---------------|--------|
| Kill switch halt | `FailSafeRiskGuardian` → all trading halted | ✅ |
| Daily loss halt | `MAX_DAILY_LOSS_PCT = 2.0%` → halt | ✅ |
| SESSION_EXPIRED | Carry beyond `_CARRY_DAYS_BY_TYPE` limit | ✅ |
| ORPHAN_WATCH governance | Past carry limit → restricted status, monitored | ✅ |
| Adaptive early exit (EARLY_LOSS) | Profit-extended SL hit → close + 24h cooldown | ✅ |
| Stop-loss hit | `TradeMonitor` detects SL breach → `close_position()` | ✅ |
| Target hit | `TradeMonitor` detects target breach → `close_position()` | ✅ |

---

## 10. KILL SWITCH

| Circuit Breaker | Threshold | Action |
|----------------|-----------|--------|
| Market crash (Nifty) | `< -5.0%` intraday | Halt all trading |
| Market fear (VIX) | `> 45.0` | Halt all trading |
| Daily loss | `> 2.0%` of capital | Halt all trading |
| Max open trades | `> 8` concurrent | Block new entries |
| Portfolio risk | `> 5.0%` risk-at-stake | Block new entries |
| Consecutive losses | 3 consecutive losing fills | Temporary pause |
| Margin buffer | `< 20%` free margin | Block new entries |
| Dhan circuit breaker | 5 consecutive API failures | Fallback to yfinance |

The `FailSafeRiskGuardian` is the final gate before any order reaches the broker. It is stateful, intraday-resetting, and parameterised by `total_capital` — not hard-coded.

---

## 11. BROKER RECONNECT

| Scenario | Recovery | Status |
|----------|---------|--------|
| Token expired | `reload_token()` via Telegram → `_connect()` | ✅ |
| Circuit breaker tripped | `reload_token()` → reset counter → re-probe | ✅ |
| Options session stale | Auto-reconnect after 3 consecutive failures per symbol | ✅ |
| WebSocket disconnected | 5-second reconnect loop in `_ws_loop()` | ✅ |
| Process restart | `_restore_from_journal()` rehydrates all open positions | ✅ |

---

## 12. MARKET CLOSE HANDLING

| Rule | Implementation | Status |
|------|---------------|--------|
| No entries after 14:30 | `_LATE_ENTRY_CUTOFF_H/M` hard block | ✅ |
| Elevated threshold 13:30–14:30 | Minimum score 7.0 in elevated window | ✅ |
| EOD learning at 15:35 | Scheduled slot in `SCHEDULE` dict | ✅ |
| SESSION_EXPIRED at EOD | `check_and_expire_carries()` — carries past limit | ✅ |
| Monitoring continues to close | `TradeMonitor` active until market close | ✅ |
| Market holiday handling | Weekday filter in `_trading_days_elapsed()` | ✅ |

---

## 13. RESTART RECOVERY

| Aspect | Implementation | Status |
|--------|---------------|--------|
| Journal re-hydration | `_restore_from_journal()` reads `paper_trades.csv` | ✅ |
| Ghost close detection | `closed_orders_{date}.txt` registry | ✅ |
| Expiry retry count | `expiry_retries.json` sidecar survives restart | ✅ |
| Orphan tmp file cleanup | `expiry_retry_*.tmp` files cleaned on startup | ✅ |
| LTP pre-fetch | `_prefetch_restored_ltps()` resolves LTP immediately | ✅ |
| Post-restore governance | Immediate SL and expiry checks on restored positions | ✅ |

---

## 14. EXECUTION AUDIT SUMMARY

| Domain | Verification Result |
|--------|-------------------|
| Order Creation | ✅ VERIFIED |
| Order Validation (3-layer defence) | ✅ VERIFIED |
| Position Sizing | ✅ VERIFIED |
| Capital Reservation | ✅ VERIFIED |
| Partial Fills | ✅ VERIFIED |
| Order Rejection | ✅ VERIFIED |
| Order Cancellation | ✅ VERIFIED |
| Portfolio Replacement | ✅ VERIFIED |
| Emergency Exit | ✅ VERIFIED |
| Kill Switch | ✅ VERIFIED |
| Broker Reconnect | ✅ VERIFIED |
| Market Close Handling | ✅ VERIFIED |
| Restart Recovery | ✅ VERIFIED |

**Live Execution Audit Result: PASS**  
All execution lifecycle stages verified. No gaps in critical execution path.

*Report completed: 2026-08-06*
