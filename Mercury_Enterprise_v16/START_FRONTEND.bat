@echo off
setlocal
cd /d "%~dp0frontend"
title Mercury Enterprise V2.0 Frontend - Port 3000
if not exist "js\config.local.js" (
  echo Creating js\config.local.js for local API on :8000
  copy /Y "js\config.local.js.example" "js\config.local.js" >nul
)
py -m http.server 3000
if errorlevel 1 (
  echo.
  echo Frontend failed to start. Port 3000 may already be in use.
  pause
)
