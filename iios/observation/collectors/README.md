# IIOS Observation Collection Framework

A modular, plugin-based framework for collecting observations from every
internal and external data source used by IIOS.

---

## Overview

The Collection Framework provides a standardised way to:

- Pull data from any external source (broker, exchange, news, macro, …)
- Push real-time events into the observation pipeline
- Schedule and execute collectors reliably with retry, circuit breaking, and rate limiting
- Monitor collector health and surface problems early
- Extend the system with third-party plugin collectors

---

## Quick Start

```python
from iios.observation.collectors import (
    CollectorFactory, get_collector_manager,
    ScheduleConfig, ScheduleType,
)

# 1. Get the shared manager
mgr = get_collector_manager()
mgr.initialise()

# 2. Register a built-in sync collector from a plain dict
mgr.register_from_dict({
    "name": "my_feed",
    "type": "sync",
})

# 3. Run it once
result = mgr.run("my_feed")
print(result.count)  # number of observations collected

# 4. Or schedule it to run every 60 s
from iios.observation.collectors import ScheduleConfig, ScheduleType
sc = ScheduleConfig(schedule_type=ScheduleType.INTERVAL, interval_s=60.0)
mgr.schedule("my_feed", sc)
mgr.start_scheduler()
```

---

## Architecture

```
CollectorManager          ← top-level orchestrator
  ├── CollectorRegistry   ← thread-safe collector store
  ├── CollectorScheduler  ← background tick loop (INTERVAL, EVENT, …)
  ├── CollectorExecutor   ← ThreadPoolExecutor, run_one / run_many
  ├── CollectorMonitor    ← periodic health checks, stale detection
  ├── CollectorMetrics    ← per-collector run records and summaries
  └── CollectorFactory    ← build collectors from config dicts / code
```

Each collector follows a linear lifecycle:

```
IDLE → INITIALISING → CONFIGURED → AUTHENTICATING → CONNECTING
     → COLLECTING → IDLE  (repeats)
     → PAUSED            (manual hold)
     → STOPPING → STOPPED
```

---

## Lifecycle Methods

| Method | Description |
|---|---|
| `initialise()` | One-time setup (load config, validate) |
| `configure(**kw)` | Update config fields at runtime |
| `authenticate()` | Acquire credentials / tokens |
| `connect()` | Open persistent connection |
| `run()` | Execute the collect → normalise → publish pipeline |
| `pause()` / `resume()` | Temporarily stop scheduling |
| `health_check()` | Return a dict with current state |
| `shutdown()` | Release all resources |

---

## Reliability Features

### Retry

```python
from iios.observation.collectors import RetryPolicy, RetryStrategy

policy = RetryPolicy(
    max_retries  = 3,
    strategy     = RetryStrategy.EXPONENTIAL,
    base_delay_s = 1.0,
    max_delay_s  = 30.0,
    jitter       = True,
)
config.retry_policy = policy
```

Strategies: `NONE`, `FIXED`, `LINEAR`, `EXPONENTIAL`, `FIBONACCI`.

### Circuit Breaker

```python
from iios.observation.collectors import CircuitBreaker

cb = CircuitBreaker(failure_threshold=5, recovery_timeout_s=30.0)
config.circuit_breaker = cb
```

States: `CLOSED` → `OPEN` (on *n* failures) → `HALF_OPEN` (after timeout) → `CLOSED` (on success).

### Rate Limiter

```python
from iios.observation.collectors import RateLimiter

rl = RateLimiter(max_calls=60, window_s=60.0)  # 1 req/s average
config.rate_limiter = rl
```

Uses a sliding-window counter.

---

## How to Write a Custom Collector

### 1. Subclass the right base

```python
from iios.observation.collectors import SyncCollector, CollectorConfig
from iios.observation.collectors import CircuitBreaker, RateLimiter, RetryPolicy

class MyFeedCollector(SyncCollector):
    def _do_collect(self):
        """Fetch raw data and return anything."""
        return my_api.get_data()

    def _do_normalise(self, raw) -> list:
        """Convert raw data to Observation objects."""
        return [self._make_observation(content=item) for item in raw]
```

### 2. Build the config

```python
from iios.observation.observation_constants import ObservationSource, ObservationType

cfg = CollectorConfig(
    name             = "my_feed",
    source           = ObservationSource.BROKER_DHAN,
    obs_type         = ObservationType.MARKET_DATA,
    poll_interval_s  = 30.0,
    retry_policy     = RetryPolicy(max_retries=3),
    circuit_breaker  = CircuitBreaker(failure_threshold=5),
    rate_limiter     = RateLimiter(max_calls=120, window_s=60.0),
)
collector = MyFeedCollector(cfg)
```

### 3. Register and run

```python
mgr = get_collector_manager()
mgr.initialise()
mgr.register(collector)
mgr.run("my_feed")
```

---

## Collector Types

| Class | Execution mode | Use when |
|---|---|---|
| `SyncCollector` | `SYNC` | Simple pull-based HTTP / SDK calls |
| `AsyncCollector` | `ASYNC` | `asyncio`-native clients |
| `StreamCollector` | `STREAM` | WebSocket / generator-based feeds |
| `BatchCollector` | `BATCH` | Paginated APIs, resumable with checkpoints |
| `ScheduledCollector` | any | Needs cron-like or interval scheduling |
| `EventCollector` | `SYNC` | Receives pushed events (internal bus, callbacks) |

---

## Schedule Types

| `ScheduleType` | Triggers |
|---|---|
| `MANUAL` | Only when explicitly called |
| `INTERVAL` | Every `interval_s` seconds |
| `CRON` | At times matching `cron_expr` (not yet executed — reserved) |
| `MARKET_HOURS` | Only during 09:15 – 15:30 IST Mon–Fri |
| `EVENT` | When `trigger_event(name)` is called |
| `DEPENDENCY` | When all listed collectors have finished |

---

## Plugin Guide

Third-party collectors subclass `PluginCollector`:

```python
from iios.observation.collectors.categories import PluginCollector
from iios.observation.collectors import CollectorConfig
from iios.observation.observation_constants import ObservationSource, ObservationType

class AlphaVantagePlugin(PluginCollector):
    PLUGIN_NAME    = "alpha_vantage"
    PLUGIN_VERSION = "1.0.0"
    PLUGIN_AUTHOR  = "Your Name"

    def _do_collect(self):
        return alpha_vantage_client.get_quote("RELIANCE")

    def _do_normalise(self, raw) -> list:
        return [self._make_observation(content=raw)]
```

Register via `CollectorFactory`:

```python
factory = get_collector_factory()
factory.register_type("alpha_vantage", AlphaVantagePlugin)
collector = factory.from_dict({"name": "av1", "type": "alpha_vantage"})
```

---

## Category Base Classes

Each category enforces the correct `CollectorCategory` and default `ObservationType`:

| Class | Category | Default obs_type |
|---|---|---|
| `MarketDataCollector` | `MARKET_DATA` | — |
| `NewsCollector` | `NEWS` | `NEWS` |
| `MacroCollector` | `MACRO` | `ECONOMIC` |
| `CorporateActionCollector` | `CORPORATE` | `CORPORATE_ACTION` |
| `FinancialStatementCollector` | `FINANCIAL` | — |
| `ExchangeCollector` | `EXCHANGE` | `MARKET_DATA` |
| `BrokerCollector` | `BROKER` | `ORDER_EVENT` |
| `AlternativeDataCollector` | `ALTERNATIVE` | — |
| `SocialMediaCollector` | `SOCIAL` | `SOCIAL` |
| `ResearchCollector` | `RESEARCH` | `RESEARCH` |
| `InternalSystemCollector` | `INTERNAL` | `SYSTEM_EVENT` |
| `PluginCollector` | `PLUGIN` | — |

---

## Monitoring

```python
from iios.observation.collectors import get_collector_manager

mgr = get_collector_manager()
mgr.start_monitor()                # background health checks every 60 s

# Inspect a single collector
report = mgr.health("my_feed")
print(report.is_healthy, report.warnings)

# System-wide summary
summary = mgr.system_health()
# {"status": "healthy", "total": 5, "healthy": 5, "unhealthy": 0, ...}
```

Unhealthy conditions detected automatically:
- **Stale** — no successful run in `stale_threshold_s` (default 300 s)
- **High error rate** — >20 % of recent runs failed
- **Circuit open** — circuit breaker tripped
- **Stopped** — collector reached `STOPPED` state unexpectedly

---

## Singletons

All infrastructure components follow the `get_X()` / `reset_X()` singleton pattern:

```python
get_collector_manager()   → CollectorManager
get_collector_registry()  → CollectorRegistry
get_collector_factory()   → CollectorFactory
get_collector_scheduler() → CollectorScheduler
get_collector_executor()  → CollectorExecutor
get_collector_monitor()   → CollectorMonitor
get_collector_metrics()   → CollectorMetrics
```

In tests, call `reset_X()` in `setUp` / `tearDown` to guarantee isolation.
