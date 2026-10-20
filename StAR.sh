#!/bin/bash
# Quick launcher for the StAR GUI on Linux/macOS.
# Checks the Python dependencies, installs them if missing and starts
# star_gui.py.

set -e
cd "$(dirname "$0")"

# Find a Python interpreter
PYTHON=""
for cmd in python3 python; do
    if command -v "$cmd" &>/dev/null && "$cmd" --version &>/dev/null; then
        PYTHON="$cmd"
        break
    fi
done

if [ -z "$PYTHON" ]; then
    echo "ERROR: Python 3 not found."
    echo "Install Python 3.9+ and tkinter, then run again."
    exit 1
fi

echo "Python: $PYTHON ($($PYTHON --version))"

# Make sure tkinter is available (it must live in the system Python)
if ! $PYTHON -c "import tkinter" 2>/dev/null; then
    echo "ERROR: tkinter is not installed."
    echo "  Ubuntu/Debian: sudo apt install python3-tk"
    echo "  Fedora/RHEL:   sudo dnf install python3-tkinter"
    echo "  Arch:          sudo pacman -S tk"
    exit 1
fi

# If the dependencies are not already available with the system Python,
# create/use a local virtual environment (this also handles a missing pip
# and the "externally-managed-environment" error).
VENV_DIR="venv"
DEPS_CHECK="import numpy, scipy, matplotlib, pandas, skimage, PIL"

if ! $PYTHON -c "$DEPS_CHECK" 2>/dev/null; then
    if [ ! -d "$VENV_DIR" ]; then
        echo "Creating virtual environment ($VENV_DIR)..."
        if ! $PYTHON -m venv "$VENV_DIR" 2>/dev/null; then
            echo "ERROR: could not create the virtual environment."
            echo "Install the venv package, for example:"
            echo "  Ubuntu/Debian: sudo apt install python3-venv"
            exit 1
        fi
    fi

    # Use the venv Python from now on
    PYTHON="$VENV_DIR/bin/python"

    # Make sure pip is present in the venv (ensurepip fixes 'No module named pip')
    if ! $PYTHON -m pip --version &>/dev/null; then
        $PYTHON -m ensurepip --upgrade
    fi

    if ! $PYTHON -c "$DEPS_CHECK" 2>/dev/null; then
        echo "Installing dependencies into the virtual environment..."
        $PYTHON -m pip install --upgrade pip
        $PYTHON -m pip install -r requirements.txt
    fi
elif [ -d "$VENV_DIR" ]; then
    # A venv already exists: prefer it (keeps optional deps together).
    PYTHON="$VENV_DIR/bin/python"
fi

# Optional dependency for the Stereology module (not on PyPI, needs git).
# Best-effort: a failure here does not stop the other three modules.
if ! $PYTHON -c "import pysizeunfolder" 2>/dev/null; then
    echo "Installing pysizeunfolder (Stereology module)..."
    if ! $PYTHON -m pip install \
            "git+https://github.com/thomasvdj/pysizeunfolder"; then
        echo "WARNING: could not install 'pysizeunfolder'."
        echo "         The Stereology tab will be unavailable."
        echo "         It requires git; install git and run again, or:"
        echo "           $PYTHON -m pip install \\"
        echo "             git+https://github.com/thomasvdj/pysizeunfolder"
    fi
fi

# Launch the GUI
echo "Starting StAR GUI..."
$PYTHON star_gui.py
