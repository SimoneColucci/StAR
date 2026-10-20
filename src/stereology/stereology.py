"""
Stereological conversion of a single 2-D measurements table into a 3-D
size distribution, with a comparison plot (histogram + CDF).

Ported from matlab/src/Stereology/stereology.py.
"""

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from pathlib import Path

from .convert_measurement import convert_measurement


def stereology(my_measurement_path, output_dir=None):
    """
    Run the stereological conversion for one measurements file and save a
    comparison figure ``Stereology_XXX.png``.

    Parameters
    ----------
    my_measurement_path : str | Path
        Input ``measurementsTable_XXX.csv`` file.
    output_dir : str | Path | None
        Where to save the .csv / .png outputs. If ``None`` they are saved
        next to the input file.

    Returns
    -------
    diam_3D : ndarray
        Reconstructed 3-D diameters.
    """
    diam_2D, diam_3D, xcdf_est, ycdf_est = convert_measurement(
        my_measurement_path, output_dir=output_dir)

    # Plotting
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

    # plot probability
    nbin = 20
    ax1.hist(diam_2D, bins=nbin, alpha=0.5, label="2D",
             color="tab:blue", edgecolor='blue')
    ax1.hist(diam_3D, bins=nbin, alpha=0.5, label="3D",
             color="tab:red", edgecolor='red')
    ax1.set_xlabel("Diameter (m)")
    ax1.set_ylabel("Frequency")
    ax1.legend()
    ax1.grid(axis='y', alpha=0.3)

    # plot cdf
    diam_2D_sorted = np.sort(diam_2D)
    cdf_2D = np.linspace(0, 1, len(diam_2D_sorted))
    ax2.step(diam_2D_sorted, cdf_2D, where="post", c="tab:blue", label="2D")
    ax2.step(xcdf_est, ycdf_est, where="post", c="tab:red", label="3Dstereo")
    ax2.set_xlabel("Diameter (m)")
    ax2.set_ylabel("CDF")
    ax2.legend(loc="lower right")
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()

    input_path = Path(my_measurement_path)
    suffix_number = input_path.stem[-3:]
    if output_dir is None:
        out_dir = input_path.parent
    else:
        out_dir = Path(output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
    figure_path = out_dir / f"Stereology_{suffix_number}.png"
    fig.savefig(figure_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved figure to {figure_path}")

    return diam_3D
