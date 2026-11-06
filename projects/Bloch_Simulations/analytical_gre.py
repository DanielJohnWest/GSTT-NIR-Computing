"""
Analytical steady-state signal of the spoiled GRE sequence for each tissue (Ernst equation).

    S = PD sin(a) (1 - E1) / (1 - cos(a) E1) exp(-TE/T2*),   E1 = exp(-TR/T1)

Assumes a single isochromat, an instantaneous RF pulse with the nominal flip angle (no slice
profile) and ideal spoiling (no transverse magnetization left before each pulse).
Sequence parameters and tissues are taken from simulate_gre.py.

Output: one value per tissue, the steady-state signal at TE, in units of PD.

Differences from full isochromat simulation come from slice profile, imperfect spoiling and transients.

"""

from typing import Any

import numpy as np
import matplotlib.pyplot as plt

import simulate_gre as sg

def ernst(tissue, flip_angle_deg, tr, te):
    """Steady-state spoiled GRE signal at TE (units of PD)."""
    a = np.deg2rad(flip_angle_deg)
    e1 = np.exp(-tr / tissue['T1'])
    return tissue['PD'] * np.sin(a) * (1 - e1) / (1 - np.cos(a) * e1) * np.exp(-te / tissue['T2s'])

def steady_state(seq_params=None, tissues=None, plot=True):
    """Analytical steady-state signal at TE for each tissue, as {tissue name: signal}."""
    p: dict[str, Any] = dict(sg.SEQ_PARAMS if seq_params is None else seq_params)
    tissues = sg.TISSUES if tissues is None else tissues
    result = {name: float(ernst(t, p['flip_angle_deg'], p['tr'], p['te'])) for name, t in tissues.items()}

    fa_deg, tr_ms, te_ms = float(p['flip_angle_deg']), 1e3 * float(p['tr']), 1e3 * float(p['te'])
    print(f"\nAnalytical GRE signal (Ernst equation): FA {fa_deg:g} deg, TR {tr_ms:g} ms, TE {te_ms:g} ms")
    for name, s in result.items():
        print(f'  {name:26s} {s:.4f}')

    if plot:
        tubes = {n: s for n, s in result.items() if n != 'gel matrix'}
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.bar(range(len(tubes)), list(tubes.values()), color='gray')
        ax.set_xticks(range(len(tubes)), [n.split(':')[0] for n in tubes])
        ax.set_ylabel('Steady-state signal (units of PD)')
        ax.grid(True)
        ax.set_axisbelow(True)  # grid behind the bars
        fig.tight_layout()
        plt.show()
    return result

if __name__ == '__main__':
    steady_state()
