# AI Trading Brain — Auto-Start Setup for Windows

## Overview

Your AI Trading Brain system is now configured to **start automatically when your PC powers on or boots**, without requiring any manual login or intervention.

---

## One-Time Setup Required: Register the Scheduled Task

Because this is your first setup, you need to register the Windows scheduled task. This is **one-time only** — after this, the system runs automatically.

### Step 1: Run as Administrator

**Option A: Using Batch File (Easiest)**

1. Open File Explorer
2. Navigate to: `C:\Users\UCIC\OneDrive\Desktop\ai_trading_brain\scripts\`
3. Find `RegisterTask-Admin.bat`
4. **Right-click** on it
5. Select **"Run as administrator"**
6. Click **"Yes"** when Windows asks for permission
7. Wait for the completion message

**Option B: Using PowerShell**

1. Open PowerShell (Windows + R, type `powershell`, press Enter)
2. **Right-click** the PowerShell window title bar
3. Select **"Run as administrator"**
4. Paste this command and press Enter:

```powershell
C:\Users\UCIC\OneDrive\Desktop\ai_trading_brain\scripts\RegisterTask-Admin.ps1
```

### Step 2: Verify Setup

After the script completes successfully, verify the task is registered:

```cmd
schtasks /query /tn AiTradingBrain
```

You should see task details displayed.

---

## What Happens Automatically

### Tomorrow Morning at 8:00 AM

When your PC powers on or 8:00 AM arrives:

1. ✅ **Dashboard starts** on `http://localhost:8501`
   - Displays live trading status, signals, and performance

2. ✅ **Trading Brain starts** in scheduler mode
   - Runs full 17-layer cycle every 30 seconds during market hours
   - Makes trading decisions in **paper trading mode** (no real money)
   - Logs all output to: `logs\scheduler.log`

3. ✅ **Market monitoring begins**
   - Scans 30+ Nifty 100 stocks
   - Analyzes market regime (bull, bear, range, volatile)
   - Generates signals based on evolved strategies

### If PC is Off at 8:00 AM

When you power on anytime after that:

1. ✅ Task scheduler detects logon
2. ✅ Automatically starts the system within seconds
3. ✅ Dashboard and trading brain become active

### No Login Required

- ✅ Works **before** you log in
- ✅ Works **while** you're logged in
- ✅ Works **after** you log out
- The system runs under your Windows user account with automatic privileges

---

## Monitor & Access

### View the Dashboard

Once running, open your browser and go to:
```
http://localhost:8501
```

**What you'll see:**
- Live regime indicator (Bull/Bear/Range/Volatile)
- VIX level and market condition
- Real-time signal funnel
- Executed trades and P&L
- Strategy performance breakdown

### Check Logs

All activity is logged to:
- **Main log:** `data/logs/scheduler.log`
- **Dashboard log:** `data/logs/dashboard.log`
- **Trade journal:** `data/paper_trades.csv`

Example log command (PowerShell):
```powershell
Get-Content C:\Users\UCIC\OneDrive\Desktop\ai_trading_brain\logs\scheduler.log -Tail 20
```

---

## If You Need to Stop or Restart

### Manually Stop the Task

```cmd
schtasks /end /tn AiTradingBrain
```

### Manually Start the Task (for testing)

```cmd
schtasks /run /tn AiTradingBrain
```

### Uninstall the Scheduled Task

```cmd
schtasks /delete /tn AiTradingBrain /f
```

Then run `RegisterTask-Admin.bat` again to re-register if needed.

---

## Deployment Summary

| Component | Status | Details |
|-----------|--------|---------|
| Task Name | AiTradingBrain | Registered in Windows Task Scheduler |
| Schedule  | Weekdays 08:00 | Monday–Friday at 8:00 AM IST |
| Fallback  | At Logon | Catches any missed 08:00 AM starts |
| Executable | autostart.bat | `scripts/autostart.bat` |
| Working Dir | Project Root | `C:\Users\UCIC\OneDrive\Desktop\ai_trading_brain` |
| Run Level | Limited | No admin required at runtime |
| Mode | Paper Trading | No real money; ₹100K reference capital |
| Dashboard | Port 8501 | http://localhost:8501 |
| Logs | logs/ directory | scheduler.log, dashboard.log |

---

## Tomorrow's Timeline

| Time | Event | Status |
|------|-------|--------|
| 08:00 AM | Scheduled task triggers | Dashboard starts |
| 08:00 AM | Trading Brain initializes | Market scan begins |
| 08:00-15:30 | Market hours cycle | 30-second intervals |
| 15:30 | EOD summary written | `data/paper_trading_daily.json` |
| 15:31 | Dashboard updates | Final state shown |

---

## Testing (Optional)

To test **today** without waiting:

1. Open Command Prompt (as regular user)
2. Run:
   ```cmd
   schtasks /run /tn AiTradingBrain /i
   ```
3. It will start immediately
4. Check the dashboard on `http://localhost:8501`

---

## Troubleshooting

**Q: "Access is denied" when running RegisterTask-Admin.bat**
- A: You must right-click and select "Run as administrator"

**Q: Task created but nothing happens at 8:00 AM**
- A: Check logs at `logs/scheduler.log` — also verify Windows Task Scheduler is enabled
- Command: `schtasks /query /tn AiTradingBrain /v`

**Q: Dashboard not accessible at localhost:8501**
- A: Check if port 8501 is blocked by firewall
- Or: Check `logs/dashboard.log` for startup errors

**Q: I want to change the start time**
- A: Delete the task and re-run RegisterTask-Admin.bat, or manually edit in Task Scheduler GUI

---

## Questions?

Check the logs for detailed error messages:
```cmd
type logs\scheduler.log
```

Or review the system readiness test:
```cmd
python system_readiness_test.py
```

---

**Your system is now ready. Enjoy automated trading! 🚀**
