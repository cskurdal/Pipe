# SPDX-FileCopyrightText: 20211002 CS for CSigns
# SPDX-License-Identifier: MIT

import os
import gc
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

i2c = board.I2C()
sensor = adafruit_bme680.Adafruit_BME680_I2C(i2c)

# Touchscreen setup
SCREEN_WIDTH = board.DISPLAY.width
SCREEN_HEIGHT = board.DISPLAY.height

BLUE = 0x0000FF
BLACK = 0x0
ORANGE = 0xE39300
WHITE = 0xFFFFFF

BOX_WIDTH = 80 #box sizes in each corner for temp/humidity/BP/VOC

DISPLAY_LR_BUTTONS = False
PROCESS_BUTTON_PRESSES = True
USE_WIFI = False

STATION_ID = "9449424"   # tide location, find yours here: https://tidesandcurrents.noaa.gov/

DATA_SOURCE = (
    "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter?date=today&product=predictions&datum=mllw&interval=hilo&format=json&units=metric&time_zone=lst_ldt&station="
    + STATION_ID
)

DATA_LOCATION = ["predictions"]


# Backlight function
# Value between 0 and 1 where 0 is OFF, 0.5 is 50% and 1 is 100% brightness.
def set_backlight(val):
    val = max(0, min(1.0, val))
    board.DISPLAY.auto_brightness = False
    board.DISPLAY.brightness = val
 
pyportal = PyPortal() #for background


# Connect to the internet and get local time
#pyportal.get_local_time()

pyportal.set_background('/images/loading.bmp')
time.sleep(5) #show the back ground for 5 seconds more

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


APP_NAME = 'Buoy'

title_welcome = 'Welcome to {}'.format(APP_NAME)

print(title_welcome)


#esp._debug = True

print("Loading")

# Set the font and preload letters
font0 = terminalio.FONT
font2 = bitmap_font.load_font("/fonts/Arial-ItalicMT-23.bdf")
font = bitmap_font.load_font("/fonts/Helvetica-Bold-16.bdf")
font.load_glyphs(b'abcdefghjiklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890- ()')

splash = displayio.Group() # The Main Display Group

board.DISPLAY.show(splash)


#Setup corner views
lower_center_view = displayio.Group(x = BOX_WIDTH, y = SCREEN_HEIGHT - BOX_WIDTH)

view1 = displayio.Group(x = BOX_WIDTH, y = 0) # Group for View 1 objects


splash.append(view1)
splash.append(lower_center_view)

# This group will make it easy for us to read a button press later.
buttons = []

if DISPLAY_LR_BUTTONS:
    # Main User Interface Buttons
    button_left = Button(x=0, y=BOX_WIDTH,
                         width=BOX_WIDTH, height=SCREEN_HEIGHT - (2 * BOX_WIDTH),
                         label="<<", label_font=font, label_color=0xff7e00,
                         fill_color=0x5c5b5c, outline_color=0x767676,
                         selected_fill=0x1a1a1a, selected_outline=0x2e2e2e,
                         selected_label=0x525252)
    buttons.append(button_left)  # adding this button to the buttons group
     
    button_right = Button(x=SCREEN_WIDTH - BOX_WIDTH, y=BOX_WIDTH,
                          width=BOX_WIDTH, height=SCREEN_HEIGHT - (2 * BOX_WIDTH),
                          label=">>", label_font=font, label_color=0xff7e00,
                          fill_color=0x5c5b5c, outline_color=0x767676,
                          selected_fill=0x1a1a1a, selected_outline=0x2e2e2e,
                          selected_label=0x525252)
    buttons.append(button_right)  # adding this button to the buttons group

    # Add all of the main buttons to the splash Group
    for b in buttons:
        splash.append(b)

board.DISPLAY.show(splash)

center_label = Label(font0, color=WHITE)

lower_center_view.append(center_label)

# Create the text label
temp_label = Label(font, color=BLUE)

# Set the location
temp_label.x = 0 #int(BOX_WIDTH / 2)
temp_label.y = int(BOX_WIDTH / 2)

button_temp = Button(x=0, y=0,
                         width = BOX_WIDTH, height =BOX_WIDTH,
                         label="", label_font=font, label_color=0xff7e00,
                         fill_color=0x5c5b5c, outline_color=0x767676,
                         selected_fill=0x1a1a1a, selected_outline=0x2e2e2e,
                         selected_label=0x525252)

buttons.append(button_temp)

splash.append(button_temp)


# Create the text label
humidity_label = Label(font, text="", color=BLUE)

# Set the location
humidity_label.x = 0
humidity_label.y = int(BOX_WIDTH / 2)

button_humidity = Button(x=SCREEN_WIDTH - BOX_WIDTH, y=0,
                         width = BOX_WIDTH, height =BOX_WIDTH,
                         label="", label_font=font, label_color=0xff7e00,
                         fill_color=0x5c5b5c, outline_color=0x767676,
                         selected_fill=0x1a1a1a, selected_outline=0x2e2e2e,
                         selected_label=0x525252)

buttons.append(button_humidity)
splash.append(button_humidity)

#pressure - lower left
button_pressure = Button(x = 0, y = SCREEN_HEIGHT - BOX_WIDTH,
                         width = BOX_WIDTH, height =BOX_WIDTH,
                         label="", label_font=font, label_color=0xff7e00,
                         fill_color=0x5c5b5c, outline_color=0x767676,
                         selected_fill=0x1a1a1a, selected_outline=0x2e2e2e,
                         selected_label=0x525252)
                         
buttons.append(button_pressure)
splash.append(button_pressure)


#VOC - lower right
button_voc = Button(x = SCREEN_WIDTH - BOX_WIDTH, y = SCREEN_HEIGHT - BOX_WIDTH,
                    width = BOX_WIDTH, height =BOX_WIDTH,
                    label="", label_font=font, label_color=0xff7e00,
                         fill_color=0x5c5b5c, outline_color=0x767676,
                         selected_fill=0x1a1a1a, selected_outline=0x2e2e2e,
                         selected_label=0x525252)

buttons.append(button_voc)
splash.append(button_voc)


feed1_label = Label(font, text="", color=ORANGE)
feed1_label.x = 0
feed1_label.y = 0
view1.append(feed1_label)


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

    # CircuitPython 7+ compatible
    image = displayio.OnDiskBitmap(filename)
    image_sprite = displayio.TileGrid(image, pixel_shader=image.pixel_shader)

    group.append(image_sprite)


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

def find_button(label):
    result = None
    for _, btn in enumerate(buttons):
        if btn.label == label:
            result = btn
    return result


def get_tide_info():
    """Fetch JSON tide time info and return it."""

    # Get raw JSON data
    raw_info = pyportal.network.fetch_data(DATA_SOURCE, json_path=DATA_LOCATION)

    # Return will be a dictionary of lists containing tide times
    new_tide_info = {"H": [], "L": []}

    # Parse out the tide time info
    for info in raw_info[0]:
        tide_type = info["type"]
        tide_time = info["t"].split(" ")[1]
        new_tide_info[tide_type].append(tide_time)

    return new_tide_info


#From:https://learn.adafruit.com/making-a-pyportal-user-interface-displayio/text-box
# Used to calculate vertical text height for Top Alignment
text_hight = Label(font, text="M", color=0x03AD31)

# return a string with word wrapping using PyPortal.wrap_nicely
def text_box(target, top, max_chars, string):
    text = pyportal.wrap_nicely(string, max_chars)
    new_text = ""
    test = ""
    for w in text:
        new_text += '\n'+w
        test += 'M\n'
    text_hight.text = test
    glyph_box = text_hight.bounding_box
    print(glyph_box[3])
    target.text = "" # Odd things happen without this
    target.y = round(glyph_box[3]/2)+top
    target.text = new_text



# You will usually have to add an offset to account for the temperature of
# the sensor. This is usually around 5 degrees but varies by use. Use a
# separate temperature sensor to calibrate this one.
temperature_offset = 0 #-1.8

#Initialize while loop variables
refresh_time = None
refresh_time2 = None
last_op = ""
button = ""
c = 0

#from: https://learn.adafruit.com/pyportal-calculator-using-the-displayio-ui-elements/circuitpython-code
while True:
    point = ts.touch_point
    
    #Refresh sensor values every 5 seconds
    if not refresh_time2 or (time.monotonic() - refresh_time2) > 5:
        c += 1 #Increment loop counter
        
        #Set temperatures
        tempC = sensor.temperature + temperature_offset
        tempF = (tempC * 9/5) + 32

        '''
        temp_label.text = "{:.1f}/{:.1f}".format(tempC, tempF)
        humidity_label.text = '{:.0f}% {}'.format(sensor.humidity, c)
        pressure_label.text = '{:.0f}'.format(sensor.pressure)
        voc_label.text = '{}'.format(sensor.gas) #ohms
        '''
        
        button_temp.label = "{:.1f}/{:.1f}".format(tempC, tempF)
        button_humidity.label = '{:.0f}% {}'.format(sensor.humidity, c)
        button_pressure.label = '{:.0f}'.format(sensor.pressure)
        button_voc.label = '{}'.format(sensor.gas) #ohms
        
        refresh_time2 = time.monotonic()
    
    if not refresh_time or (time.monotonic() - refresh_time) > 3600:
        gc.collect()
        the_time = time.localtime()
        raw_info = pyportal.network.fetch_data(DATA_SOURCE, json_path=DATA_LOCATION)
        #txt =  get_tide_info()
        refresh_time = time.monotonic()
    
        text_box(feed1_label, 0, 45, str(raw_info))
    
    '''
    if not refresh_time2 or (time.monotonic() - refresh_time2) > 5:
        text_box(center_label, -20, 45, "{} {} {}".format(point, refresh_time, the_time))
    '''
    

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
        
            temp_label.text = op_button + '-' + button
            
            if button in ('=', 'AC', 'CE'):
                op_button.selected = False
            elif button in ('+', '-', 'x', '/') and button != last_op:
                op_button.selected = False

        b = find_button(button)
        
        if b is not None:
            if button not in ('+', '-', 'x', '/') or button != calculator.get_current_operator():
                b.selected = False

        button = ""
    
    if PROCESS_BUTTON_PRESSES:
        time.sleep(0.05)
    else:
        time.sleep(5)
