"""
Input validation for bubble properties analysis.
"""

import os


def check_input_properties(measure_data, sample, method):
    """
    Validate all input parameters before running the analysis.

    Parameters
    ----------
    measure_data : dict
        Must contain 'input_dir', 'output_dir', 'input_file', 'type'.
    sample : dict
        Must contain 'px2m', 'crop_area'.
    method : dict
        Must contain 'minsearch'.
    """
    # ---- Required fields ----------------------------------------------------
    _require(measure_data, 'input_dir',  'measureData.input_dir')
    _require(measure_data, 'output_dir', 'measureData.output_dir')
    _require(measure_data, 'input_file', 'measureData.input_file')
    _require(measure_data, 'type',       'measureData.type')
    _require(sample, 'px2m',      'sample.px2m')
    _require(sample, 'crop_area', 'sample.crop_area')
    _require(method, 'minsearch', 'method.minsearch')

    # ---- Type checks --------------------------------------------------------
    if not isinstance(measure_data['input_dir'], str):
        raise TypeError('measureData.input_dir must be a string.')
    if not isinstance(measure_data['output_dir'], str):
        raise TypeError('measureData.output_dir must be a string.')

    for group in measure_data['input_file']:
        for f in group:
            if not isinstance(f, str):
                raise TypeError('All entries in measureData.input_file must be strings.')

    for group in sample['px2m']:
        for val in group:
            if not isinstance(val, (int, float)):
                raise TypeError('All entries in sample.px2m must be numbers.')

    for group in sample['crop_area']:
        for val in group:
            if not isinstance(val, (int, float)):
                raise TypeError('All entries in sample.crop_area must be numbers.')

    if method['minsearch'] not in ('fmincon', 'simplex'):
        raise ValueError(
            f"Invalid method.minsearch '{method['minsearch']}'.\n"
            "Available options:\n - fmincon\n - simplex")

    for group in measure_data['type']:
        for t in group:
            if t not in ('2D', '3D', '3Dstereo'):
                raise ValueError(
                    f"Invalid measureData.type '{t}'.\n"
                    "Available options:\n - 2D\n - 3D\n - 3Dstereo")

    # Check sample.D for 3D measurements
    for i, group in enumerate(measure_data['input_file']):
        for j, fname in enumerate(group):
            if measure_data['type'][i][j] == '3D':
                if 'D' not in sample or not sample['D']:
                    filepath = os.path.join(measure_data['input_dir'], fname)
                    raise ValueError(f"sample.D not provided for sample '{filepath}'")

    # ---- Dimension consistency ----------------------------------------------
    base_structure = [len(g) for g in measure_data['input_file']]
    num_groups = len(base_structure)

    vars_to_check = [
        (measure_data['type'],   'measureData.type'),
        (sample['px2m'],         'sample.px2m'),
        (sample['crop_area'],    'sample.crop_area'),
    ]

    for var, name in vars_to_check:
        if len(var) != num_groups:
            raise ValueError(
                f'Dimension Mismatch: "{name}" has {len(var)} groups, '
                f'but "inputFile" has {num_groups}.')
        for i in range(num_groups):
            expected = base_structure[i]
            actual = len(var[i])
            if actual != expected:
                raise ValueError(
                    f'Consistency Error in "{name}":\n'
                    f'At Group Index {{{i}}}, {actual} elements were found,\n'
                    f'but "measureData.input_file" expects {expected} elements.')

    # ---- Optional per-group bin counts --------------------------------------
    for key in ('nbins_density', 'nbins_exceedance'):
        vals = measure_data.get(key)
        if vals is None:
            continue
        if len(vals) != num_groups:
            raise ValueError(
                f'Dimension Mismatch: "measureData.{key}" has {len(vals)} '
                f'entries, but "inputFile" has {num_groups} groups.')
        for v in vals:
            if not isinstance(v, int) or isinstance(v, bool) or v < 3:
                raise ValueError(
                    f'Invalid measureData.{key} value {v!r}: '
                    'it must be an integer >= 3.')

    # ---- File existence -----------------------------------------------------
    for group in measure_data['input_file']:
        for fname in group:
            path = os.path.join(measure_data['input_dir'], fname)
            if not os.path.isfile(path):
                raise FileNotFoundError(f'Input measurements file "{path}" not found.')


def _require(d, key, display_name):
    """Check that *key* exists in dict *d* and is not None/empty."""
    if key not in d or d[key] is None:
        raise ValueError(f'Missing Parameter: {display_name} is required.')
    if isinstance(d[key], (str, list)) and len(d[key]) == 0:
        raise ValueError(f'Missing Parameter: {display_name} is required.')
