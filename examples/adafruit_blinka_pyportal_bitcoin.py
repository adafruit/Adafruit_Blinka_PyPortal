# SPDX-FileCopyrightText: 2017 Scott Shawcroft, written for Adafruit Industries
#
# SPDX-License-Identifier: Unlicense
"""
This example will access the coindesk API, grab a number like bitcoin value in
USD and display it on a screen
If you can find something that spits out JSON data, we can display it!
"""
import os
import time
import board
import digitalio
import displayio
from adafruit_stmpe610 import Adafruit_STMPE610_SPI
import adafruit_ili9341
from adafruit_pyportal import PyPortal

displayio.release_displays()

spi = board.SPI()
tft_cs = board.CE0
touch_cs = board.CE1
tft_dc = board.D25

touchscreen = Adafruit_STMPE610_SPI(spi, digitalio.DigitalInOut(touch_cs))

display_bus = displayio.FourWire(spi, command=tft_dc, chip_select=tft_cs)
display = adafruit_ili9341.ILI9341(display_bus, width=320, height=240)

board.TFT_BACKLIGHT = board.D26
# You can display in 'GBP', 'EUR' or 'USD'
CURRENCY = "USD"
# Set up where we'll be fetching data from
DATA_SOURCE = "https://api.coindesk.com/v1/bpi/currentprice.json"
DATA_LOCATION = ["bpi", CURRENCY, "rate_float"]


def text_transform(val):
    if CURRENCY == "USD":
        return "$%d" % val
    if CURRENCY == "EUR":
        return "‎€%d" % val
    if CURRENCY == "GBP":
        return "£%d" % val
    return "%d" % val


# the current working directory (where this file is)
cwd = os.path.dirname(os.path.realpath(__file__))
pyportal = PyPortal(
    url=DATA_SOURCE,
    json_path=DATA_LOCATION,
    display=display,
    touchscreen=touchscreen,
    status_neopixel=None,
    default_bg=cwd + "/bitcoin_background.bmp",
    text_font=cwd + "/fonts/Arial-Bold-24-Complete.bdf",
    text_position=(195, 130),
    text_color=0x0,
    text_transform=text_transform,
    debug=True,
)
pyportal.preload_font(b"$012345789")  # preload numbers
pyportal.preload_font((0x00A3, 0x20AC))  # preload gbp/euro symbol

while True:
    try:
        value = pyportal.fetch()
        print("Response is", value)
    except (ValueError, RuntimeError) as e:
        print("Some error occured, retrying! -", e)

    time.sleep(3 * 60)  # wait 3 minutes
