# PRODUCTION SAFETY REPORT
## LTR-001 — Phase 5

**Date:** 2026-08-06  
**Scope:** All production safety mechanisms verified  
**Auditor:** LTR-001 Certification Process

---

## 1. KILL SWITCH

### Implementation: `FailSafeRiskGuardian` (`risk_guardian/risk_guardian.py`)

The kill switch is the final authority before any order reaches the broker. It evaluates every cycle and can halt the system entirely.

```python
class FailSafeRiskGuardian:
    def evaluate(signals, snapshot, portfolio) -> GuardianDecision:
        halt = _check_system_halts(snapshot, portfolio)
        if halt:
            return GuardianDecision(approved=False, rejected_signals=ALL)
```

| Kill Condition | Threshold | Priority |
|---------------|-----------|----------|
| Nifty intraday drop | `KILL_SWITCH_NIFTY_DROP = -5.0%` | 1 (highest) |
| VIX spike | `KILL_SWITCH_VIX = 45.0` | 1 (highest) |

**Verification:** Both conditions result in `GuardianDecision(approved=False)` with ALL signals in `rejected_signals`. Trading fully halted until condition resolves or system restarts.

**Status: ✅ VERIFIED**

---

## 2. MAXIMUM DAILY LOSS

### Implementation: `FailSafeRiskGuardian._daily_pnl` tracking

```python
MAX_DAILY_LOSS_PCT = 2.0  # % of total capital
# daily_loss_limit = total_capital × 0.02
# if _daily_pnl ≤ -daily_loss_limit → HALT
```

| Aspect | Implementation | Status |
|--------|---------------|--------|
| Threshold | 2.0% of `total_capital` | ✅ Capital-parameterised |
| Trigger | `record_trade_result(pnl, won)` called on every fill | ✅ |
| Reset | `_reset_daily_if_new_session()` — resets at market open | ✅ |
| Halt action | `_trading_halted = True` → all new signals rejected | ✅ |
| State persistence | In-memory; resets cleanly on restart | ✅ |

**Observation:** SRA diagnostic `if _today_pnl < -50000` in `master_orchestrator.py:5145` is a pre-market readiness label only. The actual trading halt uses `FailSafeRiskGuardian` which correctly applies `total_capital × 2.0%`.

**Status: ✅ VERIFIED**

---

## 3. MAXIMUM PORTFOLIO RISK

| Layer | Threshold | Implementation |
|-------|-----------|---------------|
| Risk Manager AI | `MAX_PORTFOLIO_RISK_PCT = 8.0%` (total risk-at-stake) | `risk_manager_ai.py` |
| Risk Guardian | `MAX_PORTFOLIO_RISK_PCT = 5.0%` (stricter final gate) | `risk_guardian.py` |
| Capital Risk Engine | VIX/regime/drawdown limits reduce deployable | `capital_risk_engine.py` |

The two-layer approach means portfolio risk is checked both before and after the decision engine. The Guardian's 5.0% threshold is stricter and provides a second safety net.

**Status: ✅ VERIFIED**

---

## 4. MAXIMUM EXPOSURE

| Limit | Threshold | Implementation |
|-------|-----------|---------------|
| Per-trade capital cap | `MAX_CAPITAL_PER_TRADE_PCT = 15.0%` | `order_manager.py` |
| Total exposure cap | `MAX_TOTAL_OPEN_EXPOSURE_PCT = 85.0%` | `order_manager.py` |
| Concurrent positions | `MAX_OPEN_POSITIONS = 15` | `order_manager.py` |
| Strategy position cap | `_MAX_POSITIONS = 8` in CRE | `capital_risk_engine.py` |
| Liquidity cap | `position_value ≤ ADV × 2%` | `LiquidityGuard` |

**Status: ✅ VERIFIED**

---

## 5. MAXIMUM OPEN POSITIONS

| Layer | Limit | Status |
|-------|-------|--------|
| `OrderManager` | `MAX_OPEN_POSITIONS = 15` | ✅ |
| `CapitalRiskEngine` | `_MAX_POSITIONS = 8` | ✅ |
| `FailSafeRiskGuardian` | `MAX_OPEN_TRADES = 8` | ✅ |

Three independent position count limits provide defence in depth. The stricter CRE/Guardian limit of 8 applies before OrderManager's limit of 15.

**Status: ✅ VERIFIED**

---

## 6. DUPLICATE ORDER PROTECTION

| Mechanism | Implementation | Status |
|-----------|---------------|--------|
| Symbol uniqueness per cycle | `seen_symbols` set in `RiskManagerAI.filter()` | ✅ |
| Open position deduplication | `portfolio.positions` checked before new order | ✅ |
| AET pending deduplication | `_aet_pending` keyed by `slot_id` | ✅ |
| Re-entry deduplication | `_reentry_slots` keyed by `original_order_id` | ✅ |
| Journal closed-order registry | `closed_orders_{date}.txt` — prevents re-close | ✅ |
| EARLY_LOSS cooldown | 24-hour symbol-level block after early exit | ✅ |
| Same-zone price protection | `_SAME_ZONE_PCT` — blocks re-entry too close to prior close | ✅ |

**Status: ✅ VERIFIED**

---

## 7. CIRCUIT BREAKER HANDLING

### Trading Circuit Breakers

| Breaker | Trigger | Action |
|---------|---------|--------|
| Consecutive losses | 3 losing fills | Temporary trading pause |
| Daily loss halt | `> 2%` daily loss | Full halt until next session |
| Kill switch (VIX) | VIX `> 45` | Full halt |
| Kill switch (Nifty) | `< -5%` intraday | Full halt |

### Broker Circuit Breaker (Dhan)

| Breaker | Trigger | Action |
|---------|---------|--------|
| Dhan data API | 5 consecutive API failures | `_live = False` → yfinance fallback |
| Options auto-reconnect | 3 consecutive option_chain failures per symbol | SDK client recreated |

The broker circuit breaker is classified separately from the trading circuit breaker. A Dhan API failure does NOT halt trading — the system falls back to yfinance for market data while order routing continues.

**Status: ✅ VERIFIED**

---

## 8. MARKET HOLIDAY HANDLING

| Aspect | Implementation | Status |
|--------|---------------|--------|
| Carry day counting | `_trading_days_elapsed()` counts weekdays (Mon–Fri) only | ✅ |
| Weekend budget exclusion | `d.weekday() < 5` guard | ✅ |
| Holiday approximation | Treated as trading days (conservative — causes earlier expiry not later) | ✅ |
| Pre-market guard | No trades before 09:45 IST regardless of day | ✅ |
| Orchestrator guard | Market hours check before cycle execution | ✅ |

**Design note (from code comment):** Holidays add at most 1 session of over-counting per occurrence, which is the safe failure mode (earlier exit, not later). Accepted risk per CarryDesignReview Jun 8 2026.

**Status: ✅ VERIFIED**

---

## 9. RESTART RECOVERY

| Recovery Aspect | Implementation | Status |
|----------------|---------------|--------|
| Open position rehydration | `_restore_from_journal()` on `OrderManager.__init__()` | ✅ |
| Ghost-close detection | `closed_orders_{date}.txt` registry checked before restore | ✅ |
| Expiry retry count preservation | `expiry_retries.json` sidecar | ✅ |
| Immediate SL/target check post-restore | `post_restore_governance_pass()` | ✅ |
| Session-expired positions at restore | `check_and_expire_carries()` run at restore | ✅ |
| LTP pre-fetch | `_prefetch_restored_ltps()` — resolves LTP before first cycle | ✅ |
| Orphan tmp cleanup | `expiry_retry_*.tmp` files removed on startup | ✅ |
| Restore diagnostics | `get_restore_stats()` → startup Telegram ping | ✅ |

**Status: ✅ VERIFIED**

---

## 10. INTRADAY STATE MANAGEMENT

| State Variable | Reset Point | Status |
|---------------|------------|--------|
| `_daily_pnl` | Market open (`_reset_daily_if_new_session()`) | ✅ |
| `_consec_losses` | Win → reset to 0 | ✅ |
| `_trading_halted` | Session reset | ✅ |
| `_open_trades` | `record_open_trade()` / `record_closed_trade()` | ✅ |
| `_dup_guard_stats` | Not reset (cumulative telemetry) | ✅ |
| `_ltp_stale_at` | Per-tick freshness | ✅ |

**Status: ✅ VERIFIED**

---

## 11. TIMING GOVERNANCE

| Rule | Enforcement | Layers |
|------|------------|--------|
| No orders before 09:45 | 3-layer defence: orchestrator → cycle guard → `execute()` | 3 layers |
| Elevated threshold 13:30–14:30 | `_LATE_ENTRY_MIN_SCORE = 7.0` in execute() | 1 layer |
| No new entries after 14:30 | Hard block in `execute()` | 1 layer |
| Exempt from cutoff | Same-symbol position swap (management, not fresh entry) | ✅ |
| EOD learning | 15:35 scheduler slot | ✅ |

**Status: ✅ VERIFIED**

---

## 12. PRODUCTION SAFETY SUMMARY

| Safety Control | Verified | Confidence |
|----------------|---------|-----------|
| Kill Switch (VIX ≥ 45) | ✅ | HIGH |
| Kill Switch (Nifty ≤ -5%) | ✅ | HIGH |
| Maximum Daily Loss (2%) | ✅ | HIGH |
| Maximum Portfolio Risk (5%/8%) | ✅ | HIGH |
| Maximum Exposure (85%) | ✅ | HIGH |
| Maximum Open Positions (8/15) | ✅ | HIGH |
| Duplicate Order Protection | ✅ | HIGH |
| Circuit Breaker (consecutive losses) | ✅ | HIGH |
| Circuit Breaker (broker API) | ✅ | HIGH |
| Market Holiday Handling | ✅ | MEDIUM (conservative approximation) |
| Restart Recovery | ✅ | HIGH |
| Timing Governance (09:45 / 14:30) | ✅ | HIGH |
| SRA Daily-Loss Diagnostic Hard-code | ⚠️ | Observation (non-blocking) |

---

## PRODUCTION SAFETY VERDICT

**Result: PASS WITH ONE OBSERVATION**

**Observation:** `master_orchestrator.py:5145` — hard-coded `-50000` in SRA readiness label. The actual trading halt in `FailSafeRiskGuardian` correctly uses `TOTAL_CAPITAL × 2.0%`. The SRA label may misreport readiness for portfolios under ₹25,000. This is a diagnostic display issue, not a safety failure.

All critical safety mechanisms (kill switch, daily loss halt, position limits, duplicate protection, restart recovery) are verified correct and capital-independent.

*Report completed: 2026-08-06*
