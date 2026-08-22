import sys, os
sys.path.insert(0, '/app')

print('=== DEPLOYED FILE SIZES ===')
files = [
    '/app/data_feeds/angelone_feed.py',
    '/app/data_feeds/data_feed_manager.py',
    '/app/data_feeds/options_feed.py',
    '/app/opportunity_engine/equity_scanner_ai.py',
    '/app/opportunity_engine/candidate_store.py',
    '/app/opportunity_engine/filter_funnel_audit.py',
    '/app/utils/scalar_audit.py',
    '/app/utils/safe_scalar.py',
]
for f in files:
    sz = os.path.getsize(f)
    print(f'  {os.path.basename(f)}: {sz:,} bytes')

print()
print('=== PATCH MARKERS ===')
checks = [
    ('/app/data_feeds/angelone_feed.py',           '_last_reconnect_attempt',                      'AngelOne: reconnect attr'),
    ('/app/data_feeds/angelone_feed.py',           '5-minute backoff',                             'AngelOne: 5-min backoff'),
    ('/app/data_feeds/data_feed_manager.py',       'Do NOT gate on is_live',                       'FeedMgr: no is_live gate'),
    ('/app/data_feeds/options_feed.py',            'Do NOT gate on is_live',                       'OptionsFeed: no is_live gate'),
    ('/app/opportunity_engine/candidate_store.py', 'stamp each candidate with prepared_at',        'CandidateStore: prepared_at stamp'),
    ('/app/opportunity_engine/candidate_store.py', 'populated by write() with prepared_at',        'CandidateStore: last_refresh_time comment'),
    ('/app/opportunity_engine/equity_scanner_ai.py','freshness_age_minutes_fixed_computed_from',   'Scanner: freshness fix note'),
]
all_ok = True
for fpath, marker, label in checks:
    try:
        found = marker in open(fpath, encoding='utf-8').read()
    except Exception as e:
        found = False
    status = 'OK' if found else 'MISSING'
    if not found:
        all_ok = False
    print(f'  [{status}] {label}')

print()
print('=== FEED STATUS ===')
from data_feeds.data_feed_manager import get_feed_manager
fm = get_feed_manager()
ao = fm.angelone
print(f'  AngelOne is_live: {ao.is_live}')
print(f'  Dhan     is_live: {fm.dhan.is_live}')
yahoo_feed = getattr(fm, 'yahoo', None) or getattr(fm, 'yfinance', None) or getattr(fm, 'yahoo_feed', None)
print(f'  Yahoo    is_live: {getattr(yahoo_feed, "is_live", "N/A")}')

print()
print('=== CANDIDATE STORE ===')
from opportunity_engine.candidate_store import CandidateStore
cs = CandidateStore()
candidates = cs.read()
print(f'  Candidates in store: {len(candidates)}')
if candidates:
    c0 = candidates[0]
    print(f'  Sample [{c0.get("symbol")}]: prepared_at={c0.get("prepared_at","-")} freshness_age_minutes={c0.get("freshness_age_minutes","-")} last_refresh_time={c0.get("last_refresh_time","-")}')
    zero_age = sum(1 for c in candidates if c.get('freshness_age_minutes', 0) == 0)
    print(f'  Candidates with age=0: {zero_age}/{len(candidates)} ({100*zero_age//len(candidates)}%)')

print()
print('=== TOKEN / SESSION ===')
import subprocess, json
r = subprocess.run(['cat', '/app/.env'], capture_output=True, text=True)
env_lines = [l for l in r.stdout.splitlines() if 'DHAN_TOKEN' in l or 'ACTIVE_BROKER' in l or 'ANGELONE' in l and 'SECRET' not in l and 'PASSWORD' not in l]
for l in env_lines:
    print(f'  {l[:80]}')

print()
if all_ok:
    print('ALL PATCHES VERIFIED OK')
else:
    print('WARNING: SOME PATCHES MISSING')
