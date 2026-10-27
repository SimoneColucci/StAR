"""
Core pre-processing logic (backend agnostic).

Python port of matlab/src/PreProcessing/preProcessing.m

The three interactive operations (spatial calibration, cropping and intensity
range selection) are delegated to *interactor* callbacks, so that the same
logic can be driven either by a Tkinter GUI (embedded matplotlib canvases) or
by stand-alone matplotlib pop-up windows for command-line use.

Interactor protocol (all optional depending on the enabled steps)::

    interactors['calibrate'](image_path) -> float | None      # px2m [m/pixel]
    interactors['crop'](image_path, save_path, state) -> (area_px2, state)
    interactors['intensity'](image_path) -> (i_min, i_max)

``state`` is an opaque dict used by the crop interactor to offer the
"use previous crop" option across images.
"""

import os
import numpy as np


def preprocessing(preprocess, img_data, interactors):
    """
    Run the enabled pre-processing steps.

    Parameters
    ----------
    preprocess : dict
        Flags: ``calibration``, ``crop``, ``intensityRange`` (bool).
    img_data : dict
        input_dir  : list[str]  (one directory per image)
        input_file : list[str]  (image file names)
        output_dir : str
        crop_dir   : str        (where cropped images are written)
        calibration_input_file : list[str] (calibration image names)
    interactors : dict
        Callbacks for the interactive steps (see module docstring).

    Returns
    -------
    px2m : ndarray | None
    crop_area : ndarray | None
    i_range : ndarray | None   shape (2, n) -> [min row; max row]
    """
    input_dir = img_data['input_dir']
    input_file = img_data['input_file']
    announced_images = set()

    def announce_image(index, filename, count):
        if index in announced_images:
            return
        if index < len(input_file):
            filename = input_file[index]
            count = len(input_file)
        print(f'Preprocessing image {index + 1}/{count}: {filename}')
        announced_images.add(index)

    # -- Calibration ----------------------------------------------------------
    px2m = None
    if preprocess.get('calibration'):
        calib_files = img_data['calibration_input_file']
        px2m = np.zeros(len(calib_files))
        for i, cf in enumerate(calib_files):
            calib_path = os.path.join(input_dir[i], cf)
            announce_image(i, cf, len(calib_files))
            temp = interactors['calibrate'](calib_path)
            if temp is None or (isinstance(temp, float) and np.isnan(temp)):
                print(f'Warning: Calibration failed for {cf}. Skipping...')
            else:
                px2m[i] = temp
                print(f'Calibration: m/pixel = {px2m[i]:.6e} m/pixel')

    # -- Cropping -------------------------------------------------------------
    crop_area = None
    if preprocess.get('crop'):
        state = {}
        crop_area = np.zeros(len(input_file))
        for i, f in enumerate(input_file):
            crop_path = os.path.join(input_dir[i], f)
            name, ext = os.path.splitext(f)
            crop_filename = f'{name}_{i + 1:03d}{ext}'
            save_path = os.path.join(img_data['crop_dir'], crop_filename)
            announce_image(i, f, len(input_file))
            area, state = interactors['crop'](crop_path, save_path, state)
            crop_area[i] = area if area is not None else 0
            print(f'Crop: CropArea: {int(crop_area[i])} pixels^2')

    # -- Intensity range ------------------------------------------------------
    i_range = None
    if preprocess.get('intensityRange') and input_file:
        i_range = np.zeros((2, len(input_file)))
        for i, f in enumerate(input_file):
            intensity_path = os.path.join(input_dir[i], f)
            announce_image(i, f, len(input_file))
            imin, imax = interactors['intensity'](intensity_path)
            i_range[:, i] = [imin, imax]
            print(f'Intensity range:  Min = {imin:.2f}, '
                  f'Max = {imax:.2f}')

    return px2m, crop_area, i_range
