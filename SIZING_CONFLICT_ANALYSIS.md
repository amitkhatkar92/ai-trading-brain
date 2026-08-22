# SIZING_CONFLICT_ANALYSIS.md
## Forensic Audit — Risk Sizer vs. Capital Guard Incompatibility
**Date of Investigation:** June 16, 2026  
**Verdict:** Structural mathematical incompatibility. Risk sizer always produces notional ≈ 50% of capital. Guard 5 caps at 15%. Block rate is 100% under standard conditions.

---

## 1. The Two Constraints

### Constraint 1 — Risk-Based Position Sizer

Implemented in `capital_risk_engine/portfolio_allocation_ai.py` (and downstream `StrategyLab` sizing).

```python
risk_budget   = capital × MAX_RISK_PER_TRADE_PCT      # ₹ at risk per trade
stop_distance = entry_price × stop_loss_gap_pct        # ₹ distance to stop
quantity      = risk_budget / stop_distance            # shares to buy
notional      = quantity × entry_price
             = (risk_budget / stop_distance) × entry_price
             = risk_budget / stop_loss_gap_pct         # price cancels
```

**Key insight:** `entry_price` cancels out. The notional is independent of the stock price.

$$\text{notional} = \frac{\text{capital} \times \text{risk\_pct}}{\text{sl\_gap\_pct}}$$

With system parameters:
- `MAX_RISK_PER_TRADE_PCT = 0.01` (1%)
- Typical SL gap: **2%** (observed from paper_trades.csv data)

$$\text{notional} = \frac{\text{capital} \times 0.01}{0.02} = \text{capital} \times 0.50$$

The sizer will always target **50% of total capital** per trade, regardless of which stock is selected.

### Constraint 2 — Capital Per Trade Guard (Guard 5)

Implemented in `execution_engine/order_manager.py`, lines 599–625.

```python
MAX_CAPITAL_PER_TRADE_PCT = 15.0   # module-level constant, line 174

notional_capital     = qty * signal.entry_price
trade_utilization_pct = (notional_capital / self._portfolio.capital) * 100.0
if trade_utilization_pct > MAX_CAPITAL_PER_TRADE_PCT:
    return None   # BLOCKED
```

Guard 5 blocks any trade whose notional exceeds **15% of portfolio capital**.

---

## 2. Mathematical Proof of Incompatibility

For Guard 5 to pass, the following must hold:

$$\frac{\text{notional}}{\text{capital}} \leq 15\%$$

Substituting the sizer formula:

$$\frac{\text{capital} \times \text{risk\_pct}}{\text{sl\_gap\_pct} \times \text{capital}} \leq 0.15$$

$$\frac{\text{risk\_pct}}{\text{sl\_gap\_pct}} \leq 0.15$$

With current parameters:

$$\frac{0.01}{0.02} = 0.50 \quad \not\leq \quad 0.15$$

**The inequality fails by a factor of 3.33×.** This is a permanent structural conflict, not a data or configuration error.

### What it would take to pass Guard 5

| Change | Required value | Current value | Change factor |
|---|---|---|---|
| Reduce `MAX_RISK_PER_TRADE_PCT` | ≤ 0.30% | 1.00% | ÷ 3.33 |
| Widen average SL gap | ≥ 6.67% | ~2.00% | × 3.33 |
| Raise `MAX_CAPITAL_PER_TRADE_PCT` | ≥ 50% | 15.00% | × 3.33 |
| Any combination satisfying `risk_pct / sl_gap ≤ 0.15` | — | — | — |

All three options represent fundamental policy decisions, not minor tuning.

---

## 3. Empirical Evidence from paper_trades.csv

The CSV contains 234 rows (119 OPEN, 112 CLOSE). Every recorded OPEN was placed. This means these trades were either:

(a) Placed **before Guard 5 existed** (earlier orchestrator version)  
(b) Placed via a **code path that bypasses Guard 5**  
(c) Placed under a **different `MAX_CAPITAL_PER_TRADE_PCT`** setting

### Group A — March 19 Backtest/Emergency-Close trades

All 119 OPEN records from March 19 closed within 1 second of opening (reason: `emergency_close`). These are **backtesting replay runs** that wrote to the CSV directly, not live execution through `execute()`. Guard 5 was not in the path.

Example: MARUTI BUY qty=7 @ ₹16,649 = ₹116,543 notional
- ₹116,543 / ₹800,000 = 14.6% → just below 15% guard
- But this was via a different code path than the current `execute()` guard

### Group B — March 20 Hedging_Model (pre-guard code version)

6 OPEN positions on 2026-03-20 07:35, strategy=`Hedging_Model`, confidence=10.0.

| Symbol | Qty | Entry | Notional | % of ₹800K |
|---|---|---|---|---|
| RELIANCE | 44 | ₹2,838.61 | ₹124,899 | 15.6% — **exceeds guard** |
| HDFCBANK | 74 | ₹1,676.25 | ₹124,042 | 15.5% — **exceeds guard** |
| ICICIBANK | 136 | ₹915.38 | ₹124,492 | 15.6% — **exceeds guard** |
| INFY | 72 | ₹1,722.35 | ₹124,009 | 15.5% — **exceeds guard** |
| LT | 33 | ₹3,673.42 | ₹121,223 | 15.2% — **exceeds guard** |
| COALINDIA | 191 | ₹490.06 | ₹93,601 | 11.7% — passes |

5 of 6 notionals exceed 15%. These positions were placed before Guard 5 was added to the codebase. The addition of Guard 5 was a direct response to the March 13 "90 position explosion" event.

### Group C — April 10–17 large positions (post-capital-raise)

Positions placed after capital was raised to ₹10,000,000:

| Date | Symbol | Qty | Entry | Notional | % of ₹10M |
|---|---|---|---|---|---|
| Apr 10 | ICICIBANK | 166 | ₹1,281.30 | ₹212,696 | 2.1% — passes |
| Apr 10 | ICICIBANK | 178 | ₹1,318.60 | ₹234,711 | 2.3% — passes |
| Apr 13 | RELIANCE | 74 | ₹2,870.79 | ₹212,438 | 2.1% — passes |
| Apr 13 | HDFCBANK | 126 | ₹1,680.93 | ₹211,797 | 2.1% — passes |
| Apr 15 | RELIANCE | 690 | ₹2,871.28 | ₹1,981,183 | 19.8% — **exceeds guard** |
| Apr 15 | ICICIBANK | 1,480 | ₹1,341.00 | ₹1,984,680 | 19.8% — **exceeds guard** |
| Apr 16 | RELIANCE | 824 | ₹2,861.67 | ₹2,358,016 | 23.6% — **exceeds guard** |
| Apr 17 | ITC | 4,861 | ₹308.55 | ₹1,499,862 | 15.0% — exactly at threshold |

April 10–13 positions (₹211K–₹234K) pass Guard 5 on ₹10M capital (2.1–2.3%).  
April 15–16 Momentum_Retest positions (₹2M–₹2.4M) exceed 15% — these cannot have passed Guard 5 on ₹10M capital. Either:
- Capital was ≥ ₹15.7M at that time, OR
- Guard 5 was not applied (e.g., these positions entered through a REPLACEMENT path in `_smart_swap_check()` which re-uses the slot of an evicted position — the replacement trade falls through after the swap and proceeds to `_place_entry_with_retry()` without re-checking Guard 5? This warrants separate investigation.)

April 17 ITC at exactly 15.0% of ₹10M suggests that the ITC sizing was computed to land precisely at the threshold (rounding to ≤15%).

---

## 4. Block Rate for Standard Risk-Sized Trades

Under current parameters (`risk_pct=1%`, `sl_gap≈2%`, `MAX_CAPITAL_PER_TRADE_PCT=15%`):

| Capital level | Notional produced | 15% limit | Blocked? |
|---|---|---|---|
| ₹800,000 | ₹400,000 (50%) | ₹120,000 | ✅ 100% blocked |
| ₹10,000,000 | ₹5,000,000 (50%) | ₹1,500,000 | ✅ 100% blocked |
| ₹100,000,000 | ₹50,000,000 (50%) | ₹15,000,000 | ✅ 100% blocked |

**Theoretical block rate: 100%.** No amount of capital increase resolves the conflict because the sizer scales notional proportionally with capital.

### Confirmed empirical block events

| Date | Approved signals | Blocked by Guard 5 | Executed |
|---|---|---|---|
| 2026-03-18 | 18 (6/cycle × 3 cycles) | 18 | 0 |

March 17 and March 19–20 show `trades_executed=0` in the same pattern, consistent with the same block.

---

## 5. Observed Trades That Did Execute

Three categories of trades in `paper_trades.csv` bypassed or predate Guard 5:

| Category | Period | Path | Guard 5 status |
|---|---|---|---|
| Backtest replay (emergency_close) | Mar 19 | Not through `execute()` | Not applicable |
| Hedging_Model opens | Mar 20 | Pre-Guard-5 code version | Guard absent at time |
| Mean_Reversion / Momentum_Retest | Apr 10–17 | ₹10M capital, smaller trades first | Passes for ≤15%; exceeds for ≥19.8% |

The April 10–13 Mean_Reversion trades (notional ≈ ₹212K = 2.1% of ₹10M) are the **only positions that passed Guard 5 under current code logic**. These had confidence scores ≥ 9.5 and strategies that produce conservative sizing relative to their entry prices (smaller `risk_pct / sl_gap` ratio due to wider SL gaps).

---

## 6. Guard 5 vs. Guard 6 (Total Exposure) Interaction

Guard 6 (`MAX_TOTAL_OPEN_EXPOSURE_PCT = 85%`) caps total portfolio exposure. Guard 5 caps per-trade notional. Under the standard risk-sizer:

- A single risk-sized trade would consume 50% of capital.
- Guard 5 blocks it at 15%.
- Therefore Guard 6 is never reached via standard sizing — Guard 5 fires first.
- Guard 6 only becomes relevant if Guard 5 is somehow bypassed or if sizing produces small notionals (< 15%).

---

## 7. Context: Why Guard 5 Was Added

`EXECUTION_PATH_REPORT.md` documents the March 13 "position explosion" event: 90 positions placed in a ~24-minute window by the old orchestrator, totalling enormous exposure. Guard 5 was added as a defensive measure after that event. Its 15% threshold was calibrated to prevent single-trade concentration, but was set without verifying mathematical compatibility with the 1%/2% risk sizer.

---

## 8. Compatibility Matrix

$$\boxed{\text{Incompatible. } \frac{1\%}{2\%} = 50\% \gg 15\%}$$

| Component | Parameter | Value |
|---|---|---|
| Sizer | `MAX_RISK_PER_TRADE_PCT` | 1.0% |
| Sizer | Typical SL gap | 2.0% |
| Sizer | Implied notional / capital | **50%** |
| Guard 5 | `MAX_CAPITAL_PER_TRADE_PCT` | **15%** |
| Guard 5 | `execute()` location | `order_manager.py` line 599 |
| Compatibility | — | **No** |
| Block rate (standard sizing) | — | **100%** |

---

*End of SIZING_CONFLICT_ANALYSIS.md — observation only, no parameter changes applied*
