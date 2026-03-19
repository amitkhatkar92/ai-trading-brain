# Tomorrow's Action Guide — Paper Trading Start

**Date:** March 19, 2026  
**Market Open:** 09:15 AM IST  
**Your System:** Ready for Automatic Trading

---

## 📋 Morning Checklist (Before 09:15 AM)

### 5 Minutes Before Market Open (09:10 AM)

```bash
# Quick health check - copy and paste this command:
ssh -i ~/.ssh/trading_vps root@178.18.252.24 "echo '✓ Trading Service:' && systemctl is-active trading-brain && echo '✓ OAuth Service:' && systemctl is-active dhan-oauth && echo '✓ Memory:' && free -h | grep Mem && echo '✓ Ready!'"
```

Expected output:
```
✓ Trading Service:
active
✓ OAuth Service:
active
✓ Memory:
Mem:           7.8Gi       845Mi       6.6Gi
✓ Ready!
```

### At Market Open (09:15 AM)

**You:** Watch system start up (optional)
```bash
ssh -i ~/.ssh/trading_vps root@178.18.252.24 "tail -f /root/ai-trading-brain/data/logs/trading-brain.log"
```

**System:** Automatically starts trading cycles
- No action needed from you
- System handles everything

---

## 📊 Monitoring During Market Hours (09:15 AM - 16:30 PM)

### View Live Trades (Check Anytime)

```bash
# See recent trading decisions
ssh -i ~/.ssh/trading_vps root@178.18.252.24 "tail -20 /root/ai-trading-brain/data/logs/trading-brain.log"

# See paper trades executed
ssh -i ~/.ssh/trading_vps root@178.18.252.24 "tail -10 /root/ai-trading-brain/data/paper_trades.csv"

# Check system status
ssh -i ~/.ssh/trading_vps root@178.18.252.24 "ps aux | grep trading-brain | grep -v grep"
```

### What Each Command Shows

**Trading Log:**
- ✓ Trading decisions made
- ✓ Risk checks performed
- ✓ Orders placed/canceled
- ✓ Performance metrics
- ✓ Any errors (none expected)

**Paper Trades CSV:**
- ✓ Symbol traded
- ✓ Entry price
- ✓ Exit price
- ✓ Profit/Loss
- ✓ Timestamp

**Process Status:**
- ✓ Python process running
- ✓ Memory usage
- ✓ CPU usage

---

## 🆘 If Something Goes Wrong

### System Stops / Service Dead

```bash
# Method 1: Check what happened
ssh -i ~/.ssh/trading_vps root@178.18.252.24 "journalctl -eu trading-brain -n 50"

# Method 2: Restart service
ssh -i ~/.ssh/trading_vps root@178.18.252.24 "sudo systemctl restart trading-brain"

# Method 3: Check if it restarted
ssh -i ~/.ssh/trading_vps root@178.18.252.24 "sudo systemctl status trading-brain | head -5"
```

### Kill Switch Triggered (No Trades But System Running)

```bash
# Check kill switch status
ssh -i ~/.ssh/trading_vps root@178.18.252.24 "cat /root/ai-trading-brain/config/kill_switch.json"

# Reset kill switch and resume
ssh -i ~/.ssh/trading_vps root@178.18.252.24 "cd /root/ai-trading-brain && python3 scripts/kill_switch_toggle.py --reset"
```

### High Memory Usage / Crashes

```bash
# Check memory
ssh -i ~/.ssh/trading_vps root@178.18.252.24 "free -h"

# Restart service (clears memory)
ssh -i ~/.ssh/trading_vps root@178.18.252.24 "sudo systemctl restart trading-brain && sleep 2 && sudo systemctl status trading-brain"
```

### Network Issues

```bash
# Test VPS connectivity
ping 178.18.252.24

# SSH test
ssh -i ~/.ssh/trading_vps root@178.18.252.24 "echo Connected"

# If disconnected: Restart entirely
ssh -i ~/.ssh/trading_vps root@178.18.252.24 "sudo reboot"
```

---

## 📈 After Market Close (16:30+ PM)

### Step 1: Review Performance

```bash
# Copy all trades to analyze locally
scp -i ~/.ssh/trading_vps root@178.18.252.24:/root/ai-trading-brain/data/paper_trades.csv ~/Desktop/trades_today.csv
```

### Step 2: Check Daily Summary

```bash
# View full trading log for the day
ssh -i ~/.ssh/trading_vps root@178.18.252.24 "tail -100 /root/ai-trading-brain/data/logs/trading-brain.log"

# Generate statistics
ssh -i ~/.ssh/trading_vps root@178.18.252.24 "wc -l /root/ai-trading-brain/data/paper_trades.csv && echo 'trades executed'"
```

### Step 3: Example Metrics to Check

```
Total Trades:         X trades
Win Rate:             XX%
Average P&L:          +/- X%
Max Drawdown:         X%
Sharpe Ratio:         X.X
Best Trade:           +X%
Worst Trade:          -X%
System Uptime:        24h
Kill Switch Events:    X
Errors:               X
```

---

## ⚙️ Key Configuration (Already Set)

### Paper Trading Mode
✅ **ENABLED** - No real money at risk
```
PAPER_TRADING = True
```

### Kill Switch Thresholds
✅ **ACTIVE** - System stops if:
```
VIX > 45         (Market panic)
Daily Loss > 2%  (Risk limit)
```

### Trading Schedule
✅ **AUTOMATIC** - Runs at:
```
09:15 AM - 16:30 PM (Market open to close)
```

### Risk Management
✅ **ACTIVE** - System enforces:
```
Position sizing per strategy
Maximum daily loss limit
Volatility checks
Liquidity verification
```

---

## 🎯 What NOT to Do

❌ **DON'T:**
- Manually edit config files during trading hours
- Kill the process without reason
- Turn off VPS server
- Change PAPER_TRADING setting
- Restart services during active trades

✅ **DO:**
- Monitor logs
- Check health anytime
- Review trades after market
- Take notes on performance
- Let system run automatically

---

## 📞 Quick Commands Reference

```bash
# Service Status
systemctl status trading-brain
systemctl status dhan-oauth

# Restart Services
sudo systemctl restart trading-brain
sudo systemctl restart dhan-oauth

# View Logs (Live)
tail -f /root/ai-trading-brain/data/logs/trading-brain.log

# View Logs (Last N lines)
tail -50 /root/ai-trading-brain/data/logs/trading-brain.log

# View Paper Trades
cat /root/ai-trading-brain/data/paper_trades.csv

# Check System Resources
top -b -n 1
free -h
df -h

# Emergency Stop
kill -9 $(pgrep -f "trading-brain")

# Emergency Restart
sudo systemctl restart trading-brain
```

---

## 🎉 Expected Behavior Tomorrow

### 09:00 AM - 09:15 AM
- System wakes up
- Loads configuration
- Connects to Dhan
- Fetches market data
- Initializes all agents
- **Status:** Warming up ✓

### 09:15 AM (Market Open)
- Trading begins
- Orders may be placed
- Positions monitored
- Logs written
- **Status:** Active trading ✓

### Throughout Day
- Continuous trading loops
- Risk checks
- Position management
- Performance logging
- **Status:** Running smoothly ✓

### 16:30 PM (Market Close)
- Final positions closed
- Day summary recorded
- System hibernates
- **Status:** Waiting for tomorrow ✓

---

## 📝 Important Reminders

1. **Paper Trading = Safe Testing**
   - No real money at risk
   - Perfect for learning
   - All trades are virtual

2. **Kill Switch = Safety Net**
   - Automatically stops risky trading
   - Can be manually reset
   - Always monitoring

3. **Logs = Complete History**
   - Every decision recorded
   - Review daily
   - Learn from results

4. **System = Hands-Off**
   - Automatic execution
   - No manual trading needed
   - Just monitor

5. **Tomorrow = Fresh Day**
   - Previous day's trades closed
   - New analysis starts
   - No carryover

---

## ✅ Final Checklist

- [x] OAuth token captured
- [x] Trading service running
- [x] Paper mode enabled
- [x] Kill switch ready
- [x] Firewall open
- [x] Auto-start enabled
- [x] Resources available
- [x] Logs clean

**Status: READY TO TRADE TOMORROW**

---

## 🚀 See You Tomorrow at 09:15 AM!

Your system will be trading automatically.

### Monitor these three files:
1. **Trading Log:** All decisions
2. **Paper Trades: Executed trades
3. **Kill Switch:** Emergency status

### Optional: Check Streamlit Dashboard
If you want to see visual dashboard:
```bash
ssh -i ~/.ssh/trading_vps root@178.18.252.24 -L 8501:localhost:8501
# Then visit: http://localhost:8501
```

---

**Good luck tomorrow! The system is ready. Let it work.** 🎯

