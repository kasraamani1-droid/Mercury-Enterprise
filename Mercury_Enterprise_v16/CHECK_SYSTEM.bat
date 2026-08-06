@echo off
cd /d "%~dp0"
echo Mercury v15.0 system check
echo ==========================
where py >nul 2>nul && (echo [OK] Python launcher found) || (echo [FAIL] Python launcher not found)
if exist backend\requirements.txt (echo [OK] Backend files found) else (echo [FAIL] Backend files missing)
if exist frontend\index.html (echo [OK] Frontend files found) else (echo [FAIL] Frontend files missing)
powershell -NoProfile -Command "foreach($p in 3000,8000){$x=Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue;if($x){Write-Host ('[WARN] Port '+$p+' is in use')}else{Write-Host ('[OK] Port '+$p+' is available')}}"
echo.
pause
