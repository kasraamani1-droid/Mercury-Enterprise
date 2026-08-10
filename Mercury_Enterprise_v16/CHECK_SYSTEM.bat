@echo off
cd /d "%~dp0"
echo Mercury Enterprise V2.0 (16.0.0) system check
echo =============================================
where py >nul 2>nul && (echo [OK] Python launcher found) || (echo [FAIL] Python launcher not found)
if exist backend\requirements.txt (echo [OK] Backend files found) else (echo [FAIL] Backend files missing)
if exist frontend\index.html (echo [OK] Frontend files found) else (echo [FAIL] Frontend files missing)
if defined MERCURY_AUTH_PASSWORD (echo [OK] MERCURY_AUTH_PASSWORD is set) else (echo [WARN] MERCURY_AUTH_PASSWORD not set in this shell — required to start backend)
if exist .env (echo [OK] .env present) else (echo [WARN] .env missing — copy from .env.example)
powershell -NoProfile -Command "foreach($p in 3000,8000){$x=Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue;if($x){Write-Host ('[WARN] Port '+$p+' is in use')}else{Write-Host ('[OK] Port '+$p+' is available')}}"
echo.
pause
