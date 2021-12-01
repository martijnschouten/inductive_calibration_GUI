.. inductive calibration GUI documentation master file, created by
   sphinx-quickstart on Wed Dec  1 10:50:33 2021.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to inductive calibration GUI's documentation!
=====================================================

.. toctree::
   :maxdepth: 2
   :caption: Contents:

This documentation documenents the code of a GUI for calibrating a Diabase H-Series 3D printer in x and y using and LDC1101EVM evaluation module. The easiest way to run a frozen binary which can be found in `releases <https://github.com/martijnschouten/inductive_calibration_GUI/releases>`_

The inductive calibraiton GUI consists of three classes. The mainwindow of the app contain the entire GUI. The diabase class implements the communication with the diabase 3D printer and the ldc1101evm class implements the communication with the LDC1101EVM evaluation module.

App mainwindow class
==============
.. automodule:: app
   :members:
   :undoc-members:
   :show-inheritance:

diabase class
=============
.. automodule:: diabase
   :members:
   :undoc-members:
   :show-inheritance:

ldc1101evm class
=============
.. automodule:: ldc1101evm
   :members:
   :undoc-members:
   :show-inheritance:

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
