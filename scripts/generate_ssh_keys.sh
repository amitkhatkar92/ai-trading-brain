#!/bin/bash
# SSH Key Generator for Contabo VPS
# Save as: generate_ssh_keys.sh and run

echo "🔐 Generating SSH Keys for Contabo VPS..."
echo "=========================================="

# Create .ssh directory
mkdir -p ~/.ssh
chmod 700 ~/.ssh

# Generate ED25519 keypair (will prompt for passphrase - just press Enter twice)
ssh-keygen -t ed25519 -f ~/.ssh/trading_vps -C "amitkhatkar92@gmail.com"

echo ""
echo "✅ SSH keys generated!"echo ""
echo "📋 Your SSH key files:"
echo "  Private key: ~/.ssh/trading_vps"
echo "  Public key:  ~/.ssh/trading_vps.pub"
echo ""
echo "📝 View private key (for GitHub secret):"
echo "   cat ~/.ssh/trading_vps"
echo ""
echo "📝 View public key (for VPS authorized_keys):"
echo "   cat ~/.ssh/trading_vps.pub"
echo ""
