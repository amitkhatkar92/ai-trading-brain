# Institutional Performance Analytics Framework

**C8 Execution Analytics & Intelligence — Phase 1, Module 3**

---

## Overview

The Performance Analytics Framework transforms execution operational data into institutional performance intelligence.

It computes KPIs, trends, benchmarks, aggregations, and efficiency metrics.

**It NEVER performs predictive forecasting.**  
**It NEVER generates alerts.**  
**It NEVER executes trades.**

---

## Architecture

```
PerformanceAnalyticsEngine          ← PRIMARY PUBLIC INTERFACE
    └── PerformanceManager          ← orchestrates full cycle
            ├── PerformanceValidator
            ├── PerformanceAnalyticsRegistry
            ├── PerformanceCollector        ← extracts raw data from snapshots
            ├── PerformanceCalculator       ← computes all 19 KPIs (pure Python)
            ├── PerformanceAggregator       ← rolling window aggregation
            ├── PerformanceTrendAnalyzer    ← linear regression trend detection
            ├── PerformanceBenchmark        ← compares against thresholds
            └── PerformanceScorecardBuilder ← grades overall performance
```

---

## Analytics Cycle

```
1. Validate request
2. Register request
3. Collect data from snapshots  →  CollectedData
4. Calculate KPIs               →  Dict[KPIType, KPIValue]
5. Aggregate with window        →  Dict[KPIType, KPIValue]
6. Analyse trends (optional)    →  List[TrendAnalysis]
7. Compare benchmarks (optional)→  BenchmarkReport
8. Build scorecard (optional)   →  PerformanceScorecard
9. Publish snapshot             →  PerformanceSnapshot
10. Build report                →  PerformanceAnalyticsReport
11. Record stats / history / events
12. Return PerformanceAnalyticsReport
```

---

## KPIs (19 institutional metrics)

| KPI | Domain | Unit |
|---|---|---|
| EXECUTION_SUCCESS_RATE | Execution | ratio |
| EXECUTION_FAILURE_RATE | Execution | ratio |
| AVG_EXECUTION_TIME_MS | Execution | ms |
| MEDIAN_EXECUTION_TIME_MS | Execution | ms |
| P95_LATENCY_MS | Execution | ms |
| P99_LATENCY_MS | Execution | ms |
| RECOVERY_SUCCESS_RATE | Recovery | ratio |
| MEAN_TIME_TO_RECOVERY_MS | Recovery | ms |
| GATEWAY_AVAILABILITY | Gateway | ratio |
| BROKER_AVAILABILITY | Broker | ratio |
| MONITORING_AVAILABILITY | Monitoring | ratio |
| SYSTEM_THROUGHPUT | Infrastructure | ratio |
| QUEUE_EFFICIENCY | Infrastructure | ratio |
| ORDER_COMPLETION_RATE | Order | ratio |
| POSITION_ACCURACY | Position | ratio |
| RISK_RULE_EFFECTIVENESS | Risk | ratio |
| PORTFOLIO_EFFICIENCY | Portfolio | ratio |
| STRATEGY_EFFICIENCY | Strategy | ratio |
| RESOURCE_UTILIZATION | Infrastructure | ratio |

---

## Performance Domains (11)

`EXECUTION` · `ORDER` · `POSITION` · `RISK` · `GATEWAY` · `MONITORING` ·
`RECOVERY` · `BROKER` · `PORTFOLIO` · `STRATEGY` · `INFRASTRUCTURE`

---

## Aggregation Windows (10)

`REAL_TIME` · `ONE_MINUTE` · `FIVE_MINUTES` · `FIFTEEN_MINUTES` ·
`THIRTY_MINUTES` · `ONE_HOUR` · `DAILY` · `WEEKLY` · `MONTHLY` · `CUSTOM`

---

## Performance Grades

| Grade | Threshold |
|---|---|
| EXCELLENT | ≥ 0.90 |
| GOOD | ≥ 0.75 |
| ACCEPTABLE | ≥ 0.60 |
| POOR | ≥ 0.40 |
| CRITICAL | < 0.40 |

---

## Usage

```python
from iios.execution.analytics.performance import (
    PerformanceAnalyticsEngine,
    PerformanceDomain,
    AggregationWindow,
)

engine = PerformanceAnalyticsEngine()
engine.start()

# Full cycle
request = engine.factory.create_request(
    domain             = PerformanceDomain.EXECUTION,
    window             = AggregationWindow.FIVE_MINUTES,
    include_trends     = True,
    include_benchmarks = True,
    include_scorecard  = True,
)
report = engine.process(request)

print(report.kpi_count)           # 19
print(report.scorecard.grade)     # PerformanceGrade.GOOD
print(report.processing_ms)       # <float>

# Convenience methods
kpi_report   = engine.calculate_kpis(PerformanceDomain.EXECUTION)
trends       = engine.analyze_trends(PerformanceDomain.EXECUTION)
benchmarks   = engine.compare_benchmarks(PerformanceDomain.EXECUTION)
scorecard    = engine.generate_scorecard(PerformanceDomain.EXECUTION)

# Observability
stats = engine.get_statistics()
hist  = engine.get_history()

engine.stop()
```

---

## Module Layout

```
iios/execution/analytics/performance/
├── __init__.py
├── constants.py
├── exceptions.py
├── performance_kpi.py
├── performance_context.py
├── performance_request.py
├── performance_response.py
├── performance_collector.py
├── performance_calculator.py
├── performance_aggregator.py
├── performance_benchmark.py
├── performance_trend_analyzer.py
├── performance_scorecard.py
├── performance_validation.py
├── performance_statistics.py
├── performance_history.py
├── performance_events.py
├── performance_factory.py
├── performance_registry.py
├── performance_manager.py
└── performance_analytics_engine.py
```

---

## Error Codes

| Code | Exception |
|---|---|
| PA-000 | PerformanceAnalyticsError (base) |
| PA-001 | PerformanceEngineNotRunningError |
| PA-002 | PerformanceRequestNotFoundError |
| PA-003 | PerformanceCalculationError |
| PA-004 | PerformanceValidationError |
| PA-005 | PerformanceDataInsufficientError |
| PA-006 | PerformanceBenchmarkError |
| PA-007 | PerformanceTrendError |
| PA-008 | PerformanceAggregationError |

---

## Design Principles

- **Pure Python arithmetic** — no NumPy, no SciPy, no external math libraries
- **Immutable value objects** — all output types are frozen dataclasses
- **Thread-safe** — RLock on stats, Lock on history/registry
- **Bounded history** — deque(maxlen=DEFAULT_MAX_HISTORY)
- **Graceful degradation** — analytics cycle never raises to caller; returns error report
- **M2 compatibility** — `process()` accepts both `PerformanceRequest` and `str` request_id
