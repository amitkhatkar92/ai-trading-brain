# MOVER_DISCOVERY_RESEARCH_CANDIDATES
**Date:** 2026-08-14  
**Source:** MOVER_DISCOVERY_AUDIT_002

These are RESEARCH CANDIDATES only. No production changes have been made.
All candidates require further validation before any implementation.

---

## P0 — Critical Discovery Failures

### RC-MD-001 (P0): Pre-Breakout Accumulation Detection Gap
**Finding:** 81.0% of ≥2% movers are never generated as signals.
The scanner has no mechanism to detect stocks in a quiet accumulation phase
before their move begins. The bucket-based scoring rewards stocks already
showing breakout/oversold patterns, not those about to show them.
**Evidence class:** PROVEN (from data, confirmed by code trace)
**What to test:** Add a "preparation phase" score component that detects:
- Low ATR (consolidation) + increasing volume trend
- Relative strength improving vs universe (RS percentile improving over 3-5 days)
- Price forming higher lows without breaking resistance yet
**Do NOT implement:** Do not change the scanner threshold until the above
combinations are validated in OOS over 2+ years.

### RC-MD-002 (P0): Phase D Scanner Has No Early Sector Rotation Signal
**Finding:** Sector context (sector_leaders) is loaded only at intraday scan
time, AFTER the Phase D candidate pool is fixed.
Sector rotation signals visible at end-of-day (16:45) are not used to
prioritize candidates.
**Evidence class:** PROVEN (from code trace)
**What to test:** Compute sector return and breadth at 16:45 Phase D scan
and use as a scoring bonus for candidates from outperforming sectors.
**Expected impact (from research):** -0.013 lift delta in historical test.
**Do NOT implement:** This requires changes to market_scanner.py — protected module.
Research candidate only.

---

## P1 — Promising Research Candidates

### RC-MD-003 (P1): Relative Strength Percentile as Early Discovery Signal
**Finding:** Stocks in top 90th percentile of 5d momentum within the universe
show score_FULL_DOWN is the best-performing combination in walk-forward OOS.
**Evidence class:** POSSIBLE (walk-forward validated)
**Formula:** rs_pct_5d + vol_ratio + sector_breadth (score_K / score_FULL_UP)
**OOS recall at pool=20:** See mover_discovery_combination_analysis.csv for detail
**Do NOT implement:** Research candidate only.

### RC-MD-004 (P1): Volume Expansion as Magnitude Predictor
**Finding:** Top magnitude predictors from pre-move analysis:
  - atr_pct: spearman_r=0.2440, mag_ratio=2.14x
  - hv_20: spearman_r=0.2250, mag_ratio=2.01x
  - mom_accel: spearman_r=-0.0767, mag_ratio=0.80x
**Evidence class:** POSSIBLE (in-sample, needs OOS validation)
**What it means:** High atr_pct and vol_expansion BEFORE a move predict larger
subsequent moves. This could enable magnitude-ranked selection.
**Do NOT implement:** Needs OOS validation and signal pipeline integration design.

### RC-MD-005 (P1): DOWN Discovery Gap — Structural Architecture Issue
**Finding:** All historical signals (57,037) are LONG. DOWN discovery requires
completely different pipeline logic. The only DOWN setup is HighRSIShort
(RSI>65-70), which misses:
- Sector-led breakdown (sector turns negative before individual stocks)
- Momentum exhaustion (extended rise, then reversal)
- Volume divergence (price rising on falling volume)
**Evidence class:** PROVEN (from data: all signals LONG, code trace confirms limited SHORT setups)
**What to test:** score_DOWN_B (negative momentum + sector + volume) shows
OOS recall for DOWN movers. Compare with current HighRSIShort recall.
**Do NOT implement:** Major pipeline change. Research only.

---

## P2 — Secondary Improvements

### RC-MD-006 (P2): MLS Knowledge Pipeline Activation
**Finding:** The 4-component MLS pipeline (MarketObserver, PopulationClassifier,
DNADiscoveryEngine, DNAConsensusEngine) is not scheduled. library.json is static.
If MLS had been operational, institutional DNA features COULD have improved
discovery for ~46% of missed movers (those in TRENDING_UP regime with momentum).
**Evidence class:** POSSIBLE (not testable without running MLS on historical data)
**Determination:** POSSIBLE — historical MLS output not available for direct test.
**Do NOT activate:** Schedule change to orchestrator. Out of scope for this audit.

### RC-MD-007 (P2): Range Expansion Early Identification
**Finding:** range_expansion (today's ATR / 20d avg ATR) shows meaningful
correlation with future move magnitude.
**Evidence class:** POSSIBLE
**Formula to test:** Add range_expansion to Phase D scoring (volatility expansion bonus)
**Do NOT implement:** Test first with historical simulation.

### RC-MD-008 (P2): 52-Week High Breakout Context
**Finding:** dist_52w_high features (how far below 52-week high) provide context
that the current 20d resistance lookback misses.
A stock at 52-week high breakout but with a resistance level set >20 days ago
does NOT get BREAKOUT bucket treatment.
**Evidence class:** POSSIBLE
**Do NOT implement:** Requires scanner lookback change.

---

## P3 — Insufficient Evidence

### RC-MD-009 (P3): Intraday Volume Pattern (Not Available)
No intraday data exists in replay.db. Cannot validate intraday volume patterns.

### RC-MD-010 (P3): News/Event Catalyst
No historical event/news data exists in replay.db. Cannot validate.

### RC-MD-011 (P3): Gap-and-Continue Pattern
Gap detection (gap_pct) feature is available but shows limited predictive value
in daily data. Needs intraday context to validate.

---

## Priority Order for Next Audit

1. RC-MD-001: Pre-breakout accumulation (P0) — validate score_FULL_UP OOS
2. RC-MD-005: DOWN discovery (P0) — validate score_DOWN_B OOS
3. RC-MD-003: RS percentile scoring (P1) — validate score_K OOS
4. RC-MD-002: Early sector rotation (P1) — design Phase D sector scoring
5. RC-MD-004: Magnitude prediction (P1) — validate ATR-based magnitude model

---

## What Should NOT Change

1. The debate/decision engine — Model A outperforms Model B (raw knowledge).
   The 5-agent debate adds value.
2. The 6.5 debate threshold — this is calibrated.
3. The sector cap (20%) — prevents over-concentration.
4. The MIN_PREPARED_SCORE = 0.55 — should be LOWERED (not removed) or
   the scoring formula improved before raising the floor.
