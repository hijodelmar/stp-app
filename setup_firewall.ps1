# PowerShell script to add firewall rule for Flask server
# Run this as Administrator

Write-Host "Adding firewall rule for Flask STP Server on port 5001..." -ForegroundColor Cyan

try {
    # Add inbound rule for TCP port 5001
    New-NetFirewallRule -DisplayName "Flask STP Server" `
                        -Direction Inbound `
                        -Protocol TCP `
                        -LocalPort 5001 `
                        -Action Allow `
                        -Profile Private,Public `
                        -Description "Allow Flask STP application on port 5001"
    
    Write-Host "✅ Firewall rule added successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "You can now access the server from your iPhone at:" -ForegroundColor Yellow
    Write-Host "http://192.168.0.24:5001" -ForegroundColor White
    Write-Host ""
    Write-Host "Press any key to exit..."
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
}
catch {
    Write-Host "❌ Error: $_" -ForegroundColor Red
    Write-Host ""
    Write-Host "Make sure you run this script as Administrator!" -ForegroundColor Yellow
    Write-Host "Right-click on PowerShell and select 'Run as Administrator'" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Press any key to exit..."
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
}
