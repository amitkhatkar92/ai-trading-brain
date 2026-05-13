path = '/app/data/paper_trades.csv'
with open(path, 'r') as f:
    content = f.read()
content = content.replace(
    '2026-05-07 09:10:17,SIM_NIFTY_SELL_43,',
    '2026-05-07 09:10:17,SIM_NIFTY_SELL_43_20260507,'
)
content = content.replace(
    '2026-05-07 11:29:04,SIM_NIFTY_SELL_43,',
    '2026-05-07 11:29:04,SIM_NIFTY_SELL_43_20260507,'
)
with open(path, 'w') as f:
    f.write(content)
print('Done')
import subprocess
result = subprocess.run(['grep', 'NIFTY_SELL_43', path], capture_output=True, text=True)
print(result.stdout)
