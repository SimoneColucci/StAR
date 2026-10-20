"""
Main runner for the Stereology module.
Equivalent of the MATLAB runStereology.m

Converts 2-D measurement tables into stereologically reconstructed 3-D size
distributions. Results (measurementsStereoTable_XXX.csv and Stereology_XXX.png)
are written into ``<output_dir>/Measurements``.
"""

import os

from .stereology.stereology import stereology


def run_stereology(measure_data):
    """
    Run the stereological conversion for every input file.

    Parameters
    ----------
    measure_data : dict
        Keys:
          - input_dir  : str, directory containing the measurement CSVs
          - input_file : list[str], CSV file names
          - output_dir : str, base output directory
    """
    rd = measure_data['output_dir']
    os.makedirs(rd, exist_ok=True)
    rd_measure = os.path.join(rd, 'Measurements')
    os.makedirs(rd_measure, exist_ok=True)

    print()
    for fname in measure_data['input_file']:
        filepath = os.path.join(measure_data['input_dir'], fname)
        if os.path.isfile(filepath):
            print(f'Convert {fname} ...')
            print()
        else:
            raise FileNotFoundError(f'File {filepath} does not exist.')

        stereology(filepath, output_dir=rd_measure)
        print('Stereological conversion successful!')

    print('\nDone. Results saved to:', rd_measure)
