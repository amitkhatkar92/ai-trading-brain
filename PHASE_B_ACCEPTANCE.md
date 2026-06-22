# Phase B Acceptance Checklist

**Status:** PENDING CERTIFICATION  
**Date created:** 2026-06-16  
**Spec authority:** MAS_v1.2.md (FROZEN)

Phase B certification requires every item below to be marked PASS by the forensic
audit script (`phase_b_audit.py`) with zero FAIL before Phase C may begin.

---

## B1 — Schema

- [ ] `sector_conviction_daily` table exists with correct schema
- [ ] `theme_phase_history` table exists with correct schema
- [ ] Both tables have required indexes
- [ ] Neither table existed at end of Phase A (Phase A audit confirmed A10 pass)

---

## B2 — Layer 1B Acceptance

- [ ] `DNA_1B_QUIET_ACCUMULATION` fires on correct input
- [ ] `DNA_1B_DELIVERY_EXPANSION` fires when delivery % is rising
- [ ] `DNA_1B_LOW_NOISE_STRENGTH` fires on tight-range strength build
- [ ] `DNA_1B_SECTOR_PRE_BKT` fires on pre-breakout sector setup
- [ ] Layer 1B scanner produces zero DB writes (`run_scan` purity test)
- [ ] All 1B signals have `signal_type = "1B"`
- [ ] All 1B signals have `expected_ttl_days = 18` (Phase B default per MAS Section 5)
- [ ] Signals below MIN_WRITE_THRESHOLD (4.0) are NOT written

---

## B3 — Delivery Expansion Audit

- [ ] `bhav_daily` table is populated (BHAV pipeline operational)
- [ ] `delivery_pct` column present and non-null for EQ-series rows
- [ ] `DNA_1B_DELIVERY_EXPANSION` reads from `bhav_daily` (not from `ohlcv_daily`)
- [ ] Delivery Expansion archetype skips symbol when BHAV data unavailable (graceful degradation)
- [ ] No BHAV data gap causes scanner crash

---

## B4 — sector_conviction_daily Population

- [ ] `run_sector_conviction(conn, sector, trade_date)` writes one row per sector per date
- [ ] `participation_rate_1d` computed using weighted purity scores
- [ ] `participation_rate_5d` computed using weighted purity scores
- [ ] `participation_expansion` = participation_rate_5d today minus participation_rate_5d 5 days ago
- [ ] Data quality = "PARTIAL" when stocks_with_data / stocks_total < 0.80
- [ ] Layer 1.5 outputs suppressed (not written) for PARTIAL sectors

---

## B5 — Consensus Shift

- [ ] `consensus_score` populated in `sector_conviction_daily`
- [ ] `rs_vs_market_20d` populated
- [ ] `volume_trend_10d` populated
- [ ] `capital_flow_score` = 0.5 (neutral) when `capital_flow_data_quality = "UNAVAILABLE"`
- [ ] `sector_conviction_score` = 0.40 × capital_flow_score + 0.60 × consensus_score
- [ ] When capital_flow_data_quality = "UNAVAILABLE": weight rescaled to pure consensus (1.0×)

---

## B6 — Theme Phase Engine

- [ ] Theme Phase Engine requires ≥ 30 days of `sector_conviction_daily` history before activating
- [ ] EMERGENCE detected: participation_rate_5d 30–50%, week-over-week delta > 0
- [ ] ACCELERATION detected: participation_rate_5d 50–65%, delta still positive
- [ ] CONSENSUS detected: participation_rate_5d 65–80%, delta flat or decelerating
- [ ] CROWDING detected: participation_rate_5d > 80% OR (high participation + volume declining)
- [ ] EXHAUSTION detected: participation declining from peak + volume asymmetric to downside
- [ ] On phase transition: old record in `theme_phase_history` receives `exited_at` and `duration_trading_days`
- [ ] New phase record in `theme_phase_history` has `exited_at = NULL`
- [ ] `data_quality = "PARTIAL"` rows in `sector_conviction_daily` do NOT trigger phase transitions

---

## B-Audit-01 — Sector Coverage Integrity

- [ ] No sector in `universe_stocks` has fewer than 8 active stocks
- [ ] Every sector represented in `sector_conviction_daily` maps to a valid sector in `universe_stocks`
- [ ] Sector counts are consistent between `universe_stocks` and `universe_230.py`

---

## Audit Acceptance (Architecture Integrity)

- [ ] No modifications to Phase A0 or Phase A tables
- [ ] No modifications to the state machine, repository, or opportunity service
- [ ] No new root entities created outside the MAS specification
- [ ] `phase_b_audit.py` reports 0 FAIL before Phase C begins
- [ ] Full test suite (48 Phase A + all Phase B tests) passes with 0 failures

---

## Phase B Exit Condition (per MAS Section 7)

- [ ] `sector_conviction_daily` has 30+ days of data
- [ ] `theme_phase_history` has ≥ 5 phase transition records

Phase C may not begin until both exit conditions are satisfied by real market data.
