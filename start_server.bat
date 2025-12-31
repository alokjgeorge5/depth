@echo off
cls
echo ============================================================
echo  DEPTH AI COUNCIL - SERVER STARTUP
echo ============================================================
echo.
echo  ⚠️  WARNING: Free tier = 100k tokens/day
echo  Each question = ~6k tokens (16 questions max/day)
echo  Budget wisely!
echo.

echo [1/3] Killing zombie processes...
taskkill /F /IM python.exe 2>nul
timeout /t 2 /nobreak >nul

echo [2/3] Verifying port 5000 is clear...
netstat -ano | findstr :5000
if %ERRORLEVEL% EQU 0 (
    echo    WARNING: Port 5000 still busy! Waiting 2 more seconds...
    timeout /t 2 /nobreak >nul
)

echo [3/3] Starting backend...
echo.
cd /d "%~dp0"
python backend\app.py

echo.
echo ============================================================
echo  SERVER STOPPED
echo ============================================================
pause
