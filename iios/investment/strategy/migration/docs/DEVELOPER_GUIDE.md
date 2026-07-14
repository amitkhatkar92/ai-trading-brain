# Developer Guide

## Adding a New Legacy Strategy

### Code-based strategy (in `STRATEGY_PARAMS`)

Add an entry to `_KNOWN_CODE_STRATEGIES` in `legacy_registry.py`:

```python
"My_New_Strategy": {
    "min_rr":            2.0,
    "max_loss_pct":      0.02,
    "stop_loss_pct":     0.015,
    "target_multiplier": 2.0,
    "base_strategy":     "",
    "category":          "momentum",
    "direction":         "BUY",
    "preferred_regimes": ["bull_trend"],
    "compatible_regimes": ["bull_trend", "range_market"],
    "description":       "Short description of strategy logic",
    "tags":              ["momentum", "intraday"],
},
```

Then update `STRATEGY_PARAMS` in `strategy_lab/strategy_generator_ai.py` to match.

---

### JSON-discovered strategy

Add to `data/discovered_edges.json`:
```json
{
    "strategy_id": "EDG_MY_EDGE_001",
    "strategy_name": "My_Edge_Strategy",
    "min_signal_rr": 2.0,
    "max_loss_pct": 0.02,
    "precision": 0.62,
    "support": 40,
    "entry_conditions": [
        {"feature": "rsi", "operator": "<", "threshold": 30}
    ]
}
```

---

## Writing Behavior Test Cases

Test cases validate that the adapter evaluates entry conditions identically
to the legacy strategy:

```python
from iios.investment.strategy.migration import BehaviorTestCase

test_cases = [
    BehaviorTestCase(
        test_id="tc-rsi-low-vol-high",
        features={"rsi": 25.0, "volume_ratio": 2.0},
        expected_entry_result=True,
        description="Low RSI + high volume → entry",
    ),
    BehaviorTestCase(
        test_id="tc-rsi-high",
        features={"rsi": 70.0, "volume_ratio": 0.5},
        expected_entry_result=False,
    ),
]
```

Good test cases cover:
- All condition combinations (AND logic)
- Boundary values (exactly at threshold)
- At least one positive and one negative case per feature

---

## Extending Validation Categories

To add a new category of checks to `CompatibilityValidator`:

1. Add a value to `ValidationCheckType` in `validation_report.py`
2. Add a `_check_<category>()` method to `CompatibilityValidator`
3. Call it in `validate()`

Each check should use the `_check()` helper which handles pass/fail + severity.

---

## Thread Safety Contract

All public-facing objects are thread-safe:

| Class | Lock type |
|---|---|
| `AdapterRegistry` | `threading.RLock` |
| `MigrationAudit` | `threading.RLock` |
| `MigrationStatistics` | `threading.RLock` |
| `LegacyCatalog` | `threading.RLock` |
| `LegacyStrategyRegistry` | `threading.RLock` |
| `MigrationEventBus` | `threading.Lock` |
| `MigrationSession` | `threading.RLock` (per session) |

The pipeline uses `ThreadPoolExecutor` for parallel batch migration.
Shared objects (`AdapterRegistry`, `MigrationAudit`) are safe to access
concurrently from pipeline workers.

---

## Immutability Convention

All result types are `@dataclass(frozen=True)`:
- `ValidationReport`
- `ValidationCheck`
- `MigrationReport`
- `MigrationStepResult`
- `MigrationSummary`
- `EquivalenceResult`
- `BehaviorReport`
- `ComparisonResult`
- `MigrationConfidence`
- `AuditEntry`

Never mutate these objects. Create new ones instead.

---

## Score Convention

All scores are **0–100** (100 = best):
- `confidence_score` in `MigrationReport`
- `overall_confidence` in `MigrationConfidence`
- `pass_rate` in `BehaviorReport` (0.0–1.0 float, not 0–100)
- `match_rate` in `SignalComparison` (0.0–1.0 float)

---

## Approval Recommendation Rules

| Condition | Recommendation |
|---|---|
| Status == FAILED or ROLLED_BACK | REJECT |
| Validation has blocking errors | REJECT |
| Equivalence check failed | REVIEW |
| Confidence ≥ 80 | APPROVE |
| 55 ≤ confidence < 80 | REVIEW |
| Confidence < 55 | REJECT |
