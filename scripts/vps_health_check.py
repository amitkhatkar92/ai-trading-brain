import sys
sys.path.insert(0, '/app')

from learning_system.strategy_performance_tracker import (
    get_performance_tracker, get_stability_ledger, MIN_SAMPLE
)

t = get_performance_tracker()
s = get_stability_ledger()

print("=== StabilityLedger ===")
print(f"  streak        : {s.streak}/{s.required}")
print(f"  confirmed     : {s.is_confirmed()}")
print(f"  last_session  : {s._last_session_date}")
print(f"  summary       : {s.status_summary()}")
print()

print("=== StrategyStats ===")
for name, st in sorted(t.get_all_stats().items()):
    w = t.get_performance_weight(name)
    flag = " ← NEUTRAL (below MIN_SAMPLE)" if st.official_trades < MIN_SAMPLE else ""
    print(f"  {name}")
    print(f"    official_trades={st.official_trades}  total_trades={st.total_trades}  perf_weight={w:.2f}x{flag}")
    print(f"    enabled={st.enabled}  wins={st.wins}  losses={st.losses}")
print()
print(f"MIN_SAMPLE={MIN_SAMPLE}")
