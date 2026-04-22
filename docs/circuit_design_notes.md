# Circuit Design Notes

## Why Non-Inverting Topology?

The non-inverting amplifier was selected over the inverting topology for two reasons:

1. **High input impedance** — The signal source sees the op-amp's differential
   input impedance (> 10¹² Ω for JFET input), not R1. This avoids loading the
   signal source, which is critical in sensor interfaces.

2. **Positive gain** — Many signal conditioning chains need the output in-phase
   with the input. Inverting stages require an additional inversion or careful
   sign management downstream.

## Gain Derivation

By virtual short principle, V(IN−) = V(IN+) = Vin.
The voltage divider at the inverting input gives:

```
V(IN−) = Vout × R1 / (R1 + R2)
```

Setting V(IN−) = Vin and solving:

```
Gain = Vout / Vin = 1 + R2 / R1
```

For R1 = 1 kΩ, R2 = 9 kΩ: Gain = 1 + 9 = 10 (20 dB).

## Why ±15 V Supply?

The ±15 V dual-supply rail maximizes output swing for the TL071 (rated
output swing ≈ ±13.5 V on ±15 V). A single +5 V supply would limit
Vout to roughly 3.5 V peak, reducing the signal-to-noise headroom.
In a battery-powered design you'd optimize supply voltage for power budget,
but for a bench characterization board, ±15 V is conventional.

## -3 dB Bandwidth and GBW

For a voltage-feedback op-amp with dominant-pole compensation:

```
BW = GBW / Gain
```

This means every time you double the gain, you halve the bandwidth.
The TL071's GBW ≈ 3 MHz gives:

| Gain | BW        |
|------|-----------|
| 5    | 600 kHz   |
| 10   | 300 kHz   |
| 20   | 150 kHz   |
| 100  | 30 kHz    |

## Load Resistor Choice

R_LOAD = 10 kΩ was chosen to stay within the TL071's output current limit
(~10 mA short-circuit). With Vout_max ≈ 13 V and R_LOAD = 10 kΩ:

```
I_out = 13 V / 10 kΩ = 1.3 mA   (well within the 10 mA limit)
```

In a real design you'd also account for the feedback resistor network loading.

## Slew Rate Limitation

The TL071 slew rate is 13 V/µs. For a full-swing 13 V output:

```
f_slew = SR / (2π × Vpeak) = 13 V/µs / (2π × 13 V) ≈ 159 kHz
```

This means the slew rate can become limiting near or above 159 kHz for
large-signal inputs. At the 100 mV test stimulus used here, slew rate is
not a concern at the test frequencies.

## Metal Film vs Carbon Film Resistors

1% metal film resistors (e.g., 1 kΩ, 9 kΩ) were assumed in the component
table. Using 5% carbon film resistors would add up to ±0.4 dB gain error
worst-case. For a precision characterization fixture, 0.1% or better
resistors are preferred.

## Decoupling Capacitors (Not in Netlist, Essential in Hardware)

Any real implementation must include:
- 100 nF ceramic caps on each supply rail, placed within 5 mm of the op-amp pins
- Optional 10 µF bulk electrolytic caps at the supply entry point

Without decoupling, power supply noise couples into the output and degrades
apparent SNR. This is a common source of anomalies in bench measurements
that looks like amplifier noise but disappears when you probe the supply rail.
