"""
Exceedance-based statistical analysis of particle size distributions.
"""

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from .distributions import (
    exponential_exceedance, weibull_exceedance,
    normal_exceedance, logistic_exceedance,
)
from .minsearch import minsearch


def exceedance_based_analysis(v, sample_new, method, rd, idx, num, mtype,
                              nbins=22):
    """
    Exceedance-based analysis of particle size distributions.

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
        histogram (default 22).

    Returns
    -------
    X2, Nu, Sigma : ndarray (4,)
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
    sumv = sumv[idx_sorted]
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
                'Cannot fit exceedance model: a gap exists between '
                f'intervals {j - 1} and {j} '
                f'([{interval_min[j - 1]}, {interval_max[j - 1]}] and '
                f'[{interval_min[j]}, {interval_max[j]}]).'
            )

        if interval_max[j] <= interval_max[j - 1]:
            raise ValueError(
                'Cannot fit exceedance model: interval '
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

    # ---- Combined histogram (exceedance) ------------------------------------
    sigma_array = []
    Sprime_array = []
    Vtot = (np.array(sample_new['Depth'])
            * np.array(sample_new['Area'])
            * np.array(sample_new['px2m'])**2)
    Vtot = Vtot[idx_sorted]
    Vm = Vtot - sumv  # Matrix volume (area for 2D measurements)
    if np.any(~np.isfinite(Vm) | (Vm <= 0)):
        raise ValueError('Matrix volume/area must be finite and strictly positive.')
    rho = np.zeros(Nm)

    for j in range(Nm):
        edges_j = bin_edges[Il_new[j]:Ir_new[j] + 1]
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

        n0 = np.sum(n)
        if n0 == 0:
            raise ValueError(
                f'Interval {j} contains no data after removing the '
                'shared boundary.'
            )
        n1 = np.flip(np.cumsum(np.flip(n)))
        n2 = n0 - n1
        sigma_j = np.sqrt(n1 * n2 * (np.sqrt(n1) + np.sqrt(n2))**2 / n0**4)
        Sp_j = np.flip(np.cumsum(np.flip(n))) / np.sum(n)
        sigma_array.append(sigma_j)
        Sprime_array.append(Sp_j)
        rho[j] = np.sum(n) / Vm[j]

    # Weight each interval and include all subsequent intervals
    w = rho / np.sum(rho)
    for j in range(Nm):
        Sprime_array[j] = (
            Sprime_array[j] * w[j]
            + np.sum(w[j + 1:])
        )
        sigma_array[j] = sigma_array[j] * w[j]

    sigma = np.concatenate(sigma_array)
    # fix junction points
    for k in range(Nm - 1):
        junction = sum(len(values) for values in sigma_array[:k + 1])
        if junction < len(sigma) - 1:
            sigma[junction] = sigma[junction + 1]

    Sprime = np.concatenate(Sprime_array)

    # ---- Prepare fitting data -----------------------------------------------
    data = {
        'x': 10.0**bin_centers,
        'y': Sprime,
        'sigma': sigma.copy(),
    }
    data['sigma'][0] = 1.0
    data['sigma'][-1] = 1.0

    params = {
        'low_bound':  np.array([all_vals.min(), 1e-10]),
        'high_bound': np.array([all_vals.max(), 1.0]),
    }

    # ---- Fitting ------------------------------------------------------------
    print('#### Fitting based on exceedance ####')
    p_exp, x2_exp = minsearch(params, data, 'Exponential', 'Exceedance', method['minsearch'])
    p_wei, x2_wei = minsearch(params, data, 'Weibull',     'Exceedance', method['minsearch'])
    p_nor, x2_nor = minsearch(params, data, 'Normal',      'Exceedance', method['minsearch'])
    p_log, x2_log = minsearch(params, data, 'Logistic',    'Exceedance', method['minsearch'])

    # ---- Plot ---------------------------------------------------------------
    fig = plt.figure(idx)
    ax = fig.add_subplot(1, 2, 2)

    ax.bar(bin_centers, Sprime, width=np.diff(bin_edges)[0] * 0.8,
           color='steelblue', label='Data')

    if mtype[0] == '2D':
        xlab = r'$\log_{10}(v)$, $v$ = particle area (m$^2$)'
    else:
        xlab = r'$\log_{10}(v)$, $v$ = particle volume (m$^3$)'

    xgrid = 10.0**np.linspace(bin_centers.min() - 2, bin_centers.max() + 1, 100)
    ax.plot(np.log10(xgrid), exponential_exceedance(p_exp, xgrid), 'b',  label='Exponential')
    ax.plot(np.log10(xgrid), weibull_exceedance(p_wei, xgrid),     'r',  label='Weibull')
    ax.plot(np.log10(xgrid), normal_exceedance(p_nor, xgrid),       'k',  label='Normal')
    ax.plot(np.log10(xgrid), logistic_exceedance(p_log, xgrid),     'm',  label='Logistic')
    ax.legend()
    ax.set_xlabel(xlab)
    ax.set_ylabel('Exceedance')

    # Add the best exceedance fit to the second panel of the additional figure.
    best_index = int(np.argmin([x2_exp, x2_wei, x2_nor, x2_log]))
    best_exceedance, best_parameters, best_color, best_name = [
        (exponential_exceedance, p_exp, 'b', 'Exponential'),
        (weibull_exceedance, p_wei, 'r', 'Weibull'),
        (normal_exceedance, p_nor, 'k', 'Normal'),
        (logistic_exceedance, p_log, 'm', 'Logistic'),
    ][best_index]
    best_fig = plt.figure(-idx, figsize=(13.3, 5.3))
    best_fig.patch.set_facecolor('white')
    best_ax = best_fig.add_subplot(1, 2, 2)
    best_ax.bar(bin_centers, Sprime, width=np.diff(bin_edges)[0] * 0.8,
                color='steelblue', label='Data')
    best_ax.plot(np.log10(xgrid), best_exceedance(best_parameters, xgrid),
                 best_color, label=best_name)
    best_ax.legend()
    best_ax.set_xlabel(xlab)
    best_ax.set_ylabel('Exceedance')

    # ---- Save table ---------------------------------------------------------
    table_data = {
        'Distribution': ['Exponential', 'Weibull', 'Normal', 'Logistic'],
        'chi2':  [x2_exp, x2_wei, x2_nor, x2_log],
        'nu':    [p_exp[0], p_wei[0], p_nor[0], p_log[0]],
        'sigma': [p_exp[1], p_wei[1], p_nor[1], p_log[1]],
    }
    base_name = f'ExceedanceBasedFitting_{num}'
    df = pd.DataFrame(table_data)
    df.to_csv(os.path.join(rd, base_name + '.csv'), sep='\t', index=False)

    # ---- Return vectors -----------------------------------------------------
    X2    = np.array([x2_exp,   x2_wei,   x2_nor,   x2_log])
    Nu    = np.array([p_exp[0], p_wei[0], p_nor[0], p_log[0]])
    Sigma = np.array([0.0,      p_wei[1], p_nor[1], p_log[1]])

    return X2, Nu, Sigma
