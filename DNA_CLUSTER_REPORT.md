# DNA CLUSTER REPORT
## Study 2A — Natural Winner Cluster Discovery

**Evidence base:** 73,665 winners (Group A) | Clustering on Top-20 features | KMeans algorithm  
**Classification:** HYPOTHESIS (silhouette=0.168, low separation — clusters are present but overlapping)

---

## 1. Cluster Discovery Method

| Parameter | Value | Rationale |
|---|---|---|
| Algorithm | KMeans | Appropriate for continuous feature space |
| Feature set | Top 20 ranked features | Captures all relevant information |
| Standardization | StandardScaler | Removes scale bias across features |
| k selection | Silhouette score over k=2..8 | Data-driven, no predefined k |
| Sample | Winners only (n=73,665) | Focus on winner archetypes |

**Silhouette scores tested:**

| k | Silhouette Score |
|---|---|
| 2 | **0.168 (optimal)** |
| 3 | 0.152 |
| 4 | 0.141 |
| 5 | 0.124 |
| 6–8 | <0.120 |

**Interpretation of silhouette=0.168:** Low separation. The winner population does not form sharply distinct groups — the two archetypes discovered are OVERLAPPING subpopulations within a continuous distribution, not separate clusters. **All cluster findings classified as HYPOTHESIS.**

---

## 2. Optimal Cluster Configuration: k=2

### Cluster 1 — SECTOR_LEADERSHIP_ROTATION

| Attribute | Value |
|---|---|
| **Size** | 32,306 winners |
| **% of all winners** | 43.9% |
| **Average forward return** | +2.70% |
| **Median forward return** | (not stored separately) |
| **Dominant regime** | SIDEWAYS |
| **Top sector** | BANKING_FINANCE |

**Centroid profile (top 5 distinguishing features):**

| Feature | Centroid Value | Interpretation |
|---|---|---|
| `prox_52w_low` | 1.591 | Stock is 59% ABOVE its 52-week low — has already recovered |
| `cons_up_days` | 1.465 | ~1.5 consecutive up days — mild upward momentum |
| `vol_ratio` | 1.313 | Volume 31% above 5-day average — above-normal activity |
| `vol_ratio_20` | 1.272 | Volume 27% above 20-day average — sustained elevated activity |
| `prox_52w_high` | 0.855 | Closing at 85.5% of 52-week high — still 15% below breakout |

**Sector distribution:**
- BANKING_FINANCE: 4,581 (14.2%)
- INFRA: 3,396 (10.5%)
- CHEMICALS: 2,707 (8.4%)
- METALS: 2,665 (8.2%)
- PHARMA: 2,664 (8.2%)

**Regime distribution:**
- SIDEWAYS: 18,224 (56.4%)
- TRENDING_UP: 12,465 (38.6%)
- TRENDING_DOWN: 1,617 (5.0%)

**Cluster 1 Archetype Interpretation:**
This cluster describes stocks that have **already recovered from their 52-week low** (59% above) and are rising with above-normal volume. Banking and infrastructure sectors dominate — cyclical sectors with clear earnings catalysts. The elevated volume ratio (1.31×) suggests institutional participation. This archetype occurs most in TRENDING_UP regime (38.6%), significantly higher than Cluster 2 (14.5%). 

**Named SECTOR_LEADERSHIP_ROTATION** because: stocks in leading sectors (Banking, Infra) rotate into leadership during up-trends, driven by institutional flows. The high 52W-low proximity indicates prior recovery has already happened — these are trending winners, not mean-reversion plays.

---

### Cluster 2 — COMPOSITE_SETUP

| Attribute | Value |
|---|---|
| **Size** | 41,359 winners |
| **% of all winners** | 56.1% |
| **Average forward return** | +2.60% |
| **Dominant regime** | SIDEWAYS |
| **Top sector** | BANKING_FINANCE |

**Centroid profile (top 5 distinguishing features):**

| Feature | Centroid Value | Interpretation |
|---|---|---|
| `prox_52w_low` | 1.446 | Stock 45% above 52-week low — less recovery than Cluster 1 |
| `cons_dn_days` | 1.402 | ~1.4 consecutive DOWN days — mild prior weakness |
| `vol_ratio` | 1.069 | Volume only 7% above average — near normal activity |
| `vol_ratio_20` | 0.981 | Volume at 20-day average — no volume surge |
| `sc_low` | 0.950 | In low-breadth environment (avg_conviction < 0.4) |

**Sector distribution:**
- BANKING_FINANCE: 5,747 (13.9%)
- INFRA: 3,933 (9.5%)
- IT: 3,734 (9.0%)
- CONSUMER_DURABLES: 3,496 (8.5%)
- CHEMICALS: 3,440 (8.3%)

**Regime distribution:**
- SIDEWAYS: 26,762 (64.7%)
- TRENDING_UP: 8,258 (20.0%)
- TRENDING_DOWN: 6,339 (15.3%)

**Cluster 2 Archetype Interpretation:**
This cluster describes a more diverse, structurally complex winner archetype. Key markers: (1) moderate 52W-low distance (less recovery than Cluster 1), (2) mild prior weakness (1.4 consecutive down days), (3) near-normal volume (no institutional surge), (4) predominantly low-breadth market environment. This archetype covers IT, Consumer Durables alongside Banking — a cross-sector spread suggesting these winners arise from idiosyncratic catalysts rather than sector rotation.

The `cons_dn_days=1.4` centroid confirms the **mean reversion** component: these stocks had mild prior weakness and bounced. The `sc_low=0.95` flag (nearly always in low-breadth) says these winners occur in quiet markets — contrarian plays.

**Named COMPOSITE_SETUP** because: no single feature dominates — these winners are the product of multiple weaker signals combining without a single dominant theme. Larger population (56.1%) means this is the more common winner archetype.

---

## 3. Cluster Comparison

| Attribute | SECTOR_LEADERSHIP | COMPOSITE_SETUP |
|---|---|---|
| Size | 32,306 (44%) | 41,359 (56%) |
| Avg return | +2.70% | +2.60% |
| Primary regime | SIDEWAYS / UP | SIDEWAYS |
| Volume character | 1.31× avg (elevated) | 1.07× avg (normal) |
| Prior momentum | Mild upside streak | Mild downside streak |
| 52W recovery | 59% above low | 45% above low |
| Breadth context | Moderate | Low (contrarian) |
| Primary sectors | Bank, Infra, Metals, Pharma | Bank, Infra, IT, CD, Chemicals |
| Archetype | Institutional sector rotation | Individual stock mean reversion |

**Performance difference:** Cluster 1 (SECTOR_LEADERSHIP) averages +2.70% vs Cluster 2 (COMPOSITE_SETUP) +2.60% — very similar. Both archetypes produce similar average gains; the difference is in how they're identified, not how much they return.

---

## 4. Cluster Feature Centroid Map

(Top 10 features from ranking, both cluster centroids in original scale)

| Feature | Cluster 1 Centroid | Cluster 2 Centroid | Difference |
|---|---|---|---|
| `avg_conviction` | ~0.31 | ~0.28 | C1 higher breadth |
| `sect_conviction` | ~0.30 | ~0.28 | C1 higher sector conv |
| `atr_14` | ~0.035 | ~0.034 | Near equal |
| `intra_range` | ~0.034 | ~0.034 | Near equal |
| `sc_high` | ~0.07 | ~0.06 | C1 more high-breadth |
| `sect_part5d` | ~0.51 | ~0.49 | C1 slightly higher |
| `close_pos` | ~0.47 | ~0.47 | Equal |
| `sc_low` | ~0.64 | **0.950** | C2 strongly low-breadth |
| `mom_5d` | ~0.005 | ~0.003 | C1 slightly higher momentum |
| `cons_up_days` | **1.465** | ~0.80 | C1 on upward streak |

---

## 5. Cluster Stability Assessment

| Assessment | Result |
|---|---|
| Silhouette score | 0.168 (low) |
| Cluster overlap | HIGH — not well separated |
| Number of outliers | Not computed (KMeans has no outlier concept) |
| Stability across random seeds | Not tested (single seed=42) |
| Confidence classification | HYPOTHESIS |

**Recommendation:** The two clusters describe real tendencies in the data, but a stock can belong to either cluster on different days. The cluster labels should be treated as **archetypes** (characteristic patterns) rather than **categories** (discrete groups).

---

## 6. What the Clusters Tell Us About the Market

1. **Winners are not one thing.** The dataset required only k=2 clusters with low silhouette — the winner population is a continuous distribution, not distinct types.

2. **Institutional rotation vs contrarian reversion.** The two main winner pathways are: (a) being in a sector with strong institutional flows (Banking, Infra) during uptrends, and (b) being any quality stock in a low-breadth market that quietly bounces from mild weakness.

3. **Volume does not distinguish winners reliably.** Cluster 2 (56% of winners) has near-normal volume (1.07×). Waiting for volume confirmation would exclude the majority of winners.

4. **Sector matters more in Cluster 1.** BANKING_FINANCE dominates Cluster 1 (4,581 winners). In Cluster 2, IT and Consumer Durables join the mix — the cluster is more diversified.

---

## 7. Actionable Cluster Insights (Research Grade)

> **HYPOTHESIS 1:** When the market is in TRENDING_UP regime AND Banking/Infra stocks are on mild upward streaks (cons_up_days ≥ 1) with elevated volume (vol_ratio > 1.3), seek Cluster 1 (SECTOR_LEADERSHIP) setups.

> **HYPOTHESIS 2:** When the market is in SIDEWAYS regime with low breadth (avg_conviction < 0.4), any stock with mild prior weakness (cons_dn_days ≥ 1) and near-average volume qualifies for Cluster 2 (COMPOSITE) mean-reversion consideration.

> **HYPOTHESIS 3:** The sectors IT, Consumer Durables, and Chemicals are primarily Cluster 2 (contrarian) sectors — seek them in low-breadth sideways markets, not during up-trends.

---

*Study 2A — DNA Cluster Report | 2026-08-03 | 73,665 winners | KMeans k=2 | Silhouette 0.168*
