"""
Live minifig detector.

Opens the laptop webcam, runs the trained YOLOv8 model on each frame,
draws a box and centroid for each minifig, and publishes each minifig's
normalized position (0 to 1) over MQTT as JSON.

Run from the project folder with the venv active:
    python detect_live.py
Press q in the video window to quit.
"""
import json
import time

import cv2
import paho.mqtt.client as mqtt
from ultralytics import YOLO

# ---------- Settings ----------
MODEL_PATH = "models/best.pt"
CAMERA_INDEX = 0          # try 1 if it opens your iPhone camera instead
CONF_THRESHOLD = 0.5      # ignore detections below this confidence
PUBLISH_HZ = 10           # MQTT messages per second, per topic

BROKER = "broker.hivemq.com"
PORT = 1883
TEAM = "ceci"           # change to something unique to your team
TOPICS = {
    "green-minifig": f"ME193/{TEAM}/green",
    "blue-minifig": f"ME193/{TEAM}/blue",
}
COLORS = {                # OpenCV uses BGR, not RGB
    "green-minifig": (0, 200, 0),
    "blue-minifig": (255, 80, 0),
}


def best_detection_per_class(result, names):
    """Keep only the highest-confidence box for each class we care about."""
    best = {}
    for box in result.boxes:
        conf = float(box.conf[0])
        if conf < CONF_THRESHOLD:
            continue
        name = names[int(box.cls[0])]
        if name not in TOPICS:
            continue
        if name not in best or conf > best[name][0]:
            best[name] = (conf, box.xyxy[0].tolist())
    return best


def main():
    model = YOLO(MODEL_PATH)
    names = model.names

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.connect(BROKER, PORT)
    client.loop_start()

    cap = cv2.VideoCapture(CAMERA_INDEX)
    if not cap.isOpened():
        raise SystemExit("Could not open webcam. Check camera permissions "
                         "for VS Code / Terminal in System Settings.")

    last_pub = 0.0
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            h, w = frame.shape[:2]

            result = model(frame, verbose=False)[0]
            best = best_detection_per_class(result, names)

            # Vertical line per car marking its stop target (must match TARGET_X in each sketch)
            for name, line_x in {"green-minifig": 0.2, "blue-minifig": 0.8}.items():
                px = int(line_x * w)
                cv2.line(frame, (px, 0), (px, h), COLORS[name], 2)

            messages = {}
            for name, topic in TOPICS.items():
                if name in best:
                    conf, (x1, y1, x2, y2) = best[name]
                    cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
                    msg = {
                        "detected": True,
                        "x": round(cx / w, 3),
                        "y": round(cy / h, 3),
                        "width": round((x2 - x1) / w, 3),
                        "height": round((y2 - y1) / h, 3),
                        "conf": round(conf, 2),
                    }
                    color = COLORS[name]
                    cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), color, 2)
                    cv2.circle(frame, (int(cx), int(cy)), 5, color, -1)
                    cv2.putText(frame, f"{name} x={msg['x']:.2f} y={msg['y']:.2f}",
                                (int(x1), max(int(y1) - 8, 15)),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
                else:
                    msg = {"detected": False}
                messages[topic] = msg

            now = time.time()
            if now - last_pub >= 1 / PUBLISH_HZ:
                for topic, msg in messages.items():
                    client.publish(topic, json.dumps(msg))
                last_pub = now

            cv2.imshow("Minifig detector (q to quit)", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    finally:
        cap.release()
        cv2.destroyAllWindows()
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()
