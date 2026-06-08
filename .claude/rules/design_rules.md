# Design Rules

## Core Principles

1. **Safety first** — the arm has moving parts that can damage hardware or hurt fingers. Every design decision must be reversible or have an E-stop path.
2. **Deterministic actuation** — servo motion is on the Arduino, period. No "let the Jetson drive servos over USB" shortcuts; latency jitter will smash the gripper.
3. **Single source of truth per concern** — vision belongs to the Jetson, motion belongs to the Arduino. Don't duplicate logic on both sides.
4. **Fail safe** — on power loss, comms drop, or Jetson crash, the arm should land in a known *safe home position*, not stay frozen mid-motion.

---

## Visual / Mechanical

- Arm joints labelled and colour-coded in `docs/` diagrams so anyone can see which servo goes to which Arduino pin.
- The "working envelope" of the arm (the cylinder it can sweep through) is documented — bins must sit inside it.
- Each bin has its **(x, y, angle)** position recorded in a single config table on the Arduino. Don't sprinkle hard-coded angles across the sketch.
- Cable runs are tied down and don't cross the arm's path. A cable snagged in a joint at full torque can break a servo.

---

## Vision

- HSV thresholds live in **one place** (`jetson/config.py` or similar). Don't hardcode them inline in classify functions.
- The classifier outputs the bin code AND a confidence score. If confidence < threshold, emit `00` (idle) — never guess.
- Capture lighting must be controlled: fixed white-balance, fixed exposure, fixed light source. "It works in this room but not that one" is a calibration failure, not a vision failure.
- Show the classification debug overlay (current bin + confidence) on a preview window during development. Hide it for production.

---

## Power & Wiring

- Servos **never** powered from Arduino's onboard 5 V regulator. Always external supply.
- All grounds tied together (Arduino, Jetson, external PSU) at one star point — not daisy-chained.
- Level shifter between Jetson and Arduino GPIO is the default, not an afterthought. 3.3 V → 5 V direct works most of the time but fails under noise; cheaper to fix now than to chase intermittent miss-codes later.
- Add a fuse or polyfuse on the external 5 V rail. Servo stall current can be 2+ A and a short to ground is a fire hazard.

---

## Accessibility / Demo

- Add a single physical button that returns the arm to the home position. Useful for demos and panic recovery.
- LCD or RGB LED on the front panel shows the **current bin code** so observers can see what the system decided without watching a serial console.
- The system should be runnable in a "no Jetson" debug mode where the Arduino sweeps through bins on a timer — proves the arm works without needing the vision side.
