@echo off
setlocal
cd /d "%~dp0backend"
title Mercury v10 Backend - Port 8000
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
