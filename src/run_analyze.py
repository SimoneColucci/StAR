"""
Main runner for the Analyze module.
Equivalent of the MATLAB runAnalyzeBubble.m

For every input image it performs threshold segmentation, measures the region
properties, scales them to physical units using ``px2m`` and saves:
  - <output>/Measurements/measurementsTable_XXX.csv
  - <output>/LabeledImages/<input_name>_label_XXX.<input_extension>

After processing, frequency histograms of the measured properties are saved
in <output>/Measurements/Figures. Files belonging to the same group are
plotted together. The ``Orientation`` property is drawn as a rose diagram.
"""

import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from .analyze.analyze_bubble import analyze_bubble
from .analyze.property_figures import save_property_figures

# Columns scaled linearly by px2m (Area is scaled by px2m**2)
_LINEAR_COLS = ['EquivDiameter', 'MajorAxisLength', 'MinorAxisLength',
                'Perimeter', 'MaxFeretDiameter', 'MinFeretDiameter']


def _normalise_ranges(technique_range, n_files):
    """Return a list of [min, max] ranges, one per file."""
    rng = technique_range
    # single [min, max] pair -> replicate
    arr = np.asarray(rng, dtype=float)
    if arr.ndim == 1 and arr.size == 2:
        return [list(arr)] * n_files
    # list of pairs
    ranges = [list(np.asarray(r, dtype=float).ravel()) for r in rng]
    if len(ranges) == 1:
        ranges = ranges * n_files
    return ranges


def _normalise_px2m(px2m, n_files):
    arr = np.atleast_1d(np.asarray(px2m, dtype=float))
    if arr.size == 1:
        return np.full(n_files, arr[0])
    return arr


def run_analyze(img_data, technique):
    """
    Parameters
    ----------
    img_data : dict
        input_dir  : str
        input_file : list[str]
        output_dir : str
        px2m       : float | list[float]  (m/pixel)
    technique : dict
        range : [min, max] or list of [min, max] per file
    """
    input_files = img_data['input_file']
    n_files = len(input_files)

    rd = img_data['output_dir']
    os.makedirs(rd, exist_ok=True)
    rd_fig = os.path.join(rd, 'LabeledImages')
    os.makedirs(rd_fig, exist_ok=True)
    rd_measure = os.path.join(rd, 'Measurements')
    os.makedirs(rd_measure, exist_ok=True)

    px2m = _normalise_px2m(img_data['px2m'], n_files)
    ranges = _normalise_ranges(technique['range'], n_files)

    all_dfs = []
    measure_names = []
    for i in range(n_files):
        fname = input_files[i]
        image_path = os.path.join(img_data['input_dir'], fname)
        print(f'Analyzing image file "{image_path}".')

        props, gray, boundaries, n_blobs = analyze_bubble(
            image_path, {'range': ranges[i]})

        df = pd.DataFrame(props)

        # ---- Scale to physical units ------------------------------------
        p = px2m[i]
        if not df.empty:
            for col in _LINEAR_COLS:
                if col in df.columns:
                    df[col] = df[col] * p
            df['Area'] = df['Area'] * (p ** 2)

        # ---- Save measurements table (CSV only) -------------------------
        base = f'measurementsTable_{i + 1:03d}'
        csv_path = os.path.join(rd_measure, base + '.csv')
        df.to_csv(csv_path, index=False)
        all_dfs.append(df)
        measure_names.append(base + '.csv')
        print(f'  Saved {csv_path}')

        # ---- Plot labelled image ----------------------------------------
        fig, ax = plt.subplots()
        ax.set_title('Segmented image')
        ax.imshow(gray, cmap='gray', vmin=0, vmax=255)
        ax.axis('image')
        for b in boundaries:
            ax.plot(b[:, 1], b[:, 0], 'y', linewidth=1)
        ax.axis('off')
        image_name, image_ext = os.path.splitext(os.path.basename(fname))
        name_prefix, separator, image_index = image_name.rpartition('_')
        if separator and image_index.isdigit():
            label_name = f'{name_prefix}_label_{image_index}'
        else:
            label_name = f'{image_name}_label'
        if image_ext.lstrip('.').lower() not in fig.canvas.get_supported_filetypes():
            image_ext = '.png'
        fig_path = os.path.join(rd_fig, label_name + image_ext)
        fig.savefig(fig_path, dpi=150, bbox_inches='tight')
        plt.close(fig)

    # ---- Property frequency figures (per group) -------------------------
    groups = img_data.get('groups')
    if not groups:
        groups = [{'name': 'Group 1', 'indices': list(range(n_files))}]
    rd_prop_fig = os.path.join(rd_measure, 'Figures')
    save_property_figures(all_dfs, measure_names, groups, rd_prop_fig)
    print('Property figures saved to:', rd_prop_fig)

    print('\nDone. Results saved to:', rd_measure)
