# SPDX-FileCopyrightText: 2017 Scott Shawcroft, written for Adafruit Industries
# SPDX-FileCopyrightText: Copyright (c) 2020 Melissa LeBlanc-Williams for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
`adafruit_pyportal`
================================================================================

A port of the PyPortal library intended to run on Blinka in CPython.

* Author(s): Melissa LeBlanc-Williams

Implementation Notes
--------------------

**Software and Dependencies:**

* Adafruit CircuitPython firmware for the supported boards:
  https://github.com/adafruit/circuitpython/releases

"""

# imports
import os
import time
import gc
import subprocess
import requests

try:
    import board
    _display_arg_required = False
except NotImplementedError:
    # okay to run Generic Linux
    _display_arg_required = True
    pass
import digitalio
import displayio
import wget as wget_lib
from adafruit_bitmap_font import bitmap_font
from adafruit_display_text.label import Label
from adafruit_io.adafruit_io import IO_HTTP, AdafruitIO_RequestError
from adafruit_stmpe610 import Adafruit_STMPE610_SPI
from PIL import Image
import adafruit_focaltouch
import adafruit_ili9341

__version__ = "0.0.0-auto.0"
__repo__ = "https://github.com/adafruit/Adafruit_CircuitPython_pyportal.git"


# pylint: disable=line-too-long
# you'll need to pass in an io username, width, height, format (bit depth), io key, and then url!
IMAGE_CONVERTER_SERVICE = "https://io.adafruit.com/api/v2/%s/integrations/image-formatter?x-aio-key=%s&width=%d&height=%d&output=BMP%d&url=%s"
# you'll need to pass in an io username and key
TIME_SERVICE = (
    "https://io.adafruit.com/api/v2/%s/integrations/time/strftime?x-aio-key=%s"
)
# our strftime is %Y-%m-%d %H:%M:%S.%L %j %u %z %Z see http://strftime.net/ for decoding details
# See https://apidock.com/ruby/DateTime/strftime for full options
TIME_SERVICE_STRFTIME = (
    "&fmt=%25Y-%25m-%25d+%25H%3A%25M%3A%25S.%25L+%25j+%25u+%25z+%25Z"
)
LOCALFILE = "local.txt"
# pylint: enable=line-too-long


class Fake_Requests:
    """For faking 'requests' using a local file instead of the network."""

    def __init__(self, filename):
        self._filename = filename
        with open(filename, "r") as file:
            self.text = file.read()

    def json(self):
        """json parsed version for local requests."""
        import json  # pylint: disable=import-outside-toplevel

        return json.loads(self.text)


class PyPortal:
    """Class representing the Adafruit PyPortal.

    :param url: The URL of your data source. Defaults to ``None``.
    :param headers: The headers for authentication, typically used by Azure API's.
    :param json_path: The list of json traversal to get data out of. Can be list of lists for
                      multiple data points. Defaults to ``None`` to not use json.
    :param regexp_path: The list of regexp strings to get data out (use a single regexp group). Can
                        be list of regexps for multiple data points. Defaults to ``None`` to not
                        use regexp.
    :param default_bg: The path to your default background image file or a hex color.
                       Defaults to 0x000000.
    :param status_neopixel: The pin for the status NeoPixel. Use ``board.NEOPIXEL`` for the on-board
                            NeoPixel. Defaults to ``None``, no status LED
    :param str text_font: The path to your font file for your data text display.
    :param text_position: The position of your extracted text on the display in an (x, y) tuple.
                          Can be a list of tuples for when there's a list of json_paths, for example
    :param text_color: The color of the text, in 0xRRGGBB format. Can be a list of colors for when
                       there's multiple texts. Defaults to ``None``.
    :param text_wrap: Whether or not to wrap text (for long text data chunks). Defaults to
                      ``False``, no wrapping.
    :param text_maxlen: The max length of the text for text wrapping. Defaults to 0.
    :param text_transform: A function that will be called on the text before display
    :param json_transform: A function or a list of functions to call with the parsed JSON.
                           Changes and additions are permitted for the ``dict`` object.
    :param image_json_path: The JSON traversal path for a background image to display. Defaults to
                            ``None``.
    :param image_resize: What size to resize the image we got from the json_path, make this a tuple
                         of the width and height you want. Defaults to ``None``.
    :param image_position: The position of the image on the display as an (x, y) tuple. Defaults to
                           ``None``.
    :param image_dim_json_path: The JSON traversal path for the original dimensions of image tuple.
                                Used with fetch(). Defaults to ``None``.
    :param success_callback: A function we'll call if you like, when we fetch data successfully.
                             Defaults to ``None``.
    :param str caption_text: The text of your caption, a fixed text not changed by the data we get.
                             Defaults to ``None``.
    :param str caption_font: The path to the font file for your caption. Defaults to ``None``.
    :param caption_position: The position of your caption on the display as an (x, y) tuple.
                             Defaults to ``None``.
    :param caption_color: The color of your caption. Must be a hex value, e.g. ``0x808000``.
    :param image_url_path: The HTTP traversal path for a background image to display.
                           Defaults to ``None``.
    :param busio.SPI external_spi: A previously declared spi object. Defaults to ``None``.
    :param debug: Turn on debug print outs. Defaults to False.
    :param display: The displayio display object to use
    :param touchscreen: The touchscreen object to use. Usually STMPE610 or FocalTouch.
    :param secrets: The secrets object to use. If not supplied we will attempt to import.

    """

    # pylint: disable=too-many-instance-attributes, too-many-locals, too-many-branches, too-many-statements
    def __init__(
        self,
        *,
        url=None,
        headers=None,
        json_path=None,
        regexp_path=None,
        default_bg=0x000000,
        status_neopixel=None,
        text_font=None,
        text_position=None,
        text_color=0x808080,
        text_wrap=False,
        text_maxlen=0,
        text_transform=None,
        json_transform=None,
        image_json_path=None,
        image_resize=None,
        image_position=None,
        image_dim_json_path=None,
        caption_text=None,
        caption_font=None,
        caption_position=None,
        caption_color=0x808080,
        image_url_path=None,
        success_callback=None,
        external_spi=None,
        debug=False,
        display=None,
        touchscreen=None,
        secrets=None
    ):

        if not secrets:
            # pylint: disable=import-outside-toplevel
            try:
                from secrets import secrets  # pylint: disable=no-name-in-module
            except RuntimeError:
                raise "API tokens are kept in secrets.py, please add them there!" from RuntimeError
            self.secrets = secrets
        else:
            self.secrets = secrets

        self._debug = debug
        self._debug_start = time.monotonic()
        self.display = display

        spi = None

        if self.display is None:
            if _display_arg_required:
                raise RuntimeError("Display must be provided on platforms without board.")
            if external_spi:  # If SPI Object Passed
                spi = external_spi
            else:  # Else: Make ESP32 connection
                spi = board.SPI()

            display_bus = displayio.FourWire(
                spi, command=board.D25, chip_select=board.CE0
            )
            self.display = adafruit_ili9341.ILI9341(
                display_bus, width=320, height=240, backlight_pin=board.D18
            )

        if self.display is None:
            raise RuntimeError("Display not found or provided")
        self.set_backlight(1.0)  # turn on backlight

        self._url = url
        self._headers = headers
        if json_path:
            if isinstance(json_path[0], (list, tuple)):
                self._json_path = json_path
            else:
                self._json_path = (json_path,)
        else:
            self._json_path = None

        self._regexp_path = regexp_path
        self._success_callback = success_callback

        if status_neopixel:
            import neopixel  # pylint: disable=import-outside-toplevel

            self.neopix = neopixel.NeoPixel(status_neopixel, 1, brightness=0.2)
        else:
            self.neopix = None
        self.neo_status(0)

        self.audio_device = 1

        try:
            os.stat(LOCALFILE)
            self._uselocal = True
        except OSError:
            self._uselocal = False

        self._debug_print("Init display")
        self.splash = displayio.Group(max_size=15)

        self._debug_print("Init background")
        self._bg_group = displayio.Group(max_size=1)
        self._bg_file = None
        self._default_bg = default_bg
        self.splash.append(self._bg_group)

        # show thank you and bootup file if available
        for bootscreen in ("thankyou.bmp", "pyportal_startup.bmp"):
            try:
                os.stat(bootscreen)
                self.display.show(self.splash)
                self.set_backlight(0)
                self.set_background(bootscreen)
                self.set_backlight(1)
            except OSError:
                pass  # they removed it, skip!
        try:
            self.play_file("pyportal_startup.wav")
        except OSError:
            pass  # they deleted the file, no biggie!

        self._debug_print("My IP address is", self.get_ip_address())

        # set the default background
        self.set_background(self._default_bg)
        self.display.show(self.splash)

        self._qr_group = None
        # Tracks whether we've hidden the background when we showed the QR code.
        self._qr_only = False

        self._debug_print("Init caption")
        self._caption = None
        if caption_font:
            self._caption_font = bitmap_font.load_font(caption_font)
        self.set_caption(caption_text, caption_position, caption_color)

        if text_font:
            if isinstance(text_position[0], (list, tuple)):
                num = len(text_position)
                if not text_wrap:
                    text_wrap = [0] * num
                if not text_maxlen:
                    text_maxlen = [0] * num
                if not text_transform:
                    text_transform = [None] * num
            else:
                num = 1
                text_position = (text_position,)
                text_color = (text_color,)
                text_wrap = (text_wrap,)
                text_maxlen = (text_maxlen,)
                text_transform = (text_transform,)
            self._text = [None] * num
            self._text_color = [None] * num
            self._text_position = [None] * num
            self._text_wrap = [None] * num
            self._text_maxlen = [None] * num
            self._text_transform = [None] * num
            self._text_font = bitmap_font.load_font(text_font)
            self._debug_print("Loading font glyphs")
            # self._text_font.load_glyphs(b'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'
            #                             b'0123456789:/-_,. ')
            gc.collect()

            for i in range(num):
                self._debug_print("Init text area", i)
                self._text[i] = None
                self._text_color[i] = text_color[i]
                self._text_position[i] = text_position[i]
                self._text_wrap[i] = text_wrap[i]
                self._text_maxlen[i] = text_maxlen[i]
                self._text_transform[i] = text_transform[i]
        else:
            self._text_font = None
            self._text = None

        # Add any JSON translators
        self._json_transform = []
        if json_transform:
            if callable(json_transform):
                self._json_transform.append(json_transform)
            else:
                self._json_transform.extend(filter(callable, json_transform))

        self._image_json_path = image_json_path
        self._image_url_path = image_url_path
        self._image_resize = image_resize
        self._image_position = image_position
        self._image_dim_json_path = image_dim_json_path
        if image_json_path or image_url_path:
            self._debug_print("Init image path")
            if not self._image_position:
                self._image_position = (0, 0)  # default to top corner
            if not self._image_resize:
                self._image_resize = (
                    self.display.width,
                    self.display.height,
                )  # default to full screen

        self._debug_print("Init touchscreen")
        self.touchscreen = touchscreen
        if spi is not None:
            # Attempt to Init STMPE610
            if self.touchscreen is None:
                self._debug_print("Attempting to initialize STMPE610...")
                try:
                    chip_select = digitalio.DigitalInOut(board.CE1)
                    self.touchscreen = Adafruit_STMPE610_SPI(spi, chip_select)
                except (RuntimeError, AttributeError):
                    self._debug_print("None Found")
            # Attempt to Init FocalTouch
            if self.touchscreen is None:
                self._debug_print("Attempting to initialize Focal Touch...")
                try:
                    i2c = board.I2C()
                    self.touchscreen = adafruit_focaltouch.Adafruit_FocalTouch(i2c)
                except Exception:  # pylint: disable=broad-except
                    self._debug_print("None Found")

        self.set_backlight(1.0)  # turn on backlight

        gc.collect()

    def set_headers(self, headers):
        """Set the headers used by fetch().

        :param headers: The new header dictionary
        """
        self._headers = headers

    def set_background(self, file_or_color, position=None):
        """The background image to a bitmap file.

        :param file_or_color: The filename of the chosen background image, or a hex color.
        """
        self._debug_print("Set background to", file_or_color)
        while self._bg_group:
            self._bg_group.pop()
        if not position:
            position = (0, 0)  # default in top corner

        if not file_or_color:
            return  # we're done, no background desired
        if self._bg_file:
            self._bg_file.close()
        if isinstance(file_or_color, str):  # its a filenme:
            self._bg_file = open(file_or_color, "rb")
            background = displayio.OnDiskBitmap(self._bg_file)
            self._bg_sprite = displayio.TileGrid(
                background,
                pixel_shader=displayio.ColorConverter(),
                x=position[0],
                y=position[1],
            )
        elif isinstance(file_or_color, int):
            # Make a background color fill
            color_bitmap = displayio.Bitmap(self.display.width, self.display.height, 1)
            color_palette = displayio.Palette(1)
            color_palette[0] = file_or_color
            self._bg_sprite = displayio.TileGrid(
                color_bitmap, pixel_shader=color_palette, x=position[0], y=position[1],
            )
        else:
            raise RuntimeError("Unknown type of background")
        self._bg_group.append(self._bg_sprite)
        self.display.refresh(target_frames_per_second=60)
        gc.collect()

    def set_backlight(self, val):
        """Adjust the TFT backlight.

        :param val: The backlight brightness. Use a value between ``0`` and ``1``, where ``0`` is
                    off, and ``1`` is 100% brightness.
        """
        self.display.auto_brightness = False
        self.display.brightness = val

    def preload_font(self, glyphs=None):
        # pylint: disable=line-too-long
        """Preload font.

        :param glyphs: The font glyphs to load. Defaults to ``None``, uses alphanumeric glyphs if
                       None.
        """
        # pylint: enable=line-too-long
        if not glyphs:
            glyphs = b"0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ-!,. \"'?!"
        self._debug_print("Preloading font glyphs:", glyphs)
        if self._text_font:
            self._text_font.load_glyphs(glyphs)

    def set_caption(self, caption_text, caption_position, caption_color):
        # pylint: disable=line-too-long
        """A caption. Requires setting ``caption_font`` in init!

        :param caption_text: The text of the caption.
        :param caption_position: The position of the caption text.
        :param caption_color: The color of your caption text. Must be a hex value, e.g.
                              ``0x808000``.
        """
        # pylint: enable=line-too-long
        self._debug_print("Setting caption to", caption_text)

        if (not caption_text) or (not self._caption_font) or (not caption_position):
            return  # nothing to do!

        if self._caption:
            self._caption._update_text(  # pylint: disable=protected-access
                str(caption_text)
            )
            try:
                self.display.refresh(target_frames_per_second=60)
            except AttributeError:
                self.display.refresh_soon()
                self.display.wait_for_frame()
            return

        self._caption = Label(self._caption_font, text=str(caption_text))
        self._caption.x = caption_position[0]
        self._caption.y = caption_position[1]
        self._caption.color = caption_color
        self.splash.append(self._caption)

    def set_text(self, val, index=0):
        """Display text, with indexing into our list of text boxes.

        :param str val: The text to be displayed
        :param index: Defaults to 0.
        """
        if self._text_font:
            string = str(val)
            if self._text_maxlen[index]:
                string = string[: self._text_maxlen[index]]
            if self._text[index]:
                # print("Replacing text area with :", string)
                # self._text[index].text = string
                # return
                try:
                    text_index = self.splash.index(self._text[index])
                except AttributeError:
                    for i in range(len(self.splash)):
                        if self.splash[i] == self._text[index]:
                            text_index = i
                            break

                self._text[index] = Label(self._text_font, text=string)
                self._text[index].color = self._text_color[index]
                self._text[index].x = self._text_position[index][0]
                self._text[index].y = self._text_position[index][1]
                self.splash[text_index] = self._text[index]
                return

            if self._text_position[index]:  # if we want it placed somewhere...
                self._debug_print("Making text area with string:", string)
                self._text[index] = Label(self._text_font, text=string)
                self._text[index].color = self._text_color[index]
                self._text[index].x = self._text_position[index][0]
                self._text[index].y = self._text_position[index][1]
                self.splash.append(self._text[index])

    def neo_status(self, value):
        """The status NeoPixel.

        :param value: The color to change the NeoPixel.
        """
        if self.neopix:
            self.neopix.fill(value)

    def play_file(self, file_name, wait_to_finish=True):
        """Play a wav file.

        :param str file_name: The name of the wav file to play on the speaker.
        """
        self._debug_print("Playing audio file", file_name)
        os.system("aplay -Dhw:" + str(self.audio_device) + ",0 " + file_name)
        if not wait_to_finish:
            # To do: Add threading support
            print("Immediately returning not currently supported.")

    @staticmethod
    def _json_traverse(json, path):
        value = json
        for x in path:
            value = value[x]
            gc.collect()
        return value

    def get_local_time(self, location=None):
        # pylint: disable=line-too-long
        """Fetch and "set" the local time of this microcontroller to the local time at the location, using an internet time API.

        :param str location: Your city and country, e.g. ``"New York, US"``.
        """
        # pylint: enable=line-too-long
        api_url = None
        try:
            aio_username = self.secrets["aio_username"]
            aio_key = self.secrets["aio_key"]
        except KeyError:
            raise KeyError(
                "\n\nOur time service requires a login/password to rate-limit. Please register for a free adafruit.io account and place the user/key in your secrets file under 'aio_username' and 'aio_key'"  # pylint: disable=line-too-long
            ) from KeyError

        location = self.secrets.get("timezone", location)
        if location:
            print("Getting time for timezone", location)
            api_url = (TIME_SERVICE + "&tz=%s") % (aio_username, aio_key, location)
        else:  # we'll try to figure it out from the IP address
            print("Getting time from IP address")
            api_url = TIME_SERVICE % (aio_username, aio_key)
        api_url += TIME_SERVICE_STRFTIME
        try:
            response = requests.get(api_url, timeout=10)
            if response.status_code != 200:
                raise ValueError(response.text)
            self._debug_print("Time request: ", api_url)
            self._debug_print("Time reply: ", response.text)
            times = response.text.split(" ")
            the_date = times[0]
            the_time = times[1]
            year_day = int(times[2])
            week_day = int(times[3])
            is_dst = None  # no way to know yet
        except KeyError:
            raise KeyError(
                "Was unable to lookup the time, try setting secrets['timezone'] according to http://worldtimeapi.org/timezones"  # pylint: disable=line-too-long
            ) from KeyError
        year, month, mday = [int(x) for x in the_date.split("-")]
        the_time = the_time.split(".")[0]
        hours, minutes, seconds = [int(x) for x in the_time.split(":")]
        now = time.struct_time(
            (year, month, mday, hours, minutes, seconds, week_day, year_day, is_dst)
        )
        print(now)

        # now clean up
        response.close()
        response = None
        gc.collect()

    # pylint: disable=no-self-use
    def wget(self, url, filename):
        """Download a url and save to filename location, like the command wget.

        :param url: The URL from which to obtain the data.
        :param filename: The name of the file to save the data to.
        """
        print("Fetching stream from", url)
        self.neo_status((100, 100, 0))
        wget_lib.download(url, filename)
        self.neo_status((0, 0, 0))

    # pylint: enable=no-self-use

    def image_converter_url(self, image_url, width, height, color_depth=16):
        """Generate a converted image url from the url passed in,
           with the given width and height. aio_username and aio_key must be
           set in secrets."""
        try:
            aio_username = self.secrets["aio_username"]
            aio_key = self.secrets["aio_key"]
        except KeyError:
            raise KeyError(
                "\n\nOur image converter service require a login/password to rate-limit. Please register for a free adafruit.io account and place the user/key in your secrets file under 'aio_username' and 'aio_key'"  # pylint: disable=line-too-long
            ) from KeyError

        return IMAGE_CONVERTER_SERVICE % (
            aio_username,
            aio_key,
            width,
            height,
            color_depth,
            image_url,
        )

    # pylint: disable=no-self-use
    def sd_check(self):
        """Returns True if there is an SD card present and False
        if there is no SD card. The _sdcard value is set in _init
        """
        return False

    def push_to_io(self, feed_key, data):
        # pylint: disable=line-too-long
        """Push data to an adafruit.io feed

        :param str feed_key: Name of feed key to push data to.
        :param data: data to send to feed
        """
        # pylint: enable=line-too-long

        try:
            aio_username = self.secrets["aio_username"]
            aio_key = self.secrets["aio_key"]
        except KeyError:
            raise KeyError(
                "Adafruit IO secrets are kept in secrets.py, please add them there!\n\n"
            ) from KeyError

        # This may need a fake wrapper written to just use onboard eth0 or whatever
        # wifi = adafruit_esp32spi_wifimanager.ESPSPI_WiFiManager(
        #    self._esp, secrets, None
        # )
        wifi = None
        io_client = IO_HTTP(aio_username, aio_key, wifi)

        while True:
            try:
                feed_id = io_client.get_feed(feed_key)
            except AdafruitIO_RequestError:
                # If no feed exists, create one
                feed_id = io_client.create_new_feed(feed_key)
            except RuntimeError as exception:
                print("An error occured, retrying! 1 -", exception)
                continue
            break

        while True:
            try:
                io_client.send_data(feed_id["key"], data)
            except RuntimeError as exception:
                print("An error occured, retrying! 2 -", exception)
                continue
            except NameError as exception:
                print(feed_id["key"], data, exception)
                continue
            break

    def resize_image(self, filename, width, height):
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

    def fetch(self, refresh_url=None, timeout=10):
        """Fetch data from the url we initialized with, perfom any parsing,
        and display text or graphics. This function does pretty much everything
        Optionally update the URL
        """

        if refresh_url:
            self._url = refresh_url
        json_out = None
        image_url = None
        values = []

        gc.collect()

        r = None
        if self._uselocal:
            print("*** USING LOCALFILE FOR DATA - NOT INTERNET!!! ***")
            r = Fake_Requests(LOCALFILE)

        if not r:
            # great, lets get the data
            print("Retrieving data...", end="")
            self.neo_status((100, 100, 0))  # yellow = fetching data
            gc.collect()
            try:
                r = requests.get(self._url, headers=self._headers, timeout=timeout)
            except Exception:  # pylint: disable=broad-except
                print("Error: Read timed out.")
                raise

            gc.collect()
            self.neo_status((0, 0, 100))  # green = got data
            print("Reply is OK!")

        if not self._image_json_path and not self._json_path:
            self._debug_print(r.text)

        if self._image_json_path or self._json_path:
            try:
                json_out = r.json()
                self._debug_print(json_out)
            except ValueError:  # failed to parse?
                print("Couldn't parse json: ", r.text)
                raise

        if self._regexp_path:
            import re  # pylint: disable=import-outside-toplevel

        if self._image_url_path:
            image_url = self._image_url_path

        # optional JSON post processing, apply any transformations
        # these MAY change/add element
        for idx, json_transform in enumerate(self._json_transform):
            try:
                json_transform(json_out)
            except Exception as error:
                print("Exception from json_transform: ", idx, error)
                raise

        # extract desired text/values from json
        if self._json_path:
            for path in self._json_path:
                try:
                    values.append(PyPortal._json_traverse(json_out, path))
                except KeyError:
                    print(json_out)
                    raise
        elif self._regexp_path:
            for regexp in self._regexp_path:
                values.append(re.search(regexp, r.text).group(1))
        else:
            values = r.text

        if self._image_json_path:
            try:
                image_url = PyPortal._json_traverse(json_out, self._image_json_path)
            except KeyError as error:
                print("Error finding image data. '" + error.args[0] + "' not found.")
                self.set_background(self._default_bg)

        iwidth = 0
        iheight = 0
        if self._image_dim_json_path:
            iwidth = int(
                PyPortal._json_traverse(json_out, self._image_dim_json_path[0])
            )
            iheight = int(
                PyPortal._json_traverse(json_out, self._image_dim_json_path[1])
            )
            print("image dim:", iwidth, iheight)

        # we're done with the requests object, lets delete it so we can do more!
        json_out = None
        r = None
        gc.collect()

        if image_url:
            try:
                print("original URL:", image_url)
                # convert image to bitmap and cache
                # print("**not actually wgetting**")
                filename = "cache.bmp"
                self.wget(image_url, filename)
                self.resize_image(
                    filename, self._image_resize[0], self._image_resize[1]
                )

                if iwidth < iheight:
                    pwidth = int(
                        self._image_resize[1]
                        * self._image_resize[1]
                        / self._image_resize[0]
                    )
                    self.set_background(
                        filename,
                        (
                            self._image_position[0]
                            + int((self._image_resize[0] - pwidth) / 2),
                            self._image_position[1],
                        ),
                    )
                else:
                    self.set_background(filename, self._image_position)

            except ValueError as error:
                print("Error displaying cached image. " + error.args[0])
                self.set_background(self._default_bg)
            finally:
                image_url = None
                gc.collect()

        # if we have a callback registered, call it now
        if self._success_callback:
            self._success_callback(values)

        # fill out all the text blocks
        if self._text:
            for i in range(len(self._text)):
                string = None
                if self._text_transform[i]:
                    func = self._text_transform[i]
                    string = func(values[i])
                else:
                    try:
                        string = "{:,d}".format(int(values[i]))
                    except (TypeError, ValueError):
                        string = values[i]  # ok its a string
                self._debug_print("Drawing text", string)
                if self._text_wrap[i]:
                    self._debug_print("Wrapping text")
                    lines = PyPortal.wrap_nicely(string, self._text_wrap[i])
                    string = "\n".join(lines)
                self.set_text(string, index=i)
        if len(values) == 1:
            return values[0]
        return values

    # pylint: disable=no-self-use
    def get_ip_address(self):
        """Look up the IP address and return it"""
        return subprocess.check_output(
            "hostname -I | cut -d' ' -f1", shell=True
        ).decode("utf-8")

    # pylint: enable=no-self-use

    def show_QR(
        self, qr_data, *, qr_size=1, x=0, y=0, hide_background=False
    ):  # pylint: disable=invalid-name
        """Display a QR code on the TFT

        :param qr_data: The data for the QR code.
        :param int qr_size: The scale of the QR code.
        :param x: The x position of upper left corner of the QR code on the display.
        :param y: The y position of upper left corner of the QR code on the display.
        :param hide_background: Show the QR code on a black background if True.
        """
        import adafruit_miniqr  # pylint: disable=import-outside-toplevel

        # generate the QR code
        qrcode = adafruit_miniqr.QRCode()
        qrcode.add_data(qr_data)
        qrcode.make()

        # monochrome (2 color) palette
        palette = displayio.Palette(2)
        palette[0] = 0xFFFFFF
        palette[1] = 0x000000

        # pylint: disable=invalid-name
        # bitmap the size of the matrix, plus border, monochrome (2 colors)
        qr_bitmap = displayio.Bitmap(
            qrcode.matrix.width + 2, qrcode.matrix.height + 2, 2
        )
        for i in range(qr_bitmap.width * qr_bitmap.height):
            qr_bitmap[i] = 0

        # transcribe QR code into bitmap
        for xx in range(qrcode.matrix.width):
            for yy in range(qrcode.matrix.height):
                qr_bitmap[xx + 1, yy + 1] = 1 if qrcode.matrix[xx, yy] else 0

        # display the QR code
        qr_sprite = displayio.TileGrid(qr_bitmap, pixel_shader=palette)
        if self._qr_group:
            try:
                self._qr_group.pop()
            except IndexError:  # later test if empty
                pass
        else:
            self._qr_group = displayio.Group()
            self.splash.append(self._qr_group)
        self._qr_group.scale = qr_size
        self._qr_group.x = x
        self._qr_group.y = y
        self._qr_group.append(qr_sprite)
        if hide_background:
            self.display.show(self._qr_group)
        self._qr_only = hide_background

    def hide_QR(self):  # pylint: disable=invalid-name
        """Clear any QR codes that are currently on the screen
        """

        if self._qr_only:
            self.display.show(self.splash)
        else:
            try:
                self._qr_group.pop()
            except (IndexError, AttributeError):  # later test if empty
                pass

    # return a list of lines with wordwrapping
    @staticmethod
    def wrap_nicely(string, max_chars):
        """A helper that will return a list of lines with word-break wrapping.

        :param str string: The text to be wrapped.
        :param int max_chars: The maximum number of characters on a line before wrapping.
        """
        string = string.replace("\n", "").replace("\r", "")  # strip confusing newlines
        words = string.split(" ")
        the_lines = []
        the_line = ""
        for w in words:
            if len(the_line + " " + w) <= max_chars:
                the_line += " " + w
            else:
                the_lines.append(the_line)
                the_line = "" + w
        if the_line:  # last line remaining
            the_lines.append(the_line)
        # remove first space from first line:
        the_lines[0] = the_lines[0][1:]
        return the_lines

    def _debug_print(self, *args):
        if self._debug:
            print(time.monotonic() - self._debug_start, args)
