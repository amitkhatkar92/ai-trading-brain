@echo off
REM SSH Key Generator for Windows PowerShell
REM Run this to generate SSH keys for VPS access

echo.
echo Generating SSH Keys for Contabo VPS...
echo =======================================
echo.

REM Create .ssh directory
mkdir %USERPROFILE%\.ssh 2>nul

REM Generate ED25519 keypair  
echo When prompted for passphrase, just press ENTER twice (no password)
echo.
ssh-keygen -t ed25519 -f "%USERPROFILE%\.ssh\trading_vps" -C "amitkhatkar92@gmail.com"

echo.
echo SSH keys generated!
echo.
echo Private key location: %USERPROFILE%\.ssh\trading_vps
echo Public key location: %USERPROFILE%\.ssh\trading_vps.pub
echo.
echo View private key (for GitHub):
echo   type "%USERPROFILE%\.ssh\trading_vps"
echo.
echo View public key (for VPS):
echo   type "%USERPROFILE%\.ssh\trading_vps.pub"
echo.
pause
