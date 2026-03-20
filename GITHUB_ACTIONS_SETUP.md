# GitHub Actions Deployment Setup

## ⚠️ Current Status
❌ GitHub Actions deployment failing due to missing SSH credentials
✅ VPS system trading normally (unaffected by CI/CD failure)

---

## 🔧 Setup Required (Only 4 Steps)

### Step 1: Get VPS SSH Key

**Already done** — SSH keys generated on VPS.

On your local machine, extract the key:
```powershell
$keyPath = "$env:USERPROFILE\.ssh\trading_vps"
ssh -i $keyPath root@178.18.252.24 "cat ~/.ssh/id_rsa"
```

**Copy the entire output** (starts with `-----BEGIN OPENSSH PRIVATE KEY-----`)

### Step 2: Add GitHub Secrets

Go to:
```
GitHub → Your Repo → Settings → Secrets and Variables → Actions
```

Click **"New repository secret"** and add these 4 secrets:

| Name | Value |
|------|-------|
| `VPS_HOST` | `178.18.252.24` |
| `VPS_USER` | `root` |
| `VPS_PORT` | `22` |
| `VPS_SSH_KEY` | **Paste the private key from Step 1** |

⚠️ **IMPORTANT**: The SSH key must be the FULL output including:
- `-----BEGIN OPENSSH PRIVATE KEY-----`
- All lines in between
- `-----END OPENSSH PRIVATE KEY-----`

### Step 3: Verify SSH File

On VPS, verify permissions are correct:
```bash
sudo chmod 600 ~/.ssh/id_rsa
sudo chmod 644 ~/.ssh/id_rsa.pub
sudo chmod 600 ~/.ssh/authorized_keys
sudo chmod 700 ~/.ssh
```

### Step 4: Test Deployment

Push a test commit:
```bash
git add GITHUB_ACTIONS_SETUP.md
git commit -m "test: GitHub Actions SSH deploy"
git push origin main
```

Watch GitHub Actions:
```
GitHub → Actions → "Deploy Trading Brain to VPS"
```

Expected output:
```
✅ Checkout code
✅ Deploy to VPS
  → cd /root/ai-trading-brain
  → git pull origin main
  → pip install -r requirements.txt
  → sudo systemctl restart trading-brain-schedule
  → ✅ Deployment complete
```

---

## 📋 What the Workflow Does (After Setup)

Each time you push to `main`:

1. **Checkout** latest code from GitHub
2. **SSH into VPS** using `VPS_SSH_KEY`
3. **Pull** latest changes from GitHub
4. **Install** any new Python dependencies
5. **Restart** the trading scheduler
6. **Verify** service is running

Total time: ~30 seconds

---

## 🎯 Result — Auto Updates

Now this pipeline works:

```
Local Edit → git push → GitHub Actions → VPS Auto-Updates → Trading Resumes
```

No manual SSH commands needed anymore!

---

## ❌ Troubleshooting

### Error: "ssh: no key found"

✅ Fix: Add `VPS_SSH_KEY` secret from Step 2

### Error: "permission denied (publickey)"

✅ Fix: Run on VPS:
```bash
chmod 600 ~/.ssh/id_rsa
chmod 600 ~/.ssh/authorized_keys
```

### Error: "repository not found"

✅ Fix: Ensure you're in `/root/ai-trading-brain` on VPS

### Workflow won't start

✅ Fix: Check if you pushed to `main` branch (not `develop`)

---

## 📊 Expected Workflow Run

Status → Job → Result

```
✅ Checkout code          Succeeded
✅ Deploy to VPS          Succeeded (was: FAILED)
```

After Step 2 secrets are added, the next `git push` will automatically trigger this workflow and deploy to your VPS!

---

## 🚀 Next Steps (After Setup Works)

1. Any code changes → just `git push`
2. Deployment happens automatically
3. Trading system stays running (no manual intervention needed)
4. Check logs: `kubectl logs -u trading-brain-schedule -f` on VPS

This is your final automation! ✨
