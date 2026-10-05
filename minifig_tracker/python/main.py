"""
minifig_tracker - Linux side (Phase 1)

Subscribes to the laptop's YOLO detections for the GREEN minifig over MQTT
and shows the minifig's position as a single dot on the 8x13 LED matrix.

Data flow:
    laptop (detect_live.py) --MQTT--> this script --Bridge--> sketch.ino --> LEDs

All MQTT, JSON parsing, and "which LED?" decisions happen here.
The sketch just lights whatever (row, col) we tell it to.
"""
import json
import threading
import time

import paho.mqtt.client as mqtt
from arduino.app_utils import App, Bridge

# ---------- Settings ----------
BROKER = "test.mosquitto.org"
PORT = 1883
TOPIC_GREEN = "ME193/ceci/green"

# LED matrix size (8 rows x 13 columns, from the Arduino_LED_Matrix library docs)
MATRIX_ROWS = 8
MATRIX_COLS = 13

# ---------- Shared state ----------
# The MQTT callback runs on paho's background thread, but we make all Bridge
# calls from the App loop. The callback only stores the newest message here,
# and the lock stops both threads touching it at the same time.
latest_msg = None
latest_lock = threading.Lock()

# What the matrix is currently showing: (row, col), or None when blank.
# Used to avoid re-sending the same command 10 times per second.
shown = "unset"  # forces the first real message to be sent


def scale_to_cell(x, y):
    """Map normalized camera coords (0-1) to a matrix (row, col).

    x = 0 is the left edge of the camera image -> column 0 (left of matrix).
    y = 0 is the top edge of the camera image  -> row 0 (top of matrix).
    int(x * 13) gives 0..12 for x in [0, 1); clamping handles x = 1.0 exactly
    and any slightly out-of-range values.
    """
    col = min(max(int(x * MATRIX_COLS), 0), MATRIX_COLS - 1)
    row = min(max(int(y * MATRIX_ROWS), 0), MATRIX_ROWS - 1)
    return row, col


# ---------- MQTT callbacks (run on paho's network thread) ----------
def on_connect(client, userdata, flags, reason_code, properties):
    print(f"MQTT connected ({reason_code}), subscribing to {TOPIC_GREEN}", flush=True)
    # Subscribing here (not once at startup) means we re-subscribe
    # automatically if the connection drops and reconnects.
    client.subscribe(TOPIC_GREEN)


def on_message(client, userdata, msg):
    global latest_msg
    try:
        data = json.loads(msg.payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        print(f"Ignoring bad payload: {msg.payload!r}", flush=True)
        return
    with latest_lock:
        latest_msg = data


# ---------- App loop (runs repeatedly on the main thread) ----------
def loop():
    global latest_msg, shown

    # Grab the newest message (if any) and mark it as handled.
    with latest_lock:
        data = latest_msg
        latest_msg = None

    if data is None:
        time.sleep(0.02)  # nothing new; don't spin the CPU
        return

    # Decide what the matrix should show.
    if data.get("detected") is True and "x" in data and "y" in data:
        try:
            target = scale_to_cell(float(data["x"]), float(data["y"]))
        except (TypeError, ValueError):
            print(f"Ignoring message with bad x/y: {data}", flush=True)
            return
    else:
        target = None  # detected is false (or message incomplete) -> blank

    # Only talk to the MCU when the picture actually changes.
    if target == shown:
        return

    if target is None:
        Bridge.call("clear_dot")
        print("Not detected -> cleared matrix", flush=True)
    else:
        row, col = target
        Bridge.call("show_dot", row, col)
        print(f"x={data['x']:.2f} y={data['y']:.2f} -> row {row}, col {col}", flush=True)
    shown = target


# ---------- Start up ----------
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.on_connect = on_connect
client.on_message = on_message
# connect_async + loop_start: connects in the background and keeps retrying,
# so the app doesn't crash if Wi-Fi isn't ready the moment it starts.
client.connect_async(BROKER, PORT)
client.loop_start()

try:
    App.run(user_loop=loop)  # required: starts the Bridge and calls loop() forever
finally:
    # App.run() exits via SystemExit on stop, so cleanup must live in finally
    # (see "Clean shutdown" in UNOQKNOWLEDGE.md).
    client.loop_stop()
    client.disconnect()
