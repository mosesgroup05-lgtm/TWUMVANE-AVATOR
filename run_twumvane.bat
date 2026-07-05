@echo off
echo 🚀 Starting TWUMVANE Platform...

if exist "RSL\.venv\Scripts\python.exe" (
    echo ✅ Found RSL virtual environment. Launching...
    RSL\.venv\Scripts\python.exe app.py
) else if exist "RSL\venv\Scripts\python.exe" (
    echo ✅ Found RSL venv. Launching...
    RSL\venv\Scripts\python.exe app.py
) else if exist "RSL\signlang_env\Scripts\python.exe" (
    echo ✅ Found signlang_env. Launching...
    RSL\signlang_env\Scripts\python.exe app.py
) else (
    echo ⚠️  No virtual environment found. Attempting to run with global python...
    py app.py
)
pause
