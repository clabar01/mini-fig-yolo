# 🟢 Minifig Tracker

Subscribes to `ME193/ceci/green` on `broker.hivemq.com` and lights one pixel on the
8×13 LED matrix at the scaled `x`/`y` position. Clears the matrix when `detected` is false.

Expected payload (JSON):

```json
{"x": 0.5, "y": 0.5, "detected": true, "width": 640, "height": 480, "conf": 0.9}
```

`x`/`y` are normalized 0..1; `x` is scaled to columns `0..12`, `y` to rows `0..7`
(`y = 0` is the top row). `width`, `height` and `conf` are ignored.
