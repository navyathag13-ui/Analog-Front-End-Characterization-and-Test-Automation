# Component Values and Circuit Parameters

## Op-Amp: TL071

| Parameter              | Value (Typical) | Source            |
|------------------------|-----------------|-------------------|
| Gain-bandwidth product | 3 MHz           | TI datasheet (SLOS082) |
| Input bias current     | 65 pA           | TI datasheet      |
| Input offset voltage   | 3 mV            | TI datasheet      |
| Input noise voltage    | 18 nV/√Hz @ 1 kHz | TI datasheet   |
| 1/f noise corner       | ~200 Hz         | TI datasheet      |
| Slew rate              | 13 V/µs         | TI datasheet      |
| Output voltage swing   | ±13.5 V (on ±15 V rail) | TI datasheet |
| Supply voltage         | ±15 V (this project) | Design choice |

## Gain Resistors

| Config | R1 (Ω) | R2 (Ω) | Nominal Gain (V/V) | Gain (dB) | Predicted fc (kHz) |
|--------|--------|--------|-------------------|-----------|-------------------|
| 1      | 1,000  | 9,000  | 10                | 20.00     | 300               |
| 2      | 1,000  | 19,000 | 20                | 26.02     | 150               |
| 3      | 1,000  | 4,000  | 5                 | 13.98     | 600               |

**Gain formula (non-inverting topology):**

```
Gain = 1 + R2 / R1
```

**-3 dB bandwidth prediction (single-pole model):**

```
fc = GBW / Gain
```

All three configurations share GBW = 3 MHz, consistent with the TL071 model.

## Power Supply

| Rail | Value |
|------|-------|
| VCC  | +15 V |
| VEE  | –15 V |

## Input Stimulus

| Parameter       | Value     |
|-----------------|-----------|
| AC amplitude    | 100 mV    |
| Transient amp.  | 100 mV (sine, 1 kHz) |
| Source impedance | 50 Ω (assumed) |

## Load

| Parameter     | Value   |
|---------------|---------|
| Load resistor | 10 kΩ   |

## Optional Output RC Filter

Intended to demonstrate single-pole filtering combined with the gain stage.

| Part  | Value | Purpose |
|-------|-------|---------|
| Rout  | 560 Ω | Series resistance |
| Cout  | 1 nF  | Shunt capacitance |
| fc    | ≈ 284 kHz | Cutoff frequency (at Config 1 nominal gain) |

To enable: uncomment the `Rout` and `Cout` lines in `circuit_netlist.txt`.

## Component Tolerances (Design Assumptions)

| Component | Tolerance | Effect on Gain |
|-----------|-----------|---------------|
| R1, R2    | ±1% (metal film) | ±0.09 dB worst-case |
| Supply rails | ±0.5% | Negligible for gain |
| Op-amp GBW | ±30% part-to-part | ±30% BW shift |
