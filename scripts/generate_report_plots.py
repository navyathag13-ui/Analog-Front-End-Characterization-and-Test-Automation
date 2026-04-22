"""
generate_report_plots.py
-------------------------
Master script that runs every analysis module and generates all plots
needed for the technical report.  Suitable for use in a CI/automation
pipeline or a single-command "build all" workflow.

Plots generated:
  bode_config1.png            — Bode plot, Config 1
  bode_config2.png            — Bode plot, Config 2
  bode_config3.png            — Bode plot, Config 3
  gain_bandwidth_summary.png  — Bar chart: gain and BW per config
  gbw_product_comparison.png  — GBW consistency verification
  bode_overlay.png            — All configs on one Bode plot
  normalized_gain_overlay.png — Normalized rolloff comparison
  linearity_vout_vs_vin.png   — Linearity check with regression
  anomaly_zscore.png          — Z-score heat map (multi-run)
  bw_vs_expected.png          — Measured vs predicted BW
  noise_density.png           — Input-referred noise density
  transient_waveform.png      — Time-domain waveform, Config 1

Usage:
  python scripts/generate_report_plots.py
"""

import os
import sys
import importlib
import argparse
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR   = os.path.join(SCRIPT_DIR, "..")
DATA_DIR   = os.path.join(ROOT_DIR, "data")
PLOTS_DIR  = os.path.join(ROOT_DIR, "plots")
os.makedirs(PLOTS_DIR, exist_ok=True)

# Add scripts/ to path so we can import sibling modules
sys.path.insert(0, SCRIPT_DIR)


# ─────────────────────────────────────────────────────────────────────────────
# Individual plot generators (inlined here so this file is self-contained)
# ─────────────────────────────────────────────────────────────────────────────

def _load_ac(cfg_num):
    path = os.path.join(DATA_DIR, f"ac_sweep_config{cfg_num}.csv")
    if not os.path.isfile(path):
        sys.exit(f"[ERROR] {path} missing. Run generate_simulation_data.py first.")
    return (pd.read_csv(path, comment="#")
              .sort_values("Frequency_Hz")
              .reset_index(drop=True))


def _midband(df):
    return float(df[df["Frequency_Hz"] <= 10_000]["Gain_dB"].median())


def _bw(df, mid):
    tgt   = mid - 3.0
    gains = df["Gain_dB"].values
    freqs = df["Frequency_Hz"].values
    idx   = np.argmax(gains < tgt)
    if idx == 0:
        return np.nan
    lf = np.interp(tgt, [gains[idx], gains[idx - 1]],
                        [np.log10(freqs[idx]), np.log10(freqs[idx - 1])])
    return 10 ** lf


# ── Noise density ─────────────────────────────────────────────────────────────

def plot_noise_density():
    path = os.path.join(DATA_DIR, "noise_sweep.csv")
    if not os.path.isfile(path):
        print("  [SKIP] noise_sweep.csv not found.")
        return
    df = pd.read_csv(path, comment="#")

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.set_title(
        "Input-Referred Voltage Noise Density — TL071\n"
        "(1/f + White Noise Model, f_corner = 200 Hz)  —  Simulation-Derived",
        fontsize=11, fontweight="bold"
    )
    ax.loglog(df["Frequency_Hz"], df["InputReferred_nV_rtHz"],
              "k-", linewidth=2.5, label="Input-referred noise")
    ax.axvline(200, color="gray", linestyle="--", linewidth=1,
               label="1/f corner ≈ 200 Hz")
    ax.axhline(18,  color="blue", linestyle=":",  linewidth=1,
               label="White noise floor ≈ 18 nV/√Hz")
    ax.set_xlabel("Frequency (Hz)", fontsize=11)
    ax.set_ylabel("Noise Density (nV/√Hz)", fontsize=11)
    ax.set_ylim(10, 300)
    ax.legend(fontsize=9)
    ax.grid(True, which="both", linestyle=":", alpha=0.5)
    plt.tight_layout()
    out = os.path.join(PLOTS_DIR, "noise_density.png")
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Plot saved → {out}")


# ── Transient waveform ────────────────────────────────────────────────────────

def plot_transient():
    path = os.path.join(DATA_DIR, "transient_config1.csv")
    if not os.path.isfile(path):
        print("  [SKIP] transient_config1.csv not found.")
        return
    df = pd.read_csv(path, comment="#")

    # show 2 cycles only
    mask = df["Time_s"] <= 2e-3
    df   = df[mask]
    t_us = df["Time_s"].values * 1e6    # convert to µs for readability

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 6), sharex=True)
    fig.suptitle(
        "Transient Analysis — Config 1 (Gain=10)  @  1 kHz\n"
        "Vin = 100 mV amplitude sine  (Simulation-Derived)",
        fontsize=11, fontweight="bold"
    )
    ax1.plot(t_us, df["Vin_V"].values * 1e3, color="#0057B8",
             linewidth=1.5, label="Vin (mV)")
    ax1.set_ylabel("Vin (mV)", fontsize=11)
    ax1.legend(fontsize=9, loc="upper right")
    ax1.grid(linestyle=":", alpha=0.5)

    ax2.plot(t_us, df["Vout_V"].values, color="#C44B4B",
             linewidth=1.5, label="Vout (V)")
    ax2.set_ylabel("Vout (V)", fontsize=11)
    ax2.set_xlabel("Time (µs)", fontsize=11)
    ax2.legend(fontsize=9, loc="upper right")
    ax2.grid(linestyle=":", alpha=0.5)

    plt.tight_layout()
    out = os.path.join(PLOTS_DIR, "transient_waveform.png")
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Plot saved → {out}")


# ─────────────────────────────────────────────────────────────────────────────
# Master runner
# ─────────────────────────────────────────────────────────────────────────────

def main():
    print("\n=== Master Report Plot Generator ===")
    print(f"    Output directory: {PLOTS_DIR}\n")

    # ── Step 1: Individual Bode plots ─────────────────────────────────────
    from analyze_frequency_response import (
        load_ac_sweep, estimate_midband_gain, estimate_bandwidth, plot_bode
    )
    print("Generating individual Bode plots …")
    for cfg in [1, 2, 3]:
        df  = load_ac_sweep(cfg)
        mid = estimate_midband_gain(df)
        bw  = estimate_bandwidth(df, mid)
        plot_bode(df, cfg, bw, mid)

    # ── Step 2: Gain-BW summary ───────────────────────────────────────────
    print("\nGenerating gain-bandwidth summary charts …")
    from compute_gain_bandwidth import (
        build_results_table, plot_gain_bw_summary, plot_gbw_comparison
    )
    results = build_results_table()
    plot_gain_bw_summary(results)
    plot_gbw_comparison(results)

    # ── Step 3: Configuration comparison ─────────────────────────────────
    print("\nGenerating configuration comparison plots …")
    from compare_configurations import (
        plot_bode_overlay, plot_normalized_gain, plot_linearity
    )
    plot_bode_overlay()
    plot_normalized_gain()
    plot_linearity()

    # ── Step 4: Anomaly detection ─────────────────────────────────────────
    print("\nRunning anomaly detection …")
    from anomaly_detection import (
        build_multi_run_data, detect_zscore_anomalies,
        build_bw_comparison, plot_zscore_heatmap, plot_bw_vs_expected
    )
    df_runs, _, _ = build_multi_run_data()
    z_scores, flagged = detect_zscore_anomalies(df_runs, 2.0)
    plot_zscore_heatmap(z_scores)
    bw_df = build_bw_comparison()
    plot_bw_vs_expected(bw_df)

    # ── Step 5: Noise and transient ───────────────────────────────────────
    print("\nGenerating noise density and transient plots …")
    plot_noise_density()
    plot_transient()

    # ── Summary ───────────────────────────────────────────────────────────
    pngs = [f for f in os.listdir(PLOTS_DIR) if f.endswith(".png")]
    print(f"\n{'='*50}")
    print(f"  {len(pngs)} plots written to {PLOTS_DIR}/")
    for p in sorted(pngs):
        print(f"    {p}")
    print("="*50)
    print("All report plots generated successfully.\n")


if __name__ == "__main__":
    main()
