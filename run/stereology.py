#!/usr/bin/env python3
"""
Command-line entry point for the Stereology module.
Equivalent of the MATLAB run/Stereology.m

Usage:
    cd /var/www/html/StAR/python/run
    python stereology.py
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.run_stereology import run_stereology


measure_data = {
    'input_dir': '../data/Measurements',
    'input_file': ['measurementsTable_001.csv', 'measurementsTable_002.csv'],
    'output_dir': '../output',
}


if __name__ == '__main__':
    run_stereology(measure_data)
