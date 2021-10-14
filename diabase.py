# -*- coding: utf-8 -*-
"""
Created on Sun Nov 24 14:51:20 2019

@author: Martijn
"""

import serial
import struct
import time
from PyQt5 import QtTest

class diabase:
    def __init__(self, port):
        self.ser = serial.Serial(port,baudrate=57600,timeout=0.01)
        
    def write_line(self,string):
        self.ser.write(string.encode('utf-8')+b'\r\n')
        #print(string)
        old_result = self.ser.read(1)
        watchdog = 0
        while(1):
            watchdog = watchdog + 1
            new_result =  self.ser.read(1)
            if (old_result == b'o' and new_result == b'k'):
                break
            else:
                old_result = new_result
                if watchdog > 1000:
                    print('watchdog in write_line triggered!')
                    break   

    def set_tool_offset(self, tool, pos):
        string = 'G10 P' + str(tool)
        if 'x' in pos:
            string = string + ' X' + str(pos['x'])
        if 'y' in pos:
            string = string + ' Y' + str(pos['y'])
        if 'z' in pos:
            string = string + ' Z' + str(pos['z'])
        #print(string)
        self.write_line(string)
    
    def set_tool_offset_differential(self,tool,extra_offset):

        self.write_line('T'+str(tool))
        self.write_line('M400')
        #time.sleep(5)
        pos0 = self.get_current_position()
        #print(pos0['x'])
        #print(pos0['y'])
        #print(pos0['z'])

        pos = {}
        if 'x' in extra_offset:
            pos['x'] = 0
        if 'y' in extra_offset:
            pos['y'] = 0
        if 'z' in extra_offset:
            pos['z'] = 0
        
        self.set_tool_offset(tool, pos)

        pos1 = self.get_current_position()
        #print(pos1['x'])
        #print(pos1['y'])
        #print(pos1['z'])

        tool_offset = {}
        new_offset = {}
        if 'x' in extra_offset:
            tool_offset['x'] = pos0['x'] - pos1['x']
            new_offset['x'] = tool_offset['x'] + extra_offset['x']
            print(new_offset['x'])

        if 'y' in extra_offset:
            tool_offset['y'] = pos0['y'] - pos1['y']
            new_offset['y'] = tool_offset['y'] + extra_offset['y']
            print(new_offset['y'])

        if 'z' in extra_offset:
            tool_offset['z'] = pos0['z'] - pos1['z']
            new_offset['z'] = tool_offset['z'] + extra_offset['z']
            print(new_offset['z'])

        self.set_tool_offset(tool, new_offset)
        
    def store_offset_parameters(self):
        string = 'M500 P10'
        self.ser.write(string.encode('utf-8')+b'\r\n')

    def get_current_position(self):
        string = 'M114'
        self.ser.write(string.encode('utf-8')+b'\r\n')
        answer = list()
        x_str = b''
        y_str = b''
        z_str = b''
        answer.append(self.ser.read(1))
        while(1):
            answer.append(self.ser.read(1))
            #print(answer)
            if answer[-2] == b'X' and answer[-1]== b':':
                while(1):
                    answer.append(self.ser.read(1))
                    if answer[-1] == b' ':
                        break
                    else:
                        x_str = x_str + answer[-1]
                        
            if answer[-2] == b'Y' and answer[-1]== b':':
                while(1):
                    answer.append(self.ser.read(1))
                    if answer[-1] == b' ':
                        break
                    else:
                        y_str = y_str + answer[-1]
                        
            if answer[-2] == b'Z' and answer[-1]== b':':
                while(1):
                    answer.append(self.ser.read(1))
                    if answer[-1] == b' ':
                        break
                    else:
                        z_str = z_str + answer[-1]

            # if answer[-2] == b'o' and answer[-1]== b'k':
            #     self.ser.write(string.encode('utf-8')+b'\r\n')
            if len(x_str) > 0 and len(y_str) > 0 and len(z_str) > 0:
                break
            #QtTest.QTest.qWait(1) 
        
        pos = {}
        try:
            pos['x'] = float(x_str.decode("utf-8"))
        except:
            pos['x'] = 0
            print('Could not decode x value')

        try:
            pos['y'] = float(y_str.decode("utf-8"))
        except:
            pos['y'] = 0
            print('Could not decode y value')
        try:
            pos['z'] = float(z_str.decode("utf-8"))
        except:
            pos['z'] = 0
            print('Could not decode z value')
        return pos

    def close(self):
        self.ser.close()