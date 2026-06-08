# Tech Defaults

## Jetson Python

- **Python 3.8+** (Jetson stock is usually 3.10).
- **OpenCV** for image capture + HSV classification (`pip3 install opencv-python`).
- **Jetson.GPIO** for the 2-bit binary output (`sudo pip3 install Jetson.GPIO` then add user to the `gpio` group).
- One main entry point: `jetson/main.py`. Three responsibilities only — capture, classify, emit. Don't bolt unrelated services onto this script.
- Configuration in a separate file (`jetson/config.py`): HSV ranges, GPIO pin numbers, camera index, confidence threshold. **No magic numbers in the main script.**
- Use `numpy` array operations for masks, not pixel-by-pixel Python loops. A 720p frame iterated in Python is ~30 s; the same masking in NumPy is ~5 ms.

---

## Arduino C++

- **Arduino Uno or Nano**, ATmega328P.
- Use the built-in `Servo.h` library — supports up to 12 servos on Uno without timer conflicts (avoid pin 9 + 10 if using `tone()`).
- Pin assignments live in `#define` constants at the top of the sketch, **never** as bare numbers in function calls.
- Each bin's motion sequence is a `const PROGMEM` array of `{angle1, angle2, ...}` — keeps RAM free.
- Use `delay()` only during deliberate motion pauses. Sensor / GPIO reads should be in a `millis()`-based scheduler so the loop can respond to E-stop in <50 ms.
- **Never** call `Serial.print()` inside a servo-write loop — UART writes take ~1 ms each and will visibly stutter the motion.

---

## Signalling Protocol

- 2 GPIO lines from Jetson to Arduino, both inputs on the Arduino side.
- Arduino uses `INPUT_PULLUP` on both pins so a disconnected Jetson reads as `11` — pick an *idle* code that's not `11` (i.e., use `00` for idle so dropped cable doesn't trigger Bin C).
- Read both pins on every loop iteration; debounce with at least 3 consecutive identical reads before acting. Code transitions during the Jetson's GPIO write should not cause a glitched bin movement.
- Optional 3rd line: `data_valid` strobe. Recommended.

---

## Naming Conventions

- **Folders**: lowercase, hyphenated (`firmware/`, `jetson/`, `hardware/`).
- **Files**: snake_case for Python (`color_classify.py`), kebab-case for top-level docs (`bring-up-guide.md`), CamelCase for Arduino sketches (`Sorter.ino`).
- **Constants**: SCREAMING_SNAKE_CASE in both Python and C++.
- **Bin labels**: use letters or named colours, not numbers. `BIN_RED` / `BIN_BLUE` reads better than `BIN_1` / `BIN_3` six months later.

---

## Clean Code

- **Functions do one thing** and are < 30 lines. If a function is longer, it's actually two functions.
- **No copy-paste**. If a motion sequence appears in 3 places, extract it.
- **Comment the *why*, not the *what*.** Code shows what; comments should explain why an unusual choice was made.
- **No dead code.** Delete commented-out blocks before committing.
- **No premature abstraction.** Three near-duplicates is acceptable; six is not. Don't build a "framework" for a one-week project.

---

## Testing & Verification

- Every PR is bench-tested on real hardware before merge. Simulation-only changes are explicitly labelled as such.
- The Arduino sketch has a "demo mode" (compile flag) that cycles through bins on a timer — proves the arm works without needing the Jetson present.
- The Jetson script has a "dry-run mode" that prints the bin code to stdout instead of toggling GPIO — proves classification works without needing the arm.
- Calibration data (HSV ranges, servo angles per bin) lives in version control. Tuning is a recorded artifact, not folklore.
