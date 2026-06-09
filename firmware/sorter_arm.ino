/**
 * IoT Recycling Sorter - Arduino Robotic Arm Firmware
 * 
 * Drives 4 servos (Base, Shoulder, Elbow, Gripper) to pick up classified
 * items from the feed area and place them into one of three bins.
 * 
 * Decodes the 2-bit binary command from the Jetson GPIO lines, utilizing 
 * an optional Strobe/Data-Valid handshake. 
 * Includes linear joint interpolation for smooth, low-jerk movement,
 * and an emergency stop (E-stop) button detection system.
 */

#include <Servo.h>

// --- Pin Definitions ---
// Servos (PWM Pins)
const int PIN_SERVO_BASE     = 9;
const int PIN_SERVO_SHOULDER = 10;
const int PIN_SERVO_ELBOW    = 11;
const int PIN_SERVO_GRIPPER  = 6;

// Jetson GPIO Signals (Logic Level Shifted 3.3V -> 5V)
const int PIN_B0     = 2;  // Bit 0 (LSB)
const int PIN_B1     = 3;  // Bit 1 (MSB)
const int PIN_STROBE = 4;  // Data-Valid Strobe

// Safety & User Interface
const int PIN_ESTOP       = 7;   // Emergency Stop (active low with internal pullup)
const int PIN_STATUS_LED  = 13;  // Onboard LED for status feedback

// --- Configuration Options ---
const bool USE_STROBE     = true; // Verify data-valid via strobe line before decoding
const int MOVE_DELAY_MS   = 15;   // Milliseconds delay between step increments (higher = slower motion)

// --- Servo Angle Definitions ---
// Structure representing a target coordinate frame for the arm's joints
struct ArmPosture {
  int base;
  int shoulder;
  int elbow;
  int gripper;
};

// Home/Idle Posture
const ArmPosture POSTURE_HOME = { 90, 90, 90, 40 }; // Gripper open at home

// Pick Postures
const ArmPosture POSTURE_PICK_APPROACH = { 90, 60, 100, 40 }; // Hovering above pickup point
const ArmPosture POSTURE_PICK_CONTACT  = { 90, 45, 120, 40 }; // Lowered down, ready to clamp
const ArmPosture POSTURE_PICK_CLAMP    = { 90, 45, 120, 130 }; // Clamped around object
const ArmPosture POSTURE_PICK_LIFT     = { 90, 80, 80,  130 }; // Lifted clear off the surface

// Drop Postures for each Bin: { Base, Shoulder, Elbow, Gripper (open) }
const ArmPosture POSTURES_BIN_DROP[] = {
  { 90, 90, 90, 40 },   // Dummy / Bin 0 (Idle placeholder)
  { 30, 70, 90, 40 },   // Bin 1 (Red / Code 01)
  { 150, 70, 90, 40 },  // Bin 2 (Green / Code 10)
  { 180, 80, 100, 40 }  // Bin 3 (Blue / Code 11)
};

// --- Global Objects & State Variables ---
Servo baseServo;
Servo shoulderServo;
Servo elbowServo;
Servo gripperServo;

// Tracking actual current angles of the joints (to support incremental movement)
ArmPosture currentPosture = POSTURE_HOME;

// Sorter states
enum SorterState {
  STATE_IDLE,
  STATE_PICKING,
  STATE_TRANSPORTING,
  STATE_DROPPING,
  STATE_RETURNING,
  STATE_WAIT_FOR_RESET
};

SorterState currentState = STATE_IDLE;
int targetBin = 0; // Decoded bin ID (1, 2, or 3)

// --- Function Prototypes ---
void checkEStop();
void moveJointsSmoothly(const ArmPosture& target, int stepDelay);
int readBinSignal();
void triggerEStop();

void setup() {
  Serial.begin(115200);
  Serial.println(F("--- IoT Recycling Sorter Starting ---"));

  // Pins Setup
  pinMode(PIN_B0, INPUT);
  pinMode(PIN_B1, INPUT);
  pinMode(PIN_STROBE, INPUT);
  
  pinMode(PIN_ESTOP, INPUT_PULLUP);
  pinMode(PIN_STATUS_LED, OUTPUT);
  digitalWrite(PIN_STATUS_LED, LOW);

  // Attach servos
  baseServo.attach(PIN_SERVO_BASE);
  shoulderServo.attach(PIN_SERVO_SHOULDER);
  elbowServo.attach(PIN_SERVO_ELBOW);
  gripperServo.attach(PIN_SERVO_GRIPPER);

  // Move arm to home position instantly on startup
  baseServo.write(POSTURE_HOME.base);
  shoulderServo.write(POSTURE_HOME.shoulder);
  elbowServo.write(POSTURE_HOME.elbow);
  gripperServo.write(POSTURE_HOME.gripper);
  currentPosture = POSTURE_HOME;

  Serial.println(F("System calibrated. Arm in HOME position. Ready."));
}

void loop() {
  // Always inspect safety E-Stop button first
  checkEStop();

  switch (currentState) {
    case STATE_IDLE: {
      digitalWrite(PIN_STATUS_LED, LOW);
      int signalCode = readBinSignal();
      
      if (signalCode > 0 && signalCode <= 3) {
        targetBin = signalCode;
        Serial.print(F("Signal Received! Target Bin: "));
        Serial.println(targetBin);
        currentState = STATE_PICKING;
      }
      delay(50); // Sample rate around 20 Hz
      break;
    }

    case STATE_PICKING: {
      digitalWrite(PIN_STATUS_LED, HIGH);
      Serial.println(F("Executing picking sequence..."));

      // 1. Move to approach hover
      moveJointsSmoothly(POSTURE_PICK_APPROACH, MOVE_DELAY_MS);
      // 2. Lower to make contact
      moveJointsSmoothly(POSTURE_PICK_CONTACT, MOVE_DELAY_MS);
      // 3. Close gripper around item
      moveJointsSmoothly(POSTURE_PICK_CLAMP, MOVE_DELAY_MS + 5); 
      delay(500); // Allow gripper to securely squeeze item
      // 4. Lift item off the platform
      moveJointsSmoothly(POSTURE_PICK_LIFT, MOVE_DELAY_MS);

      currentState = STATE_TRANSPORTING;
      break;
    }

    case STATE_TRANSPORTING: {
      Serial.print(F("Transporting item to Bin "));
      Serial.println(targetBin);

      // Look up target angles for the corresponding bin
      ArmPosture dropApproach = POSTURES_BIN_DROP[targetBin];
      // Gripper should remain closed during transportation
      dropApproach.gripper = POSTURE_PICK_CLAMP.gripper; 

      moveJointsSmoothly(dropApproach, MOVE_DELAY_MS);
      currentState = STATE_DROPPING;
      break;
    }

    case STATE_DROPPING: {
      Serial.println(F("Dropping item..."));
      
      // Look up drop angles (gripper will open)
      ArmPosture dropAction = POSTURES_BIN_DROP[targetBin];
      moveJointsSmoothly(dropAction, MOVE_DELAY_MS);
      
      delay(500); // Wait for gravity to pull the item down
      currentState = STATE_RETURNING;
      break;
    }

    case STATE_RETURNING: {
      Serial.println(F("Returning arm to home position..."));
      
      // Move back home safely
      moveJointsSmoothly(POSTURE_HOME, MOVE_DELAY_MS);
      
      Serial.println(F("Sequence complete. Waiting for Jetson signal to clear..."));
      currentState = STATE_WAIT_FOR_RESET;
      break;
    }

    case STATE_WAIT_FOR_RESET: {
      // Prevent immediate re-triggering if the Jetson is still outputting the same color
      int signalCode = readBinSignal();
      if (signalCode == 0) {
        Serial.println(F("Signal cleared. Ready for next item."));
        currentState = STATE_IDLE;
      }
      delay(50);
      break;
    }
  }
}

/**
 * Polls the signal pins and returns the decoded binary bin ID (0 to 3).
 * Uses strobe configuration if enabled.
 */
int readBinSignal() {
  if (USE_STROBE) {
    int strobe = digitalRead(PIN_STROBE);
    if (strobe == LOW) {
      return 0; // Signal is invalid/idle
    }
  }

  // Read data lines
  int b0 = digitalRead(PIN_B0);
  int b1 = digitalRead(PIN_B1);

  // Assemble 2-bit binary integer
  int decodedVal = (b1 << 1) | b0;
  return decodedVal;
}

/**
 * Iteratively steps all servo positions concurrently to avoid sudden jerks.
 */
void moveJointsSmoothly(const ArmPosture& target, int stepDelay) {
  while (currentPosture.base != target.base || 
         currentPosture.shoulder != target.shoulder || 
         currentPosture.elbow != target.elbow || 
         currentPosture.gripper != target.gripper) {
    
    // Check E-Stop button at every step of motion
    checkEStop();

    // Increment or decrement joint angles towards target
    if (currentPosture.base < target.base) currentPosture.base++;
    else if (currentPosture.base > target.base) currentPosture.base--;

    if (currentPosture.shoulder < target.shoulder) currentPosture.shoulder++;
    else if (currentPosture.shoulder > target.shoulder) currentPosture.shoulder--;

    if (currentPosture.elbow < target.elbow) currentPosture.elbow++;
    else if (currentPosture.elbow > target.elbow) currentPosture.elbow--;

    if (currentPosture.gripper < target.gripper) currentPosture.gripper++;
    else if (currentPosture.gripper > target.gripper) currentPosture.gripper--;

    // Output values to servos
    baseServo.write(currentPosture.base);
    shoulderServo.write(currentPosture.shoulder);
    elbowServo.write(currentPosture.elbow);
    gripperServo.write(currentPosture.gripper);

    delay(stepDelay);
  }
}

/**
 * Checks the E-Stop pin and halts all routines if it is pulled LOW (active-low button).
 */
void checkEStop() {
  if (digitalRead(PIN_ESTOP) == LOW) {
    triggerEStop();
  }
}

/**
 * Emergency Shutdown routine. Detaches all servos to cut motor current, preventing
 * further movement, and enters a lock state that requires a physical reset.
 */
void triggerEStop() {
  // Turn off PWM signal to all servos immediately, letting them go limp
  baseServo.detach();
  shoulderServo.detach();
  elbowServo.detach();
  gripperServo.detach();

  Serial.println(F("!!! EMERGENCY STOP DETECTED !!!"));
  Serial.println(F("Servos detached. System halted. Reset Arduino to recover."));

  // Blink status LED rapidly to indicate panic state
  while (true) {
    digitalWrite(PIN_STATUS_LED, HIGH);
    delay(100);
    digitalWrite(PIN_STATUS_LED, LOW);
    delay(100);
  }
}
