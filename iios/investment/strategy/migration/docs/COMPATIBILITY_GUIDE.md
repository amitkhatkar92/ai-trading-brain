# Compatibility Guide

## Overview

The `CompatibilityLayer` and `CompatibilityValidator` determine how well a
legacy strategy maps to the IIOS interface before migration begins.

---

## Compatibility Levels

| Level | Error Count | Warning Count | Gaps |
|---|---|---|---|
| `full` | 0 | 0 | 0 |
| `partial` | 0 | >0 | 0 |
| `requires_adapter` | 0 | any | >0 |
| `incompatible` | >0 | any | any |

---

## Running a Compatibility Check

```python
from iios.investment.strategy.migration import CompatibilityValidator

validator = CompatibilityValidator()
report = validator.validate(metadata)

print(report.compatibility_level)
print(report.is_migration_approved)   # False if blocking errors
print(report.interface_gaps)          # list of gap descriptions
print(report.recommendations)         # remediation hints
```

---

## Check Categories

| Category | What Is Checked |
|---|---|
| **LIFECYCLE** | strategy_id/name present, source known, not archived |
| **CONFIGURATION** | min_rr > 0, max_loss_pct in range, target_multiplier ≥ min_rr |
| **SIGNAL** | direction valid (BUY/SELL/NEUTRAL/BOTH), entry conditions operators valid |
| **RISK** | stop_loss_pct > 0, max_drawdown ≤ 20%, stop_loss ≤ max_loss |
| **EXECUTION** | category defined, regime map available |
| **DEPENDENCY** | base_strategy known, source file accessible |

---

## Parameter Translation

`CompatibilityLayer.translate_params()` maps legacy parameter names to IIOS canonical names:

| Legacy Name | IIOS Name |
|---|---|
| `min_rr` | `minimum_risk_reward_ratio` |
| `max_loss_pct` | `maximum_loss_percent` |
| `stop_loss_pct` | `stop_loss_percent` |
| `target_multiplier` | `profit_target_multiplier` |
| `use_rsi_filter` | `rsi_filter_enabled` |
| `volume_ratio` | `volume_confirmation_ratio` |
| `base_strategy` | `parent_strategy_name` |

---

## Regime Translation

```python
from iios.investment.strategy.migration import CompatibilityLayer

# Legacy → IIOS
regime = CompatibilityLayer.translate_regime_to_iios("bull_trend")
# → MarketRegime.BULL

# IIOS → Legacy
legacy = CompatibilityLayer.translate_regime_to_legacy("bull")
# → "bull_trend"

# Batch
iios_regimes = CompatibilityLayer.translate_regimes_to_iios(
    ["bull_trend", "range_market", "volatile"]
)
```

---

## Interface Gap Detection

```python
gaps = CompatibilityLayer.check_interface_gaps(metadata)
# Returns list of gap descriptions (empty = fully compatible)
# Examples:
# - "min_rr is zero or negative"
# - "JSON strategy has no entry conditions — signal logic cannot be verified"
# - "Precision (hit rate) not available — evaluation confidence limited"
```

---

## Severity Reference

| Severity | Blocks Migration? | Meaning |
|---|---|---|
| `PASS` | No | Check passed cleanly |
| `INFO` | No | Informational note |
| `WARNING` | No | Caution, may affect confidence |
| `ERROR` | Yes | Must be resolved or accepted |
| `FATAL` | Yes | Hard block — migration cannot proceed |
