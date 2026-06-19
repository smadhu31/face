#!/usr/bin/env bash
# setup.sh — one-shot environment setup for FaceAttend
# Usage: bash setup.sh

set -e

echo "=================================================="
echo " FaceAttend - Setup"
echo "=================================================="

if ! command -v python3 &> /dev/null; then
    echo "Python3 is required but not found. Please install Python 3.9+."
    exit 1
fi

echo "[1/4] Creating virtual environment (venv)..."
python3 -m venv venv

echo "[2/4] Activating virtual environment..."
# shellcheck disable=SC1091
source venv/bin/activate

echo "[3/4] Upgrading pip and installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo "[4/4] Done."
echo "=================================================="
echo " Setup complete!"
echo " Activate the environment with:  source venv/bin/activate"
echo " Run the app with:               python app.py"
echo " Then open:                      http://127.0.0.1:5000"
echo " Default admin login:            admin / Admin@123"
echo "=================================================="
