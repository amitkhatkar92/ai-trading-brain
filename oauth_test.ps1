Clear-Host
Write-Host "OAuth Server Diagnostics" -ForegroundColor Cyan
Write-Host "========================" -ForegroundColor Cyan
Write-Host ""

$key = "$env:USERPROFILE\.ssh\trading_vps"
$host = "root@178.18.252.24"

function Test {
    param([string]$Name, [string]$Cmd)
    Write-Host "$Name... " -NoNewline
    try {
        $result = & ssh -i $key $host $Cmd 2>&1
        if ($LASTEXITCODE -eq 0) {
            $firstLine = ($result -split "`n" | Select-Object -First 1)
            Write-Host "OK" -ForegroundColor Green
            Write-Host "  > $($firstLine.Substring(0, [Math]::Min(60, $firstLine.Length)))`n"
        } else {
            Write-Host "FAIL (exit $LASTEXITCODE)" -ForegroundColor Red
            Write-Host "  > $($result -split "`n" | Select-Object -First 1)`n"
        }
    } catch {
        Write-Host "ERROR" -ForegroundColor Red  
        Write-Host "  > $($_.Exception.Message)`n"
    }
}

Test "1. Process Status" "ps aux | grep dhan_oauth_server | grep -v grep"
Test "2. Port 8000 Listening" "ss -tuln | grep 8000"
Test "3. Local /health" "curl -s http://localhost:8000/health"
Test "4. Local /callback" "curl -s 'http://localhost:8000/callback?code=test_code'"
Test "5. External /callback" "curl -s 'http://178.18.252.24:8000/callback?code=test_code'"
Test "6. Recent Logs" "tail -5 /root/ai-trading-brain/data/logs/oauth-callback.log 2>&1"
