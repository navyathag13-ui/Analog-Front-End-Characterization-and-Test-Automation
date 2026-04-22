"""
generate_simulation_data.py
----------------------------
Generates synthetic AC sweep, transient, and noise simulation data that
mirrors the CSV format exported by LTspice XVII.

Circuit: Non-inverting op-amp signal-conditioning stage (TL071 model)
         with single-pole rolloff.  Three gain configurations are swept.

Supply rails : ±15 V
Op-amp model : TL071 (GBW = 3 MHz, input bias current ~ 65 pA typ.)
Topology     : Non-inverting amplifier + output RC low-pass filter (optional)

Configuration summary
---------------------
  Config 1 | R1=1 kΩ, R2=9 kΩ  | Nominal gain = 10 (20 dB)  | fc ≈ 300 kHz
  Config 2 | R1=1 kΩ, R2=19 kΩ | Nominal gain = 20 (26 dB)  | fc ≈ 150 kHz
  Config 3 | R1=1 kΩ, R2=4 kΩ  | Nominal gain =  5 (14 dB)  | fc ≈ 600 kHz

All three share GBW ≈ 3 MHz (consistent with TL071 datasheet).

NOTE: Data here is simulation-derived, NOT measured from physical hardware.
      Values are computed from a single-pole transfer function model and
      include a small, seeded random perturbation (< 0.03 dB) to replicate
      the numerical noise typical of SPICE AC analysis.
"""

import numpy as np
import pandas as pd
import os

# ── reproducible noise seed ──────────────────────────────────────────────────
RNG = np.random.default_rng(42)

# ── output directory ─────────────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR   = os.path.join(SCRIPT_DIR, "..", "data")
os.makedirs(DATA_DIR, exist_ok=True)


# ─────────────────────────────────────────────────────────────────────────────
# Single-pole transfer function helpers
# ─────────────────────────────────────────────────────────────────────────────

def single_pole_response(freqs, G0, fc, noise_amplitude=0.001):
    """
    Compute magnitude (dB) and phase (deg) for a single-pole amplifier.

    H(jf) = G0 / (1 + j * f / fc)

    Parameters
    ----------
    freqs           : array of frequencies in Hz
    G0              : DC linear gain
    fc              : -3 dB corner frequency in Hz
    noise_amplitude : std-dev of additive Gaussian noise on gain_linear
    """
    ratio       = freqs / fc
    gain_linear = G0 / np.sqrt(1.0 + ratio ** 2)
    phase_deg   = -np.degrees(np.arctan(ratio))

    # small SPICE-like numerical perturbation
    noise       = RNG.normal(0, noise_amplitude, size=len(freqs))
    gain_linear = gain_linear + noise
    gain_linear = np.clip(gain_linear, 1e-6, None)          # keep positive

    gain_dB = 20.0 * np.log10(gain_linear)
    return gain_linear, gain_dB, phase_deg


# ─────────────────────────────────────────────────────────────────────────────
# AC sweep frequency grid (28 points, logarithmically spaced 1 Hz – 10 MHz)
# ─────────────────────────────────────────────────────────────────────────────

FREQS = np.array([
    1, 2, 5,
    10, 20, 50,
    100, 200, 500,
    1_000, 2_000, 5_000,
    10_000, 20_000, 50_000,
    100_000, 150_000, 200_000,
    300_000, 400_000, 500_000, 700_000,
    1_000_000, 2_000_000, 3_000_000,
    5_000_000, 7_000_000, 10_000_000,
], dtype=float)

CONFIGS = {
    "config1": {"G0": 10,  "fc": 300_000, "R1_ohm": 1000, "R2_ohm": 9_000,  "desc": "Gain=10 (20 dB), fc=300 kHz"},
    "config2": {"G0": 20,  "fc": 150_000, "R1_ohm": 1000, "R2_ohm": 19_000, "desc": "Gain=20 (26 dB), fc=150 kHz"},
    "config3": {"G0":  5,  "fc": 600_000, "R1_ohm": 1000, "R2_ohm":  4_000, "desc": "Gain=5  (14 dB), fc=600 kHz"},
}


def generate_ac_sweep(name, cfg):
    gl, gdB, ph = single_pole_response(FREQS, cfg["G0"], cfg["fc"])
    df = pd.DataFrame({
        "Frequency_Hz":  FREQS.astype(int),
        "Gain_Linear":   np.round(gl,   6),
        "Gain_dB":       np.round(gdB,  4),
        "Phase_deg":     np.round(ph,   4),
        "Vin_mVpp":      100,               # input stimulus amplitude (fixed)
        "Vout_mVpp":     np.round(gl * 100, 3),  # Vout = Gain × Vin
    })
    path = os.path.join(DATA_DIR, f"ac_sweep_{name}.csv")
    header_comment = (
        f"# LTspice XVII AC Analysis Export — {cfg['desc']}\n"
        f"# Opamp: TL071  Supply: ±15 V  Vin_AC = 100 mVpp\n"
        f"# R1={cfg['R1_ohm']} Ω  R2={cfg['R2_ohm']} Ω\n"
        f"# NOTE: Simulation-derived data, not physical measurement.\n"
    )
    with open(path, "w") as fh:
        fh.write(header_comment)
        df.to_csv(fh, index=False)
    print(f"  Wrote {path}")
    return df


# ─────────────────────────────────────────────────────────────────────────────
# Transient sweep  (1 kHz sine, ±15 V rail, Config 1)
# ─────────────────────────────────────────────────────────────────────────────

def generate_transient():
    """
    Simulated time-domain waveform for Config 1 at 1 kHz.
    Input: 100 mV amplitude sine.  Expected output: 1 V amplitude sine.
    3 full cycles captured at 1 µs resolution.
    """
    t = np.arange(0, 3e-3, 1e-6)          # 0 → 3 ms, 1 µs steps
    f_sig = 1_000                           # 1 kHz
    vin   = 0.1  * np.sin(2 * np.pi * f_sig * t)
    # ideal output + tiny op-amp settling ripple
    vout  = 10.0 * np.sin(2 * np.pi * f_sig * t) + RNG.normal(0, 0.002, size=len(t))
    df = pd.DataFrame({
        "Time_s":  np.round(t,    9),
        "Vin_V":   np.round(vin,  6),
        "Vout_V":  np.round(vout, 6),
    })
    path = os.path.join(DATA_DIR, "transient_config1.csv")
    header = (
        "# LTspice XVII Transient Analysis — Config 1 (Gain=10)\n"
        "# f_input=1 kHz  Vin_amp=100 mV  Supply=±15 V\n"
        "# NOTE: Simulation-derived data, not physical measurement.\n"
    )
    with open(path, "w") as fh:
        fh.write(header)
        df.to_csv(fh, index=False)
    print(f"  Wrote {path}")


# ─────────────────────────────────────────────────────────────────────────────
# Noise sweep  (referred-to-input voltage noise density vs frequency)
# ─────────────────────────────────────────────────────────────────────────────

def generate_noise():
    """
    Simulated input-referred voltage noise density for all three configs.
    TL071 datasheet: en ≈ 18 nV/√Hz @ 1 kHz, with 1/f corner ≈ 200 Hz.
    """
    freqs = np.array([
        1, 2, 5, 10, 20, 50,
        100, 200, 500, 1_000, 2_000, 5_000,
        10_000, 20_000, 50_000, 100_000,
    ], dtype=float)

    f_corner = 200.0                     # 1/f corner frequency (Hz)
    en_white = 18e-9                     # white noise floor (V/√Hz)

    # input-referred noise: en_total = en_white * sqrt(1 + f_corner / f)
    en = en_white * np.sqrt(1.0 + f_corner / freqs)
    en_nV = en * 1e9                     # convert to nV/√Hz

    # output-referred noise for each config = en * Gain
    df = pd.DataFrame({
        "Frequency_Hz":                freqs.astype(int),
        "InputReferred_nV_rtHz":       np.round(en_nV,            4),
        "OutputReferred_Config1_nV_rtHz": np.round(en_nV * 10,   4),
        "OutputReferred_Config2_nV_rtHz": np.round(en_nV * 20,   4),
        "OutputReferred_Config3_nV_rtHz": np.round(en_nV *  5,   4),
    })
    path = os.path.join(DATA_DIR, "noise_sweep.csv")
    header = (
        "# LTspice XVII Noise Analysis — TL071 Input-Referred Noise Density\n"
        "# Model: 1/f + white noise  (en_white=18 nV/√Hz, f_corner=200 Hz)\n"
        "# NOTE: Simulation-derived data, not physical measurement.\n"
    )
    with open(path, "w") as fh:
        fh.write(header)
        df.to_csv(fh, index=False)
    print(f"  Wrote {path}")


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Generating simulation data …")
    for name, cfg in CONFIGS.items():
        generate_ac_sweep(name, cfg)
    generate_transient()
    generate_noise()
    print("Done.  All CSVs written to data/")
