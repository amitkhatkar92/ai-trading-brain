import json, pathlib, datetime

path = pathlib.Path('/app/data/daily_candidates.json')
data = json.loads(path.read_text())

print('=== PREPARED STORE METADATA ===')
print('prepared_at:      ', data.get('prepared_at'))
print('premarket_complete:', data.get('premarket_refresh_complete'))
print('premarket_at:     ', data.get('premarket_refreshed_at'))
print('schema_version:   ', data.get('schema_version'))
print('timezone:         ', data.get('timezone'))
print()

ctx = data.get('context', {})
print('=== CONTEXT (regime/market at prep time) ===')
for k, v in ctx.items():
    print(f'  {k}: {v}')
print()

stats = data.get('scanner_stats', {})
print('=== SCANNER STATS ===')
for k, v in sorted(stats.items()):
    print(f'  {k}: {v}')
print()

# Candidate validity
cands = data.get('candidates', [])
now_utc = datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc)
expired = []
valid = []
for c in cands:
    vu = c.get('valid_until_utc')
    if vu:
        try:
            exp = datetime.datetime.fromisoformat(vu.replace('Z','+00:00'))
            if exp < now_utc:
                expired.append(c['symbol'])
            else:
                valid.append((c['symbol'], (exp - now_utc).total_seconds()/3600))
        except Exception:
            valid.append((c['symbol'], 999))

print(f'=== CANDIDATE VALIDITY (as of now UTC={now_utc.strftime("%H:%M")}) ===')
print(f'  Valid:   {len(valid)}')
print(f'  Expired: {len(expired)}')
print(f'  Expired symbols: {expired[:20]}')
if valid:
    soonest = sorted(valid, key=lambda x: x[1])
    print(f'  Soonest expiry: {soonest[0]}')
    print(f'  Latest expiry:  {soonest[-1]}')
print()

# Support/resistance spot check
print('=== SUPPORT/RESISTANCE SPOT CHECK (5 samples) ===')
for c in cands[:5]:
    print('  {} support={} resistance={} base_ltp={} buckets_count={}'.format(
        c.get('symbol'),
        c.get('support'),
        c.get('resistance'),
        c.get('base_ltp'),
        len(c.get('buckets', [])) if isinstance(c.get('buckets'), list) else c.get('buckets','?'),
    ))

# ATR check
print()
print('=== ATR CHECK ===')
for c in cands[:5]:
    print('  {} atr14={} atr_anchored={} atr_pct={}'.format(
        c.get('symbol'),
        c.get('atr14','?'),
        c.get('atr_anchored','?'),
        c.get('atr_pct','?'),
    ))
