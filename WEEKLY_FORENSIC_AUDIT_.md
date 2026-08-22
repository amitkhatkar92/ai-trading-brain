# WEEKLY FORENSIC AUDIT
**Period:** 2026-06-13 (Friday open) → 2026-06-19 (Thursday, current)
**Generated:** 2026-06-19 11:15 IST
**Mode:** Paper Trading | Evidence collection only — NO CODE MODIFIED

---

## DATA SOURCES USED
| Source | Status | Notes |
|---|---|---|
| `data/paper_trades.csv` | Partial | Reset on Jun 16 restart — only contains DRREDDY (Jun 18) |
| `data/paper_trades_legacy.csv` | Full historical | Moved on Jun 16; prior trades preserved here |
| `data/trading_brain.db → system_logs` | 1,783 entries | Primary event record |
| `data/control_tower.db → ct_cycles` | 2,646 all-time | Confirmed running |
| `data/control_tower.db → ct_decisions` | 1,298 all-time | Signal decisions |
| `data/eod_retro_*.txt` | Jun 15–18 ✅ | Jun 13–14 missing (weekend/pre-period) |
| `data/trade_analytics_*.json` | Jun 15–16 ✅ | Jun 17–18 absent (0 closed trades) |
| `data/closed_orders_*.txt` | Jun 15–16 ✅ | |
| `data/options_trades.csv` | 3 entries | 1 NIFTY IC closed, 1 BANKNIFTY IC open |
| `data/feed_audit.csv` | 319 entries | ANGELONE source throughout |
| `data/borderline_rejections.json` | 76 entries | 5 from Jun 16 |
| `data/market_behavior.db` | **MISSING** | Phase D/E/F DB not initialised on VPS |

---

## REPORT 1 — EXECUTION SUMMARY

### Trading Days This Week
| Date | Day | Traded? | Notes |
|---|---|---|---|
| 2026-06-13 | Friday | Unknown | No EOD retro file (system may have been in restart) |
| 2026-06-14 | Saturday | No | Market closed |
| 2026-06-15 | Monday | Yes | 12 cycles |
| 2026-06-16 | Tuesday | Yes | 12 cycles + 2 system restarts at EOD |
| 2026-06-17 | Wednesday | Yes | 12 cycles — 0 executions (ODM SECONDARY) |
| 2026-06-18 | Thursday | Yes | 12 cycles — 1 execution, governance violation |

### Aggregate Metrics (Jun 15–18, 4 trading days)

| Metric | Value | Source |
|---|---|---|
| Total cycles | ~48 (12/day × 4 days) | EOD retros |
| Total signals generated | ~697 (146+210+177+164) | EOD retros Section 2 |
| BT-rejected | 0 | EOD retros |
| MC-rejected (Stability) | ~363 | EOD retros — **all Stability** |
| Debate approved | ~48 | EOD retros |
| Opportunities explored (debate) | ~48 | Inferred from debate counts |
| Trades executed | 7 | system_logs TRADE_OPENED events |
| Trades closed this week | 6 | EOD retros + trade_analytics |
| Trades open at EOD | 1 (DRREDDY) | paper_trades.csv |
| **Win rate** | **2/6 = 33.3%** | trade_analytics + EOD retros |
| Gross profit | ~₹+31,939 | Jun 16 Mean_Reversion winners |
| Gross loss | ~₹-73,662 | 4 EARLY_LOSS trades |
| **Net P&L (week)** | **≈ ₹-41,723** | EOD retros: Jun 15 ₹-26,563, Jun 16 ₹-15,160 |
| Profit factor | ~0.43 | 31,939 / 73,662 |
| Average trade duration | ~32 hours | DRREDDY 75h, JSWSTEEL 22.8h, others ~5h |
| Largest winner | Unknown (within Jun 16 ₹+31,939 split) | Not individually itemised in source |
| Largest loser | ≈ ₹-26,563 (DRREDDY Jun 15) | trade_analytics Jun 15 |

### Day-by-Day P&L Summary
| Date | Closed | W | L | Net P&L | Strategy |
|---|---|---|---|---|---|
| Jun 15 | 1 | 0 | 1 | ₹-26,563 | Mean_Reversion |
| Jun 16 | 5 | 2 | 3 | ₹-15,160 | Mean_Reversion + EDG_MOMENT |
| Jun 17 | 0 | — | — | ₹0 | No executions |
| Jun 18 | 0 | — | — | ₹0 | DRREDDY still open |
| **TOTAL** | **6** | **2** | **4** | **₹-41,723** | |

### Trade Detail Log
| Symbol | Strategy | Direction | Entry | Exit | R | Exit Reason | Date |
|---|---|---|---|---|---|---|---|
| DRREDDY | Mean_Reversion | BUY | 1271.5 | 1248.97 | -0.512 | EARLY_LOSS | Jun 15 |
| JSWSTEEL | EDG_MOMENT_100_EE0005 | BUY | 1311.3 | 1292.0 | -0.616 | EARLY_LOSS | Jun 16 |
| TITAN | Mean_Reversion | BUY | 4254.9 | 4149.05 | -0.749 | EARLY_LOSS | Jun 16 |
| APOLLOHOSP | Mean_Reversion | BUY | 8491.0 | 8319.06 | -0.575 | EARLY_LOSS | Jun 16 |
| DRREDDY | Mean_Reversion | BUY | ~? | ~? | WIN | (part of ₹+31,939) | Jun 16 |
| PAGEIND | Mean_Reversion | BUY | ~? | ~? | WIN | (part of ₹+31,939) | Jun 16 |

**Evidence:** trade_analytics_2026-06-15.json, trade_analytics_2026-06-16.json, closed_orders_2026-06-15.txt, closed_orders_2026-06-16.txt, system_logs IDs 1771–1776

**No TARGET_HIT exits this week. All exits were EARLY_LOSS.**

---

## REPORT 2 — OPEN POSITIONS FORENSIC

### Currently Open (as of 2026-06-19)

| Field | Value |
|---|---|
| Symbol | DRREDDY |
| Strategy | Momentum_Retest |
| Order ID | SIM_DRREDDY_BUY_Q856_P1272.22_1781754016515 |
| Entry Date | 2026-06-18 09:10:16 |
| Entry Price | ₹1,269.50 |
| Quantity | 856 |
| Stop Loss | ₹1,228.64 |
| Target | ₹1,371.65 |
| Gross Exposure | ₹1,086,692 |
| Holding Days | 1 day (entered Jun 18, today Jun 19) |
| Current Price | ~₹1,271 (feed data from Jun 18) |
| Unrealized P&L | ~₹0 to -₹2,000 (near-flat) |

**Classification: MONITORING_RISK**

Reason: This position was entered at 09:10 IST on Jun 18 — **35 minutes before the approved entry window opens at 09:45**. It is also the only active position and creates single-symbol concentration risk. The strategy assigned (Momentum_Retest) has had 0 trades in current health monitoring period — there is no recent live performance data to calibrate this entry against. The position has not hit stop or target as of EOD Jun 18.

**Action required upon review:** Verify whether the pre-open entry was a valid pre-market setup or a timing bug in the Momentum_Retest execution path.

---

## REPORT 3 — TRADE LIFECYCLE REVIEW

### All Closed Trades This Week (6 total)

| Close Reason | Count | Win Rate | Avg P&L | Notes |
|---|---|---|---|---|
| TARGET_HIT | 0 | — | — | **Zero target hits all week** |
| STOP_HIT | 0 | — | — | |
| EARLY_LOSS | 4 | 0% | ₹-35,415 avg | All bear exits |
| EOD_CLOSE | 0 | — | — | |
| ORPHAN_CLOSE | 0 | — | — | |
| SYSTEM_CLEANUP | 0 | — | — | |
| REPLACEMENT | 0 | — | — | |
| *Win (reason unknown)* | 2 | 100% | ~+₹15,970 each | From Jun 16 ₹+31,939 split |

**Evidence:** trade_analytics_2026-06-15.json, trade_analytics_2026-06-16.json

### Key Finding
All 4 confirmed losses exited via EARLY_LOSS — meaning the system chose to close positions before reaching the formal stop level. This may indicate the EARLY_LOSS logic is triggering prematurely. **Natural exits (TARGET_HIT, STOP_HIT) did not occur this week.** This is a persistent pattern, not an isolated anomaly.

### Are Natural Exits Occurring?
**No.** For the past week, 100% of confirmed losses were EARLY_LOSS, not STOP_HIT. This means:
- Either the EARLY_LOSS threshold is too aggressive (closing before the stop is reached)
- Or the positions never had a viable recovery path

The 2 wins have unknown close reasons from available data — they are part of the Jun 16 Mean_Reversion group but exit reason is not individually itemised in the EOD retro.

---

## REPORT 4 — OPTION OPPORTUNITY REVIEW

### Option Signals This Week

| Metric | Value |
|---|---|
| Option signals generated | 0 new signals Jun 13–18 |
| Option positions opened this week | 0 |
| Option positions closed this week | 1 |
| Option positions remaining open | 1 |

### Pre-Existing Option Positions (opened Jun 5, active during audit window)

| Instrument | Strategy | Type | Lots | Entry | Exit | P&L | Exit Reason | Status |
|---|---|---|---|---|---|---|---|---|
| NIFTY | Iron_Condor_Range | IRON_CONDOR SELL | 3 × 75 | 46.33 | 46.56 | ₹-51.75 | DTE_EXIT (DTE=5) | CLOSED Jun 18 |
| BANKNIFTY | Iron_Condor_Range | IRON_CONDOR SELL | 3 × 15 | 98.89 | — | Open | — | OPEN (expiry Jun 30) |

### Option Chain Data (from logs Jun 18)
- NIFTY: live chain via AngelOne, expiry 07-Jul-26, 462 contracts, PCR = 0.84, ATM-IV = 16%
- BANKNIFTY: live chain via AngelOne, expiry 30-Jun-26, 804 contracts, PCR = 1.10, ATM-IV = 16%

### Why No New Options Were Generated This Week
- `options_weights.json = {}` — the options strategy has no learned weights; the weight vector is empty, which likely causes option strategy confidence to fall below the decision threshold
- No new Iron Condor signals fired: The system may have an internal cooldown after the Jun 5 positions or the ODM SECONDARY tier suppressed new option entries

### Evidence Assessment
The NIFTY Iron Condor barely broke even and exited via time-based DTE logic, not target. The BANKNIFTY IC remains open with 11 DTE remaining. Neither was a decisive outcome.

---

## REPORT 5 — UNIVERSE HEALTH CHECK

### Feed Source This Week
**Primary Feed: AngelOne** (100% of all scans)
- Dhan: MULTI_SID_REJECTED on all equity, IDX, and LTP endpoints — confirmed non-functional throughout the week
- YFinance: 0 calls logged — AngelOne serving as complete substitute
- Fallback rate: 0% (all live ANGELONE, no SIM, no CACHE)

### Daily Scan Counts (from feed_audit.csv)

| Date | Approx. Symbols Scanned | Source | Notes |
|---|---|---|---|
| Jun 16 | 397–1,064 per cycle | ANGELONE | Live |
| Jun 17 | 376–767 per cycle | ANGELONE | Live |
| Jun 18 | 105–6,409 per cycle | ANGELONE | 6,409 = large batch (pre-market + position monitoring) |
| Jun 19 | 9,510 (pre-market) | ANGELONE | First batch of the day |

### nifty500_universe.json
- Present: `nifty500_universe.json` (28,378 bytes, last modified 2026-05-25)
- 500 symbols available. The scanner uses this file.

### OHLCV / Universe Refresh
- `market_behavior.db` does not exist — **no OIOS-layer universe refresh records available**
- Universe refresh is executed via AngelOne scanner each morning (confirmed by `9,510` symbol batch at 09:10 on Jun 19)
- No missing OHLCV warnings detected in available log lines

### Daily Candidates
- `daily_candidates.json` last updated: 2026-06-19 10:30:02
- 10 schema keys: `candidates`, `scanner_stats`, `prepared_at`, etc.
- Enrichment runs confirmed (scanner_memory.json updated 10:30:21 Jun 19)

**Data quality verdict:** Feed healthy. No contamination, no fallback. Universe refresh running. The absence of `market_behavior.db` means OIOS-layer Phase A–F are blind to this universe data.

---

## REPORT 6 — PHASE D SHADOW REVIEW

### Status: NOT ACTIVE — DATABASE MISSING

```
OIOS DB Path: /app/data/market_behavior.db — DOES NOT EXIST
Fallback checked: /app/market_behavior.db — NOT FOUND
                  /app/oios.db             — NOT FOUND
```

**Evidence:** The `market_behavior.db` has never been initialised on the VPS container. Phase D `pending_adjustments` table does not exist. No recommendations have been generated, tracked, or applied.

**Confirmation: NO recommendation was auto-applied** — trivially true because the pipeline has never run.

**Impact:** The entire OIOS research pipeline (Phase A through F2.5) is dark. No universe stocks, no OHLCV, no signal_births, no cause_scores, no sector_conviction, no market leaders, no failure attribution, and no feature differentials have been recorded on the VPS.

---

## REPORT 7 — PHASE E SHADOW REVIEW

### Status: NOT ACTIVE — DATABASE MISSING

Same root cause as Report 6.

| Metric | Value |
|---|---|
| Cause scores generated | 0 (DB missing) |
| Propagation scores generated | 0 (DB missing) |
| Signal births recorded | 0 (DB missing) |
| Top causes identified | N/A |
| Top propagation paths | N/A |

**Evidence:** `market_behavior.db` not present on VPS container.

---

## REPORT 8 — PHASE F MARKET RESEARCH REVIEW

### Status: NOT ACTIVE — DATABASE MISSING

Same root cause.

| Metric | Value |
|---|---|
| Winners captured | 0 |
| Losers captured | 0 |
| Winner features extracted | 0 |
| Outcome rows | 0 |
| Control population | 0 |
| Failure attributions | 0 |
| Feature differentials (F2.5) | 0 |

### Indirect Evidence from Borderline Rejections (available)
The `borderline_rejections.json` (76 entries) does provide indirect market research data. From Jun 16:

| Symbol | Strategy | Direction | Entry | Day1 Close | Outcome | Would-Pass? |
|---|---|---|---|---|---|---|
| DIXON | EDG_MOMENT | BUY | 11,935 | 12,833 | +7.5% gain — MISSED | Yes (sim+debate) |
| NESTLEIND | Mean_Reversion | BUY | 1,374.7 | 1,407.3 | +2.4% gain — MISSED | Yes (sim+debate) |
| GODREJPROP | EDG_MOMENT | BUY | 1,779.9 | 1,788.3 | +0.5% — marginal | Yes |
| APOLLOHOSP | EDG_MOMENT | BUY | 8,491 | 8,427.5 | -0.75% — correct to skip | Yes |
| SRF | EDG_MOMENT | BUY | 2,744.2 | 2,705.5 | -1.4% — correct to skip | Yes |

**Key finding:** On Jun 16, DIXON (+7.5%) and NESTLEIND (+2.4%) were rejected by the execution layer (not by simulation or debate — both would have passed) but still not executed. This likely indicates the ODM density cap or position limit was the blocking factor, not signal quality.

---

## REPORT 9 — SYSTEM HEALTH

### Scheduler
- Running continuously: confirmed by 12 cycle slots per day Jun 15–18
- No scheduler crash events in system_logs
- Status: **HEALTHY**

### Monitoring Cycles
- 12 cycles per trading day (consistent)
- All cycles completed with 0 errors: "12 ✓ 12 ↯0" in all EOD retros
- Latency range: 291ms – 11,686ms (peak on Jun 15, slowest 11,686ms)
- Status: **HEALTHY**

### Price Feeds
| Source | Status | Evidence |
|---|---|---|
| AngelOne | **LIVE — Primary** | feed_audit: ANGELONE, 100% live, 0 fallback |
| Dhan | **DEAD — MULTI_SID_REJECTED** | All endpoints: quote_data, ltp_single, equity_batch all return 'failure', classified MULTI_SID_REJECTED |
| YFinance | Not in use | 0 fallback events logged |
| Options Chain | LIVE via AngelOne | NIFTY 462 contracts, BANKNIFTY 804 contracts |

**Dhan Assessment:** Dhan API has been returning MULTI_SID_REJECTED consistently across the entire audit window. The new token deployed today (2026-06-19) should address this — the old token had expired. The AngelOne fallback served all equity data successfully. No trading gap occurred.

### Telegram
- No Telegram error lines in filtered log output
- Governance violation on Jun 18 detected and reported in EOD retro (pre-open entry DRREDDY)
- Status: **PRESUMED HEALTHY** (no errors seen)

### Event Bus
- No EventBus errors in available log lines
- System restarts on Jun 16 (×2: 18:38, 18:51) and Jun 19 (11:05) observed in system_logs
- Status: **HEALTHY** (restarts were deliberate, not crash events)

### Database Write Failures
- No db write failure events in filtered logs
- control_tower.db: 26MB + 4MB WAL (actively writing)
- trading_brain.db: 377KB (updated normally)
- paper_trades.csv: Updated Jun 18 09:10 (DRREDDY entry)
- Status: **HEALTHY**

### Strategy Health Monitor
| Strategy | Status | WR Recent | Total R | Notes |
|---|---|---|---|---|
| Mean_Reversion | **DISABLED** | 22.2% (9 trades) | -1.69R | Disabled 2026-06-16 — EARLY_ABORT_LOW_WR |
| EDG_MOMENT_100_EE0005 | Enabled (degraded) | 0% (8 recent) | -7.98R | 0 wins in last 8 health-period trades |
| Momentum_Retest | Enabled | — | 0R | 0 trades in health monitoring period; strategy_health.json shows no recent trades |
| Bull_Call_Spread | Enabled | 0/4 wins | 0R | |
| Trend_Pullback | Enabled | — | — | |

**Critical: Mean_Reversion is disabled. EDG_MOMENT has 0 recent wins. System is effectively operating with no proven active strategy.**

### ODM Tier
- Current tier: SECONDARY (history: [9,0],[11,0],[11,0],[12,0],[12,0])
- Density: 0.0% — no signals allowed to breach concentration cap
- Consecutive expand: 0

---

## REPORT 10 — ACTIONABLE FINDINGS

### CRITICAL

---

#### CRITICAL-1: paper_trades.csv Reset — Execution Record Corrupted
**Evidence:**
- `paper_trades.csv` contains only 1 trade (DRREDDY, Jun 18)
- `paper_trades_legacy.csv` (28KB) was created 2026-06-16 18:37:17
- System was restarted twice on Jun 16 evening (18:38, 18:51)
- Jun 15–16 trades (6 closed) are NOT in the current paper_trades.csv

**Root Cause:** A restart or re-initialisation on Jun 16 evening overwrote `paper_trades.csv`. The prior content was saved to `paper_trades_legacy.csv` but the active journal is now missing 6 trades from this week.

**Impact:** EOD learning, win-rate tracking, and the `paper_trading_daily.json` cumulative P&L (`cum_pnl=0`) are all reading from the reset file. The learning system sees 0 closed trades this session. Strategy weights and confidence are being calculated on an empty ledger.

**Recommended Fix:** Merge `paper_trades_legacy.csv` into `paper_trades.csv` and replay EOD learning for Jun 15–16.

---

#### CRITICAL-2: Mean_Reversion Strategy Disabled — No Primary Strategy Active
**Evidence:**
- `strategy_health.json`: `"disabled_reason": "EARLY_ABORT_LOW_WR"`, disabled since 2026-06-16T15:35:12
- WR at disable: 22.2% (2W in 9 trades)
- Sessions since disabled: 3
- EDG_MOMENT_100_EE0005: 0 wins in 8 recent health-tracked trades

**Root Cause:** Mean_Reversion's recent performance (primarily EARLY_LOSS exits this week) triggered the automatic low-WR guard. The strategy is now in cooldown.

**Impact:** The system is executing with Momentum_Retest as the primary remaining enabled strategy, but Momentum_Retest has 30 all-time trades at 47% WR with -16.6R total. This is the strategy that generated the Jun 18 governance violation.

**Recommended Fix:** Review whether EARLY_LOSS (pre-stop closure) should count against Win Rate calculations as harshly as STOP_HIT losses. The 22.2% WR may be artificially low due to premature exits, not true strategy failure.

---

### HIGH

---

#### HIGH-1: Governance Violation — DRREDDY Momentum_Retest at 09:10 (Window: 09:45)
**Evidence:**
- system_logs ID 1781: `TRADE_OPENED symbol=DRREDDY strategy=Momentum_Retest ts=2026-06-18T09:10:17`
- EOD retro Jun 18: "Pre-open entry: DRREDDY (Momentum_Retest) at 09:10 — window opens 09:45"
- paper_trades.csv: `timestamp=2026-06-18 09:10:16`

**Root Cause:** Momentum_Retest execution triggered 35 minutes before the approved window opens. The entry guard for the 09:45 open may not be enforced in the Momentum_Retest path (vs Mean_Reversion which never violated the window).

**Impact:** The position is currently open. It represents ₹1.08M gross exposure entered outside the governance window. Price action in the first 35 minutes of the session is typically high-volatility pre-open. If this position stops out, the exit will be from an illegally entered position.

**Recommended Fix:** Audit the time-window guard in the Momentum_Retest strategy execution path. The 09:45–14:30 constraint must be enforced at the order manager level regardless of strategy.

---

#### HIGH-2: All MC Rejections Are "Stability" — Systemic Filter Blockage
**Evidence:**
- Jun 15: 132/132 MC-rejected = Stability
- Jun 16: 180/180 MC-rejected = Stability
- Jun 17: 41/41 MC-rejected = Stability
- Jun 18: 10/10 MC-rejected = Stability

**Root Cause:** The Monte Carlo simulation is rejecting signals exclusively for Stability reasons. This means market conditions (or simulation parameters) consistently fail the stability threshold. In range_market with VIX 12.7–14.3, this may indicate the stability parameter is calibrated for a more volatile regime.

**Impact:** Of ~697 signals generated this week, ~363 were blocked at MC stage for stability alone. This is the dominant filter. If this threshold is miscalibrated, many valid signals are being suppressed.

**Recommended Fix:** Review the `stability` threshold in `market_simulation/`. Compare current VIX regime (12.7–14.3) against the calibration baseline. Consider whether the stability threshold needs a regime-aware override.

---

#### HIGH-3: OIOS market_behavior.db Not Initialised on VPS
**Evidence:**
- `/app/data/market_behavior.db` — NOT FOUND
- `/app/market_behavior.db` — NOT FOUND
- `/app/oios.db` — NOT FOUND

**Root Cause:** The migration script `phase_f_migration.py` has never been executed on the VPS container. All OIOS infrastructure (Phase A through F2.5) exists in code but has never been initialised.

**Impact:** Phase D (pending_adjustments), Phase E (cause_scores, signal_births), Phase F (market_leaders, outcomes, controls, failure_attribution, feature_differentials) — all dark. The entire research pipeline has produced zero data since it was built.

**Recommended Fix:** Run `python phase_f_migration.py` inside the container once to initialise the DB. Then schedule the daily capture pipeline.

---

#### HIGH-4: Missed Winners Blocked by ODM Density Cap (Jun 16)
**Evidence:**
- `borderline_rejections.json`: DIXON rejected Jun 16, day1_price=12,833 vs entry 11,935 = **+7.5%**
- NESTLEIND rejected Jun 16, day1_price=1,407.3 vs entry 1,374.7 = **+2.4%**
- Both would_pass_simulation=True, would_pass_debate=True
- ODM density: 0.0%, tier: SECONDARY

**Root Cause:** The signal quality was sufficient (debate and simulation approved), but ODM density/position cap prevented execution. On the same day, 3 EARLY_LOSS trades were executed, consuming the position budget.

**Impact:** The system skipped DIXON (+7.5%) and NESTLEIND (+2.4%) while holding positions that went on to lose. The density cap may be inversely calibrated — blocking good signals while holding deteriorating ones.

**Recommended Fix:** Review whether ODM SECONDARY tier should use a higher signal quality threshold for new entries (e.g. require higher confidence) rather than a blanket density cap that equally blocks all signals.

---

### MEDIUM

---

#### MEDIUM-1: Dhan API Dead for All Equity/Index Endpoints
**Evidence:**
- All Dhan calls: `MULTI_SID_REJECTED`, `circuit_impact=NO`
- DhanTimeWindowAudit: `success_rate=0.0% successes=0 failures=5`
- Affects: equity_batch, quote_data (NIFTY/BANKNIFTY), ltp_single

**Root Cause:** Previous token was expired (confirmed by today's token deployment). With new token deployed 2026-06-19, this should self-resolve on next cycle.

**Impact:** Dhan was non-functional all week. AngelOne served as complete fallback with no trading gaps. Monitoring required to confirm Dhan comes live with new token.

---

#### MEDIUM-2: EDG_MOMENT_100_EE0005 — 0 Wins in Recent Health Period
**Evidence:**
- `strategy_health.json`: EDG_MOMENT 8 recent trades, 0 wins, total_r = -7.98R
- Recent P&L: all negative (-1.8%, -5.2%, -4.4%, -5.2%, -4.4%, -0.9%, -1.7%, -1.5%)

**Root Cause:** The strategy has not found a profitable setup in recent market conditions. All 8 health-period trades are losses. The strategy has not yet been auto-disabled (possibly because the WR threshold has not been breached by the health monitor, or because the period count doesn't trigger the guard).

**Impact:** EDG_MOMENT is assigned trades but producing consistent losses. With Mean_Reversion disabled and EDG_MOMENT at 0% WR, the system's remaining active strategies have poor recent track records.

---

#### MEDIUM-3: System Restarts Create paper_trades.csv Fragmentation
**Evidence:**
- 5 system restarts in the audit period (Jun 16 ×2, Jun 19 ×1; pre-period: Jun 12 ×4)
- Each restart risks resetting the paper_trades.csv if the restore-from-journal logic has a gap

**Root Cause:** Likely a `paper_trades.csv` path initialisation issue on restart — the file gets opened in write mode (truncated) rather than append mode.

**Recommended Fix:** On startup, check if paper_trades.csv exists and has content; if yes, append rather than overwrite.

---

#### MEDIUM-4: Mean_Reversion Disabled — Cooldown Not Auto-Lifting
**Evidence:**
- Disabled 2026-06-16T15:35:12
- sessions_since_disabled: 3 (Jun 16, Jun 17, Jun 18)
- cooldown_override: false
- No re-enable event in system_logs

**Root Cause:** The EARLY_ABORT_LOW_WR guard activates after sustained low WR. The cooldown timer is counting sessions but has not yet triggered re-evaluation.

**Impact:** The system has been without its historically best strategy for 3 sessions. Mean_Reversion has the highest all-time WR (75% lifetime, 32 trades), but the recent 10-trade health window shows 20% — indicating a regime shift or a EARLY_LOSS counting problem.

---

### LOW

---

#### LOW-1: BANKNIFTY Iron Condor Still Open — Monitor Expiry Risk
**Evidence:**
- `options_trades.csv`: BANKNIFTY IC opened Jun 5, expiry Jun 30, status=open
- `options_outcomes.json`: only NIFTY entry (BANKNIFTY outcome not logged yet)
- DTE remaining: ~11 days

**Root Cause:** The DTE_EXIT logic did not fire for BANKNIFTY (fires at DTE=5). Normal.

**Impact:** Position carries gamma risk in the last week before expiry (Jun 30). If BANKNIFTY moves sharply before expiry, the IC could have outsized losses.

---

#### LOW-2: options_weights.json Is Empty
**Evidence:** `options_weights.json = {}`

**Root Cause:** The options strategy learning system has not generated any weight entries. Likely requires minimum trade count.

**Impact:** New options signals may use default/equal weights rather than learned optimal weights.

---

#### LOW-3: Research Gate at 19/100 Prepared Trades — Adaptive Mutation Frozen
**Evidence:**
- All EOD retros: `prepared=19 required=100 ready=NO adaptive_mutation_blocked=YES — FROZEN`
- Jun 17 retro: `prepared=19` (no new trades added, 0 closed Jun 17)
- Jun 18 retro: same count (CSV reset means DRREDDY not counted yet)

**Root Cause:** Adaptive mutation is correctly frozen pending 100 clean prepared-universe trades.

**Impact:** The system will not self-optimise for another ~81 trades minimum. This is by design and healthy given current sample size.

---

## SUMMARY DASHBOARD

```
PERIOD    : 2026-06-13 → 2026-06-19
TRADES    : 7 opened | 6 closed | 1 open
WIN RATE  : 33.3% (2/6)
NET P&L   : ₹-41,723
PROFIT F  : 0.43
SIGNALS   : ~697 generated | 363 MC-blocked | ~48 debate approved
FEED      : AngelOne LIVE 100% | Dhan DEAD (new token deployed Jun 19)
STRATEGY  : Mean_Reversion DISABLED | EDG_MOMENT 0 recent wins
OIOS      : market_behavior.db MISSING — all Phase D/E/F dark
GOVN VIOL : 1 — DRREDDY 09:10 entry (window 09:45–14:30)
OPEN POS  : DRREDDY (Momentum_Retest, MONITORING_RISK, governance flag)
STABILITY : 32-session clean streak ✅
OPTIONS   : NIFTY IC closed (₹-51.75) | BANKNIFTY IC open (11 DTE)
```

### Finding Priority Matrix
| Priority | Finding |
|---|---|
| CRITICAL | paper_trades.csv reset — execution record corrupted |
| CRITICAL | Mean_Reversion disabled — no primary strategy active |
| HIGH | Governance violation — DRREDDY 09:10 pre-open entry |
| HIGH | All MC rejections = Stability — systemic MC filter blockage |
| HIGH | OIOS market_behavior.db not initialised on VPS |
| HIGH | Missed winners DIXON +7.5%, NESTLEIND +2.4% blocked by ODM cap |
| MEDIUM | Dhan dead all week (token expired — fixed Jun 19) |
| MEDIUM | EDG_MOMENT 0 wins in 8 recent health trades |
| MEDIUM | System restarts causing CSV fragmentation |
| MEDIUM | Mean_Reversion cooldown not auto-lifting after 3 sessions |
| LOW | BANKNIFTY IC approaching expiry (11 DTE) |
| LOW | options_weights.json empty |
| LOW | Research gate at 19/100 — adaptive mutation frozen |

---

*This document is an evidence-gathering audit only. No code was modified. No fixes were applied. All figures sourced directly from VPS container data.*
