# STUDY 002 EXECUTION
## One-Year Historical Market Learning

**Document Type:** Study Execution Record  
**Date:** 2026-08-01  
**Classification:** Research — Permanent Reference

---

## 1. Study Parameters

| Parameter | Value |
|---|---|
| **Study Name** | Study 002 — One-Year Historical Market Learning |
| **Study Period** | 2025-08-01 to 2026-07-31 |
| **Replay Mode** | Chronological — oldest session first |
| **Historical Provider** | Yahoo Finance (yfinance) — primary and sole source |
| **Integrity Mode** | STRICT |
| **Platform Version** | IIOS — certified Research Phase 1 (`research-phase-1-certified`) |
| **Study DB** | `data/study002_replay.db` (isolated, never touches live DB) |
| **Results File** | `data/study002_results.json` |
| **Pipeline** | `study002_pipeline.py` |

---

## 2. Feature Flags

| System | Status |
|---|---|
| Historical Outcome Engine | Enabled |
| Pattern Miner | Enabled |
| Edge Discovery | Enabled |
| Learning Engine | Enabled |
| MetaModel | Enabled (awaiting closed trade outcomes) |
| Strategy Evolution | Enabled |
| BHAV Delivery Data | Disabled (NSE archives HTTP 404 for all historical dates) |

---

## 3. Execution Timeline

| Phase | Start | End | Duration |
|---|---|---|---|
| Phase 1: OHLCV Download | 19:02:30 | ~19:03:30 | ~1 min |
| Phase 2: BHAV Download Attempts | ~19:03:30 | ~19:10:40 | ~7 min |
| Phase 3: Simulation (244 days) | ~19:10:40 | ~19:12:14 | ~1.5 min |
| Phase 4: Knowledge Pipeline | 19:14:51 | 19:14:56 | 5.5 sec |
| **Total elapsed** | 19:02:30 | 19:14:56 | **~12 min** |

---

## 4. Data Coverage

### OHLCV

| Metric | Value |
|---|---|
| Universe size | 230 symbols |
| Symbols with data | 209 symbols |
| Symbols failed (delisted) | 21 symbols |
| NIFTY50 trading dates loaded | 244 |
| OHLCV rows (excl. NIFTY50) | 51,793 |
| Calendar dates covered | 248 |
| Trading days confirmed | 244 |

### BHAV Delivery Data

| Metric | Value |
|---|---|
| Rows loaded | 0 |
| Status | Unavailable — NSE archives return HTTP 404 for all historical dates in study period |
| Impact | DNA_1B_QUIET_ACCUMULATION and DNA_1B_LOW_NOISE_STRENGTH archetypes operate without delivery volume confirmation |

---

## 5. Simulation Execution

| Metric | Value |
|---|---|
| Trading sessions simulated | 244 |
| Signals written | 8,562 |
| Opportunities created | 1,966 |
| Signals merged into existing opportunities | 6,596 |
| Exit code | 1 (UnicodeEncodeError in final console report only — all DB data intact) |
| DB integrity | Confirmed — study002_replay.db verified post-simulation |

### Regime Distribution (NIFTY50-based detection)

| Regime | Sessions | % of Year |
|---|---|---|
| SIDEWAYS | 191 | 78.3% |
| TRENDING_DOWN | 37 | 15.2% |
| TRENDING_UP | 16 | 6.6% |
| VOLATILE | 0 | 0.0% |

---

## 6. Knowledge Pipeline Execution

| Stage | Description | Status | Key Output |
|---|---|---|---|
| Stage 0 | Session Record Generation | COMPLETE | 244 session records |
| Stage 1 | Regime Analysis | COMPLETE | 3 regimes classified |
| Stage 2 | Signal & Opportunity Analysis | COMPLETE | 8,562 signals, 1,966 opps |
| Stage 3 | Sector Analysis | COMPLETE | 12 sectors, 2,916 FULL rows |
| Stage 4 | Feature Database Enrichment | COMPLETE | 50,539 feature vectors |
| Stage 5 | Edge Discovery Pipeline (EDE) | COMPLETE | 2 edges ACTIVE, 1 rejected |
| Stage 6 | MetaModel Status | BLOCKED | 0 closed outcomes |
| Stage 7 | Knowledge Store Verification | COMPLETE | All stores verified |
| **Total elapsed** | — | — | **5.5 seconds** |

---

## 7. Defects Observed (Not Corrected)

| # | Defect | Location | Impact | Classification |
|---|---|---|---|---|
| D-01 | `SectorFlow.sector` → should be `SectorFlow.sector_name` | `study002_pipeline.py` line 739 | Pipeline crash on first run — fixed before document generation | Bug |
| D-02 | UnicodeEncodeError on `✓` in Windows cp1252 console | `historical_replay.py` `print_replay_report()` | Exit code 1 — data intact | Display |
| D-03 | All 21 failed symbol downloads silently skipped | `historical_replay.py` | Survivorship bias — 21 delisted symbols absent | Data |

Per study rules: defects documented, not corrected during study.

---

## 8. Reference Files

| File | Description |
|---|---|
| `data/study002_replay.db` | Isolated SQLite replay database — 16 tables |
| `data/study002_results.json` | Complete pipeline results — machine-readable |
| `data/study002_pipeline_log.txt` | Full pipeline execution log |
| `data/study002_replay_log.txt` | Full historical replay log |
| `study002_pipeline.py` | Knowledge generation pipeline |
