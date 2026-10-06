# Minifig YOLO Cars

A YOLOv8 model running on a laptop finds a green and a blue LEGO minifig in the
webcam image. It publishes each minifig's position over MQTT to
`broker.hivemq.com` on the topics `ME193/ceci/green` and `ME193/ceci/blue`. Two
Arduino Uno Q cars each subscribe to one topic and drive forward or backward
until their minifig reaches its target line: green at x = 0.2 and blue at
x = 0.8. Here x is the minifig's horizontal position in the image, from 0 at the
left edge to 1 at the right.

## How the pieces connect

```
laptop webcam
   │  frames
   ▼
detect_live.py  (YOLOv8 on the laptop)
   │  JSON {"detected", "x", "y", "width", "height", "conf"}, 10 times per second
   ▼
MQTT broker: broker.hivemq.com:1883
   ├── ME193/ceci/green ──► green car (minifig_tracker_green)
   └── ME193/ceci/blue  ──► blue car  (minifig_tracker_blue)
```

On each car, the Python side (`python/main.py`) receives the MQTT messages and
runs a PD controller on `error = x − TARGET_X`. It sends motor speeds to the
sketch (`sketch/sketch.ino`) over the Uno Q's Bridge. The sketch drives the
motors and shows the minifig's position as a dot on the 8×13 LED matrix. A car
stops when the minifig is within 0.015 of its target, when the minifig isn't
detected, or when no message has arrived for 1 second.

## Files and folders

| Path | What it is |
|------|------------|
| `train.py` | Fine-tunes the pretrained `yolov8n.pt` on `dataset/` for 100 epochs at 640 px, on the Apple GPU (`mps`) with a CPU fallback. |
| `detect_live.py` | Runs the trained model on the webcam, draws each box, its center and the two target lines, and publishes positions over MQTT. Press `q` to quit. |
| `models/` | `best.pt`, the trained weights that `detect_live.py` loads. |
| `dataset/` | 95 labeled images in YOLOv8 format (67 train, 19 valid, 9 test) with two classes, `blue-minifig` and `green-minifig`. `data.yaml` describes the split. |
| `minifig_tracker_green/` | Arduino App Lab app for the green car (`COLOR = "green"`, `TARGET_X = 1 / 5`). |
| `minifig_tracker_blue/` | The same app for the blue car (`COLOR = "blue"`, `TARGET_X = 4 / 5`). |
| `motor_test/` | Wiring check app: drives forward for 1 s, stops, drives backward for 1 s, stops. |
| `yolov8n.pt` | Pretrained YOLOv8n weights that training starts from. |

Training writes its output (weights and plots such as `results.png`) to `runs/`,
which isn't tracked in git.

## Labeling and training

Roboflow was used only to label the images and export them in YOLOv8 format.
Training was done locally on the laptop with Ultralytics (`python train.py`).
The resulting `best.pt` was copied into `models/`.

## How to run

1. Activate the virtual environment from the repo folder:
   ```bash
   source .venv/bin/activate
   ```
   It needs `ultralytics`, `opencv-python` and `paho-mqtt`.
2. Start the detector:
   ```bash
   python detect_live.py
   ```
   If it opens the wrong camera, set `CAMERA_INDEX = 1` at the top of the file.
3. Power both cars. Each board runs its tracker app: `minifig_tracker_green` on
   the green car and `minifig_tracker_blue` on the blue car. If an app doesn't
   start on its own, open it in Arduino App Lab and press Run.
4. Put the minifigs in view of the webcam. Each car drives until its minifig
   lines up with the matching colored line in the video window.

## Hardware (per car)

- Arduino Uno Q
- Cytron Maker Drive motor driver (MX1508), powered from 5V and GND
- Two TT gearmotors, on driver channels M1 and M2

| Driver input | Uno Q pin | Use |
|--------------|-----------|-----|
| M1A | D9 | PWM |
| M1B | D10 | digital |
| M2A | D7 | digital |
| M2B | D8 | PWM |

Both motors get the same speed. If a motor spins the wrong way, flip its
`invert` flag in `sketch/sketch.ino` (and in `motor_test`).
