# IoT Recycling Sorter — Claude Code Project Brain

## Project Overview

**IoT Recycling Sorter** — an automated waste-sorting station that uses computer-vision colour classification on an NVIDIA Jetson, and a robotic arm controlled by an Arduino, to pick recyclable items off a feed surface and drop them into one of four colour-coded bins.

Lead developer: **Faaz Ali Sayyed**.

The system is *vision-driven, hardware-actuated*: every classification decision comes from an image, but the physical sorting is a closed-loop motion that does not require the Jetson once the bin is decided.

---

## Core Architecture: See → Classify → Encode → Pick → Drop

```
Item placed on feed surface
  → Webcam captures frame (USB → Jetson)
  → Jetson runs OpenCV colour classification (HSV thresholds or small CNN)
  → 2-bit binary code (bin_id) emitted on 2 GPIO pins
  → Arduino reads 2 GPIO pins → looks up bin → drives robotic arm
  → Servos move to: pick → travel → drop into matching bin
  → Arm returns to home → ready for next item
```

---

## Dual-Processor Design

| Processor | Role |
|-----------|------|
| **NVIDIA Jetson** | Camera capture, image classification, sets two GPIO pins |
| **Arduino Uno/Nano** | Reads two GPIO pins, drives robotic arm servos via PWM |
| **Communication** | 2 GPIO lines (Jetson 3.3 V → Arduino 5 V, **logic-level-shifted**) — see "Signalling Protocol" below |

This split is deliberate. The Jetson does the heavy lifting that needs Linux + OpenCV. The Arduino does the deterministic, real-time work (servo PWM) that does not tolerate kernel scheduling jitter. Each side can be developed, tested, and debugged independently.

---

## Signalling Protocol (Jetson → Arduino)

Two GPIO lines carry a 2-bit binary code. The Arduino samples both lines at ≥10 Hz and acts only when the code changes from `00` (idle).

| Bit B1 | Bit B0 | Code | Meaning |
|---:|---:|:---:|---|
| 0 | 0 | `00` | Idle / no item / not yet classified |
| 0 | 1 | `01` | Bin A (e.g., Red — define in project README) |
| 1 | 0 | `10` | Bin B (e.g., Green) |
| 1 | 1 | `11` | Bin C (e.g., Blue) |

**Note:** if a 4th bin is needed, switch to 3 GPIO lines (8 codes) instead of widening the protocol later — a one-line firmware change.

**Voltage levels:** Jetson GPIO is 3.3 V. Arduino registers 3.3 V as logic-HIGH (V_IH ≈ 3.0 V), so direct wiring works but a **74HCT04 or bidirectional level shifter is recommended** for noise immunity in a workshop environment.

**Strobe / handshake (optional, recommended):** add a third GPIO line as a `data_valid` strobe so the Arduino only samples B1/B0 when the strobe is high. Without it, transient values during the Jetson's classification can be misread.

---

## Classification Method

**Primary:** OpenCV HSV colour thresholding. Capture frame → BGR→HSV → mask each colour range → pick the bin whose mask has the largest pixel area above a confidence threshold. Fast (~30 fps), no training required, deterministic.

**Fallback / future:** lightweight CNN (MobileNetV3-Small or YOLOv8n-cls) for shape-aware classification when colour alone is ambiguous (e.g., transparent plastic).

**Why colour first:** the project goal is sorting by colour-coded bin, and the items are visually distinct in colour. HSV is robust to lighting changes if the camera's white balance is locked.

---

## Robotic Arm

Pick-and-place arm with at least 4 degrees of freedom. Each joint is a servo driven by an Arduino PWM pin.

| Joint | Servo | Approx. range |
|---|---|---|
| Base rotation | MG996R or similar | 0° – 180° |
| Shoulder | MG996R | 0° – 180° |
| Elbow | SG90 or MG996R | 0° – 180° |
| Wrist (optional) | SG90 | 0° – 180° |
| Gripper | SG90 | open ↔ close |

**Power:** servos draw spikes of 1+ A under load. Power them from an **external 5–6 V supply**, never from the Arduino's onboard 5 V regulator. Common ground between Arduino, Jetson, and the external supply is non-negotiable.

**Motion model:** the Arduino runs an `armMoveTo(bin_id)` routine — a pre-recorded sequence of joint angles for each of the 4 bins. Tune these once during bring-up; they do not change at runtime.

---

## Sensors & Actuators Summary

| Component | Interface | Purpose |
|---|---|---|
| USB webcam (UVC, 720p) | Jetson USB | Capture item image |
| Robotic arm (≥4 servos) | Arduino PWM pins | Pick-and-place |
| External 5–6 V PSU | Wall adapter | Servo power, separate from Arduino |
| Level shifter (recommended) | 74HCT or bidirectional FET | Jetson 3.3 V → Arduino 5 V GPIO |
| Status LED (optional) | Arduino GPIO | Show current bin / idle state |
| Reset / E-stop button | Arduino GPIO | Halt arm in motion (safety) |

---

## Folder Map

```
IoT Recycling Sorter/
├── firmware/        ← Arduino sketches (motion sequences, GPIO read, safety)
├── jetson/          ← Python: camera capture, OpenCV classification, GPIO write
├── hardware/        ← Wiring diagrams, BOM, mechanical drawings
├── docs/            ← Design notes, calibration data, demo scripts
├── README.md
└── .claude/         ← Claude Code workspace
    ├── CLAUDE.md
    ├── rules/
    └── agents/
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Embedded vision | NVIDIA Jetson — Python 3 + OpenCV + `Jetson.GPIO` |
| Microcontroller | Arduino Uno/Nano — `Servo.h`, plain C++ |
| Comms | 2 GPIO lines (3.3 V → 5 V level-shifted) |
| Power | Arduino USB-powered; servos on external 5–6 V supply |
| Version control | Git + GitHub (private repo) |

---

## Mandatory Development Loop

```
1. TASK    → Define what you're building and why
2. BUILD   → Implement the change
3. VERIFY  → Confirm it works (video clip, log output, or photo of behaviour)
```

No exceptions. Especially important for the arm motion sequences — a wrong angle can damage the gripper or jam the mechanism.

---

## Safety Notes

- The arm has real moving parts. Always run new motion code at **slow speed first** (e.g., 30°/sec) before normal speed.
- Keep your hands clear of the arm's working envelope during testing.
- Have an E-stop wired so you can cut power in 100 ms if a sequence goes wrong.
- Servos can stall and overheat if they fight against an obstruction — don't leave the system unattended on first runs.

---

## Open Questions to Resolve Early

1. **Which 4 colour categories** map to which bins? (Define in `docs/` before tuning HSV thresholds.)
2. **Item feed mechanism** — manual placement, gravity-fed chute, or conveyor belt?
3. **Lighting** — fixed LED ring over the camera, or rely on ambient room light? (Fixed lighting massively simplifies HSV tuning.)
4. **Item size** — what's the max dimension the gripper can handle? Drives gripper design.
5. **Cycle time target** — 3 s per item? 10 s? Drives servo speed and arm trajectory complexity.
