# -*- coding: utf-8 -*-
"""
Created on Sun Nov 17 21:09:14 2019

@author: Martijn
"""
import serial
import threading
from time import sleep
import numpy as np

class ldc1101evm:
    received_bytes = b''
    lock = threading.Lock()
    stop_thread = False
    #Csensor = 330e-12
    Csensor = 1200e-12
    def __init__(self, port):
            try: 
                self.ser = serial.Serial(port,baudrate=115200,timeout=1)
            except serial.serialutil.SerialException:
                self.ser = serial.Serial(port,baudrate=115200,timeout=1)
            self.thread = threading.Thread(target=self.serial_daemon, args=(), daemon=True)
            self.thread.start()
            
    def serial_daemon(self):
        while(1):
            if self.ser.isOpen():
                try:
                    received_bytes_local = bytes(self.ser.read(8))
                except Exception as e:
                    print('error: could not read data from LDC1101')
                    break
            with self.lock:
                self.received_bytes = self.received_bytes + received_bytes_local
            if self.stop_thread == True:
                break
    def __read_register(self,register):
        self.ser.write(bytes('03'+register+'\r\n', encoding='utf8'))
        while len(self.received_bytes) < 8:
            sleep(0.001)
        result = self.received_bytes
        self.received_bytes = b''
        return result[8]
    
    def __write_register(self,register,value):
        self.ser.write(bytes('02'+register+value+'\r\n', encoding='utf8'))
        while len(self.received_bytes) < 9:
            sleep(0.001)
        result = self.received_bytes
        value_hex = int(value[0:2],16)
        self.received_bytes = b''
        if value_hex == result[8]:
            return True
        else:
            return False
    
    def __stop_conversion(self):
        self.ser.write(bytes('07', encoding='utf8'))
        
    def __start_LHR_conversion(self):
        self.ser.write(bytes('0638', encoding='utf8'))
        
    def LHR_init(self):
        
        self.__stop_conversion()
        #set to sleep mode
        self.__write_register('0B','01')
        
        #reset Rp range to maximum
        self.__write_register('01','07')
        
        #enable L-only optimisation
        self.__write_register('05','01')
        
        # continue if sensor amplitude cannot be kept regulated
        self.__write_register('0C','01')
        
        #again put into sleep mode
        self.__write_register('0B','01') 
        
        #again put into sleep mode
        #self.__write_register('0A','00')
        
        #don't use interrupt pin
        #self.__write_register('0A','00') 
        
        #downsample sensor frequency by a factor 8
        #self.__write_register('34','03') 
        
        #do not downsample
        self.__write_register('34','00') 

        #reset inductance offset
        self.__write_register('32','00') 
        
        #reset status register
        self.__write_register('3B','00')
        
        #set RID to zero?
        #self.__write_register('3E','00')
        
        #set ID to zero?
        #self.__write_register('3F','00')
        
        #reset Rp range to maximum
        #self.__write_register('01','07')
        
        #don't use interrupt pin
        self.__write_register('0A','00') 
        
        #set to maximum settling time
        self.__write_register('04','07')
        
        #set conversion time LSB
        self.__write_register('30','FF')
        
        #set conversion time MSB
        self.__write_register('31','0F')
        
        #set into active conversion mode
        self.__write_register('0B','00')
        
        self.__start_LHR_conversion()
        
        
        return 0
        
    def get_LHR_data(self,down_sample_ratio):
        average = 0
        i1 = 0
        while 1:
            while len(self.received_bytes) < 8:
                sleep(0.001)
            result = self.received_bytes[0:8]
            if ((result[4] == 0x5A) & (result[6] == 0x5A) & (result[7] == 0x5A)):
                LHR_value = result[1]*2**16+result[2]*2**8+result[3]
                #print(result)
                self.received_bytes =  self.received_bytes[8:]
                fosc = 12e6/2**24*(LHR_value+1)
                #print(fosc)
                inductance = 1/(self.Csensor*(2*np.pi*fosc)**2)
                average = average + inductance/down_sample_ratio
                i1 = i1 + 1
                
                if i1 < down_sample_ratio:
                    continue
                else:
                    #errors = self.__read_register('3B')
                    #print(errors)
                    
                    return average
            else:
                self.received_bytes =  self.received_bytes[1:]
                continue
    
    def flush(self):
        self.received_bytes = b''
        self.ser.reset_input_buffer()
    
    def close(self):
        self.stop_thread = True
        #self.thread.join()
        self.ser.close()