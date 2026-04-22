# LTspice Simulation Procedure

## Software
**LTspice XVII** (free download from Analog Devices)
- Windows / macOS (via Wine or native ADI version)

---

## Step 1 — Create the Schematic

1. Open LTspice → **File → New Schematic**
2. Place the TL071 op-amp symbol: press `P`, search `TL071`
3. Wire the non-inverting topology using the pin assignments in `circuit_netlist.txt`
4. Add:
   - `VCC` and `VEE` voltage sources (±15 V DC)
   - `Vin` voltage source (AC = 0.1, SINE for transient)
   - `R1 = 1 kΩ`, `R2 = 9 kΩ` (Config 1 default)
   - `RLOAD = 10 kΩ`
5. Label the output node `VOUT`

> **Shortcut:** Instead of drawing the schematic, paste the contents of
> `circuit_netlist.txt` into a new `.net` file and run it directly via
> **File → Open → (select .net file)**.

---

## Step 2 — AC Sweep (Frequency Response)

1. Click **Simulate → Edit Simulation Command**
2. Select the **AC Analysis** tab
3. Settings:
   - Type: **Decade**
   - Points/decade: `100`
   - Start frequency: `1`
   - Stop frequency: `10Meg`
4. Click OK → Run (`F9`)
5. Click on the `VOUT` node in the schematic to plot the output

### Export Data
1. Right-click the plot area → **File → Export**
2. Save as `ac_sweep_config1.csv`
3. LTspice exports columns: `Freq`, `V(VOUT)` (complex dB + phase)
4. Rename and move to `data/ac_sweep_config1.csv`

Repeat for Config 2 (`R2 = 19 kΩ`) and Config 3 (`R2 = 4 kΩ`), saving
as `ac_sweep_config2.csv` and `ac_sweep_config3.csv`.

---

## Step 3 — Transient Analysis (1 kHz Sine)

1. Change `Vin` source: `SINE(0 0.1 1k)` (100 mV amplitude, 1 kHz)
2. Simulation command: `.tran 1u 3m` (3 ms total, 1 µs max step)
3. Run simulation
4. Export `V(VOUT)` and `V(IN)` as `transient_config1.csv`

---

## Step 4 — Noise Analysis

1. Simulation command: `.noise V(VOUT) Vin dec 100 1 100k`
2. This computes input-referred voltage noise density
3. Plot `onoise` (output noise) and `inoise` (input-referred noise)
4. Export as `noise_sweep.csv`

> **Expected result:** Input-referred noise ≈ 18 nV/√Hz at 1 kHz,
> rising as 1/f below ≈ 200 Hz.

---

## Step 5 — Run Python Analysis

```bash
# Install dependencies
pip install -r requirements.txt

# Generate plots for all configurations
python scripts/generate_report_plots.py

# Or analyze a single configuration
python scripts/analyze_frequency_response.py --config 1
```

---

## Expected Results Summary

| Configuration | Midband Gain | -3 dB BW | GBW Product |
|---------------|-------------|----------|-------------|
| Config 1      | 20.00 dB    | 300 kHz  | 3.00 MHz    |
| Config 2      | 26.02 dB    | 150 kHz  | 3.00 MHz    |
| Config 3      | 13.98 dB    | 600 kHz  | 3.00 MHz    |

All three configurations should yield GBW ≈ 3 MHz, verifying consistency
with the TL071 model. Deviations > 5% indicate a simulation or netlist error.

---

## Extending to Real Lab Measurements

To replace simulation data with real measurements:

1. Build the circuit on a breadboard or PCB
2. Use a **network analyzer** (e.g., Analog Discovery 2 / Bode 100) or
   a **function generator + oscilloscope** to measure Vin and Vout
3. Compute gain = 20·log₁₀(|Vout/Vin|) at each frequency
4. Export measurement data in the same CSV column format used here
5. Drop the new CSVs into `data/` — the Python scripts will work unchanged

> The scripts are designed to be instrument-agnostic: any tool that can
> export `Frequency_Hz`, `Gain_dB`, and `Phase_deg` columns will work.
