# RELATIONSHIP ONTOLOGY
## AI Trading Brain — Complete Relationship Universe

**Version:** 1.0
**Status:** Authoritative
**Date:** 2026-07-01
**Parent Documents:** MASTER_KNOWLEDGE_ARCHITECTURE.md | INFORMATION_ONTOLOGY.md | ENTITY_ONTOLOGY.md

---

> *This document answers the question: "How can entities be connected?"*
> *Every edge in the knowledge graph. Every causal path. Every reasoning link.*
> *Every relationship in the investment universe — named, defined, governed.*

---

## PART I — THE NATURE OF A RELATIONSHIP

### What Is a Relationship?

A relationship is a typed, directed, semantically meaningful connection between two or more entity instances that enables information flow, causal reasoning, or structural understanding — producing knowledge that neither connected entity contains alone.

Relationships are the EDGES of the investment knowledge graph. Entities are nodes. Relationships are what make a collection of nodes into an intelligent network capable of inference.

**The Five-Test Definition:**
A relationship exists if and only if:
1. It connects **two or more specific entity instances** — not types in the abstract
2. It carries **semantic meaning that changes when reversed** — direction matters
3. It **enables information or logic to flow** between the entities
4. It **may change, evolve, or expire** over time (or be provably permanent)
5. It **adds reasoning value** not available from either entity alone

If all five conditions are met, it is a relationship.

**The Constitutional Definition:**
A relationship is a typed, directed, temporally-bounded or permanent, semantically meaningful connection between two entity instances that enables information flow, causal reasoning, or structural understanding in the investment intelligence system — and that produces knowledge beyond what either connected entity contains individually.

---

### Relationship vs. Adjacent Concepts

| Concept | What It Is | How It Differs From a Relationship |
|---|---|---|
| **Entity** | An independently existing thing in the investment universe | Entities are **nodes**. Relationships are **edges**. Entities exist independently; relationships require at least two entities to exist at all. A relationship without endpoints is undefined. |
| **Information** | A structured signal describing an entity's internal state | Information lives **inside** an entity as an attribute. "HDFC Bank ROE = 16%" is information about the entity. "HDFC Bank **COMPETES_WITH** Kotak Mahindra Bank" is the relationship. The relationship connects entities; information describes them. |
| **Knowledge** | A validated, durable pattern about entities or relationships | Knowledge is a **meta-claim** about patterns: "Private banks with ROE > 15% tend to outperform the NIFTY Bank Index in bull markets." This claim involves the COMPETES_WITH and CORRELATES_WITH relationships — but is itself a higher-order validated pattern, not the relationship itself. |
| **Observation** | A timestamped record of an entity's state | An observation captures a **moment** of a **single** entity. "ITC closed at ₹452 on June 30, 2026" is about one entity. A relationship connects two: "ITC **PART_OF** NIFTY 50." Observations can be the basis for discovering relationships; they are not relationships themselves. |
| **Evidence** | A contextualized observation weighted toward a hypothesis | Evidence is an **interpreted observation** pointing toward or against a claim. A relationship is **structural**: it connects two entities for a defined period. Evidence is interpretive and weighted; relationships are structural and typed. |
| **Decision** | An action commitment produced by the reasoning process | A decision is an **output** at the terminal end of the reasoning chain. Relationships are **inputs** — they define the network topology through which information travels to produce that decision. The relationship "Conviction **TRIGGERS** Decision" is itself a relationship. |
| **Dependency** | A functional requirement where B requires A to exist or function | Dependency is a **narrow subset** of structural relationships. "Options Contract **DEPENDS_ON** Underlying Equity" expresses dependency. All dependencies are relationships; not all relationships are dependencies. Dependency implies structural necessity; relationships may be optional. |
| **Ownership** | The entity legally responsible for another entity's lifecycle | Ownership is a **specific, binding relationship type** — carrying legal rights, obligations, and accountability. "Investor **OWNS** Portfolio" is an ownership relationship. Ownership is a relationship with maximum strength, permanence, and legal enforceability. |
| **Association** | A loose, untyped co-occurrence between entities | Association is the **weakest** form of relationship — two entities tend to co-occur or be mentioned together without a defined mechanism or direction. Every well-defined relationship is stronger than a mere association. The value of this ontology is precisely in upgrading associations to typed relationships. |
| **Correlation** | A quantified statistical co-movement between entity attributes | Correlation is a **specific, measured, directionally neutral** relationship type. It says "these two entities' observable values co-move with a coefficient of X" — without specifying direction or mechanism. Correlation is one relationship type in this ontology (CORRELATES_WITH). |
| **Causation** | A directional mechanism where A's state deterministically changes B's state | Causation is a **specific, directional, mechanistic** relationship. It is stronger than correlation and influence: it requires a defined pathway, not just statistical evidence. "RBI Rate Hike **CAUSES** Increase in MCLR" — there is a defined transmission mechanism. |
| **Influence** | A directional impact of one entity's state on another's, without full determination | Influence is **weaker than causation** — it says "A's state changes B's probability distribution" without requiring a deterministic pathway. "Market Regime **INFLUENCES** Strategy Performance" — the regime shapes outcomes but doesn't determine them. |
| **Inheritance** | The transfer of properties from a parent type to a child type | Inheritance is a **hierarchical IS-A relationship** operating at the type level, not the instance level. "Options Contract IS-A Derivative" means Options inherits all properties of Derivatives. In the knowledge graph, inheritance defines the type hierarchy used for reasoning by analogy. |
| **Composition** | A structural whole-part relationship where parts cannot exist meaningfully outside the whole | Composition is a **strong structural relationship**: the composed parts derive their identity from the whole. "Option Chain COMPOSED_OF Options Contracts" — the chain is meaningless without its component options. Destroy the chain; the options lose their relational context. |
| **Aggregation** | A structural whole-part relationship where parts can exist independently | Aggregation is **weaker than composition**: the parts have independent existence. "Portfolio AGGREGATES_INTO Positions" — positions exist independently; they can be transferred. The portfolio is a collection; not a fusion. |

---

### Three Fundamental Properties of Every Relationship

**Property 1 — Direction**
Every relationship is asymmetric. "A INFLUENCES B" is not the same as "B INFLUENCES A." The direction of a relationship is defined by the arrow of semantic meaning: which entity is the source (subject) and which is the target (object). Reversing direction produces the inverse relationship — which may have a different name, different strength, and different implications.

**Property 2 — Type**
Every relationship has a type — a precisely defined semantic category determining what it means, how it behaves, what entities it can connect, and how it should be used in reasoning. An untyped relationship is not a relationship — it is a mere co-occurrence. Type is what makes relationships usable in inference.

**Property 3 — Confidence**
Every relationship carries a confidence score — a measure of how certain the system is that this relationship is real, current, and significant. Confidence degrades over time unless refreshed by new evidence. Low-confidence relationships are treated as hypothetical and should not anchor critical decisions.

---

## PART II — COMPLETE RELATIONSHIP VOCABULARY

*The complete lexicon of typed relationships in the investment intelligence universe.*
*Organized by semantic category. Full definitions in Part III.*

---

### Category 1 — Structural Relationships
*Define the physical and logical architecture of the investment universe.*

| Relationship | Inverse | Brief Meaning |
|---|---|---|
| CONTAINS | CONTAINED_IN / PART_OF | A includes B as a component |
| PART_OF | CONTAINS | B is a component of A |
| SUB_TYPE_OF | HAS_SUBTYPE | B is a specialization of A |
| COMPOSED_OF | COMPONENT_OF | A's identity requires B |
| AGGREGATES | AGGREGATED_INTO | A is a collection including B (parts independent) |
| NESTED_WITHIN | NESTS | B exists within A's scope |
| EXTENDS | EXTENDED_BY | B adds properties to A's type |
| INHERITS_FROM | INHERITED_BY | B receives A's properties by type hierarchy |
| INSTANCES | INSTANCE_OF | A is the type; B is a specific instance |
| DECOMPOSES_INTO | DECOMPOSED_FROM | A breaks into B components |
| MEMBER_OF | HAS_MEMBER | B belongs to group A |
| SUBSET_OF | SUPERSET_OF | A's elements are a proper subset of B's |

---

### Category 2 — Ownership and Control Relationships
*Define legal, administrative, and operational authority.*

| Relationship | Inverse | Brief Meaning |
|---|---|---|
| OWNS | OWNED_BY | A has legal ownership of B |
| CONTROLS | CONTROLLED_BY | A can determine B's actions or state |
| GOVERNS | GOVERNED_BY | A sets the rules B must follow |
| REGULATES | REGULATED_BY | A is the statutory authority over B |
| MANAGES | MANAGED_BY | A has operational responsibility for B |
| OPERATES | OPERATED_BY | A executes day-to-day functioning of B |
| SUPERVISES | SUPERVISED_BY | A monitors and can intervene in B's activities |
| AUTHORIZES | AUTHORIZED_BY | A grants B the right to act |
| CUSTODIES | CUSTODIED_BY | A holds B's assets in safekeeping |
| LICENSES | LICENSED_BY | A grants B rights to use A's intellectual property |
| MANDATES | MANDATED_BY | A legally requires B to do something |
| PROHIBITS | PROHIBITED_BY | A forbids B from doing something |

---

### Category 3 — Issuance and Market Structure Relationships
*Define how instruments enter, exist in, and exit markets.*

| Relationship | Inverse | Brief Meaning |
|---|---|---|
| ISSUES | ISSUED_BY | A creates and offers B as a financial instrument |
| LISTED_ON | LISTS | A is available for trading on exchange B |
| TRADED_ON | TRADES | A is the venue on which B changes hands |
| CLEARED_BY | CLEARS | A manages settlement risk for B |
| SETTLED_BY | SETTLES | A completes transfer of B between parties |
| CUSTODIED_BY | CUSTODIES | A holds B in safekeeping on behalf of owner |
| UNDERLIES | DERIVED_FROM_UNDERLYING | A is the reference asset on which derivative B is written |
| BENCHMARKED_AGAINST | BENCHMARKS | A is measured relative to index/rate B |
| INDEXED_TO | CONSTITUTES | A tracks the performance of index B |
| CONSTITUENT_OF | COMPRISES | A is a component of index/basket B |
| PRICED_IN | PRICES | Currency A is the unit in which B is denominated |
| CLASSIFIED_IN | CLASSIFIES | A belongs to classification system B |
| DENOMINATED_IN | DENOMINATES | A's value is expressed in currency B |

---

### Category 4 — Financial Activity Relationships
*Define how capital flows, instruments are held, and positions are created.*

| Relationship | Inverse | Brief Meaning |
|---|---|---|
| HOLDS | HELD_BY | A currently owns B as an asset or position |
| INVESTS_IN | INVESTED_IN_BY | A deploys capital into B |
| ALLOCATES_TO | ALLOCATED_FROM | A assigns a portion of capital to B |
| TRADES | TRADED_BY | A buys or sells B in the market |
| EXECUTES | EXECUTED_BY | A processes order B into a filled trade |
| FUNDS | FUNDED_BY | A provides capital to B |
| COLLATERALIZES | COLLATERALIZED_BY | A is pledged as security for B |
| CONVERTS_TO | CONVERTED_FROM | A transforms into a different instrument B |
| MATURES_INTO | MATURES_FROM | A reaches maturity and becomes cash/B |
| HEDGES | HEDGED_BY | A is used to reduce risk from B |
| REBALANCES | REBALANCED_BY | A's weights are periodically adjusted toward B |
| BENCHMARKS | BENCHMARKED_BY | A is the reference against which B is measured |
| PRICES | PRICED_BY | A determines the value of B |
| WEIGHTS_IN | WEIGHTED_BY | A has a specific weight in composite B |
| TRANSFERS | TRANSFERRED_TO | A moves from one owner to B |
| LEVERAGES | LEVERAGED_BY | A amplifies exposure to B using borrowed capital |

---

### Category 5 — Organizational Relationships
*Define how institutions relate to each other.*

| Relationship | Inverse | Brief Meaning |
|---|---|---|
| REPORTS_TO | OVERSEES | A's activities are accountable to B |
| EMPLOYS | EMPLOYED_BY | A hires B to perform work |
| ADVISES | ADVISED_BY | A provides professional guidance to B |
| PARTNERS_WITH | PARTNERS_WITH | A and B cooperate on shared activity |
| COMPETES_WITH | COMPETES_WITH | A and B vie for the same resource/customer |
| ACQUIRES | ACQUIRED_BY | A purchases control of B |
| MERGES_WITH | MERGES_WITH | A and B combine into a single entity |
| SPINS_OFF | SPUN_OFF_FROM | A creates B as an independent entity from its operations |
| DISTRIBUTES_THROUGH | DISTRIBUTED_BY | A uses B as a channel to reach customers |
| RATED_BY | RATES | A's creditworthiness is assessed by B |
| COVERED_BY | COVERS | A is analyzed by B (research coverage) |
| AUDITED_BY | AUDITS | A's financial statements are verified by B |
| SUPPLIED_BY | SUPPLIES | A receives inputs/goods from B |
| SUPPLIES_TO | SUPPLIED_BY | A provides inputs to B |

---

### Category 6 — Causal and Transmission Relationships
*Define how events, states, and information travel through the investment universe.*

| Relationship | Inverse | Brief Meaning |
|---|---|---|
| CAUSES | CAUSED_BY | A's state deterministically produces B's state change |
| TRIGGERS | TRIGGERED_BY | A's threshold crossing initiates B |
| ENABLES | ENABLED_BY | A's presence makes B possible |
| PREVENTS | PREVENTED_BY | A's presence makes B impossible |
| AMPLIFIES | AMPLIFIED_BY | A increases the magnitude of B's effect |
| DAMPENS | DAMPENED_BY | A reduces the magnitude of B's effect |
| DRIVES | DRIVEN_BY | A is the primary determinant of B's direction |
| INFLUENCES | INFLUENCED_BY | A changes B's probability distribution |
| TRANSMITS_TO | RECEIVED_FROM | A carries an effect from source to B |
| PROPAGATES_THROUGH | CARRIES | A passes an effect through system B |
| CASCADES_INTO | PRECEDED_BY_CASCADE | A's failure initiates chain reaction reaching B |
| DISRUPTS | DISRUPTED_BY | A breaks or severely impairs B's normal functioning |
| ABSORBS | ABSORBED_BY | A takes in the impact of B, preventing further propagation |
| SHIELDS | SHIELDED_BY | A protects B from external effects |
| CORRELATES_CAUSALLY | CORRELATES_CAUSALLY | A and B are causally linked bidirectionally |
| MODERATES | MODERATED_BY | A controls or limits the effect of B |

---

### Category 7 — Temporal Relationships
*Define how entities, events, and states relate across time.*

| Relationship | Inverse | Brief Meaning |
|---|---|---|
| PRECEDES | FOLLOWS | A occurs or comes into being before B |
| FOLLOWS | PRECEDES | A occurs after B |
| COINCIDES_WITH | COINCIDES_WITH | A and B occur at the same time |
| EXPIRES_ON | EXPIRY_DATE_OF | A ceases to exist or be valid at date B |
| ROLLS_OVER_TO | ROLLED_OVER_FROM | Position/contract A transfers to successor B |
| SUCCEEDS | SUCCEEDED_BY | A replaces B as the active version |
| SUPERSEDES | SUPERSEDED_BY | A makes B obsolete or invalid |
| SCHEDULED_FOR | SCHEDULES | Event A is planned for date/time B |
| CYCLES_WITH | CYCLES_WITH | A and B repeat on the same periodic schedule |
| OVERLAPS_WITH | OVERLAPS_WITH | A's active period partially coincides with B's |
| PERSISTS_THROUGH | CONTAINS_PERIOD | A remains valid across time period B |
| RESETS_AT | RESET_TRIGGER_FOR | A's state returns to baseline at event B |
| BORN_FROM | GIVES_RISE_TO | A comes into existence as a result of B |
| TERMINATES_ON | TERMINATION_DATE_OF | A's lifecycle ends definitively at B |

---

### Category 8 — Statistical and Quantitative Relationships
*Define mathematically measurable connections between entity attributes.*

| Relationship | Inverse | Brief Meaning |
|---|---|---|
| CORRELATES_WITH | CORRELATES_WITH | A and B's values co-move with a measurable coefficient |
| LEADS | LAGGED_BY | A moves before B with measurable average lead time |
| LAGS | LEADS | A moves after B with measurable average lag time |
| CO_INTEGRATES_WITH | CO_INTEGRATES_WITH | A and B share a long-run equilibrium relationship |
| MEAN_REVERTS_TO | ANCHOR_FOR | A's value gravitates toward B's level over time |
| BETA_TO | BETA_ANCHOR_FOR | A's movement is B multiplied by a coefficient |
| TRACKS | TRACKED_BY | A's value closely follows B's value |
| DEVIATES_FROM | DEVIATION_ANCHOR_FOR | A's current value has a measured distance from B |
| DIVERGES_FROM | DIVERGES_FROM | A and B are moving apart from a previously shared path |
| CONVERGES_TO | CONVERGING_FROM | A's value is approaching B from a distance |
| COVARIANCE_WITH | COVARIANCE_WITH | A and B have a measured joint variance |
| SEASONALLY_FOLLOWS | SEASONAL_ANCHOR | A exhibits predictable cyclical behavior relative to B |
| GRANGER_CAUSES | GRANGER_CAUSED_BY | A's past values have predictive power over B's future values |

---

### Category 9 — Knowledge Creation Relationships
*Define how facts, patterns, and understanding are generated.*

| Relationship | Inverse | Brief Meaning |
|---|---|---|
| DERIVED_FROM | SOURCE_OF | A is computed or inferred from B |
| CALCULATED_FROM | CALCULATION_INPUT_FOR | A is the mathematical result of applying a formula to B |
| BASED_ON | FOUNDATION_OF | A's validity depends on B's truth |
| REFERENCES | REFERENCED_BY | A explicitly cites or depends on B |
| DOCUMENTS | DOCUMENTED_BY | A records a formal record of B |
| EXPLAINS | EXPLAINED_BY | A provides the causal or logical account of B |
| SUMMARIZES | SUMMARIZED_BY | A condenses B into key information |
| ABSTRACTS_FROM | INSTANTIATED_BY | A is a generalization derived from multiple Bs |
| SYNTHESIZES_FROM | COMPONENT_OF_SYNTHESIS | A combines multiple Bs into a unified understanding |
| ANNOTATES | ANNOTATED_BY | A adds interpretive context to B |
| VALIDATES | VALIDATED_BY | A confirms B's accuracy through independent evidence |
| CONTRADICTS | CONTRADICTED_BY | A's content is logically inconsistent with B |
| UPDATES | UPDATED_BY | A replaces an earlier version of B with new information |
| INDEXES | INDEXED_BY | A provides navigation access to B's content |
| MODELS | MODELED_BY | A is a mathematical representation of how B behaves |

---

### Category 10 — Reasoning Relationships
*Define how evidence, hypotheses, and conclusions relate in the reasoning process.*

| Relationship | Inverse | Brief Meaning |
|---|---|---|
| SUPPORTS | SUPPORTED_BY | A is evidence that increases confidence in B |
| CONTRADICTS | CONTRADICTED_BY | A is evidence that decreases confidence in B |
| CONFIRMS | CONFIRMED_BY | A is strong evidence that validates B as true |
| INVALIDATES | INVALIDATED_BY | A demonstrates that B is false or inapplicable |
| STRENGTHENS | STRENGTHENED_BY | A increases the conviction weight behind B |
| WEAKENS | WEAKENED_BY | A decreases the conviction weight behind B |
| CONTEXTUALIZES | CONTEXTUALIZED_BY | A provides the framing that changes interpretation of B |
| QUALIFIES | QUALIFIED_BY | A adds conditions that limit B's applicability |
| OVERRIDES | OVERRIDDEN_BY | A's authority or weight supersedes B in the reasoning process |
| SYNTHESIZES_INTO | SYNTHESIZED_FROM | Multiple evidence items A converge into conclusion B |
| ANCHORS | ANCHORED_BY | A provides the reference point against which B is interpreted |
| CHALLENGES | CHALLENGED_BY | A raises questions about B's validity without fully refuting |
| CONVERGES_WITH | CONVERGES_WITH | A and B independently reach the same conclusion |
| EXPLAINS_AWAY | EXPLAINED_AWAY_BY | A provides an alternative account that reduces B's significance |
| CORROBORATES | CORROBORATED_BY | A is independent evidence consistent with B |

---

### Category 11 — Decision Relationships
*Define how decisions are formed, constrained, and executed.*

| Relationship | Inverse | Brief Meaning |
|---|---|---|
| TARGETS | TARGETED_BY | Decision A is aimed at achieving outcome B |
| CONSTRAINS | CONSTRAINED_BY | A limits the space of valid choices for B |
| APPROVES | APPROVED_BY | A grants permission for B to proceed |
| REJECTS | REJECTED_BY | A denies permission for B to proceed |
| OVERRIDES | OVERRIDDEN_BY | A supersedes B's authority in the decision process |
| ALLOCATES_TO | ALLOCATED_FROM | Decision A assigns capital/resource to target B |
| SIZES | SIZED_BY | A determines the quantity parameter of B |
| OPTIMIZES | OPTIMIZED_BY | A adjusts parameters of B toward best outcome |
| PRIORITIZES | PRIORITIZED_BY | A determines that B should be acted on before alternatives |
| DEFERS | DEFERRED_BY | A delays B pending additional information |
| TRIGGERS | TRIGGERED_BY | A's threshold condition initiates B |
| RECOMMENDS | RECOMMENDED_BY | A advises B as the preferred action |
| ESCALATES_TO | ESCALATED_FROM | A passes B to a higher authority for decision |
| CANCELS | CANCELLED_BY | A terminates B before completion |
| REVISES | REVISED_BY | A modifies B to reflect updated information |

---

### Category 12 — Risk Relationships
*Define how risk is borne, transferred, managed, and measured.*

| Relationship | Inverse | Brief Meaning |
|---|---|---|
| EXPOSES_TO | EXPOSURE_FROM | A puts the holder at risk of B |
| HEDGES | HEDGED_BY | A offsets the risk created by B |
| MITIGATES | MITIGATED_BY | A reduces the probability or impact of B |
| AMPLIFIES_RISK_IN | RISK_AMPLIFIED_BY | A increases B's total risk level |
| CONCENTRATES_IN | CONCENTRATION_SOURCE | A creates above-average concentration of risk in B |
| DIVERSIFIES_AGAINST | DIVERSIFIED_BY | A reduces B's idiosyncratic risk |
| STRESS_TESTS | STRESS_TESTED_BY | A applies an extreme scenario to B |
| LIMITS_EXPOSURE_IN | EXPOSURE_LIMITED_BY | A constrains the maximum risk taken in B |
| BUFFERS_AGAINST | BUFFERED_BY | A absorbs adverse outcomes from B |
| CORRELATES_RISK_WITH | RISK_CORRELATES | A and B's risks increase together under stress |
| INSURES_AGAINST | INSURED_BY | A provides financial protection from B's adverse outcome |
| DEFAULTS_ON | DEFAULTED_ON_BY | A fails to meet its obligations to B |
| GUARANTEES | GUARANTEED_BY | A promises to fulfill B's obligations if B cannot |
| MARGINED_BY | MARGINS | A requires collateral B to manage default risk |

---

### Category 13 — Learning and Predictive Relationships
*Define how the system learns, updates, and predicts.*

| Relationship | Inverse | Brief Meaning |
|---|---|---|
| LEARNS_FROM | TEACHES | A updates its model/knowledge based on B |
| TRAINS_ON | TRAINING_DATA_FOR | A is the dataset that shapes model B |
| VALIDATES_AGAINST | VALIDATES | A is tested against holdout dataset B |
| UPDATES_FROM | UPDATE_SOURCE | A's state is revised based on evidence B |
| BACKTESTS_AGAINST | BACKTEST_DATASET | Strategy A is tested against historical data B |
| PREDICTS | PREDICTED_BY | A generates a forecast of entity/state B |
| FORECASTS | FORECASTED_BY | A produces a probabilistic outlook for B |
| RETROACTIVELY_CONFIRMS | RETROACTIVELY_CONFIRMED_BY | Outcome A validates the prediction B made |
| DISCONFIRMS | DISCONFIRMED_BY | Outcome A contradicts the prediction B made |
| OUTPERFORMS | OUTPERFORMED_BY | A's realized performance exceeded expectation B |
| UNDERPERFORMS | UNDERPERFORMED_BY | A's realized performance fell short of expectation B |
| REVISES_ESTIMATE_OF | ESTIMATE_REVISED_BY | A produces a new prediction, superseding prior forecast of B |

---

### Category 14 — Information and Monitoring Relationships
*Define how entities are observed, measured, and tracked.*

| Relationship | Inverse | Brief Meaning |
|---|---|---|
| MEASURES | MEASURED_BY | A produces a quantitative value describing B |
| OBSERVES | OBSERVED_BY | A generates a timestamped record of B's state |
| MONITORS | MONITORED_BY | A tracks B continuously over time |
| REPORTS_ON | REPORTED_BY | A produces periodic disclosures about B's state |
| DISCLOSES | DISCLOSED_BY | A publicly reveals information about B |
| ALERTS_ON | ALERT_SOURCE | A triggers notification when B crosses a threshold |
| SCANS_FOR | SCANNED_BY | A searches the universe for instances of B |
| TRACKS | TRACKED_BY | A follows the evolution of B's state over time |
| BENCHMARKS | BENCHMARKED_BY | A provides the reference against which B is compared |
| SURVEYS | SURVEYED_BY | A samples B across a defined population |
| INDEXES | INDEXED_BY | A tracks B across its components |
| PRICES | PRICED_BY | A establishes or discovers B's market value |
| RATES | RATED_BY | A assigns a quality/risk score to B |
| RANKS | RANKED_BY | A establishes B's relative position in an ordered set |

---

### Category 15 — Intelligence and Analytical Relationships
*Define how intelligence is produced from raw data.*

| Relationship | Inverse | Brief Meaning |
|---|---|---|
| RANKS | RANKED_BY | A establishes B's position in an ordered universe |
| SCORES | SCORED_BY | A assigns a composite numerical rating to B |
| CLASSIFIES | CLASSIFIED_BY | A assigns B to a defined category |
| CLUSTERS | CLUSTERED_BY | A groups B with similar entities |
| SCREENS_FOR | SCREENED_BY | A filters the universe to find instances with property B |
| FILTERS_OUT | FILTERED_OUT_BY | A removes B from consideration based on criteria |
| SEGMENTS | SEGMENTED_BY | A divides B into meaningful subgroups |
| WEIGHTS | WEIGHTED_BY | A assigns a relative importance measure to B |
| NORMALIZES | NORMALIZED_BY | A transforms B to a comparable scale |
| AGGREGATES | AGGREGATED_INTO | A combines multiple B values into a composite |
| DISAGGREGATES | DISAGGREGATED_FROM | A breaks down B into constituent components |
| ATTRIBUTES_TO | ATTRIBUTION_SOURCE | A assigns responsibility for B's performance to a cause |
| COMPARES | COMPARED_BY | A measures B against a reference or peer |

---

### Category 16 — Governance and Audit Relationships
*Define how authority, compliance, and accountability flow.*

| Relationship | Inverse | Brief Meaning |
|---|---|---|
| AUDITS | AUDITED_BY | A independently examines and certifies B |
| REVIEWS | REVIEWED_BY | A periodically examines B's quality or compliance |
| ESCALATES_TO | ESCALATED_FROM | A passes B's issue to a higher authority |
| SANCTIONS | SANCTIONED_BY | A penalizes B for violations |
| ENFORCES | ENFORCED_BY | A compels compliance with rule B |
| EXEMPTS | EXEMPTED_BY | A releases B from a general obligation |
| APPROVES | APPROVED_BY | A grants formal permission for B |
| REJECTS | REJECTED_BY | A formally denies B |
| CERTIFIES | CERTIFIED_BY | A validates that B meets defined standards |
| DISQUALIFIES | DISQUALIFIED_BY | A determines that B no longer meets criteria |
| MANDATES | MANDATED_BY | A legally requires B |
| PROHIBITS | PROHIBITED_BY | A legally forbids B |

---

### Category 17 — Context and Scope Relationships
*Define the conditions under which other relationships are valid.*

| Relationship | Inverse | Brief Meaning |
|---|---|---|
| APPLIES_IN | CONTEXT_FOR | Relationship/rule A is valid within scope B |
| VALID_FOR | VALIDATION_SCOPE | A's truth or relevance is bounded by condition B |
| CONDITIONED_ON | CONDITIONS | A's behavior depends on state B |
| SCOPED_TO | SCOPE_OF | A applies only within domain/period B |
| QUALIFIED_BY | QUALIFIES | A's meaning is modified by condition B |
| SUBJECT_TO | GOVERNS | A must comply with rule/constraint B |
| VARIES_WITH | MODULATES | A changes systematically as a function of B |
| STABLE_UNDER | STABILITY_CONDITION | A's relationship holds even when condition B changes |
| BREAKS_DOWN_IN | BREAKDOWN_CONDITION | A's relationship fails under extreme condition B |

---

### Category 18 — Semantic and Identity Relationships
*Define type hierarchies and identity mappings.*

| Relationship | Inverse | Brief Meaning |
|---|---|---|
| IS_A | HAS_SUBTYPE | A is a specialization of type B |
| INSTANCE_OF | HAS_INSTANCE | A is a specific instance of type B |
| SYNONYM_OF | SYNONYM_OF | A and B refer to the same concept by different names |
| MAPS_TO | MAPPED_FROM | A corresponds to B in a different system or classification |
| REPRESENTS | REPRESENTED_BY | A stands as a proxy or symbol for B |
| PROXIES_FOR | PROXY_USED_BY | A is used as a measurable substitute for unobservable B |
| EQUIVALENT_TO | EQUIVALENT_TO | A and B are interchangeable in defined contexts |
| ANALOGOUS_TO | ANALOGOUS_TO | A and B share structural similarity useful for reasoning |
| DISTINGUISHES_FROM | DISTINGUISHED_FROM | A and B appear similar but have important differences |
| SPECIALIZES | GENERALIZED_BY | A is a more specific form of B |

---

## PART III — COMPLETE RELATIONSHIP DEFINITIONS

*For every relationship: all 16 attributes. Organized by category. Critical relationships receive full prose treatment; structural relationships use efficient table format.*

---

## CATEGORY 1 — STRUCTURAL RELATIONSHIPS

---

### REL-001 — CONTAINS / PART_OF

| Attribute | Value |
|---|---|
| **Name** | CONTAINS (forward) / PART_OF (inverse) |
| **Definition** | A structural relationship where entity A includes entity B as a meaningful component, and entity B exists as a constituent of entity A |
| **Meaning** | A is the whole; B is the part. B cannot be fully understood without reference to A. |
| **Direction** | A → B (A CONTAINS B); inverse: B PART_OF A |
| **Inverse** | PART_OF / CONTAINS |
| **Allowed Entity Types** | A: Market, Exchange, Index, Portfolio, Sector, Universe, Option Chain; B: Exchange, Trading Session, Stock, Position, Industry, Instrument, Options Contract |
| **Cardinality** | 1→N (one container holds many parts) |
| **Strength** | Structural — permanent during lifecycle overlap |
| **Mandatory/Optional** | Mandatory — no part exists without a container |
| **Lifecycle** | Exists as long as both entities are active and B is a recognized component of A |
| **Temporal Behaviour** | Stable. Changes only when B is added or removed from A (e.g., index rebalancing) |
| **Constraints** | B must be a valid type for inclusion in A; inclusion must be formally recognized |
| **Examples** | NSE **CONTAINS** NSE F&O Segment; NIFTY 50 **CONTAINS** Reliance Industries; Portfolio **CONTAINS** Position in HDFC Bank |
| **Knowledge Produced** | Structural context: understanding B requires understanding A's rules, scope, and constraints |
| **Reasoning Value** | Critical for traversal: "what contains this entity?" determines regulatory regime, pricing rules, settlement framework |
| **Risk** | If container A faces stress (exchange circuit halt), all parts B are affected simultaneously |
| **Importance** | Critical |

---

### REL-002 — SUB_TYPE_OF / HAS_SUBTYPE

| Attribute | Value |
|---|---|
| **Name** | SUB_TYPE_OF (forward) / HAS_SUBTYPE (inverse) |
| **Definition** | A type-hierarchy relationship where entity type A is a more specific kind of entity type B — inheriting all B's properties and adding its own |
| **Meaning** | Every instance of A is also an instance of B. A is narrower than B. |
| **Direction** | A SUB_TYPE_OF B (A is the child; B is the parent type) |
| **Inverse** | HAS_SUBTYPE |
| **Allowed Entity Types** | Both A and B must be entity types (not instances) in the investment ontology |
| **Cardinality** | N→1 (many subtypes can share one parent type) |
| **Strength** | Structural — permanently defined by type hierarchy |
| **Mandatory/Optional** | Mandatory — every entity type must have a position in the type hierarchy |
| **Lifecycle** | Permanent — type hierarchies change only through ontology revision |
| **Temporal Behaviour** | Static. Changes only when the ontology itself is revised. |
| **Constraints** | No circular inheritance. Single parent per type (or explicit multi-inheritance with conflict resolution) |
| **Examples** | Options Contract **SUB_TYPE_OF** Derivative; Derivative **SUB_TYPE_OF** Financial Instrument; Listed Company **SUB_TYPE_OF** Organization |
| **Knowledge Produced** | Property inheritance: knowing B's properties tells you A's minimum properties; enables reasoning by analogy |
| **Reasoning Value** | Enables class-level inference: rules that apply to Derivatives apply to Options Contracts |
| **Risk** | Over-generalization: assuming subtype fully inherits parent behavior without noting the differences |
| **Importance** | Critical (for reasoning architecture) |

---

### REL-003 — COMPOSED_OF / COMPONENT_OF

| Attribute | Value |
|---|---|
| **Name** | COMPOSED_OF / COMPONENT_OF |
| **Definition** | A whole-part relationship where A's identity and existence is fundamentally defined by its components B; the components' meaning derives from being part of A |
| **Meaning** | Composition is strong containment: parts without the whole lose their primary meaning |
| **Direction** | A COMPOSED_OF B |
| **Inverse** | COMPONENT_OF |
| **Allowed Entity Types** | A: Option Chain, Reasoning Chain, Annual Report, Financial Statement, Portfolio (composition view); B: Options Contracts, Evidence Items, Financial Statement Sub-entities |
| **Cardinality** | 1→N |
| **Strength** | Strong structural — identity-binding |
| **Examples** | Reasoning Chain **COMPOSED_OF** Evidence Items; Option Chain **COMPOSED_OF** Options Contracts; Annual Report **COMPOSED_OF** P&L, Balance Sheet, Cash Flow, Notes |
| **Knowledge Produced** | Understanding the whole requires examining all components |
| **Reasoning Value** | High — composition implies that gaps in components degrade the whole |
| **Importance** | High |

---

### REL-004 — AGGREGATES / AGGREGATED_INTO

| Attribute | Value |
|---|---|
| **Name** | AGGREGATES / AGGREGATED_INTO |
| **Definition** | A whole-part relationship where A is a collection of independently-existing Bs; parts retain independent existence and can exist in multiple aggregates |
| **Meaning** | Aggregation is weak containment: parts can exist outside the aggregate |
| **Direction** | A AGGREGATES B (A is the container; B parts exist independently) |
| **Inverse** | AGGREGATED_INTO |
| **Allowed Entity Types** | A: Portfolio, Index, Universe, Fund, Sector, Watchlist; B: Positions, Stocks, Instruments, Companies |
| **Cardinality** | N→N (one stock can be in multiple indices; one portfolio can aggregate many positions) |
| **Strength** | Structural — medium; parts can be reassigned |
| **Examples** | NIFTY 50 **AGGREGATES** 50 constituent stocks; Portfolio **AGGREGATES** all current positions; Fund **AGGREGATES** constituent securities |
| **Knowledge Produced** | Collective behavior: aggregate properties (total value, sector exposure, beta) emerge from component properties |
| **Importance** | High |

---

### REL-005 — MEMBER_OF / HAS_MEMBER

| Attribute | Value |
|---|---|
| **Name** | MEMBER_OF / HAS_MEMBER |
| **Definition** | An entity A belongs to a defined group, category, or collective entity B |
| **Meaning** | B's rules, characteristics, and treatment apply to A by virtue of membership |
| **Direction** | A MEMBER_OF B |
| **Inverse** | HAS_MEMBER |
| **Allowed Entity Types** | A: Stock, Company, Instrument, Broker; B: Index, Exchange, Regulator's universe, Category |
| **Cardinality** | N→N |
| **Examples** | HDFC Bank **MEMBER_OF** NIFTY 50; Zerodha **MEMBER_OF** NSE; RELIANCE **MEMBER_OF** NIFTY Bank (via HDFCBANK, not a good example) — Kotak Bank **MEMBER_OF** NIFTY Bank Index |
| **Knowledge Produced** | Membership triggers specific rules (index inclusion → passive fund buying; F&O member → leverage available) |
| **Importance** | High |

---

## CATEGORY 2 — OWNERSHIP AND CONTROL RELATIONSHIPS

---

### REL-006 — OWNS / OWNED_BY

| Attribute | Value |
|---|---|
| **Name** | OWNS (forward) / OWNED_BY (inverse) |
| **Definition** | A holds legal ownership rights over entity B — conferring rights to B's economic benefits, voting rights, and responsibility for B's liabilities |
| **Meaning** | Ownership is the strongest form of control: A can direct B's disposition, receive B's returns, and bears B's losses |
| **Direction** | A OWNS B |
| **Inverse** | OWNED_BY |
| **Allowed Entity Types** | A: Investor, Fund House, Portfolio, Company, Government; B: Stock, Portfolio, Subsidiary, Property, Bond |
| **Cardinality** | N→N (multiple entities can own portions of B; A can own multiple Bs) |
| **Strength** | Maximum — legal and binding |
| **Mandatory/Optional** | Mandatory — every ownable entity must have an owner |
| **Lifecycle** | Created when ownership is transferred; terminated when sold, gifted, or dissolved |
| **Temporal Behaviour** | Persistent. Changes on ownership transfer events. |
| **Constraints** | Ownership must be registered (demat for securities); ownership thresholds trigger regulatory disclosure (5%, 10%, 25%, 75% in SEBI regulations) |
| **Examples** | Mukesh Ambani family **OWNS** 50.3% of Reliance Industries; LIC **OWNS** stake in HDFC Bank; Portfolio_01 **OWNS** 1000 shares of TATAMOTORS |
| **Knowledge Produced** | Ownership concentration signals control; promoter ownership changes signal conviction; institutional ownership signals smart money presence |
| **Reasoning Value** | Critical — ownership change is among the highest-value signals for directional bias |
| **Risk** | Concentrated ownership creates governance risk; owner distress may force selling |
| **Importance** | Critical |

---

### REL-007 — CONTROLS / CONTROLLED_BY

| Attribute | Value |
|---|---|
| **Name** | CONTROLS / CONTROLLED_BY |
| **Definition** | A has the practical ability to determine the strategic and operational direction of B, whether through legal ownership, contractual authority, or de facto power |
| **Meaning** | Control is broader than ownership — it includes contractual arrangements, board representation, and voting blocks that fall short of majority ownership |
| **Direction** | A CONTROLS B |
| **Inverse** | CONTROLLED_BY |
| **Allowed Entity Types** | A: Promoter Group, Government, Parent Company, SEBI; B: Company, Subsidiary, Market, Exchange, Regulator |
| **Cardinality** | 1→N (one entity may control multiple; one entity may be co-controlled) |
| **Strength** | High — but less absolute than legal ownership |
| **Examples** | Tata Sons **CONTROLS** Tata Motors; Government of India **CONTROLS** ONGC (via 58% stake + nominee directors); RBI **CONTROLS** banking sector credit growth |
| **Knowledge Produced** | Control concentration; potential for related-party transactions; governance quality assessment |
| **Importance** | Critical |

---

### REL-008 — GOVERNS / GOVERNED_BY

| Attribute | Value |
|---|---|
| **Name** | GOVERNS / GOVERNED_BY |
| **Definition** | A establishes the rules, standards, and norms that B must follow within a defined domain |
| **Meaning** | Governance is rule-making authority — not day-to-day control but the power to set the framework |
| **Direction** | A GOVERNS B |
| **Inverse** | GOVERNED_BY |
| **Allowed Entity Types** | A: Board of Directors, SEBI, RBI, Government, Index Provider, Exchange; B: Company operations, Markets, Banks, Listed companies, Index constituents |
| **Cardinality** | 1→N |
| **Examples** | Board of Directors **GOVERNS** listed company operations; SEBI **GOVERNS** all market participants; Index provider **GOVERNS** index composition rules |
| **Knowledge Produced** | Governance quality signals; regulatory risk assessment |
| **Importance** | Critical |

---

### REL-009 — REGULATES / REGULATED_BY

| Attribute | Value |
|---|---|
| **Name** | REGULATES / REGULATED_BY |
| **Definition** | A is the statutory authority that sets rules, grants licenses, and enforces compliance for B within a defined legal framework |
| **Meaning** | Regulation is the highest-authority form of governance — backed by legal sanction |
| **Direction** | A REGULATES B |
| **Inverse** | REGULATED_BY |
| **Allowed Entity Types** | A: SEBI, RBI, IRDAI, PFRDA, CCI, MCA; B: Listed companies, Brokers, Banks, Insurers, Pension funds, Market participants |
| **Cardinality** | N→N |
| **Examples** | SEBI **REGULATES** all listed companies; RBI **REGULATES** commercial banks; IRDAI **REGULATES** insurance companies |
| **Knowledge Produced** | Regulatory risk profile; compliance requirements; sector-level constraints on business behavior |
| **Importance** | Critical |

---

### REL-010 — MANAGES / MANAGED_BY

| Attribute | Value |
|---|---|
| **Name** | MANAGES / MANAGED_BY |
| **Definition** | A has operational responsibility for B — including decisions about B's resources, direction, and performance |
| **Direction** | A MANAGES B |
| **Inverse** | MANAGED_BY |
| **Allowed Entity Types** | A: Fund Manager, CEO, Management Team, Portfolio Manager; B: Fund, Company, Portfolio |
| **Cardinality** | 1→N |
| **Examples** | Fund Manager X **MANAGES** HDFC Equity Fund; CEO A **MANAGES** operations of Company B |
| **Knowledge Produced** | Manager quality as alpha/risk factor; management change as signal |
| **Importance** | High |

---

### REL-011 — AUTHORIZES / AUTHORIZED_BY

| Attribute | Value |
|---|---|
| **Name** | AUTHORIZES / AUTHORIZED_BY |
| **Definition** | A grants B the formal right or permission to perform a specific action or assume a specific role |
| **Direction** | A AUTHORIZES B |
| **Inverse** | AUTHORIZED_BY |
| **Allowed Entity Types** | A: SEBI, Exchange, Board, Risk System; B: Broker, Market Maker, Decision, Trade |
| **Cardinality** | 1→N |
| **Examples** | SEBI **AUTHORIZES** Zerodha to operate as a stockbroker; Risk System **AUTHORIZES** Decision to proceed (after risk checks pass) |
| **Knowledge Produced** | Authorization status determines what actions are legally or operationally permitted |
| **Importance** | High |

---

### REL-012 — CUSTODIES / CUSTODIED_BY

| Attribute | Value |
|---|---|
| **Name** | CUSTODIES / CUSTODIED_BY |
| **Definition** | A holds B in safekeeping on behalf of its owner, without owning it |
| **Direction** | A CUSTODIES B |
| **Inverse** | CUSTODIED_BY |
| **Allowed Entity Types** | A: NSDL, CDSL, Broker, Bank; B: Securities, Bonds, Portfolio |
| **Cardinality** | 1→N |
| **Examples** | NSDL **CUSTODIES** all dematerialized equity holdings; CDSL **CUSTODIES** bond holdings |
| **Knowledge Produced** | Custody chain clarity; counterparty risk in settlement |
| **Importance** | High |

---

## CATEGORY 3 — ISSUANCE AND MARKET STRUCTURE RELATIONSHIPS

---

### REL-013 — ISSUES / ISSUED_BY

| Attribute | Value |
|---|---|
| **Name** | ISSUES (forward) / ISSUED_BY (inverse) |
| **Definition** | Entity A creates and makes available to the market a financial instrument B, establishing itself as the counterparty for all of B's contractual obligations |
| **Meaning** | Issuance is the act of bringing an instrument into existence. The issuer is legally bound by B's terms for B's entire lifecycle. |
| **Direction** | A ISSUES B (A is issuer; B is the instrument) |
| **Inverse** | ISSUED_BY |
| **Allowed Entity Types** | A: Listed Company, Government, RBI, Fund House, Exchange; B: Equity, Bond, T-Bill, ETF, Futures Contract, Options Contract, Commercial Paper |
| **Cardinality** | 1→N (one company can issue multiple instruments) |
| **Strength** | Permanent — binding for instrument's entire lifecycle |
| **Mandatory/Optional** | Mandatory — every instrument has an issuer |
| **Lifecycle** | Created at instrument issuance; terminated at instrument maturity, delisting, or wind-up |
| **Temporal Behaviour** | Permanent during instrument lifecycle. Survives changes in the company's other relationships. |
| **Constraints** | Issuer must have regulatory authorization (SEBI, RBI, MCA). Issuance size, terms must comply with applicable regulations. |
| **Examples** | Reliance Industries **ISSUES** Reliance Equity (NSE: RELIANCE); Government of India **ISSUES** 7.10% G-Sec 2034; NSE **ISSUES** NIFTY Futures contracts |
| **Knowledge Produced** | Issuer quality directly informs instrument risk; issuer financial health predicts default probability; management quality signals growth potential |
| **Reasoning Value** | Critical — issuer is the anchor of fundamental analysis for debt instruments; for equity, issuer IS the underlying investment thesis |
| **Risk** | Issuer distress propagates to instrument: company bankruptcy → equity to zero; credit downgrade → bond price collapse |
| **Importance** | Critical |

---

### REL-014 — LISTED_ON / LISTS

| Attribute | Value |
|---|---|
| **Name** | LISTED_ON (forward) / LISTS (inverse) |
| **Definition** | A financial instrument A is formally admitted to trading on exchange B, making it accessible to market participants through B's infrastructure |
| **Meaning** | Listing grants an instrument price discovery, liquidity, regulatory oversight, and visibility. It creates the institutional framework for the instrument to function. |
| **Direction** | A LISTED_ON B (instrument → exchange) |
| **Inverse** | LISTS |
| **Allowed Entity Types** | A: Equity, Bond, ETF, Futures, Options; B: NSE, BSE, MCX, NCDEX |
| **Cardinality** | N→N (one instrument can be listed on multiple exchanges; one exchange lists many instruments) |
| **Strength** | Active while listing is maintained |
| **Mandatory/Optional** | Mandatory — an instrument cannot be publicly traded without listing |
| **Lifecycle** | Created at IPO/contract launch; terminated at delisting, compulsory delisting, or contract expiry |
| **Examples** | Infosys Equity **LISTED_ON** NSE and BSE; NIFTY50 Futures **LISTED_ON** NSE F&O Segment |
| **Knowledge Produced** | Exchange-specific liquidity, price discovery quality, regulatory framework, available derivative universe |
| **Reasoning Value** | High — listing exchange determines circuit limits, settlement rules, eligible participants |
| **Importance** | Critical |

---

### REL-015 — UNDERLIES / DERIVED_FROM_UNDERLYING

| Attribute | Value |
|---|---|
| **Name** | UNDERLIES (forward) / DERIVED_FROM_UNDERLYING (inverse) |
| **Definition** | A is the reference asset from which derivative instrument B derives its value; B's price is a function of A's price |
| **Meaning** | The underlying anchors the derivative's entire value. Without A, B has no reference and no value. |
| **Direction** | A UNDERLIES B (underlying → derivative) |
| **Inverse** | DERIVED_FROM_UNDERLYING |
| **Allowed Entity Types** | A: Equity, Index, Bond, Currency Pair, Commodity; B: Futures Contract, Options Contract, ETF (partially) |
| **Cardinality** | 1→N (one underlying can have many derivative series across strikes and expiries) |
| **Strength** | Mathematical — the relationship is encoded in the derivative's pricing formula |
| **Examples** | NIFTY 50 **UNDERLIES** all NIFTY Futures and NIFTY Options; Reliance Equity **UNDERLIES** Reliance Futures and Reliance Options |
| **Knowledge Produced** | Pricing model: derivative value = f(underlying price, time, volatility, rate); basis = derivative price minus spot price |
| **Reasoning Value** | Critical — without this relationship, derivative pricing, hedging, and arbitrage are impossible |
| **Risk** | Discontinuity risk: if underlying is suspended, all derivatives lose reference price |
| **Importance** | Critical |

---

### REL-016 — CONSTITUENT_OF / COMPRISES

| Attribute | Value |
|---|---|
| **Name** | CONSTITUENT_OF (forward) / COMPRISES (inverse) |
| **Definition** | A is one of the component instruments of index/basket B, with a defined weight contributing to B's overall value |
| **Direction** | A CONSTITUENT_OF B |
| **Inverse** | COMPRISES |
| **Allowed Entity Types** | A: Equity, Bond, Commodity; B: Index, ETF, Basket, Portfolio |
| **Cardinality** | N→N |
| **Examples** | HDFC Bank **CONSTITUENT_OF** NIFTY 50 (weight ~12%); RELIANCE **CONSTITUENT_OF** NIFTY 50 (weight ~10%) |
| **Knowledge Produced** | Weight in index → magnitude of passive fund flows on rebalancing; index constituent status → institutional coverage signal |
| **Reasoning Value** | Critical — index inclusion/exclusion triggers forced buying/selling by passive funds (MSCI weight changes move billions) |
| **Risk** | Exclusion from index triggers forced selling pressure; inclusion triggers forced buying |
| **Importance** | Critical |

---

### REL-017 — BENCHMARKED_AGAINST / BENCHMARKS

| Attribute | Value |
|---|---|
| **Name** | BENCHMARKED_AGAINST / BENCHMARKS |
| **Definition** | A's performance is formally or conventionally measured relative to index/rate B |
| **Direction** | A BENCHMARKED_AGAINST B |
| **Inverse** | BENCHMARKS |
| **Allowed Entity Types** | A: Portfolio, Fund, Strategy, Manager; B: Index, Rate, Composite |
| **Cardinality** | N→N |
| **Examples** | Large cap equity fund **BENCHMARKED_AGAINST** NIFTY 50; Debt fund **BENCHMARKED_AGAINST** CRISIL Composite Bond Index |
| **Knowledge Produced** | Active/passive decision: how much alpha vs beta is the strategy producing? |
| **Importance** | High |

---

### REL-018 — CLASSIFIED_IN / CLASSIFIES

| Attribute | Value |
|---|---|
| **Name** | CLASSIFIED_IN / CLASSIFIES |
| **Definition** | A belongs to classification category B within a defined taxonomy system |
| **Direction** | A CLASSIFIED_IN B |
| **Inverse** | CLASSIFIES |
| **Allowed Entity Types** | A: Company, Instrument, Fund; B: Sector Classification, Index Category, SEBI MF Category |
| **Cardinality** | N→1 (in a given taxonomy) or N→N (across multiple taxonomies) |
| **Examples** | HDFC Bank **CLASSIFIED_IN** Financials (GICS); AXIS Bank **CLASSIFIED_IN** Private Banks (NSE Sectoral) |
| **Knowledge Produced** | Sector-level analysis; peer comparison; sector rotation strategies |
| **Importance** | High |

---

## CATEGORY 4 — FINANCIAL ACTIVITY RELATIONSHIPS

---

### REL-019 — HOLDS / HELD_BY

| Attribute | Value |
|---|---|
| **Name** | HOLDS (forward) / HELD_BY (inverse) |
| **Definition** | Entity A currently has a position in, or directly owns, financial instrument B as an active part of its portfolio |
| **Meaning** | Holding is the live, active ownership state. It implies current economic exposure to B's price movements. |
| **Direction** | A HOLDS B |
| **Inverse** | HELD_BY |
| **Allowed Entity Types** | A: Portfolio, Investor, Fund, Institution; B: Equity, Bond, Futures, Options, ETF |
| **Cardinality** | N→N |
| **Strength** | Active — exists while the position is open |
| **Lifecycle** | Created when position is opened; terminated when position is closed |
| **Examples** | SBI Mutual Fund **HOLDS** 2.3% of Infosys; Portfolio_01 **HOLDS** 500 shares of TATAMOTORS long |
| **Knowledge Produced** | Institutional ownership → demand side data; large holder activity changes → supply/demand signal |
| **Reasoning Value** | Critical — "who is holding" determines selling pressure potential and conviction signal quality |
| **Importance** | Critical |

---

### REL-020 — INVESTS_IN / INVESTED_IN_BY

| Attribute | Value |
|---|---|
| **Name** | INVESTS_IN / INVESTED_IN_BY |
| **Definition** | Entity A deploys capital with the intention of earning returns from entity B over a defined or open-ended time horizon |
| **Direction** | A INVESTS_IN B |
| **Inverse** | INVESTED_IN_BY |
| **Allowed Entity Types** | A: Fund House, Investor, Portfolio; B: Company, Equity, Bond, Project, Sector |
| **Cardinality** | N→N |
| **Examples** | Mirae Asset MF **INVESTS_IN** Infosys; LIC **INVESTS_IN** Indian equities broadly |
| **Knowledge Produced** | Institutional conviction; capital allocation preferences by sector |
| **Importance** | High |

---

### REL-021 — ALLOCATES_TO / ALLOCATED_FROM

| Attribute | Value |
|---|---|
| **Name** | ALLOCATES_TO / ALLOCATED_FROM |
| **Definition** | A assigns a defined portion of available capital or resources to target B according to a defined rule or decision |
| **Direction** | A ALLOCATES_TO B |
| **Inverse** | ALLOCATED_FROM |
| **Allowed Entity Types** | A: Portfolio, Fund, Decision; B: Position, Instrument, Sector, Strategy |
| **Cardinality** | 1→N |
| **Examples** | Portfolio **ALLOCATES_TO** 5% in RELIANCE; Decision **ALLOCATES_TO** ₹50,000 in NIFTY call options |
| **Knowledge Produced** | Capital allocation is the revealed preference of the investment process |
| **Importance** | Critical |

---

### REL-022 — TRADES / TRADED_BY

| Attribute | Value |
|---|---|
| **Name** | TRADES / TRADED_BY |
| **Definition** | Entity A executes a buy or sell transaction in instrument B through a defined market mechanism |
| **Direction** | A TRADES B |
| **Inverse** | TRADED_BY |
| **Allowed Entity Types** | A: Portfolio, Fund, Investor, Broker; B: Equity, Bond, Futures, Options, Currency |
| **Cardinality** | N→N |
| **Examples** | FII **TRADES** NIFTY Futures (net seller ₹1,200 crore); DII **TRADES** large-cap equities |
| **Knowledge Produced** | Fund flow data; institutional activity; sentiment signal from volume and direction |
| **Importance** | Critical |

---

### REL-023 — COLLATERALIZES / COLLATERALIZED_BY

| Attribute | Value |
|---|---|
| **Name** | COLLATERALIZES / COLLATERALIZED_BY |
| **Definition** | Entity A is pledged as security to support an obligation or position B |
| **Direction** | A COLLATERALIZES B |
| **Inverse** | COLLATERALIZED_BY |
| **Allowed Entity Types** | A: Securities, Bonds, Cash; B: Margin requirement, Loan, Position |
| **Cardinality** | N→N |
| **Examples** | Shares **COLLATERALIZE** a margin obligation; GOI Bonds **COLLATERALIZE** repo borrowing |
| **Knowledge Produced** | Pledging ratio signals promoter financial stress |
| **Importance** | High |

---

### REL-024 — HEDGES / HEDGED_BY (Financial Activity)

| Attribute | Value |
|---|---|
| **Name** | HEDGES / HEDGED_BY |
| **Definition** | Entity A is held or constructed specifically to offset the risk created by holding entity B |
| **Direction** | A HEDGES B (A is the hedge; B is the exposure being protected) |
| **Inverse** | HEDGED_BY |
| **Allowed Entity Types** | A: Options Contract, Futures Contract, Currency Forward, Inverse ETF; B: Position, Portfolio, Exposure |
| **Cardinality** | N→N |
| **Examples** | NIFTY Put Option **HEDGES** long equity portfolio; USD/INR Forward **HEDGES** FII equity exposure |
| **Knowledge Produced** | Hedge ratio; net exposure after hedging; basis risk |
| **Reasoning Value** | Critical for risk-adjusted position sizing |
| **Importance** | Critical |

---

## CATEGORY 5 — ORGANIZATIONAL RELATIONSHIPS

---

### REL-025 — COMPETES_WITH

| Attribute | Value |
|---|---|
| **Name** | COMPETES_WITH |
| **Definition** | Entity A and entity B vie for the same customers, market share, resources, or capital within a defined competitive arena |
| **Meaning** | Competition creates comparison pressure — what A achieves, B must respond to. Competitive dynamics drive pricing, margins, and innovation. |
| **Direction** | Symmetric (A COMPETES_WITH B = B COMPETES_WITH A) but competitive advantage may be asymmetric |
| **Inverse** | COMPETES_WITH (symmetric) |
| **Allowed Entity Types** | A: Company, Fund, Strategy; B: Company, Fund, Strategy |
| **Cardinality** | N→N |
| **Strength** | Dynamic — varies with market conditions and strategic choices |
| **Examples** | HDFC Bank **COMPETES_WITH** ICICI Bank; Infosys **COMPETES_WITH** TCS, Wipro, HCLTech; Jio **COMPETES_WITH** Airtel, Vi |
| **Knowledge Produced** | Competitive position: who is gaining/losing market share; pricing power relative to competitors; risk of margin compression |
| **Reasoning Value** | High — competitor performance is a leading indicator of company's own trajectory |
| **Importance** | High |

---

### REL-026 — ACQUIRES / ACQUIRED_BY

| Attribute | Value |
|---|---|
| **Name** | ACQUIRES / ACQUIRED_BY |
| **Definition** | Entity A purchases a controlling or significant stake in entity B, gaining ownership rights and strategic control |
| **Direction** | A ACQUIRES B |
| **Inverse** | ACQUIRED_BY |
| **Allowed Entity Types** | A: Company, Investor, Private Equity; B: Company, Subsidiary, Fund |
| **Cardinality** | N→N |
| **Temporal Behaviour** | Event — creates lasting OWNS/CONTROLS relationship once complete |
| **Examples** | HDFC Bank **ACQUIRED** HDFC Ltd; Tata Motors **ACQUIRED** Jaguar Land Rover |
| **Knowledge Produced** | Strategic fit; synergy potential; dilution impact; management bandwidth |
| **Importance** | Critical (event) |

---

### REL-027 — RATED_BY / RATES

| Attribute | Value |
|---|---|
| **Name** | RATED_BY / RATES |
| **Definition** | Rating Agency B formally assesses and publicly assigns a creditworthiness score to entity A |
| **Direction** | A RATED_BY B |
| **Inverse** | RATES |
| **Allowed Entity Types** | A: Company, Bond, Commercial Paper; B: CRISIL, ICRA, CARE, Moody's, S&P |
| **Cardinality** | N→N |
| **Temporal Behaviour** | Dynamic — ratings are reviewed periodically and changed on events |
| **Examples** | RELIANCE Commercial Paper **RATED_BY** CRISIL (A1+); Company X **RATED_BY** CARE (downgraded from AA to AA-) |
| **Knowledge Produced** | Credit quality signal; default probability estimate; required yield premium |
| **Importance** | Critical (debt), High (equity as governance signal) |

---

### REL-028 — SUPPLIED_BY / SUPPLIES_TO

| Attribute | Value |
|---|---|
| **Name** | SUPPLIED_BY / SUPPLIES_TO |
| **Definition** | Entity A receives key inputs or goods from entity B; or A provides key outputs to B |
| **Direction** | A SUPPLIED_BY B (A is receiver; B is supplier) |
| **Inverse** | SUPPLIES_TO |
| **Allowed Entity Types** | A: Company; B: Company, Commodity Supplier |
| **Cardinality** | N→N |
| **Examples** | Auto OEM **SUPPLIED_BY** steel companies; Pharma company **SUPPLIED_BY** chemical API manufacturers |
| **Knowledge Produced** | Input cost sensitivity; supply chain disruption risk; pricing power over supplier |
| **Importance** | High (for sector analysis) |

---

## CATEGORY 6 — CAUSAL RELATIONSHIPS

---

### REL-029 — CAUSES / CAUSED_BY

| Attribute | Value |
|---|---|
| **Name** | CAUSES (forward) / CAUSED_BY (inverse) |
| **Definition** | A change in the state of entity A deterministically or near-deterministically produces a defined change in the state of entity B through a documented transmission mechanism |
| **Meaning** | Causation is the highest-confidence directional relationship. It implies a known mechanism — not just correlation. Establishing causation in investment contexts requires a documented transmission pathway. |
| **Direction** | A CAUSES B (A is the cause; B is the effect) |
| **Inverse** | CAUSED_BY |
| **Allowed Entity Types** | A: Interest Rate, Policy Event, Corporate Action, RBI Decision; B: Bond Price, Loan Cost, Stock Price, Sector Rotation |
| **Cardinality** | N→N |
| **Strength** | High — but mechanism must be documented to qualify as causation |
| **Mandatory/Optional** | Optional |
| **Lifecycle** | Valid while the causal mechanism is intact; may break down under regime change |
| **Temporal Behaviour** | May have lag — A's change at time T causes B's change at T+k with measurable k |
| **Constraints** | Must document the transmission mechanism. Correlation alone is insufficient. The system must track mechanism validity. |
| **Examples** | RBI Rate Hike **CAUSES** increase in MCLR (transmission: policy rate → bank borrowing cost → lending rate); Corporate Action BONUS_ISSUE **CAUSES** face value reduction in stock |
| **Knowledge Produced** | Transmission pathway model; lag estimation; strength of causation; regime validity |
| **Reasoning Value** | Critical — causal relationships enable forward-looking reasoning; knowing A changed allows predicting B will change |
| **Risk** | Causal relationships can break down: mechanism may fail under extreme conditions or regime change |
| **Importance** | Critical |

---

### REL-030 — TRIGGERS / TRIGGERED_BY

| Attribute | Value |
|---|---|
| **Name** | TRIGGERS / TRIGGERED_BY |
| **Definition** | A's crossing of a defined threshold or occurrence of a defined condition initiates event or state change B |
| **Meaning** | Triggering is threshold-based causation: A doesn't cause B continuously — it causes B only when A's state crosses a specific boundary |
| **Direction** | A TRIGGERS B |
| **Inverse** | TRIGGERED_BY |
| **Allowed Entity Types** | A: Price Level, Conviction Score, VIX Level, Loss Threshold, Event; B: Alert, Decision, Order, Position Exit, Circuit Halt |
| **Cardinality** | N→N |
| **Examples** | Conviction crossing 6.5 **TRIGGERS** Decision; Stock hitting Stop Loss **TRIGGERS** Exit Order; VIX > 45 **TRIGGERS** Kill Switch; Ex-date **TRIGGERS** dividend adjustment |
| **Knowledge Produced** | System behavior map: what events cause what actions; threshold sensitivity analysis |
| **Reasoning Value** | Critical for system design — every automated action in the system has a trigger relationship |
| **Importance** | Critical |

---

### REL-031 — INFLUENCES / INFLUENCED_BY

| Attribute | Value |
|---|---|
| **Name** | INFLUENCES / INFLUENCED_BY |
| **Definition** | A change in entity A's state changes the probability distribution of entity B's future state — without full determinism |
| **Meaning** | Influence is directional but probabilistic. A increases or decreases the likelihood of outcomes for B. Multiple entities may simultaneously influence B. |
| **Direction** | A INFLUENCES B |
| **Inverse** | INFLUENCED_BY |
| **Allowed Entity Types** | A: Market Regime, Macro Variable, Sector State, Event; B: Strategy Performance, Company Earnings, Stock Price, Risk Level |
| **Cardinality** | N→N |
| **Strength** | Variable — measured as correlation coefficient or conditional probability shift |
| **Temporal Behaviour** | Dynamic — strength of influence varies with market regime |
| **Examples** | Market Regime **INFLUENCES** Strategy Performance (trending regime favors momentum); US Fed Policy **INFLUENCES** RBI rate decisions; DXY strength **INFLUENCES** FII equity flows into India |
| **Knowledge Produced** | Influence network: which entities should be watched when analyzing B; regime-dependent influence strength |
| **Reasoning Value** | Critical — evidence that A has changed triggers reassessment of B's outlook |
| **Importance** | Critical |

---

### REL-032 — AMPLIFIES / AMPLIFIED_BY

| Attribute | Value |
|---|---|
| **Name** | AMPLIFIES / AMPLIFIED_BY |
| **Definition** | Entity A increases the magnitude or impact of an effect associated with B, beyond what would occur without A's presence |
| **Direction** | A AMPLIFIES B |
| **Inverse** | AMPLIFIED_BY |
| **Allowed Entity Types** | A: Leverage, Options Position, High Beta Stock, Media Coverage, Sentiment; B: Price Movement, Loss, Gain, Volatility |
| **Cardinality** | N→N |
| **Examples** | 5× Leverage **AMPLIFIES** Price Movement; Media coverage **AMPLIFIES** earnings surprise reaction; High beta stock **AMPLIFIES** index movement |
| **Knowledge Produced** | Amplification factor; leverage-adjusted risk calculation |
| **Importance** | High |

---

### REL-033 — DAMPENS / DAMPENED_BY

| Attribute | Value |
|---|---|
| **Name** | DAMPENS / DAMPENED_BY |
| **Definition** | Entity A reduces the magnitude or impact of an effect associated with B |
| **Direction** | A DAMPENS B |
| **Inverse** | DAMPENED_BY |
| **Allowed Entity Types** | A: Diversification, Hedging, Low Beta, DII Buying, Liquidity; B: Price Movement, Volatility, Loss, Portfolio Risk |
| **Examples** | DII systematic buying **DAMPENS** market falls; diversification **DAMPENS** idiosyncratic risk; low beta stocks **DAMPEN** portfolio volatility |
| **Importance** | High |

---

### REL-034 — TRANSMITS_TO / RECEIVED_FROM

| Attribute | Value |
|---|---|
| **Name** | TRANSMITS_TO / RECEIVED_FROM |
| **Definition** | An effect, signal, or state change originating in entity A passes through the system and manifests in entity B |
| **Meaning** | Transmission describes the pathway of contagion, signal propagation, or macro effect flow through the investment universe |
| **Direction** | A TRANSMITS_TO B (A is origin; B is recipient) |
| **Inverse** | RECEIVED_FROM |
| **Allowed Entity Types** | A: US Fed Decision, Global Market, Credit Market, Sector; B: RBI Response, Indian Market, Company Earnings, FII Flows |
| **Cardinality** | N→N (one source can transmit to many recipients; one recipient may receive from many sources) |
| **Examples** | Fed rate hike **TRANSMITS_TO** DXY strength → FII selling India → NIFTY decline; Oil price spike **TRANSMITS_TO** inflation → rate hike risk → auto sector margin pressure |
| **Knowledge Produced** | Transmission chain map: who receives what signal from whom, with measured lag and attenuation |
| **Reasoning Value** | Critical for macro analysis and multi-hop reasoning |
| **Importance** | Critical |

---

### REL-035 — CASCADES_INTO / PRECEDED_BY_CASCADE

| Attribute | Value |
|---|---|
| **Name** | CASCADES_INTO / PRECEDED_BY_CASCADE |
| **Definition** | A's stress or failure initiates a chain reaction that propagates through connected entities, amplifying at each step |
| **Direction** | A CASCADES_INTO B |
| **Inverse** | PRECEDED_BY_CASCADE |
| **Allowed Entity Types** | A: Market Event, Credit Default, Sector Collapse; B: Sector, Company, Portfolio |
| **Examples** | IL&FS default **CASCADED_INTO** NBFC crisis → mutual fund redemption pressure → liquidity crunch; Lehman collapse **CASCADED_INTO** global credit freeze |
| **Knowledge Produced** | Systemic risk map; cascade probability estimation |
| **Importance** | Critical (tail risk) |

---

### REL-036 — DISRUPTS / DISRUPTED_BY

| Attribute | Value |
|---|---|
| **Name** | DISRUPTS / DISRUPTED_BY |
| **Definition** | Entity A's emergence or action breaks the normal functioning or assumed continuity of entity B |
| **Direction** | A DISRUPTS B |
| **Inverse** | DISRUPTED_BY |
| **Allowed Entity Types** | A: New Entrant, Technology, Regulatory Change, Geopolitical Event; B: Industry, Company, Market |
| **Examples** | Jio **DISRUPTED** telecom industry; COVID-19 **DISRUPTED** aviation sector; UPI **DISRUPTED** traditional banking payment fees |
| **Knowledge Produced** | Disruption signal: which companies are threatened; which benefit; timeline estimation |
| **Importance** | High |

---

## CATEGORY 7 — TEMPORAL RELATIONSHIPS

---

### REL-037 — PRECEDES / FOLLOWS

| Attribute | Value |
|---|---|
| **Name** | PRECEDES (forward) / FOLLOWS (inverse) |
| **Definition** | Event or state A occurs before event or state B in chronological time, establishing a defined temporal ordering |
| **Meaning** | Temporal ordering enables sequence reasoning: if A precedes B, then observing A creates an expectation about B's timing |
| **Direction** | A PRECEDES B (A is earlier; B is later) |
| **Inverse** | FOLLOWS |
| **Allowed Entity Types** | A: Event, State Change, Data Release, Corporate Action, Earnings; B: Event, State Change, Market Reaction |
| **Cardinality** | N→N |
| **Strength** | Permanent (historical precedence is immutable) |
| **Temporal Behaviour** | Historical relationships are immutable; future patterns are probabilistic |
| **Constraints** | Must specify the time gap (T+0, T+1 day, T+2 weeks) to be useful for reasoning |
| **Examples** | Results announcement **PRECEDES** analyst estimate revision; Ex-dividend date **PRECEDES** dividend receipt; Quarter end **PRECEDES** earnings release (by 30-45 days) |
| **Knowledge Produced** | Timing model: when to expect B given A has occurred; calendar-based opportunity identification |
| **Reasoning Value** | High — "A just happened; B typically follows in T+k days" generates actionable preparation |
| **Importance** | High |

---

### REL-038 — EXPIRES_ON / EXPIRY_DATE_OF

| Attribute | Value |
|---|---|
| **Name** | EXPIRES_ON / EXPIRY_DATE_OF |
| **Definition** | Entity A ceases to exist or loses its contractual validity at date B |
| **Direction** | A EXPIRES_ON B (entity → date) |
| **Inverse** | EXPIRY_DATE_OF |
| **Allowed Entity Types** | A: Futures Contract, Options Contract, Right (Entitlement), Commercial Paper, Knowledge Item, Signal; B: Expiry Date |
| **Cardinality** | N→1 |
| **Examples** | NIFTY July Futures **EXPIRES_ON** last Thursday July; Hypothesis **EXPIRES_ON** 30 days unless refreshed |
| **Knowledge Produced** | Time pressure on positions; rollover decision timing |
| **Importance** | Critical |

---

### REL-039 — ROLLS_OVER_TO / ROLLED_OVER_FROM

| Attribute | Value |
|---|---|
| **Name** | ROLLS_OVER_TO / ROLLED_OVER_FROM |
| **Definition** | A position or contract in near-month A is transferred to far-month contract B as A approaches expiry |
| **Direction** | A ROLLS_OVER_TO B (near month → far month) |
| **Inverse** | ROLLED_OVER_FROM |
| **Allowed Entity Types** | A: Near-month Futures/Options; B: Next-month Futures/Options |
| **Cardinality** | 1→1 |
| **Examples** | NIFTY June Futures **ROLLS_OVER_TO** NIFTY July Futures; Rollover % signals market directional bias |
| **Knowledge Produced** | Rollover data: high rollover with high OI = strong trending conviction; low rollover = uncertainty |
| **Importance** | High |

---

### REL-040 — SUPERSEDES / SUPERSEDED_BY

| Attribute | Value |
|---|---|
| **Name** | SUPERSEDES / SUPERSEDED_BY |
| **Definition** | Entity A replaces entity B as the authoritative, active, or valid version, rendering B obsolete |
| **Direction** | A SUPERSEDES B |
| **Inverse** | SUPERSEDED_BY |
| **Allowed Entity Types** | A: New Circular, Revised Model, Updated Strategy, New Knowledge Item, New SEBI Rule; B: Old Circular, Prior Model, Previous Strategy, Prior Knowledge Item, Old Rule |
| **Cardinality** | 1→1 |
| **Examples** | SEBI Circular 2026-01 **SUPERSEDES** SEBI Circular 2023-07; New model version **SUPERSEDES** previous model |
| **Knowledge Produced** | Tracks version history; ensures decisions are based on current rules |
| **Importance** | High |

---

### REL-041 — SCHEDULED_FOR / SCHEDULES

| Attribute | Value |
|---|---|
| **Name** | SCHEDULED_FOR / SCHEDULES |
| **Definition** | Event A is planned to occur at date/time B |
| **Direction** | A SCHEDULED_FOR B |
| **Inverse** | SCHEDULES |
| **Allowed Entity Types** | A: Earnings Event, Monetary Policy Event, AGM, IPO, Index Rebalancing, Budget; B: Date, Trading Day |
| **Cardinality** | N→1 |
| **Examples** | RBI MPC Meeting Q2 FY27 **SCHEDULED_FOR** October 8, 2026; NIFTY Quarterly Rebalancing **SCHEDULED_FOR** last trading day of March |
| **Knowledge Produced** | Calendar intelligence: pre-event positioning, volatility anticipation, IV expansion in options |
| **Importance** | High |

---

### REL-042 — OVERLAPS_WITH

| Attribute | Value |
|---|---|
| **Name** | OVERLAPS_WITH |
| **Definition** | Entity A's active period and entity B's active period share a common time interval |
| **Direction** | Symmetric |
| **Allowed Entity Types** | A/B: Events, Positions, Market Regimes, Fiscal Years, Contracts |
| **Examples** | India earnings season **OVERLAPS_WITH** global macro uncertainty period; Multiple open positions **OVERLAP_WITH** each other |
| **Knowledge Produced** | Interaction effects: concurrent exposures; regime coexistence analysis |
| **Importance** | Medium |

---

### REL-043 — CYCLES_WITH / SEASONAL_PATTERN

| Attribute | Value |
|---|---|
| **Name** | CYCLES_WITH / SEASONAL_PATTERN |
| **Definition** | A and B recur on the same periodic schedule, or A follows a predictable seasonal pattern relative to calendar entity B |
| **Direction** | A CYCLES_WITH B |
| **Inverse** | Symmetric or SEASONAL_ANCHOR |
| **Allowed Entity Types** | A: Sector Performance, Commodity Price, Corporate Action Pattern; B: Season, Quarter, Agricultural Cycle |
| **Examples** | Agri-commodity prices **CYCLE_WITH** Kharif/Rabi seasons; Dividend announcements **CYCLE_WITH** Q4 results season; Auto sales **CYCLE_WITH** festive season (Oct-Nov) |
| **Knowledge Produced** | Seasonal alpha: predictable timing of sector-specific events |
| **Importance** | High |

---

## CATEGORY 8 — STATISTICAL RELATIONSHIPS

---

### REL-044 — CORRELATES_WITH

| Attribute | Value |
|---|---|
| **Name** | CORRELATES_WITH |
| **Definition** | The observable values of entities A and B exhibit a measurable tendency to co-move, quantified by a correlation coefficient ranging from -1 (perfectly inverse) to +1 (perfectly coincident) |
| **Meaning** | Correlation is a purely statistical relationship — it captures co-movement without implying causation. It is the raw material from which higher-order relationships are inferred. |
| **Direction** | Symmetric (but context makes direction meaningful: which follows which?) |
| **Inverse** | CORRELATES_WITH (symmetric) |
| **Allowed Entity Types** | A/B: Stock, Index, Commodity, Currency, Rate, Macro Variable, Portfolio |
| **Cardinality** | N→N |
| **Strength** | Numeric — coefficient ρ ∈ [-1, +1]; interpreted as: |ρ| > 0.7 = strong; |ρ| 0.4-0.7 = moderate; |ρ| < 0.4 = weak |
| **Lifecycle** | Dynamic — measured over a rolling window; regime-dependent |
| **Temporal Behaviour** | Dynamic. Correlations increase toward 1 in crisis periods (diversification breaks down). |
| **Constraints** | Must specify: lookback period, frequency (daily/weekly), instrument used (price, return, excess return) |
| **Examples** | NIFTY 50 **CORRELATES_WITH** S&P 500 (ρ ≈ 0.65 on daily returns); Gold **CORRELATES_WITH** USD/INR (ρ ≈ -0.55); IT Sector **CORRELATES_WITH** USD/INR (positive — export revenue) |
| **Knowledge Produced** | Portfolio construction: correlation matrix for diversification; pairs trading opportunities; sector rotation signals |
| **Reasoning Value** | Critical for portfolio risk and diversification; High for signal generation |
| **Risk** | Correlation is not causation; correlations break down in tail events; rolling window creates lag |
| **Importance** | Critical |

---

### REL-045 — LEADS / LAGGED_BY

| Attribute | Value |
|---|---|
| **Name** | LEADS (forward) / LAGGED_BY (inverse) |
| **Definition** | Entity A's changes systematically precede changes in entity B by a measurable average time lag, providing predictive information about B |
| **Meaning** | A leading indicator is operationally useful: observing A's current state allows anticipating B's future state |
| **Direction** | A LEADS B (A changes first; B follows) |
| **Inverse** | LAGGED_BY (B LAGGED_BY A) |
| **Allowed Entity Types** | A: Macro Variable, Sector Signal, Credit Spread, Volume; B: Stock Price, Earnings, Economic Activity |
| **Cardinality** | N→N |
| **Temporal Behaviour** | Dynamic — lead time can vary; may switch in different regimes |
| **Examples** | TATASTEEL **LEADS** the metals sector by 2-3 sessions (sector bellwether); PMI Manufacturing **LEADS** GDP by ~2 quarters; Credit spreads **LEAD** equity volatility |
| **Knowledge Produced** | Actionable lead indicator model: "when A does X, expect B to do Y in T+k sessions" |
| **Reasoning Value** | Critical — validated lead relationships are among the highest-value inputs for timing entries |
| **Importance** | Critical |

---

### REL-046 — LAGS / LEADS

| Attribute | Value |
|---|---|
| **Name** | LAGS / LEADS |
| **Definition** | Entity A's changes systematically follow changes in entity B with a measurable delay |
| **Direction** | A LAGS B (A changes after B) |
| **Inverse** | LEADS |
| **Examples** | Consumer inflation **LAGS** wholesale commodity prices; Small cap stocks **LAG** large cap in bull market initiation |
| **Knowledge Produced** | Lagging indicators confirm but don't predict; useful for regime confirmation |
| **Importance** | High |

---

### REL-047 — CO_INTEGRATES_WITH

| Attribute | Value |
|---|---|
| **Name** | CO_INTEGRATES_WITH |
| **Definition** | Entity A and entity B have individual non-stationary time series but share a long-run equilibrium relationship — when they diverge, reversion forces are active |
| **Direction** | Symmetric |
| **Allowed Entity Types** | A/B: Stock pairs (Reliance Industries vs Reliance Retail); Index vs futures; Related commodities |
| **Strength** | Statistical — tested via Engle-Granger or Johansen test |
| **Examples** | NIFTY Spot **CO_INTEGRATES_WITH** NIFTY Futures; Gold India **CO_INTEGRATES_WITH** Gold USD × INR rate; Nifty Bank vs Private Bank Index |
| **Knowledge Produced** | Pairs trading signal; arbitrage opportunity; reversion probability |
| **Importance** | High |

---

### REL-048 — MEAN_REVERTS_TO / ANCHOR_FOR

| Attribute | Value |
|---|---|
| **Name** | MEAN_REVERTS_TO / ANCHOR_FOR |
| **Definition** | Entity A's value tends to return toward entity B's level (or A's own historical mean B) when it deviates significantly |
| **Direction** | A MEAN_REVERTS_TO B |
| **Inverse** | ANCHOR_FOR |
| **Allowed Entity Types** | A: Spread, Ratio, Relative Valuation, Volatility; B: Long-run mean, Fair value, Historical average |
| **Examples** | P/E ratio **MEAN_REVERTS_TO** historical sector average; Intraday price **MEAN_REVERTS_TO** VWAP; VIX **MEAN_REVERTS_TO** long-run average after spikes |
| **Knowledge Produced** | Reversion signal: distance from mean → magnitude of expected reversion |
| **Importance** | High |

---

### REL-049 — BETA_TO / BETA_ANCHOR_FOR

| Attribute | Value |
|---|---|
| **Name** | BETA_TO / BETA_ANCHOR_FOR |
| **Definition** | Entity A's price movements = entity B's movements multiplied by a coefficient β (beta) |
| **Direction** | A BETA_TO B (A is the instrument; B is the market/index) |
| **Inverse** | BETA_ANCHOR_FOR |
| **Cardinality** | N→1 (many instruments have beta to one index) |
| **Examples** | TATAMOTORS **BETA_TO** NIFTY 50 (β ≈ 1.4); HDFC Bank **BETA_TO** NIFTY 50 (β ≈ 1.1); FMCG sector **BETA_TO** NIFTY 50 (β ≈ 0.6) |
| **Knowledge Produced** | Systematic risk measurement; hedging ratio calculation; portfolio beta management |
| **Importance** | Critical |

---

### REL-050 — GRANGER_CAUSES / GRANGER_CAUSED_BY

| Attribute | Value |
|---|---|
| **Name** | GRANGER_CAUSES / GRANGER_CAUSED_BY |
| **Definition** | Entity A Granger-causes B if past values of A contain statistically significant information for predicting B's future values, above and beyond B's own past values |
| **Direction** | A GRANGER_CAUSES B |
| **Inverse** | GRANGER_CAUSED_BY |
| **Strength** | Statistical — F-test significance; not true causation but predictive precedence |
| **Examples** | FII flows **GRANGER_CAUSE** large-cap index returns; PMI data **GRANGER_CAUSES** industrial production |
| **Knowledge Produced** | Predictive lead indicator identification; VAR model input |
| **Importance** | High |

---

### REL-051 — DEVIATES_FROM / DEVIATION_ANCHOR

| Attribute | Value |
|---|---|
| **Name** | DEVIATES_FROM / DEVIATION_ANCHOR |
| **Definition** | Entity A's current value has a measurable distance from benchmark/reference B |
| **Direction** | A DEVIATES_FROM B |
| **Examples** | Stock price **DEVIATES_FROM** 200-day moving average by 15%; P/E **DEVIATES_FROM** 5-year sector average by 2 standard deviations |
| **Knowledge Produced** | Reversion opportunity identification; overbought/oversold signals |
| **Importance** | High |

---

## CATEGORY 9 — KNOWLEDGE CREATION RELATIONSHIPS

---

### REL-052 — DERIVED_FROM / SOURCE_OF

| Attribute | Value |
|---|---|
| **Name** | DERIVED_FROM (forward) / SOURCE_OF (inverse) |
| **Definition** | The value, content, or validity of entity A is computed or inferred from entity B through a defined derivation process |
| **Meaning** | Derivation creates a dependency: if B's value changes, A must be recomputed. A is "downstream" of B. |
| **Direction** | A DERIVED_FROM B (A is the result; B is the source) |
| **Inverse** | SOURCE_OF |
| **Allowed Entity Types** | A: Indicator, Score, Prediction, Signal, Conviction, Knowledge Item, Derived Price; B: Price/Volume Data, Financial Statement, Macro Data, Other Indicators |
| **Cardinality** | N→N (one indicator can derive from many inputs; one input can produce many derivatives) |
| **Strength** | Mathematical — derivation is a precise function |
| **Lifecycle** | Active as long as source B is valid; A is stale when B changes and A hasn't been recomputed |
| **Examples** | RSI **DERIVED_FROM** price history (14-period); Beta **DERIVED_FROM** return history vs index; EBITDA margin **DERIVED_FROM** P&L statement; Conviction score **DERIVED_FROM** weighted evidence items |
| **Knowledge Produced** | Traceability: every derived value can be audited back to its source data |
| **Reasoning Value** | Critical — derivation chains must be intact for system to be trusted |
| **Risk** | Garbage-in-garbage-out: corrupted source → invalid derived value; stale source → stale derivative |
| **Importance** | Critical |

---

### REL-053 — CALCULATED_FROM / CALCULATION_INPUT_FOR

| Attribute | Value |
|---|---|
| **Name** | CALCULATED_FROM / CALCULATION_INPUT_FOR |
| **Definition** | A is the result of a specific mathematical formula applied to inputs B (a more precise form of DERIVED_FROM, implying a defined formula) |
| **Direction** | A CALCULATED_FROM B |
| **Examples** | P/E ratio **CALCULATED_FROM** Price ÷ EPS; ATR **CALCULATED_FROM** 14-day range history; Free Cash Flow **CALCULATED_FROM** CFO - Capex |
| **Knowledge Produced** | Reproducibility: given the same inputs and formula, any system produces the same result |
| **Importance** | Critical |

---

### REL-054 — BASED_ON / FOUNDATION_OF

| Attribute | Value |
|---|---|
| **Name** | BASED_ON / FOUNDATION_OF |
| **Definition** | Entity A's validity or quality depends on entity B's truth — A is built on B's assumptions |
| **Direction** | A BASED_ON B |
| **Inverse** | FOUNDATION_OF |
| **Examples** | Hypothesis BASED_ON observation record B; Prediction BASED_ON model trained on data B; Conviction BASED_ON assembled evidence items |
| **Knowledge Produced** | Dependency auditing: if B is false or stale, A's validity is compromised |
| **Importance** | High |

---

### REL-055 — EXPLAINS / EXPLAINED_BY

| Attribute | Value |
|---|---|
| **Name** | EXPLAINS / EXPLAINED_BY |
| **Definition** | Entity A provides the causal or logical account of why entity B has the state or behavior it exhibits |
| **Direction** | A EXPLAINS B |
| **Inverse** | EXPLAINED_BY |
| **Allowed Entity Types** | A: Macro Variable, Event, Knowledge Item, Reasoning Chain; B: Stock Price Movement, Earnings Surprise, Market Regime Change |
| **Examples** | Fed rate hike **EXPLAINS** fall in bond prices; Earnings beat **EXPLAINS** post-results gap-up; Management guidance downgrade **EXPLAINS** selling pressure |
| **Knowledge Produced** | Attribution: understanding why B behaved as it did improves prediction of future behavior |
| **Reasoning Value** | Critical — separates "explained" from "unexplained" price moves; unexplained moves deserve further investigation |
| **Importance** | Critical |

---

### REL-056 — DOCUMENTS / DOCUMENTED_BY

| Attribute | Value |
|---|---|
| **Name** | DOCUMENTS / DOCUMENTED_BY |
| **Definition** | Entity A creates a formal, structured record of entity B's state, actions, or existence |
| **Direction** | A DOCUMENTS B |
| **Inverse** | DOCUMENTED_BY |
| **Allowed Entity Types** | A: Annual Report, Financial Statement, Audit Trail, Regulatory Filing; B: Company, Portfolio, Decision, Trade |
| **Examples** | Annual Report **DOCUMENTS** company's FY26 performance; Audit Trail **DOCUMENTS** every system action |
| **Knowledge Produced** | Verifiable record; legal standing; accountability |
| **Importance** | High |

---

### REL-057 — MODELS / MODELED_BY

| Attribute | Value |
|---|---|
| **Name** | MODELS / MODELED_BY |
| **Definition** | Entity A is a mathematical or logical construct that approximates and predicts how entity B behaves |
| **Direction** | A MODELS B |
| **Inverse** | MODELED_BY |
| **Allowed Entity Types** | A: Pricing Model, Risk Model, Regime Model, Earnings Model; B: Options Premium, Portfolio Risk, Market State, Company Earnings |
| **Examples** | Black-Scholes variant **MODELS** options premium; Regime classification model **MODELS** market state; Earnings model **MODELS** company quarterly EPS |
| **Knowledge Produced** | Model accuracy tracking; model-based predictions; out-of-sample validation results |
| **Importance** | Critical |

---

### REL-058 — VALIDATES / VALIDATED_BY

| Attribute | Value |
|---|---|
| **Name** | VALIDATES / VALIDATED_BY |
| **Definition** | Entity A confirms entity B's accuracy through an independent verification process |
| **Direction** | A VALIDATES B |
| **Inverse** | VALIDATED_BY |
| **Examples** | Auditor **VALIDATES** financial statements; Out-of-sample test **VALIDATES** backtested strategy; Walk-forward test **VALIDATES** model parameters |
| **Knowledge Produced** | Confidence in B; known failure modes of B |
| **Importance** | Critical |

---

## CATEGORY 10 — REASONING RELATIONSHIPS

---

### REL-059 — SUPPORTS / SUPPORTED_BY

| Attribute | Value |
|---|---|
| **Name** | SUPPORTS (forward) / SUPPORTED_BY (inverse) |
| **Definition** | Evidence item A increases the probability that hypothesis B is true — A is directionally aligned with B's prediction |
| **Meaning** | Support is the primary relationship in evidence-based reasoning. It is weighted: different pieces of evidence carry different support strengths depending on their independence, reliability, and directional alignment. |
| **Direction** | A SUPPORTS B (A is evidence; B is hypothesis) |
| **Inverse** | SUPPORTED_BY |
| **Allowed Entity Types** | A: Evidence Item, Signal, Observation, Knowledge Item; B: Hypothesis, Decision, Conviction |
| **Cardinality** | N→1 (many evidence items support one hypothesis) |
| **Strength** | Variable (0 to 1 support weight per evidence item) |
| **Lifecycle** | Active while evidence is current; expires when evidence is superseded or becomes stale |
| **Temporal Behaviour** | Dynamic — support weight degrades with evidence age |
| **Constraints** | Evidence must be independent for supports weights to be additive; correlated evidence items inflate apparent conviction |
| **Examples** | Increasing FII buying SUPPORTS bullish hypothesis on NIFTY; Strong earnings beat SUPPORTS bullish hypothesis on HDFC Bank; RSI divergence SUPPORTS bullish reversal hypothesis |
| **Knowledge Produced** | Conviction building: cumulative support across independent evidence items produces conviction score |
| **Reasoning Value** | Critical — this is the primary relationship in the evidence assembly process |
| **Risk** | Evidence correlation: if all "supporting" evidence is correlated (e.g., all derived from the same macro signal), the apparent support is illusory |
| **Importance** | Critical |

---

### REL-060 — CONTRADICTS / CONTRADICTED_BY

| Attribute | Value |
|---|---|
| **Name** | CONTRADICTS (forward) / CONTRADICTED_BY (inverse) |
| **Definition** | Evidence item A is inconsistent with hypothesis B — A's truth reduces the probability that B is correct |
| **Meaning** | Contradicting evidence is as important as supporting evidence. A robust hypothesis must acknowledge and explain its contradictions. |
| **Direction** | A CONTRADICTS B |
| **Inverse** | CONTRADICTED_BY |
| **Allowed Entity Types** | A: Evidence Item, Signal, Observation; B: Hypothesis, Conviction |
| **Strength** | Variable (0 to 1 contradiction weight) |
| **Examples** | Deteriorating promoter holding CONTRADICTS bullish thesis on management confidence; Rising debt/equity CONTRADICTS growth investment thesis |
| **Knowledge Produced** | Risk awareness: key risks to the investment thesis; conditions that would cause thesis invalidation |
| **Reasoning Value** | Critical — ignoring contradicting evidence is a primary source of investment error |
| **Importance** | Critical |

---

### REL-061 — CONFIRMS / CONFIRMED_BY

| Attribute | Value |
|---|---|
| **Name** | CONFIRMS / CONFIRMED_BY |
| **Definition** | Evidence A is strong, direct validation of hypothesis B — moving conviction above the decision threshold |
| **Direction** | A CONFIRMS B |
| **Inverse** | CONFIRMED_BY |
| **Strength** | High — confirmation requires strong, direct evidence |
| **Examples** | Actual earnings beat of 15%+ CONFIRMS earnings acceleration hypothesis; Central bank policy pivot CONFIRMS rate cycle hypothesis |
| **Importance** | Critical |

---

### REL-062 — INVALIDATES / INVALIDATED_BY

| Attribute | Value |
|---|---|
| **Name** | INVALIDATES / INVALIDATED_BY |
| **Definition** | Evidence or event A demonstrates that hypothesis B is false or no longer applicable, requiring its retirement |
| **Direction** | A INVALIDATES B |
| **Inverse** | INVALIDATED_BY |
| **Examples** | Management guidance cut INVALIDATES earnings growth hypothesis; Regime change from trending to ranging INVALIDATES momentum strategy hypothesis |
| **Knowledge Produced** | Forced hypothesis retirement; learning from why the thesis was wrong |
| **Importance** | Critical |

---

### REL-063 — STRENGTHENS / STRENGTHENED_BY

| Attribute | Value |
|---|---|
| **Name** | STRENGTHENS / STRENGTHENED_BY |
| **Definition** | New evidence A increases the conviction weight behind hypothesis/knowledge item B, without yet reaching confirmation |
| **Direction** | A STRENGTHENS B |
| **Examples** | Additional technical signal STRENGTHENS existing fundamental thesis; Second independent evidence source STRENGTHENS conviction |
| **Importance** | High |

---

### REL-064 — WEAKENS / WEAKENED_BY

| Attribute | Value |
|---|---|
| **Name** | WEAKENS / WEAKENED_BY |
| **Definition** | New information A reduces confidence in hypothesis/knowledge item B, without fully invalidating it |
| **Direction** | A WEAKENS B |
| **Examples** | Sector headwind evidence WEAKENS individual company bullish hypothesis |
| **Importance** | High |

---

### REL-065 — CONTEXTUALIZES / CONTEXTUALIZED_BY

| Attribute | Value |
|---|---|
| **Name** | CONTEXTUALIZES / CONTEXTUALIZED_BY |
| **Definition** | Entity A provides the framing or background that changes the interpretation or significance of entity B |
| **Direction** | A CONTEXTUALIZES B |
| **Meaning** | The same evidence B means different things in different contexts A. A 10% revenue growth is excellent in a contracting economy but disappointing in a booming sector. |
| **Examples** | Market Regime (trending) CONTEXTUALIZES momentum signal (more reliable); Economic downturn CONTEXTUALIZES individual company results |
| **Importance** | Critical |

---

### REL-066 — CORROBORATES / CORROBORATED_BY

| Attribute | Value |
|---|---|
| **Name** | CORROBORATES / CORROBORATED_BY |
| **Definition** | Independent evidence A is consistent with hypothesis B, adding weight without directly confirming |
| **Direction** | A CORROBORATES B |
| **Note:** Corroboration differs from confirmation in independence: corroborating evidence arrives from a different source, adding genuine weight |
| **Examples** | Option chain structure (high Put OI at support) CORROBORATES technical support hypothesis based on price chart analysis |
| **Importance** | High |

---

### REL-067 — SYNTHESIZES_INTO / SYNTHESIZED_FROM

| Attribute | Value |
|---|---|
| **Name** | SYNTHESIZES_INTO / SYNTHESIZED_FROM |
| **Definition** | Multiple independent evidence items A collectively produce a unified conclusion B through structured aggregation |
| **Direction** | Multiple As SYNTHESIZE_INTO B (N-to-1) |
| **Inverse** | SYNTHESIZED_FROM |
| **Allowed Entity Types** | A: Evidence Items; B: Conviction, Knowledge Item, Decision |
| **Cardinality** | N→1 |
| **Examples** | [Technical signal + Fundamental signal + Macro alignment + Sector momentum] SYNTHESIZE_INTO conviction score of 7.2 |
| **Importance** | Critical |

---

## CATEGORY 11 — DECISION RELATIONSHIPS

---

### REL-068 — TARGETS / TARGETED_BY

| Attribute | Value |
|---|---|
| **Name** | TARGETS / TARGETED_BY |
| **Definition** | Decision A is directed toward achieving a specific outcome B — B is the intended result of A's execution |
| **Direction** | A TARGETS B |
| **Inverse** | TARGETED_BY |
| **Allowed Entity Types** | A: Decision, Strategy, Portfolio; B: Price Level, Return Target, Risk Reduction, Sector Exposure |
| **Examples** | Decision TARGETS 15% profit (target = ₹1,450 on RELIANCE); Strategy TARGETS NIFTY+5% annual alpha |
| **Importance** | Critical |

---

### REL-069 — CONSTRAINS / CONSTRAINED_BY

| Attribute | Value |
|---|---|
| **Name** | CONSTRAINS / CONSTRAINED_BY |
| **Definition** | Entity A limits the space of valid choices for entity B, preventing B from exceeding defined boundaries |
| **Direction** | A CONSTRAINS B |
| **Inverse** | CONSTRAINED_BY |
| **Allowed Entity Types** | A: Constraint, Regulation, Risk Limit, Portfolio Rule; B: Decision, Position Size, Trade, Portfolio |
| **Examples** | "Max 5% NAV per position" CONSTRAINS every Decision; VaR limit CONSTRAINS portfolio construction; SEBI circuit limit CONSTRAINS intraday price movement |
| **Importance** | Critical |

---

### REL-070 — APPROVES / APPROVED_BY

| Attribute | Value |
|---|---|
| **Name** | APPROVES / APPROVED_BY |
| **Definition** | Entity A formally grants permission for entity B to proceed |
| **Direction** | A APPROVES B |
| **Inverse** | APPROVED_BY |
| **Allowed Entity Types** | A: Risk System, Kill Switch Check, Conviction Threshold, Human Override; B: Decision, Order, Trade, New Strategy |
| **Examples** | Risk Guardian APPROVES decision (no kill switch condition met); SEBI APPROVES IPO prospectus |
| **Importance** | Critical |

---

### REL-071 — OVERRIDES / OVERRIDDEN_BY

| Attribute | Value |
|---|---|
| **Name** | OVERRIDES / OVERRIDDEN_BY |
| **Definition** | Authority A supersedes the decision, rule, or recommendation of B — typically at a higher level of the decision hierarchy |
| **Direction** | A OVERRIDES B |
| **Examples** | Kill Switch OVERRIDES all buy decisions when VIX > 45; Human Operator OVERRIDES automated sell recommendation |
| **Importance** | Critical |

---

### REL-072 — SIZES / SIZED_BY (Position)

| Attribute | Value |
|---|---|
| **Name** | SIZES / SIZED_BY |
| **Definition** | Entity A determines the quantity of capital to allocate to position B, based on a defined sizing methodology |
| **Direction** | A SIZES B |
| **Allowed Entity Types** | A: Position Sizing Rule, Kelly Formula, ATR-based sizer; B: Position, Order |
| **Examples** | Conviction-scaled sizing rule SIZES TATAMOTORS long position at 2.5% NAV (high conviction = larger size) |
| **Importance** | Critical |

---

### REL-073 — PRIORITIZES / PRIORITIZED_BY

| Attribute | Value |
|---|---|
| **Name** | PRIORITIZES / PRIORITIZED_BY |
| **Definition** | A determines that B should be acted on before alternative entities, given limited capital or attention |
| **Direction** | A PRIORITIZES B over C |
| **Examples** | Higher conviction PRIORITIZES trade entry; Capital constraint PRIORITIZES high-conviction over medium-conviction opportunities |
| **Importance** | High |

---

### REL-074 — RECOMMENDS / RECOMMENDED_BY

| Attribute | Value |
|---|---|
| **Name** | RECOMMENDS / RECOMMENDED_BY |
| **Definition** | Intelligence layer A produces a directional suggestion B as the preferred action, without yet committing as a decision |
| **Direction** | A RECOMMENDS B |
| **Examples** | Intelligence system RECOMMENDS buying NIFTY if conviction exceeds 6.0; Analyst RECOMMENDS reducing position on thesis weakening |
| **Importance** | High |

---

## CATEGORY 12 — RISK RELATIONSHIPS

---

### REL-075 — EXPOSES_TO / EXPOSURE_FROM

| Attribute | Value |
|---|---|
| **Name** | EXPOSES_TO (forward) / EXPOSURE_FROM (inverse) |
| **Definition** | Holding or participating in entity A creates a measurable financial risk in entity B — B's adverse state can cause loss in A |
| **Meaning** | Exposure is directional risk: by holding A, the investor is exposed to risks in B. This is the fundamental risk relationship. |
| **Direction** | A EXPOSES_TO B (A is the instrument/position; B is the risk source) |
| **Inverse** | EXPOSURE_FROM |
| **Allowed Entity Types** | A: Position, Portfolio; B: Market Risk, Credit Risk, Liquidity Risk, Currency Risk, Sector Risk |
| **Cardinality** | N→N |
| **Strength** | Quantified — in ₹ and % of NAV |
| **Temporal Behaviour** | Changes with position size and market prices |
| **Examples** | TATAMOTORS long position EXPOSES_TO auto sector slowdown risk; INR-denominated portfolio EXPOSES_TO USD/INR depreciation risk; IT sector overweight EXPOSES_TO USD weakening risk |
| **Knowledge Produced** | Exposure map; gross and net exposure by risk factor |
| **Reasoning Value** | Critical — every position sizing decision references exposure |
| **Importance** | Critical |

---

### REL-076 — MITIGATES / MITIGATED_BY

| Attribute | Value |
|---|---|
| **Name** | MITIGATES / MITIGATED_BY |
| **Definition** | Entity A reduces the probability of occurrence or severity of impact of risk entity B |
| **Direction** | A MITIGATES B |
| **Inverse** | MITIGATED_BY |
| **Allowed Entity Types** | A: Hedge Position, Diversification, Stop Loss, Constraint, Insurance; B: Market Risk, Credit Risk, Tail Risk |
| **Examples** | Portfolio diversification MITIGATES idiosyncratic risk; Stop loss MITIGATES single-position loss; Circuit breaker MITIGATES extreme intraday loss |
| **Knowledge Produced** | Risk reduction quantification; residual risk after mitigation |
| **Importance** | Critical |

---

### REL-077 — AMPLIFIES_RISK_IN / RISK_AMPLIFIED_BY

| Attribute | Value |
|---|---|
| **Name** | AMPLIFIES_RISK_IN / RISK_AMPLIFIED_BY |
| **Definition** | Entity A increases the total risk level in B beyond what would exist without A |
| **Direction** | A AMPLIFIES_RISK_IN B |
| **Examples** | Leverage AMPLIFIES_RISK_IN portfolio (same price move → larger loss); Concentration in one sector AMPLIFIES_RISK_IN portfolio |
| **Importance** | Critical |

---

### REL-078 — CONCENTRATES / CONCENTRATION_SOURCE

| Attribute | Value |
|---|---|
| **Name** | CONCENTRATES / CONCENTRATION_SOURCE |
| **Definition** | Entity A creates above-average concentration of risk in entity B (portfolio/position) by allocating disproportionate capital to a narrow set of exposures |
| **Direction** | A CONCENTRATES B |
| **Examples** | Overweighting a single sector CONCENTRATES portfolio risk; Single large position CONCENTRATES idiosyncratic risk |
| **Importance** | High |

---

### REL-079 — DIVERSIFIES / DIVERSIFIED_BY

| Attribute | Value |
|---|---|
| **Name** | DIVERSIFIES / DIVERSIFIED_BY |
| **Definition** | Entity A reduces idiosyncratic or concentration risk in B by adding non-correlated or low-correlated exposure |
| **Direction** | A DIVERSIFIES B |
| **Examples** | Adding gold to equity portfolio DIVERSIFIES risk; International exposure DIVERSIFIES domestic macro risk |
| **Importance** | High |

---

### REL-080 — STRESS_TESTS / STRESS_TESTED_BY

| Attribute | Value |
|---|---|
| **Name** | STRESS_TESTS / STRESS_TESTED_BY |
| **Definition** | Entity A applies an extreme hypothetical scenario to entity B to assess B's resilience |
| **Direction** | A STRESS_TESTS B |
| **Examples** | Stress Test Scenario "2008 crisis" STRESS_TESTS current portfolio; Walk-forward test STRESS_TESTS strategy parameters |
| **Importance** | High |

---

### REL-081 — DEFAULTS_ON / DEFAULTED_ON_BY

| Attribute | Value |
|---|---|
| **Name** | DEFAULTS_ON / DEFAULTED_ON_BY |
| **Definition** | Entity A fails to fulfill its contractual financial obligations to entity B |
| **Direction** | A DEFAULTS_ON B |
| **Examples** | Company A DEFAULTS_ON its bond obligations; Counterparty DEFAULTS_ON F&O settlement |
| **Knowledge Produced** | Credit event: triggers credit default swap; cascades through bondholder portfolios |
| **Importance** | Critical (tail event) |

---

## CATEGORY 13 — LEARNING AND PREDICTIVE RELATIONSHIPS

---

### REL-082 — LEARNS_FROM / TEACHES

| Attribute | Value |
|---|---|
| **Name** | LEARNS_FROM (forward) / TEACHES (inverse) |
| **Definition** | The system (model, knowledge base, strategy) A updates its parameters, beliefs, or rules based on new data or outcomes from entity B |
| **Meaning** | Learning is the core self-improvement mechanism. Without it, the system cannot adapt to market regime changes. |
| **Direction** | A LEARNS_FROM B (A is the learner; B is the source of learning) |
| **Inverse** | TEACHES |
| **Allowed Entity Types** | A: Model, Strategy, Knowledge Item, Evidence Weights; B: Outcome Record, Learning Record, Historical Data, Market Event |
| **Cardinality** | N→N |
| **Lifecycle** | Continuous — every new outcome is a learning opportunity |
| **Examples** | Regime model LEARNS_FROM recent market behavior; Strategy LEARNS_FROM backtested outcome; Evidence weight LEARNS_FROM historical reliability of signal type |
| **Knowledge Produced** | Updated model parameters; revised evidence weights; new knowledge items; improved strategy conditions |
| **Reasoning Value** | Critical — the ability to learn differentiates an intelligent system from a static ruleset |
| **Risk** | Overfitting: learning too specifically from recent history; regime shift: learning from a regime that no longer applies |
| **Importance** | Critical |

---

### REL-083 — TRAINS_ON / TRAINING_DATA_FOR

| Attribute | Value |
|---|---|
| **Name** | TRAINS_ON / TRAINING_DATA_FOR |
| **Definition** | Model A is fitted or calibrated using historical dataset B |
| **Direction** | A TRAINS_ON B |
| **Examples** | Regime classification model TRAINS_ON 5 years of market data; Earnings predictor TRAINS_ON 40 quarters of results |
| **Knowledge Produced** | Model parameters; in-sample performance; known biases from training period |
| **Importance** | Critical |

---

### REL-084 — VALIDATES_AGAINST / VALIDATES

| Attribute | Value |
|---|---|
| **Name** | VALIDATES_AGAINST / VALIDATES |
| **Definition** | Model or strategy A is tested against holdout dataset B that was not used in training, assessing genuine out-of-sample performance |
| **Direction** | A VALIDATES_AGAINST B |
| **Examples** | Strategy VALIDATES_AGAINST out-of-sample period Q1-Q4 2025; Model VALIDATES_AGAINST walk-forward test |
| **Importance** | Critical |

---

### REL-085 — UPDATES_FROM / UPDATE_SOURCE

| Attribute | Value |
|---|---|
| **Name** | UPDATES_FROM / UPDATE_SOURCE |
| **Definition** | Entity A's current state is revised based on new information from entity B, without full retraining |
| **Direction** | A UPDATES_FROM B |
| **Examples** | Evidence weight for "FII buying" signal UPDATES_FROM tracking recent accuracy; Knowledge item UPDATES_FROM new corroborating observations |
| **Importance** | Critical |

---

### REL-086 — BACKTESTS_AGAINST / BACKTEST_DATASET

| Attribute | Value |
|---|---|
| **Name** | BACKTESTS_AGAINST / BACKTEST_DATASET |
| **Definition** | Strategy A is run over historical data B to assess what its performance would have been in the past |
| **Direction** | A BACKTESTS_AGAINST B |
| **Constraints** | Backtest period should not overlap validation period; survivor bias must be documented |
| **Examples** | Momentum strategy BACKTESTS_AGAINST 2010-2020 NSE data |
| **Importance** | High |

---

### REL-087 — PREDICTS / PREDICTED_BY

| Attribute | Value |
|---|---|
| **Name** | PREDICTS (forward) / PREDICTED_BY (inverse) |
| **Definition** | Entity A produces a probabilistic, time-bound forecast of entity B's future state or value |
| **Meaning** | Prediction is the purpose of all analysis. The quality of predictions is measured by comparing them to eventual outcomes. |
| **Direction** | A PREDICTS B (A is predictor; B is the predicted entity/state) |
| **Inverse** | PREDICTED_BY |
| **Allowed Entity Types** | A: Model, Analyst, Strategy, Conviction; B: Price, Earnings, Rate, Regime, Outcome |
| **Cardinality** | N→1 (many predictors can predict the same entity) |
| **Temporal Behaviour** | Time-bounded — prediction expires at horizon |
| **Constraints** | Must specify: probability, time horizon, confidence interval, model used |
| **Examples** | Earnings model PREDICTS HDFC Bank Q3 EPS at ₹20.5 ± ₹0.8; Regime model PREDICTS trending regime continues for 15 ± 5 more sessions |
| **Knowledge Produced** | Prediction vs outcome comparison → model calibration |
| **Reasoning Value** | Critical — the entire system exists to make better predictions |
| **Importance** | Critical |

---

### REL-088 — RETROACTIVELY_CONFIRMS / RETROACTIVELY_CONFIRMED_BY

| Attribute | Value |
|---|---|
| **Name** | RETROACTIVELY_CONFIRMS / RETROACTIVELY_CONFIRMED_BY |
| **Definition** | Actual outcome A validates that prediction B was accurate — providing positive learning signal |
| **Direction** | Outcome A RETROACTIVELY_CONFIRMS Prediction B |
| **Examples** | Actual earnings beat of 15% RETROACTIVELY_CONFIRMS "earnings acceleration" prediction |
| **Knowledge Produced** | Prediction accuracy score; model calibration; evidence weight update |
| **Importance** | Critical |

---

### REL-089 — DISCONFIRMS / DISCONFIRMED_BY

| Attribute | Value |
|---|---|
| **Name** | DISCONFIRMS / DISCONFIRMED_BY |
| **Definition** | Actual outcome A shows that prediction B was wrong — providing negative learning signal |
| **Direction** | Outcome A DISCONFIRMS Prediction B |
| **Examples** | Actual earnings miss DISCONFIRMS "strong growth" prediction; regime staying ranging DISCONFIRMS "breakout imminent" prediction |
| **Knowledge Produced** | What assumptions were wrong; model recalibration signal |
| **Importance** | Critical |

---

## CATEGORY 14 — INFORMATION AND MONITORING RELATIONSHIPS

---

### REL-090 — MEASURES / MEASURED_BY

| Attribute | Value |
|---|---|
| **Name** | MEASURES / MEASURED_BY |
| **Definition** | Entity A produces a quantitative value that characterizes a specific attribute of entity B |
| **Meaning** | Measurement is the process of extracting a number from an entity's state. It creates the observation records that feed all higher reasoning. |
| **Direction** | A MEASURES B (A is the measurement instrument/process; B is the entity measured) |
| **Inverse** | MEASURED_BY |
| **Allowed Entity Types** | A: Indicator, Model, Data Feed, Rating Process; B: Volatility, Beta, P/E, Market Breadth, Liquidity |
| **Cardinality** | N→N |
| **Examples** | RSI MEASURES momentum of Reliance stock; ATR MEASURES volatility of NIFTY; P/E ratio MEASURES relative valuation |
| **Knowledge Produced** | Quantified entity state; time series of measurements enables trend analysis |
| **Importance** | Critical |

---

### REL-091 — MONITORS / MONITORED_BY

| Attribute | Value |
|---|---|
| **Name** | MONITORS / MONITORED_BY |
| **Definition** | Entity A continuously tracks entity B's state over time, creating a time series of observations and triggering alerts when thresholds are crossed |
| **Direction** | A MONITORS B |
| **Inverse** | MONITORED_BY |
| **Allowed Entity Types** | A: System Monitor, Portfolio Manager, Alert System, Regulator; B: Position, Market, Company, Risk Level |
| **Examples** | TradeMonitor MONITORS all open positions; Market Monitor MONITORS NIFTY breadth every 30 seconds; LTP Guard MONITORS live prices vs theoretical |
| **Importance** | Critical |

---

### REL-092 — REPORTS_ON / REPORTED_BY

| Attribute | Value |
|---|---|
| **Name** | REPORTS_ON / REPORTED_BY |
| **Definition** | Entity A produces periodic structured disclosures about entity B's state, actions, or performance |
| **Direction** | A REPORTS_ON B |
| **Examples** | Company REPORTS_ON its own quarterly financial results; Portfolio system REPORTS_ON trade journal to operator; Dashboard REPORTS_ON cycle health |
| **Importance** | High |

---

### REL-093 — DISCLOSES / DISCLOSED_BY

| Attribute | Value |
|---|---|
| **Name** | DISCLOSES / DISCLOSED_BY |
| **Definition** | Entity A publicly reveals material information about entity B, making it available to all market participants simultaneously |
| **Direction** | A DISCLOSES B |
| **Constraint** | For listed companies, selective disclosure to some participants before others is illegal (SEBI insider trading regulations) |
| **Examples** | Company DISCLOSES quarterly earnings on exchange platform; Board meeting outcome DISCLOSED on BSE/NSE immediately after meeting |
| **Importance** | Critical (market fairness) |

---

### REL-094 — ALERTS_ON / ALERT_SOURCE

| Attribute | Value |
|---|---|
| **Name** | ALERTS_ON / ALERT_SOURCE |
| **Definition** | Monitoring system A triggers a notification when entity B's state crosses a defined threshold |
| **Direction** | A ALERTS_ON B |
| **Examples** | Position monitoring ALERTS_ON stop loss breach; Breadth monitor ALERTS_ON advance-decline ratio below 0.5; Market regime engine ALERTS_ON regime transition |
| **Importance** | Critical |

---

### REL-095 — TRACKS / TRACKED_BY

| Attribute | Value |
|---|---|
| **Name** | TRACKS / TRACKED_BY |
| **Definition** | Entity A follows the evolution of entity B's state over time, maintaining a history of observations |
| **Direction** | A TRACKS B |
| **Examples** | Watchlist TRACKS 25 shortlisted stocks; Learning System TRACKS strategy win rates; Fund Flow Dashboard TRACKS daily FII/DII activity |
| **Importance** | High |

---

## CATEGORY 15 — MARKET INTELLIGENCE RELATIONSHIPS

---

### REL-096 — RANKS / RANKED_BY

| Attribute | Value |
|---|---|
| **Name** | RANKS / RANKED_BY |
| **Definition** | Intelligence process A orders entities by their relative score or value, establishing a hierarchy of preference or priority |
| **Direction** | A RANKS B (process to entity) |
| **Examples** | Composite scoring engine RANKS 500 stocks from most to least attractive; Strategy RANKS sectors by momentum score |
| **Knowledge Produced** | Actionable priority list; top-decile selection for opportunity identification |
| **Importance** | High |

---

### REL-097 — SCORES / SCORED_BY

| Attribute | Value |
|---|---|
| **Name** | SCORES / SCORED_BY |
| **Definition** | Intelligence process A assigns a numerical rating to entity B on a defined scale |
| **Direction** | A SCORES B |
| **Examples** | Conviction Engine SCORES hypothesis at 7.2/10; Governance scoring SCORES management quality; Technical scoring SCORES price structure strength |
| **Importance** | Critical |

---

### REL-098 — CLASSIFIES / CLASSIFIED_BY

| Attribute | Value |
|---|---|
| **Name** | CLASSIFIES / CLASSIFIED_BY |
| **Definition** | Intelligence process A assigns entity B to a defined category in a taxonomy |
| **Direction** | A CLASSIFIES B |
| **Examples** | Regime engine CLASSIFIES market as "trending"; Sector classification CLASSIFIES HDFC Bank as "Private Banks" |
| **Importance** | High |

---

### REL-099 — SCREENS_FOR / SCREENED_BY

| Attribute | Value |
|---|---|
| **Name** | SCREENS_FOR / SCREENED_BY |
| **Definition** | Filter process A searches the universe for instruments meeting criteria B |
| **Direction** | A SCREENS_FOR B (criteria) within universe |
| **Examples** | Scanner SCREENS_FOR stocks with ADTV > ₹50 crore and RSI < 30; Screen SCREENS_FOR companies with ROE > 15% and PEG < 1.5 |
| **Importance** | High |

---

### REL-100 — ATTRIBUTES_TO / ATTRIBUTION_SOURCE

| Attribute | Value |
|---|---|
| **Name** | ATTRIBUTES_TO / ATTRIBUTION_SOURCE |
| **Definition** | Performance analysis A identifies entity B as responsible for a portion of the overall return or risk |
| **Direction** | A ATTRIBUTES_TO B (performance record attributes returns to individual strategies/sectors) |
| **Examples** | Portfolio attribution ATTRIBUTES 40% of monthly return TO momentum strategy; Loss analysis ATTRIBUTES 60% of drawdown TO banking sector overweight |
| **Knowledge Produced** | Strategy contribution; sector contribution; factor exposure analysis |
| **Importance** | High |

---

## CATEGORY 16 — GOVERNANCE AND AUDIT RELATIONSHIPS

---

### REL-101 — AUDITS / AUDITED_BY

| Attribute | Value |
|---|---|
| **Name** | AUDITS / AUDITED_BY |
| **Definition** | Independent entity A examines entity B's records, processes, or states to certify their accuracy and compliance |
| **Direction** | A AUDITS B |
| **Examples** | Statutory Auditor AUDITS financial statements; SEBI AUDITS broker compliance; Internal audit AUDITS trade records |
| **Importance** | Critical |

---

### REL-102 — ENFORCES / ENFORCED_BY

| Attribute | Value |
|---|---|
| **Name** | ENFORCES / ENFORCED_BY |
| **Definition** | Entity A compels compliance with rule/regulation B, using authority and sanction power |
| **Direction** | A ENFORCES B |
| **Examples** | SEBI ENFORCES disclosure norms; Kill Switch ENFORCES daily loss limit; Risk Guardian ENFORCES VIX kill-switch rule |
| **Importance** | Critical |

---

### REL-103 — MANDATES / MANDATED_BY

| Attribute | Value |
|---|---|
| **Name** | MANDATES / MANDATED_BY |
| **Definition** | Regulatory/governance entity A legally requires entity/activity B |
| **Direction** | A MANDATES B |
| **Examples** | SEBI MANDATES quarterly shareholding disclosure; RBI MANDATES minimum reserve ratios; System MANDATES audit trail for every trade |
| **Importance** | High |

---

### REL-104 — PROHIBITS / PROHIBITED_BY

| Attribute | Value |
|---|---|
| **Name** | PROHIBITS / PROHIBITED_BY |
| **Definition** | Authority A forbids entity or activity B from occurring |
| **Direction** | A PROHIBITS B |
| **Examples** | SEBI PROHIBITS insider trading; F&O Ban PROHIBITS new positions in banned stocks; Constraint PROHIBITS position size exceeding 5% NAV |
| **Importance** | Critical |

---

### REL-105 — ESCALATES_TO / ESCALATED_FROM

| Attribute | Value |
|---|---|
| **Name** | ESCALATES_TO / ESCALATED_FROM |
| **Definition** | Entity A passes issue or decision B to a higher authority C for resolution, when A lacks the authority or information to resolve it |
| **Direction** | A ESCALATES_TO C (via entity B) |
| **Examples** | Conviction between 5.0 and 6.5 ESCALATES_TO human review; Unusual market event ESCALATES_TO manual intervention mode |
| **Importance** | High |

---

## CATEGORY 17 — CONTEXT AND SCOPE RELATIONSHIPS

---

### REL-106 — APPLIES_IN / CONTEXT_FOR

| Attribute | Value |
|---|---|
| **Name** | APPLIES_IN / CONTEXT_FOR |
| **Definition** | Relationship or rule A is valid and applicable only within context or condition B |
| **Meaning** | This is a meta-relationship: it qualifies when other relationships are valid. "Momentum WORKS_IN trending regime" — the WORKS_IN relationship APPLIES_IN the trending regime context. |
| **Direction** | A APPLIES_IN B |
| **Examples** | Momentum strategy APPLIES_IN trending market regime; RSI overbought signal APPLIES_IN non-trending market (false signals in strong trend); Yield curve inversion recession signal APPLIES_IN developed economies |
| **Knowledge Produced** | Regime-conditional strategy validity; contextual evidence weight adjustment |
| **Importance** | Critical |

---

### REL-107 — CONDITIONED_ON / CONDITIONS

| Attribute | Value |
|---|---|
| **Name** | CONDITIONED_ON / CONDITIONS |
| **Definition** | Entity A's behavior or validity depends on entity B's state being in a defined condition |
| **Direction** | A CONDITIONED_ON B |
| **Examples** | Breakout strategy CONDITIONED_ON high volume confirmation; Conviction score interpretation CONDITIONED_ON market regime; Short selling CONDITIONED_ON F&O eligible status |
| **Importance** | High |

---

### REL-108 — VALID_FOR / VALIDATION_SCOPE

| Attribute | Value |
|---|---|
| **Name** | VALID_FOR / VALIDATION_SCOPE |
| **Definition** | Entity A's truth or relevance is bounded by context B — outside B, A may not apply |
| **Direction** | A VALID_FOR B |
| **Examples** | Knowledge item "tech stocks lead market in early bull phases" VALID_FOR post-bear-market conditions; Seasonal pattern VALID_FOR specific calendar periods |
| **Importance** | High |

---

### REL-109 — VARIES_WITH / MODULATES

| Attribute | Value |
|---|---|
| **Name** | VARIES_WITH / MODULATES |
| **Definition** | Entity A's strength or value changes systematically as a function of entity B |
| **Direction** | A VARIES_WITH B |
| **Examples** | Correlation between stocks VARIES_WITH market stress (increases in crisis); Lead-lag relationship VARIES_WITH market regime |
| **Importance** | High |

---

## CATEGORY 18 — SEMANTIC AND IDENTITY RELATIONSHIPS

---

### REL-110 — IS_A / HAS_SUBTYPE

| Attribute | Value |
|---|---|
| **Name** | IS_A / HAS_SUBTYPE |
| **Definition** | Entity A is a specific type or specialization of entity B — inheriting all of B's essential properties |
| **Direction** | A IS_A B (A is the subtype; B is the supertype) |
| **Examples** | Options Contract IS_A Derivative IS_A Financial Instrument; Listed Company IS_A Organization |
| **Knowledge Produced** | Type inference: rules applying to the supertype apply to the subtype |
| **Importance** | Critical (for inference) |

---

### REL-111 — PROXIES_FOR / PROXY_USED_BY

| Attribute | Value |
|---|---|
| **Name** | PROXIES_FOR / PROXY_USED_BY |
| **Definition** | Observable entity A is used as a measurable substitute for unobservable or difficult-to-measure entity B |
| **Direction** | A PROXIES_FOR B |
| **Examples** | India VIX PROXIES_FOR market fear and uncertainty; Credit spreads PROXY_FOR default probability; ADT/Daily Volume PROXIES_FOR liquidity |
| **Knowledge Produced** | Proxy accuracy; conditions when proxy breaks down |
| **Importance** | High |

---

### REL-112 — MAPS_TO / MAPPED_FROM

| Attribute | Value |
|---|---|
| **Name** | MAPS_TO / MAPPED_FROM |
| **Definition** | Entity A in one classification system corresponds to entity B in a different system |
| **Direction** | A MAPS_TO B |
| **Examples** | NSE symbol RELIANCE MAPS_TO ISIN INE002A01018; GICS "Banks" MAPS_TO NSE "Private Banks" + "PSU Banks" |
| **Knowledge Produced** | Cross-system interoperability; entity resolution across data sources |
| **Importance** | High |

---

### REL-113 — REPRESENTS / REPRESENTED_BY

| Attribute | Value |
|---|---|
| **Name** | REPRESENTS / REPRESENTED_BY |
| **Definition** | Entity A stands as a proxy, symbol, or numerical embodiment of entity B |
| **Direction** | A REPRESENTS B |
| **Examples** | NIFTY 50 REPRESENTS the performance of India's 50 largest listed companies; Conviction score REPRESENTS the system's confidence level |
| **Importance** | High |

---

## CATEGORY 19 — ADDITIONAL SPECIALIZED RELATIONSHIPS

---

### REL-114 — ARBITRAGES_BETWEEN

| Attribute | Value |
|---|---|
| **Name** | ARBITRAGES_BETWEEN |
| **Definition** | A market participant A exploits a price discrepancy between two related entities B and C, buying the cheaper and selling the more expensive to profit from convergence |
| **Direction** | A ARBITRAGES_BETWEEN (B, C) |
| **Allowed Entity Types** | A: Arbitrage Fund, HFT; B/C: NSE Spot and BSE Spot prices; Spot and Futures prices |
| **Examples** | Arbitrage fund ARBITRAGES_BETWEEN NSE spot price and BSE spot price of INFY; Statistical arb ARBITRAGES_BETWEEN cointegrated pair |
| **Knowledge Produced** | Price efficiency signal: arbitrage activity reduces and eliminates mispricings |
| **Importance** | High |

---

### REL-115 — REBALANCES / REBALANCED_BY

| Attribute | Value |
|---|---|
| **Name** | REBALANCES / REBALANCED_BY |
| **Definition** | Entity A periodically adjusts the weights of its constituent entities B toward target allocations |
| **Direction** | A REBALANCES B |
| **Examples** | Portfolio REBALANCES positions monthly; Index Provider REBALANCES NIFTY 50 quarterly; ETF fund manager REBALANCES to match index |
| **Knowledge Produced** | Predictable buying/selling pressure ahead of rebalancing dates |
| **Importance** | High |

---

### REL-116 — SETTLES / SETTLED_BY

| Attribute | Value |
|---|---|
| **Name** | SETTLES / SETTLED_BY |
| **Definition** | Entity A completes the transfer of funds and securities associated with trade B |
| **Direction** | A SETTLES B |
| **Allowed Entity Types** | A: Clearing Corporation, Broker; B: Trade, Position (at expiry) |
| **Examples** | NSCCL SETTLES all NSE equity trades on T+1; Options exercise settlement occurs at expiry |
| **Importance** | High |

---

### REL-117 — GENERATES / GENERATED_BY

| Attribute | Value |
|---|---|
| **Name** | GENERATES / GENERATED_BY |
| **Definition** | Entity A produces entity B as an output through a defined process |
| **Direction** | A GENERATES B |
| **Examples** | Company GENERATES revenue; Position GENERATES return (or loss); Learning process GENERATES updated knowledge item; Evidence assembly GENERATES conviction score |
| **Importance** | High |

---

### REL-118 — CONVERTS_TO / CONVERTED_FROM

| Attribute | Value |
|---|---|
| **Name** | CONVERTS_TO / CONVERTED_FROM |
| **Definition** | Entity A transforms into a different entity B at a defined event or condition |
| **Direction** | A CONVERTS_TO B |
| **Examples** | Convertible Bond CONVERTS_TO equity shares at conversion price; Right Entitlement CONVERTS_TO equity share on exercise; Hypothesis CONVERTS_TO Decision when conviction exceeds threshold |
| **Importance** | High |

---

### REL-119 — BENCHMARKS_PERFORMANCE_OF / BENCHMARK_FOR

| Attribute | Value |
|---|---|
| **Name** | BENCHMARKS_PERFORMANCE_OF / BENCHMARK_FOR |
| **Definition** | Index A serves as the reference standard against which portfolio or fund B's returns are measured |
| **Direction** | A BENCHMARKS_PERFORMANCE_OF B |
| **Examples** | NIFTY 50 BENCHMARKS_PERFORMANCE_OF large-cap equity funds; CRISIL Short Term Bond Index BENCHMARKS_PERFORMANCE_OF short-duration debt funds |
| **Importance** | High |

---

### REL-120 — ANNOUNCES / ANNOUNCED_BY

| Attribute | Value |
|---|---|
| **Name** | ANNOUNCES / ANNOUNCED_BY |
| **Definition** | Entity A makes a public disclosure of event or decision B |
| **Direction** | A ANNOUNCES B |
| **Examples** | Company ANNOUNCES quarterly results; RBI ANNOUNCES MPC decision; Exchange ANNOUNCES circuit halt |
| **Knowledge Produced** | Information timing: the announcement moment is when the market processes the information |
| **Importance** | High |

---

### REL-121 — DIVERSIFIES_AGAINST / DIVERSIFIED_FROM

| Attribute | Value |
|---|---|
| **Name** | DIVERSIFIES_AGAINST / DIVERSIFIED_FROM |
| **Definition** | Adding entity A to portfolio reduces the idiosyncratic risk of the portfolio's exposure to B because A's returns are non-correlated with B |
| **Direction** | A DIVERSIFIES_AGAINST B |
| **Examples** | Gold position DIVERSIFIES_AGAINST equity portfolio risk; IT stocks DIVERSIFY_AGAINST INR depreciation risk in domestic sectors |
| **Importance** | High |

---

### REL-122 — FUNDS / FUNDED_BY

| Attribute | Value |
|---|---|
| **Name** | FUNDS / FUNDED_BY |
| **Definition** | Entity A provides the capital necessary for entity B to operate, invest, or exist |
| **Direction** | A FUNDS B |
| **Examples** | Equity issuance FUNDS company capex; IPO proceeds FUND company expansion plan; SIP inflows FUND mutual fund deployment |
| **Importance** | High |

---

### REL-123 — CROWDED_WITH / CROWDING_PARTNER

| Attribute | Value |
|---|---|
| **Name** | CROWDED_WITH / CROWDING_PARTNER |
| **Definition** | Entity A and entity B are held in the same direction by the same group of investors, creating correlated forced selling risk if sentiment reverses |
| **Direction** | Symmetric |
| **Examples** | IT sector positions CROWDED_WITH USD/INR long positions (FII view); momentum stocks CROWDED_WITH each other at market peak |
| **Knowledge Produced** | Crowding risk: simultaneous exit by many investors amplifies price decline |
| **Importance** | High |

---

### REL-124 — SENTIMENT_TOWARD / SENTIMENT_SOURCE

| Attribute | Value |
|---|---|
| **Name** | SENTIMENT_TOWARD / SENTIMENT_SOURCE |
| **Definition** | The aggregate behavior or positioning of market participants A toward entity B reflects a measurable directional sentiment |
| **Direction** | A SENTIMENT_TOWARD B |
| **Examples** | Retail investors SENTIMENT_TOWARD NIFTY (net buyers = bullish sentiment); Options PCR SENTIMENT_TOWARD NIFTY direction |
| **Knowledge Produced** | Contrarian signals: extreme bullish sentiment may signal impending reversal |
| **Importance** | High |

---

### REL-125 — BRIDGES / BRIDGED_BY

| Attribute | Value |
|---|---|
| **Name** | BRIDGES / BRIDGED_BY |
| **Definition** | Entity A acts as the connective intermediary between entities B and C, enabling flow or relationship that would not otherwise exist |
| **Direction** | A BRIDGES B and C |
| **Examples** | Broker BRIDGES retail investor and exchange; Custodian BRIDGES foreign investor and Indian depository system; Clearing corp BRIDGES buyer and seller of derivatives |
| **Knowledge Produced** | Intermediary risk: if bridge entity fails, the flow is disrupted |
| **Importance** | High |

---

---

## PART IV — RELATIONSHIP TAXONOMY

*Every relationship belongs to one or more fundamental categories. This taxonomy enables systematic reasoning: when analyzing an entity, traverse all relationship types in sequence to ensure complete coverage.*

---

### Taxonomy Level 1 — By Structural Purpose

| Taxonomy Class | Core Question It Answers | Relationship Types |
|---|---|---|
| **Ownership & Control** | Who owns, controls, or has authority over this entity? | OWNS, CONTROLS, GOVERNS, REGULATES, MANAGES, OPERATES, SUPERVISES, AUTHORIZES, CUSTODIES, LICENSES |
| **Structural Composition** | What is this entity made of? What larger thing contains it? | CONTAINS, PART_OF, COMPOSED_OF, AGGREGATES, MEMBER_OF, SUB_TYPE_OF, NESTED_WITHIN, DECOMPOSES_INTO |
| **Hierarchical** | Where does this entity sit in the hierarchy? What is above and below it? | REPORTS_TO, MANAGED_BY, SUB_TYPE_OF, INHERITS_FROM, ESCALATES_TO, IS_A |
| **Temporal** | When was this entity created? When does it expire? What comes before/after? | PRECEDES, FOLLOWS, EXPIRES_ON, SUPERSEDES, SCHEDULED_FOR, CYCLES_WITH, OVERLAPS_WITH, ROLLS_OVER_TO |
| **Financial** | How does this entity relate to capital, value, and returns? | HOLDS, INVESTS_IN, ALLOCATES_TO, TRADES, FUNDS, COLLATERALIZES, HEDGES, PRICES, WEIGHTS_IN, LEVERAGES |
| **Market Structure** | How does this entity participate in the market mechanism? | ISSUES, LISTED_ON, TRADED_ON, CLEARED_BY, SETTLED_BY, UNDERLIES, CONSTITUENT_OF, BENCHMARKED_AGAINST, CLASSIFIED_IN |
| **Organizational** | How do institutions relate to each other? | REPORTS_TO, COMPETES_WITH, ACQUIRES, MERGES_WITH, PARTNERS_WITH, ADVISES, LICENSES_TO, RATED_BY, SUPPLIED_BY |
| **Economic** | How does this entity participate in the macroeconomy? | INFLUENCES, TRANSMITS_TO, PROPAGATES_THROUGH, CYCLES_WITH, GRANGER_CAUSES, CO_INTEGRATES_WITH |
| **Behavioral** | What patterns does this entity exhibit relative to others? | CORRELATES_WITH, LEADS, LAGS, MEAN_REVERTS_TO, BETA_TO, TRACKS, DEVIATES_FROM, SEASONALLY_FOLLOWS |
| **Causal** | What causes what in the investment universe? | CAUSES, TRIGGERS, ENABLES, PREVENTS, AMPLIFIES, DAMPENS, DRIVES, DISRUPTS, CASCADES_INTO, TRANSMITS_TO |
| **Statistical** | What quantitative relationships exist between entity attributes? | CORRELATES_WITH, LEADS, LAGS, CO_INTEGRATES_WITH, GRANGER_CAUSES, BETA_TO, MEAN_REVERTS_TO |
| **Knowledge** | How is knowledge created and structured? | DERIVED_FROM, CALCULATED_FROM, BASED_ON, REFERENCES, DOCUMENTS, EXPLAINS, MODELS, VALIDATES, SYNTHESIZES_INTO |
| **Reasoning** | How does evidence relate to conclusions? | SUPPORTS, CONTRADICTS, CONFIRMS, INVALIDATES, STRENGTHENS, WEAKENS, CONTEXTUALIZES, CORROBORATES, SYNTHESIZES_INTO |
| **Decision** | How are decisions formed, constrained, and executed? | TARGETS, CONSTRAINS, APPROVES, REJECTS, OVERRIDES, ALLOCATES_TO, SIZES, PRIORITIZES, RECOMMENDS |
| **Learning** | How does the system improve over time? | LEARNS_FROM, TRAINS_ON, VALIDATES_AGAINST, UPDATES_FROM, PREDICTS, RETROACTIVELY_CONFIRMS, DISCONFIRMS |
| **AI / Computational** | How do models and algorithms process entities? | TRAINS_ON, VALIDATES_AGAINST, MODELS, PREDICTS, BACKTESTS_AGAINST, SCORES, CLASSIFIES, CLUSTERS, RANKS |
| **Risk** | How is risk created, measured, and managed? | EXPOSES_TO, HEDGES, MITIGATES, AMPLIFIES_RISK_IN, CONCENTRATES, DIVERSIFIES, STRESS_TESTS, DEFAULTS_ON |
| **Control** | What mechanism constrains or enables system behavior? | CONSTRAINS, ENFORCES, PROHIBITS, MANDATES, APPROVES, OVERRIDES, TRIGGERS, LIMITS |
| **Governance** | How is compliance, accountability, and oversight structured? | AUDITS, REVIEWS, ESCALATES_TO, SANCTIONS, ENFORCES, MANDATES, PROHIBITS, CERTIFIES |
| **Event** | How do events relate to their causes and effects? | TRIGGERS, CAUSED_BY, ANNOUNCES, SCHEDULES, CANCELS, SUPERSEDES, PRECEDES, FOLLOWS |
| **Context** | Under what conditions do other relationships hold? | APPLIES_IN, VALID_FOR, CONDITIONED_ON, SCOPED_TO, QUALIFIED_BY, VARIES_WITH, STABLE_UNDER, BREAKS_DOWN_IN |
| **Semantic** | What identity and type hierarchies exist? | IS_A, INSTANCE_OF, SYNONYM_OF, MAPS_TO, REPRESENTS, PROXIES_FOR, EQUIVALENT_TO, ANALOGOUS_TO |
| **Information Flow** | How does information travel through the system? | MEASURES, OBSERVES, MONITORS, REPORTS_ON, DISCLOSES, ALERTS_ON, TRACKS, TRANSMITS_TO |
| **Market Intelligence** | How is intelligence produced from data? | RANKS, SCORES, CLASSIFIES, CLUSTERS, SCREENS_FOR, ATTRIBUTES_TO, NORMALIZES, WEIGHTS |

---

### Taxonomy Level 2 — By Temporal Nature

| Temporal Class | Meaning | Examples |
|---|---|---|
| **Permanent** | The relationship holds for both entities' entire lifespans | ISSUES, LISTED_ON, COMPOSED_OF, SUB_TYPE_OF, CLASSIFIED_IN |
| **Persistent** | The relationship holds for a long period and changes only on defined events | OWNS, CONTROLS, HOLDS, MEMBER_OF, RATED_BY |
| **Dynamic** | The relationship's strength or character changes continuously | CORRELATES_WITH, LEADS, BETA_TO, SENTIMENT_TOWARD, CROWDED_WITH |
| **Event-Triggered** | The relationship exists only at a specific event or point in time | DEFAULTS_ON, ANNOUNCES, TRIGGERS, CONVERTS_TO, ROLLS_OVER_TO |
| **Time-Bounded** | The relationship exists for a defined period | EXPIRES_ON, OVERLAPS_WITH, VALID_FOR, SCHEDULED_FOR |
| **Historical** | The relationship existed in the past and is now immutable | RETROACTIVELY_CONFIRMS, DISCONFIRMS, PRECEDED, FOLLOWED |
| **Conditional** | The relationship exists only when a condition is met | CONDITIONED_ON, APPLIES_IN, VALID_FOR, VARIES_WITH |
| **Recurring** | The relationship reoccurs periodically | CYCLES_WITH, ROLLS_OVER_TO, REBALANCES, SEASONALLY_FOLLOWS |

---

### Taxonomy Level 3 — By Direction Type

| Direction Class | Meaning | Examples |
|---|---|---|
| **Strictly Directional** | A→B is fundamentally different from B→A | CAUSES, ISSUES, OWNS, LEARNS_FROM, PREDICTS |
| **Symmetric** | A RELATES_TO B is same as B RELATES_TO A | CORRELATES_WITH, COMPETES_WITH, CO_INTEGRATES_WITH |
| **Bidirectional but Asymmetric** | Both directions exist but with different meanings | LEADS/LAGS are same pairs, different directions; INFLUENCES may be unequal both ways |
| **Reflexive** | An entity can have this relationship with itself | CORRELATES_WITH (auto-correlation); MEAN_REVERTS_TO (own mean) |

---

### Taxonomy Level 4 — By Certainty Class

| Certainty Class | Meaning | Examples |
|---|---|---|
| **Deterministic** | The relationship holds with certainty when conditions are met | CALCULATED_FROM, EXPIRES_ON, SETTLED_BY, IS_A |
| **High Confidence** | The relationship holds consistently with documented exceptions | ISSUES, LISTED_ON, REGULATED_BY, COMPOSED_OF |
| **Probabilistic** | The relationship holds with measurable probability | CORRELATES_WITH (probability of co-movement), PREDICTS, LEADS |
| **Contextual** | The relationship holds only under defined market conditions | APPLIES_IN, VALID_FOR, CONDITIONED_ON, BREAKS_DOWN_IN |
| **Hypothetical** | The relationship is proposed but not validated | SUPPORTS (unverified evidence), PREDICTS (pre-outcome) |

---

## PART V — RELATIONSHIP CARDINALITY

*Cardinality defines how many instances of entity A can be connected to how many instances of entity B through a given relationship type.*

---

### 1:1 — One-to-One

**Definition:** Exactly one instance of A connects to exactly one instance of B.

**Investment Examples:**
- Futures Contract EXPIRES_ON exactly one Expiry Date
- Decision CREATES exactly one Position (at entry)
- Specific Trade SETTLES_ON exactly one Settlement Date
- Specific Bond MATURES_INTO exactly one cash maturity event

**Characteristics:**
- Strongest structural constraint
- Ensures uniqueness
- Common in legal/contractual relationships
- Any violation signals data integrity error

---

### 1:N — One-to-Many

**Definition:** One instance of A connects to many instances of B.

**Investment Examples:**
- Exchange LISTS many Instruments (thousands)
- Company ISSUES multiple Instruments (equity, bonds, CPs)
- Portfolio CONTAINS many Positions
- Sector CONTAINS many Companies
- Index COMPRISES many Constituent Stocks
- Strategy PRODUCES many Trades over time
- Regulator REGULATES many market participants
- Knowledge Item EXPLAINS many Observations

**Characteristics:**
- Most common cardinality in hierarchical relationships
- The "one" side (A) is structurally superior
- Traversal: "what does this entity contain?"

---

### N:1 — Many-to-One

**Definition:** Many instances of A connect to one instance of B.

**Investment Examples:**
- Many Stocks CONSTITUENT_OF one Index
- Many Positions AGGREGATED_INTO one Portfolio
- Many Evidence Items SYNTHESIZE_INTO one Conviction
- Many Strategies MANAGED_BY one Portfolio Manager
- Many Instruments CLASSIFIED_IN one Sector
- Many Tickers LISTED_ON one Exchange

**Characteristics:**
- Mirror of 1:N (same relationship, different direction)
- The "many" side (A) is typically a component or member

---

### N:N — Many-to-Many

**Definition:** Many instances of A can connect to many instances of B.

**Investment Examples:**
- Many Stocks CORRELATE_WITH many other Stocks
- Many Investors TRADE many Instruments
- Many Models TRAINED_ON many Datasets
- Many Companies COMPETE_WITH many other Companies
- Many Evidence Items SUPPORT many Hypotheses
- FIIs HOLD many Stocks; many Stocks HELD_BY many FIIs

**Characteristics:**
- Creates rich networks — the basis of knowledge graph traversal
- Requires relationship attributes (edge properties) to be meaningful
- "HDFC Bank CORRELATES_WITH ICICI Bank" must include: coefficient, lookback, regime

---

### Recursive — Self-Referential

**Definition:** An entity A has a relationship with another entity of the same type.

**Investment Examples:**
- Company ACQUIRES Company (both are Company entities)
- Company COMPETES_WITH Company
- Index CORRELATES_WITH Index (NIFTY 50 vs NIFTY Bank)
- Evidence CONTRADICTS Evidence (conflicting signals)
- Hypothesis SUPERSEDES Hypothesis (updated view)
- Strategy OUTPERFORMS Strategy (benchmark comparison)

**Characteristics:**
- Creates within-type networks — critical for competitive analysis, correlation matrices
- Enables similarity reasoning: "find all companies like this one"

---

### Circular — Bidirectional Recursive

**Definition:** A relationship forms a closed loop: A → B → C → A.

**Investment Examples:**
- Global Market TRANSMITS_TO Indian Market TRANSMITS_TO Asia Markets TRANSMITS_TO Global Market
- Company Growth DRIVES Earnings DRIVES Stock Price DRIVES Investor Interest DRIVES Capital Availability DRIVES Company Growth
- Inflation CAUSES Rate Hike CAUSES Currency Strength CAUSES Import Cost Reduction CAUSES Lower Inflation

**Characteristics:**
- Creates feedback loops — both virtuous and vicious
- Critical for systemic risk analysis
- Must track cycle direction (amplifying vs stabilizing)
- Circular relationships require cycle detection and dampening mechanisms

---

### Dynamic — Time-Varying

**Definition:** The relationship exists at some times but not others, or its strength/character varies with time.

**Investment Examples:**
- Correlation between sectors VARIES over market cycle
- Lead time in LEADS relationship changes in different regimes
- Strategy VALID_FOR trending regime; INVALID in ranging regime
- CROWDED_WITH relationships form and dissolve with market narrative cycles

**Characteristics:**
- Requires timestamping all relationship instances
- Historical relationship strengths must be preserved
- Current strength ≠ historical average strength

---

### Conditional — State-Dependent

**Definition:** The relationship activates or strengthens only when a defined condition is met.

**Investment Examples:**
- Kill Switch relationship activates ONLY WHEN VIX > 45
- Circuit breaker relationship ONLY WHEN price moves > 10% in session
- Merger relationship activates ONLY WHEN regulatory approval granted
- Buyback relationship ONLY WHEN company has surplus cash and stock is undervalued

**Characteristics:**
- Condition must be precisely specified
- System must evaluate condition state at each reasoning cycle
- Conditions can be multi-dimensional (multiple conditions must all be met)

---

### Temporary — Time-Bounded

**Definition:** The relationship exists for a defined, limited period.

**Investment Examples:**
- Rights (Entitlement) VALID_FOR subscription window only
- Evidence Item SUPPORTS hypothesis for defined staleness period
- Signal VALID_FOR N trading sessions
- Conviction VALID_FOR until thesis invalidation event

**Characteristics:**
- Must track creation date and expiry date for every temporary relationship
- Stale relationships that are treated as current corrupt reasoning

---

### Permanent — Lifetime-Bound

**Definition:** The relationship holds for the entire lifespans of both connected entities.

**Investment Examples:**
- Company ISSUED Stock (permanent; stock cannot change its issuer)
- Entity INSTANCE_OF type (permanent type membership)
- Event OCCURRED_ON date (historical fact — immutable)
- Trade EXECUTED_AT price on date (immutable financial record)

**Characteristics:**
- No expiry date — lasts as long as both entities exist
- Historical instances remain permanent even after one entity ceases to exist

---

### Versioned — Historical Chain

**Definition:** Multiple versions of the relationship exist at different points in time, forming a version history.

**Investment Examples:**
- Rating RATED_AT (AA in 2023, AA- in 2024, A+ in 2025) — versioned credit relationship
- Strategy parameters VERSION_1, VERSION_2, VERSION_3 — versioned strategy-parameter relationship
- Shareholding pattern — promoter OWNS X% in Q1, Y% in Q2 (versioned ownership)

**Characteristics:**
- Every version is preserved with its effective date
- Point-in-time queries must specify which version is requested
- Current version = most recent; historical analysis requires version specification

---

## PART VI — RELATIONSHIP RULES: THE CONSTITUTIONAL FRAMEWORK

*Twelve constitutional rules governing every relationship in this ontology. These rules are permanent and universal — no relationship type can violate them.*

---

**Rule 1 — Relationships Cannot Exist Without Entities**

A relationship is definitionally dependent on its endpoint entities. A→B cannot exist if either A or B ceases to exist in an active state. When an entity is retired, all relationships connecting to it must be either terminated, archived with an end-date, or explicitly transferred to a successor entity. There are no "floating" relationships. An unanchored relationship is a data integrity violation.

*Corollary:* Before retiring an entity, the system must enumerate all its relationships and resolve each one: terminate, transfer, or archive.

---

**Rule 2 — Every Relationship Has Direction**

Every relationship is asymmetric. "HDFC Bank LISTED_ON NSE" and "NSE LISTED_ON HDFC Bank" are different statements — the second is nonsensical. The direction defines which entity is the subject (source) and which is the object (target). The direction also defines the inverse relationship, which may have a different name and different meaning.

*Corollary:* Directionless associations are not typed relationships. Upgrading an observation of co-occurrence to a typed relationship requires assigning direction.

---

**Rule 3 — Every Relationship Has Type**

An untyped link between two entities is not a relationship — it is a raw co-occurrence. Type is what gives a relationship its semantic meaning, its inference implications, its applicable reasoning rules, and its constraint set. Every relationship added to the system must be assigned to one of the types defined in this ontology. If no type fits, a new type must be formally defined here before the relationship is created.

*Corollary:* Adding a "type: unknown" relationship is prohibited. Unknown relationships must be analyzed and typed.

---

**Rule 4 — Relationships May Have Confidence**

Not all relationships are equally certain. A relationship derived from a single observation carries less confidence than one validated by 50 independent observations. Every relationship carries a confidence attribute: a number from 0 to 1 representing the system's certainty that the relationship is real, current, and significant. Confidence of 0 = hypothetical; 1 = proven beyond reasonable doubt. Most investment relationships live between 0.6 and 0.9.

*Corollary:* Decisions based on relationships with confidence < 0.5 must be treated as speculative. The system must propagate low confidence: a chain of relationships with confidences 0.9, 0.8, 0.7 produces a path confidence of 0.9 × 0.8 × 0.7 = 0.504.

---

**Rule 5 — Relationships May Expire**

Temporal relationships become invalid after their natural lifetime. A signal SUPPORTS a hypothesis only for a defined validity window. An evidence item's relevance decays with time. A correlation measured in 2022 may not hold in 2026. The system must track every relationship's creation date and, where applicable, its expiry date. Expired relationships must not be treated as current.

*Corollary:* Stale relationships are more dangerous than missing relationships — they give the appearance of information while providing outdated or wrong context.

---

**Rule 6 — Relationships May Evolve**

The same fundamental relationship type between the same two entities can change in strength, direction, or character over time. The correlation between India and US markets was 0.4 before 2008 and 0.65 after. The leading relationship between PMI and GDP has shifted with structural changes in the Indian economy. Relationships must be re-measured periodically, with the history of measurements preserved.

*Corollary:* No relationship is assumed permanently static except those that are definitionally permanent (type hierarchies, historical events). All statistical relationships must have a scheduled refresh frequency.

---

**Rule 7 — Relationships May Strengthen or Weaken**

Relationships have magnitude as well as type and direction. A correlation can strengthen from 0.4 to 0.7. A causal relationship's effect size can grow or shrink. Evidence weight in a support relationship can increase as more corroborating observations accumulate. The system must track not just whether a relationship exists but how strong it currently is, and whether it is strengthening or weakening.

*Corollary:* Trend in relationship strength is as important as current strength. A rapidly weakening causal relationship is a warning signal — the transmission mechanism may be breaking down.

---

**Rule 8 — Relationships May Become Invalid**

Structural changes can render a relationship completely invalid — not merely weakened. The causal relationship "RBI rate hike → MCLR increase" is valid only when the banking sector is functioning normally. Under extreme credit stress, the transmission breaks down. The lead relationship between a sector bellwether and its peers can vanish after the bellwether's business model changes. The system must monitor for relationship invalidation events.

*Corollary:* Relationship validity depends on the stability of the mechanism underlying it. When mechanisms change, relationships must be re-validated from scratch.

---

**Rule 9 — Relationships Have Mechanism**

For causal and influence relationships, the system must document the transmission mechanism — the pathway through which A's state change reaches B. "Fed rate hike INFLUENCES NIFTY" requires: Fed Rate → DXY Strength → FII sell India → NIFTY falls. The mechanism makes the relationship testable, falsifiable, and exploitable for multi-hop reasoning.

*Corollary:* A relationship without a documented mechanism is an association, not a causal relationship. Associations have lower reasoning value than mechanistic relationships.

---

**Rule 10 — Relationships Are Independent From Their Endpoints' Internal States**

The ISSUES relationship between Reliance Industries and Reliance Equity does not change when the company's CEO changes or when its quarterly earnings miss estimates. The relationship's type is structural — determined by the founding event (IPO). Internal state changes within an entity do not change the structural relationships that entity has already established. What changes is the information (attributes) those entities carry, not their structural connections.

*Corollary:* Clearly separate relationship changes (structural) from attribute changes (informational). Conflating the two corrupts the graph.

---

**Rule 11 — The Relationship Graph Is the System's Reasoning Infrastructure**

The complete graph of all entities and relationships constitutes the system's permanent knowledge infrastructure. It is more durable than any single model, more valuable than any single dataset, and more important than any single decision. Every piece of software is replaceable; the relationship graph is not. It must be treated as a first-class asset — versioned, backed up, audited, and protected.

*Corollary:* No software migration, model replacement, or system upgrade justifies truncating or simplifying the relationship graph. Migrations must preserve full relationship history.

---

**Rule 12 — New Relationship Types Must Not Break Existing Reasoning**

When a new relationship type is added to this ontology, it must not invalidate or override existing relationships or reasoning paths. New types are additive. They extend the system's vocabulary. They do not redefine existing types. If a new type appears to overlap with an existing type, the difference must be precisely defined and documented.

*Corollary:* Any change to an existing relationship type's definition, direction, cardinality, or constraints requires a full impact assessment on all existing instances of that relationship and all reasoning paths that traverse it.

---

## PART VII — RELATIONSHIP EVOLUTION

*How relationships evolve through time — the dynamic nature of connections in the investment universe.*

---

### Seven Modes of Relationship Evolution

**Mode 1 — Inception**
Every relationship begins with an inception event. The ISSUES relationship between a company and its equity began at the moment of the IPO. The CORRELATES_WITH relationship between two stocks can only be calculated after sufficient co-observation history exists (minimum 20-30 data points for statistical validity). The SUPPORTS relationship between evidence and hypothesis begins when the evidence is formally assembled. Tracking inception dates is critical for historical analysis.

**Mode 2 — Strengthening**
Relationships grow stronger through repeated confirmation. The LEADS relationship between a sector bellwether and its sector becomes stronger evidence as more instances of lead behavior are observed across different market regimes. The SUPPORTS relationship gains weight as more independent corroborating evidence accumulates. Relationships should be tracked with an "observation count" — how many times has this relationship been confirmed?

**Mode 3 — Weakening**
Relationships weaken through contradicting observations, time passage, or structural change. A correlation that was 0.8 three years ago may weaken to 0.5 as market structure changes. Evidence supporting a hypothesis loses weight as it becomes stale. The seasonal pattern CYCLES_WITH relationship may weaken as economic structure shifts. Regular re-measurement with rolling windows is essential.

**Mode 4 — Regime-Shift Discontinuity**
In investment markets, relationships can change sharply at regime boundaries. The CORRELATES_WITH relationship between domestic equities and international markets typically strengthens sharply during crisis periods. The DAMPENS relationship between DII buying and market falls may weaken during extreme events. The APPLIES_IN relationships document these regime dependencies — every relationship must specify its regime validity.

**Mode 5 — Invalidation**
A relationship can be definitively invalidated. When IL&FS defaulted, the CROWDED_WITH relationships between NBFC bonds and "safe" institutional portfolios were instantly invalidated. When a company's business model is disrupted, the COMPETES_WITH relationships with traditional players may shift from symmetric to asymmetric. Invalidated relationships must be archived with an invalidation date and reason — they remain valuable as historical learning records.

**Mode 6 — Substitution**
A new entity can replace an old entity in a relationship, while the relationship type persists. When HDFC Bank merged with HDFC Ltd, many relationships that HDFC Ltd held were substituted into HDFC Bank. The regulatory relationship REGULATED_BY SEBI transferred. The competitor relationships were updated. Substitution must be explicitly tracked — it cannot be assumed automatically.

**Mode 7 — Legacy Preservation**
When a relationship ends (either through expiry, entity retirement, or invalidation), its historical record must be preserved. The HOLDS relationship between LIC and a stock it sold may be closed, but the record of that holding (quantity, period, average price) is permanently archived. Historical relationship records are essential for behavioral modeling, competitive analysis, and learning system calibration.

---

### Relationship Lifecycle Model

```
PROPOSED (A and B are connected by suspected relationship)
        ↓ [evidence threshold met]
HYPOTHESIZED (relationship type assigned, mechanism documented)
        ↓ [validation process]
        ├── VALIDATED (sufficient evidence, mechanism confirmed)
        │       ↓ [active use in reasoning]
        │   ACTIVE (in use, being monitored for evolution)
        │       ↓ [continuous strength monitoring]
        │       ├── STRENGTHENING → still ACTIVE
        │       ├── WEAKENING → WATCH status
        │       ├── STABLE → still ACTIVE
        │       └── BREAKING DOWN → UNDER_REVIEW
        │               ↓ [investigation]
        │           INVALIDATED or RE-VALIDATED
        │
        └── REJECTED (insufficient evidence or mechanism disproven)
                ↓
            ARCHIVED (permanent record of why relationship was rejected)
```

---

### Relationship Strength Life Cycle

```
LOW CONFIDENCE INCEPTION
        ↓ repeated confirmation across independent observations
MODERATE CONFIDENCE (0.5-0.7)
        ↓ continued validation, mechanism confirmed
HIGH CONFIDENCE (0.7-0.9) — PRIMARY USE IN REASONING
        ↓ extreme validation across multiple regimes
PROVEN STRUCTURAL (0.9+) — TREATED AS DEFINITIONAL
        ↓ structural change event OR contradicting evidence accumulation
WEAKENING — triggers review process
        ↓ investigation
        ├── Re-confirmed → strength restores
        └── Failed re-confirmation → INVALIDATED
```

---

### Dynamic Relationship Properties (Must Be Tracked)

| Property | Update Frequency | Why Critical |
|---|---|---|
| Strength / Coefficient | Daily (statistical) / Event (structural) | Current strength determines inference weight |
| Direction (for asymmetric) | Per measurement window | Lead-lag direction can reverse |
| Regime Validity | Per regime change event | Relationships valid in one regime fail in another |
| Confidence Score | Rolling window update | Confidence reflects both evidence quality and recency |
| Observation Count | Every new confirming instance | Count determines statistical reliability |
| Last Confirmed Date | Every confirmation | Staleness tracking |
| Mechanism Validity Flag | Per major structural event | Mechanism may break before relationship strength visibly deteriorates |

---

## PART VIII — KNOWLEDGE GRAPH READINESS

*How this relationship ontology naturally becomes a knowledge graph — the conceptual bridge between ontological design and intelligent reasoning infrastructure.*

---

### The Knowledge Graph Transition

This ontology is not merely a documentation exercise. Every relationship defined here is a potential edge in a knowledge graph. Every entity in ENTITY_ONTOLOGY.md is a potential node. When combined, they form the most powerful analytical instrument available to the investment intelligence system: a semantically rich, queryable, traversable, inference-capable graph of the investment universe.

Architects of Google Knowledge Graph, Palantir Foundry, Bloomberg's data platform, BlackRock's Aladdin system, and the W3C's Semantic Web all converge on the same foundational insight: **the value of a knowledge system scales exponentially with the richness of its typed relationships, not linearly with the size of its data.**

This section explains each conceptual component of that transition.

---

### 1 — Nodes (Entities as Graph Vertices)

Every entity defined in ENTITY_ONTOLOGY.md is a node in the knowledge graph. Nodes carry two things:
- **Identity:** A unique, permanent identifier (ISIN for securities, CIN for companies, SEBI registration number for intermediaries)
- **Attributes:** The information the entity holds about itself (price, ROE, sector, AUM, conviction score)

The knowledge graph contains nodes of every type simultaneously: companies, stocks, indices, indicators, hypotheses, decisions, knowledge items, events. The graph spans across all 12 entity groups defined in ENTITY_ONTOLOGY.md.

**Node Density:** A mature investment knowledge graph contains millions of nodes — every stock ever listed, every earnings event in 20 years, every hypothesis formed and resolved, every knowledge item validated.

---

### 2 — Edges (Relationships as Graph Edges)

Every relationship defined in this ontology is an edge in the knowledge graph. Edges carry:
- **Type:** Which of the 125 relationship types defined in Part III (structural, causal, statistical, reasoning, etc.)
- **Direction:** Source entity → Target entity
- **Attributes:** Strength/confidence, creation date, expiry date, mechanism, last confirmed, observation count, regime validity

The difference between a simple database and a knowledge graph is precisely the richness of the edges. A database stores: "Company: HDFC Bank, Sector: Private Banks." A knowledge graph stores: "HDFC Bank IS_A Private Bank (1:1 type relationship, permanent); HDFC Bank COMPETES_WITH ICICI Bank (dynamic, ρ_competitive ≈ 0.85); HDFC Bank CORRELATES_WITH NIFTY Bank Index (β ≈ 1.15, daily returns); HDFC Bank LEADS private sector credit growth by 1-2 quarters (validated 12 instances)."

**Edge Density:** The average node in an investment knowledge graph has 20-100 relationships. 100,000 nodes × 50 average relationships = 5 million edges.

---

### 3 — Semantic Meaning (Types as Inference Rules)

Semantic meaning is what distinguishes a knowledge graph from a property graph. In a mere property graph, edges are labeled but have no formal meaning beyond their label. In a knowledge graph, every edge type carries formal semantic implications:

- If A **ISSUES** B, then B's credit quality is a function of A's financial health
- If A **LEADS** B by 2 sessions, then observing A's directional change today generates a predictive signal for B in 2 sessions
- If A **SUPPORTS** hypothesis H, then A's staleness reduces H's conviction
- If A **CORRELATES_WITH** B (ρ = 0.8), then owning both A and B provides less diversification than expected from two "independent" positions

These semantic implications are encoded as inference rules — the system applies them automatically during graph traversal, producing derived knowledge that no explicit rule needed to produce.

**The semantic layer transforms queries from "give me data about X" to "reason about what is likely true about X given everything connected to it."**

---

### 4 — Inference (Following Relationships to New Knowledge)

Inference is the process of deriving new facts from existing facts + relationship types.

**Direct Inference (1 hop):**
- "A ISSUES B" → "B's issuer risk level = f(A's financial health)"
- "A LEADS B by 2 sessions" → "B will likely follow A's current move in 2 sessions"

**Transitive Inference (2+ hops):**
- "US Fed RAISES rate" → "DXY STRENGTHENS" → "FII SELLS India equities" → "NIFTY FALLS" — each step is a TRANSMITS_TO relationship traversal
- "Company X SUPPLIED_BY Chemical Company Y" + "Y faces regulation ban" → "X INPUT_COST likely rises" → "X MARGIN likely compresses"

**Inference by Rule:**
- "All entities of type REGULATED_BY SEBI must DISCLOSES quarterly shareholding" — applies to all instances of the REGULATED_BY relationship
- "Any entity that DEFAULTS_ON obligations TRIGGERS credit event for all bond HELD_BY portfolios"

**Inference by Analogy:**
- "Company A IS_ANALOGOUS_TO Company B" + "Company A's earnings pattern follows sector cycle with 2-quarter lead" → hypothesis that Company B also leads with similar timing

---

### 5 — Traversal (Following Paths Through the Graph)

Graph traversal is the process of following relationship paths from a starting entity to discover connected information.

**One-Hop Traversal:** "What relationships does HDFC Bank have?"
→ LISTED_ON NSE, BSE; REGULATED_BY RBI, SEBI; COMPETES_WITH ICICI Bank, Kotak Bank; CONSTITUENT_OF NIFTY 50, NIFTY Bank; HELD_BY SBI MF, LIC, Vanguard...

**Multi-Hop Traversal:** "Given Fed rate hike today, what Indian sectors are most affected?"
→ Fed Rate Hike → TRANSMITS_TO DXY Strength → TRANSMITS_TO INR Weakness → AFFECTS Export-oriented sectors (IT, Pharma) positively; AFFECTS Import-dependent sectors (Oil, Gold) negatively; TRANSMITS_TO FII selling pressure → AFFECTS High-FII-owned stocks more

**Pattern Traversal:** "Find all companies where: promoter is pledging shares AND debt/equity is rising AND revenue is slowing"
→ Graph traversal across OWNS, COLLATERALIZES, REPORTS (financial metrics) relationships — produces short-sale candidates

**Recommendation Traversal:** "Given hypothesis H has conviction 7.2, what is the chain of relationships that produced it?"
→ Conviction SYNTHESIZED_FROM Evidence Items E1, E2, E3, E4 → Each Ei DERIVED_FROM Observations → Each Observation MEASURES entity state → Full audit trail

---

### 6 — Neighborhood (Local Graph Context)

The neighborhood of an entity is the set of all entities connected to it within N hops. Neighborhood analysis reveals:

**1-hop neighborhood:** Direct relationships — the entity's immediate context
- Company HDFC Bank: sector, regulator, competitors, indices, instruments, auditor, rating

**2-hop neighborhood:** Second-order connections — what the direct connections connect to
- HDFC Bank → COMPETITOR (ICICI Bank) → ICICI Bank's financial metrics, rating, products
- HDFC Bank → SECTOR (Private Banks) → Sector performance, regulatory news, rate sensitivity

**3-hop neighborhood:** Macro context
- HDFC Bank → SECTOR → ECONOMY → Global macro conditions → Fed policy → DXY → FII flows → HDFC Bank stock price pressure

**The investment insight:** A company does not exist in isolation. Its investment outcome is determined by the network of relationships surrounding it — competitive, regulatory, macro, technical, sentiment. The neighborhood traversal reveals this context.

---

### 7 — Multi-Hop Reasoning (Investment Thesis Construction)

Multi-hop reasoning is the automated process of traversing the knowledge graph to construct or validate an investment thesis.

**Example: Constructing a bullish thesis on Indian IT sector**

Hop 1: Fed RAISES_RATE → dollar strengthens → DXY UP (TRANSMITS_TO)
Hop 2: DXY UP → USD/INR weakens → INR depreciates (CAUSES)
Hop 3: INR depreciation → IT companies with USD revenue → INR revenue goes UP (INFLUENCES)
Hop 4: INR revenue UP + stable USD costs → EBITDA margin expands (CAUSES)
Hop 5: Margin expansion → EPS upgrades → Analyst target price UP (TRIGGERS)
Hop 6: Target price UP + FII increasing India allocation → IT sector buying (INFLUENCES)
Hop 7: Technical: IT index at 52-week high breakout + high volume SUPPORTS bullish hypothesis

Each hop traverses a specific typed relationship. The entire chain is assembled automatically when the system observes the Fed rate hike. The result: a multi-source, multi-hop investment thesis — automatically constructed, with documented provenance.

**This is the transformative power of the knowledge graph: automatic reasoning along causal paths.**

---

### 8 — Graph Intelligence (Emergent Capabilities)

Graph intelligence refers to capabilities that emerge from the structure of the knowledge graph itself — capabilities that no individual data point or model could produce alone.

**Centrality Analysis:** Which entities have the most relationships? These are "systemic" entities — their stress propagates most broadly. NIFTY 50, HDFC Bank, RBI are high-centrality nodes. Their state changes matter more than average.

**Community Detection:** Which groups of entities are more densely connected to each other than to the broader graph? These communities represent "correlated risk clusters" — positions within the same community have higher correlation under stress.

**Path Analysis:** What is the shortest path between the US Fed and a mid-cap Indian auto stock? How many transmission hops? The longer the chain, the more attenuated the effect. The shorter, the more direct.

**Anomaly Detection:** When a relationship that should be strong (historically ρ = 0.8) suddenly weakens (ρ drops to 0.3), this is a structural anomaly. It may signal regime change, sector disruption, or data quality issues. Anomalies are detected by monitoring relationship properties over time.

**Network Resilience:** What is the minimum set of entities whose failure would disconnect major parts of the graph? These are the fragility points — where a small event can cascade into systemic impact.

---

### 9 — Context Propagation (How Context Flows Through Relationships)

Context propagation is the process by which the state or condition of one entity modifies the interpretation of all entities connected to it.

**Market Regime Propagation:** When the market regime changes from "trending" to "ranging," this context propagates through all APPLIES_IN relationships. Every strategy, signal, and evidence weight that is conditioned on regime must be updated. The regime context propagates through 1,000+ relationships simultaneously.

**Corporate Event Propagation:** When a company announces a large earnings miss, this propagates through:
- COMPETITOR entities → their relative attractiveness improves
- SECTOR → sector sentiment shifts
- HELD_BY portfolios → those positions face revaluation
- ANALYST entities → coverage models must be updated
- CORRELATED entities → correlated stocks face sympathy selling

**Macro Event Propagation:** A single central bank policy change propagates through:
- All BORROWING_COST relationships → lending rates
- All BOND entities → yield adjustments
- All EQUITY entities weighted by rate sensitivity
- All REAL ESTATE entities (leveraged assets)
- All CURRENCY entities
- All FII_FLOW entities

The knowledge graph enables modeling these propagations — not just the direct effect, but the second, third, and fourth-order effects through the relationship network.

---

### The Summary: Knowledge Graph as Investment Intelligence OS

The knowledge graph is not a database with relationships. It is a reasoning infrastructure.

| Layer | What It Does |
|---|---|
| **Nodes** (Entities) | Store what exists and its current state |
| **Edges** (Relationships) | Define how entities connect and information flows |
| **Types** (Semantics) | Define what connections mean |
| **Inference Rules** | Derive new knowledge from existing connections |
| **Traversal Engine** | Navigate paths to answer questions |
| **Context Propagation** | Update all connected interpretations on state change |
| **Temporal Layer** | Track how all of the above evolves through time |

Together, these layers constitute an investment intelligence operating system that is:
- **Self-describing** (knows what it knows)
- **Self-updating** (knows when its knowledge changes)
- **Self-reasoning** (can derive new knowledge from existing knowledge)
- **Self-explaining** (can trace any conclusion to its source relationships)

---

## PART IX — FUTURE EVOLUTION

*How the relationship ontology grows over the next decade without breaking compatibility.*

---

### Protocol for Adding New Relationship Types

When the investment universe evolves — new instruments, new market mechanisms, new analytical methods — new relationship types will be needed. Every new relationship type must follow this 9-step protocol before being used in any reasoning process:

**Step 1 — Natural Language Definition**
Write a precise, implementation-free definition in plain English. If the definition requires software or database concepts to articulate, it is not ready. The definition must clearly express what kind of connection exists between what kinds of entities and what semantic meaning the connection carries.

**Step 2 — Differentiation from Existing Types**
Demonstrate that the new type is genuinely different from all existing relationship types. If it is a specialization of an existing type, consider whether a condition on the existing type is sufficient. New types should not be created when an existing type with an added constraint would suffice.

**Step 3 — Inverse Definition**
Every new relationship type requires a defined inverse. Even if the inverse is rarely used, it must be formally named and defined.

**Step 4 — Cardinality Assignment**
Assign the cardinality class (1:1, 1:N, N:1, N:N, Recursive, etc.) from Part V.

**Step 5 — Taxonomy Classification**
Assign the new type to one or more taxonomy categories from Part IV.

**Step 6 — Examples Validation**
Provide at least 3 concrete examples of the relationship connecting real entities from ENTITY_ONTOLOGY.md. If 3 examples cannot be found, the relationship type may be premature.

**Step 7 — Compatibility Check**
Verify that no existing relationship instance will be misclassified as the new type, and that no existing reasoning path will be broken by the new type's introduction.

**Step 8 — Document Here First**
Update this ontology with the full definition before creating any instances of the new relationship in any system.

**Step 9 — Assign Permanent Identifier**
Assign the next sequential REL-XXX identifier. Identifiers are never reused even if a relationship type is deprecated.

---

### Anticipated Future Relationship Types (10-Year Horizon)

| Future Relationship | Trigger | Estimated Horizon |
|---|---|---|
| TOKENIZED_AS | Digital securities / CBDC introduction | 2-4 years |
| CARBON_CREDITS_FROM | ESG reporting mandates | 2-3 years |
| AI_GENERATED_BY | AI-authored research and signals | 1-2 years |
| ESG_SCORES | Formal ESG rating framework | 2-3 years |
| SUPPLY_CHAIN_LINK | Supply chain intelligence module | 3-5 years |
| REAL_ESTATE_EXPOSURE | Real estate investment trust mapping | 2-4 years |
| SOCIAL_SENTIMENT_OF | NLP-driven social intelligence | 1-2 years |
| ALTERNATIVE_DATA_FOR | Alternative data pipeline | 1-3 years |
| REGULATORY_CHANGE_AFFECTS | Regulatory intelligence module | 2-3 years |
| PEER_GROUP_BENCHMARKS | Enhanced peer analytics | 1-2 years |
| MANAGEMENT_QUALITY_OF | Governance intelligence | 3-5 years |
| GRAPH_SIMILARITY_TO | Entity graph embedding model | 3-4 years |

---

### Backward Compatibility Guarantees

When new relationship types are added, the following guarantees are maintained permanently:

1. **Existing relationship identifiers never change** — REL-001 through REL-125 always mean exactly what they mean today
2. **Existing inverse names are preserved** — renaming an inverse breaks all traversal paths using that inverse
3. **Existing cardinalities are never narrowed** — a 1:N relationship will never be changed to 1:1 (would invalidate existing instances)
4. **Existing taxonomy assignments are preserved** — entities may gain new classifications but not lose existing ones
5. **Existing examples remain valid** — if an example in this document becomes invalid, it signals a relationship definition change, which requires a major version revision
6. **Constitutional rules (Part VI) are never relaxed** — rules may be extended but not weakened

---

### Versioning the Ontology

The relationship ontology follows semantic versioning:
- **Major version (X.0):** Constitutional rule changes or fundamental redefinition of existing relationship types
- **Minor version (X.Y):** New relationship types added; no existing types modified
- **Patch version (X.Y.Z):** Clarifications, additional examples, documentation improvements to existing types

Current version: **1.0** — as of July 1, 2026

---

## RELATIONSHIP COUNT SUMMARY

| Category | Name | Relationship Types Defined |
|---|---|---|
| 1 | Structural | 12 |
| 2 | Ownership and Control | 12 |
| 3 | Issuance and Market Structure | 13 |
| 4 | Financial Activity | 16 |
| 5 | Organizational | 14 |
| 6 | Causal and Transmission | 16 |
| 7 | Temporal | 14 |
| 8 | Statistical and Quantitative | 13 |
| 9 | Knowledge Creation | 15 |
| 10 | Reasoning | 15 |
| 11 | Decision | 15 |
| 12 | Risk | 14 |
| 13 | Learning and Predictive | 12 |
| 14 | Information and Monitoring | 14 |
| 15 | Market Intelligence | 13 |
| 16 | Governance and Audit | 12 |
| 17 | Context and Scope | 9 |
| 18 | Semantic and Identity | 10 |
| 19 | Additional Specialized | 12 |
| **Total** | | **241 relationship types** |

*Including inverses, the full vocabulary exceeds 400 named relationship expressions.*

---

## DOCUMENT HISTORY

| Version | Date | Description |
|---------|------|-------------|
| 1.0 | 2026-07-01 | Initial authoritative relationship ontology — 241 relationship types across 19 categories, 125 fully defined with 16 attributes, complete cardinality framework, constitutional rules, evolution model, knowledge graph readiness framework |

---

*This document answers the question: "How can entities be connected?"*
*Every edge in the investment knowledge graph is named here.*
*Every relationship has a type. Every type has a direction. Every direction has meaning.*
*Before connecting two entities in any system, the relationship type must exist in this ontology.*
*Extend this document before creating any relationship type not already defined here.*
