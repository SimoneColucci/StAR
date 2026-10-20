"""
Convert observed 2-D section areas into 3-D reconstructed diameters,
assuming spherical particles, and save the result as a CSV file.

Ported from matlab/src/Stereology/convertMeasurement.py.
"""

import numpy as np
import pandas as pd
from pathlib import Path

from .size_estimation_unit_radius import estimate_size


def convert_measurement(my_measurement_path, output_dir=None):
    """
    Convert a 2-D measurements table (CSV with an ``EquivDiameter`` column)
    into a stereologically reconstructed 3-D diameter distribution.

    Parameters
    ----------
    my_measurement_path : str | Path
        Path to the input ``measurementsTable_XXX.csv`` file.
    output_dir : str | Path | None
        Directory where ``measurementsStereoTable_XXX.mat`` is saved.
        If ``None`` the file is saved next to the input file (MATLAB
        behaviour).

    Returns
    -------
    diam_2D, diam_3D, xxcdf_est, ycdf_est
    """
    full_path = Path(my_measurement_path).expanduser()
    if not full_path.exists():
        raise FileNotFoundError(f"File {full_path} does not exist")

    my_measurement_data = pd.read_csv(str(full_path))
    diam_array = my_measurement_data['EquivDiameter'].to_numpy()
    diam_2D = np.unique(diam_array)
    sample = (diam_2D ** 2) * 1. / 4. * np.pi

    # Estimate the underlying size distribution CDF using the sample of
    # observed section areas
    xcdf_est, ycdf_est = estimate_size(sample, debias=False)

    # For plotting with the matplotlib step function, we need to add some
    # additional points
    xcdf_est = np.append(np.append(0, xcdf_est), 1.05 * xcdf_est[-1])
    ycdf_est = np.append(np.append(0, ycdf_est), 1)

    # Calculate probability
    yp_est = np.diff(ycdf_est)  # estimated probability
    ntot = len(diam_2D)
    # number of particles per bin according to the estimated probability
    n_per_bin = np.round(yp_est * ntot).astype(int)
    # sampling from the estimated distribution
    radius_3D = np.repeat(xcdf_est[1:], n_per_bin)

    # Saving CSV file
    diam_3D = radius_3D * 2.

    input_path = Path(my_measurement_path)
    filename_stem = input_path.stem
    suffix_number = filename_stem[-3:]

    if output_dir is None:
        out_dir = input_path.parent
    else:
        out_dir = Path(output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

    new_filename = out_dir / f"measurementsStereoTable_{suffix_number}.csv"
    pd.DataFrame({'EquivDiameter': diam_3D}).to_csv(new_filename, index=False)
    print(f"Saved 3D reconstruction to {new_filename}")

    # Convert radius in diameter
    xxcdf_est = xcdf_est * 2.

    return diam_2D, diam_3D, xxcdf_est, ycdf_est
