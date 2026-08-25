"""Temporary DTA-LIVE-006 LOL audit script — runs inside container."""
import json
from collections import Counter
from pathlib import Path

lol_path = Path("/app/data/lol/LOL_2026-08-25.jsonl")
data = [json.loads(l) for l in lol_path.read_text().splitlines() if l.strip()]
recs = {}
for r in data:
    oid = r.get("observation_id")
    if oid:
        recs[oid] = r
canonical = list(recs.values())

states = Counter(r.get("lifecycle_state") for r in canonical)
kda_dec = Counter(r.get("kda_decision") for r in canonical)
strat = Counter(r.get("strategy_decision") for r in canonical)
recovery = Counter(r.get("recovery_source") for r in canonical)
no_look = Counter(r.get("no_lookahead") for r in canonical)
block = Counter(r.get("block_reason") for r in canonical)

print("total_unique:", len(canonical))
print("total_lines:", len(data))
print("by_state:", dict(states))
print("by_kda_decision:", dict(kda_dec))
print("by_strategy_decision:", dict(strat))
print("by_recovery_source:", dict(recovery))
print("by_no_lookahead:", dict(no_look))
print("by_block_reason:", dict(block))

# Show first 3 live cycle records (no recovery_source)
live = [r for r in canonical if not r.get("recovery_source")][:3]
for r in live:
    print("LIVE_RECORD:", json.dumps({
        k: r.get(k) for k in [
            "symbol", "lifecycle_state", "kda_decision", "kda_evidence_state",
            "strategy_decision", "block_reason", "trading_date", "no_lookahead",
            "authorization_source", "outcome_class",
        ]
    }))

# Check no_lookahead violations
violations = [r for r in canonical if r.get("no_lookahead") is not True]
print("no_lookahead_violations:", len(violations))

# Check outcome_at vs decision_at ordering
time_violations = 0
for r in canonical:
    oa = r.get("outcome_at")
    da = r.get("decision_at")
    if oa and da and oa <= da:
        time_violations += 1
print("outcome_before_decision_violations:", time_violations)

# Check trading_date correctness
wrong_date = [r for r in canonical if r.get("trading_date") != "2026-08-25"]
print("wrong_trading_date:", len(wrong_date))
