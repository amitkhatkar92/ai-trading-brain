# CAPITAL_10000_LIVE_READINESS
### IIOS — ₹10,000 Capital Configuration & Sizing Verification
**Date:** 2026-08-10  
**Auditor:** GitHub Copilot (AI — read-only audit, no orders placed)  
**PAPER_TRADING:** `true` throughout — no live orders possible  
**Scope:** Capital propagation audit, sizing simulation, deployment verification

---

## FINAL RESULT

```
╔══════════════════════════════════════════════╗
║  CAPITAL_10000_NOT_READY                    ║
╚══════════════════════════════════════════════╝
```

**1 safety-critical FAIL.** `FailSafeRiskGuardian` daily-loss kill-switch is
calibrated against a hardcoded `₹10,00,000` capital base instead of `TOTAL_CAPITAL=10000`.
At ₹10,000 actual capital the halt would never fire via daily-loss.
Corrective action is in Section 9. Nothing else is blocking.

---

## SECTION 1 — CAPITAL CONFIGURATION

| Item | Value | Source | Status |
|------|-------|--------|--------|
| Configured capital | ₹10,000 | `.env TOTAL_CAPITAL=10000` | ✅ |
| Config.py default | ₹1,00,00,000 (₹1 Crore) | `config.py line 35` — overridable | ✅ Overridden |
| Local runtime `config.TOTAL_CAPITAL` | ₹10,000 | Verified via `load_dotenv` | ✅ |
| VPS `.env` | `TOTAL_CAPITAL = 10000` | Added via SSH | ✅ |
| Container runtime `config.TOTAL_CAPITAL` | ₹10,000.0 | `docker exec python -c 'import config; print(config.TOTAL_CAPITAL)'` | ✅ |
| PILOT_CAPITAL | ₹1,00,000 | `.env` (informational only) | ⚠️ Not aligned — see Section 9 |
| PAPER_TRADING | `true` | `.env` both local + VPS | ✅ |
| Account available balance | ₹10,514.11 | Dhan `get_fund_limits()` API | ✅ |

---

## SECTION 2 — CAPITAL SOURCE & OVERRIDE GUARANTEE

| Check | Result |
|-------|--------|
| Config.py default ₹1Cr | `float(os.getenv("TOTAL_CAPITAL", 10_000_000))` — env var wins when set |
| Local env var present | `TOTAL_CAPITAL = 10000` in `.env` |
| dotenv `load_dotenv()` call | Present in `config.py` line 10 — loaded before constant evaluation |
| ₹1 Crore default override at runtime | ✅ Confirmed: env var takes precedence over Python default |
| No hardcoded ₹1 Crore in trading path | ✅ All trading modules read from `config.TOTAL_CAPITAL` |

**The ₹1 Crore config.py default cannot override the environment value at runtime.** `os.getenv()` is evaluated at import time. If the env var is present, the default is never used.

---

## SECTION 3 — WHERE TOTAL_CAPITAL IS READ

### 3A — Correctly reads `config.TOTAL_CAPITAL` (scales with environment)

| Module | How it reads TOTAL_CAPITAL | Verified ₹10k? |
|--------|---------------------------|---------------|
| `risk_control/capital_risk_engine.py` | `from config import TOTAL_CAPITAL` — module-level | ✅ `Capital=₹10,000` in startup log |
| `risk_control/portfolio_allocation_ai.py` | `from config import TOTAL_CAPITAL` | ✅ `Capital=₹10,000` in startup log |
| `risk_control/risk_manager_ai.py` | `from config import TOTAL_CAPITAL` | ✅ `Capital=₹10,000` in startup log |
| `execution_engine/order_manager.py` | `Portfolio(capital=TOTAL_CAPITAL)` — correct ₹10k portfolio base | ✅ |
| `risk_control/liquidity_guard.py` | `from config import TOTAL_CAPITAL` | ✅ |
| `risk_control/options_risk_engine.py` | `from config import TOTAL_CAPITAL` | ✅ |
| `live_operations/phase1_health_check.py` | `getattr(config, "TOTAL_CAPITAL", None)` | ✅ |
| `live_operations/phase2_premarket_report.py` | `getattr(_cfg, "TOTAL_CAPITAL", 0)` | ✅ |
| `orchestrator/master_orchestrator.py` | `from config import TOTAL_CAPITAL` (for logging) | ✅ |

### 3B — Hardcoded capital values (do NOT read from config)

| Module | Hardcoded value | Impact | Severity |
|--------|----------------|--------|----------|
| `orchestrator/master_orchestrator.py:250` | `FailSafeRiskGuardian(total_capital=1_000_000)` | **Daily loss kill-switch miscalibrated** | ❌ FAIL |
| `orchestrator/master_orchestrator.py:320` | `PerformanceEvaluator(capital=1_000_000)` | Performance metrics report incorrect % | ⚠️ WARNING |
| `orchestrator/master_orchestrator.py:5145` | `if _today_pnl < -50000:` (SRA diagnostic) | SRA pipeline-readiness label wrong for <₹25k | ⚠️ WARNING |

---

## SECTION 4 — POSITION SIZING FORMULA

### Formula (from `CapitalRiskEngine._size_position()`)

```
deployable       = TOTAL_CAPITAL × regime_fraction × vix_ceiling × dd_reducer
strategy_budget  = deployable × strategy_share_fraction
risk_amount      = strategy_budget × MAX_RISK_PER_TRADE_PCT   (0.25%)
qty_by_risk      = floor(risk_amount / stop_distance)
qty_by_budget    = floor(strategy_budget / entry_price)
quantity         = min(qty_by_risk, qty_by_budget)
```

### At ₹10,000 capital — RANGE_MARKET regime

| Parameter | Formula | Value |
|-----------|---------|-------|
| `TOTAL_CAPITAL` | env var | ₹10,000 |
| `MAX_RISK_PER_TRADE_PCT` | config.py percentage | 0.25% (unchanged) |
| Deployable (RANGE 50%) | ₹10,000 × 0.50 | ₹5,000 |
| Strategy budget (Mean_Rev 22%) | ₹5,000 × 0.22 | ₹1,100 |
| **Risk per trade** | **₹1,100 × 0.0025** | **₹2.75** |
| Max per-trade cap (15%) | ₹10,000 × 15% | ₹1,500 |
| Max total exposure (85%) | ₹10,000 × 85% | ₹8,500 |
| Daily loss kill (2%) | ₹1,000,000 × 2%* | ₹20,000* ← WRONG (see Section 9) |
| CRE drawdown reduce (2%) | Portfolio.capital × 2% | ₹200 ← CORRECT |

### Comparison at different capital levels (formula unchanged)

| Capital | Deployable (BULL) | Budget (Mean_Rev) | Risk/trade | Signal NBCC@₹100 SL₹1 |
|---------|------------------|-------------------|------------|----------------------|
| ₹10,000 | ₹8,000 | ₹1,760 | ₹4.40 | qty=4 (₹400 notional) |
| ₹1,00,000 | ₹80,000 | ₹17,600 | ₹44.00 | qty=44 (₹4,400 notional) |
| ₹10,00,000 | ₹8,00,000 | ₹1,76,000 | ₹440.00 | qty=440 (₹44,000 notional) |

**Logic, percentages, and thresholds are identical across all rows. Only quantity changes.**

---

## SECTION 5 — PERCENTAGE/RATIO VERIFICATION

| Parameter | Value | Type | Changed? |
|-----------|-------|------|---------|
| `MAX_RISK_PER_TRADE_PCT` | 0.25% | Percentage | ✅ No |
| `MAX_PORTFOLIO_RISK_PCT` | 8% | Percentage | ✅ No |
| `MAX_DRAWDOWN_PCT` | 10% | Percentage | ✅ No |
| `MIN_CONFIDENCE_SCORE` | 6.8 | Score (dimensionless) | ✅ No |
| `ATR_STOP_MULTIPLIER` | 1.5× | Ratio | ✅ No |
| `DD_REDUCE_PCT` | 2% | Percentage | ✅ No |
| `DD_PAUSE_PCT` | 4% | Percentage | ✅ No |
| `MIN_ADV_CRORE` | ₹50 Cr | Market filter | ✅ No |
| `MAX_ADV_PCT` | 2% | Ratio | ✅ No |
| `MAX_CAPITAL_PER_TRADE_PCT` | 15% | Percentage (order_manager) | ✅ No |
| `MAX_TOTAL_OPEN_EXPOSURE_PCT` | 85% | Percentage (order_manager) | ✅ No |
| `KILL_SWITCH_VIX` | 45.0 | Level (dimensionless) | ✅ No |
| `KILL_SWITCH_NIFTY_DROP` | -5% | Percentage | ✅ No |
| BUY/SHORT signal logic | Score-based (CDS, PMCI, Debate) | Dimensionless | ✅ No |
| Portfolio replacement/swap | Conviction score delta | Dimensionless | ✅ No |
| `ALLOCATION` | large_cap 40%, mid 30%, small 15%, options 15% | Fractions | ✅ No |

**Zero risk rules, thresholds, or strategies were modified.**

---

## SECTION 6 — SIZING SIMULATION (READ-ONLY, NO ORDERS)

_RANGE_MARKET regime, BULL_TREND regime shown. PAPER_TRADING=true. No orders submitted._

### Capital budget chain at ₹10,000

| Regime | Strategy | Deployable | Budget | Risk/trade |
|--------|----------|------------|--------|------------|
| BULL_TREND | Mean_Reversion | ₹8,000 | ₹1,760 | ₹4.40 |
| BULL_TREND | Breakout_Volume | ₹8,000 | ₹2,240 | ₹5.60 |
| RANGE_MARKET | Mean_Reversion | ₹5,000 | ₹1,100 | ₹2.75 |
| RANGE_MARKET | Breakout_Volume | ₹5,000 | ₹1,400 | ₹3.50 |
| BEAR_MARKET | Mean_Reversion | ₹3,000 | ₹660 | ₹1.65 |

### Scenario 1 — Capital sufficient for one position

| Stock | Entry | Stop | ATR stop | Qty | Notional | Capital% | Status |
|-------|-------|------|----------|-----|----------|---------|--------|
| IEX | ₹185 | ₹183 | ₹2 | **2** | ₹370 | 3.7% | ✅ OK |
| NBCC | ₹100 | ₹99 | ₹1 | **4** | ₹400 | 4.0% | ✅ OK |

### Scenario 2 — Capital insufficient (high-price stocks → qty=0, signal DROPPED)

| Stock | Entry | Stop | Risk budget | qty_by_risk | Result |
|-------|-------|------|-------------|-------------|--------|
| MARUTI | ₹12,500 | ₹12,320 | ₹2.75 | 0 (2.75÷180=0) | ❌ QTY_ZERO — dropped |
| HDFCBANK | ₹1,900 | ₹1,880 | ₹2.75 | 0 (2.75÷20=0) | ❌ QTY_ZERO — dropped |
| TATASTEEL | ₹165 | ₹160 | ₹2.75 | 0 (2.75÷5=0) | ❌ QTY_ZERO — dropped |

Signals dropped because `risk_amount < stop_distance`. **This is correct capital-independent behaviour.** Strategy ranking and conviction scores are not affected. The signal is evaluated and ranked — only execution is impossible.

**Practical implication for ₹10,000 pilot:** Only stocks priced below ~₹500 with ATR-based stops smaller than ₹3–5 will produce non-zero quantities. The ADV filter (`MIN_ADV_CRORE = 50`) will pre-screen universe candidates.

### Scenario 3 — Maximum exposure (85% = ₹8,500)

Max open exposure cap = ₹8,500. With 4 positions (NBCC×4=₹400, IRFC×3=₹225, SAIL×4=₹360, IEX×2=₹370) total = ₹1,355 (13.6%). Each additional position at ~₹400 would be blocked at position 22 (₹8,800 > ₹8,500). Percentage-based. ✅

### Scenario 4 — Multiple candidates

| Symbol | Entry | Budget | Risk | Qty | Notional | Cap% | Status |
|--------|-------|--------|------|-----|----------|------|--------|
| NBCC | ₹100 | ₹1,760 | ₹4.40 | 4 | ₹400 | 4.0% | ✅ OK |
| IRFC | ₹75 | ₹1,440 | ₹3.60 | 3 | ₹225 | 2.2% | ✅ OK |
| SAIL | ₹90 | ₹1,760 | ₹4.40 | 4 | ₹360 | 3.6% | ✅ OK |
| IEX | ₹185 | ₹1,760 | ₹4.40 | 2 | ₹370 | 3.7% | ✅ OK |
| **Total** | | | | | **₹1,355** | **13.6%** | |

Ranking by conviction score is unchanged. Only quantity reflects ₹10,000 capital.

### Scenario 5 — Weak position replacement / swap

Replacement decision uses conviction score delta (7.2 vs 6.8) — dimensionless and capital-independent. If swap approved, freed capital re-enters at ₹10,000 sizing. Swap logic is NOT changed. ✅

### Scenario 6 — BUY and SHORT coexist

| Direction | Stock | Qty | Notional | Capital% |
|-----------|-------|-----|----------|---------|
| LONG | NBCC ₹100 | 4 | ₹400 | 4.0% |
| SHORT | IRFC ₹75 | 3 | ₹225 | 2.2% |
| Combined | | | ₹625 | 6.2% |

Combined heat 6.2% < portfolio limit 8%. BUY+SHORT coexistence permitted.
**Note:** SHORT positions require SHORT DNA records. Current `institutional_dna.db` has 0 SHORT lifecycle records — the SHORT DNA gate in the execution layer will block all short-side signals until SHORT DNA is populated.

---

## SECTION 7 — LOCAL → GIT → VPS → CONTAINER CONSISTENCY

| Layer | TOTAL_CAPITAL | PAPER_TRADING | Commit | Status |
|-------|--------------|--------------|--------|--------|
| Local `.env` | ₹10,000 | `true` | — | ✅ |
| Git repository | (gitignored — correct) | — | `65db00a` | ✅ |
| VPS `.env` | ₹10,000 | `true` | `64dc0ff` | ✅ |
| Container (runtime) | ₹10,000.0 | `True` | `64dc0ff` | ✅ |

Container restart performed. Container health: `Up (healthy)`.

Startup logs confirmed at 10:44:36:
- `[RiskManagerAI] Initialised. Capital=₹10,000` ✅
- `[PortfolioAllocationAI] Initialised. Capital=₹10,000` ✅
- `[RiskGuardian] Initialised. Capital=₹1000000` ← hardcoded (see Section 9)

---

## SECTION 8 — HARDCODED CAPITAL FINDINGS

### Complete registry of non-configurable monetary values in trading path

| Location | Value | Role | Live impact at ₹10k |
|----------|-------|------|---------------------|
| `orchestrator/master_orchestrator.py:250` | `1_000_000` | `FailSafeRiskGuardian(total_capital=...)` | ❌ **CRITICAL: daily loss kill-switch miscalibrated** |
| `orchestrator/master_orchestrator.py:320` | `1_000_000` | `PerformanceEvaluator(capital=...)` | ⚠️ Performance % reporting inaccurate |
| `orchestrator/master_orchestrator.py:5145` | `-50000` | SRA `_today_pnl < -50000` diagnostic | ⚠️ SRA label never fires at ₹10k |
| `execution_engine/order_manager.py:181` | `15.0` | `MAX_CAPITAL_PER_TRADE_PCT = 15.0%` | ✅ Percentage — capital-independent |
| `execution_engine/order_manager.py:182` | `85.0` | `MAX_TOTAL_OPEN_EXPOSURE_PCT = 85.0%` | ✅ Percentage — capital-independent |
| `risk_guardian/risk_guardian.py:81` | `1_000_000` | Constructor default only | ✅ Default only — overridden by caller |
| `ops02_sizing_calibration.py` | `10_000_000` | Standalone calibration script, not in live path | ✅ Offline only |
| `calibrate.py`, `readiness_suite.py`, `system_validation.py` | `1_000_000` | Test/calibration tools, not in scheduler path | ✅ Offline only |
| `vps_governance_proof.py` | `1_000_000` | Test stub | ✅ Test only |
| `iios/execution/positions/risk/constants.py` | `DEFAULT_MAX_LOSS = 10000` | Per-position limit placeholder — overridden at runtime by risk management inputs | ✅ Framework default, not trading decision |

### Conclusion on ₹1 Crore override risk

The ₹1 Crore config.py default **cannot** override the `TOTAL_CAPITAL=10000` env var at runtime.
`os.getenv()` is evaluated before the default is used — confirmed by container runtime output.

---

## SECTION 9 — SAFETY FINDING: RISKGUARDIAN MISCALIBRATION

### Finding

`FailSafeRiskGuardian` is instantiated at:
```python
# orchestrator/master_orchestrator.py:250
self.risk_guardian = FailSafeRiskGuardian(total_capital=1_000_000)
```

The daily loss halt calculation inside `FailSafeRiskGuardian`:
```python
daily_loss_pct = abs(min(0.0, self._daily_pnl)) / self._capital * 100
if daily_loss_pct >= MAX_DAILY_LOSS_PCT:   # 2.0%
    self._trading_halted = True
```

With `self._capital = 1_000_000`, a 2% halt fires at **₹20,000 daily loss**.

### Impact at ₹10,000 capital

| Mechanism | Correct threshold | Actual threshold | Gap |
|-----------|------------------|-----------------|-----|
| Daily loss halt | 2% × ₹10,000 = **₹200** | 2% × ₹10,00,000 = **₹20,000** | Guardian never fires |
| Position governor reduce | 2% × ₹10,000 = **₹200** | 2% × ₹10,00,000 = **₹20,000** | Never reduces |
| Position governor pause | 4% × ₹10,000 = **₹400** | 4% × ₹10,00,000 = **₹40,000** | Never pauses |

Since the account has ₹10,514.11 total balance, a daily loss of ₹20,000+ is impossible —
meaning the `FailSafeRiskGuardian` daily-loss circuit breaker **would never activate** for this account.

### What still protects at ₹10,000

| Protection | Status |
|-----------|--------|
| VIX ≥ 45 kill-switch | ✅ Capital-independent — still works |
| Max open trades (8) | ✅ Count-based — still works |
| Max portfolio risk (8%) | ✅ Uses `Portfolio.drawdown_pct` (₹10k base) — still works |
| CRE drawdown reducer | ✅ Uses `portfolio.drawdown_pct` (₹10k base) — correctly reduces at ₹200 loss |
| Max capital/trade (15%) | ✅ Applied against `Portfolio.capital` = ₹10k |
| Max total exposure (85%) | ✅ Applied against `Portfolio.capital` = ₹10k |
| Confidence threshold (6.8) | ✅ Dimensionless — still works |
| Edge gate (DECAYING blocked) | ✅ Still works |
| Signal freshness gate | ✅ Still works |

### Corrective Action Required

**Do not fix this yourself. Request explicit instruction.**  
The single-line fix required (no risk-rule change, only capital parameterisation):

```python
# orchestrator/master_orchestrator.py:250 — change:
self.risk_guardian = FailSafeRiskGuardian(total_capital=1_000_000)
# to:
self.risk_guardian = FailSafeRiskGuardian(total_capital=TOTAL_CAPITAL)
# (TOTAL_CAPITAL already imported on line 34)
```

This does **not** change any risk percentage or rule. It only ensures the daily-loss
calculation uses the configured capital base instead of a hardcoded placeholder.
Same change applies to `PerformanceEvaluator(capital=1_000_000)` → `capital=TOTAL_CAPITAL`.
The SRA `-50000` diagnostic is lower priority (doesn't affect trading, only logging).

---

## READINESS GATE

| Requirement | Status |
|------------|--------|
| `TOTAL_CAPITAL = 10000` in local .env | ✅ |
| `TOTAL_CAPITAL = 10000` in VPS .env | ✅ |
| Container runtime `config.TOTAL_CAPITAL = 10000.0` | ✅ |
| No ₹1 Crore override at runtime | ✅ |
| All risk rules percentage-based, unchanged | ✅ |
| Sizing simulation: quantity reduces correctly | ✅ |
| High-price stocks correctly produce qty=0 | ✅ |
| Exposure cap (85%) scales to ₹8,500 | ✅ |
| Kill switch (VIX≥45) functional | ✅ |
| `FailSafeRiskGuardian` daily-loss calibrated to ₹10k | ❌ FAIL |
| `PerformanceEvaluator` capital calibrated to ₹10k | ⚠️ WARNING |
| `PAPER_TRADING = true` (unchanged) | ✅ |

---

## FINAL RESULT

```
CAPITAL_10000_NOT_READY

Reason: FailSafeRiskGuardian daily-loss kill-switch is calibrated
against hardcoded ₹10,00,000 instead of TOTAL_CAPITAL=10,000.
The halt would never fire at ₹10,000 account capital.

Required fix: 1 line in orchestrator/master_orchestrator.py.
All other capital configuration is correct and verified.
```

_Report generated: 2026-08-10 | Read-only audit — zero orders placed, zero rules changed._
