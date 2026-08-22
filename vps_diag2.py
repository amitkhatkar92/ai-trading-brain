import os, gzip, json
from datetime import datetime

log_dir = 'data/logs'

# LUPIN was opened 2026-06-22 and closed 2026-06-26
# Check logs around that date
target_dates = ['2026-06-22','2026-06-23','2026-06-24','2026-06-25','2026-06-26']

# Read EOD reports for last 10 days
eod_files = [f for f in os.listdir(log_dir) if f.startswith('eod_report_2026-06') or f.startswith('eod_report_2026-07')]
eod_files.sort()
print("=== EOD REPORTS (last 10 days) ===")
for fname in eod_files[-12:]:
    path = os.path.join(log_dir, fname)
    try:
        with open(path) as f:
            content = f.read()
        print(f"\n--- {fname} ---")
        print(content[:3000])
    except Exception as e:
        print(f"{fname}: {e}")

print("\n\n=== LUPIN IN LOGS ===")
# Read all log files looking for LUPIN
for lf in sorted(os.listdir(log_dir)):
    if not lf.startswith('ai_trading_brain'):
        continue
    path = os.path.join(log_dir, lf)
    try:
        if lf.endswith('.gz'):
            with gzip.open(path, 'rt', errors='replace') as f:
                lines = f.readlines()
        else:
            with open(path, 'r', errors='replace') as f:
                lines = f.readlines()
        hits = [(i+1, l.rstrip()) for i, l in enumerate(lines)
                if 'LUPIN' in l.upper()]
        if hits:
            print(f"\n  {lf} ({len(lines)} lines): {len(hits)} LUPIN hits")
            for n, l in hits:
                print(f"    L{n}: {l}")
    except Exception as e:
        print(f"  {lf}: {e}")

print("\n\n=== EARLY_LOSS / EXIT PRICE ISSUES IN MAIN LOG ===")
for lf in ['ai_trading_brain.log', 'ai_trading_brain.log.1', 'ai_trading_brain.log.2']:
    path = os.path.join(log_dir, lf)
    try:
        with open(path, 'r', errors='replace') as f:
            lines = f.readlines()
        hits = [(i+1, l.rstrip()) for i, l in enumerate(lines)
                if any(k in l for k in [
                    'EARLY_LOSS','early_loss','no price','price unavailable',
                    'fallback','stale price','exit_price=0','CLOSE',
                    'stop_loss hit','price=0','price=None','None as exit',
                    'yfinance','get_quote','get_history','price not available',
                    'SESSION_EXPIRED'
                ])]
        print(f"\n  {lf}: {len(hits)} exit/price-issue hits (first 60):")
        for n, l in hits[:60]:
            print(f"    L{n}: {l}")
    except Exception as e:
        print(f"  {lf}: {e}")
