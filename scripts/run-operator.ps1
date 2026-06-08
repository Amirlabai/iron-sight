# Iron Sight operator console: slim API + history-fixer UI
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Backend = Join-Path $Root "backend"
$Fixer = Join-Path $Root "history-fixer"
$Python = Join-Path $Backend ".venv\Scripts\python.exe"
$OperatorMain = Join-Path $Backend "operator_main.py"

if (-not (Test-Path $Python)) {
    Write-Error "Backend venv not found at $Python. Run: cd backend; python -m venv .venv; pip install -r requirements.txt"
}

Write-Host "Starting operator API on http://127.0.0.1:8081 ..."
$apiJob = Start-Job -ScriptBlock {
    param($py, $main, $cwd)
    Set-Location $cwd
    & $py $main
} -ArgumentList $Python, $OperatorMain, $Backend

Start-Sleep -Seconds 2

Write-Host "Starting history-fixer UI (Vite) on http://127.0.0.1:5174 ..."
Write-Host "Press Ctrl+C to stop both."

try {
    Set-Location $Fixer
    npm run dev
} finally {
    Write-Host "Stopping operator API..."
    Stop-Job $apiJob -ErrorAction SilentlyContinue
    Remove-Job $apiJob -Force -ErrorAction SilentlyContinue
}
