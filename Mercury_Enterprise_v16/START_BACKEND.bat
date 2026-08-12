@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title Mercury Enterprise V2.0 Backend - Port 8000

REM Load optional package .env (KEY=VALUE lines; comments ignored)
if exist "%~dp0.env" (
  for /f "usebackq eol=# tokens=1,* delims==" %%A in ("%~dp0.env") do (
    if not "%%A"=="" if not "%%B"=="" set "%%A=%%B"
  )
)

if not defined MERCURY_AUTH_PASSWORD (
  echo ERROR: MERCURY_AUTH_PASSWORD is not set.
  echo Copy .env.example to .env and set a unique password before starting.
  pause
  exit /b 1
)

cd /d "%~dp0backend"
if not exist .venv (
  echo Creating Python environment...
  py -m venv .venv || goto :error
)
call .venv\Scripts\activate.bat || goto :error
py -m pip install --disable-pip-version-check -r requirements.txt || goto :error
py -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
goto :eof
:error
echo.
echo Backend failed to start. Review the error above.
pause
exit /b 1
