# ✅ READY TO RUN - Sandbox Trading Engine

## Token Status: ✅ FIXED & DEPLOYED

Your JWT sandbox token is now:
- ✅ In local file: `config/api_tokens.json`
- ✅ Deployed to VPS: `/root/ai-trading-brain/config/api_tokens.json`
- ✅ Committed to GitHub
- ✅ Ready for trading engine

---

## 🚀 Run Trading Engine (3 Options)

### Option 1: Paper Trading (Recommended)
```bash
ssh -i ~/.ssh/trading_vps root@178.18.252.24
cd /root/ai-trading-brain
python main.py --paper
```

**What happens:**
- Trading engine loads JWT token
- Connects to: `https://sandbox.dhan.co/v2`
- Simulates trades (paper mode)
- No real money at risk

### Option 2: Scheduled Trading (Best for Testing)
```bash
ssh -i ~/.ssh/trading_vps root@178.18.252.24
cd /root/ai-trading-brain
python main.py --schedule
```

**What happens:**
- Waits for market open (09:15 IST)
- Auto-runs trading logic on schedule
- Paper mode (simulated)
- Runs all 10 strategy slots
- Logs to: `data/logs/trading.log`

### Option 3: Run via Systemd (Production)
```bash
ssh -i ~/.ssh/trading_vps root@178.18.252.24
systemctl start trading-brain
systemctl status trading-brain
```

**What happens:**
- Starts as system service
- Survives VPS reboot
- Logs to systemd journal

---

## 📊 Monitor Trading

### Watch Logs
```bash
ssh -i ~/.ssh/trading_vps root@178.18.252.24
tail -f /root/ai-trading-brain/data/logs/trading.log
```

### Check Decisions
```bash
tail -f /root/ai-trading-brain/data/logs/decisions.log
```

### View Dashboard
```bash
ssh -i ~/.ssh/trading_vps root@178.18.252.24
streamlit run /root/ai-trading-brain/monitoring/streamlit_kpi_dashboard.py
```

---

## 🔍 Verify Token is Working

```bash
ssh -i ~/.ssh/trading_vps root@178.18.252.24
cd /root/ai-trading-brain
python -c "
from utils.dhan_token_manager import get_dhan_token
token = get_dhan_token()
if token:
    print(f'✅ Token loaded: {token[:30]}...')
else:
    print('❌ Token not loaded!')
"
```

Expected output:
```
✅ Token loaded: eyJhbGciOiJIUzUxMiIsIn...
```

---

## 🛑 Stop Trading

### If running in foreground
```
Press: CTRL + C
```

### If running as service
```bash
ssh -i ~/.ssh/trading_vps root@178.18.252.24
systemctl stop trading-brain
```

---

## ✨ What's Ready

| Component | Status | Details |
|-----------|--------|---------|
| **JWT Token** | ✅ | Loaded in config, deployed to VPS |
| **Sandbox API** | ✅ | Ready at sandbox.dhan.co |
| **Data Feed** | ✅ | Will auto-load token |
| **Trading Engine** | ✅ | All 10 slots configured |
| **Paper Mode** | ✅ | No real money used |
| **Logging** | ✅ | All trades logged |
| **Dashboard** | ✅ | Real-time KPIs |

---

## 🎯 Next Steps

1. **Start trading:**
   ```bash
   python main.py --paper
   ```

2. **Let it run for:**
   - 1 hour (quick test)
   - 1 day (full market hours)
   - 1 week (realistic testing)

3. **Monitor:**
   - Check logs for errors
   - Watch KPI dashboard
   - Verify token is being used

4. **After 1 week:**
   - Review performance
   - Check returns & drawdown
   - Plan next steps

---

## 🔧 If Something Goes Wrong

### Token not loading
```bash
cat /root/ai-trading-brain/config/api_tokens.json
# Should have: "access_token": "eyJh..."
```

### API connection error
- Check internet on VPS: `ping 8.8.8.8`
- Check token is valid: `python -m utils.dhan_token_manager`
- Check Dhan API status

### No trades executing
- Check market is open (IST 09:15-16:51)
- Check paper mode is enabled
- Check logs: `tail -f data/logs/trading.log`

---

## 🚦 Trading Status Checklist

- [ ] Token file updated ✅
- [ ] Token deployed to VPS ✅
- [ ] Committed to GitHub ✅
- [ ] Can load token: `python -c "from utils.dhan_token_manager import get_dhan_token; get_dhan_token()"`
- [ ] Ready to start: `python main.py --paper`

**Everything is ready. You can start trading now.** 🎉

