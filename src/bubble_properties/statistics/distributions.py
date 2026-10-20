"""
Distribution functions for density-based and exceedance-based analysis.

Statistical formulation:
  Alexander A. Proussevitch, Dork L. Sahagian, Evgeni P. Tsentalovich,
  Statistical analysis of bubble and crystal size distributions: Formulations and procedures,
  Journal of Volcanology and Geothermal Research,
  Volume 164, Issue 3, 2007, Pages 95-111,
  https://doi.org/10.1016/j.jvolgeores.2007.04.007.
"""

import math

import numpy as np
from scipy.special import erfc

# Clip the argument of every exponential so that overflow ("inf") never
# propagates through the fit. exp(700) is already close to the double
# precision ceiling, so this is numerically transparent for valid fits
# while keeping the optimiser well behaved for extreme trial parameters.
_EXP_CLIP = 700.0


def _sexp(z):
    """Overflow-safe exponential."""
    return np.exp(np.clip(z, -_EXP_CLIP, _EXP_CLIP))


def _finite(a):
    """Replace inf/nan by finite numbers."""
    return np.nan_to_num(a, nan=0.0, posinf=0.0, neginf=0.0)


# ===================================================================
# Density distributions (linear number density on log10 scale)
# ===================================================================

def exponential_density(p, x):
    """Exponential distribution density."""
    alpha = p[0]   # cumulative number density
    nu = p[1]      # log10(median)
    N_tot = alpha
    sigma = 1.0 / np.log(10)
    with np.errstate(over='ignore', under='ignore', invalid='ignore',
                     divide='ignore'):
        z = (x - nu) / sigma
        ftilde_lin = _sexp(z - _sexp(z)) / sigma
        n_lin = N_tot * ftilde_lin
    return _finite(n_lin)


def weibull_density(p, x):
    """Weibull distribution density."""
    alpha = p[0]   # cumulative number density
    nu = p[1]      # log10(median)
    sigma = p[2]   # standard deviation
    N_tot = alpha
    with np.errstate(over='ignore', under='ignore', invalid='ignore',
                     divide='ignore'):
        z = (x - nu) / sigma
        ftilde_lin = _sexp(z - _sexp(z)) / sigma
        n_lin = N_tot * ftilde_lin
    return _finite(n_lin)


def normal_density(p, x):
    """Normal distribution density."""
    alpha = p[0]   # cumulative number density
    nu = p[1]      # log10(mean)
    sigma = p[2]   # standard deviation
    N_tot = alpha
    with np.errstate(over='ignore', under='ignore', invalid='ignore',
                     divide='ignore'):
        ftilde_lin = (1.0 / (sigma * np.sqrt(2 * np.pi))) * \
            _sexp(-((x - nu)**2) / (2 * sigma**2))
        n_lin = N_tot * ftilde_lin
    return _finite(n_lin)


def logistic_density(p, x):
    """Logistic distribution density."""
    alpha = p[0]   # cumulative number density
    nu = p[1]      # log10(mean)
    sigma = p[2]   # standard deviation
    N_tot = alpha
    with np.errstate(over='ignore', under='ignore', invalid='ignore',
                     divide='ignore'):
        ez = _sexp((x - nu) / sigma)
        ftilde_lin = (1.0 / sigma) * ez / (1 + ez)**2
        # lim A->inf ftilde_lin = 0, A = exp((x-nu)/sigma)
        ftilde_lin = _finite(ftilde_lin)
        n_lin = N_tot * ftilde_lin
    return _finite(n_lin)


# ===================================================================
# Exceedance distributions
# ===================================================================

def exponential_exceedance(p, v):
    """Exponential exceedance function."""
    with np.errstate(over='ignore', under='ignore', invalid='ignore',
                     divide='ignore'):
        mu = 10.0**p[0]
        S = _sexp(-v/mu)
    return _finite(S)


def weibull_exceedance(p, v):
    """Weibull exceedance function."""
    with np.errstate(over='ignore', under='ignore', invalid='ignore',
                     divide='ignore'):
        mu = 10.0**p[0]
        kappa = 1.0 / (np.log(10) * p[1])
        S = _sexp(-(np.maximum(v/mu, 0.0))**kappa)
    return _finite(S)


def normal_exceedance(p, v):
    """Normal exceedance function."""
    with np.errstate(over='ignore', under='ignore', invalid='ignore',
                     divide='ignore'):
        mu = 10.0**p[0]
        kappa = 1.0 / (np.log(10) * p[1])
        S = 0.5 * erfc(kappa * np.log(np.maximum(v, 1e-300) / mu) / np.sqrt(2))
    return _finite(S)


def logistic_exceedance(p, v):
    """Logistic exceedance function."""
    with np.errstate(over='ignore', under='ignore', invalid='ignore',
                     divide='ignore'):
        mu = 10.0**p[0]
        kappa = 1.0 / (np.log(10) * p[1])
        S = 1.0 / (1 + (np.maximum(v, 1e-300) / mu)**kappa)
    return _finite(S)

# ===================================================================
# Moments 
# ===================================================================

def exponential_moments(p,n):
    """Exponential distribution moments."""
    mu = 10.0**p[1]
    mom = math.factorial(n)*mu**(n)
    return mom

def weibull_moments(p,n):
    """Weibull distribution moments."""
    mu = 10.0**p[1]
    kappa = 1.0 / (np.log(10) * p[2])
    mom = mu**(n)*math.gamma(1+n/kappa)
    return mom

def normal_moments(p,n):
    """Normal distribution moments."""
    nu = p[1]
    sigma = p[2]
    mom = math.exp(n*nu + 0.5*n*n*sigma*sigma)
    return mom

def logistic_moments(p,n):
    """Logistic distribution moments."""
    mu = 10.0**p[1]
    kappa = 1.0 / (np.log(10) * p[2])
    if n == 0:
        return 1.0
    if n >= kappa:
        raise ValueError(
            f'Moment of order {n} is +infinity because n >= kappa '
            f'({kappa}).'
        )
    mom = (mu**n)*(n*math.pi/kappa)/(math.sin(n*math.pi/kappa))
    return mom
