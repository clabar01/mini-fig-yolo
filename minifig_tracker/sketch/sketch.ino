// minifig_tracker - MCU side (Phase 1)
//
// This sketch only owns the LED matrix. It does NOT know anything about
// MQTT, JSON, or the camera: the Python side decides which LED to light
// and calls the functions below over the Bridge.
//
// Matrix size comes from the Arduino_LED_Matrix library / official
// "LED Matrix Frame" example: 8 rows x 13 columns = 104 LEDs.
// The frame buffer is row-major: index = row * 13 + col,
// with row 0 at the top and col 0 at the left.

#include <Arduino_RouterBridge.h>
#include <Arduino_LED_Matrix.h>

Arduino_LED_Matrix matrix;

const uint8_t FRAME_ROWS = 8;
const uint8_t FRAME_COLS = 13;
const uint8_t FRAME_SIZE = FRAME_ROWS * FRAME_COLS;  // 104

const uint8_t DOT_BRIGHTNESS = 7;  // max brightness with 3 grayscale bits (0-7)

uint8_t frame[FRAME_SIZE] = {0};   // what the matrix shows; all zeros = blank

// Called from Python: light exactly one LED at (row, col), turn all others off.
void show_dot(int row, int col) {
    // Ignore out-of-range values instead of writing past the buffer.
    if (row < 0 || row >= FRAME_ROWS || col < 0 || col >= FRAME_COLS) {
        return;
    }
    memset(frame, 0, FRAME_SIZE);
    frame[row * FRAME_COLS + col] = DOT_BRIGHTNESS;
}

// Called from Python: turn every LED off.
void clear_dot() {
    memset(frame, 0, FRAME_SIZE);
}

void setup() {
    matrix.begin();
    matrix.setGrayscaleBits(3);  // brightness values 0-7
    matrix.clear();

    Bridge.begin();              // required for any Bridge communication
    Bridge.provide("show_dot", show_dot);
    Bridge.provide("clear_dot", clear_dot);
}

void loop() {
    // Same pattern as Arduino's official LED matrix example: the Bridge
    // handlers only edit the buffer, and loop() pushes it to the matrix.
    matrix.draw(frame);
    delay(10);
}
