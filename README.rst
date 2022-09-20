Introduction
============


.. image:: https://readthedocs.org/projects/adafruit-circuitpython-displayio-flipclock/badge/?version=latest
    :target: https://docs.circuitpython.org/projects/displayio_flipclock/en/latest/
    :alt: Documentation Status


.. image:: https://raw.githubusercontent.com/adafruit/Adafruit_CircuitPython_Bundle/main/badges/adafruit_discord.svg
    :target: https://adafru.it/discord
    :alt: Discord


.. image:: https://github.com/adafruit/Adafruit_CircuitPython_DisplayIO_FlipClock/workflows/Build%20CI/badge.svg
    :target: https://github.com/adafruit/Adafruit_CircuitPython_DisplayIO_FlipClock/actions
    :alt: Build Status


.. image:: https://img.shields.io/badge/code%20style-black-000000.svg
    :target: https://github.com/psf/black
    :alt: Code Style: Black

DisplayIO widgets for showing flip clock style animattions changing from one number to another.


Dependencies
=============
This driver depends on:

* `Adafruit CircuitPython <https://github.com/adafruit/circuitpython>`_
* `Bus Device <https://github.com/adafruit/Adafruit_CircuitPython_BusDevice>`_
* `Register <https://github.com/adafruit/Adafruit_CircuitPython_Register>`_
* `CedarGrove PaletteFader <https://github.com/CedarGroveStudios/CircuitPython_PaletteFader.git>`_

This command can be used to install the PaletteFader:

.. code-block:: shell

    circup install cedargrove_palettefader

Please ensure all dependencies are available on the CircuitPython filesystem.
This is easily achieved by downloading
`the Adafruit library and driver bundle <https://circuitpython.org/libraries>`_
or individual libraries can be installed using
`circup <https://github.com/adafruit/circup>`_.

`Purchase Feather ESP32-S2 TFT from the Adafruit shop <https://www.adafruit.com/product/5300/>`_

Installing from PyPI
=====================

On supported GNU/Linux systems like the Raspberry Pi, you can install the driver locally `from
PyPI <https://pypi.org/project/adafruit-circuitpython-displayio-flipclock/>`_.
To install for current user:

.. code-block:: shell

    pip3 install adafruit-circuitpython-displayio-flipclock

To install system-wide (this may be required in some cases):

.. code-block:: shell

    sudo pip3 install adafruit-circuitpython-displayio-flipclock

To install in a virtual environment in your current project:

.. code-block:: shell

    mkdir project-name && cd project-name
    python3 -m venv .venv
    source .env/bin/activate
    pip3 install adafruit-circuitpython-displayio-flipclock

Installing to a Connected CircuitPython Device with Circup
==========================================================

Make sure that you have ``circup`` installed in your Python environment.
Install it with the following command if necessary:

.. code-block:: shell

    pip3 install circup

With ``circup`` installed and your CircuitPython device connected use the
following command to install:

.. code-block:: shell

    circup install adafruit_displayio_flipclock

Or the following command to update an existing version:

.. code-block:: shell

    circup update

Usage Example #1
=============

.. code-block:: python

    import time
    from displayio import Group
    import board
    import adafruit_imageload
    from adafruit_displayio_flipclock.flip_digit import FlipDigit


    ANIMATION_DELAY = 0.02
    ANIMATION_FRAME_COUNT = 10
    TRANSPARENT_INDEXES = range(11)
    BRIGHTER_LEVEL = 0.99
    DARKER_LEVEL = 0.5
    MEDIUM_LEVEL = 0.9

    display = board.DISPLAY
    main_group = Group()

    static_spritesheet, static_palette = adafruit_imageload.load("static_sheet.bmp")
    static_palette.make_transparent(0)

    top_animation_spritesheet, top_animation_palette = adafruit_imageload.load(
        "grey_top_animation_sheet.bmp"
    )
    bottom_animation_spritesheet, bottom_animation_palette = adafruit_imageload.load(
        "grey_bottom_animation_sheet.bmp"
    )

    for i in TRANSPARENT_INDEXES:
        top_animation_palette.make_transparent(i)
        bottom_animation_palette.make_transparent(i)

    SPRITE_WIDTH = static_spritesheet.width // 3
    SPRITE_HEIGHT = (static_spritesheet.height // 4) // 2

    flip_digit = FlipDigit(
        static_spritesheet,
        static_palette,
        top_animation_spritesheet,
        top_animation_palette,
        bottom_animation_spritesheet,
        bottom_animation_palette,
        SPRITE_WIDTH,
        SPRITE_HEIGHT,
        anim_frame_count=ANIMATION_FRAME_COUNT,
        anim_delay=ANIMATION_DELAY,
        brighter_level=BRIGHTER_LEVEL,
        darker_level=DARKER_LEVEL,
        medium_level=MEDIUM_LEVEL,
    )

    flip_digit.anchor_point = (0.5, 0.5)
    flip_digit.anchored_position = (display.width // 2, display.height // 2)

    main_group.append(flip_digit)

    display.show(main_group)

    while True:
        for i in range(10):
            flip_digit.value = i
            time.sleep(0.75)


Usage Example #2
================
This example connects to WiFi to sync the internal RTC with the datetime stamp of a NTP server.
The following variables have to be set in the file secrets.py:
- WiFi ssid;
- WiFi password;
- timezone.

Start of the example: 'displayio_flipclock_ntp_test_PaulskPt.py'

import time
import gc
import sys
import board
#import busio
from digitalio import DigitalInOut
from adafruit_esp32spi import adafruit_esp32spi
from displayio import Group
import adafruit_imageload
from adafruit_ntp import NTP
from adafruit_displayio_flipclock.flip_clock import FlipClock

""" Global flags """
my_debug = False
use_ntp = True
use_flipclock = True
use_dynamic_fading = True

[...]

Note PaulskPt about modifications in file flip_digit.py, class FlipDigit, which were necessary 
to stop having MemoryErrors. Added 'import gc'. In function __init__() added in five places 'gc.collect()'.
These additions had the intended result. The MemoryErrors stopped to occur.
For the same reason a global flag 'use_dynamic_fading' was introduced in the file
'displayio_flipclock_ntp_test_PaulskPt.py'.

In an attempt to use less memory in the PyPortal Titano,
copies of some .bmp files were made with shortened filenames:```

+------------------------------------------+---------------------------+
| Orignal finame:                          | Copy (shortened filename) |
+------------------------------------------+---------------------------+
| static_sheet_small.bmp                   | static_s.bmp              |
+------------------------------------------+---------------------------+
| top_anmation_sheet_small_5frames.bmp     | top_anim_s_5f.bmp         |
+------------------------------------------+---------------------------+
| bottom_animation_sheet_small_5frames.bmp | btm_anim_s_5f.bmp         |
+------------------------------------------+---------------------------+
```
Example #2 sets the internal Realtime Clock of the microcontroller with the date and time received 
from the function set_time() of class NTP, in file: 'adafruit_ntp.py. 
The function 'set_time()' calls the function 'get_time' of class 'ESP_SPIcontrol'
in file: '/lib/adafruit_esp32spi/adafruit_esp32spi.py' (or .mpy).
Every ten minutes the internal RTC will be synchronized through a call to function 'refresh_from_NTP()'.
The time will be shown on the display ('hh:mm'). The displayed time will be refreshed every minute.

Documentation
=============
API documentation for this library can be found on `Read the Docs <https://docs.circuitpython.org/projects/displayio_flipclock/en/latest/>`_.

For information on building library documentation, please check out
`this guide <https://learn.adafruit.com/creating-and-sharing-a-circuitpython-library/sharing-our-docs-on-readthedocs#sphinx-5-1>`_.

Contributing
============

Contributions are welcome! Please read our `Code of Conduct
<https://github.com/adafruit/Adafruit_CircuitPython_DisplayIO_FlipClock/blob/HEAD/CODE_OF_CONDUCT.md>`_
before contributing to help this project stay welcoming.
