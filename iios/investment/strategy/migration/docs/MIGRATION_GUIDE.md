# Migration Guide

## Overview

This guide covers end-to-end migration of legacy trading strategies into IIOS.

**Migration does not change strategy logic.** It wraps legacy strategies so they
can coexist with native IIOS strategies during the transition period.

---

## Step 1 — Discover legacy strategies

```python
from iios.investment.strategy.migration import StrategyMigrationEngine

engine = StrategyMigrationEngine()
result = engine.discover()

print(f"Discovered: {result.total_discovered}")
print(f"Code-based: {result.code_based_count}")
print(f"JSON-based: {result.json_based_count}")
print(f"Errors:     {len(result.errors)}")
```

---

## Step 2 — Validate before migrating

```python
report = engine.compatibility_report("Breakout_Volume")
print(report.compatibility_level)      # full / partial / requires_adapter / incompatible
print(report.interface_gaps)           # list of detected gaps
print(report.recommendations)          # how to fix each gap
```

---

## Step 3 — Migrate

### Single strategy
```python
session = engine.migrate("Breakout_Volume")
print(session.status)
```

### Batch by name
```python
sessions = engine.migrate_batch(["Breakout_Volume", "Momentum_Retest", "Iron_Condor_Range"])
```

### All approved strategies
```python
sessions = engine.migrate_all(approved_only=True)
```

### Full migration with behavior test cases
```python
from iios.investment.strategy.migration import BehaviorTestCase

test_cases = [
    BehaviorTestCase("tc1", {"rsi": 25.0, "volume_ratio": 2.0}, expected_entry_result=True),
    BehaviorTestCase("tc2", {"rsi": 60.0, "volume_ratio": 0.5}, expected_entry_result=False),
]
session = engine.migrate("Test_MeanRev", test_cases=test_cases)
```

---

## Step 4 — Inspect results

```python
session = engine.get_session("Breakout_Volume")
report  = engine.get_report("Breakout_Volume")

print(report.approval_recommendation)     # APPROVE / REVIEW / REJECT
print(report.confidence_score)            # 0–100
print(report.known_limitations)
```

---

## Step 5 — Access migrated adapter

```python
adapter = engine.get_adapter("Breakout_Volume")
if adapter:
    definition = adapter.get_definition()
    risk_params = adapter.get_risk_params()
    print(definition.name, risk_params)
```

---

## Step 6 — Rollback if needed

```python
success = engine.rollback("Breakout_Volume")
print("Rolled back:", success)
```

---

## Step 7 — Generate summary

```python
summary = engine.summary()
print(f"Total:    {summary.total_strategies}")
print(f"Done:     {summary.completed}")
print(f"Failed:   {summary.failed}")
print(f"Approve:  {summary.approve_recommended}")
print(f"Review:   {summary.review_recommended}")
```

---

## Auto-approve Mode

For CI/CD pipelines where manual approval is not required:

```python
from iios.investment.strategy.migration import PipelineConfig

engine = StrategyMigrationEngine(
    config=PipelineConfig(
        auto_approve=True,
        require_behavior_equivalence=False,
        max_workers=4,
    )
)
```

---

## Migration Status Reference

| Status | Terminal? | Can Rollback? |
|---|---|---|
| NOT_STARTED | No | No |
| DISCOVERY | No | No |
| VALIDATION | No | No |
| PREPARATION | No | No |
| MIGRATING | No | No |
| VERIFICATION | No | No |
| APPROVAL_PENDING | No | Yes |
| COMPLETED | Yes | Yes |
| FAILED | Yes | No |
| ROLLED_BACK | Yes | No |
| ARCHIVED | Yes | No |
