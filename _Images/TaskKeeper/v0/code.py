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

_DEBUG = True

#Initialize i2c
i2c = board.I2C()
sensor = adafruit_bme680.Adafruit_BME680_I2C(i2c)


# Touchscreen setup
SCREEN_WIDTH = board.DISPLAY.width
SCREEN_HEIGHT = board.DISPLAY.height


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

#https://www.korwelphotography.com/macro-monday-bumblebee/
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


APP_NAME = 'Task Keeper'

title_welcome = 'Welcome to {}'.format(APP_NAME)

print(title_welcome)

#esp._debug = True


# This group will make it easy for us to read a button press later.
buttons = []


'''
Button methods
'''

num_buttons_x = 3
num_buttons_y = 2

BUTTON_WIDTH = int(SCREEN_WIDTH / (num_buttons_x + 0.5))
BUTTON_HEIGHT = int(SCREEN_HEIGHT / (num_buttons_y + 1))
BUTTON_MARGIN = 8
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
                        label_color=text_color, fill_color=BLUE, style=Button.ROUNDRECT)
                        
    buttons.append(new_button)
    return new_button

def find_button(label):
    result = None
    for _, btn in enumerate(buttons):
        if btn.label == label:
            result = btn
    return result



print("Loading")

# Set the font and preload letters

font = bitmap_font.load_font("/fonts/Arial-ItalicMT-23.bdf")
#font = bitmap_font.load_font("/fonts/Helvetica-Bold-16.bdf")

font.load_glyphs(b'abcdefghjiklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890- ()')
font = terminalio.FONT

splash = displayio.Group() # The Main Display Group

# Make a background color fill
color_bitmap = displayio.Bitmap(SCREEN_WIDTH, SCREEN_HEIGHT, 1)
color_palette = displayio.Palette(1)
color_palette[0] = GRAY
bg_sprite = displayio.TileGrid(color_bitmap,
                               pixel_shader=color_palette,
                               x=0, y=0)
splash.append(bg_sprite)


splash.append(add_button(0, 0, "Task 1, 0", width=1, color=WHITE, text_color=BLACK))
splash.append(add_button(1, 0, "Task 2, 0", width=1, color=WHITE, text_color=BLACK))
splash.append(add_button(2, 0, "Task 3, 0", width=1, color=WHITE, text_color=BLACK))
splash.append(add_button(0, 1, "Task 4, 0", width=1, color=WHITE, text_color=BLACK))
splash.append(add_button(1, 1, "Task 5, 0", width=1, color=WHITE, text_color=BLACK))
splash.append(add_button(2, 1, "Task 6, 0", width=1, color=WHITE, text_color=BLACK))


#Show the Group
board.DISPLAY.show(splash)


#Setup corner views
left_view = displayio.Group(x = 0, y = int(SCREEN_HEIGHT * 0.25)) # Group for temp View in upper left corner
right_view = displayio.Group(x = SCREEN_WIDTH - BOX_WIDTH, y = 0) # Group for temp View in upper left corner

label_center = Label(font, text="0:00", color=BLUE)

view1 = displayio.Group(x = 0, y = int(SCREEN_HEIGHT * 0.92)) # Group for View 1 objects

view1.append(label_center)

splash.append(view1)
splash.append(left_view)
splash.append(right_view)


# This will handel switching Images and Icons
def set_image(group, filename):
    """Set the image file for a given goup for display.
    This is most useful for Icons or image slideshows.
        :param group: The chosen group
        :param filename: The filename of the chosen image
    """
    print("Set image to ", filename)
    if group:
        group.pop()

    if not filename:
        return  # we're done, no icon desired

    # CircuitPython 6 & 7 compatible
    image_file = open(filename, "rb")
    #image = displayio.OnDiskBitmap(image_file)
    #image_sprite = displayio.TileGrid(image, pixel_shader=getattr(image, 'pixel_shader', displayio.ColorConverter()))

    # # CircuitPython 7+ compatible
    image = displayio.OnDiskBitmap(filename)
    image_sprite = displayio.TileGrid(image, pixel_shader=image.pixel_shader)

    group.append(image_sprite)


class Task:
    _name = None
    _active = False
    _elapsed_time = 0
    _last_update_time = None
    
    def __init__(self, n, active = False):
        self._name = n
        self._active = active
        

class Tasks:
    _tasks = []
    _current = None
    
    def __init__(self):
        pass
        
    def add(self, task):
        self._tasks.append(task)
        return self
        
    def set_current(self, task):
        self._current = task
        
    def get_total_elapsed_time(self):
        et = 0
        for t in self._tasks:
            et += t._elapsed_time
            
        return et
    

last_op = ""
button = ""
c = 0
update = False
current_button_start_time = None
current_button = None
refresh_time = None

tasks = Tasks()

t1 = Task("Task 1")
t2 = Task("Task 2")
t3 = Task("Task 3")
t4 = Task("Task 4")
t5 = Task("Task 5")
t6 = Task("Task 6")

tasks.add(t1).add(t2).add(t3).add(t4).add(t5).add(t6)

#from: https://learn.adafruit.com/pyportal-calculator-using-the-displayio-ui-elements/circuitpython-code
while True:
    point = ts.touch_point
     
    c += 1
    
    #Update label/time
    if current_button is not None and (not refresh_time or (time.monotonic() - refresh_time) > 1):
        split_array = current_button.label.split(', ')
        
        et = float(split_array[1]) + time.monotonic() - current_button_start_time
        
        current_button_start_time = time.monotonic()
        
        current_button.label = "{}, {}".format(split_array[0], et)
        
        if _DEBUG:
            label_center.text = current_button.label
        
        refresh_time = time.monotonic()
    
    if point is not None:
        # Button Down Events
        for _, b in enumerate(buttons):
            if b.contains(point) and button == "":
                b.selected = True
                current_button_start_time = time.monotonic()
                current_button = b
                button = b.label
    elif button != "":
        # Button Up Events
        op_button = find_button(last_op)
        
        # Deselect the last operation when certain buttons are pressed
        if op_button is not None:        
            label_center.text = op_button + '-' + button
            #time.sleep(1)
            
        b = find_button(button)
        
        if b is not None:
            #set when button is released
            label_center.text = "{} - {} - {} - {} - {}".format(str(current_button),c, split_array[1], (time.monotonic() - current_button_start_time), current_button_start_time)

            for button in buttons:
                if b != button:
                    button.selected = False

        button = ""
        
        
    if update:
        pass

    time.sleep(0.05)
    
