"""
Bubble properties: runs both density-based and exceedance-based analysis.

Statistical formulation:
  Alexander A. Proussevitch, Dork L. Sahagian, Evgeni P. Tsentalovich,
  Statistical analysis of bubble and crystal size distributions: Formulations and procedures,
  Journal of Volcanology and Geothermal Research,
  Volume 164, Issue 3, 2007, Pages 95-111,
  https://doi.org/10.1016/j.jvolgeores.2007.04.007.
"""

from src.bubble_properties.statistics.distributions import (
    exponential_moments,
    weibull_moments,
    normal_moments,
    logistic_moments,
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

    # Moments calculated using the best-fitting parameters from density-based analysis
    I = int(X2d.argmin())
    moment_functions = [
        exponential_moments,
        weibull_moments,
        normal_moments,
        logistic_moments,
    ]
    moment_function = moment_functions[I]

    if I == 0:
        moment_parameters = [0.0, Nud[I]]
    else:
        moment_parameters = [0.0, Nud[I], Sigmad[I]]

    M1_N = moment_function(moment_parameters, 1)         # V_p/N      - particle average volume
    M1_Vm = M1_N*Alphad[I]                               # V_p/V_m
    Phi = 1.0/(1.0+M1_Vm)                                # V_melt/V_tot
    M1_Vtot = M1_Vm*Phi                                  # V_p/V_tot  - particle volume fraction

    M0_Vm = Alphad[I]                                    # BND/CND per melt/matrix Volume
    M0_Vtot = M0_Vm*Phi                                  # BND/CND per total volume

    # Temporary diagnostic output
    distribution_names = ['Exponential', 'Weibull', 'Normal', 'Logistic']
    print(f'Best density distribution: {distribution_names[I]} (I={I})')
    print(f'M1_N={M1_N}, M1_Vm={M1_Vm}, M1_Vtot={M1_Vtot}')
    print(f'M0_Vm={M0_Vm}, M0_Vtot={M0_Vtot}')

    # todo
    # 1) momenti a partire da exceedance-based analysis
    # 2) altri momenti utili?
    # 3) salvare in tabella 

    return X2d, X2e, Alphad, Nud, Nue, Sigmad, Sigmae
