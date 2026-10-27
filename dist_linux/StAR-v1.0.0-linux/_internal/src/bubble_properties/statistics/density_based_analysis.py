"""
Density-based statistical analysis of particle size distributions.
"""

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from .distributions import (
    exponential_density, weibull_density, normal_density, logistic_density,
)
from .minsearch import minsearch


def density_based_analysis(v, sample_new, method, rd, idx, num, mtype,
                           nbins=16):
    """
    Density-based analysis of particle size distributions.

    Parameters
    ----------
    v : list of ndarray
        Each element contains particle size measurements from a sample.
    sample_new : dict
        Must contain 'Depth', 'Area', 'px2m' arrays.
    method : dict
        Must contain 'minsearch' string.
    rd : str
        Output directory for statistics.
    idx : int
        Figure / group index.
    num : str
        Numeric string identifier for filenames.
    mtype : list of str
        Measurement types ('2D', '3D', '3Dstereo').
    nbins : int, optional
        Number of points of the bin-edge grid used to build the combined
        histogram (default 16).

    Returns
    -------
    X2, Alpha, Nu, Sigma : ndarray (4,)
    """
    Nm = len(v)

    # ---- Data: compute log10 of particle sizes (exclude zeros) --------------
    minima = np.zeros(Nm)
    log10v = [None] * Nm
    sumv = np.zeros(Nm)
    for j in range(Nm):
        v_nozero = v[j][v[j] != 0]
        log10v[j] = np.log10(v_nozero)
        minima[j] = np.min(log10v[j])
        sumv[j] = np.sum(v_nozero)

    # sort measurements from left (smaller) to right (larger)
    idx_sorted = np.argsort(minima)
    log10v = [log10v[k] for k in idx_sorted]
    sumv = [sumv[k] for k in idx_sorted]
    mtype = [mtype[k] for k in idx_sorted]

    if len(set(mtype)) > 1:
        raise ValueError(
            'Cannot combine datasets with different measurement types: '
            f'{mtype}.'
        )

    # ---- Validate interval ordering ----------------------------------------
    # The subsequent overlap-removal logic assumes intervals that are:
    #   1. connected (no gaps);
    #   2. not nested inside one another.
    interval_min = np.array([np.min(values) for values in log10v])
    interval_max = np.array([np.max(values) for values in log10v])

    for j in range(1, Nm):
        if interval_min[j] > interval_max[j - 1]:
            raise ValueError(
                'Cannot fit density model: a gap exists between '
                f'intervals {j - 1} and {j} '
                f'([{interval_min[j - 1]}, {interval_max[j - 1]}] and '
                f'[{interval_min[j]}, {interval_max[j]}]).'
            )

        if interval_max[j] <= interval_max[j - 1]:
            raise ValueError(
                'Cannot fit density model: interval '
                f'{j} is contained in (or has the same right edge as) '
                f'interval {j - 1} '
                f'([{interval_min[j - 1]}, {interval_max[j - 1]}] and '
                f'[{interval_min[j]}, {interval_max[j]}]).'
            )

    # ---- Define bins --------------------------------------------------------
    all_vals = np.concatenate(log10v)
    bin_edges = np.linspace(all_vals.min(), all_vals.max(), nbins)
    bin_centers = bin_edges[:-1] + np.abs(np.diff(bin_edges)) / 2

    # ---- Left / right edge limits of individual histograms ------------------
    Il = np.zeros(Nm, dtype=int)
    Ir = np.zeros(Nm, dtype=int)
    for j in range(Nm):
        min_j = np.min(log10v[j])
        max_j = np.max(log10v[j])
        Il[j] = np.where(bin_edges <= min_j)[0][-1]
        Ir[j] = np.where(bin_edges >= max_j)[0][0]

    # ---- Remove overlapping regions -----------------------------------------
    Il_new = np.zeros(Nm, dtype=int)
    Ir_new = np.zeros(Nm, dtype=int)
    Il_new[0] = Il[0]
    for j in range(1, Nm):
        Il_new[j] = max(Ir[j - 1], Il[j])
    Ir_new[:Nm - 1] = Il_new[1:]
    Ir_new[Nm - 1] = Ir[-1]

    # ---- Combined histogram -------------------------------------------------
    n_lin_array = []
    sigma_array = []
    Vtot = (np.array(sample_new['Depth'])
            * np.array(sample_new['Area'])
            * np.array(sample_new['px2m'])**2)
    Vtot = Vtot[idx_sorted]

    last_n = None
    for j in range(Nm):
        edges_j = bin_edges[Il_new[j]:Ir_new[j] + 1]   # +1: Python slicing
        n, _ = np.histogram(log10v[j], bins=edges_j)

        if n.size == 0:
            raise ValueError(
                f'Interval {j} contains no histogram bins.'
            )

        # Assign shared-edge values to the subsequent interval only.
        if j < Nm - 1:
            shared_edge = edges_j[-1]
            boundary_mask = log10v[j] == shared_edge
            n[-1] -= np.count_nonzero(boundary_mask)

        diffs = np.diff(edges_j)
        Vm = Vtot[j] - sumv[j]  # Melt/matrix volume (i.e., particle free volume)
        n_lin_array.append(n / (Vm * diffs))
        sigma_array.append(np.sqrt(np.maximum(0, n)) / (Vm * diffs))
        last_n = n

    n_lin = np.concatenate(n_lin_array)
    sigma = np.concatenate(sigma_array)

    # ---- Normalise for computational efficiency -----------------------------
    Vnorm = np.mean(Vtot)
    n_lin_norm = n_lin * Vnorm

    # ---- Prepare fitting data -----------------------------------------------
    data = {
        'x': bin_centers,
        'y': n_lin_norm,
        'sigma': sigma * Vnorm,
    }
    # Where last histogram has zero counts, set sigma to 1
    zero_idx = np.where(last_n == 0)[0]
    if len(zero_idx) > 0:
        data['sigma'][zero_idx] = 1.0

    params = {
        'low_bound':  np.array([n_lin_norm.min(), all_vals.min(), 1e-10]),
        'high_bound': np.array([n_lin_norm.max(), all_vals.max(), 1.0]),
    }

    # ---- Fitting ------------------------------------------------------------
    print('#### Fitting based on distribution density ####')
    p_exp, x2_exp = minsearch(params, data, 'Exponential', 'Density', method['minsearch'])
    p_wei, x2_wei = minsearch(params, data, 'Weibull',     'Density', method['minsearch'])
    p_nor, x2_nor = minsearch(params, data, 'Normal',      'Density', method['minsearch'])
    p_log, x2_log = minsearch(params, data, 'Logistic',    'Density', method['minsearch'])

    # ---- Renormalise parameters ---------------------------------------------
    p_exp[0] /= Vnorm
    p_wei[0] /= Vnorm
    p_nor[0] /= Vnorm
    p_log[0] /= Vnorm

    # ---- Plot ---------------------------------------------------------------
    fig = plt.figure(idx)
    fig.set_size_inches(13.3, 5.3)
    fig.patch.set_facecolor('white')
    ax = fig.add_subplot(1, 2, 1)

    ax.bar(bin_centers, n_lin, width=np.diff(bin_edges)[0] * 0.8, color='steelblue', label='Data')

    if mtype[0] == '2D':
        xlab = r'$\log_{10}(v)$, $v$ = particle area (m$^2$)'
        ylab = r'Linear number density $n(v)/(m^{2}\log_{10}(v))$'
    else:
        xlab = r'$\log_{10}(v)$, $v$ = particle volume (m$^3$)'
        ylab = r'Linear number density $n(v)/(m^{3}\log_{10}(v))$'

    xgrid = np.linspace(bin_centers.min() - 2, bin_centers.max() + 1, 100)
    ax.plot(xgrid, exponential_density(p_exp, xgrid), 'b',  label='Exponential')
    ax.plot(xgrid, weibull_density(p_wei, xgrid),     'r',  label='Weibull')
    ax.plot(xgrid, normal_density(p_nor, xgrid),       'k',  label='Normal')
    ax.plot(xgrid, logistic_density(p_log, xgrid),     'm',  label='Logistic')
    ax.legend()
    ax.set_xlabel(xlab)
    ax.set_ylabel(ylab)

    # Additional figure: data and the distribution with the lowest chi-square.
    best_index = int(np.argmin([x2_exp, x2_wei, x2_nor, x2_log]))
    best_density, best_parameters, best_color, best_name = [
        (exponential_density, p_exp, 'b', 'Exponential'),
        (weibull_density, p_wei, 'r', 'Weibull'),
        (normal_density, p_nor, 'k', 'Normal'),
        (logistic_density, p_log, 'm', 'Logistic'),
    ][best_index]
    # Negative figure numbers keep these separate from the original group figures.
    best_fig = plt.figure(-idx)
    best_fig.set_size_inches(13.3, 5.3)
    best_fig.patch.set_facecolor('white')
    best_ax = best_fig.add_subplot(1, 2, 1)
    best_ax.bar(bin_centers, n_lin, width=np.diff(bin_edges)[0] * 0.8,
                color='steelblue', label='Data')
    best_ax.plot(xgrid, best_density(best_parameters, xgrid), best_color,
                 label=best_name)
    best_ax.legend()
    best_ax.set_xlabel(xlab)
    best_ax.set_ylabel(ylab)

    # ---- Save table ---------------------------------------------------------
    table_data = {
        'Distribution': ['Exponential', 'Weibull', 'Normal', 'Logistic'],
        'chi2':  [x2_exp, x2_wei, x2_nor, x2_log],
        'N':     [p_exp[0], p_wei[0], p_nor[0], p_log[0]],
        'nu':    [p_exp[1], p_wei[1], p_nor[1], p_log[1]],
        'sigma': ['', p_wei[2], p_nor[2], p_log[2]],
    }
    base_name = f'DensityBasedFitting_{num}'
    df = pd.DataFrame(table_data)
    df.to_csv(os.path.join(rd, base_name + '.csv'), sep='\t', index=False)

    # ---- Return vectors -----------------------------------------------------
    X2    = np.array([x2_exp,   x2_wei,   x2_nor,   x2_log])
    Alpha = np.array([p_exp[0], p_wei[0], p_nor[0], p_log[0]])
    Nu    = np.array([p_exp[1], p_wei[1], p_nor[1], p_log[1]])
    Sigma = np.array([0.0,      p_wei[2], p_nor[2], p_log[2]])

    return X2, Alpha, Nu, Sigma
