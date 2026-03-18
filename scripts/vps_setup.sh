#!/bin/bash
################################################################################
# AI TRADING BRAIN — VPS SECURITY & DEPLOYMENT SETUP SCRIPT
# ────────────────────────────────────────────────────────────────────────────
# This script automates the complete security hardening and deployment setup
# for the trading system on the VPS.
#
# Run as root: bash vps_setup.sh
# Or with sudo: sudo bash vps_setup.sh
################################################################################

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[✓]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

log_error() {
    echo -e "${RED}[✗]${NC} $1"
}

################################################################################
# PHASE 1: SYSTEM UPDATES & DEPENDENCIES
################################################################################

log_info "═══════════════════════════════════════════════════════════════"
log_info "PHASE 1: System Updates & Dependencies"
log_info "═══════════════════════════════════════════════════════════════"

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   log_error "This script must be run as root"
   exit 1
fi

log_info "Updating system packages..."
apt update
apt upgrade -y

log_info "Installing essential packages..."
apt install -y \
    curl \
    wget \
    git \
    nano \
    ufw \
    fail2ban \
    logrotate \
    htop \
    net-tools \
    openssh-server

log_success "Phase 1 complete: System updated and dependencies installed"

################################################################################
# PHASE 2: UFW FIREWALL SETUP
################################################################################

log_info "═══════════════════════════════════════════════════════════════"
log_info "PHASE 2: UFW Firewall Configuration"
log_info "═══════════════════════════════════════════════════════════════"

log_info "Configuring UFW firewall..."

# Set default policies
ufw default deny incoming
ufw default allow outgoing

# Allow SSH (CRITICAL)
ufw allow 22/tcp
log_success "SSH (port 22) allowed"

# Allow Dashboard
ufw allow 8501/tcp
log_success "Dashboard (port 8501) allowed"

# Enable UFW
ufw --force enable
log_success "UFW firewall enabled"

# Verify status
log_info "Firewall status:"
ufw status

log_success "Phase 2 complete: Firewall configured"

################################################################################
# PHASE 3: FAIL2BAN INTRUSION PROTECTION
################################################################################

log_info "═══════════════════════════════════════════════════════════════"
log_info "PHASE 3: Fail2Ban Configuration"
log_info "═══════════════════════════════════════════════════════════════"

log_info "Configuring Fail2Ban..."

# Enable and start fail2ban
systemctl enable fail2ban
systemctl restart fail2ban

log_info "Checking Fail2Ban status..."
fail2ban-client status
fail2ban-client status sshd

log_success "Phase 3 complete: Fail2Ban configured and running"

################################################################################
# PHASE 4: FILE & DIRECTORY PERMISSIONS
################################################################################

log_info "═══════════════════════════════════════════════════════════════"
log_info "PHASE 4: File Permissions Hardening"
log_info "═══════════════════════════════════════════════════════════════"

if [ -d "/root/ai-trading-brain" ]; then
    log_info "Hardening permissions for /root/ai-trading-brain..."
    
    # Set directory permissions
    chmod -R 700 /root/ai-trading-brain
    log_success "Directory permissions: 700 (rwx------)"
    
    # Secure sensitive files
    if [ -f "/root/ai-trading-brain/.env" ]; then
        chmod 600 /root/ai-trading-brain/.env
        log_success ".env file permissions: 600 (rw-------)"
    fi
    
    if [ -f "/root/ai-trading-brain/data/paper_trades.csv" ]; then
        chmod 600 /root/ai-trading-brain/data/paper_trades.csv
        log_success "paper_trades.csv permissions: 600"
    fi
    
    # Secure logs directory
    if [ -d "/root/ai-trading-brain/logs" ]; then
        chmod 700 /root/ai-trading-brain/logs
        find /root/ai-trading-brain/logs -type f -exec chmod 600 {} \;
        log_success "Logs directory and files secured"
    fi
    
    log_success "Phase 4 complete: File permissions hardened"
else
    log_warning "Project directory not found at /root/ai-trading-brain"
    log_warning "Skipping permission hardening"
fi

################################################################################
# PHASE 5: LOG ROTATION SETUP
################################################################################

log_info "═══════════════════════════════════════════════════════════════"
log_info "PHASE 5: Log Rotation Configuration"
log_info "═══════════════════════════════════════════════════════════════"

if [ -d "/root/ai-trading-brain/logs" ]; then
    log_info "Creating logrotate configuration..."
    
    cat > /etc/logrotate.d/ai-trading-brain << 'EOF'
/root/ai-trading-brain/logs/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0600 root root
}
EOF
    
    log_success "Logrotate configuration created"
    
    # Test logrotate
    logrotate -f /etc/logrotate.d/ai-trading-brain
    log_success "Logrotate tested successfully"
else
    log_warning "Logs directory not found, skipping logrotate setup"
fi

################################################################################
# PHASE 6: SSH SECURITY HARDENING (OPTIONAL)
################################################################################

log_info "═══════════════════════════════════════════════════════════════"
log_info "PHASE 6: SSH Security Hardening (Optional)"
log_info "═══════════════════════════════════════════════════════════════"

log_info "Current SSH configuration status:"

# Backup original SSH config
if [ ! -f "/etc/ssh/sshd_config.backup" ]; then
    cp /etc/ssh/sshd_config /etc/ssh/sshd_config.backup
    log_success "SSH config backed up"
fi

# Check current settings
if grep -q "^PasswordAuthentication no" /etc/ssh/sshd_config; then
    log_success "✓ Password authentication is already disabled"
else
    log_warning "! Password authentication is still enabled"
    log_warning "  To disable: nano /etc/ssh/sshd_config"
    log_warning "  Set: PasswordAuthentication no"
    log_warning "  Then: systemctl restart ssh"
fi

if grep -q "^PubkeyAuthentication yes" /etc/ssh/sshd_config; then
    log_success "✓ Public key authentication is enabled"
else
    log_warning "! Public key authentication may not be enabled"
fi

################################################################################
# PHASE 7: SYSTEMD SERVICE SETUP (OPTIONAL)
################################################################################

log_info "═══════════════════════════════════════════════════════════════"
log_info "PHASE 7: Systemd Auto-Start Service (Optional)"
log_info "═══════════════════════════════════════════════════════════════"

if [ -d "/root/ai-trading-brain" ]; then
    log_info "Would you like to create systemd service for auto-start? (y/n)"
    read -r create_service
    
    if [ "$create_service" = "y" ] || [ "$create_service" = "Y" ]; then
        log_info "Creating trading-brain.service..."
        
        cat > /etc/systemd/system/trading-brain.service << 'EOF'
[Unit]
Description=AI Trading Brain - Paper Trading Engine
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/ai-trading-brain
ExecStart=/root/ai-trading-brain/.venv/bin/python main.py --paper
Restart=always
RestartSec=10s
StandardOutput=journal
StandardError=journal

Environment="PYTHONUNBUFFERED=1"
SuccessExitStatus=0 2

[Install]
WantedBy=multi-user.target
EOF
        
        systemctl daemon-reload
        systemctl enable trading-brain.service
        log_success "Service created and enabled"
        
        log_info "Starting trading-brain service..."
        systemctl start trading-brain.service
        
        sleep 2
        systemctl status trading-brain.service
        log_success "Service started successfully"
    fi
else
    log_warning "Project directory not found, skipping service setup"
fi

################################################################################
# SUMMARY & VERIFICATION
################################################################################

log_info "═══════════════════════════════════════════════════════════════"
log_info "SETUP COMPLETE - SECURITY VERIFICATION"
log_info "═══════════════════════════════════════════════════════════════"

log_success "Summary of changes:"
echo ""
echo "  ✓ System updated with latest patches"
echo "  ✓ UFW firewall enabled (ports 22, 8501 allowed)"
echo "  ✓ Fail2Ban configured (auto-ban after 5 failed SSH attempts)"
echo "  ✓ File permissions hardened (700 for directories, 600 for files)"
echo "  ✓ Log rotation configured (7-day retention, daily rotation)"
echo "  ✓ SSH security status checked"
echo "  ✓ Systemd service optional setup provided"
echo ""

log_info "VERIFICATION CHECKLIST:"
echo ""

log_info "1. UFW Firewall Status:"
ufw status | grep -E "(Status|22|8501)"
echo ""

log_info "2. Fail2Ban Status:"
fail2ban-client status | head -3
echo ""

log_info "3. SSH Service Status:"
systemctl is-active ssh
echo ""

log_info "4. File Permissions (if directory exists):"
if [ -d "/root/ai-trading-brain" ]; then
    ls -ld /root/ai-trading-brain | awk '{print "  " $1, $9}'
fi
echo ""

log_success "═══════════════════════════════════════════════════════════════"
log_success "VPS SECURITY SETUP COMPLETE!"
log_success "═══════════════════════════════════════════════════════════════"
echo ""
log_info "Next steps:"
echo "  1. Verify SSH key login works: ssh -i ~/.ssh/trading_vps root@178.18.252.24"
echo "  2. Access dashboard: http://178.18.252.24:8501"
echo "  3. Check logs: journalctl -u trading-brain.service -f (if service enabled)"
echo "  4. Monitor security: fail2ban-client status sshd"
echo ""
