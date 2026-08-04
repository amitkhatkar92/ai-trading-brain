# Platform Intelligence Influence Policy — R-001 Phase 2

## Principle

PIG may contribute evidence to trading decisions **only within configured bounds**.
It cannot override, veto, or directly cause any trade. The Decision Engine
retains final authority at all times.

---

## Configurable Parameters

All parameters live in `MLSConfig` (market_learning/mls_config.py) and are
surfaced through `PIGInfluencePolicy` (market_learning/pig_integration.py).

### Decision Engine Integration

| Parameter | Default | Effect |
|---|---|---|
| `pig_vote_weight` | `0.08` | Weight of InstitutionalDNAAI vote in AGENT_WEIGHTS |
| `pig_min_ca_pmci_for_vote` | `0.30` | Min CA-PMCI to cast any vote; below = silence |
| `pig_decision_vote_enabled` | `True` | Master flag — disables PIG vote injection |

**Weight context:**

| Agent | Weight |
|---|---|
| TechnicalAnalystAI | 0.30 |
| RiskDebateAI | 0.25 |
| MacroAnalystAI | 0.20 |
| SentimentAI | 0.15 |
| RegimeDebateAI | 0.10 |
| **InstitutionalDNAAI** | **0.08** |

PIG weight (0.08) is below the weakest existing agent (0.10). It cannot
single-handedly shift a decision.

### Opportunity Engine Integration

| Parameter | Default | Effect |
|---|---|---|
| `pig_max_conviction_boost` | `1.0` | Max additive boost on 0-10 confidence scale |
| `pig_min_ca_pmci_for_boost` | `0.30` | Min CA-PMCI to apply any boost |
| `pig_opportunity_boost_enabled` | `True` | Master flag |

**Boost formula:** `boost = min(max_conviction_boost, ca_pmci × max_conviction_boost)`

Examples at `max_conviction_boost=1.0`:
- CA-PMCI = 0.80 → boost = +0.80 (confidence 7.0 → 7.80)
- CA-PMCI = 0.50 → boost = +0.50 (confidence 7.0 → 7.50)
- CA-PMCI = 0.29 → boost = 0 (below threshold)

### Telemetry

| Parameter | Default | Effect |
|---|---|---|
| `pig_telemetry_enabled` | `True` | Emit [PIGTelemetry] log lines per call |

---

## Hard Invariants (enforced by design, not config)

1. **PIG never hard-rejects.** `pig_build_vote()` always returns `vote="approve"`.
   Only the 5 existing agents can issue hard rejects.

2. **PIG never reduces confidence.** `pig_enrich_signals()` is additive only.
   `new_confidence = min(10.0, old + boost)` — boost ≥ 0 always.

3. **PIG never changes position_size_modifier.** `suggested_position_modifier=1.0`
   always. Sizing is controlled by RiskEngine and CapitalRiskEngine.

4. **PIG never modifies signal direction, entry, stop, or target.**

5. **PIG never blocks the pipeline.** All calls wrapped in try/except → None.

---

## Adjusting the Policy

To reduce PIG's influence further (e.g. during initial data accumulation):

```python
# In config/mls_config_overrides.py or similar:
cfg = MLSConfig()
cfg.pig_vote_weight = 0.04           # halve the vote weight
cfg.pig_max_conviction_boost = 0.5   # halve the opportunity boost
cfg.pig_min_ca_pmci_for_vote = 0.50  # raise quality gate
```

To disable PIG entirely (emergency):

```python
cfg.pig_decision_vote_enabled    = False
cfg.pig_opportunity_boost_enabled = False
```

---

## Evolution Path

| Phase | Description |
|---|---|
| Now | `max_boost=1.0`, `vote_weight=0.08` — conservative |
| 3+ months of DNA data | Review avg CA-PMCI; consider `max_boost=1.5` |
| 6+ months + backtest evidence | Consider raising `vote_weight` to 0.10 |

Any change to `pig_vote_weight` or `pig_max_conviction_boost` requires
Architecture Council review (same gate as `MIN_CONFIDENCE_SCORE`).
