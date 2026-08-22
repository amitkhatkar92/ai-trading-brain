import json
raw = open('/app/data/daily_candidates.json').read()
d = json.loads(raw)
cands = d.get('candidates', [])
print('TOTAL_CANDS:', len(cands))
if cands:
    c0 = cands[0]
    print('KEYS_FIRST:', sorted(c0.keys()))
    print('---')
    for k in ['strategy','lifecycle_state','data_trust_score','conviction_score',
              'invalidation_state','exploration_flag','refinement_status',
              'momentum_state','breakout_state','candidate_origin',
              'freshness_age_minutes','fallback_contaminated','corruption_flags',
              'simulation_status','rerank_reason','regime_bias_applied']:
        print(f'{k}: {c0.get(k, "MISSING")}')
print('---')
print('strategy_dist:', {str(c.get("strategy","None")) for c in cands})
print('lc_dist:', {str(c.get("lifecycle_state","None")) for c in cands})
print('trust_sample:', [c.get('data_trust_score') for c in cands[:5]])
