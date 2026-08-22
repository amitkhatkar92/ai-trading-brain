# TOP_MOVER_CASE_STUDIES_001
## Historical Case Studies — Top Mover Selection
**Date:** 2026-08-14  
**Source:** TOP_MOVER_SELECTION_AUDIT_001

---

Each case shows: 230 universe → 20 UP pool → final 5–6 selection → actual top movers.
Two "good" and two "bad" selection cases are included. One average case.

## Case 1: 2024-05-14 — GOOD SELECTION

**Regime:** SIDEWAYS | **IIOS signals:** 34 | **Universe:** 210 symbols

### Model A Selections (IIOS — LONG only)
- `COCHINSHIP.NS`: T+5=21.60% | MFE=27.23%
- `HINDZINC.NS`: T+5=37.94% | MFE=44.26%
- `JINDALSTEL.NS`: T+5=10.14% | MFE=10.99%
- `HAL.NS`: T+5=20.77% | MFE=21.74%
- `FINPIPE.NS`: T+5=4.12% | MFE=8.76%
- `BEML.NS`: T+5=19.88% | MFE=23.06%

### Model B Selections (Knowledge-led — UP)
- `BEML.NS`: T+5=19.88%
- `JINDALSTEL.NS`: T+5=10.14%
- `FINPIPE.NS`: T+5=4.12%
- `BOSCHLTD.NS`: T+5=-2.97%
- `BASF.NS`: T+5=-5.65%
- `ZYDUSWELL.NS`: T+5=0.01%

### Model B Selections (Knowledge-led — DOWN)
- `BASF.NS`: T+5=-5.65%
- `FINPIPE.NS`: T+5=4.12%
- `VEDL.NS`: T+5=12.59%
- `BEML.NS`: T+5=19.88%
- `JINDALSTEL.NS`: T+5=10.14%
- `BOSCHLTD.NS`: T+5=-2.97%

### Actual Top Movers (ground truth — revealed after selection)
**Top 5 UP (by T+5 close-to-close return):**
- `HINDZINC.NS`: T+5=37.94% | ✅ IN_A | ❌ MISSED_B
- `BDL.NS`: T+5=34.92% | ❌ MISSED_A | ❌ MISSED_B
- `RVNL.NS`: T+5=24.62% | ❌ MISSED_A | ❌ MISSED_B
- `MAZDOCK.NS`: T+5=23.35% | ❌ MISSED_A | ❌ MISSED_B
- `BEL.NS`: T+5=22.80% | ❌ MISSED_A | ❌ MISSED_B

**Top 5 DOWN:**
- `JYOTHYLAB.NS`: T+5=-6.50% | ❌ MISSED
- `ONMOBILE.NS`: T+5=-5.79% | ❌ MISSED
- `BASF.NS`: T+5=-5.65% | ✅ IN_B_DOWN
- `COLPAL.NS`: T+5=-4.02% | ❌ MISSED
- `TEJASNET.NS`: T+5=-3.14% | ❌ MISSED

**Summary:** Model A avg T+5 return of selections = 19.07%

---

## Case 2: 2025-05-09 — GOOD SELECTION

**Regime:** SIDEWAYS | **IIOS signals:** 25 | **Universe:** 210 symbols

### Model A Selections (IIOS — LONG only)
- `BDL.NS`: T+5=20.25% | MFE=26.56%
- `BHARATFORG.NS`: T+5=8.36% | MFE=8.96%
- `IDEAFORGE.NS`: T+5=20.93% | MFE=26.17%
- `YESBANK.NS`: T+5=7.64% | MFE=9.64%
- `INTELLECT.NS`: T+5=27.48% | MFE=28.01%
- `PARAS.NS`: T+5=23.38% | MFE=24.61%

### Model B Selections (Knowledge-led — UP)
- `IDEAFORGE.NS`: T+5=20.93%
- `BHARATFORG.NS`: T+5=8.36%
- `LT.NS`: T+5=4.67%
- `CERA.NS`: T+5=12.10%
- `YESBANK.NS`: T+5=7.64%
- `TITAN.NS`: T+5=3.52%

### Model B Selections (Knowledge-led — DOWN)
- `IDEAFORGE.NS`: T+5=20.93%
- `TITAN.NS`: T+5=3.52%
- `YESBANK.NS`: T+5=7.64%
- `MAZDOCK.NS`: T+5=20.55%
- `M&MFIN.NS`: T+5=12.33%
- `SAPPHIRE.NS`: T+5=10.30%

### Actual Top Movers (ground truth — revealed after selection)
**Top 5 UP (by T+5 close-to-close return):**
- `GRSE.NS`: T+5=38.26% | ❌ MISSED_A | ❌ MISSED_B
- `COCHINSHIP.NS`: T+5=37.11% | ❌ MISSED_A | ❌ MISSED_B
- `MIDHANI.NS`: T+5=31.03% | ❌ MISSED_A | ❌ MISSED_B
- `IRCON.NS`: T+5=28.05% | ❌ MISSED_A | ❌ MISSED_B
- `INTELLECT.NS`: T+5=27.48% | ✅ IN_A | ❌ MISSED_B

**Top 5 DOWN:**
- `NAVINFLUOR.NS`: T+5=-7.68% | ❌ MISSED
- `MUTHOOTFIN.NS`: T+5=-5.60% | ❌ MISSED
- `JYOTHYLAB.NS`: T+5=-4.96% | ❌ MISSED
- `INDUSINDBK.NS`: T+5=-4.64% | ❌ MISSED
- `SRF.NS`: T+5=-2.98% | ❌ MISSED

**Summary:** Model A avg T+5 return of selections = 18.01%

---

## Case 3: 2021-10-18 — BAD SELECTION

**Regime:** TRENDING_UP | **IIOS signals:** 83 | **Universe:** 202 symbols

### Model A Selections (IIOS — LONG only)
- `NHPC.NS`: T+5=-8.73% | MFE=3.24%
- `TATAPOWER.NS`: T+5=-16.98% | MFE=4.10%
- `NATIONALUM.NS`: T+5=-14.71% | MFE=1.68%
- `SJVN.NS`: T+5=-11.67% | MFE=3.38%
- `CERA.NS`: T+5=-15.53% | MFE=4.02%
- `HINDZINC.NS`: T+5=-16.68% | MFE=1.23%

### Model B Selections (Knowledge-led — UP)
- `SJVN.NS`: T+5=-11.67%
- `NHPC.NS`: T+5=-8.73%
- `NATIONALUM.NS`: T+5=-14.71%
- `DEEPAKFERT.NS`: T+5=-4.97%
- `BASF.NS`: T+5=-11.97%
- `VEDL.NS`: T+5=-13.16%

### Model B Selections (Knowledge-led — DOWN)
- `SJVN.NS`: T+5=-11.67%
- `NHPC.NS`: T+5=-8.73%
- `HINDZINC.NS`: T+5=-16.68%
- `PNB.NS`: T+5=-2.39%
- `TATAPOWER.NS`: T+5=-16.98%
- `CERA.NS`: T+5=-15.53%

### Actual Top Movers (ground truth — revealed after selection)
**Top 5 UP (by T+5 close-to-close return):**
- `RVNL.NS`: T+5=13.80% | ❌ MISSED_A | ❌ MISSED_B
- `ICICIBANK.NS`: T+5=12.91% | ❌ MISSED_A | ❌ MISSED_B
- `SHRIRAMFIN.NS`: T+5=8.72% | ❌ MISSED_A | ❌ MISSED_B
- `FEDERALBNK.NS`: T+5=7.56% | ❌ MISSED_A | ❌ MISSED_B
- `KOTAKBANK.NS`: T+5=7.10% | ❌ MISSED_A | ❌ MISSED_B

**Top 5 DOWN:**
- `IRCTC.NS`: T+5=-31.57% | ❌ MISSED
- `INDIAMART.NS`: T+5=-20.53% | ❌ MISSED
- `TEJASNET.NS`: T+5=-18.97% | ❌ MISSED
- `KEI.NS`: T+5=-18.78% | ❌ MISSED
- `MASTEK.NS`: T+5=-18.70% | ❌ MISSED

**Summary:** Model A avg T+5 return of selections = -14.05%

---

## Case 4: 2022-12-16 — BAD SELECTION

**Regime:** SIDEWAYS | **IIOS signals:** 29 | **Universe:** 209 symbols

### Model A Selections (IIOS — LONG only)
- `YESBANK.NS`: T+5=-17.69% | MFE=4.25%
- `SUZLON.NS`: T+5=-16.28% | MFE=13.02%
- `POLYCAB.NS`: T+5=-8.71% | MFE=0.65%
- `CESC.NS`: T+5=-6.29% | MFE=1.31%
- `MRPL.NS`: T+5=-14.82% | MFE=0.73%
- `DEEPAKFERT.NS`: T+5=-22.37% | MFE=1.38%

### Model B Selections (Knowledge-led — UP)
- `RAJESHEXPO.NS`: T+5=-20.77%
- `KALYANKJIL.NS`: T+5=-14.15%
- `STLTECH.NS`: T+5=-14.60%
- `BSE.NS`: T+5=-10.98%
- `GAIL.NS`: T+5=-5.37%
- `ONGC.NS`: T+5=-5.03%

### Model B Selections (Knowledge-led — DOWN)
- `KALYANKJIL.NS`: T+5=-14.15%
- `IRCTC.NS`: T+5=-9.66%
- `BEL.NS`: T+5=-2.92%
- `STLTECH.NS`: T+5=-14.60%
- `MPHASIS.NS`: T+5=0.33%
- `DRREDDY.NS`: T+5=0.03%

### Actual Top Movers (ground truth — revealed after selection)
**Top 5 UP (by T+5 close-to-close return):**
- `ABBOTINDIA.NS`: T+5=5.44% | ❌ MISSED_A | ❌ MISSED_B
- `DIVISLAB.NS`: T+5=5.16% | ❌ MISSED_A | ❌ MISSED_B
- `AJANTPHARM.NS`: T+5=4.51% | ❌ MISSED_A | ❌ MISSED_B
- `LUPIN.NS`: T+5=3.76% | ❌ MISSED_A | ❌ MISSED_B
- `CIPLA.NS`: T+5=2.73% | ❌ MISSED_A | ❌ MISSED_B

**Top 5 DOWN:**
- `DEEPAKFERT.NS`: T+5=-22.37% | ❌ MISSED
- `RAJESHEXPO.NS`: T+5=-20.77% | ❌ MISSED
- `UNIONBANK.NS`: T+5=-20.25% | ❌ MISSED
- `IRCON.NS`: T+5=-19.05% | ❌ MISSED
- `COCHINSHIP.NS`: T+5=-19.02% | ❌ MISSED

**Summary:** Model A avg T+5 return of selections = -14.36%

---

## Case 5: 2024-09-18 — AVERAGE SELECTION

**Regime:** TRENDING_UP | **IIOS signals:** 44 | **Universe:** 210 symbols

### Model A Selections (IIOS — LONG only)
- `ALKYLAMINE.NS`: T+5=-0.45% | MFE=5.57%
- `BSE.NS`: T+5=-1.50% | MFE=7.80%
- `ROUTE.NS`: T+5=-4.42% | MFE=1.22%
- `SHRIRAMFIN.NS`: T+5=-1.42% | MFE=1.37%
- `BIKAJI.NS`: T+5=3.80% | MFE=7.47%
- `SOBHA.NS`: T+5=7.76% | MFE=10.68%

### Model B Selections (Knowledge-led — UP)
- `BIKAJI.NS`: T+5=3.80%
- `TORNTPOWER.NS`: T+5=-2.38%
- `MOTHERSON.NS`: T+5=0.65%
- `BSE.NS`: T+5=-1.50%
- `ALKYLAMINE.NS`: T+5=-0.45%
- `OLECTRA.NS`: T+5=-1.16%

### Model B Selections (Knowledge-led — DOWN)
- `BSE.NS`: T+5=-1.50%
- `RADICO.NS`: T+5=-6.45%
- `SHRIRAMFIN.NS`: T+5=-1.42%
- `ALKYLAMINE.NS`: T+5=-0.45%
- `TORNTPOWER.NS`: T+5=-2.38%
- `MOTHERSON.NS`: T+5=0.65%

### Actual Top Movers (ground truth — revealed after selection)
**Top 5 UP (by T+5 close-to-close return):**
- `GODREJPROP.NS`: T+5=15.35% | ❌ MISSED_A | ❌ MISSED_B
- `M&M.NS`: T+5=10.07% | ❌ MISSED_A | ❌ MISSED_B
- `SAPPHIRE.NS`: T+5=9.61% | ❌ MISSED_A | ❌ MISSED_B
- `BLUESTARCO.NS`: T+5=9.15% | ❌ MISSED_A | ❌ MISSED_B
- `SYMPHONY.NS`: T+5=8.91% | ❌ MISSED_A | ❌ MISSED_B

**Top 5 DOWN:**
- `IDEA.NS`: T+5=-19.69% | ❌ MISSED
- `ZENSARTECH.NS`: T+5=-8.31% | ❌ MISSED
- `NATCOPHARM.NS`: T+5=-8.21% | ❌ MISSED
- `ERIS.NS`: T+5=-8.06% | ❌ MISSED
- `PNBHOUSING.NS`: T+5=-7.19% | ❌ MISSED

**Summary:** Model A avg T+5 return of selections = 0.63%

---

