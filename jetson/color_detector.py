#!/usr/bin/env python3
"""
IoT Recycling Sorter - OpenCV Color Detector
Handles camera capture, HSV color classification, and GPIO output signaling.
Features:
  - Real-time HSV color detection for Red, Green, and Blue.
  - Simulation/mock mode for running on PCs without Jetson hardware.
  - Interactive Calibration Mode with HSV trackbars.
  - Robust 2-bit binary signaling with an optional Strobe/Data-Valid handshake line.
"""

import sys
import time
import argparse
import cv2
import numpy as np

# Try to import Jetson.GPIO, fall back to mock interface if unavailable
GPIO_AVAILABLE = False
try:
    import Jetson.GPIO as GPIO
    GPIO_AVAILABLE = True
except ImportError:
    try:
        import RPi.GPIO as GPIO
        GPIO_AVAILABLE = True
    except ImportError:
        pass


class MockGPIO:
    """Mock GPIO implementation for running on non-Jetson hardware (PCs)."""
    BOARD = "BOARD"
    OUT = "OUT"
    HIGH = 1
    LOW = 0

    @staticmethod
    def setmode(mode):
        print(f"[GPIO Mock] Set mode to {mode}")

    @staticmethod
    def setup(pin, direction):
        print(f"[GPIO Mock] Setup pin {pin} as {direction}")

    @staticmethod
    def output(pin, val):
        state = "HIGH" if val else "LOW"
        # We print only state changes to avoid flooding the console
        if not hasattr(MockGPIO, "_state"):
            MockGPIO._state = {}
        if MockGPIO._state.get(pin) != val:
            MockGPIO._state[pin] = val
            print(f"[GPIO Mock] Pin {pin} -> {state}")

    @staticmethod
    def cleanup():
        print("[GPIO Mock] Cleanup pins")


if not GPIO_AVAILABLE:
    GPIO = MockGPIO


class GPIOSignaller:
    """Manages the physical 2-bit binary + strobe signals sent to the Arduino."""
    def __init__(self, b0_pin, b1_pin, strobe_pin, force_mock=False):
        self.b0_pin = b0_pin
        self.b1_pin = b1_pin
        self.strobe_pin = strobe_pin
        self.is_mock = force_mock or not GPIO_AVAILABLE
        
        print(f"Initializing Signaller (Mock Mode: {self.is_mock})")
        GPIO.setmode(GPIO.BOARD)
        GPIO.setup(self.b0_pin, GPIO.OUT)
        GPIO.setup(self.b1_pin, GPIO.OUT)
        GPIO.setup(self.strobe_pin, GPIO.OUT)
        
        # Start in Idle state
        self.current_code = -1
        self.write_code(0)

    def write_code(self, code):
        """
        Sends a 2-bit code to the Arduino.
        00 = Idle (0)
        01 = Bin A (1)
        10 = Bin B (2)
        11 = Bin C (3)
        """
        if code == self.current_code:
            return  # No state change

        print(f"Signalling State Change: Bin Code {code:02b} (Decimal: {code})")
        
        if code == 0:
            # Drop Strobe first, then set data pins to LOW
            GPIO.output(self.strobe_pin, GPIO.LOW)
            time.sleep(0.02)  # Delay for level-shifting / Arduino sampling stability
            GPIO.output(self.b0_pin, GPIO.LOW)
            GPIO.output(self.b1_pin, GPIO.LOW)
        else:
            # If transitioning between two active codes, drop strobe first to avoid transient reads
            GPIO.output(self.strobe_pin, GPIO.LOW)
            time.sleep(0.02)
            
            # Write data bits
            b0_val = GPIO.HIGH if (code & 1) else GPIO.LOW
            b1_val = GPIO.HIGH if (code & 2) else GPIO.LOW
            
            GPIO.output(self.b0_pin, b0_val)
            GPIO.output(self.b1_pin, b1_val)
            
            time.sleep(0.02)  # Wait for line voltage levels to stabilize
            GPIO.output(self.strobe_pin, GPIO.HIGH) # Strobe HIGH signals data is valid

        self.current_code = code

    def cleanup(self):
        self.write_code(0)
        GPIO.cleanup()


# Default HSV threshold bounds
# HSV format in OpenCV: H in [0, 180], S in [0, 255], V in [0, 255]
DEFAULT_HSV_RANGES = {
    "Red1":   {"low": [0, 120, 70],      "high": [10, 255, 255]},
    "Red2":   {"low": [170, 120, 70],    "high": [180, 255, 255]},
    "Green":  {"low": [35, 60, 60],      "high": [85, 255, 255]},
    "Blue":   {"low": [95, 60, 60],      "high": [135, 255, 255]}
}

def create_calibration_window(ranges):
    """Creates windows and trackbars to tune HSV values in real-time."""
    cv2.namedWindow("Calibration Panel", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("Calibration Panel", 400, 700)
    
    def nothing(x):
        pass

    # Create sliders for each color channel's low/high bounds
    # We will adjust a single selected color at a time to keep it manageable,
    # or just list trackbars for one main active color channel.
    colors = ["Red1", "Red2", "Green", "Blue"]
    cv2.createTrackbar("Color Select", "Calibration Panel", 0, len(colors)-1, nothing)
    
    cv2.createTrackbar("Low H", "Calibration Panel", 0, 180, nothing)
    cv2.createTrackbar("High H", "Calibration Panel", 180, 180, nothing)
    cv2.createTrackbar("Low S", "Calibration Panel", 0, 255, nothing)
    cv2.createTrackbar("High S", "Calibration Panel", 255, 255, nothing)
    cv2.createTrackbar("Low V", "Calibration Panel", 0, 255, nothing)
    cv2.createTrackbar("High V", "Calibration Panel", 255, 255, nothing)

    # Initialize slider positions
    color_name = colors[0]
    cv2.setTrackbarPos("Low H", "Calibration Panel", ranges[color_name]["low"][0])
    cv2.setTrackbarPos("High H", "Calibration Panel", ranges[color_name]["high"][0])
    cv2.setTrackbarPos("Low S", "Calibration Panel", ranges[color_name]["low"][1])
    cv2.setTrackbarPos("High S", "Calibration Panel", ranges[color_name]["high"][1])
    cv2.setTrackbarPos("Low V", "Calibration Panel", ranges[color_name]["low"][2])
    cv2.setTrackbarPos("High V", "Calibration Panel", ranges[color_name]["high"][2])


def main():
    parser = argparse.ArgumentParser(description="IoT Recycling Sorter - Jetson OpenCV Color Classifier")
    parser.add_argument("--camera", type=int, default=0, help="Camera device index (default: 0)")
    parser.add_argument("--width", type=int, default=640, help="Frame width (default: 640)")
    parser.add_argument("--height", type=int, default=480, help="Frame height (default: 480)")
    parser.add_argument("--no-gpio", action="store_true", help="Force disable GPIO output (use mock)")
    parser.add_argument("--calibrate", action="store_true", help="Open HSV calibration panel sliders")
    parser.add_argument("--min-area", type=int, default=3000, help="Min contour pixel area to trigger bin")
    
    # GPIO pin mappings (Physical board layout numbers)
    parser.add_argument("--pin-b0", type=int, default=11, help="GPIO Pin for B0 bit (default: Board 11)")
    parser.add_argument("--pin-b1", type=int, default=13, help="GPIO Pin for B1 bit (default: Board 13)")
    parser.add_argument("--pin-strobe", type=int, default=15, help="GPIO Pin for Strobe (default: Board 15)")
    args = parser.parse_args()

    # Initialize GPIO signaling
    signaller = GPIOSignaller(args.pin_b0, args.pin_b1, args.pin_strobe, force_mock=args.no_gpio)

    # Open video capture
    cap = cv2.VideoCapture(args.camera)
    if not cap.isOpened():
        print(f"Error: Could not open camera source {args.camera}")
        sys.exit(1)
        
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, args.width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, args.height)

    # Use default HSV parameters
    hsv_ranges = DEFAULT_HSV_RANGES.copy()

    if args.calibrate:
        create_calibration_window(hsv_ranges)
        last_color_idx = 0

    print("\nStarting Color Detector main loop. Press 'q' in the window to quit.")
    print("Signaling protocol mapping:")
    print("  - NO ITEM / IDLE : 00 (Decimal 0)")
    print("  - RED            : 01 (Decimal 1)")
    print("  - GREEN          : 10 (Decimal 2)")
    print("  - BLUE           : 11 (Decimal 3)")
    print("-" * 50)

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("Failed to capture frame from camera.")
                break

            # Preprocessing
            blurred = cv2.GaussianBlur(frame, (5, 5), 0)
            hsv = cv2.cvtColor(blurred, cv2.COLOR_BGR2HSV)

            # Update calibration parameters if calibration window is active
            if args.calibrate:
                colors = ["Red1", "Red2", "Green", "Blue"]
                color_idx = cv2.getTrackbarPos("Color Select", "Calibration Panel")
                color_name = colors[color_idx]
                
                # If color selection changed on the slider, update sliders to show that color's values
                if color_idx != last_color_idx:
                    cv2.setTrackbarPos("Low H", "Calibration Panel", hsv_ranges[color_name]["low"][0])
                    cv2.setTrackbarPos("High H", "Calibration Panel", hsv_ranges[color_name]["high"][0])
                    cv2.setTrackbarPos("Low S", "Calibration Panel", hsv_ranges[color_name]["low"][1])
                    cv2.setTrackbarPos("High S", "Calibration Panel", hsv_ranges[color_name]["high"][1])
                    cv2.setTrackbarPos("Low V", "Calibration Panel", hsv_ranges[color_name]["low"][2])
                    cv2.setTrackbarPos("High V", "Calibration Panel", hsv_ranges[color_name]["high"][2])
                    last_color_idx = color_idx
                else:
                    # Update parameters from trackbar positions
                    hsv_ranges[color_name]["low"] = [
                        cv2.getTrackbarPos("Low H", "Calibration Panel"),
                        cv2.getTrackbarPos("Low S", "Calibration Panel"),
                        cv2.getTrackbarPos("Low V", "Calibration Panel")
                    ]
                    hsv_ranges[color_name]["high"] = [
                        cv2.getTrackbarPos("High H", "Calibration Panel"),
                        cv2.getTrackbarPos("High S", "Calibration Panel"),
                        cv2.getTrackbarPos("High V", "Calibration Panel")
                    ]

            # Generate masks
            # Red uses two ranges because Hue wraps around 180
            red1_mask = cv2.inRange(hsv, np.array(hsv_ranges["Red1"]["low"]), np.array(hsv_ranges["Red1"]["high"]))
            red2_mask = cv2.inRange(hsv, np.array(hsv_ranges["Red2"]["low"]), np.array(hsv_ranges["Red2"]["high"]))
            red_mask = cv2.bitwise_or(red1_mask, red2_mask)
            
            green_mask = cv2.inRange(hsv, np.array(hsv_ranges["Green"]["low"]), np.array(hsv_ranges["Green"]["high"]))
            blue_mask = cv2.inRange(hsv, np.array(hsv_ranges["Blue"]["low"]), np.array(hsv_ranges["Blue"]["high"]))

            # Clean masks using opening morphology
            kernel = np.ones((5,5), np.uint8)
            red_mask = cv2.morphologyEx(red_mask, cv2.MORPH_OPEN, kernel)
            green_mask = cv2.morphologyEx(green_mask, cv2.MORPH_OPEN, kernel)
            blue_mask = cv2.morphologyEx(blue_mask, cv2.MORPH_OPEN, kernel)

            # Calculate area of detected pixels
            red_area = int(np.sum(red_mask > 0))
            green_area = int(np.sum(green_mask > 0))
            blue_area = int(np.sum(blue_mask > 0))

            # Classification logic
            detected_color = "Idle"
            max_area = 0
            bin_code = 0
            active_mask = None

            areas = {"Red": red_area, "Green": green_area, "Blue": blue_area}
            best_color = max(areas, key=areas.get)
            
            if areas[best_color] >= args.min_area:
                detected_color = best_color
                max_area = areas[best_color]
                if best_color == "Red":
                    bin_code = 1  # 01
                    active_mask = red_mask
                elif best_color == "Green":
                    bin_code = 2  # 10
                    active_mask = green_mask
                elif best_color == "Blue":
                    bin_code = 3  # 11
                    active_mask = blue_mask

            # Send decision code to GPIO
            signaller.write_code(bin_code)

            # Draw visual feedback overlay
            display_frame = frame.copy()
            overlay_color = (128, 128, 128)
            if detected_color == "Red":
                overlay_color = (0, 0, 255)
            elif detected_color == "Green":
                overlay_color = (0, 255, 0)
            elif detected_color == "Blue":
                overlay_color = (255, 0, 0)

            # Find contours to draw bounding box
            if active_mask is not None:
                contours, _ = cv2.findContours(active_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                if contours:
                    largest_contour = max(contours, key=cv2.contourArea)
                    x, y, w, h = cv2.boundingRect(largest_contour)
                    cv2.rectangle(display_frame, (x, y), (x + w, y + h), overlay_color, 3)
                    cv2.putText(display_frame, f"{detected_color} ({max_area} px)", (x, y - 10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, overlay_color, 2)

            # Draw status bar
            cv2.rectangle(display_frame, (0, 0), (args.width, 50), (30, 30, 30), -1)
            status_text = f"STATE: {detected_color.upper()} | CODE: {bin_code:02b} | Pin B1B0={bin_code:02b}"
            if bin_code > 0:
                status_text += " | STROBE=HIGH"
            else:
                status_text += " | STROBE=LOW"
            cv2.putText(display_frame, status_text, (15, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (240, 240, 240), 2)
            
            # Show live preview
            cv2.imshow("Recycling Sorter Live", display_frame)

            # If calibrating, show the mask corresponding to the selected calibration target
            if args.calibrate:
                selected_colors = ["Red1", "Red2", "Green", "Blue"]
                sel_color = selected_colors[cv2.getTrackbarPos("Color Select", "Calibration Panel")]
                
                if sel_color == "Red1":
                    cal_mask = red1_mask
                elif sel_color == "Red2":
                    cal_mask = red2_mask
                elif sel_color == "Green":
                    cal_mask = green_mask
                elif sel_color == "Blue":
                    cal_mask = blue_mask
                
                cv2.imshow("Calibration Mask Preview", cal_mask)

            # Check key presses (exit on 'q' or Esc)
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q') or key == 27:
                break

    except KeyboardInterrupt:
        print("\nKeyboard Interrupt. Shutting down...")
    finally:
        print("Cleaning up camera capture and GPIO lines...")
        cap.release()
        cv2.destroyAllWindows()
        signaller.cleanup()
        print("Shutdown complete.")


if __name__ == "__main__":
    main()
