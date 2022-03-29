# inductive 3D printer XY calibration GUI 
This program can be used to calibration the x and y offset of a multi-material 3D printer using LDC1101EVM evaluation module, to which a coil is mounted with the axis perpendicular to the PCB.

<img src="https://user-images.githubusercontent.com/6079002/137327595-4b70b5c3-cb55-4091-8608-67f0f5b063d4.jpg" width="300">

The evaluation module should be placed on the bed and the printer and the module should be connected using usb cables to your computer. Then when running this program it will move each nozzle over the coil and determine the offset between the nozzles. This works because the nozzle will cause a decrease in the inductance of the coil as is described in this paper [future link]() ([future open access link]()). 

# Typical usage
1. Run the installer, which can be found here: https://github.com/martijnschouten/inductive_calibration_GUI/releases
2. Home the printer
4. Go to the offsets tap and press measure Z
5. Place the LDC1101EVM on the bed
6. Connect the printer and the LDC1101EVM to the computer on which you ran the installer
7. Close make sure that Cura is closed since it claim the COM ports of the sensor and the printer for itself
8. Manually move the printer such that the first tool is just above the coil.
9. Run the program and copy the current location of the printer in x-coordinate coil, y-coordinate coil z-height test. Note that this does not need to be very precise
10. Check that scanning range (default 2mm), speed (default 0.5mm/s), nozzle temperature (default 175) and bed temepature (default 0) are set to appropriate values
11. Select the tools that need to be calibrated and select the tool relative to which the offset will be shown
12. Press Calibrate X. The printer will now start moving the nozzles over the coil
13. Check that the found offsets make sense. And click on apply offsets.
14. Press Calibrate Y. The printer will now start moving the nozzles over the coil
15. Check that the found offsets make sense. And click on apply offsets.

# Compilation instructions
On windows:
1. Make sure you have a working python installation (tested using python 3.7.7)
1. Open command prompt
1. Use the `cd` to go to the folder that contains the content of this git
1. Make a virtual environment by running `python -m venv venv`
1. Activate the virtual environment by running `venv\Scripts\activate`
1. Install the dependencies by running `pip install pyqt5 pyqtgraph pyserial pyaml scipy pyinstaller sphinx sphinx-rtd-theme`
1. Freeze the python app by running `make.bat` in the terminal
1. To make the installer, run installer.iss using inno setup compiler
 
For more information on the code read the [documentation](docs/build/latex/inductivecalibrationgui.pdf)
# Acknowledgement
This work was developed within the Wearable Robotics programme, funded by the Dutch Research Council (NWO)

<img src="https://user-images.githubusercontent.com/6079002/124443163-bd35c400-dd7d-11eb-9fe5-53c3def86459.jpg" width="62" height="100"><img src="https://user-images.githubusercontent.com/6079002/124443273-d3dc1b00-dd7d-11eb-9282-54c56e0f42db.png" width="165" height="100">
