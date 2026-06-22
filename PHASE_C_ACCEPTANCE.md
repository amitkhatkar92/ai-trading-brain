# Phase C Acceptance Checklist

**Status:** PENDING — requires live data prerequisites  
**Date created:** 2026-06-16  
**Spec authority:** MAS_v1.2.md (FROZEN)

Phase C certification requires every item below to be marked PASS by the forensic
audit script (`phase_c_audit.py`) with zero FAIL before Phase D may begin.

---

## SCOPE BOUNDARY

Phase C implements the **Edge Lifecycle Engine (ELE)** with the following components:

### In scope:
- **Sub-A:** RE Calculator (linear EC fallback, universal defaults)
- **Sub-B:** Maturity Engine (Temporal × Path × Conviction)
- **Sub-D:** State Machine Integration (DISCOVERED→ACTIVE→WATCHING, terminal enforcement)

### Explicitly deferred (NOT in Phase C):
- Sub-C: Velocity Attribution — requires 60+ days of RE trajectory data
- Sub-E: Transition Probability Model — requires ≥ 20 WATCHING→(ACTIVE|INVALID) sequences per (archetype, regime)
- Layer 6 Adaptive Intelligence — Phase D gate
- `archetype_outcome_distributions` population — activates only when `observation_count_weighted ≥ 20`
- `pending_adjustments` table writes — Phase D gate

**Phase C uses MAS Phase-0 simplified ELE:**
- `EC_path` = linear ratio (actual_move_pct / expected_move_pct), not percentile-based
- `D_time` = `0.5^(age / half_life)` with fixed regime priors (no learned distributions)
- `M_consensus_delta` = `sector_conviction_score_today / sector_conviction_score_at_birth`
  (falls back to 1.0 when birth score is 0 or NULL)
- Regime multipliers: fixed priors per MAS Section 5, Layer 5

---

## C0 — Data Prerequisites (must be satisfied before coding begins)

These are verified by `check_phase_c_ready.py`, not by the audit script.

- [ ] `signal_births` contains ≥ 100 real records
- [ ] `sector_conviction_daily` contains ≥ 30 FULL rows per sector (all 12 sectors)
- [ ] `theme_phase_history` contains ≥ 5 phase transition records
- [ ] `opportunities` shows lifecycle diversity: ≥ 2 distinct states, no single state > 90% of all opportunities
- [ ] Manual inspection of 1A/1B signals confirms plausible firing frequencies
  - Quiet Accumulation: 2–15 stocks/day expected (not 0, not 70)
  - Delivery Expansion: fires only when BHAV data rises meaningfully
  - No single symbol accounts for > 15% of all signal_births

---

## C1 — RE Calculator

- [ ] `compute_re(signal, age_trading_days, regime, current_price)` returns a value in `[0, E0]`
- [ ] `D_time = 0.5 ^ (age / half_life)` formula correct
- [ ] Half-life uses MAS regime multipliers (Bull/Range/Bear/Panic per signal type)
- [ ] `EC_path` = `actual_move_pct / expected_move_pct` (linear, capped at 1.0)
- [ ] `C_crowding` = 0.0 when volume < 3× 20-day average; rises above that
- [ ] RE = 0.0 when `EC_path ≥ 1.0` (edge fully consumed)
- [ ] RE never goes negative

---

## C2 — Maturity Engine

- [ ] Three independent dimensions computed: Temporal, Path, Conviction
- [ ] Temporal: age / effective_ttl → SEED/EMERGING/DEVELOPING/MATURE/LATE_STAGE
- [ ] Path: EC percentile (linear fallback in Phase C) → same 5 buckets
- [ ] Conviction: confirming_count → same 5 buckets
- [ ] `maturity_combined` = most conservative of the three dimensions
- [ ] Maturity written to `signal_births.maturity_combined` on each cycle update

---

## C3 — State Machine Integration

- [ ] ELE reads `position_size_pct` before ACTIVE classification
  - `position_size_pct ≥ 0.80` → forced to WATCHING (reason: POSITION_FULL)
  - `0.01–0.79` → ACTIVE allowed, flagged ADD_TO_POSITION
  - `0.0` → normal evaluation
- [ ] Terminal conditions enforced by ELE cycle:
  - `age_trading_days ≥ effective_ttl_days` → INVALID (TTL_EXHAUSTED)
  - `edge_consumed_pct ≥ 1.0` → INVALID (EC_EXHAUSTED)
  - Single-day volume > 3× 20d avg → INVALID (THESIS_INVALIDATED)
  - `age_trading_days > effective_ttl_days × 1.2` → INVALID (ZOMBIE_CAP)
  - `conflicting_count > confirming_count for 3 consecutive days` → INVALID (CONTRADICTED)
- [ ] `THESIS_INVALIDATED_WITH_POSITION` event emits before transition record (already verified in A0)
- [ ] All transitions written to `signal_state_transitions` (append-only)

---

## C4 — 5% Audit Paper Trade Override

- [ ] `hash(signal_id) % 20 == 0` selects 5% of INVALID signals for audit override
- [ ] These are routed to paper trading with `is_audit_trade = TRUE`
- [ ] Audit paper trade outcomes recorded separately in `decision_log`

---

## C5 — decision_log Completeness

- [ ] Every ENTER and PASS decision written to `decision_log`
- [ ] Every INVALID decision written to `decision_log` with reason code
- [ ] `price_at_decision` always populated (non-NULL)
- [ ] Nightly retroactive job populates `price_5d_later`, `price_10d_later`, `price_20d_later`
  (can be added in Phase D if Phase C has no scheduler yet)

---

## Audit Acceptance (Architecture Integrity)

- [ ] No modifications to Phase A0, Phase A, or Phase B tables
- [ ] No modifications to signal_writer, opportunity_service, or state_machine
- [ ] `archetype_outcome_distributions` remains empty (not populated until Phase D gate)
- [ ] `pending_adjustments` table not written by ELE
- [ ] `phase_c_audit.py` reports 0 FAIL before Phase D begins
- [ ] Full test suite (75 Phase A/B + all Phase C tests) passes with 0 failures

---

## Phase C Exit Condition (per MAS Section 7)

- [ ] ELE classifying all live opportunities every cycle
- [ ] Audit paper trades executing and recording outcomes
- [ ] `decision_log` has actionable records (PASS decisions accumulating)
