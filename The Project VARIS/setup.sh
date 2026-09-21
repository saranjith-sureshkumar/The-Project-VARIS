#!/bin/bash
echo ""
echo "╔══════════════════════════════════════╗"
echo "║   V.A.R.I.S  Setup  (Linux/macOS)   ║"
echo "╚══════════════════════════════════════╝"
echo ""

echo "[1/6] Creating virtual environment..."
python3 -m venv varis_env || { echo "Python3 not found"; exit 1; }

echo "[2/6] Activating..."
source varis_env/bin/activate

echo "[3/6] Installing packages..."
# Skip pywin32 on non-Windows
pip install -r requirements.txt --ignore-requires-python \
    || pip install -r <(grep -v pywin32 requirements.txt)

echo "[4/6] Installing Chromium..."
playwright install chromium

echo "[5/6] Copying .env template..."
[ ! -f .env ] && cp .env.template .env

echo "[6/6] Checking system dependencies..."
# Tesseract for screen recall
if ! command -v tesseract &> /dev/null; then
    echo "  Optional: sudo apt install tesseract-ocr (for screen recall)"
fi
# espeak for offline voice
if ! command -v espeak-ng &> /dev/null; then
    echo "  Optional: sudo apt install espeak-ng (for offline voice)"
fi

echo ""
echo "╔══════════════════════════════════════╗"
echo "║   Setup complete!  Next steps:       ║"
echo "║                                      ║"
echo "║  1. Edit .env — add GROQ_API_KEY     ║"
echo "║     (free at console.groq.com)       ║"
echo "║                                      ║"
echo "║  2. Install Ollama: ollama.ai        ║"
echo "║     ollama pull phi3                 ║"
echo "║                                      ║"
echo "║  3. python main.py                   ║"
echo "╚══════════════════════════════════════╝"
echo ""
