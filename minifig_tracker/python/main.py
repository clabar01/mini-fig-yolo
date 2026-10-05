import json

import paho.mqtt.client as mqtt

from arduino.app_utils import App, Bridge, Logger

logger = Logger("minifig_tracker")

MQTT_HOST = "broker.hivemq.com"
MQTT_PORT = 1883
MQTT_TOPIC = "ME193/ceci/green"

# Range of the incoming x/y values (normalized by the detector). x in [0, X_MAX],
# y in [0, Y_MAX], with y = 0 at the top. Adjust to match the publisher.
X_MAX = 1.0
Y_MAX = 1.0

# LED matrix size, from Arduino_LED_Matrix.h (canvasWidth x canvasHeight).
MATRIX_COLS = 13
MATRIX_ROWS = 8

last_cell = None  # (col, row) currently shown, or None when cleared


def scale(value: float, max_value: float, cells: int) -> int:
    """Map value in [0, max_value] to a cell index in [0, cells - 1]."""
    idx = int(value / max_value * cells)
    return max(0, min(cells - 1, idx))


def show(cell) -> str:
    """Send the dot (or a clear) to the MCU, only when it changes.

    Returns a description of what was sent, for logging.
    """
    global last_cell
    if cell == last_cell:
        return "nothing (unchanged)"
    try:
        if cell is None:
            Bridge.call("clear_matrix")
            sent = "clear_matrix()"
        else:
            Bridge.call("show_dot", cell[0], cell[1])
            sent = f"show_dot({cell[0]}, {cell[1]})"
        last_cell = cell
        return sent
    except Exception as e:
        logger.warning(f"Bridge call failed: {e}")
        return "nothing (Bridge call failed)"


def on_connect(client, userdata, flags, reason_code, properties):
    logger.info(f"Connected to {MQTT_HOST} ({reason_code}); subscribing to {MQTT_TOPIC}")
    client.subscribe(MQTT_TOPIC)


def on_message(client, userdata, msg):
    try:
        data = json.loads(msg.payload)
    except ValueError:
        logger.warning(f"Ignoring non-JSON payload: {msg.payload[:100]!r}")
        return

    if not data.get("detected", False):
        sent = show(None)
        logger.info(f"detected=false -> sent {sent}")
        return

    try:
        col = scale(float(data["x"]), X_MAX, MATRIX_COLS)
        row = scale(float(data["y"]), Y_MAX, MATRIX_ROWS)
    except (KeyError, TypeError, ValueError):
        logger.warning(f"Missing/invalid x or y: {data}")
        return
    sent = show((col, row))
    logger.info(f"x={data['x']!r} y={data['y']!r} -> col={col} row={row} -> sent {sent}")


client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.on_connect = on_connect
client.on_message = on_message
client.connect_async(MQTT_HOST, MQTT_PORT, keepalive=30)
client.loop_start()  # background thread; reconnects automatically

try:
    App.run()
finally:
    client.loop_stop()
    client.disconnect()
