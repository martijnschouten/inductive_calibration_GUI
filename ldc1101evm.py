"""
.. module:: ldc1101evm
    :synopsis: This class handles the communication with the LDC1101EVM indutance to digital converter evaluation module
.. moduleauthor:: Martijn Schouten <github.com/martijnschouten>
"""

import serial
import threading
from time import sleep
import numpy as np

class ldc1101evm:
    received_bytes = b''
    """Stores all the bytes received from the LDC1101EVM"""

    lock = threading.Lock()
    """Mutex for making sure the serial daemon and the other functions don't try to access :attr:`ldc1101evm.received_bytes` at the same time"""

    stop_thread = False
    """If set to True, the serial daemon will kill itself"""

    Csensor = 1200e-12
    """Value of the capacitor soldered onto the LDC1101EVM. This will affect the measured inductance since the LDC1101EVM determines the osciallation frequency of an LC tank with this capaictor and the inductor to be measured."""

    error = False

    def __init__(self, port):
        """Code run when the ldc1101evm object is initialised. This initialises the communication with LDC1101EVM and start the serial daemon in a seperate thread.

        :param port: The full name of the port at which the printer can be found. Example: 'COM1'
        :return: None
        :rtype: None
        """
        try: 
            self.ser = serial.Serial(port,baudrate=115200,timeout=1)
        except serial.serialutil.SerialException:
            self.ser = serial.Serial(port,baudrate=115200,timeout=1)
        self.thread = threading.Thread(target=self.serial_daemon, args=(), daemon=True)
        self.thread.start()

    def serial_daemon(self):
        """The serial daemon which is run in a seperate thread as the rest and just puts all the received bytes in :attr:`ldc1101evm.received_bytes`

        :return: None
        :rtype: None
        """
        while(1):
            if self.ser.isOpen():
                try:
                    received_bytes_local = bytes(self.ser.read(8))
                except Exception as e:
                    print('error: could not read data from LDC1101')
                    self.error = True
                    break
            with self.lock:
                self.received_bytes = self.received_bytes + received_bytes_local
            if self.stop_thread == True:
                break


    def __read_register(self,register):
        """Read a register inside the LDC1101 IC`
        
        :param port: Address of the register to be read.
        :return: Value of the register
        :rtype: byte
        """
        self.ser.write(bytes('03'+register+'\r\n', encoding='utf8'))
        while len(self.received_bytes) < 8:
            sleep(0.001)
        result = self.received_bytes
        self.received_bytes = b''
        return result[8]
    
    def __write_register(self,register,value):
        """Write a register inside the LDC1101 IC`
        
        :param port: Address of the register to be written.
        :param port: Value to write to the register.
        :return: True if succesfull, False if unsuccesfull
        :rtype: Boolean
        """
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
        """Function for stopping the current conversion inside the LDC1101EVM

        :return: None
        :rtype: None
        """
        self.ser.write(bytes('07', encoding='utf8'))
        
    def __start_LHR_conversion(self):
        """Function for starting a high resolution measurement. A high resolution measurement is 24 bit and has no R measurement.

        :return: None
        :rtype: None
        """
        self.ser.write(bytes('0638', encoding='utf8'))
        
    def LHR_init(self):
        """Function for initialising a high resolution measurement. A high resolution measurement is 24 bit and has no R measurement.

        :return: None
        :rtype: None
        """
        
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
        
    def get_LHR_data(self,down_sample_ratio):
        """Function getting the inductance measured by the LDC1101EVM in LHR mode. To put it in LHR mode run :meth:`ldc1101evm.LHR_init` first. This function blocks until an inductance value that has not been read is available. To delete all currently stored measurements run :meth:`ldc1101evm.flush` first.

        :param down_sample_ratio: How much the output should be downsampled. This reduces the sampling rate but increases the effective resolution by taking the average.
        :return: The measured inductance
        :rtype: float
        """
        average = 0
        i1 = 0
        while 1:
            while len(self.received_bytes) < 8:
                sleep(0.001)
            result = self.received_bytes[0:8]
            if ((result[4] == 0x5A) & (result[6] == 0x5A) & (result[7] == 0x5A)):
                LHR_value = result[1]*2**16+result[2]*2**8+result[3]
                self.received_bytes =  self.received_bytes[8:]
                fosc = 12e6/2**24*(LHR_value+1)
                inductance = 1/(self.Csensor*(2*np.pi*fosc)**2)
                average = average + inductance/down_sample_ratio
                i1 = i1 + 1
                
                if i1 < down_sample_ratio:
                    continue
                else:                    
                    return average
            else:
                self.received_bytes =  self.received_bytes[1:]
                continue
    
    def flush(self):
        """Delete all currently stored measurements

        :return: None
        :rtype: None
        """
        self.received_bytes = b''
        self.ser.reset_input_buffer()
    
    def close(self):
        """Close the serial connection and tell the daemon to go kill itself.

        :return: None
        :rtype: None
        """
        self.stop_thread = True
        self.ser.close()