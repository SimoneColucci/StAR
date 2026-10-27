"""
Main runner for the PreProcessing module.
Equivalent of the MATLAB runPreProcessing.m

Creates the output directory (and ``CropImages`` sub-folder), runs the enabled
pre-processing steps and saves the results to::

    <output>/preProcessingResults.csv

with columns ``px2m_i``, ``cropArea_i``, ``IrangeMin_i``, ``IrangeMax_i``.
"""

import os
import numpy as np
import pandas as pd

from .preprocessing.preprocessing import preprocessing


def run_preprocessing(preprocess, img_data, interactors):
    """
    Parameters
    ----------
    preprocess : dict
        Flags ``calibration``, ``crop``, ``intensityRange``.
    img_data : dict
        input_dir, input_file, output_dir, calibration_input_file.
    interactors : dict
        Interactive callbacks (see preprocessing.preprocessing).

    Returns
    -------
    px2m, crop_area, i_range
    """
    rd = img_data['output_dir']
    os.makedirs(rd, exist_ok=True)
    crop_dir = os.path.join(rd, 'CropImages')
    os.makedirs(crop_dir, exist_ok=True)
    img_data = dict(img_data)
    img_data['crop_dir'] = crop_dir

    px2m, crop_area, i_range = preprocessing(preprocess, img_data, interactors)

    # ---- Save .csv ----------------------------------------------------------
    data = {}
    if preprocess.get('calibration') and px2m is not None and px2m.size:
        for i, v in enumerate(np.ravel(px2m)):
            data[f'px2m_{i + 1}'] = v
    if preprocess.get('crop') and crop_area is not None and crop_area.size:
        for i, v in enumerate(np.ravel(crop_area)):
            data[f'cropArea_{i + 1}'] = v
    if preprocess.get('intensityRange') and i_range is not None and i_range.size:
        imin = i_range[0, :]
        imax = i_range[1, :]
        for i, v in enumerate(imin):
            data[f'IrangeMin_{i + 1}'] = v
        for i, v in enumerate(imax):
            data[f'IrangeMax_{i + 1}'] = v

    csv_file = os.path.join(rd, 'preProcessingResults.csv')
    if data:
        pd.DataFrame([data]).to_csv(csv_file, index=False)
    else:
        print('Warning: No data to save for CSV file.')

    print('\nDone. Results saved to:', rd)
    return px2m, crop_area, i_range
