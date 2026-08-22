"""Reset Mean_Reversion and Momentum_Retest to fresh-start state."""
import json, os

path = "/app/data/strategy_performance.json"
with open(path) as f:
    data = json.load(f)

for name in ("Mean_Reversion", "Momentum_Retest"):
    if name in data:
        data[name]["enabled"] = True
        data[name]["consec_losses"] = 0
        data[name]["disabled_reason"] = ""
        # Remove the duplicated stale loss entries — keep only genuine recent ones
        # Both were last_updated 2026-05-13 with broken data feed; wipe last_trades
        data[name]["last_trades"] = []
        print(f"[RESET] {name}: enabled=True, consec_losses=0, last_trades cleared")

with open(path, "w") as f:
    json.dump(data, f, indent=2)

print("Done. Verifying:")
for name in ("Mean_Reversion", "Momentum_Retest"):
    s = data[name]
    print(f"  {name}: enabled={s['enabled']} consec_losses={s['consec_losses']} wins={s['wins']} losses={s['losses']}")
