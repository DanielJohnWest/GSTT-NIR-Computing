"""
Find the spoiled GRE parameters (flip angle, TR, TE) that give the most contrast between two
tissues of the digital phantom, then check the result with the full Bloch simulation.

  1. Search: the steady-state signal of each tissue comes from the Ernst equation
     (analytical_gre.ernst), which is fast enough to evaluate on a fine grid of flip angle,
     TR and TE. Contrast is S_a - S_b in units of PD, so the search makes tissue A as much
     brighter than tissue B as possible; swapping A and B gives the reverse contrast. With
     METRIC = 'efficiency' the contrast |S_a - S_b| per square root of TR is maximised
     instead, whichever tissue is brighter: for a fixed scan time, repeating a shorter TR
     more often averages the noise down by sqrt(number of repeats).
  2. Limits: TE and TR cannot be shorter than write_gre can play (found by trying to build
     the sequence), and are capped at TE_MAX and TR_MAX.
  3. Check: the Bloch simulator of simulate_gre.py plays the sequence from full relaxation
     until well past steady state, recording both tissues' signals at the echo centre of
     every TR. This gives the steady-state contrast of the real sequence (with its slice
     profile and RF spoiling, which the Ernst equation ignores), the contrast write_gre gives
     with no dummy scans (at the centre of k-space), and the number of dummy TRs needed for
     the first acquired line to be within SETTLE_TOL of steady-state.

The simulated signal jitters by about 1% from TR to TR (finite isochromats, see ISO_PER_CYCLE
in simulate_gre.py), so it is averaged over AVERAGE_TRS TRs before testing the tolerance. Sequence parameters other than
flip angle, TR and TE, and the tissues, are taken from simulate_gre.py, which is not changed.
"""

import contextlib
import io
from typing import Any

import numpy as np
import matplotlib.pyplot as plt

import simulate_gre as sg
from analytical_gre import ernst

TISSUE_A = 'H'  # Tissue names/letter
TISSUE_B = 'B'
METRIC = 'efficiency'  # 'contrast' = S_a - S_b; 'efficiency' = |S_a - S_b| / sqrt(TR in s)

FA_MAX = 90.0  # degrees
TE_MAX = 20e-3  # s
TR_MAX = 1.0  # s; longer TR also means a longer scan (n_y x TR)
BLOCH_CHECK = True  # run the full simulation at the current and optimal parameters (about 1 min)
SETTLE_TOL = 0.01  # dummy TRs: signals within 1% of steady state
AVERAGE_TRS = 32  # TRs averaged before testing SETTLE_TOL

# --------------------------------------------------------------------------
# HELPERS
# --------------------------------------------------------------------------
def find_tissue(name, tissues):
    """Full tissue name from a name or a tube letter ('A' -> 'A: short post-GBCA blood')."""
    matches = [n for n in tissues if n == name or n.split(':')[0] == name]
    if len(matches) != 1:
        raise ValueError(f'tissue {name!r} not found; choose from {list(tissues)}')
    return matches[0]


def can_play(p, te, tr):
    """True if write_gre can build the sequence with this TE and TR."""
    try:
        with contextlib.redirect_stdout(io.StringIO()):  # hide the timing-check messages
            sg.build_gre(plot=False, write_seq=False, **{**p, 'te': te, 'tr': tr})
        return True
    except AssertionError:
        return False


def shortest(ok, hi: float, tol: float = 1e-5) -> float:
    """Smallest value in (0, hi] for which ok(value) is True, by bisection (to tol)."""
    lo = 0.0
    if not ok(hi):
        raise ValueError(f'the sequence cannot be played even at {hi * 1e3:g} ms')
    while hi - lo > tol:
        mid = (lo + hi) / 2
        lo, hi = (lo, mid) if ok(mid) else (mid, hi)
    return hi


def score(a, b, fa, tr, te, metric):
    """Contrast S_a - S_b (positive when a is brighter), or contrast efficiency |S_a - S_b| / sqrt(TR)."""
    c = ernst(a, fa, tr, te) - ernst(b, fa, tr, te)
    return np.abs(c) / np.sqrt(tr) if metric == 'efficiency' else c


def signal_per_tr(p, tissues, n_tr):
    """Signal of each tissue at the echo centre of each of the first n_tr TRs, starting from
    full relaxation. Array (tissue, TR), units of PD. With n_tr = n_y this is write_gre as
    written (no dummies); longer runs play extra copies of the first TR in front (play_list's
    dummy scans), marked as acquired so that every TR is recorded."""
    with contextlib.redirect_stdout(io.StringIO()):
        # noinspection PyTypeChecker
        seq: sg.Sequence = sg.build_gre(plot=False, write_seq=False, **{**p, 'n_dummy': 0})
        sim = sg.BlochSim(list(tissues.values()), p['slice_thickness'],
                          sg.net_moment_per_tr(seq, p['slice_thickness']))
        play = [(b, False, ph) for b, _, ph in sg.play_list(seq, n_tr - p['n_y'])]
        signal = sim.run(play)
    kx = seq.calculate_kspace()[0][0][:p['n_x']]
    centre = int(np.argmin(np.abs(kx)))  # echo centre (kx = 0) within each readout
    pd = np.array([t['PD'] for t in tissues.values()])
    return pd[:, None] * np.abs(signal[:, centre::p['n_x']]) / p['slice_thickness']


def running_mean(curve):
    """Mean over AVERAGE_TRS TRs: column n is the mean of TRs n .. n + AVERAGE_TRS - 1."""
    k = np.ones(AVERAGE_TRS) / AVERAGE_TRS
    return np.array([np.convolve(c, k, 'valid') for c in curve])


def dummies_needed(curve):
    """Fewest dummy TRs after which every tissue's (averaged) signal stays within SETTLE_TOL
    of its steady state."""
    avg = running_mean(curve)
    off = np.any(np.abs(avg / avg[:, -1:] - 1) > SETTLE_TOL, axis=0)
    return int(np.nonzero(off)[0].max() + 1) if off.any() else 0


# --------------------------------------------------------------------------
# MAIN
# --------------------------------------------------------------------------
def optimise(seq_params=None, tissues=None, name_a=TISSUE_A, name_b=TISSUE_B, metric=METRIC,
             bloch_check=BLOCH_CHECK, plot=True):
    """Optimal {flip_angle_deg, tr, te} for contrast between two tissues (and n_dummy, with bloch_check)."""
    p: dict[str, Any] = dict(sg.SEQ_PARAMS if seq_params is None else seq_params)
    tissues = sg.TISSUES if tissues is None else tissues
    name_a, name_b = find_tissue(name_a, tissues), find_tissue(name_b, tissues)
    a, b = tissues[name_a], tissues[name_b]

    # 1. Shortest TE and TR the sequence can play. TR grows one-for-one with TE.
    te_min = shortest(lambda te_try: can_play(p, te_try, TR_MAX), TE_MAX)
    tr_min = shortest(lambda tr_try: can_play(p, te_min, tr_try), TR_MAX)
    te_min, tr_min = np.ceil(te_min / 1e-5) * 1e-5, np.ceil(tr_min / 1e-4) * 1e-4  # 0.01 / 0.1 ms

    # 2. Grid search (Ernst equation), keeping only TR >= tr_min + (TE - te_min).
    fa = np.arange(1, FA_MAX + 0.25, 0.5)[:, None, None]
    tr = np.unique(np.round(np.geomspace(tr_min, TR_MAX, 300), 4))[None, :, None]
    te = np.round(np.linspace(te_min, TE_MAX, 60), 5)[None, None, :]
    s = np.where(tr >= tr_min + (te - te_min) - 1e-9, score(a, b, fa, tr, te, metric), -np.inf)
    i_fa, i_tr, i_te = np.unravel_index(np.argmax(s), s.shape)
    best: dict[str, Any] = dict(flip_angle_deg=float(fa[i_fa, 0, 0]), tr=float(tr[0, i_tr, 0]), te=float(te[0, 0, i_te]))
    opt: dict[str, Any] = {**p, **best}

    unit = '/sqrt(s)' if metric == 'efficiency' else ''
    goal = f'Contrast between {name_a} and {name_b}' if metric == 'efficiency' else f'{name_a} brighter than {name_b}'
    print(f'\n{goal} ({metric}), Ernst equation')
    print(f'  shortest TE {te_min * 1e3:.2f} ms, shortest TR {tr_min * 1e3:.1f} ms')
    for label, q in (('current', p), ('optimal', opt)):
        fa_deg, tr_s, te_s = float(q['flip_angle_deg']), float(q['tr']), float(q['te'])
        c = float(score(a, b, fa_deg, tr_s, te_s, metric))
        print(f"  {label}: FA {fa_deg:g} deg, TR {tr_s * 1e3:g} ms, TE {te_s * 1e3:g} ms"
              f" -> {c:.4f}{unit}  (scan time {int(q['n_y']) * tr_s:.1f} s)")

    # 3. Check with the full Bloch simulation (two tissues only).
    if bloch_check:
        pair = {name_a: a, name_b: b}
        la, lb = name_a.split(':')[0], name_b.split(':')[0]
        t1_max = max(float(a['T1']), float(b['T1']))
        print('\nFull Bloch simulation (signal at the echo centre, units of PD)')
        for label, q in (('current', p), ('optimal', opt)):
            # From full relaxation until well past steady state (8 T1 of the longer-T1 tissue).
            n_tr = max(int(np.ceil(8 * t1_max / q['tr'])), q['n_y']) + AVERAGE_TRS
            curve = signal_per_tr(q, pair, n_tr)
            ss_a, ss_b = (float(x) for x in running_mean(curve)[:, -1])  # steady state
            nd_a, nd_b = (float(x) for x in signal_per_tr(q, pair, q['n_y'])[:, q['n_y'] // 2])  # no dummies, k = 0
            norm = float(np.sqrt(q['tr'])) if metric == 'efficiency' else 1.0
            q['n_dummy'] = dummies_needed(curve)
            d_ss, d_nd = ss_a - ss_b, nd_a - nd_b
            if metric == 'efficiency':
                d_ss, d_nd = abs(d_ss), abs(d_nd)
            print(f"  {label}: steady state {la} {ss_a:.4f}, {lb} {ss_b:.4f} -> {d_ss / norm:.4f}{unit};"
                  f" with no dummies {d_nd / norm:.4f}{unit};"
                  f" dummies needed {q['n_dummy']} ({q['n_dummy'] * q['tr']:.1f} s)")
            if plot and label == 'optimal':
                plot_approach(curve, q['n_dummy'], q, la, lb)
        print(f"\nTo write the optimal sequence, call write_gre.main with:\n"
              f"    main(plot=True, write_seq=True, flip_angle_deg={opt['flip_angle_deg']:g}, "
              f"tr={opt['tr']:.4g}, te={opt['te']:.4g}, n_dummy={opt['n_dummy']})")
        best['n_dummy'] = opt['n_dummy']

    if plot:
        plot_map(a, b, fa[:, 0, 0], tr[0, :, 0], best, p, metric, name_a, name_b)
    return best


def plot_map(a, b, fa, tr, best: dict[str, Any], current: dict[str, Any], metric: str, name_a, name_b):
    """Contrast against flip angle and TR, at the optimal TE. For 'contrast' (signed): red,
    tissue A brighter; blue, tissue B brighter; dashed line, where they swap."""
    c = score(a, b, fa[:, None], tr[None, :], best['te'], metric)
    fig, ax = plt.subplots(figsize=(7, 4.5))
    if metric == 'efficiency':
        im = ax.pcolormesh(tr * 1e3, fa, c, shading='auto', cmap='viridis')
    else:
        lim = float(np.abs(c).max())
        im = ax.pcolormesh(tr * 1e3, fa, c, shading='auto', cmap='RdBu_r', vmin=-lim, vmax=lim)
        ax.contour(tr * 1e3, fa, c, levels=[0], colors='k', linewidths=1, linestyles='--')
    ax.contour(tr * 1e3, fa, c, levels=[0.9 * c.max()], colors='w', linewidths=1)  # 90% of best
    ax.plot(best['tr'] * 1e3, best['flip_angle_deg'], 'wo', ms=8, label='Optimal')
    ax.plot(current['tr'] * 1e3, current['flip_angle_deg'], 'ro', ms=8, label='Current')
    ax.tick_params(labelsize=12)
    ax.set_xscale('log')
    ax.set_xlabel('TR (ms)', fontsize=14)
    ax.set_ylabel('FA (deg)', fontsize=14)
    ax.set_title(f"{name_a.split(':')[0]} vs {name_b.split(':')[0]} (TE = {float(best['te']) * 1e3:g} ms)", fontsize=16, fontweight='bold')
    ax.legend(fontsize=14, loc='upper left')
    ax.grid(visible=True, axis='both', which='both')
    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label('|Sa - Sb| / sqrt(TR)' if metric == 'efficiency' else 'Sa - Sb (PD units)', fontsize=14)
    cbar.ax.tick_params(labelsize=14)
    fig.tight_layout()
    plt.show()


def plot_approach(curve, n_dummy, q: dict[str, Any], la, lb):
    """Signal of the two tissues TR by TR from full relaxation, with the dummy TRs needed."""
    n = np.arange(curve.shape[1])
    avg = running_mean(curve)
    fig, ax = plt.subplots(figsize=(7, 4))
    for c, m, name, col in zip(curve, avg, (la, lb), ('C0', 'C1')):
        ax.plot(n, c, color=col, lw=0.5, alpha=0.4)
        ax.plot(n[:m.size], m, color=col, lw=1.5, label=f'{name} ({AVERAGE_TRS}-TR mean)')
        ax.axhline(m[-1], color=col, ls='--', lw=0.8)
    ax.tick_params(labelsize=12)
    ax.axvline(n_dummy, color='k', ls=':', lw=1, label=f'{n_dummy} Dummy TRs')
    ax.set_xlim(0, min(curve.shape[1], max(3 * n_dummy, 2 * q['n_y'])))
    ax.set_xlabel('TR no.', fontsize=12)
    ax.set_ylabel('Signal (PD units)', fontsize=12) # At echo center.
    ax.grid(visible=True, axis='both', which='both')
    fa_deg, tr_ms = float(q['flip_angle_deg']), float(q['tr']) * 1e3
    ax.set_title(f"FA {fa_deg:g} deg, TR {tr_ms:g} ms", fontsize=14, fontweight='bold')
    ax.legend(fontsize=12)
    fig.tight_layout()
    plt.show()


if __name__ == '__main__':
    optimise()
