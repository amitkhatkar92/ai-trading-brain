# CAPITAL INDEPENDENCE AUDIT
## LTR-001 — Phase 1

**Date:** 2026-08-06  
**Scope:** All trading modules inspected for fixed capital assumptions  
**Auditor:** LTR-001 Certification Process

---

## 1. AUDIT METHODOLOGY

Every Python source file under the following modules was scanned:
- `config.py` — global configuration
- `execution_engine/order_manager.py` — order routing and sizing
- `risk_control/capital_risk_engine.py` — dynamic capital allocation
- `risk_control/risk_manager_ai.py` — per-trade risk filter
- `risk_guardian/risk_guardian.py` — kill-switch and circuit breakers
- `opportunity_engine/` — signal generation
- `orchestrator/master_orchestrator.py` — full cycle orchestration
- `iios/execution/` — IIOS execution intelligence framework
- `pilot/pilot_controller.py` — pilot capital controller
- `data_feeds/dhan_feed.py` — broker integration

Search patterns used: `10000000`, `1000000`, `500000`, `100000`, `50000`, `10000`, `capital`, `portfolio_value`, `total_capital`, `available_cash`

---

## 2. HARD-CODED MONETARY VALUES — COMPLETE REGISTRY

### 2.1 PRODUCTION CRITICAL

| File | Line | Value | Context | Classification |
|------|------|-------|---------|----------------|
| `orchestrator/master_orchestrator.py` | 5145 | `-50000` | `if _today_pnl < -50000:` in System Readiness Assessment — used to set a `DAILY_LOSS_LIMIT` blocker tag, which influences the pre-market pipeline-readiness score | **PRODUCTION CRITICAL** |

**Detail:** The check `_today_pnl < -50000` is in the `[PipelineReadinessAssessment]` block (Phase 6 of the SRA). It is a diagnostic label, not a kill switch. The actual trading halt is governed by `FailSafeRiskGuardian.MAX_DAILY_LOSS_PCT = 2.0%`. However this hardcoded ₹50,000 threshold means the SRA will incorrectly report no daily-loss blocker for a ₹10,000 portfolio that lost 100% (₹10,000 < ₹50,000). The SRA gate should use `TOTAL_CAPITAL × MAX_DAILY_LOSS_PCT`.

**Risk level:** MEDIUM — SRA readiness gate incorrect for small capital. Trading halt itself (`FailSafeRiskGuardian`) is capital-independent.

---

### 2.2 CONFIGURATION ONLY

| File | Line | Value | Context | Classification |
|------|------|-------|---------|----------------|
| `config.py` | 54 | `10_000_000` | `TOTAL_CAPITAL = float(os.getenv("TOTAL_CAPITAL", 10_000_000))` — default ₹1 Crore. Overridable via `TOTAL_CAPITAL` env var. | CONFIGURATION ONLY |
| `config.py` | 330 | `20_000` | `PILOT_CAPITAL = float(os.getenv("PILOT_CAPITAL", 20_000))` — default ₹20,000 pilot capital. Overridable via env var. | CONFIGURATION ONLY |
| `pilot/pilot_controller.py` | 40 | `20_000` | `PILOT_CAPITAL = float(os.getenv("PILOT_CAPITAL", 20_000))` — reads env var | CONFIGURATION ONLY |
| `iios/execution/positions/risk/constants.py` | 50 | `10000` | `DEFAULT_MAX_LOSS = Decimal("10000")` — default per-position max loss in IIOS execution framework. Used as a fallback when no limit is configured per-position. | CONFIGURATION ONLY |
| `scripts/fix_daily_json.py` | 9 | `1000000.0` | `"pilot_capital": 1000000.0` — one-time data migration script, not trading logic | CONFIGURATION ONLY |
| `vps_governance_proof.py` | 13 | `1000000` | `stub("config", PAPER_TRADING=True, TOTAL_CAPITAL=1000000)` — test stub | CONFIGURATION ONLY |

---

### 2.3 REPORTING / SIMULATION ONLY

| File | Line | Value | Context | Classification |
|------|------|-------|---------|----------------|
| `market_intelligence/market_data_ai.py` | 151 | `10000` | `base = base_prices.get(full_name, 10000)` — simulation fallback base price in ₹ for synthetic OHLCV generation. Not capital. | SIMULATION ONLY |
| `market_intelligence/market_data_ai.py` | 170 | `10000` | `base = sim_base.get(symbol, 10000)` — same simulation fallback | SIMULATION ONLY |
| `execution_engine/order_manager.py` (constants) | — | `15.0`, `85.0` | `MAX_CAPITAL_PER_TRADE_PCT = 15.0` and `MAX_TOTAL_OPEN_EXPOSURE_PCT = 85.0` — expressed as percentages, not INR amounts | CONFIGURATION ONLY |

---

## 3. CAPITAL FLOW VERIFICATION — MODULE BY MODULE

### 3.1 `config.py` — Global Parameters

| Parameter | Value | Type | Capital-Independent? |
|-----------|-------|------|---------------------|
| `TOTAL_CAPITAL` | env var (default 1Cr) | Configurable | ✅ Yes |
| `MAX_RISK_PER_TRADE_PCT` | `0.0025` (0.25%) | Percentage | ✅ Yes |
| `MAX_PORTFOLIO_RISK_PCT` | `0.08` (8%) | Percentage | ✅ Yes |
| `MAX_DRAWDOWN_PCT` | `0.10` (10%) | Percentage | ✅ Yes |
| `MIN_CONFIDENCE_SCORE` | `6.8` | Score | ✅ Yes |
| `ATR_STOP_MULTIPLIER` | `1.5` | Ratio | ✅ Yes |
| `DD_REDUCE_PCT` | `2.0%` | Percentage | ✅ Yes |
| `DD_PAUSE_PCT` | `4.0%` | Percentage | ✅ Yes |
| `MIN_ADV_CRORE` | `50.0` | Market filter | ✅ Yes |
| `MAX_ADV_PCT` | `0.02` (2%) | Ratio | ✅ Yes |
| `ALLOCATION` | dict of fractions | Fractions | ✅ Yes |

**Verdict: FULLY CAPITAL-INDEPENDENT**

---

### 3.2 `risk_control/capital_risk_engine.py` — Position Sizing

The `CapitalRiskEngine.allocate()` method:

```
Step 1: deployable = TOTAL_CAPITAL × regime_fraction × vix_ceiling × drawdown_reducer
Step 2: strategy_budget = deployable × strategy_share_fraction
Step 3: risk_amount = strategy_budget × MAX_RISK_PER_TRADE_PCT
Step 4: quantity = risk_amount / stop_loss_distance
```

| Decision | Formula | Capital-Independent? |
|----------|---------|---------------------|
| Regime deployment fraction | `_EXPOSURE_MAP[regime]` = 0.30–0.80 | ✅ Yes |
| VIX ceiling | `_VIX_CEILINGS` = 0.10–1.00 | ✅ Yes |
| Drawdown reducer | `_DRAWDOWN_REDUCERS` = 0.25–1.00 | ✅ Yes |
| Strategy budget | fraction of deployable | ✅ Yes |
| Position quantity | `risk_amount / SL_distance` | ✅ Yes (quantity changes) |
| Exposure cap | `_MAX_POSITIONS = 8` count limit | ✅ Yes |

**Verdict: FULLY CAPITAL-INDEPENDENT. Only position QUANTITY scales.**

---

### 3.3 `risk_control/risk_manager_ai.py` — Risk Filter

| Check | Formula | Capital-Independent? |
|-------|---------|---------------------|
| Risk per trade | `signal.quantity × price × stop_pct ≤ TOTAL_CAPITAL × MAX_RISK_PER_TRADE_PCT` | ✅ Yes |
| Portfolio heat | `current_heat ≤ MAX_PORTFOLIO_RISK_PCT` | ✅ Yes |
| Drawdown guard | `drawdown ≤ MAX_DRAWDOWN_PCT` | ✅ Yes |
| Minimum R:R | `MIN_RR_RATIO = 2.0` | ✅ Yes |
| Confidence floor | `MIN_CONFIDENCE_SCORE = 6.8` | ✅ Yes |
| Duplicate symbol | symbol presence check | ✅ Yes |
| Liquidity (ADV) | `position_value ≤ ADV × MAX_ADV_PCT` | ✅ Yes |

**Verdict: FULLY CAPITAL-INDEPENDENT**

---

### 3.4 `risk_guardian/risk_guardian.py` — Kill Switch

| Circuit Breaker | Threshold | Capital-Independent? |
|----------------|-----------|---------------------|
| Daily loss halt | `MAX_DAILY_LOSS_PCT = 2.0%` applied to `self._capital` | ✅ Yes |
| Portfolio risk | `MAX_PORTFOLIO_RISK_PCT = 5.0%` | ✅ Yes |
| Max open trades | `MAX_OPEN_TRADES = 8` (count) | ✅ Yes |
| Kill switch (Nifty) | `KILL_SWITCH_NIFTY_DROP = -5.0%` | ✅ Yes |
| Kill switch (VIX) | `KILL_SWITCH_VIX = 45.0` | ✅ Yes |
| Consecutive losses | `CONSEC_LOSS_PAUSE = 3` | ✅ Yes |
| Margin buffer | `MIN_MARGIN_BUFFER_PCT = 20.0%` | ✅ Yes |

`FailSafeRiskGuardian` receives `total_capital` as a constructor argument — correctly parameterised.

**Verdict: FULLY CAPITAL-INDEPENDENT**

---

### 3.5 `execution_engine/order_manager.py` — Order Routing

| Decision | Implementation | Capital-Independent? |
|----------|---------------|---------------------|
| Order creation | `PAPER_TRADING` flag → paper vs live | ✅ Yes |
| Entry price | ATR-zone-adjusted signal price | ✅ Yes |
| Position sizing | From `signal.quantity` (set by CRE) | ✅ Yes |
| Max exposure | `MAX_TOTAL_OPEN_EXPOSURE_PCT = 85.0%` | ✅ Yes |
| Max capital/trade | `MAX_CAPITAL_PER_TRADE_PCT = 15.0%` | ✅ Yes |
| Late entry | time-based (14:30 cutoff) | ✅ Yes |
| Early entry | time-based (09:45 minimum) | ✅ Yes |
| Carry expiry | strategy-type-based day limits | ✅ Yes |
| Position governor | `DD_REDUCE_PCT/PAUSE_PCT` percentages | ✅ Yes |

**Verdict: FULLY CAPITAL-INDEPENDENT**

---

### 3.6 `opportunity_engine/` — Signal Generation

Signal ranking, scoring (PMCI, CDS, PIG, Debate): all scores are probability-weighted confidence metrics. No monetary values involved in ranking. Verified:
- ATR%, momentum scores, sector convergence → all dimensionless ratios
- Conviction score (1–10 scale) → dimensionless
- DecisionEngine score threshold = 6.5/10 → dimensionless

**Verdict: FULLY CAPITAL-INDEPENDENT**

---

### 3.7 `iios/execution/` — IIOS Execution Framework

`DEFAULT_MAX_LOSS = Decimal("10000")` in `constants.py`:
- This is the default `max_loss` field in `PositionRiskLimits`
- It is only a default placeholder; each position's actual limit is configured via `PositionRiskLimits(max_loss=...)` from risk management inputs
- The constant is not consulted in trading decision paths

**Verdict: CONFIGURATION DEFAULT ONLY — no impact on live execution decisions**

---

## 4. PORTFOLIO BEHAVIOUR SIMULATION

### Capital Scenarios

| Capital | Risk/Trade (0.25%) | ATR Stop 20₹ → Qty | ATR Stop 5₹ → Qty |
|---------|-------------------|--------------------|-------------------|
| ₹10,000 | ₹25 | 1 share | 5 shares |
| ₹20,000 | ₹50 | 2 shares | 10 shares |
| ₹1,00,000 | ₹250 | 12 shares | 50 shares |
| ₹1,00,00,000 | ₹25,000 | 1,250 shares | 5,000 shares |

**Observation for ₹10,000:** At 0.25% risk per trade = ₹25. For high-price large-cap stocks (e.g. MARUTI ₹12,000, stop ₹180), quantity = floor(25/180) = 0. These signals will be DROPPED by the sizing engine (qty=0 rejection). Lower-price stocks (TATASTEEL ₹165, stop ₹5) would yield qty=5.

**This is correct capital-independent behaviour.** The strategy, ranking, and conviction remain identical. Only executability changes. No logic modifications needed.

---

## 5. FINAL FINDINGS

### Capital-Independent ✅
- All percentage parameters (risk, exposure, drawdown, allocation)
- All ratio parameters (R:R, ATR multiplier, VIX thresholds)
- All score-based decisions (confidence, PMCI, CDS, debate votes)
- All market-indicator-based circuit breakers (VIX, Nifty drop)
- Position sizing formula: `qty = risk_amount / stop_distance` — scales naturally

### Observations
1. **`master_orchestrator.py:5145`** — Hard-coded `-50000` in SRA diagnostic. SRA readiness label may be incorrect for portfolios < ₹25,000. **Does not affect actual trading halt.** Recommend: replace with `TOTAL_CAPITAL * MAX_DAILY_LOSS_PCT` but this is NOT blocking live trading.

2. **`PILOT_CAPITAL` default ₹20,000** — Configurable via env var. Not embedded in decision logic.

3. **`DEFAULT_MAX_LOSS = 10000` in IIOS constants** — Framework default placeholder. No role in live trade decisions.

### Answer to Audit Questions
1. **Is every trading decision capital-independent?** YES — all decisions use percentages, ratios, or configurable thresholds.
2. **Does only position quantity change with capital?** YES — confirmed by sizing formula analysis.
3. **Can IIOS trade with ₹10,000 without modifying trading logic?** YES — only position quantities will be smaller. Some high-price stocks may yield qty=0 and be dropped, which is correct behaviour.

---

**Audit Result: PASS WITH OBSERVATIONS**  
One diagnostic hard-coded value in SRA (non-blocking). All decision paths capital-independent.

*Audit completed: 2026-08-06*
