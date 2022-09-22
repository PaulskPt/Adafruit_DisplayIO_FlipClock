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
from rtc import RTC
#import busio
from digitalio import DigitalInOut
from adafruit_esp32spi import adafruit_esp32spi
import adafruit_esp32spi.adafruit_esp32spi_socket as socket
from displayio import Group
import adafruit_imageload
from adafruit_displayio_flipclock.flip_clock import FlipClock
import adafruit_requests as requests

""" Global flags """
my_debug = False
use_ntp = True
use_local_time = None
use_flipclock = True
use_dynamic_fading = True

""" Other global variables """
rtc = None
esp = None
aio_username = None
aio_key = None
location = None
default_dt = None
main_group = None
clock = None
display = board.DISPLAY
start_t = time.monotonic()
tm_offset = None
tz_offset = 0
hour_old = 0
min_old = 0

def setup():
    global rtc, esp, tz_offset, use_local_time, aio_username, aio_key, location

    rtc = RTC()  # create the built-in rtc object

    esp32_cs = DigitalInOut(board.ESP_CS)
    esp32_ready = DigitalInOut(board.ESP_BUSY)
    esp32_reset = DigitalInOut(board.ESP_RESET)
    #spi = busio.SPI(board.SCK, board.MOSI, board.MISO)
    spi = board.SPI()
    esp = adafruit_esp32spi.ESP_SPIcontrol(spi, esp32_cs, esp32_ready, esp32_reset)
    requests.set_socket(socket, esp)

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

    # Get our username, key and desired timezone
    aio_username = secrets["aio_username"]
    aio_key = secrets["aio_key"]

    lt = secrets.get("LOCAL_TIME_FLAG", None)
    if lt is None:
        use_local_time = False
    else:
        lt2 = int(lt)
        if my_debug:
            print("lt2=", lt2)
        use_local_time = True if lt2 == 1 else False

    if use_local_time:
        location = secrets.get("timezone", None)
        if location is None:
            location = 'Not set'
            tz_offset = 0
        else:
            tz_offset0 = secrets.get("tz_offset", None)
            if tz_offset0 is None:
                tz_offset = 0
            else:
                tz_offset = int(tz_offset0)
    else:
        location = 'Etc/GMT'
        tz_offset = 0

    print("\nConnecting to AP...")
    while not esp.is_connected:
        try:
            esp.connect_AP(secrets["ssid"], secrets["password"])
        except RuntimeError as e:
            print("could not connect to AP, retrying: ", e)
            continue
    print("Connected to", str(esp.ssid, "utf-8"), "\tRSSI:", esp.rssi)
    gc.collect()
    make_clock()

    refresh_from_NTP()

def make_clock():
    global clock

    if use_flipclock:
        TRANSPARENT_INDEXES = range(11)
        static_ss, static_palette = adafruit_imageload.load("static_s.bmp")
        static_palette.make_transparent(0)

        gc.collect()
        top_anim_ss, top_anim_palette = adafruit_imageload.load(
            "top_anim_s_5f.bmp"
        )
        gc.collect()
        btm_anim_ss, btm_anim_palette = adafruit_imageload.load(
            "btm_anim_s_5f.bmp"
        )
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
                    colon_color=0x00FF00,
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

def dt_adjust():
    global default_dt
    if my_debug:
        print("dt_adjust(): use_local_time= {}".format("True" if use_local_time else "False"))
        print("             tz_offset=", tz_offset)
        print("             location=", location)

    default_dt = time.localtime(time.time())

def refresh_from_NTP():
    global default_dt, tm_offset
    TAG = "refresh_from_NTP(): "
    TIME_URL = "https://io.adafruit.com/api/v2/{:s}/integrations/".format(aio_username)
    TIME_URL += "time/strftime?x-aio-key={:s}&tz={}".format(aio_key, location)
    TIME_URL += "&fmt=%25Y-%25m-%25d+%25H%3A%25M%3A%25S.%25L+%25j+%25u+%25z+%25Z"
    # Create string (see a) above)

    gc.collect()

    if use_ntp:
        if esp.is_connected:
            # esp._debug = True
            if my_debug:
                t = TAG + "\nFetching time from Adafruit IO {}".format(TIME_URL)
                print(t)
            try:
                print("request=", TIME_URL)
                response = requests.get(TIME_URL)
            except RuntimeError as e:
                print(TAG+"Sending request failed")
                print("   ", e)
                if default_dt is None:
                    # default_dt has not been set before. Set it.
                    dt_to_set = time.struct_time((2022, 9, 17, 12, 0, 0, 5, 261, -1))
                    rtc.datetime = dt_to_set
                    time.sleep(0.5)
                    default_dt = time.gmt(time.time()+tz_offset)
                    print(TAG+"Setting the built-in RTC to:", dt_to_set)
                return

            if response is not None:
                n = response.text.find("error")
                if n >= 0:
                    print(TAG+"\nResponse from AIO TIME Service contains error:")
                    print(response.text)
                    print("Exiting function.")
                    return

                dt_lst = response.text.split(" ")
                response.close()
                date_lst = dt_lst[0].split('-')
                time_lst = dt_lst[1].split(':')
                if my_debug:
                    print("dt_lst", dt_lst)
                    print("date_lst", date_lst)
                    print("time_lst", time_lst)
                if not my_debug:
                    print("-" * 55)
                    t = TAG + "\nTIME received: {}".format(response.text)
                    print(t)
                dt_to_set = time.struct_time((int(date_lst[0]), int(date_lst[1]), int(date_lst[2]), int(time_lst[0]), 
                int(time_lst[1]), int(round(float(time_lst[2]))), int(dt_lst[2]), int(dt_lst[3]), -1))
                #dt_to_set = time.struct_time((tm_year, tm_month, tm_date, tm_hour, tm_min, tm_sec, tm_yday, tm_wday, -1))
                if my_debug:
                    print("Setting the built-in RTC to:", dt_to_set)
                rtc.datetime = dt_to_set
                time.sleep(0.5)
                
                dt_adjust()

                if my_debug:
                    print("Internal clock synchronized from NTP pool, now =", default_dt)
                if not my_debug:
                    print("-" * 55)
            else:
                print("response is None")
        else:
            print("No internet. Setting default time")

def upd_tm():
    global clock, default_dt, hour_old, min_old
    TAG="upd_tm(): "
    tm_hour = 3
    tm_min = 4
    tm_sec = 5

    dt_adjust()

    if my_debug:
        print(TAG+"default_dt=", default_dt)
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
                    print(TAG+"clock.first_pair=", fp2)
                sp = "{:02d}".format(default_dt[tm_min])
                if my_debug:
                    print(TAG+"setting clock.second_pair:", sp)
                clock.second_pair = sp
                sp2  = clock.second_pair
                time.sleep(wait)
                if my_debug:
                    print(TAG+"clock.second_pair=", sp2)
                print(TAG+"Time = {}:{}".format(fp2, sp2))
            except ValueError as e:
                print(TAG)
                raise
            #time.sleep(0.2)

def main():
    global start_t
    gc.collect()
    setup()
    print("main(): use_flipclock      =", "True" if use_flipclock else "False")
    print("        use_dynamic_fading =", "True" if use_dynamic_fading else "False")
    print("        use_ntp            =", "True" if use_ntp else "False")
    print("        use_local_time     =", "True" if use_local_time else "False")
    print("        location           =", location)

    while True:
        try:
            curr_t = time.monotonic()
            elapsed_t = curr_t - start_t
            if elapsed_t >= 600:  # sync rtc with NTP datetime every 10 minutes
                print("elapsed_t=", elapsed_t)
                start_t = curr_t
                refresh_from_NTP()
                gc.collect()
            upd_tm()
            gc.collect()
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
