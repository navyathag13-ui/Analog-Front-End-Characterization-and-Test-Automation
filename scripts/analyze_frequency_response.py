"""
analyze_frequency_response.py
------------------------------
Loads AC sweep CSV data for a single configuration and produces:
  - Bode magnitude plot (gain vs frequency)
  - Bode phase plot (phase vs frequency)
  - Estimated -3 dB bandwidth (printed to console)
  - Estimated midband gain (printed to console)
  - Saved PNG to plots/

Usage:
  python scripts/analyze_frequency_response.py --config 1
  python scripts/analyze_frequency_response.py --config 2
  python scripts/analyze_frequency_response.py --config 3
"""

import argparse
import os
import sys
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")                     # non-interactive backend for scripts
import matplotlib.pyplot as plt
from scipy.interpolate import interp1d

# ── paths ────────────────────────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR   = os.path.join(SCRIPT_DIR, "..")
DATA_DIR   = os.path.join(ROOT_DIR, "data")
PLOTS_DIR  = os.path.join(ROOT_DIR, "plots")
os.makedirs(PLOTS_DIR, exist_ok=True)

CONFIG_META = {
    1: {"R1": "1 kΩ", "R2":  "9 kΩ", "label": "Config 1 — Gain=10 (20 dB), fc≈300 kHz"},
    2: {"R1": "1 kΩ", "R2": "19 kΩ", "label": "Config 2 — Gain=20 (26 dB), fc≈150 kHz"},
    3: {"R1": "1 kΩ", "R2":  "4 kΩ", "label": "Config 3 — Gain=5  (14 dB), fc≈600 kHz"},
}


# ─────────────────────────────────────────────────────────────────────────────
# Data loading
# ─────────────────────────────────────────────────────────────────────────────

def load_ac_sweep(config_num: int) -> pd.DataFrame:
    path = os.path.join(DATA_DIR, f"ac_sweep_config{config_num}.csv")
    if not os.path.isfile(path):
        sys.exit(f"[ERROR] Data file not found: {path}\n"
                 f"        Run  python scripts/generate_simulation_data.py  first.")
    # skip comment lines that start with '#'
    df = pd.read_csv(path, comment="#")
    required = {"Frequency_Hz", "Gain_dB", "Phase_deg"}
    if not required.issubset(df.columns):
        sys.exit(f"[ERROR] Expected columns {required} in {path}. "
                 f"Found: {set(df.columns)}")
    df = df.sort_values("Frequency_Hz").reset_index(drop=True)
    return df


# ─────────────────────────────────────────────────────────────────────────────
# Engineering metrics
# ─────────────────────────────────────────────────────────────────────────────

def estimate_midband_gain(df: pd.DataFrame) -> float:
    """Return the median gain over the flat passband (1 Hz – 10 kHz)."""
    passband = df[df["Frequency_Hz"] <= 10_000]
    return float(passband["Gain_dB"].median())


def estimate_bandwidth(df: pd.DataFrame, midband_gain_dB: float) -> float:
    """
    Interpolate the -3 dB frequency.

    Find the crossover where Gain_dB drops below (midband_gain_dB - 3).
    Uses log-linear interpolation on the sorted frequency array.
    """
    target = midband_gain_dB - 3.0
    gains  = df["Gain_dB"].values
    freqs  = df["Frequency_Hz"].values

    # find the first index where gain drops below target
    idx = np.argmax(gains < target)
    if idx == 0:
        return float("nan")             # target never reached (data too sparse)

    # linear interpolation in log(f) space for accuracy
    f_lo, f_hi = freqs[idx - 1], freqs[idx]
    g_lo, g_hi = gains[idx - 1], gains[idx]
    log_f_interp = np.interp(target, [g_hi, g_lo], [np.log10(f_hi), np.log10(f_lo)])
    return 10 ** log_f_interp


def gain_bandwidth_product(midband_gain_linear: float, bw_hz: float) -> float:
    return midband_gain_linear * bw_hz


# ─────────────────────────────────────────────────────────────────────────────
# Plotting
# ─────────────────────────────────────────────────────────────────────────────

def plot_bode(df: pd.DataFrame, config_num: int, bw_hz: float, midband_dB: float):
    meta  = CONFIG_META[config_num]
    freqs = df["Frequency_Hz"].values
    gains = df["Gain_dB"].values
    phases = df["Phase_deg"].values

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(9, 7), sharex=True)
    fig.suptitle(
        f"Bode Plot — {meta['label']}\n"
        f"TL071 Non-Inverting Amplifier  |  R1={meta['R1']}, R2={meta['R2']}\n"
        "(Simulation-Derived Data)",
        fontsize=11, fontweight="bold"
    )

    # ── Magnitude ────────────────────────────────────────────────────────────
    ax1.semilogx(freqs, gains, color="#0057B8", linewidth=2, label="Simulated gain")
    ax1.axhline(midband_dB - 3, color="red", linestyle="--",
                linewidth=1.2, label=f"-3 dB level ({midband_dB - 3:.1f} dB)")
    ax1.axvline(bw_hz, color="orange", linestyle="--",
                linewidth=1.2, label=f"BW ≈ {bw_hz/1e3:.1f} kHz")
    ax1.set_ylabel("Gain (dB)", fontsize=11)
    ax1.set_ylim(bottom=min(gains) - 3, top=midband_dB + 4)
    ax1.grid(True, which="both", linestyle=":", alpha=0.6)
    ax1.legend(fontsize=9, loc="lower left")
    ax1.annotate(
        f" f₋₃dB ≈ {bw_hz/1e3:.1f} kHz",
        xy=(bw_hz, midband_dB - 3),
        xytext=(bw_hz * 1.5, midband_dB - 5),
        fontsize=9, color="orange",
        arrowprops=dict(arrowstyle="->", color="orange", lw=1),
    )

    # ── Phase ────────────────────────────────────────────────────────────────
    ax2.semilogx(freqs, phases, color="#C44B4B", linewidth=2, label="Phase")
    ax2.axhline(-45, color="orange", linestyle="--",
                linewidth=1.2, label="-45° at f₋₃dB")
    ax2.set_ylabel("Phase (degrees)", fontsize=11)
    ax2.set_xlabel("Frequency (Hz)", fontsize=11)
    ax2.set_ylim(-100, 5)
    ax2.grid(True, which="both", linestyle=":", alpha=0.6)
    ax2.legend(fontsize=9, loc="lower left")

    plt.tight_layout()
    out_path = os.path.join(PLOTS_DIR, f"bode_config{config_num}.png")
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Plot saved → {out_path}")


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Bode plot and bandwidth analysis.")
    parser.add_argument("--config", type=int, choices=[1, 2, 3], default=1,
                        help="Circuit configuration (1, 2, or 3)")
    args = parser.parse_args()

    print(f"\n=== Frequency Response Analysis — Config {args.config} ===")
    df = load_ac_sweep(args.config)

    midband_dB     = estimate_midband_gain(df)
    bw_hz          = estimate_bandwidth(df, midband_dB)
    midband_linear = 10 ** (midband_dB / 20)
    gbw            = gain_bandwidth_product(midband_linear, bw_hz)

    print(f"  Midband gain       : {midband_dB:.3f} dB  ({midband_linear:.2f} V/V)")
    print(f"  -3 dB bandwidth    : {bw_hz/1e3:.2f} kHz")
    print(f"  Gain-bandwidth prod: {gbw/1e6:.3f} MHz")
    print(f"  Data points loaded : {len(df)}")

    plot_bode(df, args.config, bw_hz, midband_dB)
    print("Done.\n")


if __name__ == "__main__":
    main()
