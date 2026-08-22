# TRADE_LIFECYCLE_AUDIT.md
## Forensic Audit — Historical Paper Trade Lifecycle Outcomes
**Date of Investigation:** June 16, 2026  
**Sources:** `data/paper_trades.csv` (234 rows), `data/trading_brain.db` (28 rows)  
**Verdict:** No trade has ever completed a natural lifecycle. All PnL data in production stores is zero or synthetic. The learning engine has no valid outcome data.

---

## 1. Data Sources and Scope

### `data/paper_trades.csv`

The primary production journal. 234 rows spanning 2026-03-19 to 2026-04-17.

| Event | Count |
|---|---|
| OPEN | 119 |
| CLOSE | 112 |
| REENTRY_OPEN | 2 |
| CANCELLED | 1 |

The 7 unmatched OPENs (no corresponding CLOSE) represent positions that are currently open or were never formally closed.

### `data/trading_brain.db` (trades table)

28 rows from 2026-03-11, `mode='test'`. Not a production journal. See Section 7.

---

## 2. Exit Type Classification

For all CLOSE events in `paper_trades.csv`, the `close_reason` field is stored in an overflow column (the `None` key in `csv.DictReader`). The complete distribution:

| Close Reason | Count | Exit Price = Entry Price? | Realized PnL |
|---|---|---|---|
| `emergency_close` | 108 | Yes (100%) | ₹0.00 |
| `SYSTEM_CLEANUP` | 4 | Yes (100%) | ₹0.00 |
| (1 CANCEL event, no close) | 1 | N/A | N/A |
| `SL_HIT` | **0** | — | — |
| `TARGET_HIT` | **0** | — | — |
| `CARRY_EXPIRED` | **0** | — | — |
| `REPLACEMENT` | **0** | — | — |
| **Total closes** | **112** | — | **₹0.00** |

**No trade has ever exited via SL_HIT, TARGET_HIT, CARRY_EXPIRED, or REPLACEMENT.**

---

## 3. Period-by-Period Breakdown

### Period 1: March 19 (108 open/close pairs — "Backtest Replay Burst")

**Date range:** 2026-03-19 11:55 to 2026-03-19 12:47  
**Event count:** 108 OPEN + 108 CLOSE  
**Time-to-close:** 0–2 seconds  
**Strategies:** `EDG_MOMENT_86_EE0002`, `EDG_MOMENT_86_EE0003`, `EDG_MOMENT_100_EE0003`, `Trend_Pullback`  
**Close reason:** `emergency_close`  

**Symbols traded:**

| Symbol | OPEN count | Notional range |
|---|---|---|
| MARUTI | 12 | ₹116,095 – ₹116,543 |
| TITAN | 8 | ₹121,948 |
| ULTRACEMCO | 12 | ₹117,369 – ₹117,990 |
| M&M | 8 | ₹120,790 – ₹122,404 |
| GRASIM | 12 | ₹122,503 – ₹123,622 |
| BRITANNIA | 8 | ₹120,380 – ₹124,278 |

The identical entry/exit prices, sub-second close times, and `emergency_close` reason confirm these are **backtesting or strategy replay runs**, not real-time paper trading. The journal captures the open and immediately closes it (position never held). This data contaminates the production journal with 108 zero-PnL trades.

### Period 2: March 20 (6 opens — "Hedging_Model Burst")

**Date range:** 2026-03-20 07:35  
**Event:** 6 OPEN, 0 CLOSE within this date  
**Strategy:** `Hedging_Model`, confidence=10.0  
**Closed:** 2026-04-15 12:11 via `SYSTEM_CLEANUP`  
**Holding period:** ~26 calendar days / ~18 trading days  

| Symbol | Qty | Entry | Notional | Exit | PnL |
|---|---|---|---|---|---|
| RELIANCE | 44 | ₹2,838.61 | ₹124,899 | ₹2,838.61 | ₹0 |
| HDFCBANK | 74 | ₹1,676.25 | ₹124,042 | ₹1,676.25 | ₹0 |
| ICICIBANK | 136 | ₹915.38 | ₹124,492 | ₹915.38 | ₹0 |
| INFY | 72 | ₹1,722.35 | ₹124,009 | ₹1,722.35 | ₹0 |
| LT | 33 | ₹3,673.42 | ₹121,223 | ₹3,673.42 | ₹0 |
| COALINDIA | 191 | ₹490.06 | ₹93,601 | ₹490.06 | ₹0 |

These positions were held for 26 days with no SL checks. `SYSTEM_CLEANUP` closed them at entry price. Unrealized PnL (positive or negative) that accrued over 18 trading days was never captured.

### Period 3: April 10–15 (Mean_Reversion entries)

**Opened:** 2026-04-10 09:10 to 2026-04-13 14:00  
**Closed:** 2026-04-15 12:11  
**Strategy:** `Mean_Reversion`, confidence 9.0–9.9  

| Order ID | Symbol | Qty | Entry | Open Date | Close Date | Holding | PnL |
|---|---|---|---|---|---|---|---|
| SIM_ICICIBANK_BUY_166 | ICICIBANK | 166 | ₹1,281.30 | Apr 10 09:10 | Apr 15 12:11 | ~5 days | ₹0 |
| SIM_ICICIBANK_BUY_178 (×3) | ICICIBANK | 178 | ₹1,317–₹1,319 | Apr 10 12:08–12:23 | Apr 15 12:11 | ~5 days | ₹0 |
| SIM_RELIANCE_BUY_74 | RELIANCE | 74 | ₹2,870.79 | Apr 13 09:10 | Apr 15 12:11 | ~2 days | ₹0 |
| SIM_HDFCBANK_BUY_126 | HDFCBANK | 126 | ₹1,680.93 | Apr 13 13:00 | Apr 15 12:11 | ~2 days | ₹0 |
| SIM_ICICIBANK_BUY_157 | ICICIBANK | 157 | ₹1,350.00 | Apr 13 14:00 | Apr 15 08:00 | ~1 day | ₹0 |

Additionally, ICICIBANK was `CANCELLED` on Apr 10 10:30 and then reopened as `REENTRY_OPEN` (×2) — indicating the limit order was not filled and was resubmitted. The REENTRY_OPEN entries were eventually closed with the rest.

Note: Multiple ICICIBANK BUY positions opened on Apr 10 at slightly different prices with different quantities. Three `SIM_ICICIBANK_BUY_178` positions were opened at almost identical times (12:08, 12:12, 12:21) — suggesting the system re-submitted the same signal multiple times in rapid succession, resulting in 3 concurrent positions for the same symbol.

All positions closed by `SYSTEM_CLEANUP` at entry price. PnL = ₹0.

### Period 4: April 15–16 (Momentum_Retest churn)

**Pattern:** Large Momentum_Retest positions (₹1.9M–₹2.4M notional) cycling rapidly through OPEN → REPLACEMENT → CLOSE within 1–20 minutes on the same symbols (RELIANCE and ICICIBANK).

| Timestamp | Symbol | Qty | Entry | Notional | Event |
|---|---|---|---|---|---|
| Apr 15 11:48 | RELIANCE | 690 | ₹2,871.28 | ₹1,981,183 | OPEN |
| Apr 15 11:48 | ICICIBANK | 1,480 | ₹1,341.00 | ₹1,984,680 | OPEN |
| Apr 16 10:21 | RELIANCE | 690 | ₹2,871.28 | ₹1,981,183 | CLOSE |
| Apr 16 10:21 | ICICIBANK | 1,480 | ₹1,341.00 | ₹1,984,680 | CLOSE |
| Apr 16 10:24 | RELIANCE | 824 | ₹2,861.67 | ₹2,358,016 | OPEN |
| Apr 16 10:30 | ICICIBANK | 1,734 | ₹1,360.60 | ₹2,359,280 | OPEN |
| Apr 16 12:44 | RELIANCE | 833 | ₹2,830.04 | ₹2,357,423 | OPEN |
| Apr 16 12:44 | ICICIBANK | 1,748 | ₹1,349.80 | ₹2,359,450 | OPEN |
| Apr 16 13:02 | RELIANCE | 824 | ₹2,861.67 | — | CLOSE |
| Apr 16 13:02 | RELIANCE | 828 | ₹2,847.09 | ₹2,357,391 | OPEN |
| Apr 16 13:02 | ICICIBANK | 1,734 | ₹1,360.60 | — | CLOSE |
| Apr 16 13:02 | ICICIBANK | 1,753 | ₹1,345.50 | ₹2,358,662 | OPEN |
| Apr 16 13:06 | RELIANCE | 833 | ₹2,830.04 | — | CLOSE |
| Apr 16 13:06 | RELIANCE | 823 | ₹2,866.27 | ₹2,358,940 | OPEN |
| Apr 16 13:06 | ICICIBANK | 1,748 | ₹1,349.80 | — | CLOSE |
| Apr 16 13:06 | ICICIBANK | 1,753 | ₹1,345.50 | ₹2,358,662 | OPEN |
| Apr 16 13:23 | RELIANCE | 828 | ₹2,847.09 | — | CLOSE |
| Apr 16 13:23 | RELIANCE | 826 | ₹2,851.88 | ₹2,355,653 | OPEN |

This 30-minute churning pattern on April 16 represents the `SmartSwap` replacement mechanism cycling through same-symbol replacements (higher score evicts lower score). All closes show `exit_price = entry_price`, PnL = 0. The RELIANCE and ICICIBANK positions at the end of April 16 and the ICICIBANK/RELIANCE positions from April 17 10:45 close all reflect zero PnL.

### Period 5: April 17 — ITC (Final Open Position)

- **Opened:** 2026-04-17 10:30:23 and again at 2026-04-17 13:00:20  
- **Closed:** Never  
- **Holding period as of June 16 2026:** ~43 calendar days / ~30 trading days  
- **Unrealized PnL:** Unknown (no LTP polling since April 17)  
- **Current status:** Orphaned open in `paper_trades.csv`

---

## 4. Full Lifecycle Completion Check

A "full lifecycle" requires:
1. OPEN event with valid entry
2. Price moves to either SL or TARGET
3. Monitor loop detects breach
4. CLOSE event with `exit_price ≠ entry_price`
5. Non-zero PnL captured

| Lifecycle stage | Evidence found? |
|---|---|
| Stage 1 — OPEN | ✅ 119 records |
| Stage 2 — Price moves | Unknown (no LTP polling confirmed) |
| Stage 3 — Monitor detects breach | ❌ Never — monitor loop was not running during any hold period |
| Stage 4 — CLOSE with different exit price | ❌ **Zero instances** |
| Stage 5 — Non-zero PnL | ❌ **Zero instances** |

**Conclusion: The system has never completed a full trade lifecycle.**

---

## 5. Root Cause of Zero Lifecycle Completions

### Cause 1: Backtest artifacts in production journal

108 of 112 close events (96.4%) are `emergency_close` records from a strategy replay burst on March 19. These were not generated by the live monitor loop — they were written by a strategy evolution/backtesting code path that opened and immediately closed positions. The production journal was treated as a scratchpad for strategy evaluation.

### Cause 2: Monitor loop not running

The carry-expiry check (`check_and_expire_stale_limits()`) and SL monitoring are only triggered within the orchestrator's `_do_monitor()` slot. This slot runs when the scheduler is active. The scheduler was not continuously active:

| Period | ct_cycle activity | Monitor running? |
|---|---|---|
| 2026-03-11 | Active (132 cycles) | Likely yes (old orchestrator) |
| 2026-03-12 | Active (3,036 cycles) | Yes — high frequency |
| 2026-03-13 | Active (2,090 cycles) | Yes |
| 2026-03-16 | Active (46 cycles) | Yes |
| 2026-03-17 to 2026-03-19 | 4–13 cycles/day | Intermittent |
| 2026-03-20 | 2 cycles | Barely |
| 2026-04-02 | 2 cycles | Barely |
| 2026-04-03 to 2026-04-17 | **0 cycles** | **No** |
| 2026-04-17 to 2026-06-16 | **0 cycles** | **No** |

The Hedging_Model positions (March 20) and Mean_Reversion positions (April 10–13) held for multiple days with no cycles running. Even if price had hit SL or target, no process was polling to detect it.

### Cause 3: SYSTEM_CLEANUP at entry price

The 4 SYSTEM_CLEANUP closes (and the 6 Hedging_Model closes) used `exit_price = entry_price` (confirmed by None-key column in CLOSE rows). This was a deliberate design choice in `close_position()` for cleanup scenarios where LTP is unavailable. The result is accurate PnL = 0, but it also means the actual unrealized gain or loss during the hold period was discarded.

---

## 6. Impact on Learning Engine

The `LearningSystem` (`learning_system/strategy_performance_tracker.py` and `LearningEngine`) infers strategy quality from trade outcomes:

- Win rate
- Average R-multiple
- Sharpe ratio
- Maximum drawdown

**Available outcome data:**

| Source | Outcome type | Count | Quality |
|---|---|---|---|
| March 19 emergency_close | All zero PnL | 108 | **Invalid — not real holds** |
| Hedging_Model SYSTEM_CLEANUP | All zero PnL | 6 | **Invalid — real hold, wrong exit price** |
| Mean_Reversion SYSTEM_CLEANUP | All zero PnL | 6 | **Invalid — real hold, wrong exit price** |
| Momentum_Retest SYSTEM_CLEANUP | All zero PnL | 6 | **Invalid — real hold, wrong exit price** |
| SL_HIT | None | 0 | **Absent** |
| TARGET_HIT | None | 0 | **Absent** |

The learning engine has **zero valid outcome records**. Any win-rate, R-multiple, or Sharpe calculations performed on this data will return 0% win rate and ₹0 average PnL. If the learning engine suppresses or avoids strategies with 0% win rate, it will eventually disable every strategy that has been used — without any signal that this is happening due to data absence rather than strategy failure.

---

## 7. trading_brain.db Context

The 7 closed INFY trades in `trading_brain.db` show `pnl=530.64` each (7 × ₹530.64 = ₹3,714.48 total):

```
entry=1801.8, exit=1868.13, qty=8
pnl = 8 × (1868.13 - 1801.8) = 8 × 66.33 = 530.64
```

The `ts_open` and `ts_close` for all 7 are within milliseconds of each other (same second). This confirms synthetic test execution — the old orchestrator's test harness ran a fixed scenario 7 times. These figures are **not real paper trade outcomes** and must not be used as learning data.

---

## 8. Summary Table

| Question | Answer |
|---|---|
| Has the system ever completed a full lifecycle (SL or target hit)? | **No** |
| Is any realized PnL meaningful? | **No** — all ₹0 or synthetic test data |
| Does the learning engine have valid outcome data? | **No** |
| How many trades held > 1 day? | ~18 (Hedging_Model ~18 days; Mean_Reversion ~2–5 days) |
| Were those held trades monitored? | **No** — cycles stopped while positions were open |
| What % of all CLOSE events are emergency_close? | **96.4%** (108/112) |
| Is paper_trades.csv a clean production journal? | **No** — contaminated by backtest replay events |

---

*End of TRADE_LIFECYCLE_AUDIT.md — observation only, no code modifications applied*
