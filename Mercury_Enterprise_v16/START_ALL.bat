@echo off
setlocal
cd /d "%~dp0"
title Mercury v15.0 Launcher

echo ===============================================
echo   Mercury v15.0 Production Reference Platform
echo ===============================================
echo.
where py >nul 2>nul
if errorlevel 1 (
  echo ERROR: Python launcher "py" was not found.
  echo Install Python 3.11+ and enable the Python launcher.
  pause
  exit /b 1
)

powershell -NoProfile -Command "$ports=3000,8000; foreach($p in $ports){if(Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue){Write-Host ('WARNING: Port '+$p+' is already in use. Stop older Mercury terminals first.') -ForegroundColor Yellow}}"

start "Mercury v10 Backend" cmd /k call "%~dp0START_BACKEND.bat"
timeout /t 4 /nobreak >nul
start "Mercury v10 Frontend" cmd /k call "%~dp0START_FRONTEND.bat"
timeout /t 2 /nobreak >nul
start "" http://localhost:3000

echo Mercury launch requested. Keep both terminal windows open.
timeout /t 3 /nobreak >nul
endlocal
