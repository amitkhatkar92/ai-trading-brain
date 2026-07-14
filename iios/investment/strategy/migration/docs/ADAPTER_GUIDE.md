# Adapter Guide

## What is an Adapter?

A `LegacyStrategyAdapter` wraps a `LegacyStrategyMetadata` object and exposes
a complete `BaseStrategy`-compatible interface. The original strategy logic
is never rewritten — the adapter only translates.

---

## Adaptation Modes

| Mode | When Used | What It Does |
|---|---|---|
| `PARAMETER_BRIDGE` | Code-based strategies (`STRATEGY_GENERATOR`) | Translates parameters only; no logic change |
| `BEHAVIOR_DELEGATE` | JSON/Pattern strategies with entry conditions | Delegates entry evaluation to legacy conditions |
| `FULL_WRAP` | Evolved strategies | Full wrapping with all inherited params |
| `CUSTOM` | Non-standard strategies | Custom per-strategy logic |

---

## Creating an Adapter

### Via `AdapterFactory` (recommended)
```python
from iios.investment.strategy.migration import AdapterFactory

factory = AdapterFactory()
adapter = factory.create(metadata)
# Factory automatically selects the best mode
```

### Manual construction
```python
from iios.investment.strategy.migration import LegacyStrategyAdapter, AdaptationMode

adapter = LegacyStrategyAdapter(
    metadata=metadata,
    adaptation_mode=AdaptationMode.PARAMETER_BRIDGE,
)
```

### Inspect the adaptation plan without creating
```python
desc = factory.describe_adaptation(metadata)
print(desc["chosen_mode"])     # e.g. "parameter_bridge"
print(desc["gap_count"])       # number of interface gaps
```

---

## Using an Adapter

```python
# Standard IIOS interface
definition  = adapter.get_definition()    # StrategyDefinition
params      = adapter.get_params()        # Dict[str, Any]

# Legacy-specific extensions
risk_params = adapter.get_risk_params()   # min_rr, max_loss_pct, etc.
perf_snap   = adapter.get_performance_snapshot()
summary     = adapter.summary()

# Entry condition evaluation (legacy conditions preserved exactly)
result = adapter.evaluate_entry({"rsi": 28.0, "volume_ratio": 1.8})
# Returns True / False / None (None = no conditions or code-based)
```

---

## Adapter Registry

The `AdapterRegistry` is a thread-safe store for all created adapters.

```python
from iios.investment.strategy.migration import AdapterRegistry

registry = AdapterRegistry()
registry.register(adapter)

# Look up by strategy ID or name
found = registry.get(strategy_id)
found = registry.get_by_name("Breakout_Volume")

# Enumerate
all_adapters = registry.all()
names = registry.names()
count = registry.count()

# Remove
removed = registry.remove(strategy_id)
```

---

## What the Adapter Preserves

The following fields are guaranteed to be identical in the adapter
and the original metadata:

- `strategy_id`
- `strategy_name` (→ `adapter.name`)
- `min_rr`
- `max_loss_pct`
- `stop_loss_pct`
- `target_multiplier`
- `entry_conditions` (evaluated identically)
- `preferred_regimes` (translated, not truncated)
- `is_approved` (→ drives `StrategyStatus`)
