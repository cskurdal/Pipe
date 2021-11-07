
import time
from adafruit_display_text import label
import terminalio
import math
from adafruit_bitmap_font import bitmap_font

#VRSurfing
'''
    This is a simulation of surfing.
    
    EULA: MIT
'''

AQUA = 0x00FFFF
BLUE = 0x0063D3
LILAC = 0xc49eff

class Surfing:
    #Wave info
    _wave_vector = [0,200] #x,y coordinates of the start of the wave vector
    _wave_magnitude = 1
    _wave_period = 16 #TODO: do something with this...
    _swell_height = 10 #TODO: also do something with this...
    _scale = 1 #adjust 
    _wave_caught = False
    _text_label = None
    
    _wave_dx = 20
    
    #Board info
    _board_length = 17
    _board_vector = [200,100]
    _score = 0
    _winning_amount = 10
    

    def __init__(self, logger, display = None, bitmap = None, group = None):
        self.log = logger
        self.log.debug('In __init__')
        
        self._display = display
        self._bitmap = bitmap
        
        self._text_label = self.createText(0.8, 0.8, AQUA, '')
        self._text_label_score = self.createText(0.6, 0.8, BLUE, '')
        
        win_font = bitmap_font.load_font("/fonts/Arial-ItalicMT-23.bdf")
        self._text_label_win = self.createText(0.2, 0.5, LILAC, '', win_font)
        
        if group:
            group.append(self._text_label)
            group.append(self._text_label_score)
            group.append(self._text_label_win)


    def createText(self, x, y, incolor, val = "", font = terminalio.FONT):
        textobj = label.Label(font,text=str(val),color=incolor)
        textobj.x = int(x*self._display.width)
        textobj.y = int((1-y)*self._display.height)
        
        return textobj


    def next_frame(self):
        #self.log.debug('In next_frame x = {}'.format(self._wave_vector[0]))

        c = 0
        self._bitmap[self._wave_vector[0] + c, self._wave_vector[1] + c] = 0
        
        self._wave_vector[0] += 1 #move x
        self._wave_vector[1] = 200 + int(math.sin(self._wave_vector[0] * 1/self._wave_period) * self._swell_height) #move y
        
        if self._wave_vector[0] >= self._display.width:
            self._wave_vector[0] = 0
        
        self._bitmap[self._wave_vector[0] + c, self._wave_vector[1] + c] = 2

        if self._wave_caught:
            if abs(self._wave_vector[1] - self._board_vector[1]) > self._wave_dx:
                self.log.debug('CAUGHT WAVE!')
                self._wave_caught = False
            elif self._board_vector[0] + 1 + (self._board_length // 2) >= self._display.width:
                #When at the edge of the screen reset
                self._wave_caught = False
                self.move_board(200, 100)
            else:                    
                #move along board
                self.move_board(self._board_vector[0] + 1, self._board_vector[1])
        else:
            #self.log.debug('check if caught wave')
            
            if abs(self._wave_vector[0] - self._board_vector[0]) < self._wave_dx and abs(self._wave_vector[1] - self._board_vector[1]) < self._wave_dx:
                self._text_label_score.hidden = True
                self.log.debug('CAUGHT WAVE!')
                self._text_label.hidden = False
                self._text_label.text= 'CAUGHT WAVE'
                
                time.sleep(0.6)
                
                self._text_label.text= ''
                time.sleep(0.1)
                
                self._text_label.text= 'CAUGHT WAVE'
                time.sleep(0.7)
                self._text_label.hidden = True
                
                self._score += 1
                
                if self._score == self._winning_amount:
                    self._text_label_win.text = "YOU WIN!! YOUR SCORE IS {}!!!".format(self._winning_amount)
                    time.sleep(3)
                    return False
                else:
                    self._text_label_score.text= "Your score is now {}!".format(self._score)
                    self._text_label_score.hidden = False
                    
                self._wave_caught = True
                
        #time.sleep(.05)
               
        return True

    def process_input(self, p):
        self.log.debug('In process_input = {}'.format(p))
        
        if p[1] > self._wave_vector[1]:
            self.move_board_down()
        elif p[1] < self._wave_vector[1]:
            self.move_board_up()


    def move_board(self, x,  y):
        #self.log.debug('In move_board')
        
        for c in range(-(self._board_length // 2), self._board_length // 2):
            self._bitmap[self._board_vector[0] + c, self._board_vector[1] + c] = 0
        
        self._board_vector = [x, y]
        
        for c in range(-(self._board_length // 2), self._board_length // 2):
            self._bitmap[self._board_vector[0] + c, self._board_vector[1] + c] = 3


    def move_board_up(self):
        self.log.debug('UP!')
    
        for c in range(-(self._board_length // 2), self._board_length // 2):
            self._bitmap[self._board_vector[0] + c, self._board_vector[1] + c] = 0
        
        self._board_vector[1] -= 2
        
        for c in range(-(self._board_length // 2), self._board_length // 2):
            self._bitmap[self._board_vector[0] + c, self._board_vector[1] + c] = 3


    def move_board_down(self):
        self.log.debug('Down!')
    
        for c in range(-(self._board_length // 2), self._board_length // 2):
            self._bitmap[self._board_vector[0] + c, self._board_vector[1] + c] = 0
        
        self._board_vector[1] += 2
        
        for c in range(-(self._board_length // 2), self._board_length // 2):
            self._bitmap[self._board_vector[0] + c, self._board_vector[1] + c] = 3

        