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
    isRunning = False
    connected = False
    duet_port = ''
    offset_tool_list = []
    offset_list = []
    stop_button_clicked = False
    ascend = True

    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)

        #Load the UI Page
        uic.loadUi('interface.ui', self)
        QtWidgets.QApplication.processEvents()

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
        self.update_coil_button.clicked.connect(self.update_coil)
        self.reload()
        
        #find and select the right com ports.
        

        self.load_settings()
    def reload(self):
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
        self.stop_button_clicked = True

    def clear_figure(self):
        self.sig_graph.clear()
        self.curve = list()
        
        if self.tool_list:
            for i1 in range(len(self.tool_list*2)):
                self.curve.append(self.sig_graph.plot())

    def connect(self):
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
        current_text = self.output_terminal.toPlainText()
        text =  new_text +"\r\n" + current_text
        self.output_terminal.setText(text)
        QtWidgets.QApplication.processEvents()

    def update_tool_list(self):
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
        self.isRunning=False
        self.save_settings()

    def calibrate_y(self):
        cal_x = False
        self.calibrate(cal_x)

    def calibrate_x(self):
        cal_x = True
        self.calibrate(cal_x)

    def ascend_changed(self):
        if self.ascend_box.isChecked():
            self.descend_box.setChecked(False)
            self.ascend = True
        else:
            self.descend_box.setChecked(True)
            self.ascend = False

    def descend_changed(self):
        if self.descend_box.isChecked():
            self.ascend_box.setChecked(False)
            self.ascend = False
        else:
            self.ascend_box.setChecked(True)
            self.ascend = True
        

    def test_sensor(self):
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
        if self.connected == False:
            self.connect()

        self.output_to_terminal('started calibration')

       

        x_pos = self.x_box.value()
        y_pos = self.y_box.value()
        z_pos = self.z_box.value()
        ref_tool = int(self.ref_combo.currentText())
        scan_range = self.range_box.value()
        speed = self.speed_box.value()
        filename = self.filename_line.text()

        if cal_x:
            rounds = self.rounds_x_spinner.value()
        else:
            rounds=  self.rounds_y_spinner.value()

        if cal_x:
            x_start = x_pos - scan_range
            x_stop = x_pos + scan_range
        else:
            y_start = y_pos - scan_range
            y_stop = y_pos + scan_range

        cooldown_time = 3.0
        cooldown_height = 1
        plotting_interval = 5
        buffer_size = 1e4
        default_speed = 60
        speed_factor = 1.5

        buffer_size = int(buffer_size)

        if not self.update_tool_list():
            return 0

        try:
            if self.fan_box.isChecked():
                #self.Diabase.write_line('M106 P3 S255')
                self.Diabase.write_line('M106 P3 S255')
            else:
                #self.Diabase.write_line('M106 P3 S0')
                self.Diabase.write_line('M106 P3 S0')
        except:
            self.output_to_terminal('error: could not find a Duet')
            return 0

        for i1 in range(len(self.tool_list)):
            self.Diabase.write_line('G10 P%.0f R%.0f  S%.0f' % (self.tool_list[i1],self.temp_box.value(),self.temp_box.value()))
        
        self.Diabase.write_line('M140 S%.0f' % (self.bed_temp_box.value()))

        time.sleep(1)
        
        print("doing the M116")
        self.Diabase.write_line('M116')

        print("received the M116")
        self.Diabase.write_line('G54')

        
        self.curve = list()
        for i1 in range(len(self.tool_list)*2):
            self.curve.append(self.sig_graph.plot())
        
        
        loc = np.zeros([len(self.tool_list),rounds,2])
        data = np.zeros([buffer_size,len(self.tool_list),rounds,2])
        pos = np.zeros([buffer_size,len(self.tool_list),rounds,2])
        timestamps = np.zeros([buffer_size,len(self.tool_list),rounds,2])

        tic = time.time()
        for i4 in range(rounds):
            if self.homing_box.isChecked() or i4 ==0:     
                self.Diabase.write_line('G28')
                self.Diabase.write_line('G90')
                self.Diabase.write_line('G1 X0 Y0 Z8 F8000')
                self.Diabase.write_line('G30')

            self.Diabase.write_line('M400')
            #diabase.write_line('G28 Z')
            QtWidgets.QApplication.processEvents()
            if self.stop_button_clicked:
                self.stop_button_clicked = False
                return 0
            
            self.Diabase.write_line('T'+str(self.tool_list[0]))
            print("selected tool "+ str(self.tool_list[0]))
            self.Diabase.write_line('M400')

            QtWidgets.QApplication.processEvents()
            if self.stop_button_clicked:
                self.stop_button_clicked = False
                return 0
            
            if cal_x:
                self.Diabase.write_line('G1 Z'+str(z_pos+cooldown_height)+' Y'+str(y_pos)+' X'+str(x_start) + ' F' + str(default_speed*60))
            else:
                self.Diabase.write_line('G1 Z'+str(z_pos+cooldown_height)+' Y'+str(y_start)+' X'+str(x_pos) + ' F' + str(default_speed*60))
            print("commanded to go to initial position")
            self.Diabase.write_line('M400')
            #time.sleep(10)
            

            self.offset_tool_list = []
            self.offset_list = []
            
            for i3 in range(len(self.tool_list)):
                #print(tool_list[i3])
                print("selected tool "+ str(self.tool_list[i3]))
                self.Diabase.write_line('T'+str(self.tool_list[i3]))
                self.Diabase.write_line('M400')
                #time.sleep(5)

                for i5 in range(2):#go forwards and backwards.
                    
                    if cal_x:
                        if i5 == 0:
                            self.Diabase.write_line('G1 Z'+str(z_pos)+' Y'+str(y_pos)+' X'+str(x_start) + ' F' + str(default_speed*60))
                        else:
                            self.Diabase.write_line('G1 Z'+str(z_pos)+' Y'+str(y_pos)+' X'+str(x_stop) + ' F' + str(default_speed*60))
                    else:
                        if i5 == 0:
                            self.Diabase.write_line('G1 Z'+str(z_pos)+' Y'+str(y_start)+' X'+str(x_pos) + ' F' + str(default_speed*60))
                        else:
                            self.Diabase.write_line('G1 Z'+str(z_pos)+' Y'+str(y_stop)+' X'+str(x_pos) + ' F' + str(default_speed*60))
                    self.Diabase.write_line('M400')
                    #time.sleep(1)
                    self.Ldc1101evm.flush()
                    self.Ldc1101evm.get_LHR_data(50)
                    i1 = 0#total samples number
                    tic2 = time.time()
                    while(True):
                        if self.stop_button_clicked:
                            self.stop_button_clicked = False
                            return 0

                        toc2 = time.time() -tic2
                        if cal_x:
                            if i5 == 0:
                                new_x = x_start+toc2*speed
                            else:
                                new_x = x_stop-toc2*speed
                            self.Diabase.write_line('G1 X' + str(new_x) + " F" + str(speed*60*speed_factor))
                        else:
                            if i5 == 0:
                                new_y = y_start+toc2*speed
                            else:
                                new_y = y_stop-toc2*speed
                            self.Diabase.write_line('G1 Y' + str(new_y) + " F" + str(speed*60*speed_factor))
                        self.Diabase.write_line('M400')
                        self.Ldc1101evm.flush()
                        data[i1,i3,i4,i5] = self.Ldc1101evm.get_LHR_data(50)
                        timestamps[i1,i3,i4,i5] = time.time()-tic
                        #pos_package =  self.Diabase.get_current_position()
                        if cal_x:
                            pos[i1,i3,i4,i5] = new_x
                        else:
                            pos[i1,i3,i4,i5] = new_y
                        i1 = i1 + 1
                        if i1%plotting_interval == 0:
                            self.curve[i3*2+i5].setData(pos[0:i1,i3,i4,i5],data[0:i1,i3,i4,i5])
                        if cal_x:
                            if (i5 ==0 and new_x >= x_stop) or (i5 == 1 and new_x <= x_start):    
                                break  
                        else:
                            if (i5 ==0 and new_y >= y_stop) or (i5 == 1 and new_y <= y_start): 
                                break
                        
                        QtWidgets.QApplication.processEvents()
                    
                    try:
                        loc[i3,i4,i5] = self.find_symmetry_axis(pos[int(i1/10):int(9/10*i1),i3,i4,i5],data[int(i1/10):int(9/10*i1),i3,i4,i5])
                    except RuntimeError:
                        self.output_to_terminal('error: calibration curve to ugly to fit')
                        break

                    if i3 == 0:
                        if cal_x:
                            if i5 == 0:
                                self.output_to_terminal('x position reference tool ' + str(self.tool_list[i3]) + ' when going up: ' + f"{loc[0,i4,i5]:.3f}")
                            else:
                                self.output_to_terminal('x position reference tool ' + str(self.tool_list[i3]) + ' when going down: ' + f"{loc[0,i4,i5]:.3f}")
                        else:
                            if i5 == 0:
                                self.output_to_terminal('y position reference tool ' + str(self.tool_list[i3]) + ' when going up: ' + f"{loc[0,i4,i5]:.3f}")
                            else:
                                self.output_to_terminal('y position reference tool ' + str(self.tool_list[i3]) + ' when going down: ' + f"{loc[0,i4,i5]:.3f}")
                    else:
                        offset = loc[0,i4,i5]-loc[i3,i4,i5]
                        
                        if cal_x:
                            if i5 == 0:
                                self.output_to_terminal('x offset tool ' + str(self.tool_list[i3]) + ' when going up: ' + f"{offset:.3f}")
                            else:
                                self.output_to_terminal('x offset tool ' + str(self.tool_list[i3]) + ' when going down: ' + f"{offset:.3f}")
                        else:
                            if i5 == 0:
                                self.output_to_terminal('y offset tool ' + str(self.tool_list[i3]) + ' when going up: ' + f"{offset:.3f}")
                            else:
                                self.output_to_terminal('y offset tool ' + str(self.tool_list[i3]) + ' when going down: ' + f"{offset:.3f}")
                    self.Diabase.write_line('G1 Z'+str(z_pos+cooldown_height)  + ' F' + str(default_speed*60))
                    self.Diabase.write_line('M400')
                    time.sleep(cooldown_time)

        for i3 in range(len(self.tool_list)):
            if i3 == 0:
                if cal_x:
                    self.output_to_terminal('average x position reference tool ' + str(self.tool_list[i3]) + ' when going up : ' + f"{loc[0,:,0].mean():.3f}" +' ± ' + f"{loc[0,:,0].std():.5f}")
                    self.output_to_terminal('average x position reference tool ' + str(self.tool_list[i3]) + ' when going down : ' + f"{loc[0,:,1].mean():.3f}" +' ± ' + f"{loc[0,:,1].std():.5f}")
                    self.output_to_terminal('average x position reference tool ' + str(self.tool_list[i3]) + ' as average : ' + f"{(loc[0,:,0]/2+loc[0,:,1]/2).mean():.3f}" +' ± ' + f"{(loc[0,:,0]/2+loc[0,:,1]/2).std():.5f}")
                else:
                    self.output_to_terminal('average y position reference tool ' + str(self.tool_list[i3]) + ' when going up :' + f"{loc[0,:,0].mean():.3f}" +' ± ' + f"{loc[0,:,0].std():.5f}")
                    self.output_to_terminal('average y position reference tool ' + str(self.tool_list[i3]) + ' when going down :' + f"{loc[0,:,1].mean():.3f}" +' ± ' + f"{loc[0,:,1].std():.5f}")
                    self.output_to_terminal('average y position reference tool ' + str(self.tool_list[i3]) + ' as average : ' + f"{(loc[0,:,0]/2+loc[0,:,1]/2).mean():.3f}" +' ± ' + f"{(loc[0,:,0]/2+loc[0,:,1]/2).std():.5f}")
                self.reference_location = (loc[0,:,0]/2+loc[0,:,1]/2).mean()
            else:
                offsetup = loc[0,:,0]-loc[i3,:,0]
                offsetdown = loc[0,:,1]-loc[i3,:,1]
                offsetaverage = offsetup/2+offsetdown/2
                if cal_x:
                    self.output_to_terminal('average x offset tool ' + str(self.tool_list[i3]) + ' when going up : ' + f"{offsetup.mean():.3f}" +' ± ' + f"{offsetup.std():.5f}")
                    self.output_to_terminal('average x offset tool ' + str(self.tool_list[i3]) + ' when going down : ' + f"{offsetdown.mean():.3f}" +' ± ' + f"{offsetdown.std():.5f}")
                    self.output_to_terminal('average x offset tool ' + str(self.tool_list[i3]) + ' on average : ' + f"{offsetaverage.mean():.3f}" +' ± ' + f"{offsetdown.std():.5f}")
                else:
                    self.output_to_terminal('average y offset tool ' + str(self.tool_list[i3]) + ' when going up : ' + f"{offsetup.mean():.3f}" +' ± ' + f"{offsetup.std():.5f}")
                    self.output_to_terminal('average y offset tool ' + str(self.tool_list[i3]) + ' when going down : ' + f"{offsetdown.mean():.3f}" +' ± ' + f"{offsetdown.std():.5f}")
                    self.output_to_terminal('average y offset tool ' + str(self.tool_list[i3]) + ' on average : ' + f"{offsetaverage.mean():.3f}" +' ± ' + f"{offsetdown.std():.5f}")
                self.offset_tool_list.append(self.tool_list[i3])
                self.offset_list.append(offsetaverage.mean())
                self.offset_direction = cal_x
        #update settings dict
        self.save_settings()
        self.load_settings()
        sio.savemat(filename,{'pos':pos, 'time':timestamps, 'data':data, 'loc':loc, 'tool_list':self.tool_list,'settings':self.settings_dict,'calibrated_x':cal_x})
                
        self.Diabase.write_line('G28')
        self.output_to_terminal('finished calibration')

    def func(self,x, o, a, b, c, d, e):
        return a + b * (x-o) ** 2 + c * (x-o) ** 4 + d * (x-o) ** 6 + e * (x-o) ** 8

    def update_coil(self):
        if self.reference_location:
            self.y_box.setValue(self.reference_location)

    def apply_offsets(self):
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
        
    def find_symmetry_axis(self,x,y):
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

