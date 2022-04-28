This folder contains an example for running PICam in MATLAB via a mex.

The source c++ shows the PICam and MATLAB class code. The user would need to build a mex64 function with this code. Consult the MATLAB documentation for more details.
The test m file shows how to run the built mex. Note the design to add open / acquire / close modules into a single mex and call individual modules with a switch. This is done so that the camera handle pointer is contained in one class object and does not need to transfer to different modules.
