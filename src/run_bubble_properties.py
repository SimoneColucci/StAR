"""
Main runner for bubble properties analysis.
Equivalent of the MATLAB runBubbleProperties.m
"""

import os
import re
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from .bubble_properties.check_input import check_input_properties
from .bubble_properties.bubble_properties import bubble_properties
from .bubble_properties.fractal_index import fractal_index


def _load_equiv_diameter(filepath):
    """
    Load the ``EquivDiameter`` column from a CSV measurements file.
    """
    ext = os.path.splitext(filepath)[1].lower()
    if ext != '.csv':
        raise ValueError(f"Unsupported file format: '{ext}'. Use .csv")
    df = pd.read_csv(filepath)
    return df['EquivDiameter'].values.astype(float)


def run_bubble_properties(measure_data, sample, method):
    """
    Run the full bubble-properties analysis pipeline.

    Parameters
    ----------
    measure_data : dict
        input_dir, output_dir, input_file (list of list of str),
        type (list of list of str).
        Optionally nbins_density / nbins_exceedance (list of int, one per
        group) setting the bin-edge grid size of each analysis
        (defaults 16 and 22).
    sample : dict
        px2m, crop_area (list of list of float).
        Optionally D (list of list of float) for 3-D measurements.
    method : dict
        minsearch : str ('fmincon' or 'simplex').
        fractal_index : bool, optional. When true the Otsuki (1998) fractal
        index is also computed for each group.
        fractal_callback : callable, optional. When provided the fractal
        index runs in interactive mode (GUI); otherwise automatic (CLI).
    """
    check_input_properties(measure_data, sample, method)
    do_fractal = bool(method.get('fractal_index'))
    fractal_callback = method.get('fractal_callback')
    fractal_rows = []

    # ---- Create output directories ------------------------------------------
    rd = measure_data['output_dir']
    os.makedirs(rd, exist_ok=True)
    rd_stat = os.path.join(rd, 'Statistics')
    os.makedirs(rd_stat, exist_ok=True)

    n_groups = len(measure_data['input_file'])

    # ---- Initialise result arrays (outside the loop) ------------------------
    X2d    = np.zeros((4, n_groups))
    X2e    = np.zeros((4, n_groups))
    Alphad = np.zeros((4, n_groups))
    Mud    = np.zeros((4, n_groups))
    Mue    = np.zeros((4, n_groups))
    Sigmad = np.zeros((4, n_groups))
    Sigmae = np.zeros((4, n_groups))

    # ---- Iterate over groups ------------------------------------------------
    for i in range(n_groups):
        n_files = len(measure_data['input_file'][i])

        sample_new = {
            'Depth': np.zeros(n_files),
            'Area':  np.zeros(n_files),
            'px2m':  np.zeros(n_files),
        }
        bubble_dim = [None] * n_files
        equiv_diams = [None] * n_files
        num_arr = np.zeros(n_files, dtype=int)
        mtype = [''] * n_files

        print()
        for j in range(n_files):
            fname = measure_data['input_file'][i][j]
            filepath = os.path.join(measure_data['input_dir'], fname)

            # extract trailing number from filename
            nums = re.findall(r'\d+', filepath)
            num_arr[j] = int(nums[-1]) if nums else j

            print(fname)
            print()

            equiv_diam = _load_equiv_diameter(filepath)
            equiv_diams[j] = equiv_diam

            t = measure_data['type'][i][j]
            if t == '3D':
                sample_new['Depth'][j] = sample['D'][i][j]
                bubble_dim[j] = (1.0 / 6.0) * np.pi * equiv_diam**3
            elif t == '2D':
                sample_new['Depth'][j] = 1.0
                bubble_dim[j] = (np.pi / 4.0) * equiv_diam**2
            elif t == '3Dstereo':
                sample_new['Depth'][j] = np.mean(equiv_diam)
                bubble_dim[j] = (1.0 / 6.0) * np.pi * equiv_diam**3

            sample_new['Area'][j] = sample['crop_area'][i][j]
            sample_new['px2m'][j] = sample['px2m'][i][j]
            mtype[j] = t

        num_str = '_'.join(str(n) for n in num_arr)

        (X2d[:, i], X2e[:, i], Alphad[:, i],
         Mud[:, i], Mue[:, i],
         Sigmad[:, i], Sigmae[:, i]) = bubble_properties(
            bubble_dim, sample_new, method, rd_stat, i + 1, num_str, mtype,
            measure_data.get('nbins_density', [16] * n_groups)[i],
            measure_data.get('nbins_exceedance', [22] * n_groups)[i])

        fig_name = os.path.join(rd_stat, f'Statistics_{num_str}.png')
        plt.figure(i + 1)
        plt.tight_layout()
        plt.savefig(fig_name, dpi=150, bbox_inches='tight')

        # ---- Fractal index (Otsuki, 1998) - optional --------------------
        if do_fractal:
            group_name = measure_data.get('group_names', [None] * n_groups)[i] \
                or f'Group {i + 1}'
            fractal_rows.append(fractal_index(
                equiv_diams, sample_new['Area'], sample_new['px2m'],
                group_name, num_str, rd_stat,
                interactive_callback=fractal_callback))

    '''# ---- Summary plots ------------------------------------------------------
    colors = ['b', 'r', 'k', 'm']
    labels = ['Exponential', 'Weibull', 'Normal', 'Logistic']
    gi = np.arange(1, n_groups + 1)

    # -- chi-square plot --
    fig_x2, (ax1, ax2) = plt.subplots(2, 1, figsize=(4, 5.3))
    fig_x2.patch.set_facecolor('white')
    for k in range(4):
        ax1.plot(gi, X2d[k, :], 'o-',  color=colors[k], markersize=10, label=labels[k])
        ax2.plot(gi, X2e[k, :], '+--', color=colors[k], markersize=10, label=labels[k])
    for ax in (ax1, ax2):
        ax.set_ylabel('\u03C7\u00B2')   # χ²
        ax.set_xlabel('Images')
        ax.set_xlim(gi.min() - 0.2, gi.max() + 0.2)
        ax.set_xticks(gi)
    ax2.legend(fontsize=9)
    fig_x2.tight_layout()
    fig_x2.savefig(os.path.join(rd_stat, 'Statistics_X2.png'),
                   dpi=150, bbox_inches='tight')

    # -- parameters plot --
    fig_p, (ax_a, ax_m, ax_s) = plt.subplots(3, 1, figsize=(4, 8))
    fig_p.patch.set_facecolor('white')
    for k in range(4):
        ax_a.plot(gi, Alphad[k, :], 'o-', color=colors[k], markersize=10, label=labels[k])
        ax_m.plot(gi, Mud[k, :],    'o-', color=colors[k], markersize=10)
        ax_m.plot(gi, Mue[k, :],    '+--', color=colors[k], markersize=10)
        ax_s.plot(gi, Sigmad[k, :], 'o-', color=colors[k], markersize=10)
        ax_s.plot(gi, Sigmae[k, :], '+--', color=colors[k], markersize=10)
    ax_a.set_ylabel('\u03B1')   # α
    ax_m.set_ylabel('\u03BC')   # μ
    ax_s.set_ylabel('\u03C3')   # σ
    for ax in (ax_a, ax_m, ax_s):
        ax.set_xlabel('Images')
        ax.set_xlim(gi.min() - 0.2, gi.max() + 0.2)
        ax.set_xticks(gi)
    ax_a.legend(fontsize=9)
    fig_p.tight_layout()
    fig_p.savefig(os.path.join(rd_stat, 'Statistics_parameters.png'),
                  dpi=150, bbox_inches='tight')'''

    # ---- Fractal index summary ---------------------------------------------
    if do_fractal and fractal_rows:
        fi_df = pd.DataFrame(fractal_rows,
                             columns=['group', 'alpha', 'beta', 'R2', 'Dc'])
        fi_csv = os.path.join(rd_stat, 'FractalIndex.csv')
        fi_df.to_csv(fi_csv, index=False)
        print('Fractal index summary saved to:', fi_csv)

    plt.close('all')
    print('\nDone. Results saved to:', rd_stat)
