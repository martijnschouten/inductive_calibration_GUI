"""
.. module:: app
    :synopsis: This class implements a graphical user interface for calibrating a tool offset of a multi-material 3D printer using a LDC1101EVM evaluation module
.. moduleauthor:: Martijn Schouten <github.com/martijnschouten>
"""

from PyQt5 import QtWidgets, uic, QtTest
from PyQt5.QtCore import Qt
from pyqtgraph import GraphicsLayout
import pyqtgraph as pg
import sys  # We need sys so that we can pass argv to QApplication
import yaml
import io
import serial.tools.list_ports
from ldc1101evm import ldc1101evm
from diabase import diabase
from scipy.optimize import curve_fit
import scipy.io as sio
import numpy as np
import time

class MainWindow(QtWidgets.QMainWindow):
    connected = False
    """If a connection to the LDC1101EVM and diabase has already been made"""

    duet_port = ''
    """The name of the port the duet is connected to"""

    offset_tool_list = []
    """A list of the tool numbers belonging to the tool offsets in :attr:`MainWindow.offset_list`"""

    offset_list = []
    """A list with the last found tool offsets belonging to the tools in :attr:`MainWindow.offset_tool_list`"""

    offset_direction = True
    """If True the last run calibration was in the x direction, if False it was in the y direction"""

    stop_button_clicked = False
    """Becomes True if the stop button has been clicked, until the measurement is stopped, then it becomes False again"""

    ascend = True
    """If the tools should be calibrated in ascending (True) or descending (False) order."""

    def __init__(self, *args, **kwargs):
        """Code run when the GUI is startup. Used to connect signals from the GUI to functions in this class.

        :return: None
        :rtype: None
        """
        super(MainWindow, self).__init__(*args, **kwargs)

        #Load the UI Page
        uic.loadUi('interface.ui', self)
        QtWidgets.QApplication.processEvents()

        #connect signals from the GUI to functions in this class.
        self.sig_graph = self.sig_graph.getPlotItem()
        self.cal_x_button.clicked.connect(self.calibrate_x)
        self.cal_y_button.clicked.connect(self.calibrate_y)
        self.connect_button.clicked.connect(self.connect)
        self.reload_button.clicked.connect(self.reload)
        self.apply_offsets_button.clicked.connect(self.apply_offsets)
        self.stop_button.clicked.connect(self.stop)
        self.clear_figure_button.clicked.connect(self.clear_figure)
        self.test_sensor_button.clicked.connect(self.test_sensor)
        self.ascend_box.stateChanged.connect(self.ascend_changed)
        self.descend_box.stateChanged.connect(self.descend_changed)
        
        self.reload()
        
        self.load_settings()


    def reload(self):
        """Scans all COM ports and checks the name of all COM ports. If a name with "USB Serial Device" or "Duet" is found this it is selected as the printer port. If a name with 'EVM' is found this port is selected to be the port with the LDC1101EVM.

        :return: None
        :rtype: None
        """
        ports = list(serial.tools.list_ports.comports())
        self.port_device = list()
        self.port_descr = list()
        for p in ports:
            self.port_device.append(p.device)
            self.port_descr.append(p.description)
        self.duet_combo.clear()
        self.ldc_combo.clear()
        self.duet_combo.addItems(self.port_descr)
        self.ldc_combo.addItems(self.port_descr)
        for i1 in range(len(self.port_descr)):
            if self.port_descr[i1].startswith('USB Serial Device') or self.port_descr[i1].startswith('Duet'):
                self.duet_combo.setCurrentIndex(i1)
            if self.port_descr[i1].startswith('EVM'):
                self.ldc_combo.setCurrentIndex(i1)

    
    def stop(self):
        """Function for handling the stop button being pressed. This will set a variable that will stop the running processes when possible.

        :return: None
        :rtype: None
        """
        self.stop_button_clicked = True

    def clear_figure(self):
        """Function for handling the clear figure button being pressed. This will clear the graph in the GUI and reinitialise it.
        
        :return: None
        :rtype: None
        """
        self.sig_graph.clear()
        self.curve = list()
        
        if self.tool_list:
            for i1 in range(len(self.tool_list*2)):
                self.curve.append(self.sig_graph.plot())

    def connect(self):
        """Function for handling the connect button being pressed. This will attempted to connect to the selected COM ports.
        
        :return: True if succesfull, False if unsuccesfull
        :rtype: Boolean
        """
        port_evm = self.port_device[self.ldc_combo.currentIndex()]
        try:
            self.Ldc1101evm = ldc1101evm(port_evm)
        except:
            self.output_to_terminal("could not open port of the ldc1101evm. Please make sure there are no open connections\r\n")
            print('could not open port of the ldc1101evm.')
            return False
        self.output_to_terminal("connection to ldc1101evm successfull")
            
        port_duet = self.port_device[self.duet_combo.currentIndex()]
        try:
            self.Diabase = diabase(port_duet)
        except:
            self.output_to_terminal("could not open port of the duet. Please make sure there are no open connections\r\n")
            print('could not open port of the duet.')
            return False
        self.output_to_terminal("connection to duet successfull")
        
        self.Ldc1101evm.LHR_init()
        self.connected = True

        return True
    
    def output_to_terminal(self,new_text):
        """Function for writing output to the terminal text box.
        
        :return: None
        :rtype: None
        """
        current_text = self.output_terminal.toPlainText()
        text =  new_text +"\r\n" + current_text
        self.output_terminal.setText(text)
        QtWidgets.QApplication.processEvents()

    def update_tool_list(self):
        """Function for reading out the selected tools and the reference tool and putting them in the right order. The reference tool always will go first, then the other tools follow in either ascending or descending order, depending on whether ascend or descend is selected.
        
        :return: None
        :rtype: None
        """
        tools = self.tool_list_list.selectedItems()
        if len(tools) == 0:
            self.output_to_terminal('error: no tools were selected')
            return 0
        ref_tool = int(self.ref_combo.currentText())
        self.tool_list = list()
        for tool in tools:
            new_tool = int(tool.text())
            if new_tool == ref_tool:
                self.tool_list.insert(0,new_tool)
            else:
                self.tool_list.append(new_tool)
        
        if self.ascend:
            self.tool_list[2:] = sorted(self.tool_list[2:])
        else:
            self.tool_list[2:] = reversed(sorted(self.tool_list[2:]))
        return 1

    def closeEvent(self, event):
        """Function for handling the window being closed. This makes sure the settings are saved when the window is closed.
        :return: None
        :rtype: None
        """
        self.save_settings()

    def calibrate_y(self):
        """Function for handling the calibrate y button being pressed. This will run the calibration procedure and find the y offsets.
        :return: None
        :rtype: None
        """
        cal_x = False
        self.calibrate(cal_x)

    def calibrate_x(self):
        """Function for handling the calibrate x button being pressed. This will run the calibration procedure and find the x offsets.
        :return: None
        :rtype: None
        """
        cal_x = True
        self.calibrate(cal_x)

    def ascend_changed(self):
        """Function for handling the ascend checkbox being pressed. This will update the ascend setting and deselect the descend checkbox.
        :return: None
        :rtype: None
        """
        if self.ascend_box.isChecked():
            self.descend_box.setChecked(False)
            self.ascend = True
        else:
            self.descend_box.setChecked(True)
            self.ascend = False

    def descend_changed(self):
        """Function for handling the descend checkbox being pressed. This will update the ascend setting and deselect the ascend checkbox.
        :return: None
        :rtype: None
        """
        if self.descend_box.isChecked():
            self.ascend_box.setChecked(False)
            self.ascend = False
        else:
            self.ascend_box.setChecked(True)
            self.ascend = True
        

    def test_sensor(self):
        """Function for handling the test sensor checkbox being pressed. This will just record the LDC1101EVM sensor values until the stop button is clicked and store the result in the file specified in the filename textbox.
        :return: None
        :rtype: None
        """
        if self.connected == False:
            if not self.connect():
                return 0

        self.Ldc1101evm.flush()
        i1 = 0
        L = np.zeros(100000)
        time_buf = np.zeros(100000)
        tic = time.time()
        self.sig_graph.clear()
        self.curve = self.sig_graph.plot()
        
        while(1):
            if self.stop_button_clicked:
                self.stop_button_clicked = False
                time_buf = time_buf[1:i1]
                L = L[1:i1]
                filename = self.filename_line.text()
                sio.savemat(filename,{'time_buf':time_buf, 'L':L})
                return 0

            L[i1] = self.Ldc1101evm.get_LHR_data(100)
            time_buf[i1] = time.time()-tic
            if i1 > 1001:
                self.curve.setData(time_buf[i1-1000:i1],L[i1-1000:i1])
            elif i1 > 0:
                self.curve.setData(time_buf[1:i1],L[1:i1])

            QtWidgets.QApplication.processEvents()
            i1 = i1 + 1

    def calibrate(self,cal_x):
        """Function for performing a calibration in x or y. This will just record the LDC1101EVM sensor values until the stop button is clicked and store the result in the file specified in the filename textbox.
        :param cal_x: If True, calibrate in the x direction. If False, calibate in the y direction.
        :return: False if unsucceful, True if succefull
        :rtype: Boolean
        """

        if self.connected == False:
            self.connect()

        self.output_to_terminal('started calibration')

        #get settings for the calibration process from the textboxes.
        x_pos = self.x_box.value()
        y_pos = self.y_box.value()
        z_pos = self.z_box.value()
        scan_range = self.range_box.value()
        speed = self.speed_box.value()
        filename = self.filename_line.text()

        if cal_x:
            rounds = self.rounds_x_spinner.value()
        else:
            rounds=  self.rounds_y_spinner.value()

        #calculate the start and stop position of the calibration movement.
        if cal_x:
            x_start = x_pos - scan_range
            x_stop = x_pos + scan_range
        else:
            y_start = y_pos - scan_range
            y_stop = y_pos + scan_range

        #fixed parameters of the calibration process.
        cooldown_time = 3.0
        cooldown_height = 1
        plotting_interval = 5
        buffer_size = 1e4
        default_speed = 60
        speed_factor = 1.5

        buffer_size = int(buffer_size)

        #Try to update the tool list.
        if not self.update_tool_list():
            return False

        #attempt to set the layer fan speed
        try:
            if self.fan_box.isChecked():
                self.Diabase.write_line('M106 P3 S255')
            else:
                self.Diabase.write_line('M106 P3 S0')
        except:
            self.output_to_terminal('error: could not find a Duet')
            return False

        #heat up the tools
        for i1 in range(len(self.tool_list)):
            self.Diabase.write_line('G10 P%.0f R%.0f  S%.0f' % (self.tool_list[i1],self.temp_box.value(),self.temp_box.value()))
        
        #heat up the bed
        self.Diabase.write_line('M140 S%.0f' % (self.bed_temp_box.value()))

        time.sleep(1)
        
        #wait the bed to heat up.
        print("doing the M116")
        self.Diabase.write_line('M116')

        print("received the M116")
        #select coordinate system 1 (because the coordinate system might have been changed during the z calibration)
        self.Diabase.write_line('G54')

        #reinitialise the graph
        self.curve = list()
        for i1 in range(len(self.tool_list)*2):
            self.curve.append(self.sig_graph.plot())
        
        #initialise data storage buffers to store data from the calibration process into
        loc = np.zeros([len(self.tool_list),rounds,2])
        data = np.zeros([buffer_size,len(self.tool_list),rounds,2])
        pos = np.zeros([buffer_size,len(self.tool_list),rounds,2])
        timestamps = np.zeros([buffer_size,len(self.tool_list),rounds,2])

        tic = time.time()
        for cycle in range(rounds):
            #home the printer and measure the z height. If the homing box is checked the printer is homed every round, otherwise it is calibration only during the first round.
            if self.homing_box.isChecked() or cycle ==0:     
                self.Diabase.write_line('G28')
                self.Diabase.write_line('G90')
                self.Diabase.write_line('G1 X0 Y0 Z8 F8000')
                self.Diabase.write_line('G30')

            #wait for homing to finish
            self.Diabase.write_line('M400')

            #attempt to make the GUI more responsive
            QtWidgets.QApplication.processEvents()

            #stop the calibration if the stop button was clicked.
            if self.stop_button_clicked:
                self.stop_button_clicked = False
                return 0
            
            #select the first tool
            self.Diabase.write_line('T'+str(self.tool_list[0]))
            print("selected tool "+ str(self.tool_list[0]))
            self.Diabase.write_line('M400')

            #attempt to make the GUI more responsive
            QtWidgets.QApplication.processEvents()

            #stop the calibration if the stop button was clicked.
            if self.stop_button_clicked:
                self.stop_button_clicked = False
                return 0
            
            #move the printer to the starting position for the calibration.
            if cal_x:
                self.Diabase.write_line('G1 Z'+str(z_pos+cooldown_height)+' Y'+str(y_pos)+' X'+str(x_start) + ' F' + str(default_speed*60))
            else:
                self.Diabase.write_line('G1 Z'+str(z_pos+cooldown_height)+' Y'+str(y_start)+' X'+str(x_pos) + ' F' + str(default_speed*60))
            print("commanded to go to initial position")
            self.Diabase.write_line('M400')
            
            

            self.offset_tool_list = []
            self.offset_list = []
            
            #perform calibration for all tools
            for tool in range(len(self.tool_list)):
                print("selected tool "+ str(self.tool_list[tool]))
                self.Diabase.write_line('T'+str(self.tool_list[tool]))
                self.Diabase.write_line('M400')
                
                #go forwards and backwards.
                for dir in range(2):
                    #move the printer to the starting position for the calibration.
                    if cal_x:
                        if dir == 0:
                            self.Diabase.write_line('G1 Z'+str(z_pos)+' Y'+str(y_pos)+' X'+str(x_start) + ' F' + str(default_speed*60))
                        else:
                            self.Diabase.write_line('G1 Z'+str(z_pos)+' Y'+str(y_pos)+' X'+str(x_stop) + ' F' + str(default_speed*60))
                    else:
                        if dir == 0:
                            self.Diabase.write_line('G1 Z'+str(z_pos)+' Y'+str(y_start)+' X'+str(x_pos) + ' F' + str(default_speed*60))
                        else:
                            self.Diabase.write_line('G1 Z'+str(z_pos)+' Y'+str(y_stop)+' X'+str(x_pos) + ' F' + str(default_speed*60))
                    self.Diabase.write_line('M400')
                    
                    #delete any old sample in the LDC1101EVM and make sure it is ready.
                    self.Ldc1101evm.flush()
                    self.Ldc1101evm.get_LHR_data(50)

                    i1 = 0#total samples number
                    tic2 = time.time()#time since the calibration started
                    while(True):
                        #stop the calibration if the stop button was clicked.
                        if self.stop_button_clicked:
                            self.stop_button_clicked = False
                            return 0

                        #calculate the position the printer should be at based on the desired speed and the elapsed time, and move the printer to there.
                        #Also limit the maximum movement speed to a bit above the desired speed, to minize accelerations, but allow the printer to catch up if necessary.
                        toc2 = time.time() -tic2
                        if cal_x:
                            if dir == 0:
                                new_x = x_start+toc2*speed
                            else:
                                new_x = x_stop-toc2*speed
                            self.Diabase.write_line('G1 X' + str(new_x) + " F" + str(speed*60*speed_factor))
                        else:
                            if dir == 0:
                                new_y = y_start+toc2*speed
                            else:
                                new_y = y_stop-toc2*speed
                            self.Diabase.write_line('G1 Y' + str(new_y) + " F" + str(speed*60*speed_factor))
                        self.Diabase.write_line('M400')

                        #Flush the LDC1101EVM to be sure to get the latest value and get a sample
                        self.Ldc1101evm.flush()
                        data[i1,tool,cycle,dir] = self.Ldc1101evm.get_LHR_data(50)

                        #Also store a timestamp of the current time since the beginning of the entire calibration process
                        timestamps[i1,tool,cycle,dir] = time.time()-tic

                        #And store the current position.
                        if cal_x:
                            pos[i1,tool,cycle,dir] = new_x
                        else:
                            pos[i1,tool,cycle,dir] = new_y
                        i1 = i1 + 1

                        #put the data points in the graph every once in a while
                        if i1%plotting_interval == 0:
                            self.curve[tool*2+dir].setData(pos[0:i1,tool,cycle,dir],data[0:i1,tool,cycle,dir])

                        #if the printer has moved by the required amount , stop the calibration.
                        if cal_x:
                            if (dir ==0 and new_x >= x_stop) or (dir == 1 and new_x <= x_start):    
                                break  
                        else:
                            if (dir ==0 and new_y >= y_stop) or (dir == 1 and new_y <= y_start): 
                                break
                        
                        #attempt to make the GUI more responsive
                        QtWidgets.QApplication.processEvents()
                    
                    #find the axis of symmetry in the measured data to find the location of the nozzle
                    try:
                        loc[tool,cycle,dir] = self.find_symmetry_axis(pos[int(i1/10):int(9/10*i1),tool,cycle,dir],data[int(i1/10):int(9/10*i1),tool,cycle,dir])
                    except RuntimeError:
                        self.output_to_terminal('error: calibration curve to ugly to fit')
                        break

                    #print the result of the calibration to the terminal
                    if tool == 0:
                        if cal_x:
                            if dir == 0:
                                self.output_to_terminal('x position reference tool ' + str(self.tool_list[tool]) + ' when going up: ' + f"{loc[0,cycle,dir]:.3f}")
                            else:
                                self.output_to_terminal('x position reference tool ' + str(self.tool_list[tool]) + ' when going down: ' + f"{loc[0,cycle,dir]:.3f}")
                        else:
                            if dir == 0:
                                self.output_to_terminal('y position reference tool ' + str(self.tool_list[tool]) + ' when going up: ' + f"{loc[0,cycle,dir]:.3f}")
                            else:
                                self.output_to_terminal('y position reference tool ' + str(self.tool_list[tool]) + ' when going down: ' + f"{loc[0,cycle,dir]:.3f}")
                    else:
                        offset = loc[0,cycle,dir]-loc[tool,cycle,dir]
                        
                        if cal_x:
                            if dir == 0:
                                self.output_to_terminal('x offset tool ' + str(self.tool_list[tool]) + ' when going up: ' + f"{offset:.3f}")
                            else:
                                self.output_to_terminal('x offset tool ' + str(self.tool_list[tool]) + ' when going down: ' + f"{offset:.3f}")
                        else:
                            if dir == 0:
                                self.output_to_terminal('y offset tool ' + str(self.tool_list[tool]) + ' when going up: ' + f"{offset:.3f}")
                            else:
                                self.output_to_terminal('y offset tool ' + str(self.tool_list[tool]) + ' when going down: ' + f"{offset:.3f}")
                   
                    #move the nozzle up and let the coil cool down
                    self.Diabase.write_line('G1 Z'+str(z_pos+cooldown_height)  + ' F' + str(default_speed*60))
                    self.Diabase.write_line('M400')
                    time.sleep(cooldown_time)
        #when finished with the calibration process, calculate the offsets between the tools and print them in the terminal
        for tool in range(len(self.tool_list)):
            if tool == 0:
                if cal_x:
                    self.output_to_terminal('average x position reference tool ' + str(self.tool_list[tool]) + ' when going up : ' + f"{loc[0,:,0].mean():.3f}" +' ± ' + f"{loc[0,:,0].std():.5f}")
                    self.output_to_terminal('average x position reference tool ' + str(self.tool_list[tool]) + ' when going down : ' + f"{loc[0,:,1].mean():.3f}" +' ± ' + f"{loc[0,:,1].std():.5f}")
                    self.output_to_terminal('average x position reference tool ' + str(self.tool_list[tool]) + ' as average : ' + f"{(loc[0,:,0]/2+loc[0,:,1]/2).mean():.3f}" +' ± ' + f"{(loc[0,:,0]/2+loc[0,:,1]/2).std():.5f}")
                else:
                    self.output_to_terminal('average y position reference tool ' + str(self.tool_list[tool]) + ' when going up :' + f"{loc[0,:,0].mean():.3f}" +' ± ' + f"{loc[0,:,0].std():.5f}")
                    self.output_to_terminal('average y position reference tool ' + str(self.tool_list[tool]) + ' when going down :' + f"{loc[0,:,1].mean():.3f}" +' ± ' + f"{loc[0,:,1].std():.5f}")
                    self.output_to_terminal('average y position reference tool ' + str(self.tool_list[tool]) + ' as average : ' + f"{(loc[0,:,0]/2+loc[0,:,1]/2).mean():.3f}" +' ± ' + f"{(loc[0,:,0]/2+loc[0,:,1]/2).std():.5f}")
            else:
                offsetup = loc[0,:,0]-loc[tool,:,0]
                offsetdown = loc[0,:,1]-loc[tool,:,1]
                offsetaverage = offsetup/2+offsetdown/2
                if cal_x:
                    self.output_to_terminal('average x offset tool ' + str(self.tool_list[tool]) + ' when going up : ' + f"{offsetup.mean():.3f}" +' ± ' + f"{offsetup.std():.5f}")
                    self.output_to_terminal('average x offset tool ' + str(self.tool_list[tool]) + ' when going down : ' + f"{offsetdown.mean():.3f}" +' ± ' + f"{offsetdown.std():.5f}")
                    self.output_to_terminal('average x offset tool ' + str(self.tool_list[tool]) + ' on average : ' + f"{offsetaverage.mean():.3f}" +' ± ' + f"{offsetdown.std():.5f}")
                else:
                    self.output_to_terminal('average y offset tool ' + str(self.tool_list[tool]) + ' when going up : ' + f"{offsetup.mean():.3f}" +' ± ' + f"{offsetup.std():.5f}")
                    self.output_to_terminal('average y offset tool ' + str(self.tool_list[tool]) + ' when going down : ' + f"{offsetdown.mean():.3f}" +' ± ' + f"{offsetdown.std():.5f}")
                    self.output_to_terminal('average y offset tool ' + str(self.tool_list[tool]) + ' on average : ' + f"{offsetaverage.mean():.3f}" +' ± ' + f"{offsetdown.std():.5f}")
                self.offset_tool_list.append(self.tool_list[tool])
                self.offset_list.append(offsetaverage.mean())
                self.offset_direction = cal_x
        #update settings dict
        self.save_settings()
        self.load_settings()

        #store the data of the calibraiton in a file with the name from filename textbox
        sio.savemat(filename,{'pos':pos, 'time':timestamps, 'data':data, 'loc':loc, 'tool_list':self.tool_list,'settings':self.settings_dict,'calibrated_x':cal_x})

        #home the printer        
        self.Diabase.write_line('G28')
        self.output_to_terminal('finished calibration')
        return True    

    def apply_offsets(self):
        """Function for handling the apply offset button being pressed. This will send the measured offsets to the printer.
        :return: None
        :rtype: None
        """
        for i1 in range(len(self.offset_tool_list)):
            if self.offset_direction:
                extra_offset = {}
                extra_offset['x'] = self.offset_list[i1]
                self.Diabase.set_tool_offset_differential(self.offset_tool_list[i1],extra_offset)
            else:
                extra_offset = {}
                extra_offset['y'] = self.offset_list[i1]
                self.Diabase.set_tool_offset_differential(self.offset_tool_list[i1],extra_offset)
        self.Diabase.write_line("T10")
        self.Diabase.store_offset_parameters()
        print('applied offsets')
    
    def func(self,x, o, a, b, c, d, e):
        """Polynomial function fitted to the measured inductance curve to determine the point of symmetry
        :param x: List of x coordinates at which the function should be evaluated
        :param o: The point of symmetry
        :param a: Constant offset
        :param b: Constant before the square
        :param c: Constant before the to the power 4
        :param d: Constant before the to the power 6
        :param e: Constant before the to the power 8
        :return: The output of the polynomial function
        :rtype: Boolean
        """
        return a + b * (x-o) ** 2 + c * (x-o) ** 4 + d * (x-o) ** 6 + e * (x-o) ** 8

    def find_symmetry_axis(self,x,y):
        """Function for calculating the point of symmetry of a a symmetric curve
        :param x: List of x coordinates 
        :param y: List of y coordinates
        :return: The oint of symmetry
        :rtype: float
        """
        y_min = np.min(y)
        y_max = np.max(y)
        x_avg = np.mean(x)
        x_min = np.min(x)
        b0 = (y_max-y_min)/(x_min-x_avg)**2
        p0 = [x_avg,y_min,b0,0,0,0]
        popt, _ = curve_fit(self.func, x, y,p0, maxfev=1000)
        #plt.plot(x,func(x,popt[0],popt[1],popt[2],popt[3],popt[4],popt[5]))
        return popt[0]    
        

    def save_settings(self):
        """Function for saving settings to a settings.yaml file
        :return: None
        :rtype: None
        """
        settings_dict = {}
        settings_dict['x_cor'] = self.x_box.value()
        settings_dict['y_cor'] = self.y_box.value()
        settings_dict['z_cor'] = self.z_box.value()
        settings_dict['range'] = self.range_box.value()
        settings_dict['speed'] = self.speed_box.value()
        settings_dict['ref_tool'] = int(self.ref_combo.currentText())
        settings_dict['x_rounds'] = int(self.rounds_x_spinner.value())
        settings_dict['y_rounds'] = int(self.rounds_y_spinner.value())
        settings_dict['nozzle_temperature'] = int(self.temp_box.value())
        settings_dict['bed_temperature'] = int(self.bed_temp_box.value())
        settings_dict['fan_on'] = self.fan_box.isChecked()
        settings_dict['homing_on'] = self.homing_box.isChecked()
        settings_dict['ascend'] = self.ascend_box.isChecked()
        settings_dict['version'] = '1.0.1'
        if self.update_tool_list():
            settings_dict['tool_list'] = self.tool_list

        with io.open('settings.yaml', 'w', encoding='utf8') as outfile:
                yaml.dump(settings_dict, outfile, default_flow_style=False, allow_unicode=True)

    def load_settings(self):
        """Function for loading settings to a settings.yaml file
        :return: False if unsuccesful, True if succesfull
        :rtype: Boolean
        """
        try:
            with open('settings.yaml', 'r') as stream:
                    self.settings_dict = yaml.safe_load(stream)
        except:
            return False

        if 'x_cor' in self.settings_dict:
            self.x_box.setValue(float(self.settings_dict['x_cor']))
        if 'y_cor' in self.settings_dict:
            self.y_box.setValue(float(self.settings_dict['y_cor']))
        if 'z_cor' in self.settings_dict:
            self.z_box.setValue(float(self.settings_dict['z_cor']))
        if 'x_rounds' in self.settings_dict:
            self.rounds_x_spinner.setValue(int(float(self.settings_dict['x_rounds'])))
        if 'y_rounds' in self.settings_dict:
            self.rounds_y_spinner.setValue(int(float(self.settings_dict['y_rounds'])))
        if 'range' in self.settings_dict:
            self.range_box.setValue(float(self.settings_dict['range']))
        if 'speed' in self.settings_dict:
            self.speed_box.setValue(float(self.settings_dict['speed']))
        if 'ref_tool' in self.settings_dict:
            ref_tool = int(self.settings_dict['ref_tool'])
            index = self.ref_combo.findText(str(ref_tool))
            if index >= 0:
                self.ref_combo.setCurrentIndex(index)
        if 'ascend' in self.settings_dict:
            self.ascend_box.setChecked(self.settings_dict['ascend'])
        if 'fan_on' in self.settings_dict:
            self.fan_box.setChecked(self.settings_dict['fan_on'])
        if 'homing_on' in self.settings_dict:
            self.homing_box.setChecked(self.settings_dict['homing_on'])
        if 'nozzle_temperature' in self.settings_dict:
            self.nozzle_temperature = self.temp_box.setValue(float(self.settings_dict['nozzle_temperature']))
        if 'bed_temperature' in self.settings_dict:
            self.bed_temperature = self.bed_temp_box.setValue(float(self.settings_dict['bed_temperature']))
        
        if 'tool_list' in self.settings_dict:
            tool_list_dict = self.settings_dict['tool_list']
            tool_list = list()
            for item in tool_list_dict:
                tool_list.append(int(item))
                list_item = self.tool_list_list.findItems(str(tool_list[-1]),Qt.MatchExactly)
                list_item[0].setSelected(True)

        return True
        
def main():
    pg.setConfigOption('background', 'w')
    pg.setConfigOption('foreground', 'k')
    pg.setConfigOption('useOpenGL',1)
    #pg.setConfigOption('useWeave',1)
    
    app = QtWidgets.QApplication(sys.argv)
    
    main = MainWindow()
    main.show()
    
    sys.exit(app.exec_())
    

if __name__ == '__main__':      
    main()

