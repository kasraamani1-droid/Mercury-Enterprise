@echo off
setlocal
cd /d "%~dp0"
title Mercury Enterprise V2.0 Launcher

echo ===============================================
echo   Mercury Enterprise V2.0 (package 16.0.0)
echo ===============================================
echo.
where py >nul 2>nul
if errorlevel 1 (
  echo ERROR: Python launcher "py" was not found.
  echo Install Python 3.11+ and enable the Python launcher.
  pause
  exit /b 1
)

if exist "%~dp0.env" (
  for /f "usebackq eol=# tokens=1,* delims==" %%A in ("%~dp0.env") do (
    if not "%%A"=="" if not "%%B"=="" set "%%A=%%B"
  )
)
if not defined MERCURY_AUTH_PASSWORD (
  echo ERROR: MERCURY_AUTH_PASSWORD is not set.
  echo Copy .env.example to .env and set a unique password, then re-run START_ALL.bat.
  pause
  exit /b 1
)

powershell -NoProfile -Command "$ports=3000,8000; foreach($p in $ports){if(Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue){Write-Host ('WARNING: Port '+$p+' is already in use. Stop older Mercury terminals first.') -ForegroundColor Yellow}}"

start "Mercury Enterprise V2.0 Backend" cmd /k call "%~dp0START_BACKEND.bat"
timeout /t 4 /nobreak >nul
start "Mercury Enterprise V2.0 Frontend" cmd /k call "%~dp0START_FRONTEND.bat"
timeout /t 2 /nobreak >nul
start "" http://localhost:3000

echo Mercury launch requested. Keep both terminal windows open.
timeout /t 3 /nobreak >nul
endlocal
