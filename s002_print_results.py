import json

with open('data/study002_results.json') as f:
    r = json.load(f)

print('=== REGIME ===')
for k, v in r['stage1_regime'].items():
    if v.get('sessions', 0) > 0:
        print(f"  {k}: sessions={v['sessions']} signals={v['signals']} "
              f"signal_rate={v.get('signal_rate',0):.2f} dominant={v.get('dominant_sector','-')}")

print('\n=== SIGNALS ===')
s = r['stage2_signals_opps']
print(f"  total_signals={s['total_signals']}  total_opps={s['total_opportunities']}  closed={s['closed_opportunities']}")
print('  by_archetype:')
for k, v in s['by_archetype'].items():
    print(f"    {k}: {v}")
print('  by_state:', s['by_state'])
print('  by_direction:', s['by_direction'])
print('  by_regime_signals:', s['by_regime_signals'])

print('\n=== SECTORS ===')
sec = r['stage3_sectors']
print(f"  peak_conviction={sec['peak_conviction']}")
print(f"  most_active_signal_sector={sec['most_active_signal_sector']}")
print(f"  total_full_rows={sec['total_full_conviction_rows']}")
print('  signals_by_sector:')
for k, v in sorted(sec.get('signals_by_sector', {}).items(), key=lambda x: -x[1]):
    print(f"    {k}: {v}")
print('  sector details:')
for k, v in sorted(sec.get('by_sector', {}).items(), key=lambda x: -x[1].get('avg_conviction', 0)):
    print(f"    {k}: avg={v['avg_conviction']:.3f}  peak={v['peak_conviction']:.3f} on {v['peak_date']}  rows={v['full_rows']}")

print('\n=== FEATURES ===')
f4 = r['stage4_features']
print(f"  before={f4['feat_before']}  after={f4['feat_after']}  added={f4['feat_added']}")
print(f"  positive_rate={f4['positive_rate']}  symbols={f4['symbols_enriched']}  dates={f4['dates_covered']}")
print(f"  regime_dist={f4['regime_distribution']}")
print(f"  positive_labels={f4['positive_labels']}  negative_labels={f4['negative_labels']}")

print('\n=== EDE ===')
e = r['stage5_ede']
print(f"  edges: {e['edges_before']} -> {e['edges_after']}  new={e['new_edges']}")
print(f"  updated_edges={e['updated_edges']}")
print(f"  status_after={e['edges_by_status_after']}")
print(f"  strats: {e['strats_before']} -> {e['strats_after']}  new={e['new_strats']}")
print(f"  final_regime={e['final_regime']}  snapshot_date={e['snapshot_date']}")

print('\n=== METAMODEL ===')
m = r['stage6_metamodel']
print(f"  trained={m['model_trained']}  records={m['ml_records']}")
print(f"  reason={m['reason_not_trained']}")

print('\n=== KNOWLEDGE STORE DELTAS ===')
v = r['stage7_verify']
print('  baseline:', v['baseline'])
print('  final:', v['final'])
print(f"  deltas: feat={v['feat_delta']}  labeled={v['feat_labeled_delta']}  edges={v['edges_delta']}  strats={v['strats_delta']}")

print('\n=== OHLCV COVERAGE ===')
o = r['ohlcv_coverage']
print(f"  trading_dates={o['trading_dates']}  symbols={o['symbols']}  total_rows={o['total_rows']}")

print('\n=== TIMING ===')
print(f"  elapsed_s={r['elapsed_s']}")
print(f"  date_range={r['date_range']}")
print(f"  regime_map_summary={r['regime_map_summary']}")
