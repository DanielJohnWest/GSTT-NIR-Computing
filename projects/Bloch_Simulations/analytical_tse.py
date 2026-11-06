"""
Analytical steady-state echo train of the TSE sequence for each tissue (ideal CPMG).

The 90 degree excitation leaves Mz = 0. Between instantaneous 180 degree refocusing pulses
(at ESP/2, 3 ESP/2, ...) Mz recovers with T1, and each pulse inverts it; after the last pulse
Mz recovers until the next excitation at TR. Because the excitation saturates Mz completely,
that final Mz is the steady state, Mss. Echo n (at n ESP) is then:

    S_n = PD Mss exp(-n ESP / T2)

(spin echoes refocus T2 prime, so T2 rather than T2*). With n_echo = 1 this is the classic
spin-echo formula S = PD [1 - 2 exp(-(TR - TE/2)/T1) + exp(-TR/T1)] exp(-TE/T2).

Assumes a single isochromat and instantaneous, ideal 90 and 180 degree pulses (no slice
profile, so no stimulated echoes). Sequence parameters and tissues are taken from
simulate_tse.py.

Output: for each tissue, the steady-state signal of every echo, in units of PD.

Differences from full isochromat simulation come from slice profile, imperfect spoiling and transients.

"""

from typing import Any

import numpy as np
import matplotlib.pyplot as plt

import simulate_tse as st

def echo_train(tissue, n_echo, esp, tr) -> np.ndarray:
    """Steady-state signal of each echo (units of PD) for ideal 90 and 180 degree pulses."""
    def recover(m, dt):  # T1 recovery of Mz = m towards 1 over time dt
        return 1 - (1 - m) * np.exp(-dt / tissue['T1'])

    mz, t_prev = 0.0, 0.0  # just after the 90 degree excitation
    for k in range(1, n_echo + 1):
        t_ref = (k - 0.5) * esp  # refocusing pulse k
        mz = -recover(mz, t_ref - t_prev)  # recover, then invert
        t_prev = t_ref
    m_ss = recover(mz, tr - t_prev)  # Mz just before the next excitation
    return np.asarray(tissue['PD'] * m_ss * np.exp(-esp * np.arange(1, n_echo + 1) / tissue['T2']))

def steady_state(seq_params=None, tissues=None, plot=True):
    """Analytical echo train, as {tissue name: signal of each echo}."""
    p: dict[str, Any] = dict(st.SEQ_PARAMS if seq_params is None else seq_params)
    tissues = st.TISSUES if tissues is None else tissues
    result = {name: echo_train(t, p['n_echo'], p['te'], p['tr']) for name, t in tissues.items()}
    te = p['te'] * np.arange(1, p['n_echo'] + 1)

    tr_ms, esp_ms = 1e3 * float(p['tr']), 1e3 * float(p['te'])
    print(f"\nAnalytical TSE signal (ideal CPMG): TR {tr_ms:g} ms, echo spacing {esp_ms:g} ms, {p['n_echo']} echoes")
    print(f"  {'tissue':26s} {'echo 1':>7s}  {'echo ' + str(p['n_echo']):>8s}")
    for name, s in result.items():
        print(f'  {name:26s} {s[0]:7.4f}  {s[-1]:8.4f}')

    if plot:
        fig, ax = plt.subplots(figsize=(8, 4))
        for name, s in result.items():
            if name != 'gel matrix':
                ax.plot(te * 1e3, s, 'o-', ms=3, label=name.split(':')[0])
        ax.set_xlabel('Echo time (ms)')
        ax.set_ylabel('Steady-state signal (units of PD)')
        ax.grid(True)
        ax.legend(fontsize=8, ncol=2)
        fig.tight_layout()
        plt.show()
    return result

if __name__ == '__main__':
    steady_state()
