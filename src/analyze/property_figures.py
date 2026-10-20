"""
Frequency figures for the measured particle properties.

For every numeric property found in the measurement tables a figure is
produced with one subplot per group; the files belonging to the same group
are overlaid in that subplot. The ``Orientation`` property is drawn as a
rose diagram (polar histogram), mirroring the original MATLAB behaviour
(theta zero at top, clockwise, limited to [-90, 90] degrees).
"""

import os
import math
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


# Properties plotted as ordinary histograms (Orientation handled separately).
_HIST_PROPERTIES = [
    'EquivDiameter', 'Area', 'MajorAxisLength', 'MinorAxisLength',
    'Perimeter', 'MaxFeretDiameter', 'MinFeretDiameter',
    'Circularity', 'Eccentricity', 'Solidity',
]
_ROSE_PROPERTY = 'Orientation'
_ROSE_NBINS = 18


def _grid(n):
    """Return (nrows, ncols) for ``n`` subplots."""
    ncols = int(math.ceil(math.sqrt(n)))
    nrows = int(math.ceil(n / ncols))
    return nrows, ncols


def _file_colors(n):
    cmap = plt.get_cmap('tab10' if n <= 10 else 'tab20')
    return [cmap(i % cmap.N) for i in range(n)]


def save_property_figures(dfs, names, groups, out_dir):
    """
    Save frequency figures of the measured properties.

    Parameters
    ----------
    dfs : list[pandas.DataFrame]
        One DataFrame of measured properties per input file.
    names : list[str]
        File name associated with each DataFrame (used as legend label).
    groups : list[dict]
        Each dict has ``name`` and ``indices`` (indices into ``dfs``).
    out_dir : str
        Destination directory for the figures.
    """
    os.makedirs(out_dir, exist_ok=True)
    n_groups = len(groups)
    nrows, ncols = _grid(n_groups)

    available = set()
    for df in dfs:
        if df is not None and not df.empty:
            available.update(df.columns)

    # ---- Histogram properties ----------------------------------------------
    for prop in _HIST_PROPERTIES:
        if prop not in available:
            continue
        fig, axes = plt.subplots(nrows, ncols, figsize=(6 * ncols, 4.5 * nrows),
                                 squeeze=False)
        fig.patch.set_facecolor('white')
        for gi, group in enumerate(groups):
            ax = axes[gi // ncols][gi % ncols]
            indices = group.get('indices', [])
            colors = _file_colors(len(indices))
            plotted = False
            for k, idx in enumerate(indices):
                if idx >= len(dfs):
                    continue
                df = dfs[idx]
                if df is None or df.empty or prop not in df.columns:
                    continue
                values = np.asarray(df[prop].values, dtype=float)
                values = values[np.isfinite(values)]
                if values.size == 0:
                    continue
                label = names[idx] if idx < len(names) else f'file {idx + 1}'
                ax.hist(values, bins=20, alpha=0.5, color=colors[k],
                        edgecolor=colors[k], label=label)
                plotted = True
            ax.set_title(group.get('name', f'Group {gi + 1}'))
            ax.set_xlabel(prop)
            ax.set_ylabel('Frequency')
            if plotted:
                ax.legend(fontsize=8)
        # hide unused axes
        for j in range(n_groups, nrows * ncols):
            axes[j // ncols][j % ncols].axis('off')
        fig.tight_layout()
        fig.savefig(os.path.join(out_dir, f'{prop}.png'), dpi=200,
                    bbox_inches='tight')
        plt.close(fig)

    # ---- Orientation rose diagram -------------------------------------------
    if _ROSE_PROPERTY in available:
        fig = plt.figure(figsize=(6 * ncols, 6 * nrows))
        fig.patch.set_facecolor('white')
        for gi, group in enumerate(groups):
            ax = fig.add_subplot(nrows, ncols, gi + 1, projection='polar')
            indices = group.get('indices', [])
            colors = _file_colors(len(indices))
            for k, idx in enumerate(indices):
                if idx >= len(dfs):
                    continue
                df = dfs[idx]
                if df is None or df.empty or _ROSE_PROPERTY not in df.columns:
                    continue
                orient = np.asarray(df[_ROSE_PROPERTY].values, dtype=float)
                orient = orient[np.isfinite(orient)]
                if orient.size == 0:
                    continue
                theta = np.deg2rad(orient)
                bins = np.linspace(np.deg2rad(-90), np.deg2rad(90),
                                   _ROSE_NBINS + 1)
                counts, edges = np.histogram(theta, bins=bins)
                widths = np.diff(edges)
                centers = edges[:-1] + widths / 2
                label = names[idx] if idx < len(names) else f'file {idx + 1}'
                ax.bar(centers, counts, width=widths, bottom=0.0,
                       color=colors[k], alpha=0.7, edgecolor='none',
                       label=label)
            ax.set_theta_zero_location('N')
            ax.set_theta_direction(-1)
            ax.set_thetamin(-90)
            ax.set_thetamax(90)
            ax.set_yticklabels([])
            ax.set_title(group.get('name', f'Group {gi + 1}'))
            if indices:
                ax.legend(fontsize=8, loc='upper right',
                          bbox_to_anchor=(1.25, 1.1))
        fig.tight_layout()
        fig.savefig(os.path.join(out_dir, f'{_ROSE_PROPERTY}.png'), dpi=200,
                    bbox_inches='tight')
        plt.close(fig)
