# MOVER DISCOVERY V3 — Architecture Document
**Date:** 2026-08-14
**Status:** RESEARCH / SHADOW MODE — NOT production ready

---

## Data Flow

```
┌─────────────────────────────────────────────────────────┐
│                   Market Data (at 16:45 IST)            │
│             230-symbol OHLCV, 35d lookback              │
└──────────────────────┬──────────────────────────────────┘
                       │
          ┌────────────▼────────────┐
          │  compute_v3_features()  │  PIT-safe: backward-looking only
          │  atr, momentum, volume  │  No future data allowed
          │  RSI, vol_expansion     │  check_leakage() verified
          └────────────┬────────────┘
                       │
          ┌────────────▼────────────┐
          │     score_universe()    │  Percentile ranking per date
          │  UP_SCORE / DOWN_SCORE  │  No hard gates
          └────────┬────────┬───────┘
                   │        │
         ┌─────────▼─┐   ┌──▼──────────┐
         │  UP Pool  │   │  DOWN Pool  │
         │   Top 20  │   │   Top 20    │
         └─────────┬─┘   └──┬──────────┘
                   │        │
          ┌────────▼────────▼────────┐
          │   SHADOW LOG (JSONL)     │  Append-only, research only
          │   No CandidateStore      │  No trades
          │   No OrderManager        │  No signal_births
          └──────────────────────────┘
```

## Component Map

| Component | File | Purpose |
|-----------|------|---------|
| V3Config | mover_discovery_v3.py | All V3 settings, isolated |
| V3UpWeights | mover_discovery_v3.py | Configurable UP feature weights |
| V3DownWeights | mover_discovery_v3.py | Configurable DOWN feature weights |
| compute_v3_features() | mover_discovery_v3.py | Per-symbol PIT-safe features |
| score_universe() | mover_discovery_v3.py | Cross-section percentile scoring |
| select_candidates() | mover_discovery_v3.py | Top-N with deterministic tie-break |
| run_shadow_scan() | mover_discovery_v3.py | Shadow mode entry point |
| check_leakage() | mover_discovery_v3.py | Leakage guard |
| FORBIDDEN_FUTURE_KEYS | mover_discovery_v3.py | Future-data key list |

## Safety Guarantees

1. `V3Config.enabled = False` — hard disabled
2. `V3Config.shadow_mode = True` — enforced in run_shadow_scan()
3. `validate()` raises if `enabled=True AND shadow_mode=False`
4. Shadow log is append-only JSONL, never read by production
5. No imports of CandidateStore, OrderManager, DecisionEngine
6. No writes to any production data file

## Walk-Forward OOS Results

| Fold | UP Lift | UP Recall | DOWN Lift | DOWN Recall |
|------|---------|-----------|-----------|-------------|
| OOS_2023-01_2023-12 | 1.979 | 0.193 | 1.452 | 0.141 |
| OOS_2024-01_2024-12 | 1.568 | 0.155 | 1.415 | 0.139 |
| OOS_2025-01_2025-12 | 1.505 | 0.148 | 1.230 | 0.121 |

**OOS TARGET (GO criterion):** OOS UP lift ≥ 1.10 AND DOWN lift ≥ 1.10

Actual OOS UP lift:   1.5371
Actual OOS DOWN lift: 1.3228

## Leakage Status

Violations found: 0
CLEAN — all features are PIT-safe
