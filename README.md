This program can be used to calibration the x and y offset of a multi-material 3D printer using LDC1101EVM evaluation module, to which a coil is mounted.

<img src="https://user-images.githubusercontent.com/6079002/137327595-4b70b5c3-cb55-4091-8608-67f0f5b063d4.jpg" width="300">

The evaluation module should be placed on the bed and the printer and the module should be connected using usb cables to your computer. Then when running this program it will move each nozzle over the coil and determine the offset between the nozzles.

# Typical usage
1. Run the installer, which can be found here: https://github.com/martijnschouten/inductive_calibration_GUI/releases
1. Place the LDC1101EVM on the bed
1. Connect the printer and the LDC1101EVM to the computer on which you ran the installer
1. Manually move the printer such that the first tool is just above the coil.
1. Run the program and copy the current location of the printer in x-coordinate coil, y-coordinate coil z-height test. Note that this does not need to be very precise
1. Check that scanning range (default 2mm), speed (default 0.5mm/s), nozzle temperature (default 175) and bed temepature (default 0) are set to appropriate values
1. Select the tools that need to be calibrated and select the tool relative to which the offset will be shown
1. Run Calibrate X. The printer will now start moving the nozzles over the coil
1. Check that the found offsets make sense. And click on apply offsets.
1. Run Calibrate Y. The printer will now start moving the nozzles over the coil
1. Check that the found offsets make sense. And click on apply offsets.

# Compilation instructions
On windows:
1. Make sure you have a working python installation (tested using python 3.7.7)
1. Open command prompt
1. Use the 'cd' to go to the folder that contains the content of this git
1. Make a virtual environment by running 'python -m venv'
1. Activate the virtual environment by running 'venv\Scripts\activate'
1. Install the dependencies by running 'pip install pyqt5==5.10.1 pyqtgraph pyserial pyaml scipy pyinstaller'


# Acknowledgement
This work was developed within the Wearable Robotics programme, funded by the Dutch Research Council (NWO)

<img src="https://user-images.githubusercontent.com/6079002/124443163-bd35c400-dd7d-11eb-9fe5-53c3def86459.jpg" width="62" height="100"><img src="https://user-images.githubusercontent.com/6079002/124443273-d3dc1b00-dd7d-11eb-9282-54c56e0f42db.png" width="165" height="100">
