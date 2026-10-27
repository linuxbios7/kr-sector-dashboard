@echo off
rem 더블클릭하면 수동 업데이트(수집 + GitHub 푸시/배포). 로컬 확인만 하려면: update.bat -NoPush
chcp 65001 >nul
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0update.ps1" %*
echo.
pause
