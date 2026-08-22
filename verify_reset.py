import sys
sys.path.insert(0, "/app")
from learning_system.strategy_performance_tracker import get_performance_tracker
t = get_performance_tracker()
for n, s in t._stats.items():
    print(f"{n}: enabled={s.enabled} consec_losses={s.consec_losses}")
