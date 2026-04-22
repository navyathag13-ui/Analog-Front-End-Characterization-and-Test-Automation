"""
anomaly_detection.py
---------------------
Detects anomalous measurements across test runs using two complementary methods:

  1. Z-score method — flags gain values that deviate more than ±2 σ from
     the mean at each frequency bin across multiple test runs.

  2. Expected-model comparison — compares each run's -3 dB BW against the
     theoretical value predicted from the measured midband gain and the
     known GBW product (3 MHz for TL071).  Deviations > 5% are flagged.

This models a realistic production / bench test scenario where the same
circuit is re-measured multiple times (or across multiple units) and the
automation pipeline screens for outliers before the data goes into the
characterization report.

Outputs:
  - Console summary of flagged anomalies
  - plots/anomaly_zscore.png        (Z-score heat map over freq bins)
  - plots/bw_vs_expected.png        (measured vs predicted BW)

Usage:
  python scripts/anomaly_detection.py
"""

import os
import sys
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

GBW_HZ = 3e6          # TL071 gain-bandwidth product (Hz)
ZSCORE_THRESHOLD = 2.0


# ─────────────────────────────────────────────────────────────────────────────
# Synthetic multi-run dataset
# ─────────────────────────────────────────────────────────────────────────────
# In a real lab, each "run" would be a separate CSV exported from the scope
# or VNA.  Here we synthesise 8 runs for Config 1 (Gain=10, fc=300 kHz),
# injecting two intentional anomalies:
#   Run 4 @ 200 kHz: +2.8 dB spike (e.g., ground loop artefact)
#   Run 7 @ 500 kHz: -3.5 dB drop  (e.g., intermittent connector fault)

def build_multi_run_data():
    freqs = np.array([
        1_000, 5_000, 10_000, 50_000,
        100_000, 150_000, 200_000, 300_000,
        500_000, 700_000, 1_000_000,
    ], dtype=float)

    G0, fc = 10.0, 300_000.0
    rng    = np.random.default_rng(7)
    n_runs = 8

    # ideal gain at each frequency
    ideal = 20.0 * np.log10(G0 / np.sqrt(1.0 + (freqs / fc) ** 2))

    runs = {}
    for run in range(1, n_runs + 1):
        noise = rng.normal(0, 0.04, size=len(freqs))     # ±0.04 dB run-to-run noise
        gains = ideal + noise
        runs[f"Run_{run}"] = gains

    # inject anomalies
    f_idx_200k = np.argmin(np.abs(freqs - 200_000))
    f_idx_500k = np.argmin(np.abs(freqs - 500_000))
    runs["Run_4"][f_idx_200k] += 2.8    # spike
    runs["Run_7"][f_idx_500k] -= 3.5    # drop

    df = pd.DataFrame(runs, index=freqs)
    df.index.name = "Frequency_Hz"
    return df, ideal, freqs


# ─────────────────────────────────────────────────────────────────────────────
# Z-score anomaly detection
# ─────────────────────────────────────────────────────────────────────────────

def detect_zscore_anomalies(df_runs: pd.DataFrame, threshold: float):
    """
    For each frequency bin, compute the Z-score of each run's gain value.
    Z = (x - μ) / σ

    Returns a DataFrame of Z-scores and a list of flagged (freq, run) pairs.
    """
    mean_gain = df_runs.mean(axis=1)
    std_gain  = df_runs.std(axis=1)

    z_scores  = df_runs.subtract(mean_gain, axis=0).divide(std_gain, axis=0)
    flagged   = []

    for run in df_runs.columns:
        for freq, z in z_scores[run].items():
            if abs(z) > threshold:
                flagged.append({
                    "Run":          run,
                    "Frequency_Hz": int(freq),
                    "Z_score":      round(z, 3),
                    "Gain_dB":      round(df_runs.loc[freq, run], 4),
                    "Mean_dB":      round(mean_gain[freq], 4),
                    "Severity":     "HIGH" if abs(z) > 3 else "MEDIUM",
                })
    return z_scores, pd.DataFrame(flagged)


# ─────────────────────────────────────────────────────────────────────────────
# Expected-model BW comparison
# ─────────────────────────────────────────────────────────────────────────────

def bandwidth_from_gain_and_gbw(midband_gain_linear: float, gbw_hz: float) -> float:
    """Predicted BW = GBW / gain  (single-pole approximation)."""
    return gbw_hz / midband_gain_linear


def build_bw_comparison():
    """
    Compare measured (simulated) BW for each config against the value
    predicted from GBW = 3 MHz.
    """
    data = {
        "Config":           ["Config 1", "Config 2", "Config 3"],
        "Nominal_Gain_VpV": [10,          20,          5],
        "Measured_BW_kHz":  [300.2,       150.5,       598.8],   # from compute_gain_bandwidth.py
        "Predicted_BW_kHz": [None,        None,        None],
        "Deviation_pct":    [None,        None,        None],
        "Flag":             [None,        None,        None],
    }
    df = pd.DataFrame(data)

    for i, row in df.iterrows():
        pred = bandwidth_from_gain_and_gbw(row["Nominal_Gain_VpV"], GBW_HZ) / 1e3
        meas = row["Measured_BW_kHz"]
        dev  = abs(meas - pred) / pred * 100
        df.at[i, "Predicted_BW_kHz"] = round(pred, 1)
        df.at[i, "Deviation_pct"]    = round(dev, 2)
        df.at[i, "Flag"]             = "PASS" if dev < 5.0 else "FAIL"

    return df


# ─────────────────────────────────────────────────────────────────────────────
# Plots
# ─────────────────────────────────────────────────────────────────────────────

def plot_zscore_heatmap(z_scores: pd.DataFrame):
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.set_title(
        "Z-Score Anomaly Map — Config 1, 8 Test Runs\n"
        "(|Z| > 2.0 flagged as anomaly)  —  Simulation-Derived",
        fontsize=11, fontweight="bold"
    )

    freq_labels = [f"{int(f/1e3)}k" if f >= 1e3 else str(int(f))
                   for f in z_scores.index]
    run_labels  = list(z_scores.columns)

    im = ax.imshow(
        z_scores.values.T,
        aspect="auto", cmap="RdYlGn_r",
        vmin=-4, vmax=4,
        interpolation="nearest"
    )
    ax.set_xticks(range(len(freq_labels)))
    ax.set_xticklabels(freq_labels, fontsize=9)
    ax.set_yticks(range(len(run_labels)))
    ax.set_yticklabels(run_labels, fontsize=9)
    ax.set_xlabel("Frequency (Hz)", fontsize=10)
    ax.set_ylabel("Test Run", fontsize=10)

    cbar = fig.colorbar(im, ax=ax, orientation="vertical", pad=0.02)
    cbar.set_label("Z-score", fontsize=10)

    # annotate flagged cells
    for r_idx, run in enumerate(run_labels):
        for f_idx, freq in enumerate(z_scores.index):
            z = z_scores.loc[freq, run]
            if abs(z) > ZSCORE_THRESHOLD:
                ax.text(f_idx, r_idx, f"{z:.1f}", ha="center", va="center",
                        fontsize=8, fontweight="bold", color="black")

    plt.tight_layout()
    out = os.path.join(PLOTS_DIR, "anomaly_zscore.png")
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Plot saved → {out}")


def plot_bw_vs_expected(bw_df: pd.DataFrame):
    configs    = bw_df["Config"].values
    measured   = bw_df["Measured_BW_kHz"].values
    predicted  = bw_df["Predicted_BW_kHz"].values
    flags      = bw_df["Flag"].values
    x          = np.arange(len(configs))
    w          = 0.35

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.set_title(
        "Measured vs Predicted -3 dB Bandwidth\n"
        "(Predicted from GBW = 3 MHz)  —  Simulation-Derived",
        fontsize=11, fontweight="bold"
    )

    bars_meas = ax.bar(x - w / 2, measured, w, label="Measured BW",
                       color="#0057B8", edgecolor="black", linewidth=0.8)
    bars_pred = ax.bar(x + w / 2, predicted, w, label="Predicted BW (GBW/Gain)",
                       color="#FFA500", edgecolor="black", linewidth=0.8, alpha=0.85)

    ax.set_xticks(x)
    ax.set_xticklabels(configs, fontsize=11)
    ax.set_ylabel("-3 dB Bandwidth (kHz)", fontsize=11)
    ax.set_ylim(0, max(measured.max(), predicted.max()) * 1.3)
    ax.legend(fontsize=10)
    ax.grid(axis="y", linestyle=":", alpha=0.5)

    for bar, flag in zip(bars_meas, flags):
        color = "green" if flag == "PASS" else "red"
        ax.text(bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 8,
                flag, ha="center", fontsize=10,
                fontweight="bold", color=color)

    plt.tight_layout()
    out = os.path.join(PLOTS_DIR, "bw_vs_expected.png")
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Plot saved → {out}")


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    print("\n=== Anomaly Detection Analysis ===\n")

    # ── Z-score analysis ─────────────────────────────────────────────────────
    print("Building multi-run dataset …")
    df_runs, ideal, freqs = build_multi_run_data()
    z_scores, flagged = detect_zscore_anomalies(df_runs, ZSCORE_THRESHOLD)

    if flagged.empty:
        print("  No anomalies detected (all runs within ±2σ).")
    else:
        print(f"  {len(flagged)} anomaly/anomalies detected:\n")
        print(flagged.to_string(index=False))

    print()
    plot_zscore_heatmap(z_scores)

    # ── BW vs expected ───────────────────────────────────────────────────────
    print("\nComputing BW vs predicted (GBW model) …")
    bw_df = build_bw_comparison()
    print(bw_df.to_string(index=False))
    plot_bw_vs_expected(bw_df)

    fail_count = (bw_df["Flag"] == "FAIL").sum()
    print(f"\n  {len(bw_df) - fail_count}/{len(bw_df)} configurations PASS BW prediction test.")
    print("Done.\n")


if __name__ == "__main__":
    main()
