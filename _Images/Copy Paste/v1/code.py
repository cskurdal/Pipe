# SPDX-FileCopyrightText: 20211015 CS for CSigns
# SPDX-License-Identifier: MIT

import os
import gc
from collections import namedtuple
import microcontroller
import terminalio
import time
import board
import busio
from digitalio import DigitalInOut
import adafruit_requests as requests
import adafruit_esp32spi.adafruit_esp32spi_socket as socket
from adafruit_esp32spi import adafruit_esp32spi
from adafruit_pyportal import PyPortal
import adafruit_touchscreen
import displayio
from adafruit_bitmap_font import bitmap_font
from adafruit_button import Button
from adafruit_display_text.label import Label
import adafruit_imageload
import adafruit_bme680
import usb_hid
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keyboard_layout_us import KeyboardLayoutUS
from adafruit_hid.keycode import Keycode

_DEBUG = True

#Initialize i2c
i2c = board.I2C()
sensor = adafruit_bme680.Adafruit_BME680_I2C(i2c)


# Touchscreen setup
SCREEN_WIDTH = board.DISPLAY.width
SCREEN_HEIGHT = board.DISPLAY.height


# The keyboard object!
time.sleep(1)  # Sleep for a bit to avoid a race condition on some systems
keyboard = Keyboard(usb_hid.devices)
keyboard_layout = KeyboardLayoutUS(keyboard)  # We're in the US :)


#Colors
BLACK = 0x0
WHITE = 0xFFFFFF
GRAY = 0x888888
BLUE = 0x0000FF

BOX_WIDTH = 80 #box sizes in each corner for temp/humidity/BP/VOC

DISPLAY_LR_BUTTONS = False
USE_WIFI = False
 
# Backlight function
# Value between 0 and 1 where 0 is OFF, 0.5 is 50% and 1 is 100% brightness.
def set_backlight(val):
    val = max(0, min(1.0, val))
    board.DISPLAY.auto_brightness = False
    board.DISPLAY.brightness = val
 
pyportal = PyPortal() #for background

pyportal.set_background('/images/loading.bmp')

# Set the Backlight
#set_backlight(0.45)

ts = adafruit_touchscreen.Touchscreen(board.TOUCH_XL, board.TOUCH_XR,
                                      board.TOUCH_YD, board.TOUCH_YU,
                                      calibration=((5200, 59000),
                                                   (5800, 57000)),
                                      size=(SCREEN_WIDTH, SCREEN_HEIGHT))


# Get wifi details and more from a secrets.py file
try:
    from secrets import secrets
except ImportError:
    print("WiFi secrets are kept in secrets.py, please add them there!")
    raise


if USE_WIFI:
    # If you are using a board with pre-defined ESP32 Pins:
    esp32_cs = DigitalInOut(board.ESP_CS)
    esp32_ready = DigitalInOut(board.ESP_BUSY)
    esp32_reset = DigitalInOut(board.ESP_RESET)

    spi = busio.SPI(board.SCK, board.MOSI, board.MISO)
    esp = adafruit_esp32spi.ESP_SPIcontrol(spi, esp32_cs, esp32_ready, esp32_reset)

    requests.set_socket(socket, esp)

    if esp.status == adafruit_esp32spi.WL_IDLE_STATUS:
        print("ESP32 found and in idle mode")

    print("Firmware vers.", esp.firmware_version)
    print("MAC addr:", [hex(i) for i in esp.MAC_address])

    for ap in esp.scan_networks():
        print("\t%s\t\t RSSI: %d" % (str(ap["ssid"], "utf-8"), ap["rssi"]))

    print("Connecting to AP...")
    while not esp.is_connected:
        try:
            esp.connect_AP(secrets["ssid"], secrets["password"])
        except RuntimeError as e:
            print("could not connect to AP, retrying: ", e)
            continue

    print("Connected to", str(esp.ssid, "utf-8"), "\tRSSI:", esp.rssi)
    print("My IP address is", esp.pretty_ip(esp.ip_address))

    print("Ping google.com: %d ms" % esp.ping("google.com"))


APP_NAME = 'Copy Paste'

title_welcome = 'Welcome to {}'.format(APP_NAME)

print(title_welcome)

#esp._debug = True


# This group will make it easy for us to read a button press later.
buttons = []


'''
Button methods
'''
BUTTON_WIDTH = 150
BUTTON_HEIGHT = 150
BUTTON_MARGIN = 45
Coords = namedtuple("Point", "x y")

# Some button functions
def button_grid(row, col):
    return Coords(BUTTON_MARGIN * (row + 1) + BUTTON_WIDTH * row + 20,
                  BUTTON_MARGIN * (col + 1) + BUTTON_HEIGHT * col + 40)

def add_button(row, col, label, width=1, color=WHITE, text_color=BLACK):
    pos = button_grid(row, col)

    new_button = Button(x=pos.x, y=pos.y,
                        width=BUTTON_WIDTH * width + BUTTON_MARGIN * (width - 1),
                        height=BUTTON_HEIGHT, label=label, label_font=font,
                        label_color=text_color, fill_color=color, style=Button.ROUNDRECT)
                        
    buttons.append(new_button)
    return new_button


def add_button(x, y, label, width, height, color=WHITE, text_color=BLACK):
    new_button = Button(x=x, y=y,
                        width = width,
                        height = height, label=label, label_font=font,
                        label_color=text_color, fill_color=color
                        #, style=Button.ROUNDRECT
                        )
                        
    buttons.append(new_button)
    return new_button

def find_button(label):
    result = None
    for _, btn in enumerate(buttons):
        if btn.label == label:
            result = btn
    return result



print("Loading")

splash = displayio.Group() # The Main Display Group

# Make a background color fill
color_bitmap = displayio.Bitmap(SCREEN_WIDTH, SCREEN_HEIGHT, 1)
color_palette = displayio.Palette(1)
color_palette[0] = BLACK
bg_sprite = displayio.TileGrid(color_bitmap,
                               pixel_shader=color_palette,
                               x=0, y=0)
splash.append(bg_sprite)


# Set the font and preload letters
font = bitmap_font.load_font("/fonts/Arial-ItalicMT-23.bdf")
#font = bitmap_font.load_font("/fonts/Helvetica-Bold-16.bdf")
#font = terminalio.FONT
font.load_glyphs(b'abcdefghjiklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890- ()')


label_center = Label(font, text="None", color=BLUE)

view1 = displayio.Group(x = int(SCREEN_WIDTH * 0.42), y = int(SCREEN_HEIGHT * 0.84)) # Group for View 1 objects


HALF_WIDTH = int(SCREEN_WIDTH/2)
HALF_HEIGHT = int(SCREEN_HEIGHT/2)

splash.append(add_button(0, 0, "Copy", width=HALF_WIDTH, height=HALF_HEIGHT, color=GRAY, text_color=BLACK))
splash.append(add_button(HALF_WIDTH, 0, "Paste", width=HALF_WIDTH, height = HALF_HEIGHT, color=GRAY, text_color=BLACK))
splash.append(add_button(0, HALF_HEIGHT, "Undo", width=HALF_WIDTH, height = HALF_HEIGHT, color=GRAY, text_color=BLACK))
splash.append(add_button(HALF_WIDTH, HALF_HEIGHT, "Task Manager", width=HALF_WIDTH, height = HALF_HEIGHT, color=GRAY, text_color=BLACK))

#Append after buttons to be on top
splash.append(view1)

view1.append(label_center)


#Show the Group
board.DISPLAY.show(splash)



last_op = ""
button = ""
c = 0
update = False
control_key = Keycode.CONTROL

while True:
    point = ts.touch_point
     
    c += 1
    
    if point is not None:
        # Button Down Events
        for _, b in enumerate(buttons):
            if b.contains(point) and button == "":
                b.selected = True
                button = b.label
    elif button != "":
        # Button Up Events
        op_button = find_button(last_op)
        
        # Deselect the last operation when certain buttons are pressed
        if op_button is not None:        
            label_center.text = op_button + '-' + button
            time.sleep(1)
            
        b = find_button(button)
        
        if b is not None:
            #set when button is released
            label_center.text = "{}".format(b.label)

            if b.label == 'Copy':
                keyboard.press(control_key, Keycode.C)  # "Press"...
                keyboard.release_all()  # ..."Release"!
            elif b.label == 'Paste':
                keyboard.press(control_key, Keycode.V)  # "Press"...
                keyboard.release_all()  # ..."Release"!
            elif b.label == 'Undo':
                keyboard.press(control_key, Keycode.Z)  # "Press"...
                keyboard.release_all()  # ..."Release"!
            elif b.label == 'Task Manager':
                keyboard.press(control_key, Keycode.SHIFT, Keycode.ESCAPE)  # "Press"...
                keyboard.release_all()  # ..."Release"!

            b.selected = False

        button = ""

    time.sleep(0.05)
    
