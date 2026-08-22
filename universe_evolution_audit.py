#!/usr/bin/env python3
"""
universe_evolution_audit.py
Compares previous session universe vs today's pre-market vs current live universe.
Run: docker exec ai-trading-brain python3 /tmp/universe_evolution_audit.py
"""
import json
import os
import sys
import time
from pathlib import Path
from datetime import datetime, timedelta

DATA_DIR  = Path('/app/data')
NOW       = time.time()
NOW_DT    = datetime.now()

SEP = '=' * 72

def _load_json(path):
    try:
        return json.loads(Path(path).read_text(encoding='utf-8'))
    except Exception as e:
        return None

def _age_str(ts_epoch):
    h = (NOW - ts_epoch) / 3600
    if h < 1:   return f'{h*60:.0f}min'
    if h < 48:  return f'{h:.1f}h'
    return f'{h/24:.1f}days'

# ─── Load today's candidates ───────────────────────────────────────────────
raw_today = _load_json(DATA_DIR / 'daily_candidates.json')
cands_today = raw_today.get('candidates', []) if raw_today else []
mtime_today = (DATA_DIR / 'daily_candidates.json').stat().st_mtime

# ─── Load scanner_memory.json (contains session history) ──────────────────
scanner_mem = _load_json(DATA_DIR / 'scanner_memory.json')

# ─── Look for previous session snapshot in scanner_memory ─────────────────
# scanner_memory typically stores last N session snapshots
prev_cands = []
prev_date_str = ''
prev_source = 'not_found'

print(f'\n{SEP}')
print('SCANNER MEMORY — STRUCTURE')
print(SEP)
if scanner_mem:
    print(f'Keys: {list(scanner_mem.keys())}')
    for k, v in scanner_mem.items():
        if isinstance(v, list):
            print(f'  {k}: list of {len(v)} items')
            if v and isinstance(v[0], dict):
                print(f'    First item keys: {list(v[0].keys())}')
        elif isinstance(v, dict):
            print(f'  {k}: dict with keys {list(v.keys())[:8]}')
        else:
            print(f'  {k}: {v}')
else:
    print('scanner_memory.json not found or empty')

# ─── Check for session_history / daily_history in scanner_memory ──────────
if scanner_mem:
    for key in ['session_history', 'daily_history', 'prev_candidates', 'previous_candidates',
                'snapshots', 'history', 'last_session', 'yesterday']:
        if key in scanner_mem:
            print(f'\nFound history under key: {key}')
            val = scanner_mem[key]
            if isinstance(val, list) and val:
                prev_cands = val
                prev_source = f'scanner_memory[{key}]'
                print(f'  Count: {len(prev_cands)} records')

# ─── Check for trade_analytics for previous session ───────────────────────
print(f'\n{SEP}')
print('PREVIOUS SESSION CANDIDATE ARCHIVES')
print(SEP)

# Check if there's a date-stamped candidate file
for name in sorted(DATA_DIR.glob('daily_candidates_*.json'), reverse=True)[:3]:
    mtime = name.stat().st_mtime
    print(f'Found archive: {name.name}  age={_age_str(mtime)}')
    d = _load_json(name)
    if d:
        c = d.get('candidates', [])
        print(f'  Candidates: {len(c)}')
        if c and not prev_cands:
            prev_cands = c
            prev_date_str = name.name
            prev_source = str(name.name)

# Check trade_analytics for last few days
print(f'\nTrade analytics files (last 5):')
for f in sorted(DATA_DIR.glob('trade_analytics_*.json'), reverse=True)[:5]:
    mtime = f.stat().st_mtime
    d = _load_json(f)
    syms = list(d.keys()) if d and isinstance(d, dict) else []
    print(f'  {f.name}  age={_age_str(mtime)}  symbols={len(syms)}  keys_sample={syms[:5]}')

# ─── Reconstruct from scanner_memory candidates_history ────────────────────
print(f'\n{SEP}')
print('SCANNER MEMORY — CANDIDATES HISTORY')
print(SEP)
if scanner_mem:
    # Sometimes stored as candidates_history with date keys
    for key in ['candidates_history', 'daily_snapshots', 'scan_history']:
        if key in scanner_mem:
            h = scanner_mem[key]
            if isinstance(h, dict):
                print(f'Key {key}: {len(h)} date entries: {sorted(h.keys())[-5:]}')
                # Get the most recent non-today entry
                dates = sorted(h.keys(), reverse=True)
                today_str = NOW_DT.strftime('%Y-%m-%d')
                for d in dates:
                    if not d.startswith(today_str):
                        prev_cands = h[d] if isinstance(h[d], list) else h[d].get('candidates', [])
                        prev_date_str = d
                        prev_source = f'scanner_memory[{key}][{d}]'
                        print(f'  Using prev session: {d}  candidates={len(prev_cands)}')
                        break
                # Print today if exists
                for d in dates:
                    if d.startswith(today_str):
                        tc = h[d] if isinstance(h[d], list) else h[d].get('candidates', [])
                        print(f'  Today ({d}): {len(tc)} candidates')

# Full dump of scanner_memory keys for reference
if scanner_mem:
    print(f'\nFull scanner_memory structure:')
    for k, v in scanner_mem.items():
        if isinstance(v, (str, int, float, bool)):
            print(f'  {k}: {v}')
        elif isinstance(v, list):
            print(f'  {k}: list[{len(v)}]')
        elif isinstance(v, dict):
            print(f'  {k}: dict[{len(v)} keys]  keys={list(v.keys())[:6]}')

# ─── Check if may29 is available in any form ──────────────────────────────
print(f'\n{SEP}')
print('RECONSTRUCTING PREV UNIVERSE FROM LOGS + TRADE ANALYTICS')
print(SEP)

# Try to get last-session symbols from trade_analytics files
# These contain per-symbol data for each trading day
prev_analytics_syms = {}
for f in sorted(DATA_DIR.glob('trade_analytics_2026-05-*.json'), reverse=True)[:3]:
    d = _load_json(f)
    if d and isinstance(d, dict):
        print(f'{f.name}: {len(d)} symbols  → {list(d.keys())[:8]}')
        if len(d) > 10 and not prev_analytics_syms:
            prev_analytics_syms = d
            prev_date_str = f.name.replace('trade_analytics_', '').replace('.json', '')

# ─── Load improvement_backlog — may contain universe evolution data ────────
backlog = _load_json(DATA_DIR / 'improvement_backlog.json')
if backlog:
    print(f'\nImprovement backlog keys: {list(backlog.keys())[:10]}')

# ─── NOW DO THE EVOLUTION COMPARISON ──────────────────────────────────────
print(f'\n{SEP}')
print('UNIVERSE EVOLUTION COMPARISON')
print(SEP)

today_syms = {c['symbol']: c for c in cands_today}

# Assign today's ranks
for i, c in enumerate(sorted(cands_today, key=lambda x: -x.get('score', 0))):
    c['_rank_today'] = i + 1

today_ranked = {c['symbol']: c for c in cands_today}
today_set = set(today_syms.keys())

if prev_cands:
    prev_ranked = {}
    for i, c in enumerate(sorted(prev_cands, key=lambda x: -x.get('score', 0) if isinstance(c, dict) else 0)):
        if isinstance(c, dict):
            sym = c.get('symbol', '')
            if sym:
                c['_rank_prev'] = i + 1
                prev_ranked[sym] = c
    prev_set = set(prev_ranked.keys())

    added   = today_set - prev_set
    removed = prev_set - today_set
    persist = today_set & prev_set

    turnover = (len(added) + len(removed)) / max(len(prev_set), 1) * 100

    print(f'Previous session source : {prev_source}')
    print(f'Previous universe size  : {len(prev_set)} symbols  (date: {prev_date_str})')
    print(f'Today universe size     : {len(today_set)} symbols')
    print(f'Added                   : {len(added)} symbols  ({len(added)/max(len(prev_set),1)*100:.1f}%)')
    print(f'Removed                 : {len(removed)} symbols  ({len(removed)/max(len(prev_set),1)*100:.1f}%)')
    print(f'Persisting              : {len(persist)} symbols  ({len(persist)/max(len(prev_set),1)*100:.1f}%)')
    print(f'Universe Turnover %     : {turnover:.1f}%')
    print(f'\nA. Genuinely new today  : {len(added)/max(len(today_set),1)*100:.1f}%')
    print(f'B. Carried forward      : {len(persist)/max(len(today_set),1)*100:.1f}%')

    # Top 20 additions with scores
    print(f'\nTOP 20 ADDITIONS (new today):')
    added_list = sorted(added, key=lambda s: -today_ranked.get(s, {}).get('score', 0))[:20]
    for sym in added_list:
        c = today_ranked.get(sym, {})
        print(f'  {sym:<14} score={c.get("score",0):.3f}  rank={c.get("_rank_today","?")}  strategy={c.get("strategy","?")}')

    # Top 20 removals with their old scores
    print(f'\nTOP 20 REMOVALS (dropped vs yesterday):')
    removed_list = sorted(removed, key=lambda s: -prev_ranked.get(s, {}).get('score', 0))[:20]
    for sym in removed_list:
        c = prev_ranked.get(sym, {})
        print(f'  {sym:<14} prev_score={c.get("score",0):.3f}  prev_rank={c.get("_rank_prev","?")}  strategy={c.get("strategy","?")}')

    # Top 20 rank changes
    print(f'\nTOP 20 LARGEST RANK CHANGES (persisting symbols):')
    rank_changes = []
    for sym in persist:
        c_today = today_ranked.get(sym, {})
        c_prev  = prev_ranked.get(sym, {})
        r_today = c_today.get('_rank_today', 99)
        r_prev  = c_prev.get('_rank_prev', 99)
        delta   = r_prev - r_today  # positive = moved up
        s_today = c_today.get('score', 0)
        s_prev  = c_prev.get('score', 0)
        rank_changes.append((sym, r_prev, r_today, delta, s_prev, s_today))

    rank_changes.sort(key=lambda x: -abs(x[3]))
    for sym, rp, rt, delta, sp, st in rank_changes[:20]:
        arrow = '▲' if delta > 0 else '▼' if delta < 0 else '─'
        print(f'  {sym:<14} rank: {rp:>3}→{rt:>3}  {arrow}{abs(delta):>3}   score: {sp:.3f}→{st:.3f}')

else:
    print('No previous session data available for comparison.')
    print('Today universe (all 59 candidates):')
    for sym, c in sorted(today_ranked.items(), key=lambda x: -x[1].get('score', 0)):
        print(f'  {sym:<14} score={c.get("score",0):.3f}  rank={c.get("_rank_today","?")}  strategy={c.get("strategy","?")}')

# ─── C. Survivors across multiple sessions ────────────────────────────────
print(f'\n{SEP}')
print('C. MULTI-SESSION SURVIVORS')
print(SEP)

# Check all available trade_analytics files to find persistent symbols
all_analytics_syms = {}
for f in sorted(DATA_DIR.glob('trade_analytics_2026-*.json'), reverse=True)[:10]:
    d = _load_json(f)
    if d and isinstance(d, dict):
        date_str = f.name.replace('trade_analytics_', '').replace('.json', '')
        for sym in d.keys():
            all_analytics_syms.setdefault(sym, []).append(date_str)

# Count sessions per symbol (from today's universe)
survivors = {}
for sym in today_set:
    sessions = all_analytics_syms.get(sym, [])
    survivors[sym] = len(sessions)

# Group by session count
over3 = [(s, c, survivors.get(s, 0)) for s, c in today_ranked.items() if survivors.get(s, 0) >= 3]
over3.sort(key=lambda x: -x[2])

print(f'Symbols in today\'s universe with trade analytics in >=3 prior sessions:')
print(f'Count: {len(over3)} / {len(today_set)} ({len(over3)/max(len(today_set),1)*100:.1f}%)')
print()
if over3:
    for sym, c, nsess in over3[:25]:
        dates = all_analytics_syms.get(sym, [])
        print(f'  {sym:<14} {nsess} sessions  dates={dates[-4:]}  score_today={c.get("score",0):.3f}  rank={c.get("_rank_today","?")}')

# D. Stale candidate accumulation check
print(f'\n{SEP}')
print('D. STALE CANDIDATE ACCUMULATION CHECK')
print(SEP)

# Check valid_until_utc expiry status
from datetime import timezone
expired_cands  = []
near_expiry    = []
healthy_cands  = []

for c in cands_today:
    sym = c.get('symbol', '?')
    vu  = c.get('valid_until_utc')
    state = c.get('lifecycle_state', 'UNKNOWN')

    if vu is None:
        near_expiry.append((sym, 'no_expiry_set', state))
        continue

    try:
        if isinstance(vu, str):
            dt = datetime.fromisoformat(vu.replace('Z', '+00:00'))
            dt_naive = dt.replace(tzinfo=None)
            age_past_m = (NOW_DT - dt_naive).total_seconds() / 60
        elif isinstance(vu, (int, float)):
            age_past_m = (NOW - vu) / 60
        else:
            near_expiry.append((sym, 'parse_error', state))
            continue

        if age_past_m > 0:
            expired_cands.append((sym, f'expired {age_past_m:.0f}min ago', state))
        elif age_past_m > -30:
            near_expiry.append((sym, f'expires in {-age_past_m:.0f}min', state))
        else:
            healthy_cands.append((sym, f'valid for {-age_past_m/60:.1f}h', state))
    except Exception as e:
        near_expiry.append((sym, f'parse_err: {e}', state))

print(f'Expired (past valid_until): {len(expired_cands)} — survived via TTL extension')
print(f'Near expiry (<30min):        {len(near_expiry)}')
print(f'Healthy (>30min remaining):  {len(healthy_cands)}')
if expired_cands[:5]:
    print(f'\nSample expired (surviving on extension):')
    for sym, info, state in sorted(expired_cands, key=lambda x: x[1])[:10]:
        sc = today_ranked.get(sym, {}).get('score', 0)
        print(f'  {sym:<14} {info}  state={state}  score={sc:.3f}')

# E. Is the scanner creating meaningful change?
print(f'\n{SEP}')
print('E. MEANINGFULNESS ASSESSMENT')
print(SEP)

if prev_cands and prev_ranked:
    # Score change for persisting symbols
    score_deltas = []
    for sym in persist:
        s_t = today_ranked.get(sym, {}).get('score', 0)
        s_p = prev_ranked.get(sym, {}).get('score', 0)
        score_deltas.append(abs(s_t - s_p))

    if score_deltas:
        avg_delta = sum(score_deltas) / len(score_deltas)
        sig_changes = sum(1 for d in score_deltas if d > 0.05)
        print(f'Avg score delta (persisting symbols): {avg_delta:.4f}')
        print(f'Symbols with score change >0.05:      {sig_changes}/{len(persist)} ({sig_changes/max(len(persist),1)*100:.1f}%)')
    print(f'Strategy distribution change:')
    prev_strats = {}
    for c in prev_ranked.values():
        s = c.get('strategy', 'unknown')
        prev_strats[s] = prev_strats.get(s, 0) + 1
    today_strats = {}
    for c in today_ranked.values():
        s = c.get('strategy', 'unknown')
        today_strats[s] = today_strats.get(s, 0) + 1
    all_strats = set(list(prev_strats.keys()) + list(today_strats.keys()))
    for s in sorted(all_strats):
        p = prev_strats.get(s, 0)
        t = today_strats.get(s, 0)
        delta = t - p
        arrow = f'+{delta}' if delta > 0 else str(delta) if delta < 0 else '  0'
        print(f'  {s:<28} prev={p:>3}  today={t:>3}  Δ={arrow}')
else:
    print('No previous session for comparison.')

print(f'\n{SEP}')
print(f'Audit complete at {NOW_DT.strftime("%Y-%m-%d %H:%M:%S IST")}')
print(SEP)
