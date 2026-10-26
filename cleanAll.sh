#!/bin/bash
# =========================================================================
#  StAR - cleanAll
#  Removes build products, executables, caches and temporary files, leaving
#  only the source tree. Your results in output/ and the input data/ are NOT
#  touched.
#
#  Usage:
#     ./cleanAll.sh          clean build artifacts and caches
#     ./cleanAll.sh --venv   also remove the local virtual environment (venv/)
#     ./cleanAll.sh --output also remove the output/ results
#     ./cleanAll.sh --all    remove everything above (venv + output)
# =========================================================================

set -e
cd "$(dirname "$0")"

REMOVE_VENV=0
REMOVE_OUTPUT=0
for arg in "$@"; do
    case "$arg" in
        --venv)   REMOVE_VENV=1 ;;
        --output) REMOVE_OUTPUT=1 ;;
        --all)    REMOVE_VENV=1; REMOVE_OUTPUT=1 ;;
        *) echo "Unknown option: $arg"; exit 1 ;;
    esac
done

echo "=== StAR cleanAll (in $(pwd)) ==="

# --- PyInstaller build products / executables ----------------------------
rm -rf build dist dist_linux dist_windows
# --- Python byte-compiled caches -----------------------------------------
find . -type d -name '__pycache__' -prune -exec rm -rf {} + 2>/dev/null || true
find . -type f \( -name '*.pyc' -o -name '*.pyo' \) -delete 2>/dev/null || true
# --- Jupyter / tooling caches --------------------------------------------
find . -type d -name '.ipynb_checkpoints' -prune -exec rm -rf {} + 2>/dev/null || true
rm -rf .pytest_cache .mypy_cache .ruff_cache *.egg-info
# --- Editor / OS temporary files -----------------------------------------
find . -type f \( -name '*~' -o -name '*.swp' -o -name '*.tmp' -o -name '*.bak' \) -delete 2>/dev/null || true
find . -type f -name '.DS_Store' -delete 2>/dev/null || true

echo "Removed: build/, dist/, dist_linux/, dist_windows/, __pycache__/, *.pyc/*.pyo, .ipynb_checkpoints/, caches, temp files."

# --- Optional: virtual environment ---------------------------------------
if [ "$REMOVE_VENV" -eq 1 ]; then
    rm -rf venv
    echo "Removed: venv/ (it will be recreated on the next ./StAR.sh)."
fi

# --- Optional: results ----------------------------------------------------
if [ "$REMOVE_OUTPUT" -eq 1 ]; then
    rm -rf output
    echo "Removed: output/ (analysis results)."
fi

echo "=== Done. ==="
