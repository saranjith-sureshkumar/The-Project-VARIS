@echo off
title VARIS V3 Setup
echo.
echo  ╔══════════════════════════════════════╗
echo  ║   V.A.R.I.S  Setup  (Windows)       ║
echo  ╚══════════════════════════════════════╝
echo.

echo [1/6] Creating virtual environment...
python -m venv varis_env
if errorlevel 1 (echo Python not found. Install from python.org & pause & exit /b 1)

echo [2/6] Activating...
call varis_env\Scripts\activate

echo [3/6] Installing packages...
pip install -r requirements.txt
if errorlevel 1 (echo Package install failed. Check requirements.txt & pause & exit /b 1)

echo [4/6] Installing Chromium for browser control...
playwright install chromium

echo [5/6] Copying .env template...
if not exist .env copy .env.template .env

echo [6/6] Checking Ollama...
where ollama >nul 2>&1
if errorlevel 1 (
    echo.
    echo  Ollama not found. Download from: https://ollama.ai
    echo  After installing, run: ollama pull phi3
) else (
    echo  Ollama found.
)

echo.
echo  ╔══════════════════════════════════════╗
echo  ║   Setup complete!  Next steps:       ║
echo  ║                                      ║
echo  ║  1. Open .env and add:               ║
echo  ║     - GROQ_API_KEY (free at          ║
echo  ║       console.groq.com)              ║
echo  ║     - Gmail App Password             ║
echo  ║                                      ║
echo  ║  2. Open a new terminal and run:     ║
echo  ║     ollama serve                     ║
echo  ║                                      ║
echo  ║  3. Run VARIS:                       ║
echo  ║     python main.py                   ║
echo  ╚══════════════════════════════════════╝
echo.
pause
