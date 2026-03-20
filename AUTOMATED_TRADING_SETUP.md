# 🤖 Fully Automated Trading - No Manual Commands Needed

## What Just Happened

Your trading system now **runs automatically during market hours** - zero manual intervention required.

---

## How It Works

### Timeline (IST)

| Time | Mode | Action | Service |
|------|------|--------|---------|
| **08:50** | Pre-market | ✅ Auto-start | Cron triggers systemd |
| **09:00-15:30** | Market hours | 🔄 Trading runs | `--schedule` mode |
| **15:40** | Post-market | ⏹️ Auto-stop | Cron triggers stop |
| **Weekends** | Off | — | No jobs run |

---

## Architecture: 3-Layer Automation

### Layer 1: Cron (Scheduling)
```
Cron Job @ 08:50 IST (weekdays)
    ↓
Runs: start-trading-market-hours.sh
```

### Layer 2: Systemd (Process Management)
```
Systemd Service: trading-brain-schedule
    ↓
Runs: python main.py --schedule
    ↓
Keeps running, auto-restarts if crashes
```

### Layer 3: Application (Schedule Logic)
```
main.py --schedule
    ↓
Respects config.py SCHEDULE (09:05-15:35)
    ↓
No trades outside market hours
```

---

## Setup Details

### ✅ What Was Deployed

1. **Service File**: `/etc/systemd/system/trading-brain-schedule.service`
   - Runs `--schedule` mode by default
   - Auto-restarts on crash (up to 3 retries)
   - Logs to systemd journal

2. **Start Script**: `/root/ai-trading-brain/scripts/start-trading-market-hours.sh`
   - Runs at 08:50 IST (03:20 UTC)
   - Starts the systemd service
   - Logs to `/var/log/trading-brain-cron.log`

3. **Stop Script**: `/root/ai-trading-brain/scripts/stop-trading-after-hours.sh`
   - Runs at 15:40 IST (10:10 UTC)
   - Stops the systemd service
   - Cleans up gracefully

4. **Cron Jobs** (in root's crontab):
   ```
   20 3 * * 1-5 /root/ai-trading-brain/scripts/start-trading-market-hours.sh
   10 10 * * 1-5 /root/ai-trading-brain/scripts/stop-trading-after-hours.sh
   ```

---

## Verification

### Check Service Status
```bash
ssh -i ~/.ssh/trading_vps root@178.18.252.24
systemctl status trading-brain-schedule
```

Expected output:
```
● trading-brain-schedule.service - AI Trading Brain - Automated Schedule Mode
   Loaded: loaded (/etc/systemd/system/trading-brain-schedule.service; enabled)
   Active: inactive (dead)
```
(Inactive is OK—it will start at 08:50 IST)

### Check Cron Jobs
```bash
crontab -l | grep trading
```

Expected output:
```
20 3 * * 1-5 /root/ai-trading-brain/scripts/start-trading-market-hours.sh
10 10 * * 1-5 /root/ai-trading-brain/scripts/stop-trading-after-hours.sh
```

### Watch Market Hours (Next Trading Day)
```bash
# Check if service started automatically at 08:50 IST
systemctl status trading-brain-schedule

# Watch logs in real-time
tail -f /var/log/trading-brain-cron.log
tail -f /root/ai-trading-brain/data/logs/trading.log
```

---

## What Happens Automatically

### 08:50 IST (Pre-market)
```
✅ Cron triggers start script
✅ systemd service starts
✅ Python engine loads
✅ Token loaded
✅ Waits for first scheduled task (09:05)
```

### 09:00-15:35 IST (Market hours)
```
09:05  → Regime detection + first scan
09:10  → Opportunity scan
09:20  → Strategy evaluation
09:45  → First trade window
10:30  → Mid-morning scan
13:00  → Afternoon analytics
15:00  → Pre-close trades
15:35  → EOD learning cycle
```

### 15:40 IST (Post-market)
```
✅ Cron triggers stop script
✅ Service stops gracefully
✅ All positions logged
✅ Performance saved
✅ Ready for next trading day
```

---

## Monitoring Dashboard

### View Live Logs
```bash
# Trading decisions in real-time
tail -f /root/ai-trading-brain/data/logs/decisions.log

# All trades
tail -f /root/ai-trading-brain/data/logs/trading.log

# System status
journalctl -u trading-brain-schedule -f
```

### Check If Running
```bash
ps aux | grep "main.py --schedule"
```

If running, you'll see:
```
root 12345  /root/.../python main.py --schedule
```

---

## Manual Control (If Needed)

### Force Start Now (Outside Market Hours)
```bash
systemctl start trading-brain-schedule
```

### Force Stop
```bash
systemctl stop trading-brain-schedule
```

### Check Status
```bash
systemctl status trading-brain-schedule
```

### View Recent Logs
```bash
journalctl -u trading-brain-schedule -n 50
```

### Disable Auto-Start (If You Want)
```bash
systemctl disable trading-brain-schedule
```

---

## Next Market Open (Tomorrow at 08:50 IST)

Your system will:

```
🤖 Auto-wake at 08:50 IST
📊 Load token automatically  
🔄 Start trading at 09:05 IST
📈 Execute all 10 strategies
📝 Log everything
⏹️ Auto-shutdown at 15:40 IST
```

**No commands. No manual intervention. Zero supervision needed.**

---

## Important Notes

### ⏰ Time Zones
- **IST** (Indian Standard Time) = UTC + 5:30
- Cron uses UTC internally
- Conversions:
  - 08:50 IST = 03:20 UTC
  - 15:40 IST = 10:10 UTC

### 📅 Weekday Only
The cron jobs only run **Monday-Friday** (`1-5` in crontab)
- No trading on Saturday/Sunday
- No trading on holidays (manual override if needed)

### 🔄 Auto-Restart
If the trading service crashes:
- Systemd will restart it automatically
- Up to 3 restart attempts (configurable)
- Restarts every 10 seconds

### 📊 VPS Uptime
- Service starts on VPS boot (due to `systemctl enable`)
- If VPS reboots during market hours, service restarts automatically
- If VPS reboots before 08:50, service waits for cron trigger

---

## Troubleshooting

### Service Not Starting
```bash
# Check service error
journalctl -u trading-brain-schedule -n 20

# Verify syntax
systemd-analyze verify trading-brain-schedule.service

# Try manual start
systemctl start trading-brain-schedule
```

### Cron Not Running
```bash
# Check if cron daemon is running
service cron status

# Restart cron
service cron restart

# View cron logs
tail -f /var/log/syslog | grep CRON
```

### Token Not Loading
```bash
# Verify token file exists
cat /root/ai-trading-brain/config/api_tokens.json

# Check permissions
ls -la /root/ai-trading-brain/config/
```

---

## Summary

✅ **Fully Automated**
- Starts automatically at 08:50 IST
- Runs scheduled trading all day
- Stops automatically at 15:40 IST

✅ **Reliable**
- Survives crashes (auto-restart)
- Survives VPS reboots
- Survives network blips

✅ **Monitored**
- Full logging enabled
- Real-time status visible
- KPI tracking active

✅ **Zero Manual Work**
- No `python main.py` commands needed
- No scheduled reminders
- No morning setup rituals

**Your trading brain runs 24/7 on cloud. It trades when markets open. It sleeps when markets close. Perfect automation.** 🚀

