"""Fix StrategyStats unknown-field error on load (official_trades schema drift)."""
import sys

FILE = "/app/learning_system/strategy_performance_tracker.py"
with open(FILE, "r") as f:
    src = f.read()

OLD = '''    def _load(self) -> None:
        if not os.path.exists(PERF_FILE):
            return
        try:
            with open(PERF_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            for name, raw in data.items():
                # Drop computed properties if they were accidentally serialised
                for computed in ("win_rate", "avg_r", "avg_win_r", "avg_loss_r", "expectancy"):
                    raw.pop(computed, None)
                self._stats[name] = StrategyStats(**raw)
        except Exception as exc:
            log.warning("[PerfTracker] Load failed: %s", exc)'''

NEW = '''    def _load(self) -> None:
        if not os.path.exists(PERF_FILE):
            return
        try:
            import dataclasses as _dc
            _valid_fields = {f.name for f in _dc.fields(StrategyStats)}
            with open(PERF_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            for name, raw in data.items():
                # Drop computed properties and any unknown fields (schema drift)
                for computed in ("win_rate", "avg_r", "avg_win_r", "avg_loss_r", "expectancy"):
                    raw.pop(computed, None)
                raw = {k: v for k, v in raw.items() if k in _valid_fields}
                self._stats[name] = StrategyStats(**raw)
        except Exception as exc:
            log.warning("[PerfTracker] Load failed: %s", exc)'''

if OLD not in src:
    print("ERROR: anchor not found"); sys.exit(1)

src = src.replace(OLD, NEW, 1)
with open(FILE, "w") as f:
    f.write(src)

import py_compile
py_compile.compile(FILE, doraise=True)
print("OK: StrategyStats schema-drift fix applied and syntax verified")
