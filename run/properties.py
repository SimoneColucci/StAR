#!/usr/bin/env python3
"""
Main entry point – equivalent of the MATLAB run/Properties.m

Usage:
    cd /var/www/html/StAR/run
    python properties.py
"""

import sys
import os

# Make the project root importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.run_bubble_properties import run_bubble_properties


# =========================================================================
# Properties
# =========================================================================

mypath = '../data'

measure_data = {
    # measurements of which you want to calculate properties
    'input_dir':  os.path.join(mypath, 'Measurements'),
    'input_file': [
        ['measurementsTable_001.csv', 'measurementsTable_003.csv'],
    ],
    'type': [
        ['2D', '2D'],
    ],
    # names shown for each group (e.g. in the fractal index figures)
    'group_names': ['CataclasiteA'],
    # bin-edge grid size of the density / exceedance histograms, per group
    'nbins_density': [16],
    'nbins_exceedance': [22],
    # output directory
    'output_dir': '../output',
}

sample = {
    # meters per pixel [m/pixel]
    'px2m': [
        [1.1905e-05, 1.0715e-06],
    ],
    # cropArea [pixel^2]
    'crop_area': [
        [2383948.0, 7999104.0],
    ],
}

method = {
    'minsearch': 'fmincon',
    # set to True to also compute the Otsuki (1998) fractal index per group
    'fractal_index': False,
}

# =========================================================================
# Run
# =========================================================================

if __name__ == '__main__':
    run_bubble_properties(measure_data, sample, method)
