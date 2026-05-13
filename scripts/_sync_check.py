import hashlib, subprocess, os

BASE_LOCAL = r'C:\Users\UCIC\OneDrive\Desktop\ai_trading_brain'
BASE_VPS   = '/root/ai-trading-brain'
SSH        = ['ssh', '-i', r'C:/Users/UCIC/.ssh/trading_vps', 'root@178.18.252.24']

FILES = [
    'main.py', 'config.py',
    'execution_engine/order_manager.py',
    'learning_system/strategy_performance_tracker.py',
    'learning_system/learning_engine.py',
    'notifications/notifier_manager.py',
    'notifications/telegram_bot.py',
    'orchestrator/master_orchestrator.py',
    'data_feeds/dhan_feed.py',
    'data_feeds/data_feed_manager.py',
    'data_feeds/yahoo_feed.py',
    'data_integrity/trade_classifier.py',
    'data_integrity/instrument_registry.py',
    'data_integrity/price_integrity_validator.py',
    'trade_monitoring/trade_monitor.py',
    'market_intelligence/market_monitor.py',
    'global_intelligence/global_data_ai.py',
    'system_monitor/system_monitor.py',
    'meta_learning/regime_strategy_map.py',
    'risk_guardian/risk_guardian.py',
    'scripts/ghost_position_cleanup.py',
]

local = {}
for f in FILES:
    fp = os.path.join(BASE_LOCAL, f.replace('/', os.sep))
    if os.path.exists(fp):
        local[f] = hashlib.md5(open(fp, 'rb').read()).hexdigest()

vps_paths = ' '.join(f'{BASE_VPS}/{f}' for f in FILES)
res = subprocess.run(SSH + [f'md5sum {vps_paths} 2>/dev/null'], capture_output=True, text=True)
vps = {}
for line in res.stdout.splitlines():
    parts = line.split(None, 1)
    if len(parts) == 2:
        h, path = parts
        rel = path.replace(BASE_VPS + '/', '')
        vps[rel] = h

print(f"{'FILE':<55} {'LOCAL':<10} {'VPS':<10} STATUS")
print('-' * 90)
in_sync = 0
differs = []
missing = []
for f in FILES:
    lh = local.get(f, 'MISSING')[:8]
    vh = vps.get(f, 'MISSING')[:8]
    if lh == 'MISSING':
        status = '?? LOCAL MISSING'
    elif vh == 'MISSING':
        status = '!! VPS MISSING'
        missing.append(f)
    elif local.get(f) == vps.get(f):
        status = 'OK'
        in_sync += 1
    else:
        status = '** DIFFERS **'
        differs.append(f)
    print(f"{f:<55} {lh:<10} {vh:<10} {status}")

print(f"\nResult: {in_sync}/{len(FILES)} files in sync")
if differs:
    print("DIFFERS:", differs)
if missing:
    print("MISSING:", missing)
