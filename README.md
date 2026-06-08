# IoT Recycling Sorter

An automated waste-sorting station that uses computer-vision colour classification on an NVIDIA Jetson and a robotic arm controlled by an Arduino to pick recyclable items off a feed surface and drop them into one of four colour-coded bins.

## Pipeline

```
Webcam → Jetson (OpenCV HSV classification) → 2-bit GPIO code → Arduino → robotic arm → bin
```

## Repository layout

```
IoT Recycling Sorter/
├── firmware/    Arduino sketch (servo control, GPIO read, safety)
├── jetson/      Python: camera capture, OpenCV classification, GPIO write
├── hardware/    Wiring diagrams, BOM, mechanical drawings
├── docs/        Design notes, calibration data, demo scripts
└── .claude/     Claude Code workspace
```

## Signalling protocol (Jetson → Arduino)

Two GPIO lines carry a 2-bit binary code.

| B1 | B0 | Bin | Notes |
|---:|---:|:---:|---|
| 0 | 0 | idle | no item / not yet classified |
| 0 | 1 | A | (e.g., Red — define in `docs/`) |
| 1 | 0 | B | (e.g., Green) |
| 1 | 1 | C | (e.g., Blue) |

If a 4th bin is needed, add a 3rd GPIO line (8 codes) — do not widen the protocol later.

Jetson GPIO is 3.3 V, Arduino logic is 5 V — use a level shifter (74HCT04 or bidirectional) for noise immunity.

## Quick start

1. **Hardware**: wire up per `hardware/` diagrams. External 5–6 V supply for the servos, common ground between Arduino + Jetson + supply.
2. **Arduino**: open `firmware/` sketch in Arduino IDE, upload to Uno/Nano.
3. **Jetson**: `pip3 install opencv-python Jetson.GPIO`, then run `python3 jetson/main.py`.

## Status

Early-stage scaffold. See [`.claude/CLAUDE.md`](.claude/CLAUDE.md) for architecture decisions, open questions, and the development loop.
