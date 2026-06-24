Write-Host "===================================================" -ForegroundColor Cyan
Write-Host "  1011 Media Asset Manager - Startup Script" -ForegroundColor Cyan
Write-Host "===================================================" -ForegroundColor Cyan
Write-Host ""

# Check if virtual environment exists
if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Error "Virtual environment (.venv) not found! Please ensure .venv exists."
    Read-Host "Press Enter to exit"
    exit 1
}

# Launch the default browser after a 2 second delay in the background
Write-Host "[INFO] Starting browser launcher in background..." -ForegroundColor Green
Start-Job -ScriptBlock { Start-Sleep -Seconds 2; Start-Process "http://localhost:5000/search" } | Out-Null

# Start the Flask app in the foreground
Write-Host "[INFO] Starting Flask server..." -ForegroundColor Green
Write-Host "[INFO] Press Ctrl+C to stop the server." -ForegroundColor Yellow
Write-Host ""
& .venv\Scripts\python.exe app.py
