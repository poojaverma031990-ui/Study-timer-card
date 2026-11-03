"""Host-side behavior tests; not a replacement for hardware testing."""
import runpy
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

FIRMWARE = Path(__file__).resolve().parents[1] / 'firmware/main.py'

class StopSimulation(Exception):
    pass

class FirmwareTest(unittest.TestCase):
    def simulate(self, events, end):
        clock = [0.0]
        frames, tones, outputs = [], [], {}
        board = types.SimpleNamespace(**{f'GP{i}': i for i in [4,5,10,14,15,16,17]})
        class Pin:
            def __init__(self, pin):
                self.pin = pin
                self.out = None
                self._value = True
                outputs[pin] = self
            def switch_to_input(self, pull):
                pass
            def switch_to_output(self, value):
                self.out = True
                self._value = value
            @property
            def value(self):
                if self.out:
                    return self._value
                return not any(pin == self.pin and a <= clock[0] < b for pin,a,b in events)
            @value.setter
            def value(self, value):
                self._value = value
        class Display:
            def __init__(self, *a, **k):
                self.lines = []
            def fill(self, color):
                self.lines = []
            def text(self, text, *a):
                self.lines.append(text)
            def show(self):
                frames.append((clock[0], list(self.lines)))
        class PWM:
            def __init__(self, *a, **k):
                self.last = None
                self.duty_cycle = 0
            @property
            def duty_cycle(self):
                return self.last
            @duty_cycle.setter
            def duty_cycle(self, v):
                if v != self.last:
                    tones.append((clock[0],v))
                self.last = v
        def sleep(dt):
            clock[0] += dt
            if clock[0] >= end:
                raise StopSimulation()
        modules = {'board': board, 'time': types.SimpleNamespace(monotonic=lambda:clock[0],sleep=sleep),
                   'busio': types.SimpleNamespace(I2C=lambda **k:None),
                   'digitalio':types.SimpleNamespace(DigitalInOut=Pin,Pull=types.SimpleNamespace(UP=1)),
                   'pwmio':types.SimpleNamespace(PWMOut=PWM),
                   'adafruit_ssd1306':types.SimpleNamespace(SSD1306_I2C=Display)}
        with patch.dict(sys.modules, modules):
            with self.assertRaises(StopSimulation):
                runpy.run_path(str(FIRMWARE))
        return frames, tones, outputs

    def test_complete_countdown_and_alarm(self):
        frames,tones,outputs = self.simulate([(14,.1,.3)], 1504)
        self.assertEqual(frames[0][1], ['STUDY TIMER','Press START'])
        self.assertIn(['STUDY TIMER','25:00'], [f[1] for f in frames])
        self.assertIn(['STUDY TIMER','00:01'], [f[1] for f in frames])
        self.assertIn(['BREAK! Done!','RESET to restart'], [f[1] for f in frames])
        self.assertEqual(len([v for t,v in tones if v]), 3)
        for index,(t,v) in enumerate(tones):
            if v:
                self.assertAlmostEqual(tones[index+1][0]-t, .5, delta=.02)
        self.assertFalse(outputs[16].value)  # finally cleanup
        self.assertFalse(outputs[17].value)

    def test_reset_interrupts_countdown(self):
        frames,tones,_ = self.simulate([(14,.1,.3),(15,2,2.2)], 4)
        self.assertEqual(frames[-1][1],['STUDY TIMER','Press START'])
        self.assertFalse(any(v for t,v in tones))

    def test_reset_interrupts_alarm(self):
        frames,tones,_ = self.simulate([(14,.1,.3),(15,1500.3,1500.5)],1502)
        self.assertEqual(frames[-1][1],['STUDY TIMER','Press START'])
        self.assertEqual(len([v for t,v in tones if v]),1)

    def test_sub_debounce_bounce_ignored(self):
        frames,_,_ = self.simulate([(14,.1,.11)],1)
        self.assertEqual(len(frames),1)

if __name__ == '__main__':
    unittest.main()
