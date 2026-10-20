#!/usr/bin/env python3
"""
Command-line entry point for the Analyze module.
Equivalent of the MATLAB run/Analyze.m

Usage:
    cd /var/www/html/StAR/python/run
    python analyze.py
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.run_analyze import run_analyze


img_data = {
    'input_dir': '../data/CropImages',
    'input_file': ['cataclasiteA_micro_001.jpg', 'cataclasiteA_sample_002.jpg'],
    'output_dir': '../output',
    # meters per pixel [m/pixel]
    'px2m': [0.1257e-4, 0.0116e-4],
    # grouping used for the per-group property figures (Measurements/Figures)
    'groups': [{'name': 'CataclasiteA', 'indices': [0, 1]}],
}

technique = {
    # segmentation: intensity range [min, max] per file
    'range': [[0, 100], [0, 100]],
}


if __name__ == '__main__':
    run_analyze(img_data, technique)
