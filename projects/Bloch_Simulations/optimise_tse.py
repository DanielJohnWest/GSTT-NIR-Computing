"""
Find the TSE parameters (echo train length, echo spacing, TR) that give the most contrast
between two tissues of the digital phantom, then check the result with the full Bloch simulation.

  1. Search: the steady-state signal of each tissue at the effective echo (the echo that fills
     the centre of k-space, echo n_echo/2 in write_tse) comes from the ideal CPMG model
     (analytical_tse.echo_train), which is fast enough to evaluate on a fine grid of echo
     train length, echo spacing and TR. Contrast is S_a - S_b in units of PD, so the search
     makes tissue A as much brighter than tissue B as possible; swapping A and B gives the
     reverse contrast. With METRIC = 'efficiency' the contrast |S_a - S_b| per square root of
     the time per k-space line (TR / n_echo) is maximised instead, whichever tissue is
     brighter: for a fixed scan time, acquiring the lines faster averages the noise down by
     sqrt(number of repeats). With n_echo = 1 this is the same measure as in optimise_gre.
  2. Limits: echo spacing and TR cannot be shorter than write_tse can play (found by trying to
     build the sequence), and are capped at ESP_MAX and TR_MAX. Echo spacings are multiples of
     ESP_STEP (20 us), because write_tse needs half of each gap on the 10 us gradient raster.
     The refocusing flip angle is fixed (180 degrees, as in simulate_tse.py).
  3. Check: the Bloch simulator of simulate_tse.py plays the sequence from full relaxation
     until well past steady state, recording both tissues' signals at the centre of the
     effective echo of every TR. This gives the steady-state contrast of the real sequence
     (with its slice profiles and stimulated echoes, which the CPMG model ignores), the
     contrast write_tse gives with no dummy scans (at the centre of k-space), and the number of
     dummy TRs needed for the first acquired line to be within SETTLE_TOL of steady-state.

A TSE has no RF spoiling, so the simulated signal does not jitter from TR to TR and needs no
averaging (AVERAGE_TRS = 1). Sequence parameters other than echo train length, echo spacing
and TR, and the tissues, are taken from simulate_tse.py, which is not changed.
"""

import contextlib
import io
import warnings
from typing import Any

import numpy as np
import matplotlib.pyplot as plt

import simulate_tse as st
from analytical_tse import echo_train

TISSUE_A = 'G'  # Tissue names/letter
TISSUE_B = 'B'
METRIC = 'contrast'  # 'contrast' = S_a - S_b; 'efficiency' = |S_a - S_b| / sqrt(TR / n_echo in s)

ECHO_TRAINS = (1, 2, 4, 8, 16, 32)  # echo train lengths to try (must divide n_y)
ESP_MAX = 30e-3  # s, longest echo spacing
ESP_STEP = 20e-6  # s, echo spacings are multiples of this (2 x gradient raster)
TR_MAX = 4.0  # s; longer TR also means a longer scan (n_y / n_echo x TR)
BLOCH_CHECK = True  # run the full simulation at the current and optimal parameters (a few min)
SETTLE_TOL = 0.01  # dummy TRs: signals within 1% of steady state
AVERAGE_TRS = 1  # TRs averaged before testing SETTLE_TOL (no RF spoiling, so no jitter)

# --------------------------------------------------------------------------
# HELPERS
# --------------------------------------------------------------------------
def find_tissue(name, tissues):
    """Full tissue name from a name or a tube letter ('A' -> 'A: short post-GBCA blood')."""
    matches = [n for n in tissues if n == name or n.split(':')[0] == name]
    if len(matches) != 1:
        raise ValueError(f'tissue {name!r} not found; choose from {list(tissues)}')
    return matches[0]


def build(p, **changes):
    """write_tse sequence with these changes to p, hiding its printed messages."""
    with contextlib.redirect_stdout(io.StringIO()):
        # noinspection PyTypeChecker
        seq: st.Sequence = st.build_tse(plot=False, write_seq=False, **{**p, **changes})
    return seq


def can_play(p, n_echo, esp, tr):
    """True if write_tse can build the sequence as asked. Too short an echo spacing raises an
    error; too short a TR only gives a warning (write_tse then lengthens TR), so both count."""
    with warnings.catch_warnings():
        warnings.simplefilter('error')  # the TR-too-short warning becomes an error
        try:
            return bool(build(p, n_echo=n_echo, te=esp, tr=tr).check_timing()[0])
        except (ValueError, AssertionError, UserWarning):
            return False


def shortest(ok, hi: float, step: float) -> float:
    """Smallest multiple of step in (0, hi] for which ok(value) is True, by bisection."""
    lo, hi_n = 0, int(round(hi / step))
    if not ok(hi_n * step):
        raise ValueError(f'the sequence cannot be played even at {hi * 1e3:g} ms')
    while hi_n - lo > 1:
        mid = (lo + hi_n) // 2
        lo, hi_n = (lo, mid) if ok(mid * step) else (mid, hi_n)
    return hi_n * step


def centre_echo(p, n_echo):
    """For this echo train length: the effective echo (0-based), the TR (0-based, with no
    dummies) that acquires the centre of k-space, and the effective TE (s)."""
    seq = build(p, n_echo=n_echo, n_dummy=0)
    ktraj_adc, _, t_exc, _, t_adc = seq.calculate_kspace()
    i0 = int(np.argmin(np.abs(ktraj_adc[0]) + np.abs(ktraj_adc[1])))
    line = i0 // p['n_x']  # acquired lines run echo by echo, TR by TR
    t_exc = np.asarray(t_exc)
    te_eff = float(t_adc[i0] - t_exc[t_exc <= t_adc[i0]].max())
    return line % n_echo, line // n_echo, te_eff


def signal(tissue, n_echo, esp, tr, echo):
    """Steady-state signal at the effective echo (units of PD), from the ideal CPMG model."""
    return echo_train(tissue, n_echo, esp, np.asarray(tr)[..., None])[..., echo]


def score(a, b, n_echo, esp, tr, echo, metric):
    """Contrast S_a - S_b (positive when a is brighter), or contrast efficiency
    |S_a - S_b| / sqrt(TR / n_echo)."""
    c = signal(a, n_echo, esp, tr, echo) - signal(b, n_echo, esp, tr, echo)
    return np.abs(c) / np.sqrt(np.asarray(tr) / n_echo) if metric == 'efficiency' else c


def signal_per_tr(p, tissues, n_tr):
    """Signal of each tissue at the centre of the effective echo of each of the first n_tr
    TRs, starting from full relaxation. Array (tissue, TR), units of PD. The sequence is built
    with no dummies and extra copies of its first TR are played in front, marked as acquired
    so that every TR is recorded. With no RF spoiling every TR is the same apart from phase
    encoding, which does not change the tissue signal, so the copies are exact. (Each RF
    pulse keeps its own phase, so the echo train stays CPMG.)"""
    seq = build(p, n_dummy=0)
    blocks = [seq.get_block(i) for i in seq.block_events]
    exc = [i for i, b in enumerate(blocks) if st.is_excitation(b)] + [len(blocks)]
    first_tr = blocks[exc[0]:exc[1]]
    n_ex = len(exc) - 1
    play = [(b, False, b.rf.phase_offset if b.rf else None) for b in first_tr * (n_tr - n_ex) + blocks]
    with contextlib.redirect_stdout(io.StringIO()):
        sim = st.BlochSim(list(tissues.values()), p['slice_thickness'], st.dephasing_moment(seq))
        sig = sim.run(play)
    kx = seq.calculate_kspace()[0][0][:p['n_x']]
    centre = int(np.argmin(np.abs(kx)))  # echo centre (kx = 0) within each readout
    echo = centre_echo(p, p['n_echo'])[0]
    pd = np.array([t['PD'] for t in tissues.values()])
    per_echo = np.abs(sig).reshape(len(tissues), n_tr, p['n_echo'], p['n_x'])
    return pd[:, None] * per_echo[:, :, echo, centre] / p['slice_thickness']


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
    """Optimal {n_echo, te (echo spacing), tr} for contrast between two tissues (and n_dummy,
    with bloch_check)."""
    p: dict[str, Any] = dict(st.SEQ_PARAMS if seq_params is None else seq_params)
    tissues = st.TISSUES if tissues is None else tissues
    if p['n_slices'] != 1:
        raise ValueError('optimise_tse models a single slice: set n_slices=1')
    name_a, name_b = find_tissue(name_a, tissues), find_tissue(name_b, tissues)
    a, b = tissues[name_a], tissues[name_b]
    trains = [n for n in ECHO_TRAINS if p['n_y'] % n == 0]

    # 1. Shortest echo spacing and, for each train length, shortest TR the sequence can play.
    #    TR grows by (n_echo + 1) x any increase in echo spacing.
    esp_min = shortest(lambda esp_try: can_play(p, max(trains), esp_try, TR_MAX), ESP_MAX, ESP_STEP)
    tr_min = {n: shortest(lambda t: can_play(p, n, esp_min, t), TR_MAX, 1e-4) for n in trains}
    echo = {n: centre_echo(p, n)[0] for n in trains}

    # 2. Grid search (ideal CPMG), keeping only TR >= tr_min + (n_echo + 1) (ESP - esp_min).
    esp = np.arange(esp_min, ESP_MAX + ESP_STEP / 2, 10 * ESP_STEP)  # 0.2 ms steps
    tr = np.unique(np.round(np.geomspace(min(tr_min.values()), TR_MAX, 300), 3))
    s = np.full((len(trains), esp.size, tr.size), -np.inf)
    for i, n in enumerate(trains):
        for j, e in enumerate(esp):
            ok = tr >= tr_min[n] + (n + 1) * (e - esp_min) - 1e-9
            s[i, j, ok] = score(a, b, n, float(e), tr[ok], echo[n], metric)
    i_n, i_esp, i_tr = np.unravel_index(np.argmax(s), s.shape)
    n_best = trains[i_n]
    best: dict[str, Any] = dict(n_echo=n_best, te=round(float(esp[i_esp]), 6), tr=float(tr[i_tr]))
    opt: dict[str, Any] = {**p, **best}
    if not can_play(p, n_best, best['te'], best['tr']):
        raise RuntimeError(f'write_tse cannot play the optimum found: {best}')

    unit = '/sqrt(s)' if metric == 'efficiency' else ''
    goal = f'Contrast between {name_a} and {name_b}' if metric == 'efficiency' else f'{name_a} brighter than {name_b}'
    print(f'\n{goal} ({metric}), ideal CPMG')
    print(f"  shortest echo spacing {esp_min * 1e3:.2f} ms; shortest TR "
          + ', '.join(f'{tr_min[n] * 1e3:.0f} ms ({n} echo{"es" if n > 1 else ""})' for n in trains))
    for label, q in (('current', p), ('optimal', opt)):
        n, esp_s, tr_s = int(q['n_echo']), float(q['te']), float(q['tr'])
        e, _, te_eff = centre_echo(q, n)
        c = float(score(a, b, n, esp_s, tr_s, e, metric))
        print(f"  {label}: {n} echo{'es' if n > 1 else ''}, ESP {esp_s * 1e3:g} ms (TE_eff {te_eff * 1e3:.0f} ms), TR {tr_s * 1e3:g} ms"
              f" -> {c:.4f}{unit}  (scan time {int(q['n_y']) // n * tr_s:.1f} s)")

    # 3. Check with the full Bloch simulation (two tissues only).
    if bloch_check:
        pair = {name_a: a, name_b: b}
        la, lb = name_a.split(':')[0], name_b.split(':')[0]
        t1_max = max(float(a['T1']), float(b['T1']))
        print('\nFull Bloch simulation (signal at the centre of the effective echo, units of PD)')
        for label, q in (('current', p), ('optimal', opt)):
            n, tr_s = int(q['n_echo']), float(q['tr'])
            n_ex = int(q['n_y']) // n
            # From full relaxation until well past steady state (8 T1 of the longer-T1 tissue).
            n_tr = max(int(np.ceil(8 * t1_max / tr_s)), n_ex) + AVERAGE_TRS
            curve = signal_per_tr(q, pair, n_tr)
            ss_a, ss_b = (float(x) for x in running_mean(curve)[:, -1])  # steady state
            k0_tr = centre_echo(q, n)[1]  # TR that acquires k = 0 when there are no dummies
            nd_a, nd_b = (float(x) for x in curve[:, k0_tr])  # no dummies, k = 0
            norm = float(np.sqrt(tr_s / n)) if metric == 'efficiency' else 1.0
            n_dummy = dummies_needed(curve)
            q['n_dummy'] = n_dummy
            d_ss, d_nd = ss_a - ss_b, nd_a - nd_b
            if metric == 'efficiency':
                d_ss, d_nd = abs(d_ss), abs(d_nd)
            print(f"  {label}: steady state {la} {ss_a:.4f}, {lb} {ss_b:.4f} -> {d_ss / norm:.4f}{unit};"
                  f" with no dummies {d_nd / norm:.4f}{unit};"
                  f" dummies needed {n_dummy} ({n_dummy * tr_s:.1f} s)")
            if plot and label == 'optimal':
                plot_approach(curve, n_dummy, q, la, lb)
        print(f"\nTo write the optimal sequence, call write_tse.main with:\n"
              f"    main(plot=True, write_seq=True, n_echo={opt['n_echo']}, te={opt['te']:.6g}, "
              f"tr={opt['tr']:.4g}, n_dummy={opt['n_dummy']})")
        best['n_dummy'] = opt['n_dummy']

    if plot:
        i = trains.index(n_best)
        plot_map(s[i], esp, tr, echo[n_best] + 1, best, p, centre_echo(p, int(p['n_echo']))[2],
                 metric, name_a, name_b)
    return best


def plot_map(c, esp, tr, echo_no, best: dict[str, Any], current: dict[str, Any], te_eff_current: float,
             metric: str, name_a, name_b):
    """Contrast against TR and effective TE, for the optimal echo train length (blank: TR too
    short to play). For 'contrast' (signed): red, tissue A brighter; blue, tissue B brighter;
    dashed line, where they swap."""
    c = np.where(np.isfinite(c), c, np.nan)
    te_eff = echo_no * esp  # effective TE (s) of each echo spacing
    fig, ax = plt.subplots(figsize=(7, 4.5))
    if metric == 'efficiency':
        im = ax.pcolormesh(tr * 1e3, te_eff * 1e3, c, shading='auto', cmap='viridis')
    else:
        lim = float(np.nanmax(np.abs(c)))
        im = ax.pcolormesh(tr * 1e3, te_eff * 1e3, c, shading='auto', cmap='RdBu_r', vmin=-lim, vmax=lim)
        ax.contour(tr * 1e3, te_eff * 1e3, c, levels=[0], colors='k', linewidths=1, linestyles='--')
    ax.contour(tr * 1e3, te_eff * 1e3, c, levels=[0.9 * float(np.nanmax(c))], colors='w', linewidths=1)  # 90% of best
    ax.plot(best['tr'] * 1e3, echo_no * best['te'] * 1e3, 'wo', ms=8, label='Optimal', clip_on=False)
    n_cur = int(current['n_echo'])
    on_map = n_cur == best['n_echo']  # the map is for the optimal echo train length only
    ax.plot(current['tr'] * 1e3, te_eff_current * 1e3, 'o', color='r', mfc='r' if on_map else 'none', mew=2, ms=8, zorder=5,
            label=f"Current ({n_cur} echo{'es' if n_cur > 1 else ''}{'' if on_map else ', not on this map'})")
    ax.tick_params(labelsize=12)
    ax.set_xscale('log')
    ax.set_xlabel('TR (ms)', fontsize=14)
    ax.set_ylabel('Effective TE (ms)', fontsize=14)
    n = best['n_echo']
    ax.set_title(f"{name_a.split(':')[0]} vs {name_b.split(':')[0]} ({n} echo{'es' if n > 1 else ''})", fontsize=16, fontweight='bold')
    ax.legend(fontsize=12, loc='upper center', bbox_to_anchor=(0.5, -0.2), ncol=2)  # below the map
    ax.grid(visible=True, axis='both', which='both')
    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label('|Sa - Sb| / sqrt(TR / n_echo)' if metric == 'efficiency' else 'Sa - Sb (PD units)', fontsize=14)
    cbar.ax.tick_params(labelsize=14)
    fig.tight_layout()
    plt.show()


def plot_approach(curve, n_dummy, q: dict[str, Any], la, lb):
    """Signal of the two tissues TR by TR from full relaxation, with the dummy TRs needed."""
    n = np.arange(curve.shape[1])
    avg = running_mean(curve)
    n_ex = int(q['n_y']) // int(q['n_echo'])
    fig, ax = plt.subplots(figsize=(7, 4))
    for c, m, name, col in zip(curve, avg, (la, lb), ('C0', 'C1')):
        ax.plot(n, c, 'o-', color=col, ms=3, lw=1, label=name)
        ax.axhline(m[-1], color=col, ls='--', lw=0.8)
    ax.tick_params(labelsize=12)
    ax.axvline(n_dummy, color='k', ls=':', lw=1, label=f'{n_dummy} Dummy TRs')
    ax.set_xlim(0, min(curve.shape[1], max(3 * n_dummy, 2 * n_ex, 10)))
    ax.set_xlabel('TR no.', fontsize=12)
    ax.set_ylabel('Signal (PD units)', fontsize=12)  # At the centre of the effective echo.
    ax.grid(visible=True, axis='both', which='both')
    esp_ms, tr_ms = float(q['te']) * 1e3, float(q['tr']) * 1e3
    ax.set_title(f"{q['n_echo']} echo{'es' if q['n_echo'] > 1 else ''}, ESP {esp_ms:g} ms, TR {tr_ms:g} ms", fontsize=14, fontweight='bold')
    ax.legend(fontsize=12)
    fig.tight_layout()
    plt.show()


if __name__ == '__main__':
    optimise()
