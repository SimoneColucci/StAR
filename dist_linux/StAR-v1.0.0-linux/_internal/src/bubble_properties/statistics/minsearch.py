"""
Chi-square minimisation for distribution fitting.

Supports two methods:
  - 'fmincon'  : scipy L-BFGS-B with 100 random restarts (analogous to MATLAB fmincon)
  - 'simplex'  : custom Nelder-Mead solver (see simplex.py)
"""

import numpy as np
from scipy.optimize import minimize

from .distributions import (
    exponential_density, weibull_density, normal_density, logistic_density,
    exponential_exceedance, weibull_exceedance, normal_exceedance, logistic_exceedance,
)
from .simplex import simplex


# ---- distribution dispatch tables ------------------------------------------
_DENSITY_FUNCS = {
    'Exponential': (exponential_density, 2),
    'Weibull':     (weibull_density,     3),
    'Normal':      (normal_density,      3),
    'Logistic':    (logistic_density,     3),
}

_EXCEEDANCE_FUNCS = {
    'Exponential': (exponential_exceedance, 1),
    'Weibull':     (weibull_exceedance,     2),
    'Normal':      (normal_exceedance,      2),
    'Logistic':    (logistic_exceedance,    2),
}


def _chi_square_fun(fit_parameters, data):
    """Chi-square per degrees of freedom."""
    branch = data['branch_name']
    dist = data['distribution_name']

    if branch == 'Density':
        func, Np = _DENSITY_FUNCS[dist]
    else:  # Exceedance
        func, Np = _EXCEEDANCE_FUNCS[dist]

    with np.errstate(over='ignore', under='ignore', invalid='ignore',
                     divide='ignore'):
        model = func(fit_parameters, data['x'])
        chi_sq = np.sum(((model - data['y'])
                         / np.maximum(1e-10, data['sigma']))**2)
        chi_sq_tilde = chi_sq / (len(data['x']) - Np)
    # Penalise non-finite trial evaluations so the optimiser avoids them.
    if not np.isfinite(chi_sq_tilde):
        return 1e30
    return chi_sq_tilde


def minsearch(parameters, data, distribution_name, branch_name, minsearch_method):
    """
    Minimisation search for distribution fitting.

    Parameters
    ----------
    parameters : dict
        Must contain 'low_bound' and 'high_bound' arrays.
    data : dict
        Must contain 'x', 'y', 'sigma' arrays.
    distribution_name : str
        One of 'Exponential', 'Weibull', 'Normal', 'Logistic'.
    branch_name : str
        'Density' or 'Exceedance'.
    minsearch_method : str
        'fmincon' or 'simplex'.

    Returns
    -------
    p_best : ndarray
        Best-fit parameter vector.
    chi_sq_best : float
        Best chi-square value.
    """
    data_fit = dict(data)       # shallow copy to avoid mutating caller's dict
    data_fit['distribution_name'] = distribution_name
    data_fit['branch_name'] = branch_name

    print(f'Fitting data with {distribution_name} distribution')

    low = np.asarray(parameters['low_bound'], dtype=float)
    high = np.asarray(parameters['high_bound'], dtype=float)

    if minsearch_method == 'fmincon':
        bounds = list(zip(low, high))
        pmean = low + np.abs(low - high) / 2.0
        psigma = np.abs(pmean - low) / 2.0

        best_chi = np.inf
        best_p = pmean.copy()

        for _ in range(100):
            pstart = np.random.normal(pmean, psigma)
            pstart = np.clip(pstart, low + 1e-15, high - 1e-15)

            try:
                result = minimize(
                    _chi_square_fun, pstart, args=(data_fit,),
                    method='L-BFGS-B', bounds=bounds,
                    options={'ftol': 1e-15, 'gtol': 1e-15,
                             'maxiter': 2000, 'disp': False},
                )
                if result.fun < best_chi:
                    best_chi = result.fun
                    best_p = result.x.copy()
            except Exception:
                continue

        return best_p, best_chi

    elif minsearch_method == 'simplex':
        p_best, chi_sq_best = simplex(
            _chi_square_fun, len(low),
            additional_data=data_fit,
            low_boundary=low,
            high_boundary=high,
            do_plot=False,
        )
        return p_best, chi_sq_best

    else:
        raise ValueError(f"Unknown minsearch method: '{minsearch_method}'. "
                         "Available: 'fmincon', 'simplex'.")
