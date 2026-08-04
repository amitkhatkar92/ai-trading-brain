# DNA Reinforcement Engine — API Reference

**Module:** `market_learning.dre_engine.DNAReinforcementEngine`  
**Config:** `market_learning.dre_config.DREConfig`  
**Models:** `market_learning.dre_models`  

---

## DNAReinforcementEngine

```python
from market_learning.dre_engine import DNAReinforcementEngine
from market_learning.dre_config import DREConfig

engine = DNAReinforcementEngine(
    idr=None,          # IDRRepository or compatible. Default: production IDR
    config=None,       # DREConfig. Default: DREConfig()
    data_root=None,    # Path. Default: data/mls/dre/
)
```

### Constructor Parameters

| Parameter | Type | Description |
|---|---|---|
| `idr` | `IDRRepository` \| mock | DNA store. Injected for testing. Default uses `data/mls/institutional_dna.db`. |
| `config` | `DREConfig` | All thresholds. Default uses `DREConfig()`. |
| `data_root` | `Path` | Override data directory. Useful for test isolation. |

---

## process_trade()

```python
reinforcements: List[DNAReinforcement] = engine.process_trade(
    trade,               # Required: OrderRecord, dataclass, or dict
    pmci_result,         # Required: PMCIResult at decision time
    ca_pmci_result=None, # Optional: CAPMCIResult
    cds_scores=None,     # Optional: Dict[dna_id, ContextualDNAScore]
)
```

**Returns:** one `DNAReinforcement` record per DNA feature processed.

**Trade fields used:**

| Field | Fallback | Notes |
|---|---|---|
| `order_id` / `trade_id` | "unknown" | Used as `trade_id` |
| `symbol` | "" | Stored in evidence |
| `direction` | "" | "LONG" or "SHORT" |
| `pnl` | 0.0 | Used to determine won=True/False |
| `r_multiple` | 0.0 | Primary outcome quality metric |
| `strategy` / `strategy_name` | "" | Stored in evidence |
| `signal_regime` / `regime` | "" | Stored in evidence |
| `confidence_score` | 0.0 | DecisionEngine score at entry |
| `placed_at` | None | Used for holding_period_h |
| `closed_at` | None | Used for holding_period_h |

**Accepts `OrderRecord`, any dataclass, or `dict`.**

---

## process_batch()

```python
reinforcements: List[DNAReinforcement] = engine.process_batch([
    (trade1, pmci1, ca_pmci1, cds1),
    (trade2, pmci2, None,     None),
    ...
])
```

**Safety:** each DNA is reinforced at most `config.max_reinforcements_per_batch`
times per call, regardless of batch size.

---

## history()

```python
records: List[DNAReinforcement] = engine.history(
    dna_id=None,   # Optional str — filter to one DNA
    limit=100,     # Maximum records to return
)
```

Returns records newest-first. Filters by `dna_id` when provided.

---

## statistics()

```python
stats: ReinforcementStatistics = engine.statistics()
```

Returns aggregate counts, deltas, and timestamps across all recorded
reinforcements since initialisation.

---

## pending()

```python
trade_ids: List[str] = engine.pending()
```

Returns trade IDs currently being processed by concurrent threads.
Empty list at idle. Useful for diagnostics.

---

## summarise_batch()

```python
updates: List[DNAConfidenceUpdate] = engine.summarise_batch(reinforcements)
```

Groups a flat list of `DNAReinforcement` records by `dna_id` and returns
a per-DNA summary with `net_confidence_delta`, `dominant_type`, and
`final_confidence`. Useful for EOD reporting.

---

## DREConfig

```python
from market_learning.dre_config import DREConfig

cfg = DREConfig(
    max_single_trade_delta   = 0.05,  # hard safety cap
    min_idr_evidence_count   = 10,    # DNA must have ≥ N observations
    min_alignment_threshold  = 0.30,  # ignore DNA with low PMCI alignment
    min_r_multiple_magnitude = 0.25,  # below this → NEUTRAL
    learning_rate            = 0.03,  # base multiplier
    r_multiple_scale_min     = 0.5,
    r_multiple_scale_max     = 2.0,
    r_excellent_threshold    = 2.0,
    r_good_threshold         = 1.0,
    r_fair_min               = -0.5,
    r_poor_min               = -1.5,
    stability_win_delta      =  0.01,
    stability_loss_delta     = -0.02,
    stability_neutral_delta  =  0.0,
    eligible_lifecycles      = ("INSTITUTIONAL", "WEAKENING", "DRIFTING"),
    confidence_min           = 0.05,
    confidence_max           = 0.99,
    stability_min            = 0.00,
    stability_max            = 1.00,
    max_history_records      = 10_000,
    max_reinforcements_per_batch = 5,
    contradictory_weight     = 0.5,
    dry_run                  = False,
)

# Audit fingerprint (excludes dry_run)
print(cfg.fingerprint())  # → "3a7f9c2b1e4d8f06" (16-char hex)
```

---

## Models

### DNAReinforcement

One reinforcement event. Immutable. Always traceable to one trade.

```python
@dataclass
class DNAReinforcement:
    reinforcement_id:      str       # "DRE-{sha256[:12]}"
    dna_id:                str
    feature_name:          str
    direction:             str
    trade_id:              str
    reinforcement_type:    str       # ReinforcementType.value
    evidence:              ReinforcementEvidence
    confidence_before:     float
    confidence_after:      float
    confidence_delta:      float     # signed; confidence_before + delta == after
    stability_before:      float
    stability_after:       float
    stability_delta:       float
    evidence_count_before: int
    evidence_count_after:  int
    reason:                str       # human-readable explanation
    idr_revision:          Optional[int]  # IDR version created (None = dry_run)
    processed_at:          str       # ISO datetime UTC
    dre_version:           str = "1.0"
```

### ReinforcementEvidence

Full audit bundle for one reinforcement.

```python
@dataclass
class ReinforcementEvidence:
    trade_id:         str
    symbol:           str
    trade_direction:  str
    strategy:         str
    regime_at_entry:  str
    pmci_score:       float
    ca_pmci_score:    float
    cds_score:        float
    dna_alignment:    float
    dna_contribution: float
    r_multiple:       float
    pnl:              float
    holding_period_h: float
    won:              bool
    outcome_quality:  str
    confidence_score: float
```

### ReinforcementType (enum)

```python
class ReinforcementType(str, Enum):
    POSITIVE              = "POSITIVE"
    NEGATIVE              = "NEGATIVE"
    NEUTRAL               = "NEUTRAL"
    CONTRADICTORY         = "CONTRADICTORY"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
```

### OutcomeQuality (enum)

```python
class OutcomeQuality(str, Enum):
    EXCELLENT = "EXCELLENT"   # R ≥ 2.0, won
    GOOD      = "GOOD"        # R ≥ 1.0, won
    FAIR      = "FAIR"        # 0 ≤ R < 1.0 OR −0.5 ≤ R < 0
    POOR      = "POOR"        # −1.5 ≤ R < −0.5
    BAD       = "BAD"         # R < −1.5
```

---

## Minimal Usage Example

```python
from market_learning.dre_engine import DNAReinforcementEngine
from market_learning.dre_config import DREConfig

# Inject into orchestrator
dre = DNAReinforcementEngine(config=DREConfig())

# After a trade closes (EOD loop):
reinforcements = dre.process_trade(
    trade=closed_order_record,
    pmci_result=pmci_result_at_entry,
    ca_pmci_result=ca_pmci_result_at_entry,
)

# Log summary
for r in reinforcements:
    print(
        f"[DRE] {r.dna_id} {r.reinforcement_type} "
        f"conf: {r.confidence_before:.3f} → {r.confidence_after:.3f} "
        f"({r.confidence_delta:+.4f})"
    )
```

---

## Exceptions

| Exception | When raised |
|---|---|
| `DREInputError` | `pmci_result` is None |
| `DREProcessingError` | (reserved for future use) |
| `DREError` | Base class |
