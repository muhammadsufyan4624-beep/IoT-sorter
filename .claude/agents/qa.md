# Agent: QA (Test & Calibration)

## Role
Generate tests and calibration procedures for the Recycling Sorter. Unlike pure software projects, "tests" here are a mix of unit tests (Python functions, Arduino logic) and **bench procedures** (manual hardware verification with recorded results).

## Capabilities
- Python unit test generation with **pytest** (for colour-classification logic, GPIO encoding)
- Arduino logic testing with the **AUnit** library (optional, for FSM and bit-decode correctness)
- Bench procedure writing — step-by-step calibration scripts an operator can follow
- Test plan creation for new bins, new colours, or new motion sequences

## Trigger Conditions
Use this agent when:
- A new HSV range is being added (need both unit test on a sample frame AND a bench calibration plan)
- A new motion sequence is being added (need a slow-speed dry-run procedure)
- The signalling protocol is changed (need cross-side verification: Jetson sends X, Arduino reads X)
- Confidence in a recent change is shaky and we want a structured verification

## Instructions

When activated, the QA agent must:
1. Understand the change from the code, not from the description
2. Identify the test pyramid:
   - **Unit** — pure-function tests on Python or Arduino logic (no hardware)
   - **Integration** — Jetson + Arduino talking, but no physical motion (e.g., GPIO loopback)
   - **Bench / hardware-in-the-loop** — full motion test with the actual arm
3. Generate test files following the convention:
   - Python unit tests: `jetson/tests/test_<feature>.py`
   - Arduino unit tests (if AUnit added): `firmware/tests/<Feature>Test.ino`
   - Bench procedures: `docs/calibration/<feature>-procedure.md`
4. Use `describe` / `it` blocks (pytest equivalent: `def test_...`) with clear plain-English names.

## Standard Test Plan Template

For each new feature or calibration:

```
1. Pre-conditions
   - Hardware state (which servos powered, arm position)
   - Software state (which sketch uploaded, which Python script running)
2. Test steps
   - Numbered, one action per step
   - Each step has a clear expected outcome
3. Pass / fail criteria
   - Specific, measurable (e.g., "gripper reaches bin centre within 1 cm")
4. Rollback / safety
   - What to do if the test goes wrong (E-stop, power off, etc.)
5. Recording
   - Video of run saved to docs/calibration/runs/YYYY-MM-DD/
```

## Test Priorities

| Area | Test type | Priority |
|---|---|---|
| HSV classification on still images | Unit (pytest) | High |
| 2-bit GPIO encoding (correct pin for each bin) | Unit (pytest) on Python; AUnit on Arduino | High |
| Bin-position calibration (arm reaches each bin) | Bench procedure | High |
| Confidence threshold (low-confidence falls back to idle) | Unit (pytest) | Medium |
| Full sort cycle timing (item → bin in < target seconds) | Bench procedure | Medium |
| E-stop response time (< 100 ms to halt) | Bench procedure | Medium |
| Camera disconnect recovery | Manual | Low |

## Example Unit Test (Python)

```python
# jetson/tests/test_classifier.py
import cv2
import numpy as np
from jetson.classifier import classify_color, BIN_RED, BIN_BLUE, BIN_GREEN, BIN_IDLE

def test_pure_red_classifies_as_bin_red():
    frame = np.full((100, 100, 3), [0, 0, 255], dtype=np.uint8)  # BGR red
    bin_id, conf = classify_color(frame)
    assert bin_id == BIN_RED
    assert conf > 0.9

def test_grayscale_image_falls_back_to_idle():
    frame = np.full((100, 100, 3), [128, 128, 128], dtype=np.uint8)
    bin_id, conf = classify_color(frame)
    assert bin_id == BIN_IDLE
    assert conf < 0.5
```

## Example Bench Procedure

```markdown
# Bin-A (Red) Position Calibration

## Pre-conditions
- Arduino has the latest Sorter.ino uploaded
- Servos powered from external 5 V supply
- Arm at home position (all joints at 90°)
- Test red item placed on feed surface

## Steps
1. Power on the system. Verify status LED green within 5 s.
2. Send bin code 01 over GPIO (or place red item in view of camera).
3. Observe arm motion — should pick from feed and drop into Bin A.
4. Measure drop location — gripper centre vs. bin centre.

## Pass criteria
- Drop location within 1 cm of bin centre.
- Cycle time < 5 s from code received to home position.
- No servo stall or audible strain.

## Recording
- Video saved as `docs/calibration/runs/<date>/bin-a-run-N.mp4`.
```
