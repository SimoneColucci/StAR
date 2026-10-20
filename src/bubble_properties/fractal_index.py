"""
Fractal index (power-law exponent beta) of the particle-size distribution.

Python port of the MATLAB routine ``fractal.m`` that applies the model of
Otsuki (1998, Eqn. 1) to fit the exceedance curve of the equivalent diameters
and derive the power-law exponent (fractal index).

Reference:
    Otsuki, K. (1998), Geophysical Research Letters, 25(5), 671-674.

The original MATLAB routine is interactive: the user selects the roll-off
point (where the data starts deviating) and the cut-off / inflection point,
either manually or via automatic inflection detection.

This module supports **two modes**:

* **Automatic** (default, used by CLI): the whole exceedance curve is used
  (no manual roll-off truncation) and ``Dc`` is detected automatically as
  the first inflection point (sign change of the second derivative).

* **Interactive** (used by GUI): an ``interactive_callback`` is invoked with
  the raw exceedance data ``(x, y, group_name)``.  The callback must return
  a dict with keys ``rolloff_idx`` (int, data is truncated to ``x[:rolloff_idx]``)
  and ``Dc`` (float, cut-off diameter, or ``None`` for automatic detection).
  If the callback returns ``None`` the function falls back to automatic mode.

Only the exponents ``alpha`` and ``beta`` are fitted, with ``Dc`` held fixed.
"""

import os
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit


def _otsuki_model(x, alpha, beta, Dc):
    """Otsuki (1998) exceedance model with fixed cut-off ``Dc``."""
    with np.errstate(over='ignore', under='ignore', invalid='ignore',
                     divide='ignore'):
        return (1.0 + (x / Dc) ** alpha) ** (-beta / alpha)


def _auto_cutoff(x, y):
    """First inflection point (sign change of the 2nd derivative)."""
    if len(x) < 4:
        return x[len(x) // 2]
    dy = np.diff(y) / np.diff(x)
    d2y = np.diff(dy) / np.diff(x[1:])
    x_d2 = x[1:-1]
    signs = d2y[:-1] * d2y[1:]
    idx = np.where(signs < 0)[0]
    if idx.size:
        return x_d2[idx[0]]
    return x[len(x) // 2]


def _prepare_data(equiv_diameters, areas_px2, px2m):
    """
    Compute the histogram and exceedance curve from equivalent diameters.

    Returns ``(x, y)`` where *x* are diameters in metres and *y* is the
    normalised exceedance, or ``None`` if there is not enough data.
    """
    bin_centers_tot = []
    n_tot = []
    for i, diam in enumerate(equiv_diameters):
        diam = np.asarray(diam, dtype=float)
        diam = diam[np.isfinite(diam) & (diam > 0)]
        if diam.size < 2:
            continue
        log10D = np.log10(diam)
        lo, hi = log10D.min(), log10D.max()
        if hi <= lo:
            continue
        bin_edges = np.arange(lo, hi, 0.1)
        if bin_edges.size < 2:
            bin_edges = np.linspace(lo, hi, 3)
        centers = bin_edges[:-1] + np.abs(np.diff(bin_edges)) / 2.0
        Atot = float(areas_px2[i]) * float(px2m[i]) ** 2
        if Atot <= 0:
            continue
        n, _ = np.histogram(log10D, bins=bin_edges)
        bin_centers_tot.append(centers)
        n_tot.append(n / Atot)

    if not bin_centers_tot:
        return None

    bin_centers_tot = np.concatenate(bin_centers_tot)
    n_tot = np.concatenate(n_tot)

    order = np.argsort(bin_centers_tot)
    bin_centers_s = bin_centers_tot[order]
    n_tot_s = n_tot[order]

    total = np.sum(n_tot_s)
    if total <= 0:
        return None
    # exceedance (cumulative from the right), normalised
    Sprime_s = np.flip(np.cumsum(np.flip(n_tot_s))) / total

    x = 10.0 ** bin_centers_s          # diameters in metres
    y = Sprime_s
    finite = np.isfinite(y) & (y > 0)
    x, y = x[finite], y[finite]
    if x.size < 4:
        return None
    return x, y


def _fit_and_plot(x, y, Dc, group_name, num, out_dir):
    """
    Fit the Otsuki model to ``(x, y)`` with fixed cut-off ``Dc`` and save
    the figure.  Returns the result dict.
    """
    result = {'group': group_name, 'alpha': np.nan, 'beta': np.nan,
              'R2': np.nan, 'Dc': np.nan}
    try:
        popt, _ = curve_fit(
            lambda xx, a, b: _otsuki_model(xx, a, b, Dc), x, y,
            p0=[0.1, 0.1], maxfev=20000)
        alpha, beta = float(popt[0]), float(popt[1])
        y_fit = _otsuki_model(x, alpha, beta, Dc)
        ss_res = np.sum((y - y_fit) ** 2)
        ss_tot = np.sum((y - np.mean(y)) ** 2)
        r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else np.nan
    except Exception as exc:
        print(f'Fractal index: fit failed for group "{group_name}": {exc}')
        return result

    result.update({'alpha': alpha, 'beta': beta, 'R2': r2, 'Dc': Dc})

    # ---- Figure -------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(7, 6))
    fig.patch.set_facecolor('white')
    # +6 converts log10(metre) to log10(micron) for display
    ax.plot(np.log10(x) + 6, np.log10(y), 's', color='red', label='Data')
    xs = np.linspace(x.min(), x.max(), 200)
    ax.plot(np.log10(xs) + 6, np.log10(_otsuki_model(xs, alpha, beta, Dc)),
            '-k', label='Fitting function (Otsuki, 1998)')
    ax.plot(np.log10(Dc) + 6,
            np.log10(_otsuki_model(np.array([Dc]), alpha, beta, Dc))[0],
            '+', color='red', markersize=12, markeredgewidth=2,
            label='Cut-off point')
    ax.set_xlabel(r'$\log_{10}$ of equivalent diameter ($\mu$m)')
    ax.set_ylabel(r'$\log_{10}$ of exceedance')
    ax.set_title(f'{group_name}: '
                 fr'$\alpha$={alpha:.3f}, $\beta$={beta:.3f}, '
                 fr'$R^2$={r2:.4f}')
    ax.legend(loc='lower left', fontsize=8)
    fig.tight_layout()
    fig_path = os.path.join(out_dir, f'FractalIndex_{num}.png')
    fig.savefig(fig_path, dpi=200, bbox_inches='tight')
    plt.close(fig)
    print(f'Fractal index (Otsuki, 1998): alpha={alpha:.3f}, '
          f'beta={beta:.3f}, R2={r2:.4f}. Figure saved to {fig_path}')
    return result


def fractal_index(equiv_diameters, areas_px2, px2m, group_name, num, out_dir,
                  interactive_callback=None):
    """
    Compute the fractal index for one group of measurements.

    Parameters
    ----------
    equiv_diameters : list[ndarray]
        Equivalent diameters (metres) for each file of the group.
    areas_px2 : sequence[float]
        Crop area (pixel^2) of each file.
    px2m : sequence[float]
        Metres-per-pixel of each file.
    group_name : str
        Group label used in the figure title.
    num : str
        Numeric identifier used in the output file name.
    out_dir : str
        Destination directory (Statistics folder).
    interactive_callback : callable, optional
        When provided (GUI mode), called as
        ``interactive_callback(x, y, group_name)`` where *x* and *y* are
        the raw exceedance data.  Must return a dict with keys:

        * ``rolloff_idx`` (int): data is truncated to ``x[:rolloff_idx]``
          and ``y[:rolloff_idx]`` (mirrors MATLAB's ``x = x(1:I-1)``).
        * ``Dc`` (float or None): cut-off diameter.  If ``None`` the
          automatic inflection detection is used.

        If the callback returns ``None``, falls back to automatic mode.

    Returns
    -------
    dict with keys ``group``, ``alpha``, ``beta``, ``R2``, ``Dc``.
    """
    os.makedirs(out_dir, exist_ok=True)

    data = _prepare_data(equiv_diameters, areas_px2, px2m)
    result = {'group': group_name, 'alpha': np.nan, 'beta': np.nan,
              'R2': np.nan, 'Dc': np.nan}
    if data is None:
        print(f'Fractal index: not enough data for group "{group_name}".')
        return result

    x, y = data

    # ---- Interactive mode: ask the user for roll-off and cut-off -----------
    if interactive_callback is not None:
        sel = interactive_callback(x, y, group_name)
        if sel is not None:
            rolloff_idx = sel.get('rolloff_idx')
            Dc = sel.get('Dc')
            if rolloff_idx is not None and 0 < rolloff_idx < len(x):
                x = x[:rolloff_idx]
                y = y[:rolloff_idx]
            if Dc is None or not np.isfinite(Dc):
                Dc = _auto_cutoff(x, y)
        else:
            Dc = _auto_cutoff(x, y)
    else:
        Dc = _auto_cutoff(x, y)

    return _fit_and_plot(x, y, Dc, group_name, num, out_dir)
