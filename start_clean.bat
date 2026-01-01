@echo off
echo ================================================
echo TELEGRAM BOT CLEAN STARTUP
echo ================================================
echo.

echo Killing existing Python processes...
taskkill /F /IM python.exe /T >nul 2>&1
taskkill /F /IM python3.exe /T >nul 2>&1
taskkill /F /FI "WINDOWTITLE eq *python*" >nul 2>&1

echo Waiting for processes to terminate...
timeout /t 3 /nobreak >nul

echo Cleaning up session files...
del /F /Q *.session >nul 2>&1
del /F /Q *.db >nul 2>&1
del /F /Q *.sqlite >nul 2>&1
del /F /Q *.sqlite3 >nul 2>&1

echo Cleanup complete. Starting bot...
echo ================================================
python start_bot.py
