# Decision Optimization Framework

**C9 Decision Intelligence — Phase 1, Module 4**

The Decision Optimization Framework selects the **optimal institutional decision** from a set of policy-approved candidates. It uses multi-objective optimization, configurable constraints, priorities, and pluggable optimization strategies.

---

## Responsibilities

| Does | Does NOT |
|---|---|
| Evaluate, score, rank, and select candidate decisions | Evaluate institutional policies |
| Apply configurable objectives and constraints | Execute trades or place orders |
| Support multiple optimization strategies | Modify portfolios |
| Track runtime statistics and history | Communicate with brokers |
| Bridge to the M2 OptimizationFrameworkProtocol | Generate or approve decisions |

---

## Package layout

```
iios/decision/optimization/
├── __init__.py                         ← full public API
├── constants.py                        ← enums, defaults, actor labels
├── exceptions.py                       ← DO-000 … DO-009
│
├── decision_candidate.py               ← DecisionCandidate, CandidateScore
├── decision_objective.py               ← DecisionObjective
├── decision_constraint.py              ← DecisionConstraint, ConstraintEvaluationResult
├── decision_optimization_context.py    ← DecisionOptimizationContext
├── decision_optimization_strategy.py  ← DecisionOptimizationStrategy
├── decision_optimization_request.py   ← DecisionOptimizationRequest
├── decision_optimization_response.py  ← DecisionOptimizationResponse, Summary, Report
├── decision_solution.py               ← DecisionSolution
│
├── decision_candidate_registry.py     ← thread-safe candidate store
├── decision_constraint_engine.py      ← evaluates constraints per candidate
├── decision_scoring_engine.py         ← cross-candidate min-max scoring
├── decision_ranking_engine.py         ← ranks scored candidates
├── decision_priority_engine.py        ← priority-based selection helper
├── decision_solution_selector.py      ← dispatches to strategy-specific selection
├── decision_solution_validator.py     ← 7-check structural validation
├── decision_optimizer.py              ← full pipeline: constraint→score→rank→select
│
├── decision_optimization_registry.py  ← objectives + constraints registry
├── decision_strategy_registry.py      ← optimization strategy registry
│
├── decision_optimization_events.py    ← event value objects + 8 factory functions
├── decision_optimization_statistics.py← thread-safe runtime counters
├── decision_optimization_history.py   ← bounded event + response history
├── decision_optimization_factory.py   ← stateless object factory
│
├── decision_optimization_manager.py   ← orchestrates the full workflow
└── decision_optimization_engine.py    ← primary public interface + M2 adapter
```

---

## Quick start

```python
from iios.decision.optimization import (
    DecisionOptimizationEngine,
    DecisionOptimizationFactory,
    OptimizationObjectiveType,
    ConstraintType,
    ConstraintOperator,
)

# 1. Build and start the engine
engine = DecisionOptimizationEngine()
engine.start()

fac = engine.factory()

# 2. Register objectives and constraints
engine.register_objective(fac.create_objective(
    "Maximise Return", OptimizationObjectiveType.MAXIMIZE_EXPECTED_RETURN, weight=2.0
))
engine.register_constraint(fac.create_constraint(
    "Max Risk", ConstraintType.RISK, ConstraintOperator.LTE, "risk_score", 0.6
))

# 3. Create candidates (policy-approved by M3)
candidates = [
    fac.create_candidate("RELIANCE", "buy", 10, 2500.0,
                         expected_return=0.08, risk_score=0.3, confidence=0.85),
    fac.create_candidate("INFY",     "buy",  5, 1500.0,
                         expected_return=0.05, risk_score=0.4, confidence=0.70),
]

# 4. Optimize
ctx = fac.create_context(decision_id="dec-001")
req = fac.create_request(ctx, candidates)
response = engine.optimize(req)

if response.is_success:
    print(response.solution.selected_candidate.symbol)   # RELIANCE
    print(f"Score: {response.solution.final_score:.3f}")

engine.stop()
```

---

## M2 Bridge

`OptimizationFrameworkAdapter` implements the M2 `OptimizationFrameworkProtocol`
so the engine can be injected directly into the `DecisionDispatcher`:

```python
from iios.decision.optimization import DecisionOptimizationEngine, OptimizationFrameworkAdapter

engine  = DecisionOptimizationEngine()
engine.start()
adapter = OptimizationFrameworkAdapter(engine)

# M2 signature:
result = adapter.optimize(m2_context, policy_result, inputs={"candidates": [...]})
# result is a plain dict with: selected_candidate_id, final_score, is_optimal,
# is_feasible, is_success, rationale, candidates_evaluated, optimization_strategy,
# error, response_id
```

---

## Optimization strategies

| Strategy | Class | Description |
|---|---|---|
| `WEIGHTED_SCORE` (default) | `DecisionOptimizationStrategy.weighted_score()` | Rank by confidence-adjusted weighted score |
| `PRIORITY_BASED` | `.priority_based()` | Sort by `confidence × max(expected_return, 0)` |
| `CONSTRAINT_SATISFACTION` | manual | First feasible candidate by confidence |
| `RULE_BASED` | manual | Same as weighted score |
| `MULTI_OBJECTIVE` | manual | Sort by raw final_score |
| `PARETO_RANKING` | `.pareto_ranking()` | Non-dominated Pareto front |
| `LEXICOGRAPHIC` | manual | Lex sort on per-objective scores descending |
| `CUSTOM` | manual | User-supplied callable |

---

## Objective types

| Type | Direction | Default field |
|---|---|---|
| `MAXIMIZE_EXPECTED_RETURN` | ↑ | `expected_return` |
| `MINIMIZE_RISK` | ↓ | `risk_score` |
| `MAXIMIZE_RISK_ADJUSTED_RETURN` | ↑ | `risk_adjusted_return` |
| `MINIMIZE_DRAWDOWN` | ↓ | `drawdown_estimate` |
| `MAXIMIZE_CAPITAL_EFFICIENCY` | ↑ | `capital_efficiency` |
| `MINIMIZE_EXECUTION_COST` | ↓ | `execution_cost` |
| `MINIMIZE_PORTFOLIO_EXPOSURE` | ↓ | `portfolio_exposure` |
| `MAXIMIZE_LIQUIDITY` | ↑ | `liquidity_score` |
| `MAXIMIZE_OPERATIONAL_STABILITY` | ↑ | `operational_stability` |
| `MAXIMIZE_POLICY_COMPLIANCE` | ↑ | `policy_compliance_score` |

---

## Constraint operators

`LT`, `LTE`, `GT`, `GTE`, `EQ`, `BETWEEN`, `EXISTS`, `NOT_EXISTS`

Hard constraints (`is_hard=True`, default) render candidates **infeasible** when violated.  
Soft constraints contribute a `penalty` to the score but do not disqualify.

---

## Error codes

| Code | Exception |
|---|---|
| DO-000 | `DecisionOptimizationError` (base) |
| DO-001 | `OptimizationEngineNotRunningError` |
| DO-002 | `NoCandidatesError` |
| DO-003 | `NoFeasibleSolutionError` |
| DO-004 | `ObjectiveNotFoundError` |
| DO-005 | `ConstraintNotFoundError` |
| DO-006 | `StrategyNotFoundError` |
| DO-007 | `OptimizationValidationError` |
| DO-008 | `CandidateRegistryError` |
| DO-009 | `OptimizationConfigurationError` |

---

## Tests

```
tests/unit/decision/optimization/test_optimization.py   195 tests
```

Run:

```powershell
.venv\Scripts\python.exe -m pytest tests/unit/decision/optimization/ -q
```
