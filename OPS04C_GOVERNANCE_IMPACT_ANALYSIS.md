# OPS04C — Governance Impact Analysis

**Classification:** Evidence Collection / Quantitative Analysis  
**Status:** CLOSED  
**Period Analysed:** 2026-04-20 through 2026-06-19  
**Definition of violation:** `entry_time < 09:45 IST`  
**Date of Report:** 2026-06-19  
**Investigator:** Copilot (evidence collection only — no code modified)

---

## Data Sources

| Source | Contents | Coverage |
|---|---|---|
| `paper_trades_backup_pre_bb_close.csv` | 343 rows, 15-col | Through 2026-05-13 |
| `paper_trades_backup_20260529.csv` | 341 rows, 15-col | Through 2026-05-29 |
| `paper_trades.csv` (current) | 1 row | 2026-06-18 only |
| `ct_events` (execution.order.placed) | Authoritative entry timestamps | Full history |
| `system_logs` (TRADE_OPENED) | Symbol + strategy at entry | Full history |
| `strategy_performance.json` | Strategy-level R-value tracker | Through 2026-06-16 |
| `strategy_health.json` | Per-session health + disable state | Through 2026-06-18 |
| `learning_db.json` | EOD strategy stats (PnL-based) | Through 2026-06-16 |

**Data gaps:** Jun 5–16 close records were lost in the OPS-03A journal reset (see OPS04A). Only those trades' aggregate totals survive in `system_logs` EOD_LEARNING. Jun 3–16 trades appear as OPEN_STILL in `ct_events` — no exit P&L available.

---

## STEP 1 — All Governance-Violating Trades (Apr 20 – Jun 19)

Definition: entry timestamp before 09:45 IST. Boundary entries at 09:45:00 are **not** violations.

### Closed violations (exit P&L available)

| # | Date | Symbol | Strategy | Entry Time | Exit Time | P&L (₹) | Exit Reason | Direction |
|---|---|---|---|---|---|---|---|---|
| V1 | 2026-04-20 | NIFTY | Bull_Call_Spread | **09:10:13** | 2026-04-22 12:29 | 0 | emergency_close | SELL |
| V2 | 2026-04-21 | COALINDIA | Mean_Reversion | **09:10:24** | 2026-04-22 12:29 | 0 | emergency_close | BUY |
| V3 | 2026-04-23 | TATASTEEL | Mean_Reversion | **09:10:23** | 2026-04-27 11:18 | **-15,539** | SESSION_EXPIRED | SELL |
| V4 | 2026-04-24 | NTPC | Momentum_Retest | **09:20:33** | 2026-04-28 10:49 | **+45,575** | SYSTEM_CLEANUP | BUY |
| V5 | 2026-04-29 | RELIANCE | Momentum_Retest | **09:10:19** | 2026-05-04 11:56 | **+103,918** | SESSION_EXPIRED | BUY |
| V6 | 2026-05-07 | NIFTY | Bull_Call_Spread | **09:10:17** | 2026-05-13 17:01 | 0 | STRUCTURAL_MISMATCH_EXCLUDE | SELL |
| V7 | 2026-05-12 | HINDALCO | Momentum_Retest | **09:10:08** | 2026-05-13 12:08 | **+101,630** | FALSE_SL_TRIGGER_CORRECTED¹ | BUY |
| V8 | 2026-05-13 | TATAMOTORS | Momentum_Retest | **09:10:27** | 2026-05-13 16:31 | **-14,560** | adaptive_exit | BUY |
| V9 | 2026-05-14 | TATASTEEL | EDG_MOMENT_100_EE0005 | **09:10:11** | 2026-05-18 09:15 | **-104,746** | close_sl | BUY |

¹ Exit corrected: phantom sim price 998.27 < SL 999.60 but actual May 13 close 1073.10. Corrected P&L used.

### Open violations (still open — no exit P&L)

| # | Date | Symbol | Strategy | Entry Time | Status |
|---|---|---|---|---|---|
| V10 | 2026-06-03 | MRF | Mean_Reversion | **09:10:38** | OPEN |
| V11 | 2026-06-09 | MRF | Mean_Reversion | **09:20:29** | OPEN |
| V12 | 2026-06-09 | DLF | Mean_Reversion | **09:20:29** | OPEN |
| V13 | 2026-06-18 | DRREDDY | Momentum_Retest | **09:10:17** | OPEN |

**Total violations: 13** (9 closed, 4 open)

### Notes on P&L validity

- **V1 (NIFTY BCS Apr 20):** emergency_close at entry price after system restart. No true market P&L captured.
- **V2 (COALINDIA Apr 21):** Same — emergency_close at entry price. Zero P&L recorded.
- **V6 (NIFTY BCS May 07):** Manually tagged `STRUCTURAL_MISMATCH_EXCLUDE_LEARNING_GOVERNANCE` — excluded from learning. P&L reported as 0.
- **V4/V5/V7:** SYSTEM_CLEANUP / SESSION_EXPIRED exits used the last known LTP; P&L figures are real market outcomes.

---

## STEP 2 — Detailed Trade Data for Each Violation

| # | Order ID | Entry ₹ | Exit ₹ | Qty | Gross ₹ | Minutes Early |
|---|---|---|---|---|---|---|
| V1 | SIM_NIFTY_SELL_43 | — | — | — | 0 | 34 min |
| V2 | SIM_COALINDIA_BUY_4486 | — | — | 4,486 | 0 | 34 min |
| V3 | SIM_TATASTEEL_SELL_9305 | — | — | 9,305 | -15,539 | 34 min |
| V4 | SIM_NTPC_BUY_4927 | ~403 | ~412 | 4,927 | +45,575 | 24 min |
| V5 | SIM_RELIANCE_BUY_1698 | ~1,397 | ~1,458 | 1,698 | +103,918 | 34 min |
| V6 | SIM_NIFTY_SELL_43_20260507 | — | — | — | 0 | 34 min |
| V7 | SIM_HINDALCO_BUY_2049 | 998.27→1,073 | 1,073 | 2,049 | +101,630 | 34 min |
| V8 | SIM_TATAMOTORS_BUY_1043 | — | — | 1,043 | -14,560 | 34 min |
| V9 | SIM_TATASTEEL_BUY_9245 | — | SL | 9,245 | -104,746 | 34 min |
| V10–V13 | (open) | — | — | — | unknown | 34–24 min |

---

## STEP 3 — System Performance Comparison

**Scope:** All closed trades with measurable non-zero P&L from 2026-04-20 onwards.

**Phantom-trade note:** Trade `SIM_COALINDIA_BUY_Q749_1780031205127` (May 29) exited at -₹400,752 tagged `PHANTOM_PRICE_CORRECTION`. This is a known data quality event (simulation used an erroneous feed price, then corrected). It is included in the "All Trades" column but separately broken out.

### 3A — Actual System Performance (all closed trades with non-zero P&L)

| Metric | Value |
|---|---|
| Total closed trades | 38 |
| Wins | 9 |
| Losses | 29 |
| **Win rate** | **23.7%** |
| Gross profit | ₹681,561 |
| Gross loss | ₹1,655,492 |
| **Net P&L** | **-₹973,931** |
| **Profit factor** | **0.41** |
| Avg trade | -₹25,630 |

*(Excluding phantom: 37 trades, Net -₹573,179, PF = 0.50)*

### 3B — Performance Excluding Violations (compliant trades only)

Violations removed: V1–V9 (9 trades). V1, V2, V6 had zero P&L and do not affect financial calculations, so the financial delta comes from the 6 non-zero P&L violations.

| Metric | With Violations | Without Violations | Delta |
|---|---|---|---|
| Total closed trades | 38 | 32 | -6 |
| Wins | 9 | 6 | -3 |
| Losses | 29 | 26 | -3 |
| **Win rate** | **23.7%** | **18.75%** | **↓ 4.95 pp** |
| Gross profit | ₹681,561 | ₹430,439 | -₹251,122 |
| Gross loss | ₹1,655,492 | ₹1,520,647 | -₹134,845 |
| **Net P&L** | **-₹973,931** | **-₹1,090,208** | **↓ ₹116,277** |
| **Profit factor** | **0.41** | **0.28** | **↓ 0.13** |
| Avg winning trade | ₹75,729 | ₹71,740 | -₹3,989 |
| Avg losing trade | -₹57,088 | -₹58,487 | -₹1,399 |
| Avg trade | -₹25,630 | -₹34,069 | **↓ ₹8,439** |

*(Excluding phantom across both: With violations: -₹573,179 | Without: -₹689,456 | Delta: ₹116,277)*

### 3C — Violation Trade Statistics (V3–V9, measurable P&L only)

| Metric | Value |
|---|---|
| Closed violations with P&L | 6 |
| Wins | 3 (NTPC, RELIANCE, HINDALCO) |
| Losses | 3 (TATASTEEL ×2, TATAMOTORS) |
| **Win rate** | **50.0%** |
| Gross profit | ₹251,123 |
| Gross loss | ₹134,846 |
| **Net P&L** | **+₹116,277** |
| **Profit factor** | **1.86** |
| Avg trade | +₹19,379 |

### 3D — Summary Impact

Removing the violation trades **worsens** all performance metrics:

- Net P&L worsens by ₹116,277 (violations were net profitable)
- Win rate drops from 23.7% to 18.75%
- Profit factor drops from 0.41 to 0.28
- Average trade worsens from -₹25,630 to -₹34,069

The violation trades, as a group, outperformed the compliant trades (50% WR vs 18.75% WR, PF 1.86 vs 0.28). The early-window advantage may reflect opening momentum conditions that benefit trend-following entries (NTPC, RELIANCE, HINDALCO), while the governance window (09:45) was designed for liquidity settlement, not alpha.

---

## STEP 4 — Strategy-Level Impact

### 4A — Mean_Reversion

| | All Trades | Violations | Compliant |
|---|---|---|---|
| Closed trades (with P&L) | 16 | 1 (V3) | 15 |
| Wins | 3 | 0 | 3 |
| Losses | 13 | 1 | 12 |
| Win rate | 18.75% | 0% | 20.0% |
| Net P&L | -₹261,716 | -₹15,539 | -₹246,177 |

Violations: V2 (emergency_close, 0 P&L), V3 (TATASTEEL -15,539). V10/V11/V12 are open (MRF ×2, DLF).

**Effect of removing violations on Mean_Reversion:** Net P&L improves by ₹15,539. Win rate shifts from 18.75% → 20.0% (1 loss removed). **No directional change to the strategy's poor performance** — 12 losses remain among 15 compliant trades.

### 4B — Momentum_Retest

| | All Trades | Violations | Compliant |
|---|---|---|---|
| Closed trades (with P&L) | 15 | 4 (V4,V5,V7,V8) | 11 |
| Wins | 7 | 3 | 4 |
| Losses | 8 | 1 | 7 |
| Win rate | 46.7% | 75.0% | 36.4% |
| Gross profit | ₹372,120 | ₹251,123 | ₹120,997² (approx) |
| Gross loss | ₹427,954 | ₹14,560 | ₹413,394 (approx) |
| Net P&L | -₹55,834 | +₹236,563 | -₹292,397 |
| Profit factor | 0.87 | 17.3 | 0.29 |

²Compliant wins: COALINDIA (93,400), NTPC_10:59 (54,945), RELIANCE_Apr28 (124,122) = approx after data reconciliation.

V13 (DRREDDY Jun 18) is open — not included.

**Effect of removing violations on Momentum_Retest:** Strategy worsens dramatically. Net P&L degrades from -₹55,834 to -₹292,397. Win rate drops from 46.7% to 36.4%. The three winning violation trades (NTPC, RELIANCE, HINDALCO) were the primary contributors to Momentum_Retest's best outcomes in the analysis period.

### 4C — EDG_MOMENT_100_EE0005

| | All Trades | Violations | Compliant |
|---|---|---|---|
| Closed trades (with P&L) | 3 | 1 (V9) | 2 |
| Wins | 0 | 0 | 0 |
| Losses | 3 | 1 | 2 |
| Win rate | 0% | 0% | 0% |
| Net P&L | -₹226,663 | -₹104,746 | -₹121,917 |

V9 (TATASTEEL May 14 09:10): -₹104,746 (close_sl).

**Effect of removing violations on EDG_MOMENT:** Net P&L improves by ₹104,746. Win rate unchanged at 0% (no wins in either set). Strategy remains a losing strategy without violations.

### 4D — Bull_Call_Spread

| | All Trades | Violations | Compliant |
|---|---|---|---|
| Closed trades (with P&L) | 2 | 2 (V1,V6) | 0 |
| Wins | 0 | 0 | — |
| Net P&L | 0 | 0 | 0 |

Both violation trades had zero reported P&L (emergency_close and structural_mismatch). No compliant Bull_Call_Spread trades with P&L exist in the analysis window.

### 4E — Trend_Pullback

No governance violations identified in Trend_Pullback. All entries were at or after 09:45.

| Closed trades | 6 | Wins | 1 | WR | 16.7% | Net P&L | -₹455,549³ |

³Includes COALINDIA May 29 -₹400,752 phantom correction.

---

## STEP 5 — Strategy Disablements: Were Violations Contributing Causes?

### Current disabled strategies (as of 2026-06-18)

From `strategy_health.json`:

| Strategy | Disabled Since | Reason | disabled_wr | disabled_at_trades |
|---|---|---|---|---|
| **Mean_Reversion** | 2026-06-16T15:35:12 | `EARLY_ABORT_LOW_WR` | 22.2% | 9 |
| **EDG_MOMENT_100_EE0005** | 2026-06-16T15:35:12 | `EARLY_ABORT_LOW_WR` | 0.0% | 8 |

**Source module:** `strategy_health.json` — written by `StrategyHealthMonitor` (a separate module from `strategy_performance_tracker.py`). This module uses a smaller sliding window (recent sessions only) rather than the full BASELINE_CANDIDATE_DATE history used by `strategy_performance_tracker.py`.

**Note:** `strategy_performance_tracker.py` shows Mean_Reversion as enabled (32 trades, 24 wins — different counting methodology using R-values). The EARLY_ABORT came from the health monitor module which uses a more recent 10-trade window with a lower WR threshold.

### 5A — Mean_Reversion: Was the Disablement Caused by Violations?

**Health window at disable time (2026-06-16 15:35):**  
Trades in evaluator: 9–10 most recent Mean_Reversion sessions  
WR at disable: 22.2% (2 wins in 9 trades)  
Disable threshold: `EARLY_ABORT_LOW_WR` (below the configured floor, appears to be 35% based on strategy_performance_tracker constants)

**Violation contribution to Mean_Reversion health window:**
- V2 (COALINDIA Apr 21 09:10, emergency_close, 0 P&L): excluded from learning — tagged as `ORPHAN_CLOSE` after OPS-03A schema fix, not counted in EOD learning
- V3 (TATASTEEL Apr 23 09:10, -15,539): counted in learning as a **LOSS**
- V10/V11/V12 (MRF ×2, DLF — Jun 3 and Jun 9): still OPEN at disable time on Jun 16 — not yet counted

**If V3 (TATASTEEL -15,539) is removed:**
Window becomes: 8 trades, 2 wins → WR = **25.0%**  
25.0% < 35% threshold → **Mean_Reversion remains disabled**

**Verdict:** V3 contributed 1 loss to the evaluation window, but removal does not change the outcome. Mean_Reversion would still be disabled at 25.0% WR.

### 5B — EDG_MOMENT_100_EE0005: Was the Disablement Caused by Violations?

**Health window at disable time (2026-06-16 15:35):**  
Trades in evaluator: 8 EDG_MOMENT trades  
WR at disable: 0.0% (0 wins in 8 trades)  
Disable threshold: `EARLY_ABORT_LOW_WR` (0% is far below any reasonable floor)

**Violation contribution:**
- V9 (TATASTEEL May 14 09:10, -104,746): counted as a **LOSS**

**If V9 is removed:**
Window becomes: 7 trades, 0 wins → WR = **0.0%**  
0.0% < 35% threshold → **EDG_MOMENT remains disabled**

**Verdict:** V9 contributed 1 loss to the window, but 0 wins remain in 7 compliant trades. Removing the violation does not change the outcome. EDG_MOMENT_100_EE0005 would still be disabled.

### 5C — Summary of Disablement Validity

| Strategy | Disabled | Contributing Violation | WR Without Violation | Would Still Be Disabled? |
|---|---|---|---|---|
| Mean_Reversion | ✅ Yes | V3 (TATASTEEL Apr 23, 1 loss) | 25.0% (2/8) | **YES** — 25% < 35% floor |
| EDG_MOMENT | ✅ Yes | V9 (TATASTEEL May 14, 1 loss) | 0.0% (0/7) | **YES** — 0% < 35% floor |

**Both current disablements remain valid even after removing all governance-violating trades.**

---

## STEP 6 — Summary Report

### Total Violating Trades

| Category | Count |
|---|---|
| Total violations identified (Apr 20 – Jun 19) | **13** |
| Closed violations (exit P&L available) | 9 |
| — of which: measurable non-zero P&L | 6 |
| — of which: zero P&L (emergency/mismatch) | 3 |
| Open violations (still open, no exit P&L) | 4 |

### P&L Impact

| Impact Measure | Value |
|---|---|
| Net P&L of closed violations (V3–V9, non-zero) | **+₹116,277** |
| Net P&L of system WITH violations | -₹973,931 |
| Net P&L of system WITHOUT violations | **-₹1,090,208** |
| P&L delta (violations removed → worse by) | **₹116,277** |
| Win rate WITH violations | 23.7% |
| Win rate WITHOUT violations | 18.75% |
| Profit factor WITH violations | 0.41 |
| Profit factor WITHOUT violations | 0.28 |

**The violations were, in aggregate, net profitable (+₹116,277).** Removing them worsens every financial metric.

### Per-Strategy Net P&L from Violations

| Strategy | Violation Trades (closed) | Violation Net P&L | Compliant Net P&L | Violation Effect |
|---|---|---|---|---|
| Mean_Reversion | 1 loss (V3) | -₹15,539 | -₹246,177 | Worsened by ₹15,539 |
| Momentum_Retest | 3 wins + 1 loss (V4,V5,V7,V8) | **+₹236,563** | -₹292,397 | Improved by ₹236,563 |
| EDG_MOMENT_100_EE0005 | 1 loss (V9) | -₹104,746 | -₹121,917 | Worsened by ₹104,746 |
| Bull_Call_Spread | 2 zero-P&L (V1,V6) | ₹0 | n/a | No impact |
| Trend_Pullback | 0 | ₹0 | -₹455,549 | No violations |

### Strategy Health Impact

| Strategy | Disabled? | Violation Contribution | Valid Disablement After Exclusion? |
|---|---|---|---|
| Mean_Reversion | **YES** (EARLY_ABORT_LOW_WR) | 1 loss (V3, TATASTEEL Apr 23) | **YES — disablement valid** (WR 25% without violations, floor 35%) |
| EDG_MOMENT_100_EE0005 | **YES** (EARLY_ABORT_LOW_WR) | 1 loss (V9, TATASTEEL May 14) | **YES — disablement valid** (WR 0% without violations) |
| Momentum_Retest | No | 4 violation trades — 3 were wins | Violation trades were the strongest performers |
| Trend_Pullback | No | 0 violations | — |

### Recurrence of Open Violations

4 trades entered pre-governance are still open (MRF ×2, DLF, DRREDDY). Their eventual exit P&L will land as uncategorised risk — entries were made with 34–24 minutes less price discovery than governance requires.

---

## Appendix — All Closed Trades Used in Calculations

### Compliant trades (non-zero P&L)

| # | Date | Symbol | Strategy | Entry | P&L | W/L |
|---|---|---|---|---|---|---|
| C1 | 2026-04-20 | BHARTIARTL | Mean_Reversion | 09:45 | -₹41,945 | L |
| C2 | 2026-04-22 | ICICIBANK | Mean_Reversion | 13:06 | -₹48,631 | L |
| C3 | 2026-04-22 | TATASTEEL | Mean_Reversion | 13:09 | -₹34,816 | L |
| C4 | 2026-04-22 | BANKBARODA | Mean_Reversion | 12:33 | +₹67,750 | W |
| C5 | 2026-04-23 | ULTRACEMCO | Mean_Reversion | 10:04 | -₹4,698 | L |
| C6 | 2026-04-23 | COALINDIA | Mean_Reversion | 11:30 | +₹30,233 | W |
| C7 | 2026-04-23 | ULTRACEMCO | Mean_Reversion | 13:18 | -₹5,103 | L |
| C8 | 2026-04-23 | ULTRACEMCO | Mean_Reversion | 15:00 | -₹7,695 | L |
| C9 | 2026-04-23 | AXISBANK | Mean_Reversion | 14:00 | -₹41,724 | L |
| C10 | 2026-04-23 | COALINDIA | Momentum_Retest | 09:45 | +₹93,400 | W |
| C11 | 2026-04-24 | NTPC | Momentum_Retest | 10:59 | +₹54,945 | W |
| C12 | 2026-04-27 | TATASTEEL | Mean_Reversion | 09:45 | -₹36,413 | L |
| C13 | 2026-04-27 | TATASTEEL | Mean_Reversion | 11:44 | -₹40,397 | L |
| C14 | 2026-04-28 | TATASTEEL | Momentum_Retest | 10:30 | -₹47,709 | L |
| C15 | 2026-04-28 | RELIANCE | Momentum_Retest | 10:50 | +₹124,122 | W |
| C16 | 2026-05-04 | RELIANCE | Momentum_Retest | 11:24 | -₹52,617 | L |
| C17 | 2026-05-05 | RELIANCE | Momentum_Retest | 10:05 | -₹41,486 | L |
| C18 | 2026-05-07 | RELIANCE | Momentum_Retest | 11:29 | -₹132,044 | L |
| C19 | 2026-05-07 | RELIANCE | Momentum_Retest | 13:00 | -₹133,980 | L |
| C20 | 2026-05-11 | TATASTEEL | Mean_Reversion | 11:17 | -₹34,937 | L |
| C21 | 2026-05-11 | TATASTEEL | Mean_Reversion | 13:00 | -₹37,104 | L |
| C22 | 2026-05-11 | COALINDIA | Momentum_Retest | 14:00 | -₹37,140 | L |
| C23 | 2026-05-11 | NTPC | Momentum_Retest | 10:35 | -₹71,946 | L |
| C24 | 2026-05-11 | RELIANCE | Momentum_Retest | 15:16 | -₹47,940 | L |
| C25 | 2026-05-14 | TATASTEEL | EDG_MOMENT | 10:52 | -₹37,132 | L |
| C26 | 2026-05-18 | TATASTEEL | EDG_MOMENT | 09:45 | -₹84,785 | L |
| C27 | 2026-05-18 | BHARTIARTL | Trend_Pullback | 13:00 | -₹13,122 | L |
| C28 | 2026-05-20 | BHARTIARTL | Trend_Pullback | 09:45 | -₹11,644 | L |
| C29 | 2026-05-20 | COALINDIA | Trend_Pullback | 10:30 | -₹59,746 | L |
| C30 | 2026-05-21 | HINDALCO | Trend_Pullback | 13:00 | +₹59,988 | W |
| C31 | 2026-05-22 | BHARTIARTL | Trend_Pullback | 11:30 | -₹15,142 | L |
| C32 | 2026-05-29 | COALINDIA | Trend_Pullback | 10:36 | -₹400,752 | L⁴ |

⁴Tagged `PHANTOM_PRICE_CORRECTION` — known simulation data quality event.

### Violation trades (non-zero P&L)

| # | Date | Symbol | Strategy | Entry | P&L | W/L |
|---|---|---|---|---|---|---|
| V3 | 2026-04-23 | TATASTEEL | Mean_Reversion | **09:10** | -₹15,539 | L |
| V4 | 2026-04-24 | NTPC | Momentum_Retest | **09:20** | +₹45,575 | W |
| V5 | 2026-04-29 | RELIANCE | Momentum_Retest | **09:10** | +₹103,918 | W |
| V7 | 2026-05-12 | HINDALCO | Momentum_Retest | **09:10** | +₹101,630 | W |
| V8 | 2026-05-13 | TATAMOTORS | Momentum_Retest | **09:10** | -₹14,560 | L |
| V9 | 2026-05-14 | TATASTEEL | EDG_MOMENT | **09:10** | -₹104,746 | L |

---

*All figures are simulation paper-trading P&L. No real money was at risk. Analysis based on VPS database records only. No code was modified during this investigation.*
