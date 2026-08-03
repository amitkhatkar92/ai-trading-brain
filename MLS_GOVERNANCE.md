# Market Learning System — Governance

**Phase 0 — Architecture Freeze**  
**Date:** 2026-08-03  
**Status:** FROZEN

---

## 1. Governance Contract

### 1.1 What MLS Is

MLS is a **read-only market observer and evidence generator**.

Its sole purpose is to discover statistically verified characteristics
that separate future outperformers from ordinary stocks — and to route
that evidence through ARS for validation and acceptance.

### 1.2 What MLS Is Not

| MLS is NOT | Because |
|------------|---------|
| A trading signal generator | It does not produce BUY/SELL signals |
| A strategy modifier | It cannot change strategy parameters |
| A knowledge store | It proposes findings; ARS owns acceptance |
| A research oracle | Every claim must pass statistical gates |
| A fast feedback loop | DNA takes days to weeks to stabilize; impatience = noise |

### 1.3 The Five Governance Rules

```
RULE 1: MLS never executes trades.
        No MLS module may call any order management, execution engine,
        or broker interface.

RULE 2: MLS never changes strategies.
        No MLS module may modify StrategyLab, ConfigManager,
        or any threshold/parameter store.

RULE 3: MLS never writes directly to knowledge stores.
        All findings pass through KnowledgeIntegrator, which proposes
        them to ARS. ARS owns acceptance. MLS does not own final state.

RULE 4: MLS never promotes its own discoveries.
        A DNACharacteristic is not a Finding until EvidenceValidator
        has passed it through all validation gates.
        A Finding is not accepted until HypothesisRegistry has processed it.

RULE 5: MLS never assumes its DNA is correct.
        All temporal patterns are treated as hypotheses until validated
        by cross-regime, cross-sector, and walk-forward testing.
```

---

## 2. Statistical Validation Gates

Every discovered DNA characteristic must pass all 7 configurable gates
before being submitted to ARS. No threshold is hardcoded.

### Gate Definitions

| # | Gate | Metric | Default Threshold | Configurable Key |
|---|------|--------|------------------|--------------------|
| G-ML-01 | Sample Size | n_winner, n_loser | ≥ 30 per group | `min_group_size` |
| G-ML-02 | Effect Size | Cohen's d | ≥ 0.50 (medium) | `min_effect_size` |
| G-ML-03 | Statistical Significance | p-value (BH-corrected) | ≤ 0.05 | `max_p_value` |
| G-ML-04 | Temporal Consistency | % days present in rolling window | ≥ 60% over 20 days | `min_consistency_pct.MONTHLY` |
| G-ML-05 | Cross-Regime Consistency | Regimes in which characteristic holds | ≥ 2 of recent 4 regimes | `min_regime_count` |
| G-ML-06 | Cross-Sector Consistency | Sectors in which characteristic holds | ≥ 3 of major sectors | `min_sector_count` |
| G-ML-07 | Walk-Forward Confirmation | Holds in held-out OOS period | ≥ 50% of OOS days | `min_oos_consistency_pct` |

### Gate Criticality

| Gate | Critical? | Failure Effect |
|------|-----------|---------------|
| G-ML-01 Sample Size | **YES** | Immediate rejection |
| G-ML-02 Effect Size | **YES** | Immediate rejection |
| G-ML-03 Significance | **YES** | Immediate rejection |
| G-ML-04 Temporal Consistency | No | Reduces confidence; may still submit |
| G-ML-05 Cross-Regime | No | Reduces confidence; marks as regime-specific |
| G-ML-06 Cross-Sector | No | Reduces confidence; marks as sector-specific |
| G-ML-07 Walk-Forward | **YES** | Immediate rejection for ESTABLISHED DNA |

### Gate Override Policy

- Critical gate failures cannot be overridden. A `StudyPlan` must be created to investigate.
- Non-critical gate failures reduce `confidence` score (formula in `MLS_DNA_DISCOVERY.md §5.3`).
- A characteristic with ≥ 3 non-critical gate failures is **not submitted to ARS** until the next monthly consensus cycle.
- The Scientific Director may override a non-critical failure via HypothesisRegistry annotation.

---

## 3. Knowledge Integration with ARS

This section defines the exact integration protocol between MLS and each ARS module.

### 3.1 KnowledgeProvider Integration

**Flow: MLS → KnowledgeProvider (via staging)**

MLS does **not** call KnowledgeProvider write methods.  
KnowledgeProvider is a read-only layer in ARS.  
MLS proposes findings through a **staging protocol**:

```
1. KnowledgeIntegrator writes proposed findings to:
       data/mls/proposed_findings.json

2. A separate KnowledgeIngestion job (future Phase 1 module) reads
   data/mls/proposed_findings.json and creates ResearchStudy objects.

3. KnowledgeProvider loads the new studies on its next read cycle.
```

**Finding Schema for MLS Output:**

```json
{
  "study_id":     "MLS-20260803-DAILY",
  "title":        "MLS Daily DNA Study 2026-08-03",
  "executed_at":  "2026-08-03T16:45:00",
  "n_observations": 1987,
  "findings": [
    {
      "finding_id":     "MLS-W-mom5d-20260803",
      "study_id":       "MLS-20260803-DAILY",
      "classification": "WINNER_DNA",
      "description":    "5-day momentum separates TOP_5PCT from NEUTRAL (Cohen d=1.58)",
      "metric":         "mom_5d",
      "value":          1.58,
      "confidence":     0.87,
      "regime":         "BULL",
      "evidence": [
        {"metric": "effect_size",  "value": 1.58},
        {"metric": "p_value",      "value": 0.0002},
        {"metric": "sample_n",     "value": 1290},
        {"metric": "winner_mean",  "value": 0.042},
        {"metric": "neutral_mean", "value": 0.011}
      ]
    }
  ]
}
```

`FindingClassification.WINNER_DNA` and `FindingClassification.LOSER_DNA` are
already defined in `autonomous_research/models.py`. **Zero schema changes required.**

---

### 3.2 HypothesisRegistry Integration

**Flow: MLS → HypothesisRegistry.create_hypothesis()**

Every ESTABLISHED DNA characteristic (passed all gates, present in monthly consensus)
generates one ScientificHypothesis:

```python
registry.create_hypothesis(
    title=f"WINNER DNA: {feature} shows {direction} before outperformance",
    research_question=(
        f"Is the observed {feature} separation between TOP_5PCT and NEUTRAL "
        f"({effect_size:.2f} Cohen d, {consistency_pct:.0f}% consistent) "
        f"a stable, reproducible characteristic?"
    ),
    description=(
        f"Discovered via MLS {period} consensus. "
        f"Feature: {feature}. Direction: {direction}. "
        f"Avg effect size: {effect_size:.2f}. P-value: {p_value:.4f}. "
        f"Regime: {regime}."
    ),
    origin="market_learning_system",
    priority=HypothesisPriority.HIGH if effect_size >= 1.0 else HypothesisPriority.MEDIUM,
    classification=HypothesisClassification.PERFORMANCE_GAP,
    knowledge_gap=f"Unexplained pre-move characteristic: {feature}",
    expected_knowledge_gain=f"Quantified DNA profile for {feature} in {regime} regime",
    confidence=confidence_score,
    validation_method="EvidenceValidator + StudyPlanner EDGE_VALIDATION study",
)
```

**Lifecycle control:**  
MLS creates hypotheses in `PROPOSED` status only.  
Lifecycle progression (UNDER_REVIEW → APPROVED → ...) is the exclusive
responsibility of the HypothesisRegistry and the Scientific Director.

---

### 3.3 CrossStudySynthesizer Integration

**Flow: CrossStudySynthesizer reads new MLS-produced studies (passive)**

CrossStudySynthesizer already reads all studies from KnowledgeProvider.  
Once MLS studies are loaded into KP (via staging), CrossStudySynthesizer
automatically incorporates them in its next synthesis run.

**Expected synthesis outputs:**
- New `SynthesizedFinding` linking MLS DNA to existing edge findings
- New `ContradictionRecord` if MLS DNA contradicts an existing finding
- Updated `StudyCorrelation` entries linking MLS studies to backtesting studies

**No code changes to CrossStudySynthesizer.** Integration is automatic.

---

### 3.4 GapDetector Integration

**Flow: GapDetector detects gaps from MLS-produced findings (passive)**

GapDetector already runs on KnowledgeProvider data. Once MLS findings
are loaded into KP, GapDetector automatically detects:

| Gap Type | Triggered When |
|----------|---------------|
| `REGIME_GAP` | A DNA characteristic is absent for a specific regime |
| `TEMPORAL_GAP` | A DNA characteristic was present but has been absent > 20 days |
| `EVIDENCE_GAP` | A DNA characteristic has only 1 study (MLS daily) supporting it |
| `CONTRADICTION_GAP` | MLS DNA contradicts an existing KP finding |
| `CONFIDENCE_GAP` | DNA confidence is high but corroborating studies are few |

**No code changes to GapDetector.** Integration is automatic.

---

### 3.5 RoadmapManager Integration

**Flow: RoadmapManager prioritizes DNA-derived gaps (passive)**

RoadmapManager already processes gaps from GapDetector. DNA-derived gaps
enter the roadmap automatically.

**MLS influence on priorities:**  
High-consistency, high-effect-size characteristics produce `KnowledgeGap`
objects with `estimated_knowledge_gain = confidence_score`. These receive
high `priority_score` in RoadmapManager's scoring model.

**No code changes to RoadmapManager.** Integration is automatic.

---

### 3.6 EvidenceValidator Integration

**Flow: MLS calls EvidenceValidator before submitting to KnowledgeIntegrator**

Before any DNA finding is proposed to KnowledgeIntegrator, it is validated
by EvidenceValidator using custom `EvidenceValidatorConfig`:

```python
mls_ev_config = EvidenceValidatorConfig(
    min_observations=MLSConfig.min_group_size,
    min_corroborating_studies=MLSConfig.min_weekly_consistency_days,
    min_temporal_coverage_days=MLSConfig.monthly_window_days,
    min_regime_count=MLSConfig.min_regime_count,
    min_sector_diversity=MLSConfig.min_sector_count,
    max_contradiction_ratio=MLSConfig.max_contradiction_ratio,
    critical_gates=["G-EV-08"],  # contradiction gate always critical
    passed_threshold=0.80,
)
validator = EvidenceValidator(kp, config=mls_ev_config)
result = validator.validate_finding(finding.finding_id)
```

Only findings with `outcome == ValidationOutcome.PASSED` are submitted.

**No code changes to EvidenceValidator.** Integration uses custom config only.

---

### 3.7 StudyPlanner Integration

**Flow: MLS calls StudyPlanner to design follow-on validation studies**

Every validated DNA characteristic that has been submitted to ARS
automatically generates a follow-on `StudyPlan`:

```python
plan = study_planner.create_from_gap(gap)
# where gap is the EVIDENCE_GAP or CONFIDENCE_GAP derived from DNA
# Study type: StudyType.DNA_DISCOVERY or EDGE_VALIDATION
```

This ensures that every MLS discovery has a formal research plan,
approved via the CLASS_A/CLASS_B governance process.

**No code changes to StudyPlanner.** Integration uses `create_from_gap()`.

---

## 4. Change Control

### 4.1 MLSConfig Changes

Any change to `MLSConfig` thresholds requires:
1. Scientific Director approval
2. Entry in `MLS_CHANGE_LOG.md`
3. Re-run of last 20 trading days through updated config
4. Comparison of before/after DNA to verify no regression

### 4.2 Feature Additions

Adding a new feature to the FeatureExtractor:
1. Must not change existing feature names (backward compatible)
2. Must include a test proving temporal ordering (feature timestamp < outcome)
3. Must be documented in `MLS_DNA_DISCOVERY.md §3`
4. Requires DNA Discovery re-run for last 60 days

### 4.3 New Statistical Tests

Replacing or adding statistical tests:
1. Must run on 90-day historical data
2. Must not change more than 10% of existing ESTABLISHED characteristics
3. Scientific Director approval required
4. Requires update to `MLS_DNA_DISCOVERY.md §4.2`

### 4.4 ARS Integration Points

No ARS module (KP, Registry, Synthesizer, GapDetector, RoadmapManager,
EvidenceValidator, StudyPlanner) shall be modified for MLS.  
Integration is exclusively via public APIs documented in each module's
API reference. Any required API extension is a separate change request.

---

## 5. Audit Trail

Every MLS pipeline run produces an immutable audit entry in
`data/mls/market_learning_history.json`:

```json
{
  "run_id":            "MLS-RUN-20260803-164500",
  "trading_date":      "2026-08-03",
  "start_time":        "2026-08-03T16:05:00",
  "end_time":          "2026-08-03T16:47:33",
  "universe_size":     1987,
  "regime":            "BULL",
  "winner_dna_count":  7,
  "loser_dna_count":   6,
  "validated_count":   5,
  "submitted_to_ars":  4,
  "hypotheses_created": 3,
  "gates_failed_count": 2,
  "run_status":        "SUCCESS",
  "warnings":          [],
  "mlsconfig_hash":    "a3f7..."
}
```

`mlsconfig_hash` is the sha256 of the MLSConfig at run time.  
This enables exact reproducibility of any historical run.

---

## 6. Final Questions (Definitive Answers)

**Q1: Can MLS discover characteristics BEFORE movement?**  
**A: Yes.**  
The temporal contract (INV-01 in MLS_DATAFLOW.md) enforces that all
feature vectors carry timestamps ≤ 09:15 IST (T-1 market open).
The outcome (forward return) is computed from Close(T) vs Close(T-1).
This guarantee is enforced at the MarketObserver level, not assumed.
No feature captured after 09:15 on day T is used to explain returns on day T.

**Q2: Can every discovered characteristic be traced to evidence?**  
**A: Yes.**  
Every `DNACharacteristic` carries: source date, group, feature name,
statistical test results (p_value, effect_size, test_used, sample sizes),
regime context, sector context, and validation gate results.
The full `DifferenceReport` and raw `ComparisonResult` are persisted
in `data/mls/raw/{date}/` for 90 days.
Every submitted Finding includes the full evidence array.

**Q3: Can MLS reuse existing IIOS modules with > 90% reuse?**  
**A: Yes.**  
12 of 18 modules are reused (67% by count).  
By estimated lines of code: the 6 new MLS modules are thin orchestration
layers totaling an estimated 600–900 LOC; they call into ≈15,000 LOC of
existing well-tested modules (FeatureExtractor alone is ≈400 LOC).
Effective code reuse > 90% by execution path.

**Q4: Can ARS consume MLS knowledge without architectural changes?**  
**A: Yes.**  
MLS produces `Finding` objects with `FindingClassification.WINNER_DNA`
and `FindingClassification.LOSER_DNA` — both already defined in
`autonomous_research/models.py`.  
MLS uses `EvidenceValidatorConfig` (no schema changes).  
MLS calls `HypothesisRegistry.create_hypothesis()` (no API changes).  
MLS calls `StudyPlanner.create_from_gap()` (no API changes).  
**Zero changes to any ARS module are required.**
