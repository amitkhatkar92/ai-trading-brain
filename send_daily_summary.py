#!/usr/bin/env python3
"""
Send today's paper trading summary via Telegram.
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Ensure project root is in path
_ROOT = os.path.dirname(os.path.abspath(__file__))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from dotenv import load_dotenv
import requests

load_dotenv()

def send_daily_summary():
    """Load today's summary from JSON and send via Telegram."""
    
    # Get credentials
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    
    if not bot_token or not chat_id:
        print("❌ Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID in .env")
        return False
    
    # Load daily summary
    summary_file = Path(_ROOT) / "data" / "paper_trading_daily.json"
    if not summary_file.exists():
        print(f"❌ Summary file not found: {summary_file}")
        return False
    
    with open(summary_file, "r") as f:
        summary = json.load(f)
    
    # Format message
    date_str = summary.get("date", "?")
    gen_at = summary.get("generated_at", "?")
    today = summary.get("today", {})
    cumul = summary.get("cumulative", {})
    capital = summary.get("pilot_capital", 0)
    
    trades_today = today.get("trades", 0)
    wins_today = today.get("wins", 0)
    losses_today = today.get("losses", 0)
    pnl_today = today.get("net_pnl", 0)
    win_rate = today.get("win_rate_pct", 0)
    
    closed_total = cumul.get("closed_trades", 0)
    open_total = cumul.get("open_trades", 0)
    cum_pnl = cumul.get("cum_pnl", 0)
    cum_return = cumul.get("cum_return_pct", 0)
    
    # Decision icon
    icon = "💰" if pnl_today >= 0 else "🔴"
    cumul_icon = "💰" if cum_pnl >= 0 else "🔴"
    
    message = (
        f"{icon} <b>📊 Paper Trading Summary — {date_str}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"<b>TODAY'S PERFORMANCE</b>\n"
        f"New Trades:     {trades_today}\n"
        f"Wins:           {wins_today}\n"
        f"Losses:         {losses_today}\n"
        f"Win Rate:       {win_rate:.1f}%\n"
        f"<b>Today P&amp;L:     ₹{pnl_today:+,.0f}</b>\n\n"
        f"<b>CUMULATIVE (All Time)</b>\n"
        f"Closed Trades:  {closed_total}\n"
        f"Open Positions: {open_total}\n"
        f"Cumulative P&amp;L: {cumul_icon} ₹{cum_pnl:+,.0f}\n"
        f"Return %:       {cum_return:+.2f}%\n\n"
        f"<b>CAPITAL</b>\n"
        f"Pilot Capital:  ₹{capital:,.0f}\n"
        f"Generated:      {gen_at}\n"
        f"Mode:           📝 Paper (Simulation)"
    )
    
    # Send via Telegram
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    try:
        resp = requests.post(url, json={
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "HTML"
        }, timeout=10)
        
        if resp.ok:
            print(f"✅ Summary sent to Telegram successfully!")
            print(f"   Date: {date_str}")
            print(f"   Today: {trades_today} trades, ₹{pnl_today:+,.0f} P&L")
            print(f"   Open: {open_total} positions, ₹{cum_pnl:+,.0f} cumulative")
            return True
        else:
            print(f"❌ Telegram API error: {resp.status_code}")
            print(f"   {resp.text[:200]}")
            return False
    except Exception as e:
        print(f"❌ Error sending message: {e}")
        return False

if __name__ == "__main__":
    success = send_daily_summary()
    sys.exit(0 if success else 1)
