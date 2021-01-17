# SPDX-FileCopyrightText: 2017 Scott Shawcroft, written for Adafruit Industries
# SPDX-FileCopyrightText: Copyright (c) 2020 Melissa LeBlanc-Williams for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
`adafruit_pyportal.peripherals`
================================================================================

A port of the PyPortal library intended to run on Blinka in CPython.

* Author(s): Melissa LeBlanc-Williams

Implementation Notes
--------------------

**Software and Dependencies:**

* Adafruit Blinka for supported boards:
  https://github.com/adafruit/Adafruit_Blinka/releases

"""

import os
import gc

try:
    import board
except AttributeError:
    pass
from digitalio import DigitalInOut
from adafruit_stmpe610 import Adafruit_STMPE610_SPI
import adafruit_focaltouch

__version__ = "0.0.0-auto.0"
__repo__ = "https://github.com/adafruit/Adafruit_Blinka_PyPortal.git"


class Peripherals:
    """Peripherals Helper Class for the PyPortal Library"""

    # pylint: disable=too-many-arguments
    def __init__(self, spi, display, touchscreen=None, audio_device=1, debug=False):
        self._display = display

        self._audio_device = audio_device
        self.touchscreen = touchscreen
        self._debug = debug
        if spi is not None:
            # Attempt to Init STMPE610
            if self.touchscreen is None:
                if debug:
                    print("Attempting to initialize STMPE610...")
                try:
                    chip_select = DigitalInOut(board.CE1)
                    self.touchscreen = Adafruit_STMPE610_SPI(spi, chip_select)
                except (RuntimeError, AttributeError, NameError):
                    if debug:
                        print("None Found")
            # Attempt to Init FocalTouch
            if self.touchscreen is None:
                if debug:
                    print("Attempting to initialize Focal Touch...")
                try:
                    i2c = board.I2C()
                    self.touchscreen = adafruit_focaltouch.Adafruit_FocalTouch(i2c)
                except Exception:  # pylint: disable=broad-except
                    if debug:
                        print("None Found")

        self.set_backlight(1.0)  # turn on backlight

        gc.collect()

    def set_backlight(self, val):
        """Adjust the TFT backlight.

        :param val: The backlight brightness. Use a value between ``0`` and ``1``, where ``0`` is
                    off, and ``1`` is 100% brightness.

        """
        val = max(0, min(1.0, val))
        self._display.auto_brightness = False
        self._display.brightness = val

    def play_file(self, file_name, wait_to_finish=True):
        """Play a wav file.

        :param str file_name: The name of the wav file to play on the speaker.
        """
        if self._debug:
            print("Playing audio file", file_name)

        os.system("aplay -Dhw:" + str(self._audio_device) + ",0 " + file_name)
        if not wait_to_finish:
            # To do: Add threading support
            print("Immediately returning not currently supported.")

    @staticmethod
    def sd_check():
        """Returns True if there is an SD card preset and False
        if there is no SD card. The _sdcard value is set in _init
        """
        return False

    @property
    def speaker_disable(self):
        """
        Enable or disable the speaker for power savings
        """
        return False

    @speaker_disable.setter
    def speaker_disable(self, value):
        pass
