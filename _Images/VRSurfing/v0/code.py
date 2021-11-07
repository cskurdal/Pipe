'''
https://github.com/cmontalvo251/Microcontrollers/blob/master/PyPortal/temp_light_plotter.py
'''
import board
import displayio
import time
import busio
import adafruit_logging as logging

from adafruit_pyportal import PyPortal
from simulation.Game import Surfing

#import adafruit_adt7410 #Not on PyPortal Titano

from digitalio import DigitalInOut, Direction, Pull
from analogio import AnalogIn
import terminalio
from adafruit_display_text import label
import adafruit_touchscreen

import adafruit_bme680

display = board.DISPLAY

# Touchscreen setup
SCREEN_WIDTH = board.DISPLAY.width
SCREEN_HEIGHT = board.DISPLAY.height

#Create a button for the touch screen
ts = adafruit_touchscreen.Touchscreen(board.TOUCH_XL, board.TOUCH_XR,board.TOUCH_YD, board.TOUCH_YU,
                                      calibration=((5200, 59000), (5800, 57000)),
                                      size=(SCREEN_WIDTH, SCREEN_HEIGHT))



# Backlight function
# Value between 0 and 1 where 0 is OFF, 0.5 is 50% and 1 is 100% brightness.
def set_backlight(val):
    val = max(0, min(1.0, val))
    board.DISPLAY.auto_brightness = False
    board.DISPLAY.brightness = val
 
pyportal = PyPortal() #for background


APP_NAME = 'VR Surfing'

logger = logging.getLogger(APP_NAME)
logger.setLevel(logging.DEBUG)

title_welcome = 'Welcome to {}'.format(APP_NAME)

print(title_welcome)

#esp._debug = True

pyportal.set_background('/images/loading.bmp')
time.sleep(1) #show the back ground for 5 seconds more

# Create a bitmap with three colors
bitmap = displayio.Bitmap(display.width, display.height, 4)


# You will usually have to add an offset to account for the temperature of
# the sensor. This is usually around 5 degrees but varies by use. Use a
# separate temperature sensor to calibrate this one.
temperature_offset = -2.5

def clear():
    for x in range(0,display.width):
        for y in range(0,display.height):
            bitmap[x,y] = 0

def createText(level,maxval,minval,x,incolor):
    val = int(level*(maxval-minval)+minval)
    textobj = label.Label(terminalio.FONT,text=str(val),color=incolor)
    textobj.x = int(x*display.width)
    textobj.y = int((1-level)*display.height)
    return textobj

def change_time(time_range_hrs):
    global time_sleep
    #time_range_hrs = 8.0
    #time_next = 0
    time_sleep = time_range_hrs*60*60/display.width
    time_range_text = label.Label(terminalio.FONT,text="R = " + str(time_range_hrs)+" h "+"S = "+str(int(time_sleep))+" s",color=WHITE)
    time_range_text.x = int(0.1*display.width)
    time_range_text.y = int(0.1*display.height)
    print("Sleep Range = ",time_sleep)
    return time_range_text

BLACK = 0x000000
WHITE = 0xffffff #Light color
TEMPCOLOR = 0xFFA500
LIGHTCOLOR = 0xFFFF00
AQUA = 0x00FFFF

# Create a two color palette
palette = displayio.Palette(4)
palette[0] = BLACK
palette[1] = LIGHTCOLOR
palette[2] = AQUA # TEMPCOLOR
palette[3] = WHITE
#palette[4] = AQUA

# Create a TileGrid using the Bitmap and Palette
tile_grid = displayio.TileGrid(bitmap, pixel_shader=palette)

# Create a Group
group = displayio.Group()

# Add the TileGrid to the Group
group.append(tile_grid)

#Light step
lightmax = 65536.
lightstep = lightmax/display.height
#Summer
tempmax = 105.
tempmin = 50.
#Winter
#tempmax = 75.
#tempmin = 25.
tempslope = display.height/(tempmin-tempmax)

if False:
    #Text
    tempx = 0.8
    temp_texts = []
    for i in range(1,10,4):
        print(i/10.)
        temp_texts.append(createText(i/10.,tempmax,tempmin,tempx,TEMPCOLOR))
        group.append(temp_texts[-1])

    lightx = 0.7
    light_texts = []
    for i in range(1,10,4):
        print(i/10.)
        light_texts.append(createText(i/10.,lightmax,0,lightx,LIGHTCOLOR))
        group.append(light_texts[-1])

###Make a grid now
#time_range_text = change_time(time_range_hrs)
#group.append(time_range_text)

#Setup light and temperature
#i2c_bus = busio.I2C(board.SCL, board.SDA)


i2c = board.I2C()
sensor = adafruit_bme680.Adafruit_BME680_I2C(i2c)

#adt = adafruit_adt7410.ADT7410(i2c_bus, address=0x48)
#adt.high_resolution = True
adc = AnalogIn(board.LIGHT)

##Current Temperature and light value
current_vals = label.Label(terminalio.FONT,text="L: "+str(adc.value)+" T: "+str(sensor.temperature),color=WHITE)
current_vals.x = int(0.1*display.width)
current_vals.y = int(0.2*display.height)
# Add the Group to the Display
#group.append(current_vals)

##THen finally show the group
display.show(group)

#Line Height
line_height = 5


ctr = display.width-1
yball = 1
xball = 1
time_start = time.monotonic()

g = Surfing(logger, display, bitmap, group)

while True:
    if not g.next_frame():
        break
    
    p = ts.touch_point
    
    if p:
        logger.debug('Screen touched: {}'.format(p))
            
        g.process_input(p)
        
        #time.sleep(0.05)
        
    if False and time_next < (time.monotonic()-time_start):
        print(time_next,time.monotonic()-time_start)
        time_next += time_sleep
        #Get temperature and light
        light = adc.value
        temperature_celsius = sensor.temperature + temperature_offset
        temperature_farenheit = temperature_celsius*9.0/5.0 + 32.0
        ypixel_temp = int((temperature_farenheit-tempmin)*tempslope+display.height)
        ypixel_light = int(light/lightstep)
        ##Flip the axes
        ypixel_light = display.height - ypixel_light
        print(temperature_farenheit,light,lightstep,tempslope,ypixel_temp,ypixel_light)
        #Update the text
        group.pop()
        current_vals = label.Label(terminalio.FONT,text="L: "+str(light)+" T: "+str(int(temperature_farenheit)),color=WHITE)
        current_vals.x = int(0.1*display.width)
        current_vals.y = int(0.2*display.height)
        group.append(current_vals)
        #Clear bitmap
        #Draw a pixel to indicate what column you are on
        bitmap[ctr,0] = 0
        bitmap[ctr,1] = 0
        bitmap[ctr,2] = 0
        ctr += 1
        if ctr >= display.width:
            ctr = 0
            #Clear the screen
            #clear()
        for x in range(0,display.width):
            for y in range(0,display.height):
                if x == ctr and abs(y-ypixel_temp) < line_height:
                    bitmap[x,y] = 2
                elif x == ctr and abs(y-ypixel_light) < line_height:
                    bitmap[x,y] = 1
                elif x == ctr:
                    bitmap[x,y] = 0
        bitmap[ctr,0] = 3
        bitmap[ctr,1] = 3
        bitmap[ctr,2] = 3
        
    
    ##Draw a ball dropping on the right side of the screen
    if False:
        #xball = int(0.9*display.width)
        yball = int(2/3*display.height)
        
        bitmap[xball-1,yball-1] = 0
        bitmap[xball-1,yball] = 0
        bitmap[xball-1,yball+1] = 0
        
        bitmap[xball,yball] = 0
        bitmap[xball-1,yball] = 0
        
        bitmap[xball+1,yball-1] = 0
        bitmap[xball+1,yball] = 0
        bitmap[xball+1,yball+1] = 0
        
        if xball < (display.width - 1):
            bitmap[xball+1,yball] = 0
    
        xball += 1
                
        if display.width < 1 or (display.width - 2) < xball:
            xball = 1
            
        if yball > (display.height - 2):
            yball = 1
                
        bitmap[xball-1,yball-1] = 3
        bitmap[xball-1,yball] = 3
        bitmap[xball-1,yball+1] = 3
        
        bitmap[xball-1,yball] = 3
        bitmap[xball,yball] = 3
        
        if xball < (display.width - 1):
            bitmap[xball+1,yball] = 3
        
        
        bitmap[xball+1,yball-1] = 3
        bitmap[xball+1,yball] = 3
        bitmap[xball+1,yball+1] = 3
        
    #Time sleep
    #print(time_next,time.monotonic()-time_start)
    time.sleep(0.01)



