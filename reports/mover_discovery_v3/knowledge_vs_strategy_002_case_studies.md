# KNOWLEDGE_VS_STRATEGY_INCREMENTAL_VALUE_002 â€” Case Studies

## Top 10 False Rejections (Strategy REJECTED but strong opportunity)

Strategy rejected a Knowledge-selected candidate who subsequently moved strongly.

| Date | Symbol | Direction | gap_pct | Strategy Status | dir_adj_ret | mfe_pct | n_edg_pass |
|---|---|---|---|---|---|---|---|
| 2026-03-19 | OLECTRA.NS | UP | 0.86% | REJECT | 9.65% | 12.899680255795376 | 10 |
| 2026-03-30 | DEEPAKFERT.NS | UP | 5.39% | REJECT | 8.73% | 10.561056105610556 | 10 |
| 2026-04-07 | PRESTIGE.NS | UP | 6.37% | REJECT | 8.08% | 10.220112920382965 | 12 |
| 2026-04-02 | ADANIGREEN.NS | UP | 0.12% | REJECT | 7.61% | 8.259345794392537 | 10 |
| 2026-04-07 | GRSE.NS | UP | 6.28% | REJECT | 7.47% | 8.706025246171855 | 12 |
| 2026-03-17 | JPPOWER.NS | UP | 4.43% | REJECT | 7.30% | 11.802575107296144 | 8 |
| 2026-03-16 | NOCIL.NS | UP | 1.38% | REJECT | 6.48% | 7.7317698790766 | 10 |
| 2026-03-11 | STLTECH.NS | UP | 1.79% | REJECT | 5.38% | 7.949417567425732 | 10 |
| 2026-04-16 | SUZLON.NS | UP | 1.07% | REJECT | 5.33% | 6.945273631840809 | 15 |
| 2026-03-13 | ZYDUSWELL.NS | UP | 3.40% | REJECT | 5.31% | 8.70748299319728 | 10 |

## Top 10 Correct Rejections (Strategy REJECTED and candidate failed)

Strategy rejected a Knowledge-selected candidate who subsequently moved against direction.

| Date | Symbol | Direction | gap_pct | Strategy Status | dir_adj_ret | mae_pct |
|---|---|---|---|---|---|---|
| 2026-03-12 | STLTECH.NS | UP | 1.0754829715196257 | REJECT | -6.9209 | 8.135829516032667 |
| 2026-03-20 | MIDHANI.NS | UP | -0.7294640025372723 | REJECT | -6.803 | 7.389787503964484 |
| 2026-04-17 | CENTUM.NS | UP | 0.4959835321576733 | REJECT | -6.5807 | 7.254927385892119 |
| 2026-03-20 | GODREJAGRO.NS | UP | 0.0 | REJECT | -6.1172 | 7.357689039932024 |
| 2026-03-25 | MAPMYINDIA.NS | UP | -0.0112208258527868 | REJECT | -5.3411 | 6.149012567324963 |
| 2026-03-20 | PNBHOUSING.NS | UP | -0.7450435661068289 | REJECT | -5.1964 | 6.926379593383003 |
| 2026-03-25 | DEEPAKFERT.NS | UP | -0.0050047545167908 | REJECT | -4.8546 | 5.410139632651012 |
| 2026-03-27 | ALKYLAMINE.NS | UP | -0.185686653771766 | REJECT | -4.7118 | 5.547388781431339 |
| 2026-03-18 | KPITTECH.NS | UP | -1.1986923356338552 | REJECT | -4.2644 | 4.831093352706139 |
| 2026-03-20 | ALKYLAMINE.NS | UP | -0.1547987616099089 | REJECT | -4.0712 | 4.411764705882348 |

## Strategy PASS Days vs REJECT Days Summary (OOS)

Key finding: compare quality of Knowledge-selected candidates on Strategy-PASS vs REJECT days.

See `knowledge_vs_strategy_002_model_comparison.csv` for full breakdown.

## Architecture Note

**All 177 evolved strategies in the library have direction=BUY.**
This means the Strategy layer cannot evaluate DOWN (SHORT) candidates via EDG conditions.
DOWN candidate evaluation uses a regime-based proxy (mom_20d alignment).
This is documented as a structural limitation, not a research design choice.

## Key Limitation

The Strategy evaluation in this research uses market-level OHLCV features.
Features vix, iv_rank, pcr are UNAVAILABLE (no options data in study002_replay.db).
83 of 177 strategies require these features and are UNAVAILABLE.
94 of 177 strategies can be evaluated.