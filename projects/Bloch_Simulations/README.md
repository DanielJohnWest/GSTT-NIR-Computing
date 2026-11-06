# Bloch simulations of GRE and TSE sequences

Teaching tool for MRI contrast: Bloch simulations of PyPulseq gradient-echo (GRE) and
turbo spin-echo (TSE) sequences on a digital T1MES phantom (1.5 T version).

| File | What it is |
|---|---|
| `simulate_gre.py` | Simulation of the spoiled GRE sequence in `write_gre.py` |
| `simulate_tse.py` | Simulation of the TSE (CPMG) sequence in `write_tse.py` |
| `write_gre.py`, `write_tse.py` | Unmodified copies of PyPulseq's example sequences (see below) |
| `LICENSE-pypulseq` | PyPulseq's MIT licence, which covers the two copied files |

## Requirements

Python 3.10 or later, then, from this folder:

```bash
pip install -r requirements.txt
```

You do not need the PyPulseq repository. `write_gre.py` and `write_tse.py` are copied
unchanged from PyPulseq's `examples/scripts` (GitHub commit a8cb2a8, 29 Oct 2026, MIT
licence in `LICENSE-pypulseq`); they are not part of the pip package. Both simulations were
checked to give identical results with the PyPI release pypulseq 1.5.0.post1.

## Running

Run either script from this folder (or in PyCharm):

```bash
python simulate_gre.py
python simulate_tse.py
```

Sequence parameters (`SEQ_PARAMS`), dummy scans (`N_DUMMY`) and the phantom (`TISSUES`)
are set at the top of each script. You can also call `simulate(seq_params, tissues, n_dummy)`
from your own code. Each run plots the PD, T1 and T2 maps, k-space and the image, and
returns the image, k-space and the simulated signal of each tissue.

Typical run times at 64 x 64: about 20 s for GRE and 60 s for TSE.

### Contrast examples

- **GRE:** T1 weighting through flip angle and TR, T2* weighting through TE. Set
  `N_DUMMY` to a few hundred at higher flip angles to reach steady state before acquisition.
- **TSE:** `n_echo=1` gives a conventional spin echo. Short TR and short TE give T1
  weighting, long TR and short TE PD weighting, long TR and long (effective) TE T2
  weighting. The effective TE is printed after each run.

## What is modelled

- Every RF pulse is integrated on its raster together with the slice-select gradient, so
  the real slice profile is included. RF phase cycling, spoilers and crushers act exactly as
  in the sequence.
- T1, T2 and T2* relaxation. T2* is T2 plus a reversible part (T2'), modelled as a
  Lorentzian spread of off-resonance, so gradient echoes decay with T2* and spin echoes
  refocus to T2.
- To keep it fast, each tissue is simulated once through the slice and the spatial encoding
  is applied afterwards. This is exact for spoiled GRE and for CPMG echo trains; both scripts
  warn if a modified sequence breaks the conditions. Against a pixel-by-pixel simulation the
  TSE image error was below 1%.
- Not modelled: B1 errors, diffusion, flow and noise. Relaxation during an RF pulse is
  applied after it. One slice is simulated.

## Phantom

T1MES phantom, 1.5 T version (Captur et al., J Cardiovasc Magn Reson 2016;18:58): nine
tubes in a gel matrix. Tube T1 and T2 are the published 1.5 T reference values. The
geometry (bottle, tube size and spacing) and the T2* values were measured on our own
1.5 T scanner; proton density is not published and is set to 1. Details are in the
comments above `TISSUES` in each script.
