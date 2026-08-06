@echo off
setlocal
cd /d "%~dp0frontend"
title Mercury v10 Frontend - Port 3000
py -m http.server 3000
if errorlevel 1 (
  echo.
  echo Frontend failed to start. Port 3000 may already be in use.
  pause
)
