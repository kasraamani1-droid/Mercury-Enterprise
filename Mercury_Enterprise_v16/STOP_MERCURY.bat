@echo off
setlocal
echo This closes processes currently listening on Mercury ports 3000 and 8000.
choice /M "Continue"
if errorlevel 2 exit /b 0
powershell -NoProfile -Command "foreach($p in 3000,8000){Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue | ForEach-Object {Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue; Write-Host ('Stopped process on port '+$p)}}"
echo Mercury ports released.
pause
