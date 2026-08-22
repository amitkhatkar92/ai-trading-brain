# REAL_OPTIONS_AUDIT_002 — Real Market Validation

**Run ID:** `20260619`  
**Generated:** 2026-06-19 09:54 UTC  
**Data period:** 2024-06-19 → 2026-05-20 (2y)  
**Total records:** 8,532  
**Instruments:** NIFTY + BANKNIFTY  

> This audit validates synthetic OPTIONS_AUDIT_001 findings against
> real NIFTY/BANKNIFTY price history and India VIX data.
> No live trading code was modified.

---
## Executive Summary

| Finding | Count |
|---------|-------|
| ✅ Synthetic findings CONFIRMED | 1 |
| 🔴 Synthetic findings OVERSTATED | 4 |
| 🟢 Real outperforms synthetic | 4 |
| ⚪ Insufficient real data | 0 |

---
## Strategy Validation vs OPTIONS_AUDIT_001 Synthetic

| Strategy | Real WR% | Real PF | Synthetic WR% | Synthetic PF | WR Verdict | PF Verdict | Best Regime (Real) |
|----------|----------|---------|---------------|--------------|------------|------------|--------------------|
| `BULL_PUT_SPREAD` | **80.7%** (n=948) | 2.09 | 70.3% | 1.74 | 🟢 UNDERSTATED (real beats by 10.4pp) | 🟢 STRONGER (+0.35) | HIGH_VOL (82.1%, n=28) |
| `BEAR_CALL_SPREAD` | **80.3%** (n=948) | 2.04 | 63.1% | 1.45 | 🟢 UNDERSTATED (real beats by 17.2pp) | 🟢 STRONGER (+0.59) | TRENDING (96.8%, n=31) |
| `IRON_CONDOR` | **75.3%** (n=948) | 1.22 | 62.0% | 2.2 | 🟢 UNDERSTATED (real beats by 13.3pp) | 🔴 WEAKER (−0.98) | TRENDING (83.9%, n=31) |
| `SHORT_STRANGLE` | **84.3%** (n=948) | 1.79 | 58.4% | 1.98 | 🟢 UNDERSTATED (real beats by 25.9pp) | ✅ MATCH | TRENDING (93.5%, n=31) |
| `LONG_STRANGLE` | **15.7%** (n=948) | 0.56 | 38.7% | 1.12 | 🔴 OVERSTATED (+23.0pp gap) | 🔴 WEAKER (−0.56) | HIGH_VOL (42.9%, n=28) |
| `COVERED_CALL` | **72.4%** (n=948) | 1.40 | 65.0% | 1.55 | ✅ CONFIRMED | ✅ MATCH | TRENDING (96.8%, n=31) |
| `PROTECTIVE_PUT` | **13.4%** (n=948) | 0.77 | 45.3% | 2.85 | 🔴 OVERSTATED (+31.9pp gap) | 🔴 WEAKER (−2.08) | TRENDING (16.1%, n=31) |
| `LONG_CALL` | **19.7%** (n=948) | 0.74 | 42.0% | 1.3 | 🔴 OVERSTATED (+22.3pp gap) | 🔴 WEAKER (−0.56) | HIGH_VOL (42.9%, n=28) |
| `LONG_PUT` | **19.3%** (n=948) | 0.72 | 39.5% | 1.22 | 🔴 OVERSTATED (+20.2pp gap) | 🔴 WEAKER (−0.50) | TRENDING (19.4%, n=31) |

---
## Win Rate by Strategy × Regime

| Strategy | HIGH_VOL | RANGING | TRENDING |
|----------|----------|---------|----------|
| `BULL_PUT_SPREAD` (⭐ best=TRENDING) | 82.1% (n=28) | 80.7% (n=889) | 80.6% (n=31) |
| `BEAR_CALL_SPREAD` (⭐ best=TRENDING) | 57.1% (n=28) | 80.4% (n=889) | 96.8% (n=31) |
| `IRON_CONDOR` (⭐ best=RANGING) | 50.0% (n=28) | 75.8% (n=889) | 83.9% (n=31) |
| `SHORT_STRANGLE` (⭐ best=RANGING) | 57.1% (n=28) | 84.8% (n=889) | 93.5% (n=31) |
| `LONG_STRANGLE` (⭐ best=HIGH_VOL) | 42.9% (n=28) | 15.2% (n=889) | 6.5% (n=31) |
| `COVERED_CALL` (⭐ best=RANGING) | 57.1% (n=28) | 72.0% (n=889) | 96.8% (n=31) |
| `PROTECTIVE_PUT` (⭐ best=HIGH_VOL) | 7.1% (n=28) | 13.5% (n=889) | 16.1% (n=31) |
| `LONG_CALL` (⭐ best=TRENDING) | 42.9% (n=28) | 19.6% (n=889) | 3.2% (n=31) |
| `LONG_PUT` (⭐ best=HIGH_VOL) | 17.9% (n=28) | 19.3% (n=889) | 19.4% (n=31) |

---
## Win Rate by VIX Bucket

LOW VIX < 14 | MEDIUM 14–22 | HIGH > 22

| Strategy | LOW VIX | MEDIUM VIX | HIGH VIX |
|----------|---------|------------|----------|
| `BULL_PUT_SPREAD` | 83.2% (n=518) | 77.4% (n=402) | 82.1% (n=28) |
| `BEAR_CALL_SPREAD` | 82.2% (n=518) | 79.4% (n=402) | 57.1% (n=28) |
| `IRON_CONDOR` | 79.0% (n=518) | 72.4% (n=402) | 50.0% (n=28) |
| `SHORT_STRANGLE` | 86.1% (n=518) | 83.8% (n=402) | 57.1% (n=28) |
| `LONG_STRANGLE` | 13.9% (n=518) | 16.2% (n=402) | 42.9% (n=28) |
| `COVERED_CALL` | 73.4% (n=518) | 72.1% (n=402) | 57.1% (n=28) |
| `PROTECTIVE_PUT` | 12.5% (n=518) | 14.9% (n=402) | 7.1% (n=28) |
| `LONG_CALL` | 17.8% (n=518) | 20.6% (n=402) | 42.9% (n=28) |
| `LONG_PUT` | 16.8% (n=518) | 22.6% (n=402) | 17.9% (n=28) |

---
## NIFTY vs BANKNIFTY Comparison

| Strategy | NIFTY WR% | BANKNIFTY WR% | Delta |
|----------|-----------|---------------|-------|
| `BULL_PUT_SPREAD` | 81.1% (n=475) | 80.3% (n=473) | -0.8pp |
| `BEAR_CALL_SPREAD` | 80.4% (n=475) | 80.1% (n=473) | -0.3pp |
| `IRON_CONDOR` | 76.2% (n=475) | 74.4% (n=473) | -1.8pp |
| `SHORT_STRANGLE` | 86.5% (n=475) | 82.0% (n=473) | -4.5pp |
| `LONG_STRANGLE` | 13.5% (n=475) | 18.0% (n=473) | +4.5pp |
| `COVERED_CALL` | 71.6% (n=475) | 73.2% (n=473) | +1.6pp |
| `PROTECTIVE_PUT` | 13.5% (n=475) | 13.3% (n=473) | -0.2pp |
| `LONG_CALL` | 19.6% (n=475) | 19.9% (n=473) | +0.3pp |
| `LONG_PUT` | 18.9% (n=475) | 19.7% (n=473) | +0.8pp |

---
## Key Findings & Production Readiness

**Top strategies by real profit factor:**

1. `BULL_PUT_SPREAD` — PF=2.09, WR=80.7% — 🟢 UNDERSTATED (real beats by 10.4pp)
2. `BEAR_CALL_SPREAD` — PF=2.04, WR=80.3% — 🟢 UNDERSTATED (real beats by 17.2pp)
3. `SHORT_STRANGLE` — PF=1.79, WR=84.3% — 🟢 UNDERSTATED (real beats by 25.9pp)

**Production readiness verdict:**

| Strategy | Confirmed by Real Data | Safe to Promote? |
|----------|------------------------|------------------|
| `BULL_PUT_SPREAD` | ⚠️ Partial | ✅ Promote to paper |
| `BEAR_CALL_SPREAD` | ⚠️ Partial | ⚠️ Watch — needs more data |
| `IRON_CONDOR` | ⚠️ Partial | ✅ Promote to paper |
| `SHORT_STRANGLE` | ⚠️ Partial | ⚠️ Watch — needs more data |
| `LONG_STRANGLE` | ⚠️ Partial | ⚠️ Watch — needs more data |
| `COVERED_CALL` | ✅ Yes | ✅ Promote to paper |
| `PROTECTIVE_PUT` | ⚠️ Partial | ⚠️ Watch — needs more data |
| `LONG_CALL` | ⚠️ Partial | ⚠️ Watch — needs more data |
| `LONG_PUT` | ⚠️ Partial | ⚠️ Watch — needs more data |

---
*Generated by REAL_OPTIONS_AUDIT_002.*  
*No live trading code was modified.*