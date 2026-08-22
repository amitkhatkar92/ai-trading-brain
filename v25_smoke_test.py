from opportunity_engine.delta_refresh_shadow import (
    run_shadow_audit,
    get_shadow_audit_summary,
    log_shadow_audit_summary,
    PRE_CYCLE_DELTA_REFRESH_SHADOW_MODE,
    _GATE_DECISION_DRIFT_PCT,
    _GATE_AVG_INVALIDATIONS,
    _GATE_TOP3_DRIFT_PCT,
    _GATE_AVG_RSI_DELTA,
    _GATE_RANK_INSTABILITY,
    _GATE_RUNTIME_MS,
    _kendall_tau_distance,
)
print("ALL IMPORTS OK")
print("SHADOW_MODE:", PRE_CYCLE_DELTA_REFRESH_SHADOW_MODE)

# Decision gate thresholds
print(f"Gates: drift>{_GATE_DECISION_DRIFT_PCT}% | inv>{_GATE_AVG_INVALIDATIONS} | top3>{_GATE_TOP3_DRIFT_PCT}% | rsi>{_GATE_AVG_RSI_DELTA}pts | instability<{_GATE_RANK_INSTABILITY} | ms<{_GATE_RUNTIME_MS}")

# Kendall tau tests
assert _kendall_tau_distance(["A","B","C"],["A","B","C"]) == 0.0, "identical should be 0"
assert _kendall_tau_distance(["A","B","C"],["C","B","A"]) == 1.0, "reversed should be 1"
assert 0 < _kendall_tau_distance(["A","B","C"],["A","C","B"]) < 1.0, "partial should be between 0-1"
print("kendall_tau: OK")

# Empty history returns minimal dict
summary = get_shadow_audit_summary()
assert summary.get("cycles_sampled") == 0
print("empty_summary: OK")

# run_shadow_audit fires without error on empty pool (no candidates file at test time)
import time
run_shadow_audit("TEST_SLOT")
time.sleep(0.3)   # let daemon thread complete
print("run_shadow_audit (empty pool): OK -- daemon thread completed")

# Confirm orchestrator hooks exist
from orchestrator.master_orchestrator import MasterOrchestrator
import inspect
src = inspect.getsource(MasterOrchestrator.run_full_cycle)
assert "delta_refresh_shadow" in src, "Missing run_full_cycle hook"
print("run_full_cycle hook: OK")

src_eod = inspect.getsource(MasterOrchestrator._do_eod_learning)
assert "log_shadow_audit_summary" in src_eod, "Missing EOD hook"
print("_do_eod_learning hook: OK")

print()
print("=" * 60)
print("ALL V2.5 SMOKE TESTS PASSED")
print("=" * 60)
