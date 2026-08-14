# MOVER DISCOVERY V3 — Design Document
**Date:** 2026-08-14
**Based on:** MOVER_DISCOVERY_AUDIT_002

---

## Architectural Change

### Current Production Design
```
Hard bucket gates → composite score → MIN_PREPARED_SCORE=0.55 floor → cap=120
```

Key bottlenecks (AUDIT_002 confirmed):
- `VOLUME_EXPANSION_MIN=1.8` rejects 92.8% of pre-breakout movers
- `BREAKOUT_PROXIMITY_PCT=0.02` rejects 88.4% (too far from resistance)
- RSI 45–55 zone has no bucket — 30.7% of missed movers land here

### V3 Research Design
```
Broad universe (all 230 symbols)
    │
    ├── UP_DISCOVERY_SCORE   (5 features, percentile-ranked)
    │   atr_pct × 0.25 + mom_5d × 0.20 + rs_pct_5d × 0.20
    │   + vol_ratio × 0.20 + mom_accel × 0.15
    │
    └── DOWN_DISCOVERY_SCORE (5 features, percentile-ranked)
        neg_mom_5d × 0.30 + neg_mom_accel × 0.25 + vol_expansion × 0.20
        + atr_pct × 0.15 + rsi_overbought × 0.10
```

V3 produces two separate ranked lists (top 20 each) per day.
**No hard gates on volume or resistance proximity.**
Volume expansion is a continuous rank score, not a pass/fail threshold.

---

## Feature Justification

| Feature | Used in | AUDIT_002 Lift | Direction |
|---------|---------|----------------|-----------|
| atr_pct | UP + DOWN | 1.21× | Higher ATR → more movement potential |
| mom_5d | UP (direct), DOWN (inverted) | 1.21× | Trend persistence / reversal |
| rs_pct_5d | UP | 1.13× | Universe-relative momentum |
| vol_ratio | UP | 1.09× | Accumulation signal |
| mom_accel | DOWN (primary) | 1.24× | Deceleration forecasts reversal |
| vol_expansion | DOWN | 1.26× (in DOWN_C) | Volume confirmation of reversal |
| neg_mom_5d | DOWN | 1.22× | Negative trend persistence |

## Sector Decision
Sector context: **disabled for UP, disabled for DOWN by default**

AUDIT_002 sector lift_delta = −0.013 (i.e., sector made discovery worse)
Sector can be enabled for testing via `use_sector_for_down=True`.

Sector test result (pool=20):
  Without sector: lift = 1.3224
  With sector:    lift = 1.2718
  Lift delta:     -0.0506
  Verdict:        SECTOR_NO_BENEFIT

---

## Magnitude Estimation

Legacy constant (`expected_move_pct = 8.0`):
- Source: `oios/data/sector_conviction_writer.py` (hardcoded, MAS Section 5)
- Historical status: ALL 57,037 signals in replay.db have this value
- Predictive power: spearman_r ≈ 0.0 (confirmed in AUDIT_002)

V3 approach: use `atr_pct` as magnitude signal
- atr_pct spearman_r with |ret_5d| = 0.244 (AUDIT_002)
- atr_pct magnitude_ratio = 2.14× (high ATR stocks move 2.14× more)
- NOT used in V3 scoring itself (avoids regime bias), reported as metadata

---

## OOS Separation

**Train:** 2021-01-01 to 2023-12-31 (weights/design decisions made here)
**OOS:**   2024-01-01 to 2025-12-30 (evaluation only, no tuning)

In-sample UP lift:  1.8176
OOS UP lift:        1.5371
In-sample DOWN lift: 1.3221
OOS DOWN lift:       1.3228

---

## Shadow Mode

V3 runs in shadow mode only.
- `MOVER_DISCOVERY_V3_ENABLED = False`
- `MOVER_DISCOVERY_V3_SHADOW_MODE = True`
- Shadow log: `data/mover_discovery_v3_shadow.jsonl`
- Production scanner output: unchanged
- No trades generated from V3
- No writes to CandidateStore
