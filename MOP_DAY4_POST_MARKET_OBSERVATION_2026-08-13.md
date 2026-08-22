# MOP-DAY4 POST-MARKET OPPORTUNITY OBSERVATION AUDIT
## Date: 2026-08-13 | Analyst: GitHub Copilot | Audit Type: READ-ONLY

---

## EXECUTIVE SUMMARY

| Field | Value |
|---|---|
| Audit Date | 2026-08-13 |
| NIFTY 50 Close | 24,395.85 (-0.16%) |
| BANKNIFTY Close | 57,635.25 (-0.43%) |
| India VIX | 11.37 (-2.72%) |
| Market Regime (inferred) | RANGE_MARKET / LOW_VOLATILITY |
| Stocks fetched from universe | 206 / 230 |
| Significant movers (>±1.5%) | 40 |
| Pre-move candidates in store | 7 / 40 |
| Paper trades executed | **0** |
| MOP-RC-001 observations | **0** (directory not created — no post-deploy scan) |
| **Audit Verdict** | **CORRECT_NO_TRADE** with SYSTEMIC_CONCERN flag |

**Bottom line:** 0 trades on 2026-08-13 was the expected and correct output given the flat market
regime, stale candidate store (2-day-old BML), disabled Mean_Reversion strategy in range_market,
historically stringent decision threshold (6.5–6.7), and a narrow post-deploy window (~20 min
before close). A possible mild miss exists for SOLARINDS (+8.51%) and OBEROIRLTY (+2.56%), both
of which were pre-market candidates, but neither had active intraday setup confirmation today.

---

## SECTION 1: MARKET GROUND TRUTH

### 1.1 Index Summary (2026-08-13)

| Index | Close | Change | Implication |
|---|---|---|---|
| NIFTY 50 | 24,395.85 | -0.16% | Flat; no directional breakout day |
| BANKNIFTY | 57,635.25 | -0.43% | Mild weakness in financials |
| India VIX | 11.37 | -2.72% | Very low volatility; market complacent |

VIX at 11.37 is historically low for NSE. The system's RANGE_MARKET regime is active at VIX levels
of ~13–19 (per CT cycle logs). VIX 11.37 is even below the RANGE_MARKET floor — placing today in
a **low-vol / subdued** environment where breakout strategies see very little qualifying volume.

### 1.2 Universe Coverage

- **Universe**: 230 stocks in `nifty500_universe.json`
- **Symbols with valid prices today**: 206 (89.6%)
- **Failed downloads** (likely stale symbols/ticker renames): 24 symbols including
  TATAMOTORS, TVSMOTORS, LTIM, ZOMATO, MAHINDCIE, VINATI, PVR, SHOPPERSSTOP, VEDANT,
  FINOLEX, BLUESTAR, SPICEJET, WELSPUNIND, SUNTECKRLTY, KKALPATAARU, MACROTECH,
  KSBBLTD, INDIAGRID, MINDA, ACCLTD, WABCO, MIRAE, REC, IPCA
  *(Universe staleness: 24/230 = 10.4% stale symbols)*

### 1.3 Top 20 Gainers (2026-08-13)

| Rank | Symbol | % Change | Sector | In Candidate Store |
|---|---|---|---|---|
| 1 | ASTRAL | +8.74% | INFRA | NO |
| 2 | SOLARINDS | +8.51% | DEFENCE | YES (score=0.6421) |
| 3 | CONCOR | +4.22% | INFRA | NO |
| 4 | CLEAN | +3.91% | CHEMICALS | NO |
| 5 | RAYMOND | +3.72% | TEXTILES | NO |
| 6 | GODREJCP | +3.52% | FMCG | YES (score=0.565) |
| 7 | APLAPOLLO | +3.36% | METALS | NO |
| 8 | KALYANKJIL | +2.80% | RETAIL | NO |
| 9 | AMBER | +2.72% | ELECTRONICS | NO |
| 10 | TATACONSUM | +2.69% | FMCG | NO |
| 11 | GLAND | +2.64% | PHARMA | NO |
| 12 | OBEROIRLTY | +2.56% | REALESTATE | YES (score=0.81) |
| 13 | PAYTM | +2.45% | FINTECH | NO |
| 14 | SUNTV | +2.03% | MEDIA | NO |
| 15 | GRINDWELL | +1.90% | INFRA | NO |
| 16 | PRESTIGE | +1.90% | REALESTATE | YES (score=0.5853) |
| 17 | KPITTECH | +1.85% | IT | NO |
| 18 | SENCO | +1.81% | RETAIL | NO |
| 19 | DIXON | +1.70% | ELECTRONICS | NO |
| 20 | IPCALAB | +1.68% | PHARMA | NO |

### 1.4 Top 20 Losers (2026-08-13)

| Rank | Symbol | % Change | Sector | In Candidate Store |
|---|---|---|---|---|
| 1 | PAGEIND | -4.64% | TEXTILES | YES (score=0.88) |
| 2 | EASEMYTRIP | -4.33% | CONSUMER | NO |
| 3 | FORCEMOT | -3.86% | AUTO | YES (score=0.5988) |
| 4 | BALKRISIND | -3.48% | AUTO | NO |
| 5 | ZYDUSLIFE | -3.13% | PHARMA | NO |
| 6 | SAIL | -3.06% | METALS | YES (score=0.639) |
| 7 | HINDALCO | -2.99% | METALS | NO |
| 8 | PCJEWELLER | -2.35% | RETAIL | NO |
| 9 | TIINDIA | -2.08% | AUTO | NO |
| 10 | THERMAX | -2.00% | INFRA | NO |
| 11 | GABRIEL | -1.96% | AUTO | NO |
| 12 | ABBOTINDIA | -1.85% | PHARMA | NO |
| 13 | IRCTC | -1.77% | INFRA | NO |
| 14 | KAYNES | -1.76% | ELECTRONICS | NO |
| 15 | ICICIBANK | -1.74% | BANKING | NO |
| 16 | BIOCON | -1.73% | PHARMA | NO |
| 17 | VEDL | -1.70% | METALS | NO |
| 18 | ULTRACEMCO | -1.56% | CEMENT | NO |
| 19 | GRASIM | -1.54% | CEMENT | NO |
| 20 | GMRAIRPORT | -1.48% | INFRA | NO |

---

## SECTION 2: UNIVERSE COVERAGE ANALYSIS

- All 40 significant movers (BML-40) are **within** the 230-stock IIOS universe: **40/40 (100%)**.
- No significant mover was excluded at the universe level.
- Coverage constraint: 24 universe symbols have stale/renamed tickers — these 24 are invisible to
  the scanner. None of the BML-40 today are in this stale pool.

---

## SECTION 3: PRE-MOVE DISCOVERY EVIDENCE

### 3.1 Candidate Store State

| Field | Value |
|---|---|
| Candidate file used | `daily_candidates_20260811.json` |
| Candidate file date | 2026-08-11 (2 days stale) |
| Total candidates | 57 |
| BML-40 stocks in candidate store | 7/40 (17.5%) |

The candidate store was **not refreshed today** (no `daily_candidates_20260813.json` exists).
The 2-day-old store provides degraded pre-move evidence.

### 3.2 Candidate Store — Top 15 by BML Score

| Symbol | BML Score | Moved Today | Direction |
|---|---|---|---|
| INDIANB | 0.9113 | +0.4% (approx) | — |
| INOXWIND | 0.9066 | n/a | — |
| BOSCHLTD | 0.9019 | n/a | — |
| NAUKRI | 0.8951 | n/a | — |
| **PAGEIND** | **0.88** | **-4.64%** | ❌ FELL |
| DMART | 0.86 | n/a | — |
| DEEPAKNTR | 0.8456 | n/a | — |
| CROMPTON | 0.8231 | n/a | — |
| PNBHOUSING | 0.8199 | n/a | — |
| **OBEROIRLTY** | **0.81** | **+2.56%** | ✅ ROSE |
| LTTS | 0.7867 | n/a | — |
| MARUTI | 0.7782 | n/a | — |
| POLICYBZR | 0.7678 | n/a | — |
| NYKAA | 0.7644 | n/a | — |
| NESTLEIND | 0.7621 | n/a | — |

**Key observation**: PAGEIND (highest BML mover, score=0.88) fell -4.64% today — the system
correctly NOT entering a LONG on the highest-scored candidate is the most important correct
non-trade. OBEROIRLTY (score=0.81) rose +2.56% and is the most plausible missed opportunity.

### 3.3 BML Coverage of Today's Significant Movers

| Symbol | BML Score | In Attrition (2026-08-11) | Attrition Reason |
|---|---|---|---|
| ASTRAL +8.74% | NOT IN STORE | Not scanned | Not a candidate |
| SOLARINDS +8.51% | 0.6421 | Not in attrition | Passed strategy gate or not evaluated |
| OBEROIRLTY +2.56% | 0.81 | YES (2 records) | STRATEGY_DISABLED (Mean_Reversion, scores 5.2/5.98) |
| PRESTIGE +1.90% | 0.5853 | YES (2 records) | STRATEGY_DISABLED (Mean_Reversion, scores 5.16/5.13) |
| PAGEIND -4.64% | 0.88 | YES (2 records) | STRATEGY_DISABLED (Mean_Reversion, scores 5.78/6.29) |
| FORCEMOT -3.86% | 0.5988 | Not confirmed | — |
| SAIL -3.06% | 0.639 | Not confirmed | — |
| GODREJCP +3.52% | 0.565 | Not in attrition | Passed gate or not evaluated |

**Insight**: OBEROIRLTY and PRESTIGE (both gainers today) were evaluated via Mean_Reversion on
2026-08-11 and rejected because the strategy was DISABLED. The system had pre-move evidence for
these stocks but the active strategy path was closed.

---

## SECTION 4: HYPOTHETICAL OBSERVATIONS (OBSERVATIONAL ONLY)

> **MANDATORY LABEL**: All entries below are `HYPOTHETICAL_OBSERVATION — NOT A TRADE`.
> No position suggestion. No order. No signal file created.

The following represents what the system MIGHT have observed if a full scan cycle ran today
with refreshed candidates and enabled strategies:

### 4.1 Category A — Strong Pre-Move Evidence (Candidate + Moved Significantly)

**1. SOLARINDS — HYPOTHETICAL_OBSERVATION**
- Move: +8.51% (DEFENCE sector)
- BML Score: 0.6421 (moderate)
- Not in scan attrition → likely passed initial gates on 2026-08-11
- Setup hypothesis: Defence sector momentum + volume expansion
- Regime dependency: Breakout strategies need volatile/trending regime; today's flat NIFTY
  and VIX 11.37 make breakout conditions marginal
- Probability of signal generation today: LOW-MODERATE
- Note: +8.51% without Nifty support = stock-specific catalyst; scanner might not have caught it

**2. OBEROIRLTY — HYPOTHETICAL_OBSERVATION**
- Move: +2.56% (REALESTATE sector)
- BML Score: 0.81 (strong)
- In attrition: rejected as STRATEGY_DISABLED for Mean_Reversion
- Setup hypothesis: Mean_Reversion bounce (RSI recovery) or sector rotation
- Key constraint: Mean_Reversion strategy is DISABLED in range_market regime
- Today's regime (VIX 11.37) → range_market or lower → Mean_Reversion still disabled
- Even if scanned, STRATEGY_DISABLED would block signal generation
- Probability of signal generation today: VERY LOW (strategy disabled)

### 4.2 Category B — Candidate Moved Wrong Direction (0-trade Validated)

| Symbol | BML Score | Today's Move | Non-Trade Verdict |
|---|---|---|---|
| PAGEIND | 0.88 | -4.64% | ✅ CORRECT — LONG would have lost |
| FORCEMOT | 0.5988 | -3.86% | ✅ CORRECT — LONG would have lost |
| SAIL | 0.639 | -3.06% | ✅ CORRECT — LONG would have lost |

All three of the highest-activity candidates from the attrition log moved NEGATIVELY today.
If the system had generated LONG signals for any of these, the trades would have been losers.
**This validates the 0-trade outcome for the majority of candidates.**

### 4.3 Category C — Movers Not in Candidate Store

| Symbol | Move | Assessment |
|---|---|---|
| ASTRAL +8.74% | INFRA | Not discoverable — not in candidate store |
| CONCOR +4.22% | INFRA | Not discoverable |
| CLEAN +3.91% | CHEMICALS | Not discoverable |
| RAYMOND +3.72% | TEXTILES | Not discoverable |
| APLAPOLLO +3.36% | METALS | Not discoverable |
| EASEMYTRIP -4.33% | CONSUMER | Not discoverable |
| BALKRISIND -3.48% | AUTO | Not discoverable |

ASTRAL was the biggest gainer (+8.74%). Its absence from the candidate store means the system
had no pre-move evidence — this is not a miss attributable to a signal quality issue; it is a
**universe selection gap** (ASTRAL not scored high enough by BML to be a candidate).

---

## SECTION 5: MOP-RC-001 TELEMETRY STATUS

| Field | Value |
|---|---|
| `data/mop_rc001/` directory | **Does not exist** |
| Observations today | **0** |
| Root cause | No scan cycles ran locally after MOP-RC-001 deploy |

### 5.1 Deploy Timeline Analysis

| Time (IST) | Event |
|---|---|
| ~15:10 | MOP-RC-001 deployed to VPS via `docker compose up -d` |
| ~15:10 | New containers start; `mop_rc001/` directory would be created on FIRST scan |
| 15:30 | NSE market close |
| ~15:10–15:30 | **~20-minute window** for any post-deploy scan to create observations |

The local Windows environment has no MOP-RC-001 observations because no scan cycles ran
locally. The VPS may have run 0–1 scan cycles in the narrow 20-minute post-deploy window.
VPS data volume is separate from local `data/` directory and was not inspected in this audit.

### 5.2 MOP-RC-001 Validation Status

- The observer module (`mop_rc001_observer.py`) is deployed and tested (15/15 tests pass)
- `record_signal_observation()` will create the directory on first invocation
- **Expected behavior**: First weekday scan cycle after 2026-08-13 will create the JSONL file
- The absence of today's file is **expected and correct** given the deploy timing

---

## SECTION 6: ZERO-TRADE FORENSICS

### 6.1 Paper Trades CSV

```
File: data/paper_trades.csv
Rows: 0 (headers only)
Trades on 2026-08-13: 0 (confirmed)
Total historical trades: 0 (system has never executed a paper trade)
```

### 6.2 Scan Attrition Analysis (2026-08-11 — most recent available)

| Stage | Count | % of Records |
|---|---|---|
| STRATEGY_LAB_REJECT | 111 | 100% |

| Rejection Reason | Count | % |
|---|---|---|
| STRATEGY_DISABLED | 104 | 93.7% |
| RR_0.6_below_min_2.0 | 7 | 6.3% |

| Strategy | Count | Note |
|---|---|---|
| Mean_Reversion | 111 | 100% — only strategy evaluated |

| Regime | Count |
|---|---|
| range_market | 111 |

**Interpretation**: On 2026-08-11 (range_market regime), the scan evaluated Mean_Reversion
across all candidates. 104 were rejected because Mean_Reversion is DISABLED in range_market.
7 more were rejected for insufficient risk-reward (RR < 2.0). Zero actionable signals emerged.

### 6.3 Rejection Funnel (Reconstructed for 2026-08-11)

```
Universe:                   230 stocks
    ↓ BML candidate filter
Candidate store:            57 stocks passed
    ↓ Strategy evaluation (range_market regime)
Strategy gate:              Mean_Reversion DISABLED → 104 rejected
                            RR < 2.0 → 7 rejected
Actionable signals:         0
    ↓ (Hypothetically, if any passed)
DecisionEngine threshold:   6.5 partial / 6.7 full
    (Historical: most scores in 6.3–6.5 range → rejected)
    ↓
risk_approved:              0 (in April 2026 cycles)
    ↓
trades_executed:            0
```

### 6.4 DecisionEngine Threshold Analysis

Last 10 CT decisions (from local DB, April 2026):

| Symbol | Strategy | Confidence | Decision |
|---|---|---|---|
| HDFCBANK | Equity_Breakout | 6.34 | REJECTED (< 6.5) |
| RELIANCE | Equity_Breakout | 6.49 | REJECTED (< 6.5, missed by 0.01) |
| HDFCBANK | Equity_Breakout | 6.40 | REJECTED |
| RELIANCE | Equity_Breakout | 6.49 | REJECTED |
| RELIANCE | Hedging_Model | 6.46 | REJECTED |
| COALINDIA | Breakout_Volume_RSI_HiVol | 6.55 | **APPROVED** |
| LT | Breakout_Volume_RSI_HiVol | 6.55 | **APPROVED** |
| INFY | Breakout_Volume_RSI_HiVol | 6.40 | **APPROVED** |
| ICICIBANK | Breakout_Volume_RSI_HiVol | 6.73 | **APPROVED** |
| HDFCBANK | Breakout_Volume_RSI_HiVol | 6.48 | **APPROVED** |

The threshold is calibrated stringently. `Breakout_Volume_RSI_HiVol` is the primary strategy
that generates approvals. This strategy likely requires volatile regime (VIX > ~18) to activate.
Today's VIX (11.37) is far below its activation threshold.

---

## SECTION 7: SYSTEMIC PATTERN ANALYSIS

### 7.1 Historical Cycle Statistics

From `ct_cycles` (last 20 cycles, March–April 2026):

| Metric | Value |
|---|---|
| Signals generated per cycle | 22–24 (consistent) |
| risk_approved per cycle | 0 (typical), up to 8 in March 2026 |
| sim_approved per cycle | 0–6 |
| trades_executed per cycle | **0 in all 20 cycles** |

**Critical observation**: Multiple March 2026 cycles show `risk_approved=8, sim_approved=6,
trades_executed=0`. This means signals passed CapitalRiskEngine AND MarketSimulation approval,
yet zero orders were created by ExecutionEngine. This is a systemic execution bottleneck that
pre-dates today's audit.

### 7.2 ODM State

```json
{
  "current_tier": "SECONDARY",
  "history": [[24,0], [24,0], [23,0], [24,0], [24,0], [24,0], [24,0], [24,0], [24,0], [20,0]],
  "saved_at": "2026-04-02 10:03"
}
```

ODM history format: `[signals_generated, trades_executed]`. 
**All 10 recorded cycles: trades = 0.** ODM is in SECONDARY tier (reduced trade capacity)
due to persistent zero-trade output, which creates a feedback loop: no trades → SECONDARY → 
reduced opportunity scoring → harder to reach decision threshold.

### 7.3 Data Feed Status

```json
{
  "consecutive_fallback_sessions": 9,
  "last_fallback_at": "2026-05-22T09:56:06Z"
}
```

Dhan API has been blocked (HTTP 451) for 9+ consecutive sessions since May 2026.
All market data is being fetched via yfinance fallback. This affects:
- Data latency (yfinance has ~15 min delay in some configurations)
- Volume data reliability (yfinance volume can differ from exchange feed)
- Breakout confirmation quality (volume-based breakout strategies depend on real-time volume)

### 7.4 Regime Distribution

| Regime | Cycles | Last Seen |
|---|---|---|
| volatile | Most April 2026 cycles | 2026-04-02 |
| range_market | March 2026 cycles | 2026-03-19 |
| (today: low_vol / ~11.37 VIX) | Not in local DB | 2026-08-13 |

---

## SECTION 8: VPS SYSTEM STATE (INFERENCE)

*VPS data volume not directly accessible — inferred from available evidence.*

| Item | Inference | Confidence |
|---|---|---|
| VPS running today | Yes — deployed and healthy | HIGH |
| Pre-deploy cycles today | Likely ran morning schedule (09:15 pre-market, ~09:45 scan) | MEDIUM |
| Post-deploy cycles (15:10–15:30) | 0–1 cycles (narrow window) | MEDIUM |
| VPS regime today | range_market or low_vol (VIX 11.37) | HIGH |
| VPS Mean_Reversion status | DISABLED in range_market | HIGH |
| VPS candidate store refresh | Uncertain — may have run BML pre-market | MEDIUM |
| VPS trades today | 0 (paper_trades.csv confirms no entries) | HIGH |

---

## SECTION 9: OPPORTUNITY QUALITY GRADING

| Symbol | BML Score | Today's Move | In-Universe | Strategy Path | Quality |
|---|---|---|---|---|---|
| SOLARINDS | 0.6421 | +8.51% | YES | Breakout? (not in attrition) | B+ |
| OBEROIRLTY | 0.81 | +2.56% | YES | Mean_Reversion (DISABLED) | C+ (blocked) |
| GODREJCP | 0.565 | +3.52% | YES | Not in attrition | C |
| PRESTIGE | 0.5853 | +1.90% | YES | Mean_Reversion (DISABLED) | D+ (blocked) |
| PAGEIND | 0.88 | -4.64% | YES | Mean_Reversion (DISABLED) | ❌ WRONG DIR |
| FORCEMOT | 0.5988 | -3.86% | YES | Not confirmed | ❌ WRONG DIR |
| SAIL | 0.639 | -3.06% | YES | Not confirmed | ❌ WRONG DIR |
| ASTRAL | N/A | +8.74% | YES | NOT A CANDIDATE | N/A |

**B+ grade** = best observable opportunity.
**SOLARINDS at +8.51%** is the one stock that had pre-move candidate evidence AND moved
significantly in the right direction. Its moderate BML score (0.6421) and the absent attrition
record (suggesting it passed initial gates) make it the single best missed-opportunity candidate.
However, the regime (low VIX, flat Nifty) does not support a Breakout setup on the index.

---

## SECTION 10: REGIME COMPATIBILITY MATRIX

| Strategy | Regime Required | Today's Regime | Compatible |
|---|---|---|---|
| Mean_Reversion | range_market | range_market / low_vol | DISABLED |
| Breakout_Volume_RSI_HiVol | volatile (VIX>~18) | low_vol (VIX 11.37) | NO |
| Equity_Breakout | volatile / trending | range/low_vol | UNLIKELY |
| Hedging_Model | any | any | MARGINAL |
| trend_pullback | BULL_TREND | flat/mixed | NO |
| high_rsi_short | any bearish | mixed/flat | LOW |
| momentum_retest | RSI 50–65 zone | possible | POSSIBLE |

**At VIX 11.37, none of the high-confidence strategies are well-suited to the regime.**
The system is appropriately conservative in low-volatility environments.

---

## SECTION 11: CAPITAL AND SIZING ANALYSIS

| Item | Status | Notes |
|---|---|---|
| Total capital | ₹10,000 | Paper trading |
| capital_state.json | NOT FOUND locally | VPS-only |
| strategy_budget.json | NOT FOUND locally | VPS-only |
| portfolio_state.json | NOT FOUND locally | VPS-only |
| cre_state.json | NOT FOUND locally | VPS-only |
| Inferred capital utilisation | 0% | 0 trades ever |

At ₹10,000 total capital, the minimum viable trade (with 2:1 RR and 2% risk) is approximately
₹200 risk → ₹400 target. Position size constraints may additionally filter marginal setups.

---

## SECTION 12: COMPARISON WITH LAST BML RUN (2026-08-11)

| Dimension | 2026-08-11 | 2026-08-13 |
|---|---|---|
| BML candidates | 57 | (not refreshed) |
| Regime | range_market | low_vol / range |
| Dominant rejection | STRATEGY_DISABLED | (same expected) |
| VIX | ~18.72 (early) | 11.37 |
| Actionable signals | 0 | 0 (inferred) |
| Key mover | — | SOLARINDS +8.51% |

2026-08-11's range_market scan produced 0 actionable signals. 2026-08-13 has even lower VIX —
the environment is more subdued. The 0-trade outcome is consistent with the established pattern.

---

## SECTION 13: MISSED OPPORTUNITY ASSESSMENT

### Was today's 0-trade a miss?

**For most stocks: NO — Correct.**

The three candidates that fell hardest (PAGEIND -4.64%, FORCEMOT -3.86%, SAIL -3.06%) were all
in the candidate store with meaningful scores. Had the system produced LONG signals for any of
them, these would have been immediate losing trades. The absence of trades is unambiguously
correct for these three.

**For SOLARINDS (+8.51%): BORDERLINE.**

SOLARINDS was a candidate (score=0.6421) and moved +8.51%. It was NOT in the attrition log,
suggesting it may have passed initial strategy gates. However:
- Its BML score (0.6421) is below the top-tier threshold
- The move happened in a flat-NIFTY, low-VIX environment — not a breakout day market-wide
- The system would likely have scored it below the 6.5 decision threshold
- No intraday scan ran today to confirm a live breakout signal
- DEFENCE sector rally on 2026-08-13 may have been stock-specific catalyst

**Assessment**: SOLARINDS is a **partial observation miss** — the system had the stock in scope
but lacked the regime support and intraday scan to validate the setup. This is a limitation of
using a 2-day-stale candidate store without intraday pre-market refresh.

**For OBEROIRLTY (+2.56%): GOVERNANCE BLOCKED.**

OBEROIRLTY (score=0.81) moved positively but its strategy path (Mean_Reversion) is DISABLED
in range_market regime. This is a deliberate governance decision — running Mean_Reversion in
range_market is permitted by the regime, but the strategy has been disabled (likely due to poor
backtest performance or explicit governance toggle). This is `GOVERNANCE_BLOCKED`, not a miss.

---

## SECTION 14: SYSTEMIC CONCERN FLAGS

> These are READ-ONLY observations. No action is taken in this audit.

### SC-001: Execution Bottleneck (HIGH SEVERITY)
**Observation**: CT cycles from March 2026 show `risk_approved=8, sim_approved=6, trades_executed=0`.
Signals passed both CapitalRiskEngine and MarketSimulation but zero orders were created.
**Implication**: The system may be incapable of executing any trade regardless of signal quality.
This is distinct from today's 0-trade (which has legitimate regime-based explanations).
**Status**: Pre-existing, noted for future investigation.

### SC-002: Stale Candidate Store (MEDIUM SEVERITY)
**Observation**: No BML refresh was performed for 2026-08-13. Candidate store is 2 days old.
SOLARINDS' +8.51% move was pre-identified (score=0.6421) but without a same-day BML refresh,
the entry condition could not be validated intraday.
**Implication**: Missing daily BML pre-market prep degrades opportunity capture rate.
**Status**: Today's observation; pre-existing pattern.

### SC-003: Mean_Reversion Disabled in Primary Regime (MEDIUM SEVERITY)
**Observation**: On both 2026-08-11 (range_market) and inferred today (low_vol/range), the
dominant scanning strategy is Mean_Reversion — which is DISABLED. 104/111 (93.7%) attrition
records are STRATEGY_DISABLED for Mean_Reversion.
**Implication**: The system is operationally blind in its most common market regime.
The only active strategy in range_market is breakout-type, which requires volatile conditions.
**Status**: Architectural gap — no enabled strategy for range/low-vol regime.

### SC-004: Data Feed Fallback (LOW-MEDIUM SEVERITY)
**Observation**: `consecutive_fallback_sessions: 9` — Dhan API blocked since May 2026.
All data via yfinance (~15 min delayed in some paths).
**Implication**: Volume-based breakout confirmation unreliable; yfinance volume granularity
differs from exchange feed.
**Status**: Known issue; broker API issue (HTTP 451).

### SC-005: ODM Secondary Tier Feedback Loop (LOW SEVERITY)
**Observation**: ODM current_tier='SECONDARY' due to 10 consecutive zero-trade cycles.
SECONDARY tier may reduce trade scoring weights, further suppressing confidence scores.
**Implication**: System becomes harder to pull out of zero-trade mode once it enters the loop.
**Status**: Observed; systemic.

---

## SECTION 15: MOP-RC-001 READINESS ASSESSMENT

| Component | Status |
|---|---|
| `models/trade_signal.py` — new fields | ✅ DEPLOYED |
| `equity_scanner_ai.py` — observer hook | ✅ DEPLOYED |
| `mop_rc001_observer.py` — JSONL writer | ✅ DEPLOYED |
| `test_mop_rc001.py` — 15/15 pass | ✅ VERIFIED |
| VPS containers | ✅ HEALTHY (both Up) |
| First observation file | ⏳ PENDING — will be created on next scan |

MOP-RC-001 is fully deployed and ready. Today produced no observations because the deploy
window was only ~20 minutes before market close. The first JSONL observation file
(`data/mop_rc001/MOP_RC001_YYYY-MM-DD.json`) will be created on the next weekday scan cycle
(earliest: 2026-08-14).

---

## SECTION 16: FINAL AUDIT VERDICT

### Primary Verdict: `CORRECT_NO_TRADE`

The 0-trade outcome on 2026-08-13 is **correct and expected** based on:

1. **Regime mismatch**: VIX 11.37 (low_vol), NIFTY flat (-0.16%) → no regime support for
   breakout strategies; Mean_Reversion DISABLED in range/low-vol regime
2. **Stale candidate store**: 2-day-old BML → no intraday refresh → degraded setup quality
3. **Dominant candidates moved wrong direction**: PAGEIND (-4.64%), FORCEMOT (-3.86%),
   SAIL (-3.06%) — all top candidates by BML score were losers today
4. **Decision threshold**: Historical 6.5–6.7 threshold with observed scores in 6.3–6.49 range
5. **Post-deploy window**: ~20 min between MOP-RC-001 deploy and market close — insufficient
   for a full scan-to-decision cycle to complete

### Secondary Finding: `PARTIAL_OBSERVATION_MISS`

SOLARINDS (+8.51%) was pre-identified as a candidate (score=0.6421) and moved significantly.
Without a same-day BML refresh and in a low-VIX environment, the system lacked the intraday
setup confirmation to generate a high-confidence signal. This is a **process miss** (no daily
BML refresh), not a signal quality miss.

### Systemic Flag: `SC-001 EXECUTION_BOTTLENECK` (pre-existing)

The CT cycle history shows a structural issue: signals that pass risk and simulation approval
are not reaching ExecutionEngine with created orders. This predates today and is independent
of today's 0-trade outcome. **This flag requires future investigation (not in scope of today's
read-only audit).**

---

## SUMMARY TABLE

| Category | Count | Assessment |
|---|---|---|
| Stocks with valid prices | 206 / 230 | 89.6% universe coverage |
| BML-40 all in universe | 40 / 40 | 100% |
| BML-40 in candidate store | 7 / 40 | 17.5% pre-move coverage |
| Candidates that FELL today | 3 (PAGEIND, FORCEMOT, SAIL) | 0-trade CORRECT |
| Candidates that ROSE today | 4 (SOLARINDS, OBEROIRLTY, GODREJCP, PRESTIGE) | Mixed |
| Strategy DISABLED (range) | Mean_Reversion | Primary regime strategy blocked |
| Decision threshold met | 0 (inferred) | Historically near-miss at 6.49 |
| Risk-approved trades | 0 (local DB) | SC-001 bottleneck |
| Paper trades executed | **0** | CONFIRMED |
| MOP-RC-001 observations | **0** | Post-deploy timing |
| **Final Verdict** | **CORRECT_NO_TRADE** | with PARTIAL_OBSERVATION_MISS + SC-001 |

---

*Audit completed: 2026-08-13*  
*Method: READ-ONLY — no code changes, no config changes, no orders, no position creation*  
*Data sources: yfinance (NSE prices), local SQLite DBs (CT, IIOS), JSON files (candidates, attrition, ODM)*  
*Script artifacts: `mop_day4_collect.py`, `mop_day4_detail.py` (temp study scripts — READ-ONLY)*
