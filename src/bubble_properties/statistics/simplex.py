"""
Generic Nelder-Mead Simplex Solver with boundary conditions.

Python translation of the MATLAB implementation by Bret Dahme (2016).

Reference:
  Lagarias, Jeffrey C., et al. "Convergence properties of the
  Nelder--Mead simplex method in low dimensions." SIAM Journal on
  Optimization 9.1 (1998): 112-147.
"""

import numpy as np


def simplex(performance_function, n_variable,
            tolerance=1e-8, iteration=10000,
            low_boundary=None, high_boundary=None,
            initial=None, do_plot=False, seed=17,
            additional_data=None):
    """
    Nelder-Mead simplex optimisation with simple boundary conditions.

    Parameters
    ----------
    performance_function : callable
        Objective function.  Signature: f(x) or f(x, additional_data).
    n_variable : int
        Number of optimisation variables.
    tolerance : float
        Convergence tolerance (std of vertex values).
    iteration : int
        Maximum number of iterations.
    low_boundary, high_boundary : array-like or None
        Lower / upper bounds for each variable.
    initial : ndarray (n_variable+1, n_variable) or None
        Initial simplex vertices (NaN entries are filled randomly).
    do_plot : bool
        If True, plot convergence trace at the end.
    seed : int
        Seed for the random number generator.
    additional_data : any
        Extra data passed as second argument to performance_function.

    Returns
    -------
    argument : ndarray
        Best solution found.
    minima : float
        Objective value at best solution.
    """

    # ---- defaults -----------------------------------------------------------
    if low_boundary is None:
        low_boundary = np.full(n_variable, -np.inf)
    if high_boundary is None:
        high_boundary = np.full(n_variable, np.inf)
    low_boundary = np.asarray(low_boundary, dtype=float)
    high_boundary = np.asarray(high_boundary, dtype=float)

    if initial is None:
        initial = np.full((n_variable + 1, n_variable), np.nan)
    else:
        initial = np.array(initial, dtype=float)

    iteration = int(np.ceil(iteration))

    # ---- constants ----------------------------------------------------------
    n = n_variable + 1          # number of vertices
    rho = 1.0                   # reflection coefficient
    chi = 2.0                   # expansion coefficient
    gamma = 0.5                 # contraction coefficient
    sig = 0.5                   # shrink coefficient

    rng = np.random.RandomState(seed)

    # ---- helper: evaluate with boundary check -------------------------------
    def _eval(coords):
        if np.any(coords >= high_boundary) or np.any(coords <= low_boundary):
            return np.inf
        if additional_data is None:
            return performance_function(coords)
        else:
            return performance_function(coords, additional_data)

    # ---- initial simplex ----------------------------------------------------
    coords = np.zeros((n, n_variable))
    values = np.full(n, np.inf)

    for attempt in range(iteration):
        for i in range(n):
            c = rng.rand(n_variable) * (high_boundary - low_boundary) + low_boundary
            for j in range(n_variable):
                if not np.isnan(initial[i, j]):
                    c[j] = initial[i, j]
            val = _eval(c)
            coords[i] = c
            values[i] = val
            if val != np.inf:
                initial[i] = c
            else:
                initial[i] = np.nan

        if np.all(values == np.inf):
            raise ValueError(
                'Initial conditions produced no valid results. '
                'Consider providing initial conditions.')
        if np.all(values != np.inf):
            break

    # ---- optional convergence trace -----------------------------------------
    if do_plot:
        convergence_trace = np.full(iteration, np.nan)

    # ---- sort helper --------------------------------------------------------
    def _sort():
        nonlocal coords, values
        idx = np.argsort(values)
        coords = coords[idx]
        values = values[idx]

    # ---- main loop ----------------------------------------------------------
    ii = 0
    convergence = tolerance * 10
    while convergence >= tolerance and ii < iteration:
        ii += 1
        _sort()

        # centroid of all vertices except the worst
        centroid = np.mean(coords[:n - 1], axis=0)

        if do_plot:
            convergence_trace[ii - 1] = values[0]

        # Reflect
        reflect = (1 + rho) * centroid - rho * coords[n - 1]
        reflect_val = _eval(reflect)

        if values[0] <= reflect_val < values[n - 2]:
            coords[n - 1] = reflect
            values[n - 1] = reflect_val

        elif reflect_val < values[0]:
            # Expand
            expand = (1 - chi) * centroid + chi * reflect
            expand_val = _eval(expand)
            if expand_val < reflect_val:
                coords[n - 1] = expand
                values[n - 1] = expand_val
            else:
                coords[n - 1] = reflect
                values[n - 1] = reflect_val

        elif values[n - 2] <= reflect_val:
            # Contract outside
            co = (1 - gamma) * centroid + gamma * reflect
            co_val = _eval(co)
            # Contract inside
            ci = (1 - gamma) * centroid + gamma * coords[n - 1]
            ci_val = _eval(ci)

            if (values[n - 2] <= reflect_val < values[n - 1]
                    and co_val <= reflect_val):
                coords[n - 1] = co
                values[n - 1] = co_val
            elif values[n - 1] <= reflect_val and ci_val < values[n - 1]:
                coords[n - 1] = ci
                values[n - 1] = ci_val

        else:
            # Shrink
            for jj in range(1, n):
                coords[jj] = (1 - sig) * coords[0] + sig * coords[jj]
                values[jj] = _eval(coords[jj])

        convergence = np.std(values)
        if np.isnan(convergence):
            convergence = np.inf

    # ---- collect outputs ----------------------------------------------------
    _sort()
    argument = coords[0].copy()
    minima = values[0]

    # ---- optional plot ------------------------------------------------------
    if do_plot:
        import matplotlib.pyplot as plt
        trace = convergence_trace[:ii]
        plt.figure()
        plt.semilogy(trace - np.nanmin(trace) + tolerance)
        plt.xlabel('iterations')
        plt.ylabel(f'performance index - min performance {np.nanmin(trace):.6g}')
        plt.title(f'Performance Vs {ii} Iterations')
        plt.grid(True)
        plt.show()

    return argument, minima
