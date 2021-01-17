# SPDX-FileCopyrightText: 2020 Melissa LeBlanc-Williams, written for Adafruit Industries
#
# SPDX-License-Identifier: Unlicense
"""
`adafruit_pyportal.graphics`
================================================================================

A port of the PyPortal library intended to run on Blinka in CPython.

* Author(s): Melissa LeBlanc-Williams

Implementation Notes
--------------------

**Software and Dependencies:**

* Adafruit Blinka for supported boards:
  https://github.com/adafruit/Adafruit_Blinka/releases

"""

try:
    import board

    DISPLAY_ARG_REQUIRED = False
except AttributeError:
    # okay to run Generic Linux
    DISPLAY_ARG_REQUIRED = True

import displayio
import adafruit_ili9341
from PIL import Image
from adafruit_portalbase.graphics import GraphicsBase

__version__ = "0.0.0-auto.0"
__repo__ = "https://github.com/adafruit/Adafruit_Blinka_PyPortal.git"


class Graphics(GraphicsBase):
    """Graphics Helper Class for the PyPortal Library

    :param default_bg: The path to your default background image file or a hex color.
                       Defaults to 0x000000.
    :param debug: Turn on debug print outs. Defaults to False.

    """

    # pylint: disable=too-few-public-methods
    def __init__(self, *, default_bg=None, display=None, spi=None, debug=False):
        if display is None:
            if DISPLAY_ARG_REQUIRED:
                raise RuntimeError(
                    "Display must be provided on platforms without board."
                )
            display_bus = displayio.FourWire(
                spi, command=board.D25, chip_select=board.CE0
            )
            display = adafruit_ili9341.ILI9341(
                display_bus, width=320, height=240, backlight_pin=board.D18
            )

        if display is None:
            raise RuntimeError("Display not found or provided")

        super().__init__(display, default_bg=default_bg, debug=debug)
        # Tracks whether we've hidden the background when we showed the QR code.
        self._qr_only = False

    # pylint: disable=arguments-differ
    def qrcode(self, qr_data, *, qr_size=1, x=0, y=0, hide_background=False):
        """Display a QR code

        :param qr_data: The data for the QR code.
        :param int qr_size: The scale of the QR code.
        :param x: The x position of upper left corner of the QR code on the display.
        :param y: The y position of upper left corner of the QR code on the display.

        """
        super().qrcode(
            qr_data, qr_size=qr_size, x=x, y=y,
        )
        if hide_background:
            self.display.show(self._qr_group)
        self._qr_only = hide_background

    # pylint: enable=arguments-differ

    def hide_QR(self):  # pylint: disable=invalid-name
        """Clear any QR codes that are currently on the screen"""

        if self._qr_only:
            self.display.show(self.splash)
        else:
            try:
                self._qr_group.pop()
            except (IndexError, AttributeError):  # later test if empty
                pass

    @staticmethod
    def resize_image(filename, width, height):
        """Resize the image to be within the width and height while maintaining
        proper scaling

        param: str filename: The location of the image file to resize
        param int width: The maximum width to resize to
        param int height: The maximum height to resize to
        """
        # Open image
        image = Image.open(filename)
        image_ratio = image.width / image.height
        target_ratio = width / height

        # Resize with sample
        if target_ratio < image_ratio:
            scaled_width = image.width * height // image.height
            scaled_height = height
        else:
            scaled_width = width
            scaled_height = image.height * width // image.width
        image = image.resize((scaled_width, scaled_height), Image.BICUBIC)

        # Save to same filename
        image.save(filename)

    # pylint: enable=no-self-use
