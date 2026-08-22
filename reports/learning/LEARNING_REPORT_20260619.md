# LEARNING_ENGINE_001 — Learning Report

**Run ID:** `20260619-0944`  
**Generated:** 2026-06-19 09:44 UTC  
**Databases:** `C:\Users\UCIC\OneDrive\Desktop\ai_trading_brain\data/`  
**Recommendations stored:** 62 new

> ⚠️ SAFETY NOTICE: All recommendations below require **human approval**
> before implementation. This engine NEVER modifies live trading code.

---
## Executive Summary

| Metric | Value |
|--------|-------|
| Total filters analysed | 32 |
| Positive edges (filter works) | 6 |
| Negative edges (filter hurts) | 10 |
| Neutral | 0 |
| Insufficient data | 16 |
| Strong positive signals | 1 |
| Strongest signal | `NEWS_EARNINGS` (65.3%, edge=+1.51) |
| Weakest signal | `LOW_DECISION_SCORE` (0.0%, edge=-2.92) |
| Pending recommendations (all time) | 62 |
| Approved (awaiting implementation) | 0 |
| Implemented | 0 |

---
## Priority Recommendations

These are sorted by priority (1=critical) then confidence.
> All require explicit human approval before any change is made.

### P1 — Critical (Remove or Investigate)
| Rec ID | Type | Target | Accuracy | Confidence | Suggestion |
|--------|------|--------|----------|------------|------------|
| REC-020 | REMOVE_FILTER | `TIER_MEDIUM` | 37.5% (48n) | MEDIUM | Consider disabling TIER_MEDIUM. It is blocking more winners than losers (37.5% a... |
| REC-028 | REMOVE_FILTER | `LOW_CONVICTION` | 0.0% (23n) | MEDIUM | Consider disabling LOW_CONVICTION. It is blocking more winners than losers (0.0%... |
| REC-029 | REMOVE_FILTER | `LOW_QUALITY_SCORE` | 0.0% (28n) | MEDIUM | Consider disabling LOW_QUALITY_SCORE. It is blocking more winners than losers (0... |
| REC-030 | REMOVE_FILTER | `LOW_DECISION_SCORE` | 0.0% (34n) | MEDIUM | Consider disabling LOW_DECISION_SCORE. It is blocking more winners than losers (... |
| REC-018 | REMOVE_FILTER | `NEWS_UPGRADE_DOWNGRADE` | 44.4% (45n) | LOW | Consider disabling NEWS_UPGRADE_DOWNGRADE. It is blocking more winners than lose... |
| PAT-007 | DECREASE_WEIGHT | `LOW + MEDIUM` | 10.0% (10n) | LOW | Pattern 'LOW + MEDIUM' achieves only 10.0% WR (-40.0pp below baseline). Consider... |
| PAT-008 | DECREASE_WEIGHT | `NORMAL + BULL` | 30.0% (30n) | MEDIUM | Pattern 'NORMAL + BULL' achieves only 30.0% WR (-20.0pp below baseline). Conside... |
| PAT-014 | DECREASE_WEIGHT | `UPGRADE_DOWNGRADE + HIGH_VOL` | 28.6% (14n) | LOW | Pattern 'UPGRADE_DOWNGRADE + HIGH_VOL' achieves only 28.6% WR (-21.4pp below bas... |
| PAT-030 | DECREASE_WEIGHT | `PROTECTIVE_PUT + RANGING` | 6.7% (30n) | MEDIUM | Pattern 'PROTECTIVE_PUT + RANGING' achieves only 6.7% WR (-43.3pp below baseline... |
| PAT-031 | DECREASE_WEIGHT | `PROTECTIVE_PUT + MEDIUM` | 10.7% (28n) | MEDIUM | Pattern 'PROTECTIVE_PUT + MEDIUM' achieves only 10.7% WR (-39.3pp below baseline... |
| PAT-032 | DECREASE_WEIGHT | `LONG_STRANGLE + MEDIUM` | 22.4% (49n) | MEDIUM | Pattern 'LONG_STRANGLE + MEDIUM' achieves only 22.4% WR (-27.6pp below baseline)... |

### P2 — High (Weight Adjustments)
| Rec ID | Type | Target | Accuracy | Confidence | Suggestion |
|--------|------|--------|----------|------------|------------|
| REC-017 | DECREASE_WEIGHT | `NEWS_RBI_POLICY` | 44.4% (18n) | LOW | Reduce the penalty/weight of NEWS_RBI_POLICY by ~11%. Current accuracy 44.4% sug... |
| REC-024 | DECREASE_WEIGHT | `TIER_LOW` | 11.8% (17n) | LOW | Reduce the penalty/weight of TIER_LOW by ~40%. Current accuracy 11.8% suggests i... |
| REC-025 | DECREASE_WEIGHT | `MAX_POSITIONS` | 0.0% (12n) | LOW | Reduce the penalty/weight of MAX_POSITIONS by ~40%. Current accuracy 0.0% sugges... |
| REC-026 | DECREASE_WEIGHT | `LOW_SFT` | 0.0% (14n) | LOW | Reduce the penalty/weight of LOW_SFT by ~40%. Current accuracy 0.0% suggests it ... |
| REC-027 | DECREASE_WEIGHT | `CORRELATED_POSITION` | 0.0% (19n) | LOW | Reduce the penalty/weight of CORRELATED_POSITION by ~40%. Current accuracy 0.0% ... |
| PAT-001 | INCREASE_WEIGHT | `PREMIUM + HIGH` | 75.0% (36n) | MEDIUM | Pattern 'PREMIUM + HIGH' achieves 75.0% WR (+25.0pp above baseline). Consider bo... |
| PAT-002 | INCREASE_WEIGHT | `PREMIUM + BEAR` | 83.3% (12n) | LOW | Pattern 'PREMIUM + BEAR' achieves 83.3% WR (+33.3pp above baseline). Consider bo... |
| PAT-003 | INCREASE_WEIGHT | `HIGH_CONVICTION + HIGH_VOL` | 83.3% (12n) | LOW | Pattern 'HIGH_CONVICTION + HIGH_VOL' achieves 83.3% WR (+33.3pp above baseline).... |
| PAT-004 | INCREASE_WEIGHT | `PREMIUM + HIGH + BULL` | 81.8% (11n) | LOW | Pattern 'PREMIUM + HIGH + BULL' achieves 81.8% WR (+31.8pp above baseline). Cons... |
| PAT-005 | INCREASE_WEIGHT | `HIGH + HIGH` | 72.7% (22n) | MEDIUM | Pattern 'HIGH + HIGH' achieves 72.7% WR (+22.7pp above baseline). Consider boost... |
| PAT-010 | INCREASE_WEIGHT | `EARNINGS + BEAR` | 75.8% (33n) | MEDIUM | Pattern 'EARNINGS + BEAR' achieves 75.8% WR (+25.8pp above baseline). Consider b... |
| PAT-011 | INCREASE_WEIGHT | `EARNINGS + NEGATIVE` | 70.4% (27n) | MEDIUM | Pattern 'EARNINGS + NEGATIVE' achieves 70.4% WR (+20.4pp above baseline). Consid... |
| PAT-013 | INCREASE_WEIGHT | `EARNINGS + RANGING` | 70.0% (20n) | MEDIUM | Pattern 'EARNINGS + RANGING' achieves 70.0% WR (+20.0pp above baseline). Conside... |
| PAT-017 | INCREASE_WEIGHT | `HIGH_VOL_REGIME + MEDIUM` | 82.4% (51n) | HIGH | Pattern 'HIGH_VOL_REGIME + MEDIUM' achieves 82.4% WR (+32.4pp above baseline). C... |
| PAT-018 | INCREASE_WEIGHT | `LOW_DECISION_SCORE + BEAR` | 88.0% (25n) | MEDIUM | Pattern 'LOW_DECISION_SCORE + BEAR' achieves 88.0% WR (+38.0pp above baseline). ... |
| PAT-019 | INCREASE_WEIGHT | `LOW_SFT + MEDIUM` | 78.5% (65n) | HIGH | Pattern 'LOW_SFT + MEDIUM' achieves 78.5% WR (+28.5pp above baseline). Consider ... |
| PAT-020 | INCREASE_WEIGHT | `HIGH_VOL_REGIME + HIGH_VOL` | 88.9% (18n) | LOW | Pattern 'HIGH_VOL_REGIME + HIGH_VOL' achieves 88.9% WR (+38.9pp above baseline).... |
| PAT-021 | INCREASE_WEIGHT | `LOW_SFT + BULL` | 92.3% (13n) | LOW | Pattern 'LOW_SFT + BULL' achieves 92.3% WR (+42.3pp above baseline). Consider bo... |
| PAT-025 | INCREASE_WEIGHT | `SHORT_STRANGLE + RANGING` | 78.6% (131n) | HIGH | Pattern 'SHORT_STRANGLE + RANGING' achieves 78.6% WR (+28.6pp above baseline). C... |
| PAT-026 | INCREASE_WEIGHT | `SHORT_STRANGLE + MEDIUM` | 75.3% (146n) | HIGH | Pattern 'SHORT_STRANGLE + MEDIUM' achieves 75.3% WR (+25.3pp above baseline). Co... |
| PAT-027 | INCREASE_WEIGHT | `COVERED_CALL + RANGING` | 78.0% (109n) | HIGH | Pattern 'COVERED_CALL + RANGING' achieves 78.0% WR (+28.0pp above baseline). Con... |
| PAT-028 | INCREASE_WEIGHT | `IRON_CONDOR + RANGING` | 78.4% (97n) | HIGH | Pattern 'IRON_CONDOR + RANGING' achieves 78.4% WR (+28.4pp above baseline). Cons... |
| PAT-029 | INCREASE_WEIGHT | `COVERED_CALL + MEDIUM` | 76.4% (106n) | HIGH | Pattern 'COVERED_CALL + MEDIUM' achieves 76.4% WR (+26.4pp above baseline). Cons... |

### P3 — Medium (Increase Weight)
| Rec ID | Type | Target | Accuracy | Confidence | Suggestion |
|--------|------|--------|----------|------------|------------|
| REC-021 | INCREASE_WEIGHT | `NEWS_CORPORATE_ACTION` | 67.7% (31n) | MEDIUM | Increase influence/weight of NEWS_CORPORATE_ACTION by ~17%. It is reliably discr... |
| REC-022 | INCREASE_WEIGHT | `TIER_PREMIUM` | 69.6% (46n) | MEDIUM | Increase influence/weight of TIER_PREMIUM by ~19%. It is reliably discriminating... |
| REC-023 | INCREASE_WEIGHT | `NEWS_EARNINGS` | 65.3% (98n) | MEDIUM | Increase influence/weight of NEWS_EARNINGS by ~15%. It is reliably discriminatin... |

---
## Filter Edge Strength Ranking

All filters ranked by absolute edge score. Baseline = 50% (random).
Edge score ≈ z-score direction. Positive = filter works. Negative = filter hurts.

| Filter | Category | Accuracy | N | Edge Score | Strength | Action |
|--------|----------|----------|---|------------|----------|--------|
| `LOW_DECISION_SCORE` | REJECTION_FILTER | 0.0% | 34 | -2.92 | STRONG | Review — possible false rejections |
| `LOW_QUALITY_SCORE` | REJECTION_FILTER | 0.0% | 28 | -2.65 | STRONG | Review — possible false rejections |
| `LOW_CONVICTION` | REJECTION_FILTER | 0.0% | 23 | -2.40 | STRONG | Review — possible false rejections |
| `CORRELATED_POSITION` | REJECTION_FILTER | 0.0% | 19 | -2.18 | STRONG | Review — possible false rejections |
| `LOW_SFT` | REJECTION_FILTER | 0.0% | 14 | -1.87 | STRONG | Review — possible false rejections |
| `MAX_POSITIONS` | REJECTION_FILTER | 0.0% | 12 | -1.73 | STRONG | Review — possible false rejections |
| `TIER_LOW` | QUALITY_TIER | 11.8% | 17 | -1.57 | STRONG | Review — possible false rejections |
| `NEWS_EARNINGS` | NEWS_SIGNAL | 65.3% | 98 | +1.51 | MODERATE | Watch — moderate signal |
| `TIER_PREMIUM` | QUALITY_TIER | 69.6% | 46 | +1.33 | MODERATE | Watch — moderate signal |
| `NEWS_CORPORATE_ACTION` | NEWS_SIGNAL | 67.7% | 31 | +0.98 | MODERATE | Watch — moderate signal |
| `TIER_HIGH` | QUALITY_TIER | 64.1% | 39 | +0.88 | MODERATE | Watch — moderate signal |
| `TIER_MEDIUM` | QUALITY_TIER | 37.5% | 48 | -0.87 | MODERATE | Review — possible false rejections |
| `NEWS_INDEX_REBAL` | NEWS_SIGNAL | 72.7% | 11 | +0.75 | STRONG | Keep — strong signal |
| `NEWS_SECTOR_NEWS` | NEWS_SIGNAL | 60.0% | 40 | +0.63 | MODERATE | Watch — moderate signal |
| `NEWS_UPGRADE_DOWNGRADE` | NEWS_SIGNAL | 44.4% | 45 | -0.38 | MODERATE | Review — possible false rejections |
| `NEWS_RBI_POLICY` | NEWS_SIGNAL | 44.4% | 18 | -0.24 | MODERATE | Review — possible false rejections |
| `DAILY_LOSS_LIMIT` | REJECTION_FILTER | 0.0% | 6 | +0.00 | COLLECTING | Collect 4 more observations |
| `HIGH_VOL_REGIME` | REJECTION_FILTER | 0.0% | 9 | +0.00 | COLLECTING | Collect 1 more observations |
| `MANUAL_OVERRIDE` | REJECTION_FILTER | 0.0% | 7 | +0.00 | COLLECTING | Collect 3 more observations |
| `NEWS_BUDGET` | NEWS_SIGNAL | 40.0% | 5 | +0.00 | COLLECTING | Collect 5 more observations |

---
## Pattern Mining Results

Multi-factor combinations with highest and lowest win rates.

### Quality Patterns

**High-performing combinations:**

| Pattern | WR% | N | Direction |
|---------|-----|---|-----------|
| PREMIUM + HIGH | 75.0% | 36 | POSITIVE |
| PREMIUM + BEAR | 83.3% | 12 | POSITIVE |
| HIGH_CONVICTION + HIGH_VOL | 83.3% | 12 | POSITIVE |
| PREMIUM + HIGH + BULL | 81.8% | 11 | POSITIVE |
| HIGH + HIGH | 72.7% | 22 | POSITIVE |

**Underperforming combinations (consider avoiding):**

| Pattern | WR% | N | Direction |
|---------|-----|---|-----------|
| LOW + BULL | 0.0% | 7 | NEGATIVE |
| LOW + MEDIUM | 10.0% | 10 | NEGATIVE |
| NORMAL + BULL | 30.0% | 30 | NEGATIVE |

### News Patterns

**High-performing combinations:**

| Pattern | WR% | N | Direction |
|---------|-----|---|-----------|
| CORPORATE_ACTION + BEAR | 100.0% | 8 | POSITIVE |
| EARNINGS + BEAR | 75.8% | 33 | POSITIVE |
| EARNINGS + NEGATIVE | 70.4% | 27 | POSITIVE |
| INDEX_REBAL + NEGATIVE | 77.8% | 9 | POSITIVE |
| EARNINGS + RANGING | 70.0% | 20 | POSITIVE |

**Underperforming combinations (consider avoiding):**

| Pattern | WR% | N | Direction |
|---------|-----|---|-----------|
| UPGRADE_DOWNGRADE + HIGH_VOL | 28.6% | 14 | NEGATIVE |
| RBI_POLICY + NEUTRAL | 16.7% | 6 | NEGATIVE |
| UPGRADE_DOWNGRADE + POSITIVE | 44.4% | 27 | NEGATIVE |

### Rejection Patterns

**High-performing combinations:**

| Pattern | WR% | N | Direction |
|---------|-----|---|-----------|
| HIGH_VOL_REGIME + MEDIUM | 82.4% | 51 | POSITIVE |
| LOW_DECISION_SCORE + BEAR | 88.0% | 25 | POSITIVE |
| LOW_SFT + MEDIUM | 78.5% | 65 | POSITIVE |
| HIGH_VOL_REGIME + HIGH_VOL | 88.9% | 18 | POSITIVE |
| LOW_SFT + BULL | 92.3% | 13 | POSITIVE |

**Underperforming combinations (consider avoiding):**

| Pattern | WR% | N | Direction |
|---------|-----|---|-----------|
| CORRELATED_POSITION + HIGH | 45.7% | 35 | NEGATIVE |
| CORRELATED_POSITION + HIGH_VOL | 20.0% | 5 | NEGATIVE |
| CORRELATED_POSITION + RANGING | 36.4% | 11 | NEGATIVE |

### Options Patterns

**High-performing combinations:**

| Pattern | WR% | N | Direction |
|---------|-----|---|-----------|
| SHORT_STRANGLE + RANGING | 78.6% | 131 | POSITIVE |
| SHORT_STRANGLE + MEDIUM | 75.3% | 146 | POSITIVE |
| COVERED_CALL + RANGING | 78.0% | 109 | POSITIVE |
| IRON_CONDOR + RANGING | 78.4% | 97 | POSITIVE |
| COVERED_CALL + MEDIUM | 76.4% | 106 | POSITIVE |

**Underperforming combinations (consider avoiding):**

| Pattern | WR% | N | Direction |
|---------|-----|---|-----------|
| PROTECTIVE_PUT + RANGING | 6.7% | 30 | NEGATIVE |
| PROTECTIVE_PUT + MEDIUM | 10.7% | 28 | NEGATIVE |
| LONG_STRANGLE + MEDIUM | 22.4% | 49 | NEGATIVE |

---
## Recommendation Tracker Status

| Status | Count |
|--------|-------|
| PENDING | 62 |

**Oldest pending recommendations:**

| Rec ID | Target | Priority | Confidence | Generated |
|--------|--------|----------|------------|-----------|
| REC-020 | `TIER_MEDIUM` | 1 | MEDIUM | 2026-06-19 |
| REC-028 | `LOW_CONVICTION` | 1 | MEDIUM | 2026-06-19 |
| REC-029 | `LOW_QUALITY_SCORE` | 1 | MEDIUM | 2026-06-19 |
| REC-030 | `LOW_DECISION_SCORE` | 1 | MEDIUM | 2026-06-19 |
| REC-018 | `NEWS_UPGRADE_DOWNGRADE` | 1 | LOW | 2026-06-19 |
| PAT-007 | `LOW + MEDIUM` | 1 | LOW | 2026-06-19 |
| PAT-008 | `NORMAL + BULL` | 1 | MEDIUM | 2026-06-19 |
| PAT-014 | `UPGRADE_DOWNGRADE + HIGH_VOL` | 1 | LOW | 2026-06-19 |
| PAT-030 | `PROTECTIVE_PUT + RANGING` | 1 | MEDIUM | 2026-06-19 |
| PAT-031 | `PROTECTIVE_PUT + MEDIUM` | 1 | MEDIUM | 2026-06-19 |

---

*Generated by LEARNING_ENGINE_001.*  
*No live trading code was modified in the production of this report.*