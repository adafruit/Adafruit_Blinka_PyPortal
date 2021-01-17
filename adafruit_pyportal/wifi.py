# SPDX-FileCopyrightText: 2020 Melissa LeBlanc-Williams, written for Adafruit Industries
#
# SPDX-License-Identifier: Unlicense
"""
`adafruit_pyportal.wifi`
================================================================================

A port of the PyPortal library intended to run on Blinka in CPython.

* Author(s): Melissa LeBlanc-Williams

Implementation Notes
--------------------

**Software and Dependencies:**

* Adafruit Blinka for supported boards:
  https://github.com/adafruit/Adafruit_Blinka/releases

"""

import gc
import subprocess

try:
    import neopixel
except NotImplementedError:
    pass
import requests

__version__ = "0.0.0-auto.0"
__repo__ = "https://github.com/adafruit/Adafruit_Blinka_PyPortal.git"


class WiFi:
    """Class representing the Linux Network Connection, which always is on.

    :param status_neopixel: The pin for the status NeoPixel. Use ``board.NEOPIXEL`` for the on-board
                            NeoPixel. Defaults to ``None``, not the status LED
    """

    def __init__(self, *, status_neopixel=None):

        if status_neopixel:
            self.neopix = neopixel.NeoPixel(status_neopixel, 1, brightness=0.2)
        else:
            self.neopix = None
        self.neo_status(0)
        self.requests = requests

        gc.collect()

    def connect(self, ssid, password):
        """
        Connect to WiFi using the settings found in secrets.py
        """

    def neo_status(self, value):
        """The status NeoPixel.

        :param value: The color to change the NeoPixel.

        """
        if self.neopix:
            self.neopix.fill(value)

    @property
    def is_connected(self):
        """Return whether we are connected."""
        return True

    @property
    def ip_address(self):
        """Look up the IP address and return it"""
        return subprocess.check_output(
            "hostname -I | cut -d' ' -f1", shell=True
        ).decode("utf-8")

    @property
    def enabled(self):
        """Not currently disablable on the Linux"""
        return True
