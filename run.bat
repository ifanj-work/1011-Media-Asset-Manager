@echo off
title 1011 Media Asset Manager
echo ===================================================
echo   1011 Media Asset Manager - Startup Script
echo ===================================================
echo.

:: Check if virtual environment exists
if exist .venv\Scripts\python.exe goto :start_app
echo [ERROR] Virtual environment (.venv) not found!
echo Please ensure the project is installed and .venv exists.
pause
exit /b 1

:start_app
:: Launch the default browser after a 2 second delay in the background
echo [INFO] Starting browser launcher in background...
start /b cmd /c "timeout /t 2 /nobreak > nul && start http://localhost:5000/search"

:: Start the Flask app in the foreground
echo [INFO] Starting Flask server...
echo [INFO] Press Ctrl+C in this window to stop the server.
echo.
.venv\Scripts\python.exe app.py
