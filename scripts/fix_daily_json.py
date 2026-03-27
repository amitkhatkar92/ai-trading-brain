import json
import pathlib

d = {
    "date": "2026-03-24",
    "generated_at": "2026-03-24T11:35:00",
    "today": {"trades": 0, "wins": 0, "losses": 0, "net_pnl": 0.0, "win_rate_pct": 0.0},
    "cumulative": {"closed_trades": 0, "open_trades": 0, "cum_pnl": 0, "cum_return_pct": 0.0},
    "pilot_capital": 1000000.0,
    "mode": "paper"
}
pathlib.Path("data/paper_trading_daily.json").write_text(json.dumps(d, indent=2))
print("OK - date=%s capital=%s open_trades=%s" % (d["date"], d["pilot_capital"], d["cumulative"]["open_trades"]))
