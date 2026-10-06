// motor_test: same motor driver as minifig_tracker, exposed as "set_speed".
// python/main.py runs: forward 1 s, stop, backward 1 s, stop.
// Keep the motor section in sync with minifig_tracker/sketch/sketch.ino.

#include <Arduino_RouterBridge.h>

// --- Motors: Cytron Maker Drive (MX1508), M1 on D9/D10, M2 on D7/D8 ---------
//
// Each channel uses ONE PWM pin and ONE plain digital pin ("drive/brake" mode):
//   forward: A high-ish, B low      reverse: A low, B high-ish
// The non-PWM pin is held at a fixed level and the PWM pin's duty is chosen so
// the motor is driven for `duty` of the time and braked (both inputs equal) for
// the rest. Only one pin per channel needs PWM, and a pin is never switched
// between analogWrite and digitalWrite (in this core analogWrite muxes the pin
// to its timer, and digitalWrite afterwards does not mux it back).
//
// PWM on the UNO Q (arduino:zephyr 1.0.0 variant overlay, 500 Hz):
//   D9  TIM4_CH3   ~ on header      D10 TIM4_CH4   ~ on header
//   D8  TIM3_CH1   no ~, but mapped D7  TIM8_CH4N  no ~, complementary output
// M2's PWM goes on D8 so D7 (the odd complementary channel) is just a GPIO.
struct Motor {
  pin_size_t pin_a;
  pin_size_t pin_b;
  bool pwm_on_a;  // true: PWM on pin_a, digital on pin_b; false: the reverse
  bool invert;    // flip if this motor spins the wrong way when wired
};

static const Motor MOTOR_1 = {9, 10, true, false};
static const Motor MOTOR_2 = {7, 8, false, false};

static void motor_init(const Motor &m) {
  pin_size_t dig = m.pwm_on_a ? m.pin_b : m.pin_a;
  pin_size_t pwm = m.pwm_on_a ? m.pin_a : m.pin_b;
  pinMode(dig, OUTPUT);
  digitalWrite(dig, LOW);
  analogWrite(pwm, 0);  // both low: coast
}

// speed in -100..100. 0 leaves both inputs low (coast).
static void motor_set(const Motor &m, int speed) {
  if (m.invert) speed = -speed;
  bool forward = speed > 0;
  int duty = map(abs(speed), 0, 100, 0, 255);

  if (m.pwm_on_a) {
    // Forward: B low, A PWM duty.  Reverse: B high, A low for `duty`.
    digitalWrite(m.pin_b, forward || speed == 0 ? LOW : HIGH);
    analogWrite(m.pin_a, forward || speed == 0 ? duty : 255 - duty);
  } else {
    // Forward: A high, B low for `duty`.  Reverse: A low, B PWM duty.
    digitalWrite(m.pin_a, forward ? HIGH : LOW);
    analogWrite(m.pin_b, forward ? 255 - duty : duty);
  }
}

void set_speed(int speed) {
  speed = constrain(speed, -100, 100);
  motor_set(MOTOR_1, speed);
  motor_set(MOTOR_2, speed);
}

void setup() {
  motor_init(MOTOR_1);
  motor_init(MOTOR_2);

  Bridge.begin();
  Bridge.provide("set_speed", set_speed);
}

void loop() {
  delay(10);
}
