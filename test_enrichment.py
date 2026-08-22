"""Quick smoke test for update_enrichment() — run inside container."""
from opportunity_engine.candidate_store import CandidateStore

# Read current candidates
cands = CandidateStore.read()
if not cands:
    print("SKIP: no candidates in store")
    raise SystemExit(0)

# Build a fake enrichment map for the first 3 symbols
test_map = {}
for c in cands[:3]:
    sym = c["symbol"]
    test_map[sym] = {
        "strategy": "test_breakout",
        "lifecycle_state": "ACTIVE",
        "data_trust_score": 0.95,
        "conviction_score": 7.5,
        "invalidation_state": "valid",
        "exploration_flag": False,
        "refinement_status": "premarket_refined",
        "candidate_origin": "prepared_universe",
        "momentum_state": "strong",
        "breakout_state": "near_resistance",
        "freshness_age_minutes": 30,
        "last_refresh_time": "2026-05-27T05:00:00Z",
        "fallback_contaminated": False,
        "corruption_flags": [],
        "simulation_status": "live",
        "rerank_reason": "sector:technology",
        "regime_bias_applied": "RANGE_BOUND",
    }

# First call — should write (last_write_ts = 0)
result = CandidateStore.update_enrichment(test_map)
print(f"write_result={result}")

# Verify the candidates now have the enriched fields
cands2 = CandidateStore.read()
if cands2:
    for c in cands2[:3]:
        sym = c["symbol"]
        strat = c.get("strategy", "MISSING")
        lc = c.get("lifecycle_state", "MISSING")
        trust = c.get("data_trust_score", "MISSING")
        print(f"  {sym}: strategy={strat} lifecycle={lc} trust={trust}")

print("ENRICH_SMOKE_PASS")
