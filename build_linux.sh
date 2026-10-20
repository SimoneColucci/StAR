#!/bin/bash
# =========================================================================
#  StAR - Build Linux executable
#  Prerequisites: Python 3.9+
# =========================================================================

set -e
cd "$(dirname "$0")"

echo
echo "=== StAR Linux Build ==="
echo

# --- 0. Look for Python ---
PYTHON=""
for cmd in python3 python; do
    if command -v "$cmd" &>/dev/null; then
        if "$cmd" --version &>/dev/null; then
            PYTHON="$cmd"
            break
        fi
    fi
done

if [ -z "$PYTHON" ]; then
    echo "================================================================"
    echo " ERROR: Python not found!"
    echo ""
    echo " Install Python 3.9+ with your system package manager:"
    echo "   Ubuntu/Debian:  sudo apt install python3 python3-pip python3-venv python3-tk"
    echo "   Fedora/RHEL:    sudo dnf install python3 python3-pip python3-tkinter"
    echo "   Arch:           sudo pacman -S python python-pip tk"
    echo "================================================================"
    exit 1
fi

echo "Python found: $PYTHON ($($PYTHON --version))"
echo

# --- 1. Check python3-tk (required for the GUI) ---
echo "[0] Checking python3-tk..."
if ! $PYTHON -c "import tkinter" 2>/dev/null; then
    echo "    python3-tk not found, installing..."
    if command -v apt &>/dev/null; then
        sudo apt install -y python3-tk python3-venv
    elif command -v dnf &>/dev/null; then
        sudo dnf install -y python3-tkinter
    elif command -v pacman &>/dev/null; then
        sudo pacman -S --noconfirm tk
    else
        echo "ERROR: install python3-tk manually and run the script again."
        exit 1
    fi
fi

# --- 2. Create virtual environment (avoids externally-managed error) ---
echo
echo "[1/4] Preparing virtual environment..."
if [ ! -d "venv" ]; then
    $PYTHON -m venv venv
fi
source venv/bin/activate

# --- 3. Install Python dependencies ---
echo "[2/4] Installing dependencies..."
python -m pip install --upgrade pip
python -m pip install numpy scipy matplotlib pandas scikit-image Pillow pyinstaller
# Stereology module (optional): requires pysizeunfolder from GitHub (needs git)
python -m pip install "git+https://github.com/thomasvdj/pysizeunfolder" || \
    echo "WARNING: pysizeunfolder not installed (Stereology module unavailable)."

# --- 4. Build with PyInstaller ---
echo
echo "[3/4] Building executable..."
python -m PyInstaller StAR.spec --noconfirm

# --- 5. Copy example data files ---
echo
echo "[4/4] Copying example data..."
if [ -d "data" ]; then
    cp -r data dist/StAR/
fi

# Make it executable
chmod +x dist/StAR/StAR

echo
echo "========================================="
echo "  Build completed!"
echo "  The application is in: dist/StAR/"
echo "  Executable: dist/StAR/StAR"
echo "========================================="
echo
