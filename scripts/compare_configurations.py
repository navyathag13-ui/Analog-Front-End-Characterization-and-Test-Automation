"""
compare_configurations.py
--------------------------
Overlays Bode plots for all three circuit configurations on a single figure,
enabling side-by-side comparison of gain and phase response.

Also produces:
  - Normalized gain plot (all curves shifted to 0 dB at DC) to isolate
    the -3 dB rolloff shape and highlight bandwidth trade-offs.
  - Linearity check: Vout vs Vin at 1 kHz (from transient data) with a
    linear regression and residual to identify gain compression.

Outputs (all saved to plots/):
  - bode_overlay.png
  - normalized_gain_overlay.png
  - linearity_vout_vs_vin.png

Usage:
  python scripts/compare_configurations.py
"""

import os
import sys
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.stats import linregress

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR   = os.path.join(SCRIPT_DIR, "..")
DATA_DIR   = os.path.join(ROOT_DIR, "data")
PLOTS_DIR  = os.path.join(ROOT_DIR, "plots")
os.makedirs(PLOTS_DIR, exist_ok=True)

COLORS = ["#0057B8", "#C44B4B", "#27A645"]
LABELS = [
    "Config 1 — Gain=10 (20 dB), fc≈300 kHz",
    "Config 2 — Gain=20 (26 dB), fc≈150 kHz",
    "Config 3 — Gain=5  (14 dB), fc≈600 kHz",
]


def load_ac(cfg_num):
    path = os.path.join(DATA_DIR, f"ac_sweep_config{cfg_num}.csv")
    if not os.path.isfile(path):
        sys.exit(f"[ERROR] {path} missing. Run generate_simulation_data.py first.")
    return pd.read_csv(path, comment="#").sort_values("Frequency_Hz").reset_index(drop=True)


def midband_gain(df):
    return float(df[df["Frequency_Hz"] <= 10_000]["Gain_dB"].median())


def bw_hz(df, midband):
    target = midband - 3.0
    gains  = df["Gain_dB"].values
    freqs  = df["Frequency_Hz"].values
    idx    = np.argmax(gains < target)
    if idx == 0:
        return np.nan
    log_f = np.interp(target, [gains[idx], gains[idx - 1]],
                               [np.log10(freqs[idx]), np.log10(freqs[idx - 1])])
    return 10 ** log_f


# ─────────────────────────────────────────────────────────────────────────────
# Plot 1: Bode overlay
# ─────────────────────────────────────────────────────────────────────────────

def plot_bode_overlay():
    dfs     = [load_ac(c) for c in [1, 2, 3]]
    midbands = [midband_gain(d) for d in dfs]
    bws      = [bw_hz(d, m) for d, m in zip(dfs, midbands)]

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8), sharex=True)
    fig.suptitle(
        "Bode Plot Overlay — All Configurations\n"
        "TL071 Non-Inverting Amplifier  (Simulation-Derived)",
        fontsize=12, fontweight="bold"
    )

    for i, (df, mid, bw, color, label) in enumerate(
            zip(dfs, midbands, bws, COLORS, LABELS)):
        freqs  = df["Frequency_Hz"].values
        gains  = df["Gain_dB"].values
        phases = df["Phase_deg"].values
        ax1.semilogx(freqs, gains,  color=color, linewidth=2,   label=label)
        ax2.semilogx(freqs, phases, color=color, linewidth=2,   label=label)
        ax1.axvline(bw, color=color, linestyle=":", linewidth=1, alpha=0.7)

    ax1.axhline(0, color="gray", linestyle="-", linewidth=0.5, alpha=0.4)
    ax1.set_ylabel("Gain (dB)", fontsize=11)
    ax1.grid(True, which="both", linestyle=":", alpha=0.55)
    ax1.legend(fontsize=9, loc="lower left")
    ax1.set_title("Gain vs Frequency (dotted verticals = individual -3 dB points)", fontsize=10)

    ax2.axhline(-45, color="gray", linestyle="--", linewidth=1,
                alpha=0.6, label="-45° reference")
    ax2.set_ylabel("Phase (degrees)", fontsize=11)
    ax2.set_xlabel("Frequency (Hz)", fontsize=11)
    ax2.set_ylim(-100, 10)
    ax2.grid(True, which="both", linestyle=":", alpha=0.55)
    ax2.legend(fontsize=9, loc="lower left")

    plt.tight_layout()
    out = os.path.join(PLOTS_DIR, "bode_overlay.png")
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Plot saved → {out}")


# ─────────────────────────────────────────────────────────────────────────────
# Plot 2: Normalized gain (0 dB at DC) — isolates rolloff shape
# ─────────────────────────────────────────────────────────────────────────────

def plot_normalized_gain():
    dfs      = [load_ac(c) for c in [1, 2, 3]]
    midbands = [midband_gain(d) for d in dfs]
    bws      = [bw_hz(d, m) for d, m in zip(dfs, midbands)]

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.set_title(
        "Normalized Gain Rolloff (0 dB at DC)\n"
        "TL071  —  All Configurations  (Simulation-Derived)",
        fontsize=11, fontweight="bold"
    )

    for df, mid, bw, color, label in zip(dfs, midbands, bws, COLORS, LABELS):
        norm = df["Gain_dB"].values - mid
        ax.semilogx(df["Frequency_Hz"].values, norm, color=color,
                    linewidth=2, label=label)
        ax.axvline(bw, color=color, linestyle=":", linewidth=1, alpha=0.7)

    ax.axhline(-3, color="red", linestyle="--", linewidth=1.2, label="-3 dB threshold")
    ax.set_ylabel("Normalized Gain (dB)", fontsize=11)
    ax.set_xlabel("Frequency (Hz)", fontsize=11)
    ax.set_ylim(-30, 3)
    ax.grid(True, which="both", linestyle=":", alpha=0.55)
    ax.legend(fontsize=9, loc="lower left")

    plt.tight_layout()
    out = os.path.join(PLOTS_DIR, "normalized_gain_overlay.png")
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Plot saved → {out}")


# ─────────────────────────────────────────────────────────────────────────────
# Plot 3: Linearity — Vout vs Vin amplitude sweep at 1 kHz
# ─────────────────────────────────────────────────────────────────────────────

def plot_linearity():
    """
    Simulate a Vin amplitude sweep (10 mV – 1300 mV peak) at 1 kHz.
    Config 1 (Gain=10): clipping begins near Vout ≈ ±13 V (rail - headroom).
    """
    rng = np.random.default_rng(99)
    vin_mV  = np.array([10, 20, 50, 100, 200, 300, 400, 500, 600,
                         700, 800, 900, 1000, 1100, 1200, 1300], dtype=float)

    # ideal: Vout = 10 × Vin, clipped at ±13 V (op-amp output swing on ±15 V)
    clip_mV = 13_000.0
    vout_ideal_mV = np.clip(10 * vin_mV, -clip_mV, clip_mV)

    # add small measurement noise
    vout_mV = vout_ideal_mV + rng.normal(0, 15, size=len(vin_mV))

    # linear regression on the linear region only (< 1000 mV in)
    mask    = vin_mV < 1000
    slope, intercept, r, _, _ = linregress(vin_mV[mask], vout_mV[mask])

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 7), sharex=True)
    fig.suptitle(
        "Linearity Check — Config 1 (Gain=10) @ 1 kHz\n"
        "TL071 Non-Inverting Amplifier  (Simulation-Derived)",
        fontsize=11, fontweight="bold"
    )

    # Vout vs Vin
    ax1.plot(vin_mV, vout_mV / 1e3, "o-", color="#0057B8",
             linewidth=2, markersize=6, label="Simulated Vout")
    ax1.plot(vin_mV, (slope * vin_mV + intercept) / 1e3, "--",
             color="orange", linewidth=1.5,
             label=f"Linear fit (R²={r**2:.5f})")
    ax1.axhline( 13, color="red", linestyle=":", linewidth=1, alpha=0.7, label="Output rail ±13 V")
    ax1.axhline(-13, color="red", linestyle=":", linewidth=1, alpha=0.7)
    ax1.set_ylabel("Vout (V)", fontsize=11)
    ax1.legend(fontsize=9)
    ax1.grid(linestyle=":", alpha=0.5)

    # Residual (deviation from ideal gain line)
    residual_mV = vout_mV - (slope * vin_mV + intercept)
    ax2.bar(vin_mV, residual_mV, width=40, color="#C44B4B", alpha=0.7, label="Residual error")
    ax2.axhline(0, color="black", linewidth=0.8)
    ax2.set_ylabel("Residual (mV)", fontsize=11)
    ax2.set_xlabel("Vin amplitude (mV)", fontsize=11)
    ax2.legend(fontsize=9)
    ax2.grid(linestyle=":", alpha=0.5)

    plt.tight_layout()
    out = os.path.join(PLOTS_DIR, "linearity_vout_vs_vin.png")
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Plot saved → {out}")
    print(f"    Linear fit slope (gain): {slope/1e3:.4f} V/mV  "
          f"({slope:.1f} mV/mV)  |  expected: 10.000")
    print(f"    R² = {r**2:.6f}  (1.000 = perfect linearity)")


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    print("\n=== Configuration Comparison and Linearity Analysis ===\n")
    print("Generating Bode overlay …")
    plot_bode_overlay()
    print("Generating normalized gain overlay …")
    plot_normalized_gain()
    print("Generating linearity plot …")
    plot_linearity()
    print("\nDone.\n")


if __name__ == "__main__":
    main()
