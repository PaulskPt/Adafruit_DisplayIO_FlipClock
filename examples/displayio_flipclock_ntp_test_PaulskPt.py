 # SPDX-FileCopyrightText: Copyright (c) 2022 Tim Cocks for Adafruit Industries
# (c) 2022 Paulus Schulinck for modifications done
#
# SPDX-License-Identifier: MIT
"""
    Advanced example that shows how you can use the
    FlipClock displayio object along with the adafruit_ntp library
    to show and update the current time with a FlipClock on a display.
"""

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

""" Other global variables """
esp = None
default_dt = None
main_group = None
clock = None
display = board.DISPLAY
ntp = None
start_t = time.monotonic()
tz_offset = 0
hour_old = 0
min_old = 0

def setup():
    global esp, ntp, tz_offset

    esp32_cs = DigitalInOut(board.ESP_CS)
    esp32_ready = DigitalInOut(board.ESP_BUSY)
    esp32_reset = DigitalInOut(board.ESP_RESET)
    #spi = busio.SPI(board.SCK, board.MOSI, board.MISO)
    spi = board.SPI()
    esp = adafruit_esp32spi.ESP_SPIcontrol(spi, esp32_cs, esp32_ready, esp32_reset)

    # Cleanup
    esp32_cs = None
    esp32_ready = None
    esp32_reset = None
    spi = None
    gc.collect()

    try:
        from secrets import secrets
    except ImportError:
        print("WiFi secrets are kept in secrets.py, please add them there!")
        raise

    location = secrets.get("timezone", None)
    if location is None:
        tz_offset = 0
    else:
        tz_offset0 = secrets.get("tz_offset", None)
        if tz_offset0 is None:
            tz_offset = 0
        else:
            tz_offset = int(tz_offset0)

    print("\nConnecting to AP...")
    while not esp.is_connected:
        try:
            esp.connect_AP(secrets["ssid"], secrets["password"])
        except RuntimeError as e:
            print("could not connect to AP, retrying: ", e)
            continue
    print("Connected to", str(esp.ssid, "utf-8"), "\tRSSI:", esp.rssi)

    make_clock()

    if use_ntp:
        if esp.is_connected:
            # Initialize the NTP object
            ntp = NTP(esp)
            #location = secrets.get("timezone", location)
            print("Using timezone: \'{}\'\ntimezone offset: {}".format(location, tz_offset))
        refresh_from_NTP()

def make_clock():
    global clock

    if use_flipclock:
        TRANSPARENT_INDEXES = range(11)
        # load the static sprite sheet
        static_ss, static_palette = adafruit_imageload.load("static_s.bmp")
        static_palette.make_transparent(0)

        gc.collect()
        # print(gc.mem_free())
        # load the anim sprite sheets
        top_anim_ss, top_anim_palette = adafruit_imageload.load(
            "top_anim_s_5f.bmp"
        )
        gc.collect()
        # print(gc.mem_free())
        btm_anim_ss, btm_anim_palette = adafruit_imageload.load(
            "btm_anim_s_5f.bmp"
        )
        # set the transparent color indexes in respective palettes
        for _ in TRANSPARENT_INDEXES:
            top_anim_palette.make_transparent(_)
            btm_anim_palette.make_transparent(_)
        gc.collect()
        print("make_clock(): mem_free=", gc.mem_free())
        try:
            clock = FlipClock(
                    static_ss,
                    static_palette,
                    top_anim_ss,
                    top_anim_palette,
                    btm_anim_ss,
                    btm_anim_palette,
                    static_ss.width // 3,
                    (static_ss.height // 4) // 2,
                    anim_frame_count=5,
                    anim_delay=0.02,
                    colon_color=0xFFFFFF,
                    dynamic_fading=use_dynamic_fading,
                    brighter_level=0.99,
                    darker_level=0.5,
                    medium_level=0.9,
                    h_pos=48,
                    v_pos=54)
            main_group = Group()
            main_group.append(clock)
            main_group.scale = 2  # don't go higher than 2. Then the 'flipping' will be very slow
            board.DISPLAY.show(main_group)
        except MemoryError as e:
            #print("setup(): Error: ", e)
            raise

def refresh_from_NTP():
    global default_dt, ntp
    default_dt = time.struct_time((2022, 9, 17, 12, 0, 0, 5, 261, -1))

    if use_ntp:
        if esp.is_connected:
            ntp_current_time = None
            timeout_cnt = 0
            while not ntp.valid_time:
                try:
                    ntp.set_time(tz_offset)
                except OSError:
                    pass
                timeout_cnt += 1
                time.sleep(5)
                if timeout_cnt > 10:
                    print("Timeout while trying to get ntp datetime to set the internal rtc")
                    break
            if ntp.valid_time:
                # Get the current time in seconds since Jan 1, 1970 and correct it for local timezone
                # (defined in secrets.h)
                ntp_current_time = time.time()
                # Convert the current time in seconds since Jan 1, 1970 to a struct_time
                default_dt = time.localtime(ntp_current_time)
                if not my_debug:
                    print("Internal clock synchronized from NTP pool, now =", default_dt)
        else:
            print("No internet. Setting default time")

def upd_tm():
    global clock, default_dt, hour_old, min_old
    TAG="upd_tm(): "
    tm_hour = 3
    tm_min = 4
    default_dt = time.localtime(time.time())
    p_time = False
    hh = default_dt[tm_hour]
    mm = default_dt[tm_min]
    if hh != hour_old:
       hour_old = hh
       p_time = True
    if mm != min_old:
        min_old = mm
        p_time = True
    if p_time:
        if my_debug:
            print(TAG+"default_dt[{}]={:02d} , default_dt[{}]={:02d}".format(tm_hour, default_dt[tm_hour], tm_min, default_dt[tm_min]))
        if use_flipclock:
            wait = 1
            try:
                fp = "{:02d}".format(default_dt[tm_hour])
                if my_debug:
                    print(TAG+"setting clock.first_pair:", fp)
                clock.first_pair = fp
                fp2 = clock.first_pair
                time.sleep(wait)
                if my_debug:
                    print("upd_tm(): clock.first_pair=", fp2)
                sp = "{:02d}".format(default_dt[tm_min])
                if my_debug:
                    print(TAG+"setting clock.second_pair:", sp)
                clock.second_pair = sp
                sp2  = clock.second_pair
                time.sleep(wait)
                if my_debug:
                    print("upd_tm(): clock.second_pair=", sp2)
                print("Time = {}:{}".format(fp2, sp2))
            except ValueError as e:
                print(TAG)
                raise
            #time.sleep(0.2)

def main():
    global start_t
    gc.collect()
    setup()
    if my_debug:
        print("main(): use_flipclock      =", "True" if use_flipclock else "False")
        print("        use_dynamic_fading =", "True" if use_dynamic_fading else "False")
        print("        use_ntp            =", "True" if use_ntp else "False")
    while True:
        try:
            curr_t = time.monotonic()
            elapsed_t = curr_t - start_t
            if elapsed_t >= 600:  # sync rtc with NTP datetime every 10 minutes
                start_t = curr_t
                refresh_from_NTP()
            upd_tm()
            time.sleep(0.75)
            pass
        except ValueError as e:
            print("ValueError", e)
            raise
        except KeyboardInterrupt:
            print("Keyboard interrupt. Exiting...")
            sys.exit()

if __name__ == '__main__':
    main()
