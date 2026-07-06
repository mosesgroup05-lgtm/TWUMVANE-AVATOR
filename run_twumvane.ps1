# TWUMVANE Unified Platform Launcher
Write-Host "🚀 Starting TWUMVANE Platform..." -ForegroundColor Cyan

$rslVenv = "RSL\.venv\Scripts\python.exe"
$rslVenvAlt = "RSL\venv\Scripts\python.exe"
$signlangEnv = "RSL\signlang_env\Scripts\python.exe"

if (Test-Path $rslVenv) {
    Write-Host "✅ Found RSL virtual environment. Launching..." -ForegroundColor Green
    & $rslVenv app.py
}
elseif (Test-Path $rslVenvAlt) {
    Write-Host "✅ Found RSL venv. Launching..." -ForegroundColor Green
    & $rslVenvAlt app.py
}
elseif (Test-Path $signlangEnv) {
    Write-Host "✅ Found signlang_env. Launching..." -ForegroundColor Green
    & $signlangEnv app.py
}
else {
    Write-Host "⚠️  No virtual environment found in RSL folder." -ForegroundColor Yellow
    Write-Host "Installing missing dependencies to your current environment..." -ForegroundColor Cyan
    pip install opencv-python mediapipe torch torchvision flask flask-cors
    py app.py
}
