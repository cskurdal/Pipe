# SPDX-FileCopyrightText: 20211015 CS for CSigns
# SPDX-License-Identifier: MIT

import os
import gc
import adafruit_logging as logging
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
#import adafruit_bme680
from adafruit_display_shapes.circle import Circle
from math import sqrt

_DEBUG = True

#Initialize i2c
#i2c = board.I2C()
#sensor = adafruit_bme680.Adafruit_BME680_I2C(i2c)


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


APP_NAME = 'radio'

logger = logging.getLogger(APP_NAME)
logger.setLevel(logging.DEBUG)

title_welcome = 'Welcome to {}'.format(APP_NAME)

print(title_welcome)

#esp._debug = True


# This group will make it easy for us to read a button press later.
buttons = []


'''
Button methods
'''
BUTTON_WIDTH = 55
BUTTON_HEIGHT = 55
BUTTON_MARGIN = 10
Coords = namedtuple("Point", "x y")

# Some button functions
def button_grid(row, col):
    return Coords(BUTTON_MARGIN * (row + 1) + BUTTON_WIDTH * row + 20,
                  BUTTON_MARGIN * (col + 1) + BUTTON_HEIGHT * col + 40)

def add_button(row, col, label, width=1, color=WHITE, text_color=BLACK, font = None):
    pos = button_grid(row, col)

    new_button = Button(x=pos.x, y=pos.y,
                        width=BUTTON_WIDTH * width + BUTTON_MARGIN * (width - 1),
                        height=BUTTON_HEIGHT, label=label, label_font=font,
                        label_color=text_color, fill_color=color, style=Button.ROUNDRECT)
                        
    buttons.append(new_button)
    return new_button


def add_button2(x, y, label, width, height, color=WHITE, text_color=BLACK):
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
'''
color_bitmap = displayio.Bitmap(SCREEN_WIDTH, SCREEN_HEIGHT, 1)
color_palette = displayio.Palette(1)
color_palette[0] = BLACK
bg_sprite = displayio.TileGrid(color_bitmap,
                               pixel_shader=color_palette,
                               x=0, y=0)
splash.append(bg_sprite)
'''

# Set the font and preload letters
#font = bitmap_font.load_font("/fonts/Arial-ItalicMT-23.bdf")
#font = bitmap_font.load_font("/fonts/Calculator-25.bdf")
#font = bitmap_font.load_font("/fonts/Calculator-50.bdf")
font = bitmap_font.load_font("/fonts/WhiteRabbit-50.bdf")
#font = bitmap_font.load_font("/fonts/Helvetica-Bold-16.bdf")
font_terminal = terminalio.FONT
    
#font.load_glyphs(b'abcdefghjiklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890- ()')


label_freq0 = Label(font, color=BLUE)
label_freq = Label(font, color=BLUE)

view0 = displayio.Group(x = int(SCREEN_WIDTH * 0.5), y = int(SCREEN_HEIGHT * 0.07)) # Group for View 1 objects
view1 = displayio.Group(x = int(SCREEN_WIDTH * 0.5), y = int(SCREEN_HEIGHT * 0.2)) # Group for View 1 objects


splash.append(add_button(row = 0, col = 0, label = "7", width=1, color=GRAY, text_color=BLACK, font = font))
splash.append(add_button(row = 1, col = 0, label = "8", width=1, color=GRAY, text_color=BLACK, font = font))
splash.append(add_button(row = 2, col = 0, label = "9", width=1, color=GRAY, text_color=BLACK, font = font))

splash.append(add_button(row = 0, col = 1, label = "4", width=1, color=GRAY, text_color=BLACK, font = font))
splash.append(add_button(row = 1, col = 1, label = "5", width=1, color=GRAY, text_color=BLACK, font = font))
splash.append(add_button(row = 2, col = 1, label = "6", width=1, color=GRAY, text_color=BLACK, font = font))

splash.append(add_button(row = 0, col = 2, label = "1", width=1, color=GRAY, text_color=BLACK, font = font))
splash.append(add_button(row = 1, col = 2, label = "2", width=1, color=GRAY, text_color=BLACK, font = font))
splash.append(add_button(row = 2, col = 2, label = "3", width=1, color=GRAY, text_color=BLACK, font = font))

splash.append(add_button(row = 1, col = 3, label = "0", width=1, color=GRAY, text_color=BLACK, font = font))
splash.append(add_button(row = 2, col = 3, label = "Step", width=1, color=GRAY, text_color=BLACK, font = font_terminal))

button_cancel = add_button(row = 0, col = 3, label = "Cancel", width=1, color=GRAY, text_color=BLACK, font = font_terminal)


#Append after buttons to be on top
splash.append(view0)
splash.append(view1)

view0.append(label_freq0)
view1.append(label_freq)

#Show the Group
board.DISPLAY.show(splash)

last_op = ""
button = ""
c = 0
update = False
current_frequency = 7040.0
setting_frequency = ''
FREQUECNY_LEFT_DIGITS = 8 #Digits to the left of the decimal point display up to 30000000.0 Hz
FREQUECNY_RIGHT_DIGITS = 1 #Digits to the right of the decimal point  

gc.collect()


label_freq.text = str(current_frequency)

circle_r = int(SCREEN_HEIGHT * 0.3)
circle_x = int(SCREEN_WIDTH * 0.7)
circle_y =int(SCREEN_HEIGHT * 0.6)

logger.debug("circle x/y, r: {}/{}, {}".format(circle_x, circle_y, circle_r))

circle = Circle(circle_x, circle_y, circle_r, fill = None, outline = WHITE)

splash.append(circle)
last_point = None
current_point = None
current_step_index = 1
steps = [10, 1, 0.1]

#Set _ over initial step
label_freq0.text = "   _"


'''
returns true/false if (x,y) are inside a circle with a center of (circle_x, circle_y) with a radius of r
'''
def in_circle(x, y, circle_x, circle_y, r):
    return bool(sqrt(abs(x-circle_x)**2 + abs(y-circle_y)**2) < r)

'''
    return distance between two points
'''
def get_magnitude(p1, p2, absolute_value = False):
    m = sqrt((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2)
    
    if absolute_value:
        return abs(m)
    else:
        return m

delta = []
MAGNITUDE_MINIMUM = 8 #must be more than this magnitude to process knob move

while True:
    point = ts.touch_point
     
    c += 1
    
    if point is not None:
        button_pressed = False
        
        # Button Down Events
        for _, b in enumerate(buttons):
            if b.contains(point) and button == "":
                b.selected = True
                button = b.label
                button_pressed = True
                break
           
        logger.debug("point: {}".format(point))
        
        #Check for presses in the circle
        if not button_pressed and in_circle(point[0], point[1], circle_x, circle_y, circle_r):            
            if last_point is None:
                last_point = point
            elif last_point != point:
                #a last point is set check vector direction
                #Determine if direction is CW or CCW
                
                m = get_magnitude(point, last_point, True)
                      
                if _DEBUG:
                    delta.append(m)

                if m > MAGNITUDE_MINIMUM:          
                    
                    cw = None
                    
                    if circle_x <= point[0] and point[1] <= circle_y: #upper right quadrant (I)
                        if last_point[0] < point[0] or last_point[1] < point[1]:
                            cw = True
                        elif last_point[0] > point[0] or last_point[1] > point[1]:
                            cw = False
                    elif point[0] < circle_x and point[1] < circle_y: #upper left quadrant (II)                    
                        if last_point[0] < point[0] or last_point[1] > point[1]:
                            cw = True
                        elif last_point[0] > point[0] or last_point[1] < point[1]:
                            cw = False
                    elif point[0] <= circle_x and circle_y <= point[1]: #lower left quadrant (III)
                        if last_point[0] > point[0] or last_point[1] > point[1]:
                            cw = True
                        elif last_point[0] < point[0] or last_point[1] < point[1]:
                            cw = False                
                    elif circle_x < point[0] and circle_y < point[1]: #lower right quadrant (IV)
                        if last_point[0] > point[0] or last_point[1] < point[1]:
                            cw = True
                        elif last_point[0] < point[0] or last_point[1] > point[1]:
                            cw = False
                    
                    '''
                    if ((point[0] >= circle_x and (last_point[0] < point[0] or last_point[1] < point[1]))  #on the right side and down
                            or (point[0] < circle_x and last_point[1] > point[1])):  #on the left side and up):
                        current_frequency += steps[current_step_index]
                        cw = True
                    else:
                        current_frequency -= steps[current_step_index]
                        cw = False
                    '''
                    
                    if cw is not None:
                        if cw:
                            current_frequency += steps[current_step_index]
                        else:
                            current_frequency -= steps[current_step_index]
                            
                        if _DEBUG:
                            label_freq.text = "{:.1f}Hz-{}-{}".format(current_frequency, int(m), sum(delta)/len(delta))
                        else:
                            label_freq.text = "{:.1f}Hz".format(current_frequency)
                
                last_point = point
        else:
            last_point = None #Reset
    elif button != "":
        # Button Up Events
        op_button = find_button(last_op)
        
        # Deselect the last operation when certain buttons are pressed
        if op_button is not None:        
            label_freq.text = op_button + '-' + button
            time.sleep(1)
            
        b = find_button(button)
        
        if b is not None:
            #set when button is released
            logger.debug("{} before. label/setting_frequency: {}/{}".format(c, b.label, setting_frequency))
            
            if b.label in ('0', '1', '2', '3', '4', '5', '6', '7', '8', '9'):
                #if starting to set then initialize setting string
                if len(setting_frequency) == 0:
                    splash.append(button_cancel)
                    setting_frequency = '_' * FREQUECNY_LEFT_DIGITS + '.' + '_' * FREQUECNY_RIGHT_DIGITS
                    
                
                setting_frequency = setting_frequency.replace('_', b.label, 1)
                
                #When all digits have been set then set current_frequency
                if '_' not in setting_frequency:
                    #Set frequency
                    logger.debug("setting_frequency: " + setting_frequency)
                    current_frequency = float(setting_frequency)
                    setting_frequency = '' #Reset
            elif b.label == 'Step':
                current_step_index += 1
                
                if current_step_index >= len(steps):
                    current_step_index = 0
                    
                #    
                
                freq_str = "{:.1f}".format(current_frequency)
                step_str = "{:.1f}".format(steps[current_step_index])
                
                step_str = " " * (len(freq_str) - len(step_str)) + step_str
                
                step_str = step_str.replace('.', ' ').replace('1', '_').replace('0', ' ')
                
                label_freq0.text = step_str
            elif b.label == 'Cancel':
                splash.pop()
                setting_frequency = '' #Reset

            if len(setting_frequency) > 0:
                label_freq.text = "{}Hz".format(setting_frequency)
            else:
                label_freq.text = "{:.1f}Hz".format(current_frequency)

            logger.debug("{} after. label/setting_frequency: {}/{}".format(c, b.label, setting_frequency))
            
            b.selected = False

        button = ""

    time.sleep(0.05)
    #time.sleep(0.003)
    
