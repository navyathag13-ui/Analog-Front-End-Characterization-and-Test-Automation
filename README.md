# Analog Front-End Characterization and Test Automation

**Author:** Navyatha G
**Stack:** LTspice XVII · Python 3.11 · NumPy · pandas · SciPy · Matplotlib

---

## Overview

This project characterizes a **TL071-based non-inverting signal-conditioning amplifier**
across three gain configurations, extracting key analog performance metrics —
gain, -3 dB bandwidth, gain-bandwidth product, linearity, and noise density —
through a fully automated Python analysis pipeline.

The workflow mirrors the scripted characterization approach used in analog
front-end validation and preamp test engineering: simulation data is exported,
parsed, analyzed, and reported without manual intervention.

> **Data note:** All CSV files in `data/` are simulation-derived (single-pole
> transfer function model calibrated to the TL071 datasheet, GBW = 3 MHz).
> The pipeline is designed to accept real oscilloscope / network analyzer exports
> as drop-in replacements with no code changes.

---

## Circuit Under Test

**Topology:** Non-inverting op-amp amplifier
**Op-Amp:** TL071 (JFET input, GBW = 3 MHz, en = 18 nV/√Hz)
**Supply:** ±15 V

```
          ┌────────────────────────────────────┐
          │          TL071 (±15 V)             │
Vin ──────┤ IN+ (+)                  OUT ──────┼──── Vout
          │                          │         │
          │ IN− (−) ◄────┬───────────┘         │
          └──────────────┼─────────────────────┘
                         │
                        R2  ← feedback resistor
                         │
                        R1  ← to GND
                         │
                        GND
```

| Configuration | R1    | R2     | Gain   | Gain (dB) | -3 dB BW |
|---------------|-------|--------|--------|-----------|----------|
| Config 1      | 1 kΩ  | 9 kΩ   | 10 V/V | 20.00 dB  | 300 kHz  |
| Config 2      | 1 kΩ  | 19 kΩ  | 20 V/V | 26.02 dB  | 150 kHz  |
| Config 3      | 1 kΩ  | 4 kΩ   | 5 V/V  | 13.98 dB  | 600 kHz  |

---

## Key Results

| Metric                      | Result                                   |
|-----------------------------|------------------------------------------|
| Gain-bandwidth product       | 3.00 MHz (consistent across all configs) |
| GBW deviation across configs | < 0.7%                                   |
| Linearity (R², Config 1)     | 0.99998 over 13× input range            |
| Output clipping onset        | Vin ≈ 1300 mV → Vout ≈ ±13 V           |
| Input-referred noise floor   | 18 nV/√Hz (white), corner ≈ 200 Hz     |
| Anomalies detected           | 2 injected faults found (Z > ±11σ)     |

---

## Repository Structure

```
Analog-Front-End-Characterization-and-Test-Automation/
│
├── README.md                          ← this file
├── requirements.txt                   ← Python dependencies
├── .gitignore
│
├── data/                              ← simulation-exported CSV files
│   ├── ac_sweep_config1.csv           ← AC sweep, Gain=10
│   ├── ac_sweep_config2.csv           ← AC sweep, Gain=20
│   ├── ac_sweep_config3.csv           ← AC sweep, Gain=5
│   ├── transient_config1.csv          ← time-domain, 1 kHz sine
│   └── noise_sweep.csv                ← input-referred noise density
│
├── scripts/
│   ├── generate_simulation_data.py    ← regenerates all data/ CSVs
│   ├── analyze_frequency_response.py  ← Bode plot + BW for one config
│   ├── compute_gain_bandwidth.py      ← GBW summary, all configs
│   ├── compare_configurations.py      ← overlay, linearity, normalization
│   ├── anomaly_detection.py           ← Z-score + BW model check
│   └── generate_report_plots.py       ← master script: all plots at once
│
├── plots/                             ← generated PNGs (git-ignored)
│   └── (12 plots generated on run)
│
├── simulations/
│   ├── circuit_netlist.txt            ← LTspice netlist (importable)
│   ├── component_values.md            ← component table and tolerances
│   └── simulation_procedure.md        ← step-by-step LTspice guide
│
├── report/
│   ├── technical_report.md            ← full engineering report
│
└── docs/
    ├── circuit_design_notes.md        ← design rationale and derivations
```

---

## Quick Start

### 1. Clone and install

```bash
git clone https://github.com/navyathag13-ui/Analog-Front-End-Characterization-and-Test-Automation.git
cd Analog-Front-End-Characterization-and-Test-Automation
pip install -r requirements.txt
```

### 2. Generate all plots (single command)

```bash
python scripts/generate_report_plots.py
```

This produces 12 plots in `plots/` and prints a full console summary.

### 3. Analyze a specific configuration

```bash
python scripts/analyze_frequency_response.py --config 1   # Bode, Config 1
python scripts/analyze_frequency_response.py --config 2   # Bode, Config 2
python scripts/analyze_frequency_response.py --config 3   # Bode, Config 3
```

### 4. Run gain-bandwidth comparison

```bash
python scripts/compute_gain_bandwidth.py
```

### 5. Detect anomalies

```bash
python scripts/anomaly_detection.py
```

### 6. Regenerate data from scratch

```bash
python scripts/generate_simulation_data.py
```

---

## Plots Generated

| File                          | Description                                     |
|-------------------------------|-------------------------------------------------|
| `bode_config1/2/3.png`        | Individual Bode plots with -3 dB annotations    |
| `gain_bandwidth_summary.png`  | Bar chart: gain and BW per configuration        |
| `gbw_product_comparison.png`  | GBW consistency vs datasheet value              |
| `bode_overlay.png`            | All three configs on one Bode plot              |
| `normalized_gain_overlay.png` | Normalized rolloff comparison                   |
| `linearity_vout_vs_vin.png`   | Linearity check with regression + residuals     |
| `anomaly_zscore.png`          | Z-score heat map (8 test runs)                  |
| `bw_vs_expected.png`          | Measured vs GBW-predicted bandwidth             |
| `noise_density.png`           | Input-referred noise density (1/f + white)      |
| `transient_waveform.png`      | Time-domain waveform, Vin and Vout              |

---

## Extending to Real Hardware

The pipeline accepts any CSV that contains these columns:

```
Frequency_Hz, Gain_dB, Phase_deg
```

Export from your instrument, name the file `ac_sweep_configN.csv`,
drop it into `data/`, and run the scripts. No code changes needed.

Tested-compatible export formats:
- LTspice XVII (File → Export)
- Analog Discovery 2 / WaveForms Network Analyzer
- Keysight E5061B VNA (CSV export mode)
- Manual oscilloscope gain measurements in a spreadsheet

---

## Technologies Used

| Tool        | Purpose                                          |
|-------------|--------------------------------------------------|
| LTspice XVII | SPICE simulation (netlists in `simulations/`)   |
| Python 3.11 | Analysis, automation, plotting                  |
| NumPy       | Numerical computation (gain, BW, interpolation) |
| pandas      | CSV I/O, tabular result aggregation             |
| SciPy       | Linear regression (linearity analysis)          |
| Matplotlib  | Engineering plots and Bode diagrams             |
| Git/GitHub  | Version control and portfolio hosting           |

---

## License

This project is released for educational and portfolio purposes.
Circuit models reference the Texas Instruments TL071 datasheet (SLOS082).
