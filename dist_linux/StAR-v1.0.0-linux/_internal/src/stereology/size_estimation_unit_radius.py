"""
Stereological estimation of the underlying particle size distribution CDF
from a sample of observed 2-D section areas, assuming spherical particles.

Ported verbatim from the original StAR MATLAB/Python Stereology module
(matlab/src/Stereology/size_estimation_unit_radius.py).

Requires the external package ``pysizeunfolder``:
    pip install git+https://github.com/thomasvdj/pysizeunfolder
"""

from pysizeunfolder.algorithms import hybrid_icm_em
import numpy as np
from math import pi, sqrt


def gs_sphere(x):
    y = np.zeros(len(x))
    indices = x * x < pi
    y[indices] = x[indices] / (np.sqrt(1 - x[indices] * x[indices] / pi))
    return y


def sphere_G(x):
    y = np.zeros(len(x))
    y[x >= sqrt(pi)] = 1
    x_ = x[x < sqrt(pi)]
    y[x < sqrt(pi)] = 1 - np.sqrt(1 - x_ * x_ / pi)
    return y


def de_bias_sphere(x_pts, estimate, G_cdf):
    n = len(x_pts)
    observed_x = np.linspace(0, 1, n)
    distances = np.zeros(n)
    Hb_probabilities = np.append(estimate[0], np.diff(estimate))

    FS_estimates = np.zeros((n, n))
    for i in range(n):
        kernel = G_cdf(x_pts[i] / x_pts)
        divisor = np.cumsum(np.flip(Hb_probabilities))
        divisor[divisor == 0.0] = 1.0
        FS_estimates[:, i] = np.flip(
            np.cumsum(np.flip(kernel * Hb_probabilities)) / divisor)

    for i in range(n):
        term1 = np.abs(observed_x - FS_estimates[i, :])[:(n - 1)]
        term2 = np.abs(observed_x[1:] - FS_estimates[i, :(n - 1)])
        distances[i] = 0.5 * np.dot(term1 + term2, np.diff(x_pts))

    trunc_ix = np.argmin(distances)
    temp_hb = np.copy(Hb_probabilities)
    temp_hb[:trunc_ix] = 0.0
    h_est = np.cumsum(temp_hb / x_pts)
    h_est = h_est / h_est[-1]
    return h_est


def estimate_size(observed_areas, debias=True,
                  tol=0.0001, stop_iterations=10):
    """
    Estimate the radii distribution CDF given a sample of observed section
    areas assuming spherical particles.

    See "Stereological determination of particle size distributions".

    :param observed_areas: sample of observed section areas, ndarray (n,).
    :param debias: if True the size distribution is estimated.
    :return: (x_pts, y_pts) representing a piece-wise constant CDF.
    """
    sqrt_sample = np.sqrt(observed_areas)
    n = len(sqrt_sample)
    rng = np.random.default_rng(0)
    sigma = np.std(sqrt_sample)

    if len(np.unique(sqrt_sample)) < n:
        print("Warning: input contains duplicate values, "
              "adding a small amount of noise.")
        sqrt_sample = np.abs(
            sqrt_sample + rng.normal(loc=0, scale=0.000001 * sigma, size=n))
    sqrt_sample = np.sort(sqrt_sample)

    # compute matrix alpha_{i,j}
    mat = np.broadcast_to(sqrt_sample, (n, n))
    input_mat = mat.T / mat
    data_matrix = np.reshape(gs_sphere(input_mat.flatten()), (n, n)) / mat

    # Compute MLE
    est = hybrid_icm_em(data_matrix, tol=tol, stop_iterations=stop_iterations)

    # Perform debiasing step if required
    if debias:
        est = de_bias_sphere(sqrt_sample, est, sphere_G)

    return sqrt_sample, est
