# Technical Report
## Analog Front-End Characterization and Test Automation

**Author:** Navyatha G
**Date:** April 2025
**Tool chain:** LTspice XVII (simulation) · Python 3.11 · NumPy · pandas · SciPy · Matplotlib

---

## 1. Objective

This project characterizes the frequency response, gain-bandwidth product,
linearity, noise behavior, and run-to-run measurement consistency of a
TL071-based non-inverting signal-conditioning amplifier across three gain
configurations. A Python automation pipeline processes simulation-exported
CSV data, extracts engineering metrics, detects anomalies, and generates
publication-quality plots — mirroring the scripted characterization workflow
used in analog front-end validation roles.

All data in this report is simulation-derived from a single-pole transfer
function model calibrated to the TL071 datasheet (GBW = 3 MHz, TI SLOS082).
Data is **not** from physical hardware; labels reflecting this are included
throughout.

---

## 2. Circuit Design

### 2.1 Topology Selection

A **non-inverting op-amp amplifier** was selected as the circuit under test
(CUT) because:

- It represents the standard first stage in analog signal-conditioning chains
  (preamps, sensor interfaces, ADC drivers)
- The gain is set by a simple resistor ratio, enabling rapid multi-configuration
  testing by changing a single component
- The TL071's JFET input stage gives low bias current and moderate noise, typical
  of real preamp designs
- The single-pole rolloff is analytically tractable, enabling closed-form
  verification of Python-extracted metrics

### 2.2 Schematic Description

```
          ┌─────────────────────────────────────┐
          │           TL071 (±15 V)             │
Vin ──────┤ IN+ (+)                   OUT ──────┤──── VOUT
          │                           │         │
          │ IN- (−) ◄─────┬───────────┘         │
          │               │                     │
          └───────────────┼─────────────────────┘
                          │
                         R2 (feedback)
                          │
                         R1 (to GND)
                          │
                         GND
```

**Gain formula:**

```
Gain = 1 + R2 / R1
```

### 2.3 Component Values

| Configuration | R1    | R2     | Gain (V/V) | Gain (dB) | Predicted -3 dB BW |
|---------------|-------|--------|------------|-----------|-------------------|
| Config 1      | 1 kΩ  | 9 kΩ   | 10         | 20.00 dB  | 300 kHz           |
| Config 2      | 1 kΩ  | 19 kΩ  | 20         | 26.02 dB  | 150 kHz           |
| Config 3      | 1 kΩ  | 4 kΩ   | 5          | 13.98 dB  | 600 kHz           |

All configurations share **GBW = 3 MHz**, consistent with the TL071 datasheet.

---

## 3. Test Plan

| Test              | Analysis Type | Stimulus             | Metric Extracted                    |
|-------------------|---------------|----------------------|-------------------------------------|
| AC sweep          | .ac dec 100   | 100 mV AC, 1–10 MHz  | Gain, phase, -3 dB BW, GBW product  |
| Transient capture | .tran         | 100 mV sine @ 1 kHz  | Waveform shape, settling            |
| Noise analysis    | .noise        | Input-referred        | Noise density vs frequency          |
| Linearity sweep   | Vin amplitude | 10–1300 mV (1 kHz)   | Gain linearity, clipping threshold  |
| Multi-run anomaly | 8 AC runs     | 100 mV AC, Config 1  | Z-score outliers, BW consistency    |

---

## 4. Results

### 4.1 Frequency Response

AC sweep data was processed by `analyze_frequency_response.py` using
interpolated -3 dB crossover detection in log-frequency space.

| Config | Midband Gain | -3 dB Bandwidth | GBW Product |
|--------|-------------|-----------------|-------------|
| 1      | 20.00 dB    | 300.2 kHz       | 3.002 MHz   |
| 2      | 26.02 dB    | 150.5 kHz       | 3.010 MHz   |
| 3      | 13.98 dB    | 598.8 kHz       | 2.994 MHz   |

**Observation:** GBW spread across all three configurations is < 0.02 MHz
(< 0.7%), confirming the single-pole model is internally consistent.
Phase at the -3 dB point is approximately -45° in all cases, as expected
for a single-pole system.

Plots: `plots/bode_config1.png`, `plots/bode_config2.png`, `plots/bode_config3.png`

### 4.2 Gain-Bandwidth Tradeoff

The overlay in `plots/normalized_gain_overlay.png` shows all three rolloff
curves superimposed after normalization to 0 dB at DC. The curves coincide,
confirming the gain-bandwidth tradeoff: doubling the gain halves the bandwidth.

Config 2 (highest gain) exhibits the narrowest bandwidth, which would
restrict its use in wideband signal paths. Config 3 (lowest gain, widest BW)
is appropriate when bandwidth preservation is more important than amplification.

### 4.3 Linearity

A Vin amplitude sweep from 10 mV to 1300 mV (peak) at 1 kHz was performed
for Config 1 (Gain = 10). Linear regression over the pre-clipping region
(Vin < 1000 mV) yields:

| Metric              | Value     |
|---------------------|-----------|
| Fitted gain slope   | 10.00 V/V |
| R² (linear region)  | 0.99998   |
| Output clip onset   | ~1300 mV in → ~13 V out |

The R² value confirms excellent linearity across a 13× input range.
Clipping begins near Vout = ±13 V, consistent with the TL071's rated output
swing of ±13.5 V on ±15 V rails.

Plot: `plots/linearity_vout_vs_vin.png`

### 4.4 Noise Analysis

Input-referred voltage noise density follows a 1/f + white noise model:

```
en(f) = en_white × sqrt(1 + f_corner / f)
```

| Parameter         | Value           | Source              |
|-------------------|-----------------|---------------------|
| White noise floor | 18 nV/√Hz       | TL071 datasheet     |
| 1/f corner        | ~200 Hz         | TL071 datasheet     |
| en @ 100 Hz       | ~39 nV/√Hz      | Simulation          |
| en @ 1 kHz        | ~18.9 nV/√Hz    | Simulation          |
| en @ 10 kHz       | ~18.0 nV/√Hz    | Simulation          |

At Config 1 gain (×10), the output-referred noise floor is
≈ 180 nV/√Hz in the white-noise region.

Plot: `plots/noise_density.png`

### 4.5 Anomaly Detection

Eight simulated test runs of Config 1's AC sweep were generated, with two
intentional anomalies injected:

| Anomaly          | Location          | Z-score | Cause (simulated)       |
|------------------|-------------------|---------|-------------------------|
| Run 4, 200 kHz   | +2.8 dB spike     | +11.3   | Ground loop artefact    |
| Run 7, 500 kHz   | –3.5 dB drop      | –14.0   | Intermittent connector  |

The Z-score detector (threshold = ±2σ) successfully flagged both anomalies
with high confidence. All other data points remained within ±0.1 dB.

The BW vs GBW model check confirmed that all three configurations pass
the 5% tolerance test (worst deviation: 0.2%).

Plots: `plots/anomaly_zscore.png`, `plots/bw_vs_expected.png`

---

## 5. Conclusions

1. The TL071 non-inverting amplifier delivers accurate, predictable gain
   across three configurations, with GBW consistent to < 0.7%.

2. Bandwidth scales inversely with gain, following the single-pole GBW
   relationship. Config 3 (Gain=5) provides the widest bandwidth at 600 kHz.

3. Linearity is excellent (R² > 0.9999) within the ±13 V output swing.
   Applications requiring headroom should limit Vin < 1 V on Config 1.

4. The 1/f noise corner at ~200 Hz means this amplifier is unsuitable for
   DC or very low-frequency precision measurements without chopper stabilization.

5. The Python anomaly detection pipeline reliably identifies both gain spikes
   and gain drops with Z-scores far above the ±2σ threshold.

---

## 6. Assumptions and Limitations

- All data is simulation-derived. Real hardware measurements would include
  additional sources of error: resistor tolerance, PCB parasitics, power
  supply noise, and thermal drift.
- The single-pole model assumes a dominant pole; TL071 exhibits secondary
  poles well above 3 MHz that could affect phase margin in unity-gain circuits.
- Noise model uses datasheet typical values; actual 1/f behavior varies
  part-to-part and with temperature.
- Output RC filter is designed but not included in the AC sweep (commented out
  in the netlist) to isolate the op-amp transfer function.

---

## 7. Future Work

- [ ] Validate against real hardware using Analog Discovery 2 or Digilent scope
- [ ] Add Monte Carlo component tolerance analysis (LTspice `.mc` command)
- [ ] Extend linearity test to include harmonic distortion (FFT of transient)
- [ ] Automate report generation via `jinja2` HTML or LaTeX template
- [ ] Add temperature sweep (-40°C to +85°C) for industrial design targets

---

*End of report. All plots generated by running `python scripts/generate_report_plots.py`.*
