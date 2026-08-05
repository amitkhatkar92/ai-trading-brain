# HKAP-001 Design Document

## 1. Problem Statement

The IIOS V1.0 platform processes live market data and builds institutional knowledge
in real time. However, the platform was deployed with zero historical institutional
knowledge. Agents such as `PopulationClassifier`, `DNADiscoveryEngine`, and
`ScientificDirector` are operating from a cold start.

HKAP-001 (Historical Knowledge Acquisition Program) addresses this by replaying
10+ years of historical NSE data through the complete IIOS V1.0 stack — year by year,
forward-only — to reconstruct what institutional patterns existed, when they emerged,
how they evolved, and which ones survived every market regime.

**The objective is not backtesting.** HKAP produces knowledge, not returns.

---

## 2. Architecture

```
run_hkap.py                   CLI entry point
    └── HKAPEngine             Top-level orchestrator
            ├── YearRunner × N  Per-year 9-stage pipeline
            │       ├── HistoricalSnapshotBuilder  yfinance → DailyMarketSnapshot
            │       ├── PopulationClassifier        (IIOS V1.0 — no changes)
            │       ├── DNADiscoveryEngine           (IIOS V1.0 — no changes)
            │       ├── DNAConsensusEngine           (IIOS V1.0 — no changes)
            │       ├── IDRRepository               (IIOS V1.0 — year-scoped)
            │       ├── MarketProfiler              Year characterisation
            │       └── ScientificDirector          Annual review
            └── CrossYearAnalyzer  DNA/Edge lifecycle across years
            └── HKAPReportGenerator  Markdown reports (5/year + 8 synthesis)
```

HKAP reuses 100% of IIOS V1.0 components. No architecture changes.
No new AI modules. Component instances are scoped to each year's directory.

---

## 3. Year Pipeline (9 Stages)

Each year runs through all 9 stages. If a stage fails, it is logged and the
pipeline continues to the next stage (stage isolation). A `YearKnowledgePackage`
is produced regardless of partial failures.

```
Stage              Module                       Output
─────────────────────────────────────────────────────────────────────────────
1  UNIVERSE       PointInTimeUniverseEngine    List[symbol] (point-in-time)
2  SNAPSHOTS      HistoricalSnapshotBuilder    List[snapshot_dict]
3  MLS            PopulationClassifier +        IDR db path
                  DNADiscoveryEngine +
                  DNAConsensusEngine +
                  IDRRepository
4  IDR            IDRRepository (read)         YearDNASnapshot
5  PROFILE        MarketProfiler               YearMarketProfile
6  EDGES          YearRunner._stage_edges()    YearEdgeSnapshot
7  CROSS_YEAR     CrossYearAnalyzer (partial)  Log only
8  SD_REVIEW      ScientificDirector           YearSDReview
9  REPORTS        HKAPReportGenerator          List[file paths]
─────────────────────────────────────────────────────────────────────────────
```

---

## 4. Forward-Only Constraint

**This is the most critical invariant in HKAP.**

The Scientific Director must never be influenced by future knowledge. If it sees
DNA from 2025 while studying 2018, the knowledge would be contaminated.

Enforcement:
1. `HKAPConfig.forward_only = True` is immutable (`__post_init__` raises if False)
2. `YearRunner.__init__` checks every entry in `prior_context` and raises
   `FutureDataLeakError(requesting_year, future_year)` if any entry's year >= current year
3. `HKAPEngine.run_year()` only passes `[results[y] for y in sorted_years if y < year]`
4. Each year's MLS components write to `data/hkap/{year}/` — completely isolated directories
5. The live IDR (`data/mls/institutional_dna.db`) is never touched during HKAP

---

## 5. Data Isolation

Every year's components are fresh instances writing to isolated directories:

```
data/hkap/
  {year}/
    raw/                              # yfinance cache: {symbol}_{year}.json
    mls/
      classifications/               # PopulationClassifier output
      dna/                           # DNADiscoveryEngine sessions
      consensus/
        library.json                 # DNAConsensusEngine library
    institutional_dna.db             # Year-specific IDR
    sd_journal.json                  # Year-specific SD journal
    year_knowledge_package.json      # Serialised YearKnowledgePackage
  reports/
    {year}/
      YEAR_{year}_KNOWLEDGE.md
      YEAR_{year}_DNA.md
      YEAR_{year}_EDGES.md
      YEAR_{year}_MARKET_PROFILE.md
      YEAR_{year}_RESEARCH_SUMMARY.md
    synthesis/
      HKAP_MASTER_REPORT.md
      MARKET_EVOLUTION_REPORT.md
      DNA_EVOLUTION_REPORT.md
      EDGE_EVOLUTION_REPORT.md
      BEHAVIOURAL_CLUSTER_REPORT.md
      REGIME_EVOLUTION_REPORT.md
      KNOWLEDGE_SYNTHESIS_REPORT.md
      FINAL_INSTITUTIONAL_KNOWLEDGE_RECOMMENDATION.md
  hkap_status.json                   # Persisted HKAPStatus
```

---

## 6. Snapshot Construction

`HistoricalSnapshotBuilder.build_year(year, symbols)` converts raw yfinance OHLCV
data into `DailyMarketSnapshot` dicts for every trading day in `year`.

Download window: `{year-1}-07-01` to `{year+1}-01-15`. The extra 6 months before
the target year is used to warm up 20-day and 60-day rolling features so that
the first trading day of the target year has valid computed values.

### Features computed per symbol per day (20 features)

| Feature | Description |
|---|---|
| `mom_1d` | 1-day return |
| `mom_5d` | 5-day return |
| `mom_20d` | 20-day return |
| `mom_60d` | 60-day return |
| `rsi_14` | Wilder's RSI (14 periods) |
| `rsi_5` | Wilder's RSI (5 periods) |
| `volume_ratio` | Volume today / avg 20-day volume |
| `avg_volume_20d` | 20-day average volume |
| `hist_vol_5d` | 5-day historical volatility (std of returns × sqrt252) |
| `hist_vol_20d` | 20-day historical volatility |
| `bb_position` | Position in Bollinger Band (0=lower, 1=upper) |
| `bb_width` | Bollinger Band width |
| `relative_to_52w_high` | Close / 52-week high |
| `relative_to_52w_low` | Close / 52-week low |
| `breadth_contribution` | 1 if advancing, 0 if declining |
| `sector_mom_5d` | Sector 5-day average return |
| `sector_relative` | Symbol momentum vs sector momentum |
| `close` | Last close price |
| `high` | Last high |
| `low` | Last low |

### Regime and Volatility Classification

Regime is classified per-day from the breadth and momentum of all symbols:

| Condition | Regime |
|---|---|
| Breadth > 0.6 and avg mom > 0.001 | BULL_TREND |
| Breadth < 0.4 and avg mom < -0.001 | BEAR_MARKET |
| Avg mom > 0.003 or Avg mom < -0.003 | VOLATILE_MARKET |
| Default | RANGE_MARKET |

Volatility is classified from the cross-sectional std of 1-day returns.

### Temporal contract

All historical snapshots use `feature_timestamp = "{date}T09:15:00"` (pre-market
anchor). `PopulationClassifier` is called with `outcomes=None` and uses `mom_1d`
as proxy performance. This bypasses the temporal contract restriction without
violating it (no future intraday data is used).

---

## 7. DNA Lifecycle Model

After collecting DNA from all years, `CrossYearAnalyzer` classifies each pattern:

```
survival = (years present) / (total years studied)

survival >= 0.75:
  - confidence trend RISING  → STRENGTHENING
  - confidence trend FALLING → WEAKENING
  - else                     → STABLE

survival < 0.75:
  - present recently but not early → EMERGING
  - present early but not recently → DISAPPEARING
  - else (mixed, sporadic)         → SPORADIC
```

### Regime Dependency

For each DNA pattern, the fraction of observed market regimes in which it appeared:

```
coverage = (unique regimes with DNA) / (unique regimes total)

coverage >= 0.75 → REGIME_INDEPENDENT (works in any regime)
coverage <= 0.25 → REGIME_SPECIFIC    (only in one regime)
else             → MULTI_REGIME
```

---

## 8. Cross-Year Analysis

`CrossYearAnalyzer.analyze(year_results)` produces two record sets:

### CrossYearDNARecord

One record per unique DNA id found in any year, containing:
- `years_present / years_absent` — chronological lists
- `confidence_by_year` — per-year confidence score
- `lifecycle_label` — STABLE / STRENGTHENING / WEAKENING / EMERGING / DISAPPEARING / SPORADIC
- `regime_dependency` — REGIME_INDEPENDENT / MULTI_REGIME / REGIME_SPECIFIC
- `survival_score` — 0.0 to 1.0 (fraction of years present)
- `confidence_trend` — RISING / FALLING / STABLE / VOLATILE

### CrossYearEdgeRecord

One record per edge (DNA that crossed the `dna_edge_threshold` in ≥1 year), containing:
- `years_active / years_inactive`
- `lifecycle_label`, `trend`, `peak_confidence`, `peak_confidence_year`

---

## 9. Integration with IIOS V1.0

HKAP uses IIOS V1.0 components without modification:

| Component | HKAP usage |
|---|---|
| `PointInTimeUniverseEngine` | `get_universe(date, name)` per year |
| `PopulationClassifier` | 1 fresh instance per year, scoped to year dir |
| `DNADiscoveryEngine` | 1 fresh instance per year |
| `DNAConsensusEngine` | 1 fresh instance per year |
| `IDRRepository` | 1 fresh instance per year with year-specific db path |
| `ScientificDirector` | 1 fresh instance per year (annual review) |

The **live IDR** (`data/mls/institutional_dna.db`) is **never touched** during HKAP.
`HKAPConfig.merge_to_live_idr = False` is immutable.

---

## 10. Live Merge Gate

After all years complete, `FINAL_INSTITUTIONAL_KNOWLEDGE_RECOMMENDATION.md`
is generated with Tier 1 (unconditionally stable) and Tier 2 (strengthening)
DNA recommended for promotion.

The live merge is NOT automatic. It requires:
1. All configured years to have status=COMPLETE
2. Scientific Director review of the final recommendation document
3. Explicit call to `HKAPEngine.request_live_merge()` — which always raises
   `HKAPError` in V1.0, directing the operator to the manual process

This prevents accidental contamination of the live trading system with historical
patterns that have not been reviewed.

---

## 11. Final Synthesis Questions

The synthesis answers 8 Scientific Director questions:

1. **Which DNA survived every market regime?** → Tier 1: STABLE + REGIME_INDEPENDENT
2. **Which DNA was regime-specific?** → REGIME_SPECIFIC records in DNA Evolution Report
3. **Which features predicted major winners?** → Winner DNA in yearly reports
4. **Which sectors repeatedly generated institutional leadership?** → sector_leaders across years
5. **Which market personalities repeated?** → Behavioural Cluster Report
6. **Which edges strengthened through time?** → Tier 2: RISING trend edges
7. **Which edges disappeared permanently?** → DISAPPEARING lifecycle records
8. **What becomes permanent institutional knowledge?** → Tiers 1 + 2, pending SD approval

---

## 12. Configuration

See `hkap/hkap_config.py` for full configuration reference.

Key constraints enforced at construction time:
- `forward_only` must remain True
- `merge_to_live_idr` must remain False
- `years` must be non-empty

Key tunable parameters:
- `years` — which calendar years to study (default: 2015–2026)
- `dna_edge_threshold` — minimum confidence to be an "active edge" (default: 0.60)
- `max_symbols` — symbols per year (default: 150)
- `resume_on_restart` — skip completed years on restart (default: True)
- `dry_run` — no disk writes (default: False)
