#!/usr/bin/env python3
"""
Command-line entry point for the PreProcessing module.
Equivalent of the MATLAB run/PreProcess.m

Uses matplotlib pop-up windows for the interactive steps.

Usage:
    cd /var/www/html/StAR/python/run
    python preprocess.py
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.run_preprocessing import run_preprocessing
from src.preprocessing.interactive_mpl import DEFAULT_INTERACTORS


preprocess = {
    'crop': True,
    'calibration': True,
    'intensityRange': True,
}

img_data = {
    # one input directory per image
    'input_dir': ['../data/Images', '../data/Images'],
    # image file names
    'input_file': ['cataclasiteA_micro.jpg', 'cataclasiteA_sample.jpg'],
    # calibration image file names
    'calibration_input_file': ['cataclasiteA_micro.jpg',
                               'cataclasiteA_sample.jpg'],
    # output directory
    'output_dir': '../output',
}


if __name__ == '__main__':
    run_preprocessing(preprocess, img_data, DEFAULT_INTERACTORS)
