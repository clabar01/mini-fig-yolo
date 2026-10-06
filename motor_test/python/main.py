import time

from arduino.app_utils import App, Bridge, Logger

logger = Logger("motor_test")

TEST_SPEED = 60  # -100..100; TT motors may not turn below ~30-40

# (label, speed, seconds)
STEPS = [
    ("forward", TEST_SPEED, 1.0),
    ("stop", 0, 1.0),
    ("backward", -TEST_SPEED, 1.0),
    ("stop", 0, 0.0),
]

done = False


def loop():
    global done
    if done:
        time.sleep(1)
        return
    time.sleep(3)  # let the sketch start and give you time to lift the car
    for label, speed, seconds in STEPS:
        logger.info(f"{label}: set_speed({speed})")
        Bridge.call("set_speed", speed)
        time.sleep(seconds)
    logger.info("Test finished. Restart the app to run it again.")
    done = True


try:
    App.run(user_loop=loop)
finally:
    try:
        Bridge.call("set_speed", 0)
    except Exception as e:
        logger.warning(f"Could not stop motors: {e}")
