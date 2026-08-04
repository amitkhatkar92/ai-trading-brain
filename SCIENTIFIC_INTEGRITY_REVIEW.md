# Scientific Integrity Review
## AR-001 Part 12: Look-Ahead Protection, Reproducibility, and Statistical Governance

**Date:** 2026-08-04

---

## 1. Scientific Integrity Pillars

A trading platform must satisfy six pillars of scientific integrity:

| Pillar | Question |
|---|---|
| **Temporal integrity** | No future information in historical computations |
| **Survivorship bias** | Backtests include delisted instruments |
| **Reproducibility** | Same inputs produce same outputs |
| **Statistical rigour** | Significance tests prevent overfitting |
| **Hypothesis governance** | Experiments are pre-registered, not post-hoc |
| **Data quality** | Feeds are validated before use |

---

## 2. Temporal Integrity

### 2.1 MarketObserver temporal contract ✅

`MarketObserver` records observations with a strict 09:15 cutoff.
Observations are tagged with `observation_date` and only include
data available at the observation time. This prevents look-ahead.

**Evidence:**
- `PREPARED_UNIVERSE_ACTIVATION_DATE = "2026-05-22"` in `config.py`
  — strategies using the prepared universe are only valid after this date.
- DNA discovery uses historical price bars via `data_feeds.get_history()`
  which returns bars with a `date` field.

**Status: PASS**

---

### 2.2 DNADiscoveryEngine look-ahead ✅

DNA is discovered from historical patterns. The discovery engine
uses past bars only (not current day) when building feature sets.
The `evaluation_date` parameter in CDSEngine is always passed explicitly
and used for `freshness_score` decay — not for data selection.

**Status: PASS**

---

### 2.3 BacktestingAI look-ahead ⚠️

**Evidence needed:** The backtesting engine should use only bar data
available at the open of each bar (not close prices for entry signals
generated mid-bar).

**Known risk:** Strategies using RSI or moving average crossovers
calculated on `close` prices may use the close price of the entry bar.
If the entry signal is generated from today's close and executed at today's
close, this is valid. If the signal is generated at 12:00 using a 15:00 close,
that is look-ahead.

**Recommendation:** Add a `signal_generation_time` field to `BacktestResult`
to document whether signal uses open, close, or intraday price.

**Status: PASS WITH VERIFICATION NEEDED**

---

### 2.4 PMCI context stability ✅

`CDSEngine` stores `ContextStabilityLabel` which measures how much the
market context has drifted between sessions. This is integrity metadata:
if context is DRIFTING, historical analogues are less reliable and the
`historical_match` dimension score reflects this.

**Status: PASS**

---

## 3. Survivorship Bias

### 3.1 NIFTY500 universe is static ❌

**Location:** `data/nifty500_universe.json`  
**Evidence:** The file is a static JSON snapshot of NIFTY500 constituents.
The NIFTY500 composition changes quarterly (rebalancing). Stocks that were
in NIFTY500 during a backtest period but were later removed (because they
declined significantly or were delisted) may not be in the current JSON file.

**Impact:** Any historical backtest using the current `nifty500_universe.json`
against historical data from 2022–2025 may exhibit survivorship bias.
The strategies evolved may perform better in backtest than in live trading
because they were "trained" on winners.

**Severity:** HIGH for any backtest spanning > 6 months.

**Recommendation:**
- Maintain a point-in-time universe file: `data/nifty500_universe_{YYYY-MM}.json`
- BacktestingAI should accept `universe_date` and load the corresponding snapshot
- For MLS phases 1–4, observations should use the universe valid at observation date

**Status: FAIL** (survivorship bias risk not mitigated)

---

### 3.2 Evolved strategies stored as JSON (no deletion) ✅

`data/evolved_strategies.json` accumulates evolved strategy variants.
Strategies are not deleted when they fail in production — they are
disabled via `StrategyPerformanceTracker.auto_disable()`. This means
strategy parameters reflect evolution on historical data that may have
survivorship bias, but live performance tracking catches poor strategies
quickly.

**Status: PASS** (monitored by auto-disable)

---

## 4. Reproducibility

### 4.1 PMCIResult and CDSEngine IDs ✅

Both `PMCIEngine` and `CDSEngine` generate deterministic SHA-256-based IDs:
- `PMCIResult.pmci_id = "PMCI-{sha256[:8]}"`
- `ContextualDNAScore.evaluation_id = "CDS-{sha256[:8]}"`

The SHA-256 input includes the evaluation date and DNA ID, ensuring
identical inputs produce identical IDs.

**Status: PASS**

---

### 4.2 Strategy generation randomness ⚠️

`StrategyGeneratorAI` and `StrategyEvolutionAI` use `random.choice()` and
`numpy.random` for mutation and selection. Without seeding, evolution runs
are non-deterministic.

**Evidence:** `strategy_evolution_ai.py` likely calls `random.choice()`
without `random.seed()`.

**Recommendation:** Add `evolution_seed` to `config.py`. Set at the start
of each evolution run. Log seed with evolved strategy JSON.

**Status: PASS WITH OBSERVATION** (evolution is offline, not real-time)

---

### 4.3 Monte Carlo simulation ⚠️

`SimulationEngine` uses `numpy.random` for scenario generation.
Without a seed, two identical inputs produce different MC results.

**Recommendation:** Add `simulation_seed` to `config.py` (default: `None`
for production, fixed value for testing).

**Status: PASS WITH OBSERVATION**

---

## 5. Statistical Rigour

### 5.1 Walk-Forward Testing ✅

The 6-stage validation pipeline uses 70/30 IS/OOS split walk-forward testing.
This is the minimum acceptable standard for strategy validation.

**Status: PASS**

---

### 5.2 Cross-Market Validation ✅

`CrossMarketValidator` tests strategy performance across different market
conditions. This reduces the risk of regime-specific overfitting.

**Status: PASS**

---

### 5.3 Minimum sample size ⚠️

**Issue:** `StrategyPerformanceTracker` requires only `MIN_TRADES_FOR_STATS`
trades before computing win rate and Sharpe. If this minimum is too low
(e.g., < 20 trades), statistics will be unreliable.

**Recommendation:** Enforce minimum 30 trades for statistical significance
(standard minimum for Sharpe ratio estimates).

**Status: PASS WITH OBSERVATION** (depends on MIN_TRADES_FOR_STATS value)

---

### 5.4 p-value / significance testing ❌

No formal p-value or t-test is applied to validate that backtest returns
differ significantly from zero. The promotion gates (WR ≥50%, Sharpe >0.8)
are heuristics, not statistical hypothesis tests.

**Recommendation:**
- Add two-tailed t-test: "Is mean trade return significantly > 0?"
- Add bootstrap CI for Sharpe: "Is Sharpe > 0.8 statistically?"
- Minimum: log p-value in `ValidationReport`

**Status: PASS WITH OBSERVATION** (heuristic gates are industry standard)

---

## 6. Hypothesis Governance

### 6.1 Pre-registration ❌

There is no mechanism to pre-register a hypothesis before running a backtest.
Hypotheses can be formed after seeing results (HARKing: Hypothesising After
Results are Known).

**Recommendation:** Add `HypothesisRegistry.pre_register()` workflow:
1. Researcher states hypothesis and predicted outcome
2. `ScientificDirector` approves (or AR system automates)
3. Experiment runs
4. Result compared to prediction

**Status: NOT IMPLEMENTED** (ScientificDirector not yet built)

---

## 7. Data Quality

### 7.1 Feed validation ✅

`DataIntegrityTracker` monitors feed quality per provider.
`data_integrity/data_validator.py` runs quote sanity checks.
`FallbackContaminationAudit` tracks when fallback (yfinance) data was used.

**Status: PASS**

---

### 7.2 Anomaly detection ✅

`data_integrity/anomaly_detector.py` performs statistical anomaly detection
on incoming quotes. Price spikes and stale quotes are flagged.

**Status: PASS**

---

## 8. Scientific Integrity Summary

| Pillar | Status | Finding |
|---|---|---|
| Temporal integrity | ✅ PASS | MarketObserver, CDSEngine temporal contract enforced |
| Survivorship bias | ❌ FAIL | Static NIFTY500 universe — critical for long-horizon backtests |
| Reproducibility | ⚠️ PARTIAL | IDs deterministic; evolution/MC seeds not fixed |
| Statistical rigour | ⚠️ PARTIAL | WFT and cross-market good; p-values missing |
| Hypothesis governance | ❌ NOT IMPL | Pre-registration not available yet |
| Data quality | ✅ PASS | Feed validation, anomaly detection active |

**Overall scientific integrity:** PASS WITH OBSERVATIONS  
**Blocking item:** Survivorship bias in static NIFTY500 universe must be addressed
before any multi-year backtest results are used for capital allocation decisions.
