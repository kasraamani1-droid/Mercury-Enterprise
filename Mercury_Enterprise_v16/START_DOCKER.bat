@echo off
cd /d "%~dp0"
title Mercury Enterprise V2.0 Docker Compose
if not exist .env (
  echo ERROR: .env is missing.
  echo Copy .env.example to .env and set MERCURY_AUTH_PASSWORD before starting.
  pause
  exit /b 1
)
findstr /B /C:"MERCURY_AUTH_PASSWORD=" .env >nul
if errorlevel 1 (
  echo ERROR: MERCURY_AUTH_PASSWORD is not defined in .env
  pause
  exit /b 1
)
docker compose up --build
