# Color Calibration Guide

The color classifier uses OpenCV to convert the webcam frame to the HSV (Hue, Saturation, Value) color space and segment the target colors using threshold values. Because lighting conditions and camera properties vary, you will need to calibrate the low/high boundaries.

---

## 1. HSV Color Space in OpenCV

OpenCV represents HSV values differently than standard graphics software:
*   **Hue (H)**: `0` to `180` (representing color angle: `0/180` is Red, `60` is Green, `120` is Blue).
*   **Saturation (S)**: `0` to `255` (representing color intensity/purity; `0` is gray, `255` is fully saturated).
*   **Value (V)**: `0` to `255` (representing brightness; `0` is black, `255` is white).

---

## 2. Using the Calibration GUI

To start the calibration interface on a computer or Jetson, run:

```bash
python jetson/color_detector.py --calibrate
```

Two windows will open:
1.  **Recycling Sorter Live**: Displays the active video feed with bounding boxes around classified colors.
2.  **Calibration Panel / Calibration Mask Preview**: Contains sliders to adjust limits in real time.

### Calibration Process:
1.  Place a target recyclable object (e.g. a red bottle cap) under the camera.
2.  Use the **Color Select** slider to select the color channel you are calibrating:
    *   `0`: Red1
    *   `1`: Red2 (for red wrap-around)
    *   `2`: Green
    *   `3`: Blue
3.  Observe the **Calibration Mask Preview** window. It shows a black-and-white mask of pixels matching the current range. White = matched; Black = ignored.
4.  Adjust **Low H**, **High H**, **Low S**, **High S**, **Low V**, and **High V** until only your target object appears as white, and the background remains black.
5.  Read the final slider positions and edit the defaults in `DEFAULT_HSV_RANGES` inside [color_detector.py](file:///c:/Users/maanf/OneDrive/Desktop/IoT%20Recycling%20Sorter/jetson/color_detector.py).

---

## 3. Best Practices for Calibration

*   **Fixed Lighting**: Always use a fixed LED light source. Ambient room light changes throughout the day, which will throw off HSV calibration.
*   **Red Wrap-Around**: In HSV, red lies at both ends of the scale (e.g., Hue `0-10` and Hue `170-180`). We handle this using two masks `Red1` and `Red2` which are combined with a logical OR. Calibrate both ranges.
*   **Aperture/White Balance**: Lock your camera's exposure, gain, and white balance settings in OpenCV to prevent the camera auto-adjusting to different objects.
