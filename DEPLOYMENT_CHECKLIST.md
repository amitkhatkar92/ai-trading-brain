# 🚀 Deployment Checklist — AI Trading Brain

**Status:** Ready to Deploy  
**Deployment Date:** March 18, 2026  
**VPS:** 178.18.252.24 (Contabo, EU)  

---

## ✅ Pre-Deployment Tasks

### GitHub Setup (5 min)

- [ ] Create new repository:
  - URL: `https://github.com/amitkhatkar92/ai-trading-brain`
  - Name: `ai-trading-brain`
  - Visibility: Public or Private
  - Initialize without README (we have one)
- [ ] Navigate to repository → Settings → Secrets and variables → Actions

### Add GitHub Secrets (10 min)

Copy-paste these into GitHub Secrets:

#### 1. Docker Hub Credentials
```
Secret Name: DOCKER_USERNAME
Value: amitkhatkar92 ✅ (pre-filled)

Secret Name: DOCKER_PASSWORD
Value: [your dockerhub access token from settings/security]
```

#### 2. VPS Connection Details
```
Secret Name: VPS_HOST
Value: 178.18.252.24 ✅ (pre-filled)

Secret Name: VPS_SSH_KEY
Value: [your private SSH key - see below]
```

#### Generate SSH Key (Windows - PowerShell):
```powershell
# Generate keypair
ssh-keygen -t ed25519 -f "C:\Users\UCIC\.ssh\trading_vps" -N ""

# View and copy private key
Get-Content C:\Users\UCIC\.ssh\trading_vps

# View public key (for adding to VPS)
Get-Content C:\Users\UCIC\.ssh\trading_vps.pub
```

Copy the entire private key (with `-----BEGIN...` header) to GitHub secret `VPS_SSH_KEY`.

---

## 🖥️ VPS Preparation (15 min)

### SSH into VPS

```bash
ssh root@178.18.252.24
```

**If SSH key not yet added:**
```bash
# Create .ssh directory
mkdir -p ~/.ssh
chmod 700 ~/.ssh

# Add your public key
echo "your_public_key_content_here" >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
```

### Run Setup Script

```bash
cd /root
curl -O https://raw.githubusercontent.com/YOUR_GITHUB_USERNAME/ai-trading-brain/main/scripts/setup-vps.sh
bash setup-vps.sh
```

This automatically:
- ✅ Installs Docker & Docker Compose
- ✅ Installs Git
- ✅ Creates project directories
- ✅ Sets up monitoring scripts

### Configure Environment

```bash
# Edit broker credentials
nano /root/ai-trading-brain/.env

# Add your Zerodha/Dhan credentials:
ACTIVE_BROKER=zerodha
ZERODHA_API_KEY=your_key
ZERODHA_API_SECRET=your_secret
ZERODHA_ACCESS_TOKEN=your_token
```

Save: `Ctrl+O` → Enter → `Ctrl+X`

---

## 💻 Local Git Setup (5 min)

```powershell
cd c:\Users\UCIC\OneDrive\Desktop\ai_trading_brain

# Initialize if not already git repo
git init

# Add all files
git add --all

# Initial commit
git commit -m "Initial: AI Trading Brain with Docker + CI/CD setup"

# Add GitHub remote (replace YOUR_USERNAME)
git remote add origin https://github.com/YOUR_USERNAME/ai-trading-brain.git

# Rename branch to main and push
git branch -M main
git push -u origin main
```

---

## 🚀 First Deployment (Manual - 10 min)

### On VPS:
```bash
cd /root/ai-trading-brain

# Pull latest code from GitHub
git clone https://github.com/amitkhatkar92/ai-trading-brain.git .

# Verify docker-compose.yml exists
ls -la docker-compose.yml

# Start containers
docker-compose up -d

# Verify services running
docker ps

# Check logs
docker logs ai-trading-brain

# Monitor health
bash /root/ai-trading-brain/monitor.sh
```

---

## ✨ Automate Future Deployments

### Test Auto-Deployment

Make a trivial change locally:
```powershell
# Add a comment
echo "# Test deployment on $(date)" >> README.md

# Commit and push
git add README.md
git commit -m "Test: verify GitHub Actions auto-deploy"
git push origin main
```

### Watch Deployment

1. Go to: `https://github.com/amitkhatkar92/ai-trading-brain/actions`
2. Watch the workflow execute:
   - 🔨 Build Docker image
   - 📤 Push to Docker Hub
   - 🚀 Deploy to VPS (178.18.252.24)
3. Should complete in 3-5 minutes

### Verify on VPS

```bash
ssh root@178.18.252.24
docker logs -f ai-trading-brain
```

---

## 📊 Monitoring Dashboard

Once deployed, access:

**Dashboard:** http://178.18.252.24:8501

(Runs on streamlit-dashboard container)

---

## 🆘 Troubleshooting

### "Permission denied (publickey)"
- ✅ Check SSH key is added to ~/.ssh/authorized_keys on VPS
- ✅ Verify permissions: `chmod 600 ~/.ssh/authorized_keys`

### "docker-compose: command not found"
- Run setup-vps.sh again: `bash setup-vps.sh`

### Deployment hangs on "Deploy to Contabo VPS"
- SSH timeout — check firewall allows port 22
- Or check GitHub Actions log for SSH error

### Container exits immediately
```bash
docker logs ai-trading-brain
# Shows error reason
```

---

## 🎯 Success Indicators

✅ All done when you see:

```
✅ GitHub Actions workflow: PASSED
✅ Docker image pushed to Docker Hub
✅ VPS containers running: docker ps shows 2 containers
✅ Paper trades being logged: tail -5 /root/ai-trading-brain/data/paper_trades.csv
✅ Dashboard accessible: http://178.18.252.24:8501
```

---

## 📋 Post-Deployment

- [ ] Set up automated backups (weekly):
  ```bash
  crontab -e
  # Add: 0 2 * * 0 tar -czf /root/backups/trading_$(date +\%Y\%m\%d).tar.gz /root/ai-trading-brain/data
  ```

- [ ] Monitor disk usage weekly
- [ ] Review paper trades daily
- [ ] Update .env credentials if they expire

---

## 🔄 Day-to-Day Workflow

```
1. Code changes locally
   ↓
2. git add & git commit locally
   ↓
3. git push origin main
   ↓
4. GitHub Actions auto-triggers
   ↓
5. VPS updated automatically ✅
   ↓
6. Monitor via: bash monitor.sh
```

**That's it!** No manual VPS deployment ever again.

---

**Estimated Time to Full Deployment:** 40 minutes  
**Ongoing Maintenance:** 5 minutes/week  
**Support:** Check DEPLOYMENT_GUIDE.md for detailed info
