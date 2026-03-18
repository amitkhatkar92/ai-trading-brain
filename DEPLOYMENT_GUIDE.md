# 🚀 AI Trading Brain — Hybrid Deployment Guide

**Setup Date:** March 18, 2026  
**Deployment Model:** Hybrid (GitHub → Docker → Contabo VPS)  
**VPS Details:** 178.18.252.24 (Contabo, EU, 10 SSD)  

---

## 📋 Overview

```
Local Development
    ↓ (git push)
GitHub Repository
    ↓ (webhook trigger)
GitHub Actions
    ├─ Build Docker image
    ├─ Push to Docker Hub
    └─ Deploy to VPS (178.18.252.24)
    ↓
Contabo VPS (docker-compose)
    ├─ ai-trading-brain (scheduler + paper trading)
    └─ streamlit-dashboard (monitoring)
```

---

## 🔑 Prerequisites

- ✅ GitHub account (free tier OK)
- ✅ Docker Hub account (free tier OK)
- ✅ Contabo VPS with root access (already have: 178.18.252.24)
- ✅ SSH key pair for VPS authentication
- ✅ AI_Trading_Brain folder already on VPS (via WinSCP)

---

## ⚡ Quick Start (5 Steps)

### Step 1: Set Up GitHub Repository

```powershell
# Navigate to project
cd c:\Users\UCIC\OneDrive\Desktop\ai_trading_brain

# Initialize git (if not already)
git init

# Add all files
git add --all

# Create initial commit
git commit -m "Initial AI Trading Brain setup - Hybrid deployment"

# Create GitHub repo at: https://github.com/new
# Name: ai-trading-brain
# Description: Hierarchical Multi-Agent Trading System

# Add remote and push
git remote add origin https://github.com/amitkhatkar92/ai-trading-brain.git
git branch -M main
git push -u origin main
```

### Step 2: Configure GitHub Secrets

Go to: `https://github.com/amitkhatkar92/ai-trading-brain/settings/secrets/actions`

Add these secrets:

| Secret Name | Value | Notes |
|---|---|---|
| `DOCKER_USERNAME` | `amitkhatkar92` | Pre-filled ✅ |
| `DOCKER_PASSWORD` | Your Docker Hub access token | dockerhub.com → account → security |
| `VPS_HOST` | `178.18.252.24` | Pre-filled ✅ |
| `VPS_SSH_KEY` | Your private SSH key | Generate: `ssh-keygen -t ed25519` |
| `TELEGRAM_BOT_TOKEN` | (Optional) Bot token | Telegram BotFather |
| `TELEGRAM_CHAT_ID` | (Optional) Chat ID | Your Telegram chat ID |

#### How to Generate SSH Key for VPS:

```powershell
# Generate new SSH keypair
ssh-keygen -t ed25519 -f "C:\Users\UCIC\.ssh\trading_vps" -N ""

# View private key (for GitHub secret)
Get-Content C:\Users\UCIC\.ssh\trading_vps
```

Then copy the **entire private key** (with `-----BEGIN OPENSSH PRIVATE KEY-----` header) to GitHub secret `VPS_SSH_KEY`.

Add public key to VPS:
```bash
# On VPS (178.18.252.24)
echo "YOUR_PUBLIC_KEY_CONTENT" >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
```

### Step 3: Prepare VPS with Docker

**SSH into your VPS:**

```bash
ssh root@178.18.252.24
```

**Run setup script:**

```bash
cd /root
curl -O https://raw.githubusercontent.com/amitkhatkar92/ai-trading-brain/main/scripts/setup-vps.sh
bash setup-vps.sh
```

This installs:
- ✅ Docker & Docker Compose
- ✅ Git
- ✅ Project directories
- ✅ Monitoring scripts

**Configure .env on VPS:**

```bash
# Edit your broker credentials
nano /root/ai-trading-brain/.env

# Example:
# ACTIVE_BROKER=zerodha
# ZERODHA_API_KEY=your_key
# ZERODHA_API_SECRET=your_secret
```

### Step 4: Deploy (First Time - Manual)

**On VPS:**

```bash
cd /root/ai-trading-brain

# Pull latest code
git clone https://github.com/amitkhatkar92/ai-trading-brain.git .

# Start containers
docker-compose up -d

# Verify
docker ps
docker logs ai-trading-brain
```

### Step 5: Automate Future Deployments

**Now every time you push to GitHub:**

1. GitHub Actions automatically:
   - Builds Docker image
   - Pushes to Docker Hub
   - Deploys to VPS (178.18.252.24)
   - Restarts containers
   - Notifies via Telegram (if enabled)

**You're done! 🎉**

---

## 📊 Architecture on VPS

```
Contabo VPS (178.18.252.24)
│
├─ ai-trading-brain (Container)
│  ├─ main.py --schedule --paper
│  ├─ All 17 layers running
│  ├─ Data: /app/data (persisted)
│  └─ Logs: /app/data/logs (persisted)
│
├─ streamlit-dashboard (Container)
│  ├─ Control Tower dashboard
│  ├─ Port 8501 (http://178.18.252.24:8501)
│  └─ Read-only access to /app/data
│
└─ Volumes (persisted across restarts)
   └─ ./data/
      ├─ paper_trades.csv
      ├─ strategy_performance.json
      ├─ logs/
      └─ *.db
```

---

## 🔄 Update Workflow

### Local Development → Cloud Deployment

**All you do:**

```powershell
# 1. Make changes locally
# 2. Test locally
# 3. Commit and push
git add src/
git commit -m "Fix risk control logic"
git push origin main
```

**Automatic:**
- GitHub Actions triggers
- Docker image built & pushed
- VPS pulls new code & image
- Containers restart with latest
- ✅ Done!

---

## 📈 Monitoring

### Check Status on VPS

```bash
# SSH into VPS
ssh root@178.18.252.24

# Monitor health
bash /root/ai-trading-brain/monitor.sh
```

**Output shows:**
- ✅ Container running status
- 📊 Memory/CPU usage
- 🔍 Latest paper trades
- 💾 Disk usage

### Stream Logs (Real-time)

```bash
docker logs -f ai-trading-brain
```

### Check Paper Trades

```bash
tail -20 /root/ai-trading-brain/data/paper_trades.csv
```

---

## 🛑 Troubleshooting

### Container won't start

```bash
# Check error
docker logs ai-trading-brain

# Check if port is in use
netstat -tlnp | grep 8501

# Force restart
docker-compose down
docker-compose up -d
```

### Deployment failed from GitHub Actions

Check: `https://github.com/YOUR_USERNAME/ai-trading-brain/actions`

**Common issues:**
- SSH key not in secrets → Add SSH key to GitHub secrets
- Docker credentials wrong → Verify Docker Hub credentials
- VPS SSH unreachable → Check VPS firewall, SSH key perms

### Out of disk space

```bash
# Check disk
df -h

# Clear Docker cache
docker system prune -a

# Check data directory size
du -sh /root/ai-trading-brain/data/
```

---

## 🔐 Security Best Practices

- ✅ Never commit `.env` (already in `.gitignore`)
- ✅ Use SSH keys, not passwords (~1000x safer)
- ✅ Rotate Docker Hub token yearly
- ✅ SSH: Only root user, key-based auth only
- ✅ Logs: Review `/root/ai-trading-brain/data/logs/` for anomalies
- ✅ Backup: Export paper trades weekly

```bash
# Backup trades
cd /root/ai-trading-brain
tar -czf data_backup_$(date +%Y%m%d).tar.gz data/
```

---

## 📋 Commands Reference

| Task | Command |
|---|---|
| Start containers | `docker-compose up -d` |
| Stop containers | `docker-compose down` |
| View logs | `docker logs ai-trading-brain` |
| SSH into container | `docker exec -it ai-trading-brain bash` |
| Rebuild image | `docker-compose build --no-cache` |
| Monitor status | `bash /root/ai_trading_brain/monitor.sh` |
| Pull latest code | `cd /root/ai_trading_brain && git pull` |
| Restart container | `docker-compose restart ai-trading-brain` |

---

## 🎯 Next Steps

1. ✅ Create GitHub repository
2. ✅ Add GitHub Secrets
3. ✅ SSH into VPS & run setup-vps.sh
4. ✅ Configure .env on VPS
5. ✅ Manual first deployment
6. ✅ Test: Make a dummy commit → Verify auto-deploy
7. ✅ Monitor via dashboard (port 8501)

---

## 📞 Support

- **GitHub Actions Logs:** `https://github.com/amitkhatkar92/ai-trading-brain/actions`
- **Docker Hub:** `https://hub.docker.com/r/amitkhatkar92/ai-trading-brain`
- **VPS Logs:** `ssh root@178.18.252.24 && docker logs ai-trading-brain`

---

**Deployment Model:** Hybrid (Git + Docker + CI/CD)  
**Status:** ✅ Ready to Deploy  
**Last Updated:** March 18, 2026
