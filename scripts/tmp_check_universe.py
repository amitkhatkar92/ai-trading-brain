import json
data = json.load(open('/root/ai-trading-brain/data/nifty500_universe.json'))
print('Total:', len(data))
print('Keys:', list(data[0].keys()) if data else 'empty')
print('Sample:', [(d.get('symbol'), d.get('sector')) for d in data[:8]])
