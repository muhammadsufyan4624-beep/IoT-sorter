# Electrical & Wiring Guide

This guide details the connections between the NVIDIA Jetson Nano/TX2, the Arduino Uno/Nano, and the robotic arm's servo motors.

---

## 1. GPIO Pin Mapping

The physical interface uses 3 GPIO pins to send commands from the Jetson to the Arduino.

| Signal | Jetson Board Pin (Physical) | Arduino Uno Pin (Digital) | Description |
|:---|:---:|:---:|:---|
| **B0** | Pin 11 | Pin 2 | Bit 0 (LSB) of the bin code |
| **B1** | Pin 13 | Pin 3 | Bit 1 (MSB) of the bin code |
| **Strobe** | Pin 15 | Pin 4 | Data-Valid handshake signal |
| **GND** | Pin 39 (or any Ground) | GND | Common reference ground |

---

## 2. Logic Level Shifter (Jetson 3.3V ↔ Arduino 5V)

*   **The Issue:** Jetson GPIO logic is 3.3 V. The Arduino Uno/Nano logic is 5 V. Directly sending 3.3 V signals to Arduino inputs will usually work (since high threshold $V_{IH} \approx 3.0\text{ V}$), but it has very low noise margins and can lead to erratic behavior near mechanical motors.
*   **The Solution:** Use a **74HCT04 hex inverter** or a bidirectional level shifter module (e.g. TXB0104 or a simple BSS138-based MOSFET level shifter).
*   **Wiring with a Bidirectional Level Shifter:**
    *   Connect the **Low Voltage (LV)** pin of the shifter to the Jetson's 3.3V output (Board Pin 1 or 17).
    *   Connect the **High Voltage (HV)** pin of the shifter to the Arduino's 5V output.
    *   Connect the Jetson pins (11, 13, 15) to the LV1, LV2, LV3 channels.
    *   Connect the Arduino pins (2, 3, 4) to the HV1, HV2, HV3 channels.
    *   Connect Jetson GND and Arduino GND to the level shifter's GND pins.

---

## 3. Power Distribution (Crucial)

Robotic arm servos (especially under load) draw high current spikes that will reset your Arduino if they share the same power regulator.

> [!CAUTION]
> **Never power the servos directly from the Arduino's 5V pin!** Doing so can burn out the Arduino voltage regulator or cause immediate processor brownouts.

### Power Guidelines:
1.  **Servo Power Supply**: Use a dedicated external **5 V or 6 V DC power supply** capable of outputting at least **3 A to 5 A** (depending on the number of servos).
2.  **Common Ground**: Connect the negative terminal (`-` or `GND`) of the external servo power supply, the Arduino `GND` pin, and the Jetson `GND` pin together. Without a shared common ground, the servo PWM and logic signals will drift and misbehave.

---

## 4. Wiring Diagram Schematics

```
 +------------------+                      +------------------+
 |   NVIDIA JETSON  |                      |     ARDUINO      |
 |   (3.3V Logic)   |                      |    (5V Logic)    |
 |                  |                      |                  |
 |  Board Pin 11    |--> [LV1]   [HV1] --> | Pin 2 (B0)       |
 |  Board Pin 13    |--> [LV2]   [HV2] --> | Pin 3 (B1)       |
 |  Board Pin 15    |--> [LV3]   [HV3] --> | Pin 4 (Strobe)   |
 |                  |     LEVEL SHIFTER    |                  |
 |  Board Pin 39    |--------------------->| GND              |
 +------------------+                      +--------+---------+
                                                    |
                                                    |
 +--------------------------------------------------+  Common
 |                                                     Ground
 |   +----------------------+
 +-->| Servo Power Supply   |
 |   | (5V - 6V, 3A+)       |
 |   |                      |
 |   |  Positive (+)        |--------+
 |   |  Negative (-)        |--+     |
 |   +----------------------+  |     |
 |                             |     |
 |   +----------------------+  |     |
 |   |  MG996R Servos       |  |     |
 |   |                      |  |     |
 +-->|  GND (Brown/Black)   |<-+     |
     |  VCC (Red)           |<-------+
     |  PWM Signal (Orange) |<--------- Arduino PWM Pins (6, 9, 10, 11)
     +----------------------+
```
