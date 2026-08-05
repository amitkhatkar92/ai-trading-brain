# HKAP-001 API Reference

## HKAPEngine

Top-level orchestrator. Entry point for all HKAP operations.

```python
from hkap import HKAPEngine, HKAPConfig

engine = HKAPEngine(config=HKAPConfig(), ptue=None)
```

### Constructor

| Parameter | Type | Default | Description |
|---|---|---|---|
| `config` | `HKAPConfig` | `HKAPConfig()` | Program configuration |
| `ptue` | `PointInTimeUniverseEngine` | auto-built | Universe provider |

If `ptue` is `None`, a `PointInTimeUniverseEngine(PTUEConfig())` is constructed automatically.

### Methods

#### `run(years=None, force=False) -> HKAPSummary`

Run all configured years in chronological order, then synthesis.

- `years`: override subset of `config.years` to run
- `force`: if `True`, re-run years already marked COMPLETE
- Returns `HKAPSummary` with overall statistics
- Year failures are logged and skipped; synthesis requires ≥2 completed years

#### `run_year(year: int) -> YearKnowledgePackage`

Run a single year's 9-stage pipeline.

- Raises `HKAPError` if `year` not in `config.years`
- `FutureDataLeakError` is raised by `YearRunner` if `prior_context` contains future years (impossible from this method — the engine always passes only past years)
- Persists result to `data/hkap/{year}/year_knowledge_package.json`

#### `run_synthesis() -> List[str]`

Run cross-year analysis and generate 8 synthesis reports.

- Requires ≥2 completed years
- Raises `HKAPError` if insufficient completed years
- Returns list of generated file paths

#### `status() -> HKAPStatus`

Return current program status.

#### `history() -> Dict[int, YearKnowledgePackage]`

Return all loaded year packages (completed + failed).

#### `request_live_merge() -> None`

Always raises `HKAPError`. The live IDR merge requires manual SD review.

---

## HKAPConfig

```python
from hkap import HKAPConfig

config = HKAPConfig(
    years           = list(range(2015, 2027)),
    data_root       = "data/hkap",
    reports_root    = "data/hkap/reports",
    universe_name   = "NIFTY500",
    max_symbols     = 150,
    dna_edge_threshold = 0.60,
    min_trading_days   = 50,
    download_lookback_days = 300,
    request_timeout = 30,
    dry_run         = False,
    resume_on_restart = True,
)
```

### Fields

| Field | Type | Default | Description |
|---|---|---|---|
| `years` | `List[int]` | 2015–2026 | Calendar years to study |
| `data_root` | `str` | `"data/hkap"` | Root for all year data |
| `reports_root` | `str` | `"data/hkap/reports"` | Root for markdown reports |
| `universe_name` | `str` | `"NIFTY500"` | Universe to use |
| `max_symbols` | `int` | `150` | Symbols per year |
| `dna_edge_threshold` | `float` | `0.60` | Min confidence to be an active edge |
| `min_trading_days` | `int` | `50` | Min days to consider a year valid |
| `download_lookback_days` | `int` | `300` | Days before year start to download |
| `request_timeout` | `int` | `30` | yfinance request timeout |
| `forward_only` | `bool` | **True (immutable)** | Future data leak protection |
| `merge_to_live_idr` | `bool` | **False (immutable)** | Live IDR merge protection |
| `dry_run` | `bool` | `False` | No disk writes |
| `resume_on_restart` | `bool` | `True` | Skip completed years |

### Properties

- `sorted_years: List[int]` — `config.years` in ascending order

### Validation

- Setting `forward_only=False` raises `ValueError`
- Setting `merge_to_live_idr=True` raises `ValueError`
- Empty `years` list raises `ValueError`

---

## YearRunner

```python
from hkap import YearRunner

runner = YearRunner(
    year          = 2020,
    config        = HKAPConfig(),
    ptue          = ptue,
    prior_context = [pkg_2019],   # MUST all have year < 2020
)
pkg = runner.run()
```

### Constructor

Raises `FutureDataLeakError` if any element of `prior_context` has `year >= year`.

### Methods

#### `run() -> YearKnowledgePackage`

Runs all 9 stages with isolation. Stage failures are logged and skipped.
Returns `YearKnowledgePackage` with status COMPLETE or FAILED.

### 9 Pipeline Stages

| Stage constant | Description |
|---|---|
| `_STAGE_UNIVERSE` | Get symbols from PTUE |
| `_STAGE_SNAPSHOTS` | Download/cache yfinance data, build snapshot dicts |
| `_STAGE_MLS` | Classify, discover, accumulate into year-scoped IDR |
| `_STAGE_IDR` | Read IDR, build YearDNASnapshot |
| `_STAGE_PROFILE` | Classify market personality and regime |
| `_STAGE_EDGES` | Compute active edges, compare to prior year |
| `_STAGE_CROSS_YEAR` | Log DNA count trend vs prior |
| `_STAGE_SD_REVIEW` | ScientificDirector monthly review |
| `_STAGE_REPORTS` | Generate 5 per-year markdown reports |

---

## HistoricalSnapshotBuilder

```python
from hkap.snapshot_builder import HistoricalSnapshotBuilder

builder = HistoricalSnapshotBuilder(
    cache_dir     = "data/hkap/2020/raw",
    sector_map    = {"RELIANCE": "Energy", "TCS": "IT"},
    dry_run       = False,
    lookback_days = 300,
)
snapshots = builder.build_year(year=2020, symbols=["RELIANCE", "TCS"])
```

Returns `List[dict]` — one dict per trading day in `year`.

Each dict has the same structure as `DailyMarketSnapshot.to_dict()` plus raw
`observations` as list of dicts.

---

## MarketProfiler

```python
from hkap import MarketProfiler

profiler = MarketProfiler()
profile = profiler.profile_year(year=2020, snapshots=snapshot_dicts, sector_map=sector_map)
```

### Methods

#### `profile_year(year, snapshots, sector_map) -> YearMarketProfile`

Classifies the year's market regime, personality, sector leadership, and behaviour clusters.

Returns `YearMarketProfile` with fields:

| Field | Description |
|---|---|
| `dominant_regime` | Most common regime (BULL_TREND etc.) |
| `regime_distribution` | `{regime: fraction}` |
| `volatility_level` | LOW / MEDIUM / HIGH / EXTREME |
| `market_personality` | Human label (TRENDING_BULL, VOLATILE_MIXED, etc.) |
| `sector_leaders` | Top 3 outperforming sectors |
| `sector_rotations` | Detected sector rotation events |
| `breadth_score` | Average breadth across all days |
| `momentum_strength` | 0=mean-reversion, 1=trending |
| `mean_reversion_strength` | 1 - momentum_strength |
| `institutional_activity` | Proxy for institutional footprint |
| `behaviour_clusters` | List of behavioural labels |
| `key_observations` | List of markdown bullet points |
| `index_return_ytd` | Approximate index YTD return |
| `peak_drawdown` | Approximate max drawdown |
| `trading_days` | Count of snapshots |

### Market Personality Labels

| Label | Condition |
|---|---|
| `TRENDING_BULL` | Dominant BULL_TREND, positive return |
| `TRENDING_BEAR` | Dominant BEAR_MARKET, negative return |
| `VOLATILE_MIXED` | Dominant VOLATILE_MARKET |
| `SIDEWAYS_CHOPPY` | Dominant RANGE_MARKET, small return |
| `RECOVERY` | BULL_TREND dominant, H1 negative / H2 positive |
| `CORRECTION` | BEAR_MARKET dominant, H1 positive / H2 negative |
| `ACCUMULATION` | Low volatility, positive return |
| `DISTRIBUTION` | Dominant RANGE or BEAR, negative return |

---

## CrossYearAnalyzer

```python
from hkap import CrossYearAnalyzer

analyzer = CrossYearAnalyzer()
dna_records, edge_records = analyzer.analyze(year_results)
```

### Methods

#### `analyze(year_results: Dict[int, YearKnowledgePackage]) -> Tuple[List[CrossYearDNARecord], List[CrossYearEdgeRecord]]`

Computes lifecycle and regime dependency for all DNA patterns and edges
found across the supplied years.

---

## HKAPReportGenerator

```python
from hkap import HKAPReportGenerator

gen = HKAPReportGenerator(config)
paths = gen.generate_year_reports(pkg)
paths = gen.generate_synthesis_reports(all_packages, dna_records, edge_records)
```

### Methods

#### `generate_year_reports(pkg: YearKnowledgePackage) -> List[str]`

Generates 5 markdown files to `{reports_root}/{year}/`.

Returns list of 5 absolute file paths:
- `YEAR_{year}_KNOWLEDGE.md`
- `YEAR_{year}_DNA.md`
- `YEAR_{year}_EDGES.md`
- `YEAR_{year}_MARKET_PROFILE.md`
- `YEAR_{year}_RESEARCH_SUMMARY.md`

If `config.dry_run=True`, paths are returned but files are not written.

#### `generate_synthesis_reports(all_packages, dna_records, edge_records, summary=None) -> List[str]`

Generates 8 markdown files to `{reports_root}/synthesis/`.

Returns list of 8 absolute file paths:
- `HKAP_MASTER_REPORT.md`
- `MARKET_EVOLUTION_REPORT.md`
- `DNA_EVOLUTION_REPORT.md`
- `EDGE_EVOLUTION_REPORT.md`
- `BEHAVIOURAL_CLUSTER_REPORT.md`
- `REGIME_EVOLUTION_REPORT.md`
- `KNOWLEDGE_SYNTHESIS_REPORT.md`
- `FINAL_INSTITUTIONAL_KNOWLEDGE_RECOMMENDATION.md`

---

## Data Models

### YearKnowledgePackage

```python
@dataclass
class YearKnowledgePackage:
    year:                  int
    status:                str   # YearStudyStatus value
    market_profile:        Optional[YearMarketProfile]
    dna_snapshot:          Optional[YearDNASnapshot]
    edge_snapshot:         Optional[YearEdgeSnapshot]
    sd_review:             Optional[YearSDReview]
    prior_years_context:   List[int]
    trading_days_analyzed: int
    universe_size:         int
    completed_at:          str
    reports:               List[str]
    stage_statuses:        Dict[str, str]

    def to_dict() -> Dict
```

### YearDNASnapshot

```python
@dataclass
class YearDNASnapshot:
    year:                   int
    winner_dna:             List[str]          # DNA IDs with positive direction
    loser_dna:              List[str]          # DNA IDs with negative direction
    neutral_dna:            List[str]
    regime_specific_dna:    Dict[str, List[str]]  # regime → [dna_id]
    regime_independent_dna: List[str]
    total_discovered:       int
    high_confidence_count:  int
    median_confidence:      float
    confidence_by_id:       Dict[str, float]   # dna_id → confidence
    source_db:              str
```

### YearEdgeSnapshot

```python
@dataclass
class YearEdgeSnapshot:
    year:               int
    active_edges:       List[str]     # DNA ids with confidence >= threshold
    promoted_this_year: List[str]     # new edges vs prior year
    demoted_this_year:  List[str]
    retired_this_year:  List[str]
    survival_rate:      float         # fraction of prior edges still active
    new_edge_rate:      float
    total_prior_edges:  int
```

### CrossYearDNARecord

```python
@dataclass
class CrossYearDNARecord:
    dna_id:            str
    feature_name:      str
    direction:         str
    years_present:     List[int]
    years_absent:      List[int]
    confidence_by_year: Dict[int, float]
    regimes_observed:  List[str]
    lifecycle_label:   str            # DNALifecycleLabel value
    regime_dependency: str            # RegimeDependency value
    survival_score:    float          # 0.0 to 1.0
    confidence_trend:  str            # RISING / FALLING / STABLE / VOLATILE
```

### CrossYearEdgeRecord

```python
@dataclass
class CrossYearEdgeRecord:
    edge_id:               str
    feature_name:          str
    years_active:          List[int]
    years_inactive:        List[int]
    lifecycle_label:       str
    peak_confidence_year:  int
    peak_confidence:       float
    trend:                 str
```

### HKAPStatus

```python
@dataclass
class HKAPStatus:
    years_planned:         List[int]
    years_completed:       List[int]
    years_failed:          List[int]
    years_pending:         List[int]
    current_year:          Optional[int]
    is_synthesis_done:     bool
    total_dna_accumulated: int
    last_updated:          str

    def to_dict() -> Dict
```

### HKAPSummary

```python
@dataclass
class HKAPSummary:
    years_planned:            List[int]
    years_completed:          List[int]
    years_failed:             List[int]
    total_dna_discovered:     int
    stable_dna_count:         int
    emerging_dna_count:       int
    disappearing_dna_count:   int
    stable_edges_count:       int
    regime_specific_count:    int
    regime_independent_count: int
    synthesis_reports:        List[str]
    generated_at:             str

    def to_dict() -> Dict
```

---

## Errors

| Exception | When raised |
|---|---|
| `HKAPError` | Base error for all HKAP conditions |
| `FutureDataLeakError(requesting_year, future_year)` | `prior_context` contains year >= current year |
| `YearNotCompleteError(year)` | Accessing incomplete year knowledge |

---

## CLI Reference

```
python run_hkap.py [options]
```

| Option | Description |
|---|---|
| *(no args)* | Run all configured years + synthesis |
| `--year 2023` | Run a single year |
| `--years 2020,2021,2022` | Run specific years |
| `--synthesis` | Synthesis only (needs ≥2 completed years) |
| `--status` | Print JSON status and exit |
| `--dry-run` | No disk writes, no downloads |
| `--force` | Re-run years already marked COMPLETE |
| `--universe NIFTY500` | Universe: NIFTY500 / NIFTY100 / NIFTY50 |
| `--max-symbols 50` | Override symbol limit |
| `--year-range 2015-2025` | Inclusive year range |

---

## Output Files

### Per-year (in `data/hkap/reports/{year}/`)

| File | Contents |
|---|---|
| `YEAR_{year}_KNOWLEDGE.md` | Summary: market, DNA count, edges, SD verdict |
| `YEAR_{year}_DNA.md` | Winner/loser/regime DNA with confidence scores |
| `YEAR_{year}_EDGES.md` | Active edges, promoted, demoted, retired |
| `YEAR_{year}_MARKET_PROFILE.md` | Regime, sectors, personality, observations |
| `YEAR_{year}_RESEARCH_SUMMARY.md` | Pipeline stages, SD lessons, questions |

### Synthesis (in `data/hkap/reports/synthesis/`)

| File | Contents |
|---|---|
| `HKAP_MASTER_REPORT.md` | All years summary table, DNA lifecycle totals |
| `MARKET_EVOLUTION_REPORT.md` | Regime and personality evolution year-by-year |
| `DNA_EVOLUTION_REPORT.md` | DNA lifecycle, stable/emerging/disappearing |
| `EDGE_EVOLUTION_REPORT.md` | Edge strengthening and retirement |
| `BEHAVIOURAL_CLUSTER_REPORT.md` | Cluster frequency across years |
| `REGIME_EVOLUTION_REPORT.md` | Regime shifts and regime-specific DNA |
| `KNOWLEDGE_SYNTHESIS_REPORT.md` | Answers to 5 of 8 SD questions |
| `FINAL_INSTITUTIONAL_KNOWLEDGE_RECOMMENDATION.md` | Tier 1 + Tier 2, SD sign-off |
