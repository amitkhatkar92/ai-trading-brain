import json
with open('/app/data/daily_candidates.json') as f:
    d = json.load(f)
if d.get('candidates'):
    c = d['candidates'][0]
    print("KEYS:", list(c.keys()))
    print("scanned_at:", c.get('scanned_at'))
    print("prepared_at:", c.get('prepared_at'))
    print("freshness_age_minutes:", c.get('freshness_age_minutes'))
    print("valid_until_utc:", c.get('valid_until_utc'))
print("scanner_stats:", d.get('scanner_stats'))
print("scan_ts:", d.get('scan_ts'))
