#!/usr/bin/env python3
"""
forensic_refresh_logs.py
Parses today's container logs for all universe/candidate/refresh/indicator telemetry.
Run: docker exec ai-trading-brain python3 /tmp/forensic_refresh_logs.py
"""
import subprocess
import sys
import re
from datetime import datetime

NOW_STR = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# Tags we care about
TAGS = [
    'ScannerRun', 'UniverseRebuild', 'IntradayRefresh', 'CandidateStore',
    'PreparedUniverse', 'ScannerShadow', 'PhaseD', 'PremarketRefiner',
    'RefreshExpired', 'TTLExtend', 'MiniRescan', 'ScannerEvent',
    'OptionsFeed', 'LTPFresh', 'IndicatorFresh', 'RSI', 'ATR',
    'DhanOptionsAudit', 'OptionsCapability', 'BackgroundRefresh',
    'ScoreChange', 'RankChange', 'LifecycleTransition',
    'CandidateFunnel', 'FunnelAudit', 'PreparedUniverseHealth',
    'post_market_scan', 'post_market', 'market_scanner',
    'POOL_EXHAUSTION', 'REGIME_TRANSITION',
]

def run_log_search(since_hours=24):
    """Fetch container logs from the last N hours."""
    try:
        result = subprocess.run(
            ['docker', 'logs', 'ai-trading-brain', '--since', f'{since_hours}h'],
            capture_output=True, text=True, timeout=30
        )
        lines = (result.stdout + result.stderr).splitlines()
        return lines
    except Exception as e:
        return [f'ERROR: {e}']

print(f'Audit time: {NOW_STR}')
print('Fetching container logs (last 24h)...')
all_lines = run_log_search(24)
print(f'Total log lines: {len(all_lines)}')

SEP = '=' * 72

# ─── Filter for each relevant category ────────────────────────────────────
def grep_lines(pattern, lines, max_n=50):
    pat = re.compile(pattern, re.IGNORECASE)
    return [l for l in lines if pat.search(l)][:max_n]

# ─── A. Universe Refresh events ───────────────────────────────────────────
print(f'\n{SEP}')
print('A. UNIVERSE REFRESH EVENTS (ScannerRun / UniverseRebuild / PhaseD)')
print(SEP)
for tag in ['ScannerRun', 'UniverseRebuild', 'PhaseD', 'post_market_scan', 'market_scanner']:
    hits = grep_lines(tag, all_lines, 30)
    if hits:
        print(f'\n--- {tag} ({len(hits)} lines) ---')
        for l in hits:
            print(l)

# ─── B. Intraday refresh ──────────────────────────────────────────────────
print(f'\n{SEP}')
print('B. INTRADAY REFRESH EVENTS (11:30, 13:30)')
print(SEP)
for tag in ['IntradayRefresh', 'RefreshExpired', 'TTLExtend', 'MiniRescan', 'ScannerEvent']:
    hits = grep_lines(tag, all_lines, 30)
    if hits:
        print(f'\n--- {tag} ({len(hits)} lines) ---')
        for l in hits:
            print(l)

# ─── C. Prepared universe health ──────────────────────────────────────────
print(f'\n{SEP}')
print('C. PREPARED UNIVERSE HEALTH')
print(SEP)
for tag in ['PreparedUniverseHealth', 'PreparedUniverse', 'CandidateStore', 'CandidateFunnel', 'FunnelAudit']:
    hits = grep_lines(tag, all_lines, 30)
    if hits:
        print(f'\n--- {tag} ({len(hits)} lines) ---')
        for l in hits:
            print(l)

# ─── D. Premarket refiner ──────────────────────────────────────────────────
print(f'\n{SEP}')
print('D. PREMARKET REFINER')
print(SEP)
hits = grep_lines(r'premarket_refiner|PremarketRefiner|Phase.G|premarket.refin', all_lines, 20)
if hits:
    for l in hits:
        print(l)
else:
    print('No premarket refiner events found.')

# ─── E. Options / LTP capability ──────────────────────────────────────────
print(f'\n{SEP}')
print('E. OPTIONS & LTP CAPABILITY')
print(SEP)
hits = grep_lines(r'OptionsCapability|OptionsFeed.*chain|DhanOptionsAudit.*chain_ok|LTPFresh|fallback_events', all_lines, 40)
for l in hits[:40]:
    print(l)

# ─── F. Background refresh ────────────────────────────────────────────────
print(f'\n{SEP}')
print('F. BACKGROUND PRICE/RSI REFRESH')
print(SEP)
hits = grep_lines(r'BackgroundRefresh|background.*refresh|rsi.*refresh|price.*refresh', all_lines, 20)
for l in hits[:20]:
    print(l)

# ─── G. Score/rank changes ────────────────────────────────────────────────
print(f'\n{SEP}')
print('G. SCORE / RANK / LIFECYCLE CHANGES')
print(SEP)
hits = grep_lines(r'ScoreChange|RankChange|LifecycleTransit|score.*changed|rank.*changed|lifecycle.*state', all_lines, 20)
for l in hits[:20]:
    print(l)

# ─── H. Scheduler slot execution ─────────────────────────────────────────
print(f'\n{SEP}')
print('H. SCHEDULER SLOT EXECUTION (today)')
print(SEP)
hits = grep_lines(r'IST.*starting|16:45|08:45|08:30|09:00.*prewarm|premarket.*init|08:00.*init', all_lines, 30)
for l in hits[:30]:
    print(l)

# ─── I. Candidate pool stats from last cycle ──────────────────────────────
print(f'\n{SEP}')
print('I. CANDIDATE POOL STATS (from cycles)')
print(SEP)
hits = grep_lines(r'prepared.*candidates|candidate.*pool|pool.*size|candidate.*count|candidates.*available|no.*candidates', all_lines, 30)
for l in hits[:30]:
    print(l)

# ─── J. Data feed freshness ───────────────────────────────────────────────
print(f'\n{SEP}')
print('J. DATA FEED FRESHNESS / FALLBACK EVENTS')
print(SEP)
hits = grep_lines(r'DhanFallback|fallback.*yfinance|yfinance.*fallback|DhanPartialSuccess|yf.*fallback|sim.*fallback', all_lines, 20)
for l in hits[:20]:
    print(l)

print(f'\n{SEP}')
print(f'Log audit complete at {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
print(SEP)
