"""
File: glow.py
Purpose:
    Controls RGB LED using simple HIGH / LOW (no PWM).
"""

import RPi.GPIO as GPIO

# Update pins according to your hardware
RED_PIN = 16
GREEN_PIN = 20
BLUE_PIN = 21


def init_led():
    GPIO.setmode(GPIO.BCM)

    GPIO.setup(RED_PIN, GPIO.OUT)
    GPIO.setup(GREEN_PIN, GPIO.OUT)
    GPIO.setup(BLUE_PIN, GPIO.OUT)

    # Initially turn OFF
    GPIO.output(RED_PIN, GPIO.LOW)
    GPIO.output(GREEN_PIN, GPIO.LOW)
    GPIO.output(BLUE_PIN, GPIO.LOW)


def control_led(r, g, b):
    """
    r, g, b values: 0–255
    Any non-zero value turns that color ON.
    """

    GPIO.output(RED_PIN, GPIO.HIGH if r > 0 else GPIO.LOW)
    GPIO.output(GREEN_PIN, GPIO.HIGH if g > 0 else GPIO.LOW)
    GPIO.output(BLUE_PIN, GPIO.HIGH if b > 0 else GPIO.LOW)


def cleanup_led():
    GPIO.cleanup()