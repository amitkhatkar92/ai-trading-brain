#!/usr/bin/env python3
"""
evo3.py — Universe evolution using scanner_memory (symbol lists) + today's full candidates
"""
import json
from pathlib import Path
from datetime import datetime

DATA_DIR = Path('/app/data')
NOW_DT   = datetime.now()
SEP      = '=' * 70

mem       = json.loads((DATA_DIR / 'scanner_memory.json').read_text())
raw_today = json.loads((DATA_DIR / 'daily_candidates.json').read_text())

cands_today = raw_today.get('candidates', [])

# Build today's full lookup: symbol → {score, strategy, sector, rank}
today_ranked = {}
for i, c in enumerate(sorted(cands_today, key=lambda x: -x.get('score', 0))):
    sym = c.get('symbol', '')
    today_ranked[sym] = {**c, '_rank': i + 1}

# Extract date-keyed symbol lists from scanner_memory
# Values are plain symbol strings
date_sessions = {}
for k, v in mem.items():
    if k.startswith('2026-') and isinstance(v, list):
        syms = []
        for item in v:
            if isinstance(item, str):
                syms.append(item)
            elif isinstance(item, dict):
                s = item.get('symbol', '')
                if s:
                    syms.append(s)
        date_sessions[k] = syms

date_keys = sorted(date_sessions.keys())
print(f'\n{SEP}')
print('SCANNER MEMORY — DATE SNAPSHOTS (symbol counts)')
print(SEP)
for dk in date_keys:
    today_flag = ' ← TODAY' if dk == '2026-06-01' else ''
    print(f'  {dk}: {len(date_sessions[dk]):>3} symbols{today_flag}')

# Trading session ordering (exclude weekends May 25/26)
trade_sessions_ordered = ['2026-05-27', '2026-05-28', '2026-05-29', '2026-05-30', '2026-06-01']
available = [d for d in trade_sessions_ordered if d in date_sessions]
print(f'\nTrading sessions in memory: {available}')

TODAY = '2026-06-01'
PREV  = '2026-05-30'   # Last Friday
PREV2 = '2026-05-29'   # Thursday

today_set = set(date_sessions.get(TODAY, []))
prev_set  = set(date_sessions.get(PREV,  []))
prev2_set = set(date_sessions.get(PREV2, []))

added    = today_set - prev_set
removed  = prev_set  - today_set
persist  = today_set & prev_set
turnover = (len(added) + len(removed)) / max(len(prev_set), 1) * 100

print(f'\n{SEP}')
print('1. UNIVERSE SIZE TIMELINE')
print(SEP)
for dk in available:
    syms = date_sessions[dk]
    today_flag = ' ← TODAY (Mon)' if dk == '2026-06-01' else ' (Fri)' if dk == '2026-05-30' else ''
    print(f'  {dk}: {len(syms):>3} symbols{today_flag}')

print(f'\n{SEP}')
print(f'2. TODAY ({TODAY} Mon) vs PREVIOUS DAY ({PREV} Fri)')
print(SEP)
print(f'  Previous universe (Fri) : {len(prev_set):>3} symbols')
print(f'  Today universe    (Mon) : {len(today_set):>3} symbols')
print(f'  Added                   : {len(added):>3}  ({len(added)/max(len(prev_set),1)*100:.1f}% of Friday)')
print(f'  Removed                 : {len(removed):>3}  ({len(removed)/max(len(prev_set),1)*100:.1f}% of Friday)')
print(f'  Persisting              : {len(persist):>3}  ({len(persist)/max(len(prev_set),1)*100:.1f}% of Friday)')
print(f'  Turnover                : {turnover:.1f}%')
print(f'\n  A. Genuinely new today  : {len(added)/max(len(today_set),1)*100:.1f}% of today\'s universe')
print(f'  B. Carried forward      : {len(persist)/max(len(today_set),1)*100:.1f}% of today\'s universe')

# ── ADDITIONS ─────────────────────────────────────────────────────────────
print(f'\n{SEP}')
print('3. ALL ADDITIONS (new in Mon not in Fri)')
print(SEP)
print(f'  Total: {len(added)} symbols')
added_list = sorted(added, key=lambda s: today_ranked.get(s, {}).get('_rank', 999))
print(f'  {"Symbol":<14} {"Score":>6}  {"Rank":>4}  {"Strategy":<25}  {"Also in Thu(May29)?"}')
print(f'  {"-"*72}')
for sym in added_list:
    c  = today_ranked.get(sym, {})
    in_thu = '✓ was in Thu' if sym in prev2_set else '  brand new'
    print(f'  {sym:<14} {c.get("score",0):>6.3f}  {c.get("_rank","?"):>4}  {c.get("strategy","?"):<25}  {in_thu}')

# ── REMOVALS ──────────────────────────────────────────────────────────────
print(f'\n{SEP}')
print('4. ALL REMOVALS (in Fri but not today)')
print(SEP)
print(f'  Total: {len(removed)} symbols')
removed_list = sorted(removed)
print(f'  {"Symbol":<14}  {"in Thu(May29)?"}  {"in Wed(May28)?"}  {"in Tue(May27)?"}')
print(f'  {"-"*60}')
may28_set = set(date_sessions.get('2026-05-28', []))
may27_set = set(date_sessions.get('2026-05-27', []))
for sym in removed_list:
    in_thu = '✓' if sym in prev2_set else ' '
    in_wed = '✓' if sym in may28_set else ' '
    in_tue = '✓' if sym in may27_set else ' '
    # How many prior sessions was it in?
    cnt = sum(1 for dk in ['2026-05-27','2026-05-28','2026-05-29','2026-05-30'] if sym in set(date_sessions.get(dk, [])))
    print(f'  {sym:<14}  Thu={in_thu}  Wed={in_wed}  Tue={in_tue}  (was in {cnt}/4 prior sessions)')

# ── RANK CHANGES (today rank vs position-in-today relative to persist set) ─
# Since we only have ranks within today's universe, we compare today's rank
# vs how they ranked in Friday's list ordering (position in list = rank proxy)
print(f'\n{SEP}')
print('5. TOP 20 RANK CHANGES (persisting symbols, rank within today vs pos in Fri list)')
print(SEP)

# Build friday rank (by position in the date_sessions list — list is ordered by score descending in scanner)
fri_list = date_sessions.get(PREV, [])
fri_rank = {sym: (i+1) for i, sym in enumerate(fri_list)}  # position order

changes = []
for sym in persist:
    r_today = today_ranked.get(sym, {}).get('_rank', 99)
    r_fri   = fri_rank.get(sym, 99)
    delta   = r_fri - r_today   # positive = improved rank today
    s_today = today_ranked.get(sym, {}).get('score', 0)
    changes.append((sym, r_fri, r_today, delta, s_today))

changes.sort(key=lambda x: -abs(x[3]))
print(f'  {"Symbol":<14} {"FriPos":>6}  {"MonRank":>7}  {"ΔRank":>6}  {"ScoreToday":>10}  {"Strategy":<25}')
print(f'  {"-"*72}')
for sym, rp, rt, dr, st in changes[:20]:
    arrow = '▲' if dr > 0 else '▼' if dr < 0 else '─'
    print(f'  {sym:<14} {rp:>6}  {rt:>7}  {arrow}{abs(dr):>5}  {st:>10.3f}  {today_ranked.get(sym,{}).get("strategy","?"):<25}')

# ── C. MULTI-SESSION SURVIVORS ────────────────────────────────────────────
print(f'\n{SEP}')
print('C. MULTI-SESSION SURVIVORS')
print(SEP)

session_count = {}
for dk in available:
    for sym in date_sessions[dk]:
        session_count[sym] = session_count.get(sym, 0) + 1

# Distribution for today's symbols
print(f'  Session-count distribution for today\'s {len(today_set)} symbols:')
dist = {}
for sym in today_set:
    cnt = session_count.get(sym, 0)
    dist[cnt] = dist.get(cnt, 0) + 1

all_sessions_n = len(available)
for cnt in sorted(dist.keys(), reverse=True):
    bar   = '█' * dist[cnt]
    label = f'ALL {cnt}' if cnt == all_sessions_n else f'{cnt}/{all_sessions_n}'
    print(f'  {label:>8} sessions: {dist[cnt]:>3} symbols  {bar}')

print(f'\n  Symbols in ≥3 of 5 sessions (today\'s universe only):')
survivors = sorted(
    [(sym, cnt) for sym, cnt in session_count.items() if cnt >= 3 and sym in today_set],
    key=lambda x: (-x[1], today_ranked.get(x[0], {}).get('_rank', 99))
)
print(f'  Count: {len(survivors)} / {len(today_set)} ({len(survivors)/max(len(today_set),1)*100:.1f}%)')
print()
print(f'  {"Symbol":<14} {"Sessions":>8}  {"MonRank":>7}  {"Score":>7}  {"Strategy":<25}')
print(f'  {"-"*65}')
for sym, cnt in survivors[:35]:
    c    = today_ranked.get(sym, {})
    dots = ''.join(['■' if sym in set(date_sessions.get(dk, [])) else '□' for dk in available])
    print(f'  {sym:<14} {cnt:>8}  {c.get("_rank","?"):>7}  {c.get("score",0):>7.3f}  {c.get("strategy","?"):<25}  {dots}')

# ── D. STALE CORE ─────────────────────────────────────────────────────────
print(f'\n{SEP}')
print('D. STALE CANDIDATE ACCUMULATION')
print(SEP)

in_all = [sym for sym, cnt in session_count.items() if cnt == all_sessions_n and sym in today_set]
in_all.sort(key=lambda s: today_ranked.get(s, {}).get('_rank', 99))
print(f'  Present in ALL {all_sessions_n} sessions (Tue–Mon): {len(in_all)} symbols')
if in_all:
    for sym in in_all:
        c    = today_ranked.get(sym, {})
        dots = ''.join(['■' if sym in set(date_sessions.get(dk, [])) else '□' for dk in available])
        print(f'    {sym:<14} rank={c.get("_rank","?")}  score={c.get("score",0):.3f}  strategy={c.get("strategy","?")}  sessions={dots}')

# Are the all-session survivors all high-score (justified) or mixed?
if in_all:
    scores_all = [today_ranked.get(s, {}).get('score', 0) for s in in_all]
    avg_score_all = sum(scores_all) / len(scores_all)
    print(f'\n  Avg score of all-session core: {avg_score_all:.3f}')
    print(f'  Avg score of full universe:    {sum(c.get("score",0) for c in today_ranked.values())/max(len(today_ranked),1):.3f}')

# ── E. MEANINGFULNESS SUMMARY ─────────────────────────────────────────────
print(f'\n{SEP}')
print('E. IS THE SCANNER CREATING MEANINGFUL CHANGE?')
print(SEP)

# Week-on-week composition
all_seen = set()
for dk in available:
    all_seen |= set(date_sessions[dk])
print(f'  Total unique symbols across all 5 sessions: {len(all_seen)}')
print(f'  Today\'s {len(today_set)} is {len(today_set)/max(len(all_seen),1)*100:.1f}% of total unique set')

# "Churn" — symbols that appeared exactly once across all 5 sessions
one_timers = [sym for sym, cnt in session_count.items() if cnt == 1]
multi      = [sym for sym, cnt in session_count.items() if cnt >= 3]
print(f'  One-time appearances:    {len(one_timers)} ({len(one_timers)/max(len(all_seen),1)*100:.1f}%) — true discoveries or noise?')
print(f'  Recurring (≥3 sessions): {len(multi)} ({len(multi)/max(len(all_seen),1)*100:.1f}%) — stable core')

# Day-over-day turnover history
print(f'\n  Day-over-day turnover history:')
for i in range(1, len(available)):
    d1 = available[i-1]
    d2 = available[i]
    s1 = set(date_sessions[d1])
    s2 = set(date_sessions[d2])
    add = len(s2 - s1)
    rem = len(s1 - s2)
    to  = (add + rem) / max(len(s1), 1) * 100
    print(f'  {d1} → {d2}: +{add} added, -{rem} removed, turnover={to:.1f}%  ({len(s1)}→{len(s2)} symbols)')

# Strategy distribution across sessions
print(f'\n  Strategy distribution (today):')
strats = {}
for c in today_ranked.values():
    s = c.get('strategy', '?')
    strats[s] = strats.get(s, 0) + 1
for s, n in sorted(strats.items(), key=lambda x: -x[1]):
    bar = '█' * n
    print(f'  {s:<30} {n:>3}  {bar}')

print(f'\n{SEP}')
print(f'Audit complete: {NOW_DT.strftime("%Y-%m-%d %H:%M:%S IST")}')
print(SEP)
