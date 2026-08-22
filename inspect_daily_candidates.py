import json, sys, pathlib

path = pathlib.Path('/app/data/daily_candidates.json')
if not path.exists():
    print('NOT FOUND: daily_candidates.json')
    sys.exit(1)

data = json.loads(path.read_text())
print('=== DAILY CANDIDATES STORE ===')
print('Top-level keys:', sorted(data.keys()))
print()

# Metadata
for k in ['generated_at', 'coverage_pct', 'regime', 'symbols_attempted',
          'symbols_successful', 'fallback_used', 'safe_mode', 'premarket_complete',
          'sector_cap_applied', 'exploration_budget_pct', 'store_age_h']:
    if k in data:
        print(f'{k}: {data[k]}')

print()
cands = data.get('candidates', [])
print(f'Total candidates: {len(cands)}')
if cands:
    print(f'Fields per candidate: {sorted(cands[0].keys())}')
    print()
    print('--- SAMPLE CANDIDATES (first 10) ---')
    for c in cands[:10]:
        print('  symbol={:<14} sector={:<16} rsi={:<5} atr={:<8} vol_ratio={:<6} score={}'.format(
            c.get('symbol','?'),
            c.get('sector','?'),
            c.get('rsi','?'),
            c.get('atr','?'),
            c.get('volume_ratio', c.get('vol_ratio','?')),
            c.get('score', c.get('rank','?')),
        ))
    print()
    # Sector distribution
    from collections import Counter
    sectors = Counter(c.get('sector','UNKNOWN') for c in cands)
    print('--- SECTOR DISTRIBUTION ---')
    for sector, cnt in sorted(sectors.items(), key=lambda x: -x[1]):
        print(f'  {sector:<20}: {cnt}')
    print()
    # RSI spread
    rsi_vals = [c.get('rsi') for c in cands if c.get('rsi') is not None]
    if rsi_vals:
        print(f'RSI range: min={min(rsi_vals):.1f}  max={max(rsi_vals):.1f}  mean={sum(rsi_vals)/len(rsi_vals):.1f}')
    vol_vals = [c.get('volume_ratio', c.get('vol_ratio')) for c in cands if c.get('volume_ratio', c.get('vol_ratio')) is not None]
    if vol_vals:
        print(f'VolRatio range: min={min(vol_vals):.2f}  max={max(vol_vals):.2f}  mean={sum(vol_vals)/len(vol_vals):.2f}')

# Check for expiry info
expired = data.get('expired_count', 'N/A')
print(f'\nExpired candidates: {expired}')
