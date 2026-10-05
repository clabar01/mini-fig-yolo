// minifig_tracker: draws a single dot on the 8x13 LED matrix.
// Python owns MQTT and scaling; this sketch only exposes two Bridge providers:
//  - "show_dot"     (col, row) -> lights exactly one pixel
//  - "clear_matrix" ()         -> turns every pixel off

#include <Arduino_RouterBridge.h>
#include <Arduino_LED_Matrix.h>
#include <zephyr/kernel.h>

// Dimensions from Arduino_LED_Matrix.h (canvasWidth = 13, canvasHeight = 8).
static const int MATRIX_COLS = 13;
static const int MATRIX_ROWS = 8;
static const uint8_t DOT_BRIGHTNESS = 7;  // 3-bit grayscale: 0..7

Arduino_LED_Matrix matrix;

// Bridge providers run on a separate thread; serialize matrix writes.
K_MUTEX_DEFINE(matrix_mtx);

static uint8_t frame[MATRIX_ROWS * MATRIX_COLS];  // row-major, one byte per pixel

void show_dot(int col, int row) {
  if (col < 0 || col >= MATRIX_COLS || row < 0 || row >= MATRIX_ROWS) return;

  k_mutex_lock(&matrix_mtx, K_FOREVER);
  memset(frame, 0, sizeof(frame));
  frame[row * MATRIX_COLS + col] = DOT_BRIGHTNESS;
  matrix.draw(frame);
  k_mutex_unlock(&matrix_mtx);
}

void clear_matrix() {
  k_mutex_lock(&matrix_mtx, K_FOREVER);
  memset(frame, 0, sizeof(frame));
  matrix.draw(frame);
  k_mutex_unlock(&matrix_mtx);
}

void setup() {
  matrix.begin();
  matrix.setGrayscaleBits(3);
  matrix.clear();

  Bridge.begin();
  Bridge.provide("show_dot", show_dot);
  Bridge.provide("clear_matrix", clear_matrix);
}

void loop() {
  delay(10);
}
