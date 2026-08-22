#!/usr/bin/env python3
"""
forensic_universe_audit.py
Comprehensive forensic audit of universe + candidate refresh quality.
Run inside Docker: docker exec ai-trading-brain python3 /tmp/forensic_universe_audit.py
"""
import json
import os
import time
import sys
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, '/app')

DATA_DIR = Path('/app/data')
NOW      = time.time()
NOW_DT   = datetime.now()

def _age_min(ts):
    """Return age in minutes from epoch or ISO string."""
    if ts is None:
        return None
    if isinstance(ts, (int, float)):
        return round((NOW - ts) / 60, 1)
    try:
        dt = datetime.fromisoformat(str(ts).replace('Z', '+00:00'))
        return round((NOW_DT - dt.replace(tzinfo=None)).total_seconds() / 60, 1)
    except Exception:
        return None

def _age_str(ts):
    a = _age_min(ts)
    if a is None:
        return 'unknown'
    if a < 60:
        return f'{a:.0f}min'
    return f'{a/60:.1f}h'

SEP = '=' * 72

# ─── 1. UNIVERSE FILE ──────────────────────────────────────────────────────
print(f'\n{SEP}')
print('1. NIFTY-500 UNIVERSE FILE')
print(SEP)

uf = DATA_DIR / 'nifty500_universe.json'
if uf.exists():
    mtime = uf.stat().st_mtime
    age_h = (NOW - mtime) / 3600
    raw   = json.loads(uf.read_text(encoding='utf-8'))
    syms  = raw if isinstance(raw, list) else raw.get('symbols', raw.get('universe', []))
    print(f'File          : {uf}')
    print(f'Last modified : {datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S IST")}')
    print(f'Age           : {age_h:.1f} h ({age_h/24:.1f} days)')
    print(f'Symbol count  : {len(syms)}')
    if syms:
        if isinstance(syms[0], dict):
            print(f'Schema keys   : {list(syms[0].keys())}')
            sectors = {}
            for s in syms:
                sec = s.get('sector', 'UNKNOWN')
                sectors[sec] = sectors.get(sec, 0) + 1
            top_sec = sorted(sectors.items(), key=lambda x: -x[1])[:8]
            print(f'Sectors       : {top_sec}')
        else:
            print(f'First 5       : {syms[:5]}')
else:
    print('FILE NOT FOUND — universe may not exist yet')

# ─── 2. DAILY CANDIDATES FILE ──────────────────────────────────────────────
print(f'\n{SEP}')
print('2. DAILY CANDIDATES FILE  (daily_candidates.json)')
print(SEP)

cf = DATA_DIR / 'daily_candidates.json'
if cf.exists():
    mtime_c = cf.stat().st_mtime
    age_c_h = (NOW - mtime_c) / 3600
    raw_c   = json.loads(cf.read_text(encoding='utf-8'))
    cands   = raw_c.get('candidates', raw_c if isinstance(raw_c, list) else [])
    stats   = raw_c.get('scanner_stats', {})

    print(f'File          : {cf}')
    print(f'Last modified : {datetime.fromtimestamp(mtime_c).strftime("%Y-%m-%d %H:%M:%S IST")}')
    print(f'Age           : {age_c_h:.1f} h ({age_c_h/24:.1f} days)')
    print(f'Candidate cnt : {len(cands)}')
    print(f'Schema version: {raw_c.get("schema_version", "N/A")}')
    print(f'Scanner stats : {stats}')
    if cands:
        print(f'Sample keys   : {list(cands[0].keys())}')
else:
    print('FILE NOT FOUND')
    cands = []

# ─── 3. PER-CANDIDATE FRESHNESS TABLE ──────────────────────────────────────
print(f'\n{SEP}')
print('3. PER-CANDIDATE FRESHNESS TABLE')
print(SEP)

if cands:
    header = f"{'Symbol':<14} {'Score':>6} {'Strategy':<25} {'PreparedAt':<20} {'LastRefresh':<20} {'Age':>7} {'State':<14} {'LTP':>8}"
    print(header)
    print('-' * len(header))

    stale_1h   = []
    stale_4h   = []
    stale_1day = []
    state_counts = {}

    for c in sorted(cands, key=lambda x: -x.get('score', 0)):
        sym      = c.get('symbol', '?')
        score    = c.get('score', 0)
        strat    = (c.get('strategy') or c.get('pattern') or '?')[:24]
        prep_at  = c.get('prepared_at') or c.get('scan_time') or c.get('timestamp')
        refresh  = c.get('last_refresh_time') or c.get('last_refresh') or c.get('refreshed_at') or prep_at
        ltp      = c.get('base_ltp') or c.get('ltp') or 0
        state    = c.get('lifecycle_state') or c.get('status') or 'PREPARED'

        age_m    = _age_min(prep_at)
        age_disp = _age_str(prep_at)
        ref_disp = _age_str(refresh) if refresh else '—'

        state_counts[state] = state_counts.get(state, 0) + 1

        prep_str = ''
        if prep_at:
            try:
                if isinstance(prep_at, (int, float)):
                    prep_str = datetime.fromtimestamp(prep_at).strftime('%m-%d %H:%M')
                else:
                    prep_str = str(prep_at)[:16]
            except Exception:
                prep_str = str(prep_at)[:16]

        ref_str = ''
        if refresh and refresh != prep_at:
            try:
                if isinstance(refresh, (int, float)):
                    ref_str = datetime.fromtimestamp(refresh).strftime('%m-%d %H:%M')
                else:
                    ref_str = str(refresh)[:16]
            except Exception:
                ref_str = str(refresh)[:16]
        else:
            ref_str = '—'

        print(f'{sym:<14} {score:>6.3f} {strat:<25} {prep_str:<20} {ref_str:<20} {age_disp:>7} {state:<14} {ltp:>8.1f}')

        if age_m is not None:
            if age_m > 24 * 60:
                stale_1day.append(sym)
            elif age_m > 4 * 60:
                stale_4h.append(sym)
            elif age_m > 60:
                stale_1h.append(sym)

    print(f'\nLifecycle state distribution: {state_counts}')
    print(f'Stale >1h    : {stale_1h}')
    print(f'Stale >4h    : {stale_4h}')
    print(f'Stale >1 day : {stale_1day}')

# ─── 4. CANDIDATE STORE FILE (secondary store) ─────────────────────────────
print(f'\n{SEP}')
print('4. CANDIDATE STORE FILE  (candidate_store.json or similar)')
print(SEP)

for store_name in ['candidate_store.json', 'prepared_candidates.json', 'candidates_store.json']:
    sf = DATA_DIR / store_name
    if sf.exists():
        mtime_s = sf.stat().st_mtime
        raw_s   = json.loads(sf.read_text(encoding='utf-8'))
        cands_s = raw_s.get('candidates', raw_s if isinstance(raw_s, list) else [])
        print(f'Found: {store_name}  age={_age_str(mtime_s)}  count={len(cands_s)}')
        if cands_s:
            print(f'  Keys: {list(cands_s[0].keys())[:12]}')
        break
else:
    print('No secondary candidate store found.')

# ─── 5. VALID-UNTIL EXPIRY ANALYSIS ───────────────────────────────────────
print(f'\n{SEP}')
print('5. VALID-UNTIL / EXPIRY ANALYSIS')
print(SEP)

if cands:
    expired     = []
    expiring_1h = []
    valid       = []
    no_expiry   = []

    for c in cands:
        sym     = c.get('symbol', '?')
        vu      = c.get('valid_until_utc') or c.get('valid_until') or c.get('expires_at')
        if vu is None:
            no_expiry.append(sym)
            continue
        age_min = _age_min(vu)
        if age_min is None:
            no_expiry.append(sym)
        elif age_min > 0:
            expired.append((sym, f'{age_min:.0f}min ago'))
        elif age_min > -60:
            expiring_1h.append((sym, f'{-age_min:.0f}min remaining'))
        else:
            valid.append((sym, f'{-age_min/60:.1f}h remaining'))

    print(f'Expired now   ({len(expired)}): {expired[:10]}')
    print(f'Expiring <1h  ({len(expiring_1h)}): {expiring_1h[:5]}')
    print(f'Valid >1h     ({len(valid)}): {len(valid)} candidates')
    print(f'No expiry set ({len(no_expiry)}): {len(no_expiry)} candidates')

# ─── 6. SCORE DISTRIBUTION ────────────────────────────────────────────────
print(f'\n{SEP}')
print('6. SCORE DISTRIBUTION')
print(SEP)

if cands:
    scores = [c.get('score', 0) for c in cands]
    scores_sorted = sorted(scores, reverse=True)
    bands = {'>=0.9': 0, '0.8-0.9': 0, '0.7-0.8': 0, '0.6-0.7': 0, '<0.6': 0}
    for s in scores:
        if s >= 0.9:   bands['>=0.9'] += 1
        elif s >= 0.8: bands['0.8-0.9'] += 1
        elif s >= 0.7: bands['0.7-0.8'] += 1
        elif s >= 0.6: bands['0.6-0.7'] += 1
        else:          bands['<0.6'] += 1
    print(f'Total candidates: {len(scores)}')
    print(f'Score range     : {min(scores):.3f} — {max(scores):.3f}')
    print(f'Median score    : {scores_sorted[len(scores_sorted)//2]:.3f}')
    print(f'Distribution    : {bands}')

    strategies = {}
    for c in cands:
        s = c.get('strategy') or c.get('pattern') or 'unknown'
        strategies[s] = strategies.get(s, 0) + 1
    print(f'Strategy mix    : {dict(sorted(strategies.items(), key=lambda x: -x[1]))}')

# ─── 7. DATA DIRECTORY LISTING ────────────────────────────────────────────
print(f'\n{SEP}')
print('7. DATA DIRECTORY — ALL JSON FILES')
print(SEP)

for f in sorted(DATA_DIR.glob('*.json')):
    mtime_f  = f.stat().st_mtime
    size_kb  = f.stat().st_size / 1024
    age_disp = _age_str(mtime_f)
    print(f'{f.name:<45} {size_kb:>8.1f} KB   age={age_disp}')

print(f'\nAudit complete at {NOW_DT.strftime("%Y-%m-%d %H:%M:%S IST")}')
