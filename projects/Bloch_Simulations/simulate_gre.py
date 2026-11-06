"""
Bloch simulation of write_gre.py sequence.

  1. Bloch simulation: for each tissue, isochromats spread through the slice (z) are
     played through every block. Each RF pulse is integrated at its raster together
     with the slice-select gradient (so the real slice profile is included); between
     events the spins precess under the exact gradient moments and off-resonance and
     relax with T1/T2. RF phase cycling and spoilers act exactly as in the sequence.
  2. Spatial encoding: the z-summed signal of each tissue is spread over that tissue's
     pixels with exp(-i 2 pi k.r), using k(t) from seq.calculate_kspace(), and the
     image is reconstructed with an FFT.

  Step 2 is exact for a spoiled sequence like this one (phase encoding rewound every
  TR, constant net spoiler moment).

T2* is modeled as T2 plus a reversible part T2' (1/T2* = 1/T2 + 1/T2'): each tissue's
isochromats get a Lorentzian spread of off-resonance, which a spin echo would refocus.
Not modelled: B1 errors, diffusion, flow, noise. Relaxation during an RF pulse is applied after it.
RF pulses stored as a few time points (e.g. block pulses) are resampled onto RF_RASTER.
"""

from typing import Any

import numpy as np
import matplotlib.pyplot as plt
from pypulseq.Sequence.sequence import Sequence  # the class (pypulseq.Sequence is also a folder)
from scipy.spatial.transform import Rotation

from write_gre import main as build_gre

# --------------------------------------------------------------------------
# Sequence parameters (passed straight to write_gre.main)
# --------------------------------------------------------------------------
SEQ_PARAMS: dict[str, Any] = dict(
    fov=256e-3,  # m, or (fov_x, fov_y)
    n_x=64,  # readout samples
    n_y=64,  # phase-encode lines
    flip_angle_deg=10,  # degrees
    slice_thickness=3e-3,  # m
    tr=12e-3,  # s
    te=5e-3,  # s
)

# Dummy TRs before acquisition (RF-spoiling phase continues through them). 0 = as write_gre.
N_DUMMY = 0

# --------------------------------------------------------------------------
# TISSUES: T1, T2, T2s (= T2*) in s, proton density, off-resonance df (Hz), and an ellipse
# (centre x, centre y, radius x, radius y) in metres. T2s must not exceed T2 (T2s = T2: no T2').
#
# T1MES phantom, 1.5 T version (Captur et al., JCMR 2016;18:58):
# - Tubes A-I: slow IR-SE (T1) / SE (T2) reference values at 1.5 T, 21 +/- 2 degC (Fig. 4A),
#   in the 3 x 3 layout of Fig. 4A viewed from the feet end (I at top left of the image).
# - Gel matrix: 1.4 T relaxometer at 22 degC (Table 2), the only published value.
# - PD is not published; set to 1. All tubes are on resonance (df = 0).
# - T2*: our 1.5 T QA protocol, mean of the
#   2026 sessions. Gel matrix was not measured; its T2* assumes the tubes' mean 1/T2' (7.2 /s).
# - Geometry measured from 1.5 T scans of the phantom:
#   bottle 119.7 x 122.0 mm (x by y) with rounded corners (superellipse
#   power 5.2), tubes 28.0 mm across on a 35.0 mm grid centred in the bottle, not rotated.
# --------------------------------------------------------------------------
TISSUES = {
    'gel matrix':                dict(T1=0.846, T2=0.141, T2s=0.0700, PD=1.0, df=0.0, ellipse=(0.000, 0.000, 0.0599, 0.0610), power=5.2),
    'I: med. post-GBCA myo':     dict(T1=0.430, T2=0.044, T2s=0.0369, PD=1.0, df=0.0, ellipse=(-0.035, 0.035, 0.014, 0.014)),
    'F: med. native myo':        dict(T1=1.090, T2=0.048, T2s=0.0391, PD=1.0, df=0.0, ellipse=(0.000, 0.035, 0.014, 0.014)),
    'C: long post-GBCA blood':   dict(T1=0.458, T2=0.189, T2s=0.0741, PD=1.0, df=0.0, ellipse=(0.035, 0.035, 0.014, 0.014)),
    'H: long post-GBCA myo':     dict(T1=0.562, T2=0.045, T2s=0.0328, PD=1.0, df=0.0, ellipse=(-0.035, 0.000, 0.014, 0.014)),
    'E: long native myo':        dict(T1=1.333, T2=0.050, T2s=0.0329, PD=1.0, df=0.0, ellipse=(0.000, 0.000, 0.014, 0.014)),
    'B: native blood':           dict(T1=1.489, T2=0.243, T2s=0.0754, PD=1.0, df=0.0, ellipse=(0.035, 0.000, 0.014, 0.014)),
    'G: short post-GBCA myo':    dict(T1=0.300, T2=0.044, T2s=0.0343, PD=1.0, df=0.0, ellipse=(-0.035, -0.035, 0.014, 0.014)),
    'D: short native myo':       dict(T1=0.803, T2=0.048, T2s=0.0368, PD=1.0, df=0.0, ellipse=(0.000, -0.035, 0.014, 0.014)),
    'A: short post-GBCA blood':  dict(T1=0.255, T2=0.155, T2s=0.0760, PD=1.0, df=0.0, ellipse=(0.035, -0.035, 0.014, 0.014)),
}

# Isochromats per cycle of the per-TR spoiler twist through the slice. Higher = better
# converged spoiling (matters most for long T2, e.g. blood) but slower. 256 is default.
# With T2 prime, the signal jitters slightly from TR to TR (up to ~1.5% at 256, ~0.5% at 1024).
ISO_PER_CYCLE = 256
SLICE_EXTENT = 1.5  # simulate z within +/- SLICE_EXTENT * slice thickness (sinc side lobes)
RF_RASTER = 1e-6  # s; integration step for RF shapes stored as a few time points (Pulseq default raster)

# --------------------------------------------------------------------------
# PHANTOM
# --------------------------------------------------------------------------
def make_phantom(fov, n_x, n_y, tissues):
    """Pixel coordinates (m) and a tissue label map (-1 = background)."""
    fov_x, fov_y = (fov, fov) if np.isscalar(fov) else fov
    X, Y = np.meshgrid((np.arange(n_x) - n_x / 2) * fov_x / n_x,
                       (np.arange(n_y) - n_y / 2) * fov_y / n_y)  # rows = y, cols = x
    label = np.full((n_y, n_x), -1)
    for i, t in enumerate(tissues.values()):
        cx, cy, rx, ry = t['ellipse']
        n = t.get('power', 2)  # 2 = ellipse; larger = rectangle with rounded corners
        label[np.abs((X - cx) / rx) ** n + np.abs((Y - cy) / ry) ** n <= 1] = i
    return X, Y, label

def tissue_map(tissues, label, key):
    """Image of one tissue property (NaN in the background), for display."""
    return np.array([t[key] for t in tissues.values()] + [np.nan])[label]

# --------------------------------------------------------------------------
# GRADIENTS (Pulseq units: Hz/m, moments in 1/m)
# --------------------------------------------------------------------------
def breakpoints(g):
    """Piecewise-linear (times, amplitudes) of a gradient within its block; a flat zero if absent."""
    if g is None:
        return np.array([0.0, 1.0]), np.zeros(2)
    if g.type == 'trap':
        t = g.delay + np.cumsum([0, g.rise_time, g.flat_time, g.fall_time])
        return t, np.array([0, g.amplitude, g.amplitude, 0])
    # Extended trapezoids and arbitrary waveforms; arbitrary ones are sampled at raster
    # centres, so add their start and end values (first/last) at the shape's edges.
    t, a = g.delay + np.asarray(g.tt, float), np.asarray(g.waveform, float)
    if t[0] > g.delay:
        t, a = np.r_[g.delay, t], np.r_[g.first, a]
    if t[-1] < g.delay + g.shape_dur:
        t, a = np.r_[t, g.delay + g.shape_dur], np.r_[a, g.last]
    return t, a

def moment(bp, t_end: float) -> float:
    """Gradient area from the block start to t_end."""
    t, a = bp
    t_end = min(t_end, float(t[-1]))
    if t_end <= t[0]:
        return 0.0
    tt = np.r_[t[t < t_end], t_end]
    aa = np.interp(tt, t, a)
    return float(np.sum(0.5 * (aa[:-1] + aa[1:]) * np.diff(tt)))

def rf_samples(rf) -> tuple[np.ndarray, np.ndarray]:
    """RF sample times (s, from the pulse delay) and complex B1 (Hz) on a uniform raster.
    Shapes stored as a few time points (e.g. block pulses: start and end only) are piecewise
    linear in Pulseq, so they are interpolated onto RF_RASTER."""
    t, s = np.asarray(rf.t, float), rf.signal
    if t.size < 2 or not np.allclose(np.diff(t), RF_RASTER):
        n = max(2, int(round((t[-1] - t[0]) / RF_RASTER)))
        tn = t[0] + (np.arange(n) + 0.5) * (t[-1] - t[0]) / n
        s = np.asarray(np.interp(tn, t, np.real(s)) + 1j * np.interp(tn, t, np.imag(s)))
        t = tn
    return t, np.asarray(s)

def is_excitation(b):
    return b.rf is not None and getattr(b.rf, 'use', 'excitation') != 'refocusing'

# --------------------------------------------------------------------------
# Sequence bookkeeping.
# --------------------------------------------------------------------------
def play_list(seq: Sequence, n_dummy=0):
    """[(block, is_dummy, rf_phase)]; dummies repeat the first TR without the ADC."""
    blocks = [seq.get_block(i) for i in seq.block_events]
    played = [(b, False, b.rf.phase_offset if b.rf else None) for b in blocks]
    if not n_dummy:
        return played
    rf_idx = [i for i, b in enumerate(blocks) if is_excitation(b)]  # TR = excitation to excitation
    first_tr = blocks[rf_idx[0]:rf_idx[1]]
    # Extend the quadratic RF-spoiling schedule backwards: phase(n) = p0 + c1 n + c2 n(n+1)/2
    p0, p1, p2 = (blocks[i].rf.phase_offset for i in rf_idx[:3])
    c2 = p2 - 2 * p1 + p0
    c1 = p1 - p0 - c2
    dummies = [(b, True, p0 + c1 * n + c2 * n * (n + 1) / 2 if b.rf else None)
               for n in range(-n_dummy, 0) for b in first_tr]
    return dummies + played

def net_moment_per_tr(seq: Sequence, slice_thickness):
    """Net z-moment of one TR; warns if TRs are not identically spoiled."""
    m = []
    for i in seq.block_events:
        b = seq.get_block(i)
        if b.rf is not None:
            m.append(np.zeros(3))
        if m:
            m[-1] += [moment(breakpoints(g), np.inf) for g in (b.gx, b.gy, b.gz)]
    m = np.array(m, dtype=float)
    min_spoil = float(np.min(np.abs(m[:, 2]))) * slice_thickness  # Spoiler cycles across the slice.
    max_spread = float(np.max(np.ptp(m, axis=0))) * slice_thickness  # TR-to-TR variation.
    if min_spoil < 1 or max_spread > 1e-3:
        print('WARNING: the sequence is not spoiled with the same net moment every TR, '
              'so the tissue-level encoding used here may be inaccurate.')
    return float(abs(m[0, 2]))

def quaternion_product(a, b):
    """a * b for quaternions stored as (w, x, y, z) along axis 0: rotation b, then a."""
    w1, x1, y1, z1 = a
    w2, x2, y2, z2 = b
    return np.array([w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2,
                     w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
                     w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2,
                     w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2])

# --------------------------------------------------------------------------
# BLOCH SIMULATION (tissue, z)
# --------------------------------------------------------------------------
class BlochSim:
    def __init__(self, tissues, slice_thickness, net_gz):
        self.T1, self.T2, self.df = (np.array([t[k] for t in tissues])[:, None] for k in ('T1', 'T2', 'df'))
        # Space z so the spoiler advances the phase by 2*pi/ISO_PER_CYCLE per isochromat.
        self.dz = 1 / (net_gz * ISO_PER_CYCLE) if net_gz * slice_thickness >= 1 else slice_thickness / 200
        n_half = int(np.ceil(SLICE_EXTENT * slice_thickness / self.dz))
        self.z = ((np.arange(-n_half, n_half) + 0.5) * self.dz)[None, :]
        # T2': Lorentzian spread of off-resonance (half-width 1/(2 pi T2')) across each tissue's
        # isochromats, so their sum decays as exp(-t/T2') on top of T2. Quantiles follow a golden
        # ratio sequence, which spreads every frequency band evenly over the spoiler's z cycle.
        r2p = np.array([1 / t.get('T2s', t['T2']) - 1 / t['T2'] for t in tissues])[:, None]  # 1/T2'
        u = (np.arange(self.z.size) * 0.6180339887498949 + 0.5 / self.z.size) % 1.0
        self.df = self.df + r2p / (2 * np.pi) * np.tan(np.pi * (u - 0.5))
        self.mxy = np.zeros((len(tissues), self.z.size), complex)  # PD = 1 here (scaled later)
        self.mz = np.ones((len(tissues), self.z.size))
        self.rf_cache = {}
        print(f'{len(tissues)} tissues x {self.z.size} isochromats through the slice')

    def relax(self, dt):
        self.mxy *= np.exp(-dt / self.T2)
        self.mz = 1 + (self.mz - 1) * np.exp(-dt / self.T1)

    def precess(self, dt, gz_moment):
        if dt > 0:
            self.mxy *= np.exp(-2j * np.pi * (self.df * dt + gz_moment * self.z))
            self.relax(dt)

    def rf_matrix(self, rf, gz_bp):
        """3x3 rotation per (tissue, z) for this pulse with zero phase (cached)."""
        key = (rf.signal.tobytes(), rf.delay, rf.freq_offset, gz_bp[1].tobytes())
        if key not in self.rf_cache:
            t, sig = rf_samples(rf)
            dt = np.diff(t, append=2 * t[-1] - t[-2])
            b1 = 2 * np.pi * sig * np.exp(2j * np.pi * rf.freq_offset * t)  # rad/s
            gz = np.asarray(np.interp(rf.delay + t, *gz_bp, left=0, right=0))
            q = np.zeros((4, self.mz.size))  # Rotation as quaternions (w, x, y, z)
            q[0] = 1
            for k in range(t.size):
                w = 2 * np.pi * (self.z * gz[k] + self.df)  # rad/s, (tissue, z)
                r = -np.stack(np.broadcast_arrays(b1[k].real, b1[k].imag, w)).reshape(3, -1) * dt[k]
                angle = np.linalg.norm(r, axis=0)  # dM/dt = gamma M x B: rotate by -B dt
                step = np.vstack([np.cos(angle / 2), r * 0.5 * np.sinc(angle / (2 * np.pi))])
                q = quaternion_product(step, q)
            R = Rotation.from_quat(np.roll(q, -1, axis=0).T).as_matrix()  # (x, y, z, w)
            self.rf_cache[key] = R.reshape(self.mz.shape + (3, 3))
        return self.rf_cache[key]

    def apply_rf(self, rf, phase, gz_bp):
        R = self.rf_matrix(rf, gz_bp)
        m = self.mxy * np.exp(-1j * phase)  # Pulse with phase p = rotate frame by p.
        M = np.einsum('tzij,tzj->tzi', R, np.stack([m.real, m.imag, self.mz], -1))
        self.mxy = (M[..., 0] + 1j * M[..., 1]) * np.exp(1j * phase)
        self.mz = M[..., 2]

    def run(self, play):
        """Return the z-integrated signal at every ADC sample, shape (tissue, sample)."""
        signal = []
        for n, (b, dummy, rf_phase) in enumerate(play):
            gz = breakpoints(b.gz)
            if b.rf is not None and (b.gx is not None or b.gy is not None):
                raise NotImplementedError('x/y gradients during RF are not supported')
            t_now = 0.0

            def free_to(t):
                nonlocal t_now
                self.precess(t - t_now, moment(gz, t) - moment(gz, t_now))
                t_now = t

            if b.rf is not None:
                t_rf = rf_samples(b.rf)[0]
                free_to(b.rf.delay + t_rf[0])
                self.apply_rf(b.rf, rf_phase, gz)  # Includes gz and off-resonance in the pulse.
                t_end = b.rf.delay + 2 * t_rf[-1] - t_rf[-2]
                self.relax(t_end - t_now)
                t_now = t_end
            if b.adc is not None and not dummy:
                demod = np.exp(-1j * b.adc.phase_offset)
                for t_adc in b.adc.delay + (np.arange(b.adc.num_samples) + 0.5) * b.adc.dwell:
                    free_to(t_adc)
                    signal.append(self.mxy.sum(axis=1) * self.dz * demod)
            free_to(b.block_duration)
            if (n + 1) % 100 == 0 or n + 1 == len(play):
                print(f'\r  block {n + 1}/{len(play)}', end='', flush=True)
        print()
        return np.array(signal, dtype=complex).T

# --------------------------------------------------------------------------
# MAIN
# --------------------------------------------------------------------------
def simulate(seq_params=None, tissues=None, n_dummy=None, plot=True):
    p: dict[str, Any] = dict(SEQ_PARAMS if seq_params is None else seq_params)
    tissues = TISSUES if tissues is None else tissues
    n_dummy = N_DUMMY if n_dummy is None else n_dummy

    # write_gre's docstring says 'pypulseq.Sequence', which PyCharm reads as the folder, not the class.
    # noinspection PyTypeChecker
    seq: Sequence = build_gre(plot=False, write_seq=False, **p)
    X, Y, label = make_phantom(p['fov'], p['n_x'], p['n_y'], tissues)

    # 1. Bloch simulation of each tissue through the sequence.
    sim = BlochSim(list(tissues.values()), p['slice_thickness'],
                   net_moment_per_tr(seq, p['slice_thickness']))
    tissue_signal = sim.run(play_list(seq, n_dummy)) / p['slice_thickness']  # units of PD

    # 2. Spatial encoding with the sequence's own k-space trajectory, then FFT.
    kx, ky = seq.calculate_kspace()[0][:2]
    data = np.zeros(kx.size, complex)
    for i, t in enumerate(tissues.values()):
        sel = label == i
        enc = np.exp(-2j * np.pi * (np.outer(kx, X[sel]) + np.outer(ky, Y[sel]))).sum(axis=1)
        data += t['PD'] * tissue_signal[i] * enc
    kspace = data.reshape(p['n_y'], p['n_x'])
    img = np.fft.fftshift(np.fft.ifft2(np.fft.ifftshift(kspace)))

    if plot:
        plot_results(tissues, label, kspace, img)
    return img, kspace, tissue_signal

def plot_results(tissues, label, kspace, img):
    fig, ax = plt.subplots(1, 5, figsize=(18, 3.8))
    for a, (key, title) in zip(ax[:3], [('PD', 'PD'), ('T1', 'T1 (s)'), ('T2', 'T2 (s)')]):
        im = a.imshow(tissue_map(tissues, label, key), cmap='viridis', origin='lower')
        a.set_title(title)
        fig.colorbar(im, ax=a, shrink=0.8)
    ax[3].imshow(np.log10(np.abs(kspace) + 1e-3), cmap='gray', origin='lower')
    ax[3].set_title('|k-space| (log)')
    im = ax[4].imshow(np.abs(img), cmap='gray', origin='lower')
    fig.colorbar(im, ax=ax[4], shrink=0.8)
    for a in ax:
        a.set_xticks([])
        a.set_yticks([])
    fig.tight_layout()
    plt.show()

if __name__ == '__main__':
    simulate()