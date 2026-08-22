# REPLAY FINDINGS v1

**Source:** `historical_replay.py` — 5-year NSE replay (2021-01-01 to 2025-12-31)
**Date run:** 2026-06-16
**Database:** `data/replay.db`

## Summary statistics

```
Trading days simulated:    1,235
Signals generated:        57,037
Opportunities created:    12,040
Theme phase transitions:   5,109
```

## Readiness gate outcomes (replay evidence)

| Gate | Result | Note |
|------|--------|------|
| C-Ready-1: signal_births >= 100 | PASS | 57,037 |
| C-Ready-2: all sectors 30+ FULL rows | PASS | 992–1,234 rows per sector |
| C-Ready-3: theme_phase_history >= 5 | PASS | 5,109 transitions, all 5 phases present |
| C-Ready-4: archetypes in frequency bounds | PARTIAL | DNA_1B_DELIVERY_EXPANSION=0 (BHAV skipped); DNA_1B_LOW_NOISE_STRENGTH=0.9/day (floor=1) |
| C-Ready-5: lifecycle diversity | PASS (with note) | INVALID=99.2% at simulation end-date — expected; all 4 states observed during simulation; 3 invalidation reasons active |

---

## Finding RF-1

**Metric:** TTL_EXHAUSTED = 48% of all invalidations (5,736 / 11,948)

**Observation:** Nearly half of all opportunity closures are caused by hitting the TTL ceiling before either the activation threshold (NEVER_MATURED) or the expected-move threshold (EC_EXHAUSTED) fires.

**Hypothesis:** 1A TTL=10 and 1B TTL=18 may be slightly aggressive. Opportunities may need a few more days to complete their move.

**Candidate experiment (do not run yet):**
- 1A TTL: 10 → 12
- 1B TTL: 18 → 21
- Re-run replay; compare TTL_EXHAUSTED% and EC_EXHAUSTED%

**Status:** Observe. No change. Requires live data comparison before any threshold adjustment.

---

## Finding RF-2

**Metric:** NEVER_MATURED = 31% of all invalidations (3,719 / 11,948)

**Observation:** 31% of opportunities that entered DISCOVERED state never accumulated enough confirming signals to reach ACTIVE before their `discovered_expires_at` deadline.

**Hypothesis:** Activation threshold (ACTIVE_THRESHOLD=6.0, requiring 3 confirming signals at 2.5pts each = 7.5pts) may be slightly strict. Or the `discovered_expires_at` window (floor(birth_ttl × 0.5) trading days) may be too short for 1A signals (5 days to get 3 confirms).

**Important constraint:** Cannot lower threshold without Phase D counterfactual data. Need to know whether NEVER_MATURED opportunities would have become profitable if activated. Lowering the threshold without that evidence could increase noise rather than returns.

**Status:** Observe. No change. Requires Phase D counterfactual analysis.

---

## Finding RF-3

**Metric:** Avg signals per opportunity = 4.74 (target range: 1.3–2.5)

**Observation:** Higher than the design expectation. Primary driver is `DNA_1B_SECTOR_PRE_BKT` at 18.9 signals/day — the highest-volume archetype. During broad sector rallies, this archetype fires on many stocks simultaneously, and subsequent signals on the same stock within the merge window attach to the existing opportunity rather than creating a new one.

**Hypothesis:** Merge window (TTL × 0.75 trading days) may be permissive during sector-wide trending conditions, causing signal accumulation on already-active opportunities.

**Alternative hypothesis:** The higher merge rate is correct behavior — a stock that continues generating signals over 10+ days is genuinely more confirmed than one that fires once. This is a feature, not a bug.

**Status:** Observe. No change. Compare against live data. If live data shows similar avg signals/opp, the behavior is consistent with real market conditions.

---

## Finding RF-4

**Metric:** `DNA_1B_SECTOR_PRE_BKT` = 18.9/day (40% of all signals)

**Observation:** Single dominant archetype. Still within the 1–20/day bounds defined in `check_phase_c_ready.py`, but close to the upper limit and disproportionate relative to other archetypes.

**Hypothesis:** The archetype fires across all sector members simultaneously when breadth >= 50%. In a 230-stock universe across 12 sectors, on any trending day this can fire 10–20 times. The breadth threshold (50%) may be calibrated for a smaller universe.

**Status:** Informational. Not a gate failure. Watch in live data. If live data shows SECTOR_PRE_BKT still dominates at >35% of signals, consider raising breadth threshold from 50% to 60%.

---

## What the replay did NOT find

- No structural defect (architecture survived 1,235 days of replay)
- No schema issues
- No state machine violations
- No symbol concentration (max symbol = 0.7% of signals)
- No sector concentration (max sector = 14.3% of opportunities)
- No missing lifecycle states (DISCOVERED, ACTIVE, WATCHING, INVALID all observed)
- No collapsed theme phase distribution (all 5 phases present, none >30%)

---

## Governance note

These are **calibration candidates**, not defects. No code changes are authorized based on replay findings alone.

The correct sequence:
1. Collect live data (Track B, ongoing)
2. When live readiness gates pass, compare live distributions to this baseline
3. If live distributions match replay, calibration candidates remain hypotheses
4. If live distributions diverge significantly, investigate before Phase C

**Freeze date:** 2026-06-16
**Next review:** When `check_phase_c_ready.py` returns first READY on `data/market_behavior.db`
