# Bloch simulations of GRE and TSE sequences

Bloch simulations of PyPulseq gradient-echo (GRE) and
turbo spin-echo (TSE) sequences on a digital T1MES phantom (1.5 T version), alongside
textbook analytical solutions for the same sequences and phantom, and optimisers that find
the sequence parameters giving the most contrast between two tissues.

| File | What it is |
|---|---|
| `simulate_gre.py` | Simulation of the spoiled GRE sequence in `write_gre.py` |
| `simulate_tse.py` | Simulation of the TSE (CPMG) sequence in `write_tse.py` |
| `analytical_gre.py` | Analytical steady-state GRE signal of each tissue (Ernst equation) |
| `analytical_tse.py` | Analytical steady-state TSE echo train of each tissue (ideal CPMG) |
| `optimise_gre.py` | GRE flip angle, TR and TE for the most contrast between two tissues |
| `optimise_tse.py` | TSE echo train length, echo spacing and TR for the most contrast between two tissues |
| `write_gre.py`, `write_tse.py` | PyPulseq's example sequences, slightly modified (see below) |
| `LICENSE-pypulseq` | PyPulseq's MIT licence, which covers the two PyPulseq-derived files |

## Requirements

Python 3.10 or later, then, from this folder:

```bash
pip install -r requirements.txt
```

You do not need the PyPulseq repository. `write_gre.py` and `write_tse.py` come from
PyPulseq's `examples/scripts` (GitHub commit a8cb2a8, 29 Oct 2026, MIT licence in
`LICENSE-pypulseq`); they are not part of the pip package. They have been changed as follows:

- Both take an `n_dummy` argument: the number of dummy TRs (same RF and gradients, no phase
  encoding, no ADC) played before acquisition, so the magnetisation is in steady state. The
  defaults reproduce PyPulseq's sequences exactly: 0 for GRE, and 1 for TSE (PyPulseq's TSE
  example already plays one dummy excitation).
- `write_tse.py`: the RF and ADC dead times, RF ringdown time and gradient raster time are
  plain variables (same values) rather than read back from the system settings.
- `write_gre.py`: when run, it writes a `.seq` file for each `main(...)` call at the bottom of
  the script (the standard sequence and any others added there).

All scripts were checked with the PyPI release pypulseq 1.5.0.post1.

## Running

Run any of the scripts from this folder (or in PyCharm):

```bash
python simulate_gre.py
python simulate_tse.py
python analytical_gre.py
python analytical_tse.py
python optimise_gre.py
python optimise_tse.py
```

Sequence parameters (`SEQ_PARAMS`) and the phantom (`TISSUES`) are set at the top of each
simulation script; the analytical and optimisation scripts use the same ones. You can also
call `simulate(seq_params, tissues, n_dummy)` from your own code. Each simulation run plots
the PD, T1 and T2 maps, k-space and the image, and returns the image, k-space and the
simulated signal of each tissue.

Dummy scans can be set in two ways. Use one or the other, not both:

- `n_dummy` in `SEQ_PARAMS`: passed to `write_gre`/`write_tse`, so the dummies are part of the
  sequence and of any `.seq` file written. This is the one to use for a sequence you will run.
- `N_DUMMY` in the simulation scripts: extra dummy TRs in the simulation only, a quick way
  to try different numbers without changing the sequence.

Typical run times at 64 x 64: about 20 s for the GRE simulation and 60 s for TSE; about
1 min for each optimiser with its Bloch check, and a few seconds without it. The analytical
scripts are instant.

### Contrast Examples

- **GRE:** T1 weighting through flip angle and TR, T2* weighting through TE. Short-TR
  settings need a few hundred dummy TRs to reach steady state before acquisition;
  `optimise_gre.py` reports how many.
- **TSE:** `n_echo=1` gives a conventional spin echo. Short TR and short TE give T1
  weighting, long TR and short TE PD weighting, long TR and long (effective) TE T2
  weighting. The effective TE is printed after each run.

## Optimising Contrast

`optimise_gre.py` and `optimise_tse.py` find the sequence parameters that give the most
contrast between two tissues (`TISSUE_A`, `TISSUE_B`; a tube letter is enough), in three steps:

1. **Limits.** The shortest TE, echo spacing and TR the sequence can play are found by
   building it with `write_gre`/`write_tse`; upper limits are set at the top of each script
   (GRE: flip angle up to 90 degrees, TE up to 20 ms, TR up to 1 s; TSE: echo train length
   from `ECHO_TRAINS`, each dividing `n_y`, echo spacing up to 30 ms, TR up to 4 s). The
   refocusing flip angle is fixed at 180 degrees.
2. **Search.** The steady-state signals come from the analytical models (Ernst equation for
   GRE; ideal CPMG at the effective echo, n_echo/2, for TSE), which are fast enough to
   evaluate on a fine grid. `METRIC` sets what is maximised:
   - `'contrast'`: S_a - S_b (signed), so tissue A is made as much brighter than tissue B as
     possible; swapping the two gives the reverse contrast.
   - `'efficiency'`: |S_a - S_b| per square root of time (sqrt(TR) for GRE, sqrt(TR / n_echo)
     for TSE, i.e. per k-space line), the contrast for a fixed scan time. This is the more
     useful measure for a real protocol. It ignores the dummy period, which matters for
     short-TR GRE settings but hardly at all for TSE.
3. **Bloch Check** (`BLOCH_CHECK = True`). The full simulation plays the sequence from full
   relaxation to well past steady state, and reports the steady-state contrast of the real
   sequence (with the slice profile, RF spoiling and stimulated echoes that the analytical
   models ignore), the contrast with no dummies, and the number of dummy TRs needed for the
   first acquired line to be within 1% of steady state.

Each run prints the `main(...)` call to paste into `write_gre.py`/`write_tse.py` to write the
optimised sequence, and plots a contrast map (red: tissue A brighter, blue: tissue B
brighter, dashed line where they swap) and the approach to steady state. To simulate the
optimised sequence, put the same values, including `n_dummy`, in `SEQ_PARAMS`.

## What is Modelled?

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

## Analytical Solutions

`analytical_gre.py` and `analytical_tse.py` use the same `SEQ_PARAMS` and `TISSUES` as the
simulations and give the textbook steady-state signals, in units of PD:

- **GRE:** the Ernst equation, S = PD sin(a) (1 - E1) / (1 - cos(a) E1) exp(-TE/T2*), with
  E1 = exp(-TR/T1). One value per tissue.
- **TSE:** an ideal CPMG train. The 90 degree pulse saturates Mz, each instantaneous 180
  degree pulse inverts it, and T1 recovery runs in between and until the next TR; echo n is
  that steady-state Mz times exp(-n ESP/T2). One value per echo per tissue. With
  `n_echo=1` this is the classic spin-echo formula.

Both print a table and plot the nine tubes, and `steady_state()` returns the values. They
assume a single isochromat, instantaneous pulses with the nominal flip angles (no slice
profile), perfect spoiling and steady state, which the simulations do not.

## Phantom

T1MES phantom, 1.5 T version (Captur et al., J Cardiovasc Magn Reson 2016;18:58): nine
tubes in a gel matrix. Tube T1 and T2 are the published 1.5 T reference values. The
geometry (bottle, tube size and spacing) and the T2* values were measured on our own
1.5 T scanner; proton density is not published and is set to 1. Details are in the
comments above `TISSUES` in each script.
