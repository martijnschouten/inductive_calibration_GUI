"""
.. module:: diabase
    :synopsis: This class handles the communication with the diabase 3D printer
.. moduleauthor:: Martijn Schouten <github.com/martijnschouten>
"""

import serial

class diabase:
    """The number of lines to read before deciding the 'OK'  from the printer will never arrive"""

    def __init__(self, port):
        """Code run when the diabase object is initialised. This initialises the communication with printer.

        :param port: The full name of the port at which the printer can be found. Example: 'COM1'
        :return: None
        :rtype: None
        """
        self.ser = serial.Serial(port,baudrate=57600,timeout=0.01)
        
    def write_line(self,string,attempts):
        """Write a line of GCODE to the printer. This function will wait for an 'OK' from the printer, meaning that the command has finished executing (except for G1 commands). If it takes too to many attempts for the printer give an answer it will be assumed something went wrong and the function will return anyways.

        :param string: The line of GCODE to write to the printer.
        :return: None
        :rtype: None
        """
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
                if watchdog > attempts:
                    print('watchdog in write_line triggered! sting to ok: '+string)
                    break   

    def set_tool_offset(self, tool, pos):
        """Function for setting tool offsets.

        :param tool: The tool number of the tool of which to set the offsets
        :param pos: Dict with the tool offsets. The function expect a key 'x', 'y' or 'z' with the tool offset in the corresponding direction.
        :return: None
        :rtype: None
        """
        string = 'G10 P' + str(tool)
        if 'x' in pos:
            string = string + ' X' + str(pos['x'])
        if 'y' in pos:
            string = string + ' Y' + str(pos['y'])
        if 'z' in pos:
            string = string + ' Z' + str(pos['z'])
        #print(string)
        self.write_line(string,1000)
    
    def set_tool_offset_differential(self,tool,extra_offset):
        """Function for setting tool offsets relative to the current tool offsets. To do so the printer will:

        *  Select the tool
        *  Get the current position
        *  Set the tool offset to zero
        *  Measure the position again
        *  Set the tool offset to the last measured tool offset plus the addional tool offset

        :param tool: The tool number of the tool of which to set the offsets
        :param extra_offset: Dict with the additional tool offsets. The function expect a key 'x', 'y' or 'z' with the additional tool offset in the corresponding direction.
        :return: None
        :rtype: None
        """

        #Select the tool
        self.write_line('T'+str(tool),10000)
        self.write_line('M400',10000)

        #Get the current position
        pos0 = self.get_current_position()

        #Set the tool offset to zero
        pos = {}
        if 'x' in extra_offset:
            pos['x'] = 0
        if 'y' in extra_offset:
            pos['y'] = 0
        if 'z' in extra_offset:
            pos['z'] = 0
        self.set_tool_offset(tool, pos)

        #Measure the position again
        pos1 = self.get_current_position()

        #Set the tool offset to the last measured tool offset plus the addional tool offset
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
        """Function for storing the current tool offsets in flash such that they will still be there when the printer is restarted.

        :return: None
        :rtype: None
        """

        string = 'M500 P10'
        self.ser.write(string.encode('utf-8')+b'\r\n')

    def get_current_position(self):
        """Function for getting the current position of the printer using a M114 command

        :return: Dict with the current position. The dict contains a key 'x', 'y' or 'z' with the current position in the corresponding direction.
        :rtype: Dict
        """
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
        """Function for closing the serial communication with the printer

        :return: None
        :rtype: None
        """

        self.ser.close()