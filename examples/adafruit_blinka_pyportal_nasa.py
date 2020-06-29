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

# Set up where we'll be fetching data from
DATA_SOURCE = "https://api.nasa.gov/planetary/apod?api_key=DEMO_KEY"
# There's a few different places we look for data in the photo of the day
IMAGE_LOCATION = ["url"]
TITLE_LOCATION = ["title"]
DATE_LOCATION = ["date"]

# the current working directory (where this file is)
cwd = os.path.dirname(os.path.realpath(__file__))
pyportal = PyPortal(
    url=DATA_SOURCE,
    json_path=(TITLE_LOCATION, DATE_LOCATION),
    display=display,
    touchscreen=touchscreen,
    default_bg=cwd + "/nasa_background.bmp",
    text_font=cwd + "/fonts/Arial-12.bdf",
    text_position=((5, 220), (5, 200)),
    text_color=(0xFFFFFF, 0xFFFFFF),
    text_maxlen=(50, 50),  # cut off characters
    image_json_path=IMAGE_LOCATION,
    image_resize=(320, 240),
    image_position=(0, 0),
)

while True:
    response = None
    try:
        response = pyportal.fetch()
        print("Response is", response)
    except RuntimeError as e:
        print("Some error occured, retrying! -", e)

    time.sleep(30 * 60)  # 30 minutes till next check
