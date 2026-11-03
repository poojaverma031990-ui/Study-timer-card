"""Study Timer: CircuitPython on RP2040; copy to CIRCUITPY as code.py.
Requires adafruit_ssd1306.mpy in lib/. Buttons active low, LEDs active high.
"""
import time
import board
import busio
import digitalio
import pwmio
import adafruit_ssd1306

DURATION = 25 * 60
DEBOUNCE = 0.03

i2c = busio.I2C(scl=board.GP5, sda=board.GP4)
oled = adafruit_ssd1306.SSD1306_I2C(128, 64, i2c, addr=0x3C)
buzzer = pwmio.PWMOut(board.GP10, frequency=2000, duty_cycle=0)


def output(pin):
    led = digitalio.DigitalInOut(pin)
    led.switch_to_output(value=False)
    return led


class Button:
    """Debounced press events; holding a button never repeats."""
    def __init__(self, pin):
        self.io = digitalio.DigitalInOut(pin)
        self.io.switch_to_input(pull=digitalio.Pull.UP)
        self.raw = self.io.value
        self.stable = self.raw
        self.changed = time.monotonic()

    def pressed(self, now):
        raw = self.io.value
        if raw != self.raw:
            self.raw = raw
            self.changed = now
        if raw != self.stable and now - self.changed >= DEBOUNCE:
            self.stable = raw
            return not raw
        return False


start = Button(board.GP14)
reset = Button(board.GP15)
red = output(board.GP16)
green = output(board.GP17)


def screen(top, bottom):
    oled.fill(0)
    oled.text(top, 16, 16, 1)
    oled.text(bottom, 16, 40, 1)
    oled.show()


state = "idle"
deadline = 0.0
alarm_start = 0.0
last_remaining = -1
screen("STUDY TIMER", "Press START")
try:
    while True:
        now = time.monotonic()
        start_pressed = start.pressed(now)
        reset_pressed = reset.pressed(now)
        if reset_pressed:
            state = "idle"
            buzzer.duty_cycle = 0
            red.value = green.value = False
            screen("STUDY TIMER", "Press START")
        elif start_pressed and state == "idle":
            state = "running"
            deadline = now + DURATION
            last_remaining = -1
            red.value = True
            green.value = False
        if state == "running":
            # A deadline avoids accumulating display/update latency each second.
            remaining = max(0, int(deadline - now + 0.999999))
            if remaining != last_remaining:
                screen("STUDY TIMER", "{:02d}:{:02d}".format(
                    remaining // 60, remaining % 60))
                last_remaining = remaining
            if now >= deadline:
                state = "done"
                alarm_start = now
                red.value = False
                green.value = True
                screen("BREAK! Done!", "RESET to restart")
        if state == "done":
            # Three 500 ms tones, separated by 500 ms; RESET stays responsive.
            phase = int((now - alarm_start) / 0.5)
            buzzer.duty_cycle = 32768 if phase in (0, 2, 4) else 0
        time.sleep(0.01)
finally:
    buzzer.duty_cycle = 0
    red.value = green.value = False
