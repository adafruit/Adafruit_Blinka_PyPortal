# SPDX-FileCopyrightText: 2020 Melissa LeBlanc-Williams, written for Adafruit Industries
#
# SPDX-License-Identifier: Unlicense
"""
`adafruit_pyportal.network`
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
import wget as wget_lib

# pylint: disable=unused-import
from adafruit_portalbase.network import (
    NetworkBase,
    CONTENT_JSON,
    CONTENT_TEXT,
)

# pylint: enable=unused-import
from adafruit_pyportal.wifi import WiFi

__version__ = "0.0.0-auto.0"
__repo__ = "https://github.com/adafruit/Adafruit_Blinka_PyPortal.git"

# you'll need to pass in an io username, width, height, format (bit depth), io key, and then url!
IMAGE_CONVERTER_SERVICE = (
    "https://io.adafruit.com/api/v2/%s/integrations/image-formatter?"
    "x-aio-key=%s&width=%d&height=%d&output=BMP%d&url=%s"
)


class Network(NetworkBase):
    """Class representing the Adafruit PyPortal.

    :param status_neopixel: The pin for the status NeoPixel. Use ``board.NEOPIXEL`` for the on-board
                            NeoPixel. Defaults to ``None``, not the status LED
    :param bool extract_values: If true, single-length fetched values are automatically extracted
                                from lists and tuples. Defaults to ``True``.
    :param debug: Turn on debug print outs. Defaults to False.
    :param convert_image: Determine whether or not to use the AdafruitIO image converter service.
                          Set as False if your image is already resized. Defaults to True.
    :param image_url_path: The HTTP traversal path for a background image to display.
                             Defaults to ``None``.
    :param image_json_path: The JSON traversal path for a background image to display. Defaults to
                            ``None``.
    :param image_resize: What size to resize the image we got from the json_path, make this a tuple
                         of the width and height you want. Defaults to ``None``.
    :param image_position: The position of the image on the display as an (x, y) tuple. Defaults to
                           ``None``.
    :param image_dim_json_path: The JSON traversal path for the original dimensions of image tuple.
                                Used with fetch(). Defaults to ``None``.
    :param list secrets_data: An optional list in place of the data contained in the secrets.py file

    """

    def __init__(
        self,
        *,
        status_neopixel=None,
        extract_values=True,
        debug=False,
        convert_image=True,
        image_url_path=None,
        image_json_path=None,
        image_resize=None,
        image_position=None,
        image_dim_json_path=None,
        secrets_data=None
    ):
        wifi = WiFi(status_neopixel=status_neopixel)

        super().__init__(
            wifi, extract_values=extract_values, secrets_data=secrets_data, debug=debug,
        )

        self._convert_image = convert_image
        self._image_json_path = image_json_path
        self._image_url_path = image_url_path
        self._image_resize = image_resize
        self._image_position = image_position
        self._image_dim_json_path = image_dim_json_path

        gc.collect()

    @property
    def ip_address(self):
        """Return the IP Address nicely formatted"""
        return self._wifi.ip_address

    def image_converter_url(self, image_url, width, height, color_depth=16):
        """Generate a converted image url from the url passed in,
        with the given width and height. aio_username and aio_key must be
        set in secrets."""
        try:
            aio_username = self._secrets["aio_username"]
            aio_key = self._secrets["aio_key"]
        except KeyError as error:
            raise KeyError(
                "\n\nOur image converter service require a login/password to rate-limit. Please register for a free adafruit.io account and place the user/key in your secrets file under 'aio_username' and 'aio_key'"  # pylint: disable=line-too-long
            ) from error

        return IMAGE_CONVERTER_SERVICE % (
            aio_username,
            aio_key,
            width,
            height,
            color_depth,
            image_url,
        )

    # pylint: disable=unused-argument
    def wget(self, url, filename, *, chunk_size=12000):
        """Download a url and save to filename location, like the command wget.
        :param url: The URL from which to obtain the data.
        :param filename: The name of the file to save the data to.
        """
        print("Fetching stream from", url)
        self.neo_status((100, 100, 0))
        wget_lib.download(url, filename)
        self.neo_status((0, 0, 0))

    # pylint: enable=unused-argument

    # pylint: disable=too-many-branches, too-many-statements
    def process_image(self, json_data):
        """
        Process image content

        :param json_data: The JSON data that we can pluck values from
        :param bool sd_card: Whether or not we have an SD card inserted

        """
        filename = None
        position = None
        image_url = None

        if self._image_url_path:
            image_url = self._image_url_path

        if self._image_json_path:
            image_url = self.json_traverse(json_data, self._image_json_path)

        iwidth = 0
        iheight = 0
        if self._image_dim_json_path:
            iwidth = int(self.json_traverse(json_data, self._image_dim_json_path[0]))
            iheight = int(self.json_traverse(json_data, self._image_dim_json_path[1]))
            print("image dim:", iwidth, iheight)

        if image_url:
            print("original URL:", image_url)
            if self._convert_image:
                if iwidth < iheight:
                    image_url = self.image_converter_url(
                        image_url,
                        int(
                            self._image_resize[1]
                            * self._image_resize[1]
                            / self._image_resize[0]
                        ),
                        self._image_resize[1],
                    )
                else:
                    image_url = self.image_converter_url(
                        image_url, self._image_resize[0], self._image_resize[1]
                    )
            print("convert URL:", image_url)
            # convert image to bitmap and cache
            # print("**not actually wgetting**")
            filename = "cache.bmp"
            try:
                self.wget(image_url, filename)
            except RuntimeError as error:
                raise RuntimeError("wget didn't write a complete file") from error
            if iwidth < iheight:
                pwidth = int(
                    self._image_resize[1]
                    * self._image_resize[1]
                    / self._image_resize[0]
                )
                position = (
                    self._image_position[0] + int((self._image_resize[0] - pwidth) / 2),
                    self._image_position[1],
                )
            else:
                position = self._image_position

            image_url = None
            gc.collect()

        return filename, position
