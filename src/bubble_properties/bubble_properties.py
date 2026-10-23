"""
Bubble properties: runs both density-based and exceedance-based analysis.

Statistical formulation:
  Alexander A. Proussevitch, Dork L. Sahagian, Evgeni P. Tsentalovich,
  Statistical analysis of bubble and crystal size distributions: Formulations and procedures,
  Journal of Volcanology and Geothermal Research,
  Volume 164, Issue 3, 2007, Pages 95-111,
  https://doi.org/10.1016/j.jvolgeores.2007.04.007.
"""

import csv
import os

from src.bubble_properties.statistics.distributions import (
    exponential_moments,
    weibull_moments,
    lognormal_moments,
    loglogistic_moments,
)

from .statistics.density_based_analysis import density_based_analysis
from .statistics.exceedance_based_analysis import exceedance_based_analysis


def bubble_properties(bubble_dim, sample_new, method, rd, idx, num, mtype,
                      nbins_density=16, nbins_exceedance=22):
    """
    Run both density-based and exceedance-based statistical analysis.

    Parameters
    ----------
    nbins_density : int, optional
        Bin-edge grid size for the density-based histogram (default 16).
    nbins_exceedance : int, optional
        Bin-edge grid size for the exceedance-based histogram (default 22).

    Returns
    -------
    X2d, X2e, Alphad, Nud, Nue, Sigmad, Sigmae : ndarray (4,)
    """
    # linear distribution density-based analysis
    X2d, Alphad, Nud, Sigmad = density_based_analysis(
        bubble_dim, sample_new, method, rd, idx, num, mtype, nbins_density)

    # exceedance-based analysis
    X2e, Nue, Sigmae = exceedance_based_analysis(
        bubble_dim, sample_new, method, rd, idx, num, mtype,
        nbins_exceedance)

    # Moments of the logarithmic distribution
    # M*_N: moments per particle (normalized by total number of particles)
    # M*_Vm: moments per melt/matrix volume (normalized by volume of melt/matrix)
    # M*_Vtot: moments per total volume (normalized by total volume)

    moment_functions = [
        exponential_moments,
        weibull_moments,
        lognormal_moments,
        loglogistic_moments,
    ]

    not_defined = 'not defined (n>=k)'

    def calculate_moment(moment_function, parameters, order):
        """Return a moment, or a marker when the logistic moment diverges."""
        try:
            return moment_function(parameters, order)
        except ValueError as error:
            if 'n >= kappa' not in str(error):
                raise
            return None

    def format_value(value, format_spec):
        return not_defined if value is None else format(value, format_spec)

    Id = int(X2d.argmin())
    moment_function = moment_functions[Id]
    if Id == 0:
        moment_parameters_d = [0.0, Nud[Id]]
    else:
        moment_parameters_d = [0.0, Nud[Id], Sigmad[Id]]

    M1_Nd = calculate_moment(moment_function, moment_parameters_d, 1)  # V_p/N
    if M1_Nd is None:
        M1_Vm = Phi = M1_Vtot = None
    else:
        M1_Vm = M1_Nd*Alphad[Id]                       # V_p/V_m
        Phi = 1.0/(1.0+M1_Vm)                         # V_melt/V_tot
        M1_Vtot = M1_Vm*Phi                           # V_p/V_tot

    M0_Vm = Alphad[Id]                                 # BND/CND per melt/matrix Volume
    M0_Vtot = None if Phi is None else M0_Vm*Phi        # BND/CND per total volume

    Ie = int(X2e.argmin())
    moment_function = moment_functions[Ie]
    if Ie == 0:
        moment_parameters_e = [0.0, Nue[Ie]]
    else:
        moment_parameters_e = [0.0, Nue[Ie], Sigmae[Ie]]

    M1_Ne = calculate_moment(moment_function, moment_parameters_e, 1)  # V_p/N

    # Print results
    def scientific(value):
        mantissa, separator, exponent = f'{value:.3E}'.partition('E')
        return f'{mantissa}E{int(exponent)}' if separator else mantissa

    distribution_names = ['Exponential', 'Weibull', 'log-Normal', 'log-Logistic']
    is_2d = mtype[0] == '2D'
    measure = 'area' if is_2d else 'volume'
    measure_unit = 'm²' if is_2d else 'm³'
    density_unit = 'm⁻²' if is_2d else 'm⁻³'
    fraction_unit = 'area %' if is_2d else 'vol %'
    print('\n#### Properties of the particle population ####')
    print(f'Best distribution density: {distribution_names[Id]}')
    print(f'Best exceedance function: {distribution_names[Ie]}')
    print(f'Average particle {measure} [{measure_unit}]: {format_value(M1_Nd, ".3E")} (density-based) - {format_value(M1_Ne, ".3E")} (exceedance-based)')
    print(f'Particle {measure} fraction [{fraction_unit}]: {not_defined if M1_Vtot is None else f"{M1_Vtot*100.0:.2f}"}')
    print(f'Particle number density (per melt/matrix {measure}) [{density_unit}]: {scientific(M0_Vm)}')
    print(f'Particle number density (per total {measure}) [{density_unit}]: {not_defined if M0_Vtot is None else scientific(M0_Vtot)}')

    # Save the population properties alongside the fitting tables.
    table_rows = [
        ['Best distribution density', distribution_names[Id], ''],
        ['Best exceedance function', distribution_names[Ie], ''],
        [f'Average particle {measure} (density-based)', format_value(M1_Nd, '.3E'), measure_unit],
        [f'Average particle {measure} (exceedance-based)', format_value(M1_Ne, '.3E'), measure_unit],
        [f'Particle {measure} fraction', not_defined if M1_Vtot is None else f'{M1_Vtot*100.0:.2f}', fraction_unit],
        [f'Particle number density (per melt/matrix {measure})', scientific(M0_Vm), density_unit],
        [f'Particle number density (per total {measure})', not_defined if M0_Vtot is None else scientific(M0_Vtot), density_unit],
    ]
    table_path = os.path.join(rd, f'Properties_{num}.csv')
    with open(table_path, 'w', newline='', encoding='utf-8') as table_file:
        writer = csv.writer(table_file)
        writer.writerows(table_rows[:2])
        writer.writerow([])
        writer.writerow(['Property', 'Value', 'Unit'])
        writer.writerows(table_rows[2:])

    return X2d, X2e, Alphad, Nud, Nue, Sigmad, Sigmae
