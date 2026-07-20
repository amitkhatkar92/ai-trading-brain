# Institutional Predictive Intelligence Framework

**C8 Execution Analytics & Intelligence — Phase 1, Module 4**

---

## Purpose

The Predictive Intelligence Framework converts historical execution analytics into forward-looking operational intelligence. It predicts execution trends, infrastructure capacity, anomaly probability, performance degradation risk, and operational availability across all execution domains.

**This framework ONLY produces operational forecasts. It MUST NOT:**
- Execute trades
- Generate trading signals
- Place, modify, or cancel orders
- Communicate with brokers
- Replace or bypass Decision Intelligence

---

## Architecture

```
PredictiveIntelligenceEngine   ← PRIMARY PUBLIC INTERFACE
  ├── PredictiveIntelligenceFactory      (request + context construction)
  └── PredictiveManager                  (full prediction cycle)
        ├── PredictiveValidator           (input validation)
        ├── PredictiveIntelligenceRegistry (active/completed requests)
        ├── PredictiveForecaster          (OLS + Holt + hybrid math)
        │     └── PredictiveModelRegistry (built-in model catalogue)
        ├── PredictiveTrendEngine         (trend classification)
        ├── PredictiveAnomalyDetector     (Z-score detection)
        ├── PredictiveCapacityEstimator   (utilisation + headroom)
        ├── PredictiveRiskEstimator       (weighted 4-signal aggregation)
        ├── PredictiveProbabilityEstimator(per-type probability mapping)
        ├── PredictiveScorer              (ConfidenceLevel scoring)
        ├── PredictiveIntelligenceStatistics (live counters)
        └── PredictiveIntelligenceHistory    (bounded history deques)
```

---

## Components

### `constants.py`
All framework-wide enumerations, thresholds, and identifiers:
- `PredictionDomain` — 10 operational domains
- `PredictionType` — 11 forecast types
- `ForecastHorizon` — 9 horizons (NEXT_MINUTE … MONTHLY + CUSTOM)
- `ConfidenceLevel`, `TrendType`, `RiskLevel`, `ForecastAlgorithm`
- `HORIZON_SECONDS` — mapping from ForecastHorizon to seconds

### `exceptions.py`
Typed exceptions with error codes (PI-000 … PI-008).

### `predictive_request.py`
`PredictionRequest` — immutable request value object.  
`make_prediction_request()` — factory function.

### `predictive_context.py`
`PredictiveContext` — bundles historical analytics and snapshot data for
one prediction cycle.  
`make_predictive_context()` — factory function.

### `predictive_response.py`
All result value objects (all frozen dataclasses):
`ForecastPoint`, `Forecast`, `ProbabilityReport`, `CapacityForecast`,
`RiskForecast`, `OperationalForecast`, `ForecastSummary`,
`PredictiveSnapshot`, `PredictionReport`.

### `predictive_model_registry.py`
`ForecastModel` + `PredictiveModelRegistry` — catalogue of built-in
forecast models (linear-v1, exponential-v1, hybrid-v1, fallback-v1).

### `predictive_forecaster.py`
Pure-Python math: OLS linear regression, Holt's double exponential
smoothing, hybrid algorithm. Algorithm selection by data availability
(n≥4 → hybrid, n≥3 → exponential, n≥2 → linear, n≥1 → fallback).

### `predictive_trend_engine.py`
Classifies directional trends per prediction type: IMPROVING, DEGRADING,
STABLE, VOLATILE, UNKNOWN.

### `predictive_anomaly_detector.py`
Z-score based anomaly detection. Combines historical anomaly rate with
extrapolated future Z-score to compute anomaly probability.

### `predictive_capacity_estimator.py`
Forecasts infrastructure utilisation and headroom for the given horizon.

### `predictive_risk_estimator.py`
Aggregates 4 weighted signals:
- Degrading forecasts (35 %)
- Low-confidence forecasts (15 %)
- Anomaly probability (25 %)
- Capacity bottleneck risk (25 %)

### `predictive_probability.py`
Maps terminal forecast values to domain-appropriate probability scores
in [0, 1] for each `PredictionType`.

### `predictive_scorer.py`
Scores `Forecast` objects against `ConfidenceLevel` thresholds; provides
aggregate helpers.

### `predictive_validation.py`
`PredictiveValidator` — validates `PredictionRequest` and
`PredictiveContext`, raises `PredictionValidationError` on failure.

### `predictive_statistics.py`
`PredictiveIntelligenceStatistics` — thread-safe counters: cycles,
forecasts, failures, processing time, accuracy.

### `predictive_history.py`
`PredictiveIntelligenceHistory` — bounded deques for reports, forecasts,
risk forecasts, capacity forecasts, events.

### `predictive_events.py`
`PredictiveIntelligenceEvent` — immutable domain event.  
7 factory functions covering the full prediction lifecycle.

### `predictive_factory.py`
`PredictiveIntelligenceFactory` — `create_request()`, `create_context()`,
`create_context_for_request()`.

### `predictive_registry.py`
`PredictiveIntelligenceRegistry` — active / completed request storage.

### `predictive_manager.py`
`PredictiveManager` — orchestrates the full 15-step prediction cycle.
Graceful degradation on any step failure — always returns a
`PredictionReport` (never raises to the caller).

### `predictive_intelligence_engine.py`
**`PredictiveIntelligenceEngine`** — primary public interface.

---

## Prediction Domains

| Domain | Description |
|---|---|
| `EXECUTION_PERFORMANCE` | Latency, fill rates, slippage trends |
| `GATEWAY_HEALTH` | Gateway saturation and availability |
| `BROKER_STABILITY` | Broker connectivity and uptime |
| `RECOVERY_PROBABILITY` | System recovery likelihood |
| `MONITORING_HEALTH` | Monitor and observer responsiveness |
| `INFRASTRUCTURE_CAPACITY` | CPU, memory, queue capacity |
| `QUEUE_BEHAVIOUR` | Order queue growth and depth |
| `LATENCY_FORECAST` | End-to-end execution latency |
| `SYSTEM_AVAILABILITY` | Overall system availability |
| `PORTFOLIO_OPERATIONAL_HEALTH` | Portfolio operational status |

---

## Forecast Types

| Type | Direction |
|---|---|
| `EXECUTION_VOLUME_FORECAST` | higher-neutral |
| `EXPECTED_LATENCY` | lower-is-better |
| `GATEWAY_SATURATION` | lower-is-better |
| `BROKER_AVAILABILITY_FORECAST` | higher-is-better |
| `RECOVERY_PROBABILITY` | higher-is-better |
| `FAILURE_PROBABILITY` | lower-is-better |
| `CAPACITY_FORECAST` | higher-neutral |
| `QUEUE_GROWTH_FORECAST` | lower-is-better |
| `PERFORMANCE_DEGRADATION_RISK` | lower-is-better |
| `INFRASTRUCTURE_UTILIZATION_FORECAST` | lower-is-better |
| `OPERATIONAL_HEALTH_SCORE` | higher-is-better |

---

## Quick Start

```python
from iios.execution.analytics.predictive import (
    PredictiveIntelligenceEngine,
    PredictionDomain,
    ForecastHorizon,
    PredictionType,
)

engine = PredictiveIntelligenceEngine()
engine.start()

# Create request and context with historical data
request = engine.factory.create_request(
    domain   = PredictionDomain.EXECUTION_PERFORMANCE,
    horizon  = ForecastHorizon.NEXT_HOUR,
)
context = engine.factory.create_context(
    request_id           = request.request_id,
    domain               = request.domain,
    horizon              = request.horizon,
    historical_analytics = {
        PredictionType.EXPECTED_LATENCY.value:    [120, 125, 119, 130, 140],
        PredictionType.OPERATIONAL_HEALTH_SCORE.value: [0.95, 0.93, 0.91, 0.89],
    },
)

report = engine.process(request, context)
print(f"Forecasts: {report.forecast_count}")
print(f"Risk:     {report.risk_forecast.risk_level}")
print(f"Capacity: {report.capacity_forecast.forecasted_utilization:.2f}")

engine.stop()
```

---

## Thread Safety

All public methods on `PredictiveIntelligenceEngine`, `PredictiveManager`,
`PredictiveIntelligenceRegistry`, `PredictiveIntelligenceHistory`, and
`PredictiveIntelligenceStatistics` are thread-safe.

Concurrent calls to `engine.process()` from multiple threads are safe.

---

## Design Invariants

1. All value objects are **frozen dataclasses** — immutable after creation.
2. Pure Python math — **no numpy, no scipy**.
3. `PredictiveManager.process()` **never raises** — always returns a
   `PredictionReport` (with `error_message` set on failure).
4. `PredictiveIntelligenceEngine` is the **only** public entry point.
5. No trading signals, no orders, no broker calls — ever.

---

## Tests

```
tests/unit/execution/analytics/predictive/
  └── test_predictive_intelligence_engine.py
```

Run with:
```sh
python -m pytest tests/unit/execution/analytics/predictive/ -v
```

---

## Version

**1.0.0** — Initial release, C8 M4.
