#!/usr/bin/env python3
"""
evo2.py  — Universe evolution using scanner_memory date-keyed snapshots
"""
import json
from pathlib import Path
from datetime import datetime

DATA_DIR = Path('/app/data')
NOW_DT   = datetime.now()
SEP      = '=' * 70

mem = json.loads((DATA_DIR / 'scanner_memory.json').read_text())

# ── Print first candidate from each date to understand structure ─────────
print(f'\n{SEP}')
print('SNAPSHOT STRUCTURE CHECK (first candidate per date)')
print(SEP)
date_keys = sorted([k for k in mem if k.startswith('2026-')])
print(f'Available dates: {date_keys}')
for dk in date_keys:
    items = mem[dk]
    if items and isinstance(items[0], dict):
        first = items[0]
        print(f'\n{dk}: count={len(items)}, keys={list(first.keys())}')
        print(f'  sample: symbol={first.get("symbol","?")} score={first.get("score","?")} strategy={first.get("strategy","?")}')
    else:
        print(f'{dk}: count={len(items)}, type={type(items[0]).__name__}')
        if items:
            print(f'  sample: {items[0]}')

# ── Build daily universes ────────────────────────────────────────────────
def build_ranked(items):
    """Returns {symbol: {score, strategy, rank, ...}} sorted by score."""
    if not items or not isinstance(items[0], dict):
        return {}
    ranked = {}
    for i, c in enumerate(sorted(items, key=lambda x: -x.get('score', 0))):
        sym = c.get('symbol', '')
        if sym:
            ranked[sym] = {**c, '_rank': i + 1}
    return ranked

snapshots = {dk: build_ranked(mem[dk]) for dk in date_keys}

# Trading days in order
trade_days = [d for d in date_keys if d not in ('2026-05-25', '2026-05-26')]  # skip weekend
print(f'\nTrading-day snapshots used: {trade_days}')

# ── TODAY vs PREV day comparison ─────────────────────────────────────────
TODAY    = '2026-06-01'
PREV     = '2026-05-30'   # Friday
PREV2    = '2026-05-29'   # Thursday

today_u  = snapshots.get(TODAY, {})
prev_u   = snapshots.get(PREV, {})
prev2_u  = snapshots.get(PREV2, {})

today_set = set(today_u.keys())
prev_set  = set(prev_u.keys())
prev2_set = set(prev2_u.keys())

added    = today_set - prev_set
removed  = prev_set  - today_set
persist  = today_set & prev_set

turnover = (len(added) + len(removed)) / max(len(prev_set), 1) * 100

print(f'\n{SEP}')
print(f'1. UNIVERSE SIZE TIMELINE')
print(SEP)
for dk in date_keys:
    s = snapshots.get(dk, {})
    print(f'  {dk}: {len(s):>3} symbols')

print(f'\n{SEP}')
print(f'2. TODAY ({TODAY}) vs PREVIOUS DAY ({PREV})')
print(SEP)
print(f'  Previous universe size : {len(prev_set)}')
print(f'  Today universe size    : {len(today_set)}')
print(f'  Added                  : {len(added):>3}  ({len(added)/max(len(prev_set),1)*100:.1f}%)')
print(f'  Removed                : {len(removed):>3}  ({len(removed)/max(len(prev_set),1)*100:.1f}%)')
print(f'  Persisting             : {len(persist):>3}  ({len(persist)/max(len(prev_set),1)*100:.1f}%)')
print(f'  Turnover               : {turnover:.1f}%')
print(f'\n  A. Genuinely new today : {len(added)/max(len(today_set),1)*100:.1f}%')
print(f'  B. Carried forward     : {len(persist)/max(len(today_set),1)*100:.1f}%')

# ── TOP 20 ADDITIONS ─────────────────────────────────────────────────────
print(f'\n{SEP}')
print('3. TOP 20 ADDITIONS (new in today vs Friday)')
print(SEP)
added_list = sorted(added, key=lambda s: -today_u.get(s, {}).get('score', 0))[:20]
print(f'  {"Symbol":<14} {"Score":>6}  {"Rank":>4}  {"Strategy":<25}  {"vs Thu (May29)":<14}')
print(f'  {"-"*65}')
for sym in added_list:
    c  = today_u.get(sym, {})
    in_thu = '(in May29)' if sym in prev2_set else '(brand new)'
    print(f'  {sym:<14} {c.get("score",0):>6.3f}  {c.get("_rank","?"):>4}  {c.get("strategy","?"):<25}  {in_thu}')

# ── TOP 20 REMOVALS ──────────────────────────────────────────────────────
print(f'\n{SEP}')
print('4. TOP 20 REMOVALS (in Friday but not today)')
print(SEP)
removed_list = sorted(removed, key=lambda s: -prev_u.get(s, {}).get('score', 0))[:20]
print(f'  {"Symbol":<14} {"PrevScore":>9}  {"PrevRank":>8}  {"Strategy":<25}  {"in May29?":<10}')
print(f'  {"-"*65}')
for sym in removed_list:
    c  = prev_u.get(sym, {})
    in_may29 = 'yes' if sym in prev2_set else 'no'
    print(f'  {sym:<14} {c.get("score",0):>9.3f}  {c.get("_rank","?"):>8}  {c.get("strategy","?"):<25}  {in_may29}')

# ── TOP 20 RANK CHANGES ──────────────────────────────────────────────────
print(f'\n{SEP}')
print('5. TOP 20 LARGEST RANK CHANGES (persisting symbols)')
print(SEP)
changes = []
for sym in persist:
    r_today = today_u[sym].get('_rank', 99)
    r_prev  = prev_u[sym].get('_rank', 99)
    s_today = today_u[sym].get('score', 0)
    s_prev  = prev_u[sym].get('score', 0)
    delta_rank  = r_prev - r_today   # positive = improved rank
    delta_score = s_today - s_prev
    changes.append((sym, r_prev, r_today, delta_rank, s_prev, s_today, delta_score))

changes.sort(key=lambda x: -abs(x[3]))
print(f'  {"Symbol":<14} {"PrevRk":>6}  {"TodayRk":>7}  {"ΔRank":>6}  {"PrevScore":>9}  {"TodayScore":>10}  {"ΔScore":>7}')
print(f'  {"-"*70}')
for sym, rp, rt, dr, sp, st, ds in changes[:20]:
    arrow = '▲' if dr > 0 else '▼'
    sarrow = '+' if ds > 0 else ''
    print(f'  {sym:<14} {rp:>6}  {rt:>7}  {arrow}{abs(dr):>5}  {sp:>9.3f}  {st:>10.3f}  {sarrow}{ds:>6.3f}')

# ── SCORE DELTA STATS for persisting ─────────────────────────────────────
print(f'\n{SEP}')
print('6. SCORE CHANGE DISTRIBUTION (persisting symbols)')
print(SEP)
deltas = [abs(c[6]) for c in changes]
if deltas:
    avg_d = sum(deltas) / len(deltas)
    sig   = sum(1 for d in deltas if d > 0.05)
    big   = sum(1 for d in deltas if d > 0.10)
    zero  = sum(1 for d in deltas if d < 0.001)
    print(f'  Persisting symbols : {len(deltas)}')
    print(f'  Avg |score delta|  : {avg_d:.4f}')
    print(f'  Zero change (<0.001): {zero} ({zero/len(deltas)*100:.0f}%)')
    print(f'  Minor change (>0.05): {sig} ({sig/len(deltas)*100:.0f}%)')
    print(f'  Major change (>0.10): {big} ({big/len(deltas)*100:.0f}%)')
    # Distribution bucket
    buckets = {'0.00-0.01': 0, '0.01-0.03': 0, '0.03-0.05': 0, '0.05-0.10': 0, '>0.10': 0}
    for d in deltas:
        if d < 0.01:   buckets['0.00-0.01'] += 1
        elif d < 0.03: buckets['0.01-0.03'] += 1
        elif d < 0.05: buckets['0.03-0.05'] += 1
        elif d < 0.10: buckets['0.05-0.10'] += 1
        else:          buckets['>0.10']     += 1
    for b, n in buckets.items():
        bar = '█' * n
        print(f'  |Δ| {b}: {n:>3} {bar}')

# ── C. MULTI-SESSION SURVIVORS ───────────────────────────────────────────
print(f'\n{SEP}')
print('C. MULTI-SESSION SURVIVORS (present in ≥3 of last 6 sessions)')
print(SEP)

all_sess = [snapshots[dk] for dk in date_keys]
session_count = {}
for sess_d in all_sess:
    for sym in sess_d:
        session_count[sym] = session_count.get(sym, 0) + 1

survivors_3 = [(sym, cnt) for sym, cnt in session_count.items() if cnt >= 3 and sym in today_set]
survivors_3.sort(key=lambda x: -x[1])

print(f'  Total symbols seen across all sessions: {len(session_count)}')
print(f'  Symbols in today\'s universe:            {len(today_set)}')
print(f'  Of those, in ≥3 sessions:               {len(survivors_3)} ({len(survivors_3)/max(len(today_set),1)*100:.1f}%)')
print()
print(f'  {"Symbol":<14} {"Sessions":>8}  {"Rank":>5}  {"Score":>7}  {"Strategy":<25}  Dates')
print(f'  {"-"*75}')
for sym, cnt in survivors_3[:30]:
    c     = today_u.get(sym, {})
    dates = [dk for dk in date_keys if sym in snapshots.get(dk, {})]
    print(f'  {sym:<14} {cnt:>8}  {c.get("_rank","?"):>5}  {c.get("score",0):>7.3f}  {c.get("strategy","?"):<25}  {dates}')

# ── D. STALE ACCUMULATION ────────────────────────────────────────────────
print(f'\n{SEP}')
print('D. STALE CANDIDATE ACCUMULATION')
print(SEP)

# How many of today's candidates appear in ALL 6 sessions (persistent core)?
in_all = [sym for sym, cnt in session_count.items() if cnt == len(date_keys) and sym in today_set]
print(f'  In ALL {len(date_keys)} sessions (persistent core): {len(in_all)} symbols')
if in_all:
    for sym in sorted(in_all, key=lambda s: -today_u.get(s, {}).get('score', 0)):
        c = today_u.get(sym, {})
        print(f'    {sym:<14} rank={c.get("_rank","?")}  score={c.get("score",0):.3f}  strategy={c.get("strategy","?")}')

# Distribution of session counts for today's universe
print(f'\n  Session-count distribution for today\'s 59 symbols:')
dist = {}
for sym in today_set:
    cnt = session_count.get(sym, 0)
    dist[cnt] = dist.get(cnt, 0) + 1
for cnt in sorted(dist.keys()):
    bar = '█' * dist[cnt]
    label = 'all sessions' if cnt == len(date_keys) else f'{cnt}/{len(date_keys)} sessions'
    print(f'  {label:>18}: {dist[cnt]:>3} symbols  {bar}')

# ── E. MEANINGFULNESS SUMMARY ────────────────────────────────────────────
print(f'\n{SEP}')
print('E. MEANINGFULNESS ASSESSMENT')
print(SEP)

# Strategy shifts
strats_prev  = {}
strats_today = {}
for c in prev_u.values():
    s = c.get('strategy', '?')
    strats_prev[s] = strats_prev.get(s, 0) + 1
for c in today_u.values():
    s = c.get('strategy', '?')
    strats_today[s] = strats_today.get(s, 0) + 1

print(f'  Strategy distribution change (Fri→Mon):')
all_s = set(list(strats_prev.keys()) + list(strats_today.keys()))
for s in sorted(all_s):
    p = strats_prev.get(s, 0)
    t = strats_today.get(s, 0)
    d = t - p
    arrow = f'+{d}' if d > 0 else str(d) if d < 0 else ' 0'
    print(f'    {s:<30} Fri={p:>3}  Mon={t:>3}  Δ={arrow}')

# Sector shifts
secs_prev  = {}
secs_today = {}
for c in prev_u.values():
    sec = c.get('sector', '?')
    secs_prev[sec] = secs_prev.get(sec, 0) + 1
for c in today_u.values():
    sec = c.get('sector', '?')
    secs_today[sec] = secs_today.get(sec, 0) + 1

print(f'\n  Sector distribution change (Fri→Mon):')
all_sec = set(list(secs_prev.keys()) + list(secs_today.keys()))
for sec in sorted(all_sec):
    p = secs_prev.get(sec, 0)
    t = secs_today.get(sec, 0)
    d = t - p
    arrow = f'+{d}' if d > 0 else str(d) if d < 0 else ' 0'
    print(f'    {sec:<20} Fri={p:>3}  Mon={t:>3}  Δ={arrow}')

print(f'\n{SEP}')
print(f'Audit complete: {NOW_DT.strftime("%Y-%m-%d %H:%M:%S IST")}')
print(SEP)
