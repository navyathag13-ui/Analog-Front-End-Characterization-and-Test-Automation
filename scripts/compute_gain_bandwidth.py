"""
compute_gain_bandwidth.py
--------------------------
Extracts and tabulates key performance metrics across all three circuit
configurations:
  - Midband gain (dB and V/V)
  - -3 dB bandwidth
  - Gain-bandwidth product
  - Phase margin (estimated from phase at BW)
  - Peak gain deviation (max ripple in passband)

Outputs:
  - Console summary table
  - plots/gain_bandwidth_summary.png  (bar chart comparison)
  - plots/gbw_product_comparison.png

Usage:
  python scripts/compute_gain_bandwidth.py
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

CONFIG_LABELS = {
    1: "Config 1\nGain=10\nfc≈300 kHz",
    2: "Config 2\nGain=20\nfc≈150 kHz",
    3: "Config 3\nGain=5\nfc≈600 kHz",
}
CONFIG_COLORS = ["#0057B8", "#C44B4B", "#27A645"]


# ─────────────────────────────────────────────────────────────────────────────
# Metric extraction (shared logic with analyze_frequency_response.py)
# ─────────────────────────────────────────────────────────────────────────────

def load_df(cfg_num):
    path = os.path.join(DATA_DIR, f"ac_sweep_config{cfg_num}.csv")
    if not os.path.isfile(path):
        sys.exit(f"[ERROR] {path} not found. Run generate_simulation_data.py first.")
    return pd.read_csv(path, comment="#").sort_values("Frequency_Hz").reset_index(drop=True)


def midband_gain_dB(df):
    return float(df[df["Frequency_Hz"] <= 10_000]["Gain_dB"].median())


def bandwidth_hz(df, midband):
    target = midband - 3.0
    gains  = df["Gain_dB"].values
    freqs  = df["Frequency_Hz"].values
    idx    = np.argmax(gains < target)
    if idx == 0:
        return np.nan
    f_lo, f_hi = freqs[idx - 1], freqs[idx]
    g_lo, g_hi = gains[idx - 1], gains[idx]
    log_f = np.interp(target, [g_hi, g_lo], [np.log10(f_hi), np.log10(f_lo)])
    return 10 ** log_f


def phase_at_bw(df, bw):
    """Interpolate phase at the -3 dB frequency."""
    freqs  = df["Frequency_Hz"].values
    phases = df["Phase_deg"].values
    if bw < freqs[0] or bw > freqs[-1]:
        return np.nan
    return float(np.interp(np.log10(bw), np.log10(freqs), phases))


def passband_ripple_dB(df, midband):
    """Max absolute deviation from midband gain in the range 1 Hz – 10 kHz."""
    pb = df[df["Frequency_Hz"] <= 10_000]["Gain_dB"]
    return float((pb - midband).abs().max())


# ─────────────────────────────────────────────────────────────────────────────
# Collect results
# ─────────────────────────────────────────────────────────────────────────────

def build_results_table():
    rows = []
    for cfg in [1, 2, 3]:
        df   = load_df(cfg)
        mid  = midband_gain_dB(df)
        bw   = bandwidth_hz(df, mid)
        lin  = 10 ** (mid / 20)
        gbw  = lin * bw
        ph   = phase_at_bw(df, bw)
        ripl = passband_ripple_dB(df, mid)
        rows.append({
            "Config":             f"Config {cfg}",
            "Midband_Gain_dB":    round(mid, 3),
            "Midband_Gain_VpV":   round(lin, 2),
            "BW_kHz":             round(bw / 1e3, 2),
            "GBW_MHz":            round(gbw / 1e6, 3),
            "Phase_at_BW_deg":    round(ph, 2),
            "Passband_Ripple_dB": round(ripl, 4),
        })
    return pd.DataFrame(rows)


# ─────────────────────────────────────────────────────────────────────────────
# Plots
# ─────────────────────────────────────────────────────────────────────────────

def plot_gain_bw_summary(results: pd.DataFrame):
    configs = [f"Config {i}" for i in [1, 2, 3]]
    gains   = results["Midband_Gain_dB"].values
    bws     = results["BW_kHz"].values

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 5))
    fig.suptitle(
        "Gain & Bandwidth Comparison — All Configurations\n"
        "TL071 Non-Inverting Amplifier  (Simulation-Derived)",
        fontsize=11, fontweight="bold"
    )

    # Gain bar chart
    bars1 = ax1.bar(configs, gains, color=CONFIG_COLORS, edgecolor="black", linewidth=0.8)
    ax1.set_ylabel("Midband Gain (dB)", fontsize=11)
    ax1.set_title("Midband Gain per Configuration", fontsize=10)
    ax1.set_ylim(0, max(gains) * 1.25)
    ax1.grid(axis="y", linestyle=":", alpha=0.5)
    for bar, val in zip(bars1, gains):
        ax1.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.3,
                 f"{val:.1f} dB", ha="center", va="bottom", fontsize=10, fontweight="bold")

    # Bandwidth bar chart
    bars2 = ax2.bar(configs, bws, color=CONFIG_COLORS, edgecolor="black", linewidth=0.8)
    ax2.set_ylabel("-3 dB Bandwidth (kHz)", fontsize=11)
    ax2.set_title("-3 dB Bandwidth per Configuration", fontsize=10)
    ax2.set_ylim(0, max(bws) * 1.30)
    ax2.grid(axis="y", linestyle=":", alpha=0.5)
    for bar, val in zip(bars2, bws):
        ax2.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 5,
                 f"{val:.0f} kHz", ha="center", va="bottom", fontsize=10, fontweight="bold")

    plt.tight_layout()
    out = os.path.join(PLOTS_DIR, "gain_bandwidth_summary.png")
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Plot saved → {out}")


def plot_gbw_comparison(results: pd.DataFrame):
    configs = [f"Config {i}" for i in [1, 2, 3]]
    gbws    = results["GBW_MHz"].values

    fig, ax = plt.subplots(figsize=(7, 5))
    ax.set_title(
        "Gain-Bandwidth Product Consistency\n"
        "TL071 Non-Inverting Amplifier  (Simulation-Derived)",
        fontsize=11, fontweight="bold"
    )
    bars = ax.bar(configs, gbws, color=CONFIG_COLORS, edgecolor="black", linewidth=0.8)
    ax.axhline(3.0, color="red", linestyle="--", linewidth=1.5,
               label="TL071 datasheet GBW = 3 MHz")
    ax.set_ylabel("GBW Product (MHz)", fontsize=11)
    ax.set_ylim(0, 4.0)
    ax.legend(fontsize=10)
    ax.grid(axis="y", linestyle=":", alpha=0.5)
    for bar, val in zip(bars, gbws):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.05,
                f"{val:.2f} MHz", ha="center", va="bottom", fontsize=11, fontweight="bold")

    plt.tight_layout()
    out = os.path.join(PLOTS_DIR, "gbw_product_comparison.png")
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Plot saved → {out}")


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    print("\n=== Gain-Bandwidth Product Analysis — All Configurations ===\n")
    results = build_results_table()

    # pretty-print table
    pd.set_option("display.max_columns", None)
    pd.set_option("display.width", 120)
    print(results.to_string(index=False))
    print()

    plot_gain_bw_summary(results)
    plot_gbw_comparison(results)

    # verify GBW consistency
    gbws = results["GBW_MHz"].values
    spread = gbws.max() - gbws.min()
    print(f"\n  GBW spread across configs: {spread:.3f} MHz  ", end="")
    print("(< 0.1 MHz → consistent with single op-amp model)" if spread < 0.1
          else "(> 0.1 MHz → investigate component tolerances)")
    print("Done.\n")


if __name__ == "__main__":
    main()
