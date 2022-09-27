picam.py contains the class definition for Camera, which can be instantiated and then controlled via member functions. Functions are basic and designed for demonstration. Note that this is a work in progress and will be periodically updated.

picam_opencv.py is a test script to show how the Camera class can be used to quickly open and acquire with a camera.

This example was made with Linux in mind, but if the libPath kwarg in the constructor is entered as the path to Picam.dll in Windows, the code should work in Windows as well.

code was tested with:
- CentOS7 x86_64 (kernel 3.10.0)
- Python 3.8
- numpy 1.21.4
- opencv-python 4.5.4.60
- PICam 5.11.2

also verified working with**:
- Ubuntu LTS 22.04 (kernel 5.15.0-47-generic)
- Python 3.10
- numpy 1.23.2
- opencv-python 4.6.0.66
- PICam 5.12.3.2209
**WE DO NOT OFFICIALLY SUPPORT ANY DISTRO OUTSIDE OF CENTOS7.
WHILE I GOT PICAM TO WORK ON UBUNTU, THERE WERE PACKAGE CHANGES
I HAD TO MAKE. IF YOU WANT TO RUN ON A NON-CENTOS7 DISTRO, YOU
WILL NEED TO FIGURE OUT WHAT CHANGES ARE NEEDED FOR YOUR DISTRO**

***************************************
Test script sample use (in terminal):
python3 -m picam-opencv 0 -p -exp 0 -speed 20 -roi 400

Sample output:
PICam Initialized: True
	Version 5.12.3.2209
*****
2 Teledyne SciCam camera(s) detected:
[1]: E2V 1024 x 1024 (CCD 351)(B)(eXcelon), Serial #: Eng_12345
[2]: E2V 2048 x 2048 (CCD 230-42)(B)(MP)(eXcelon), Serial #: 08701220
*****
Enter the integer for the camera you want to open, or 0 for demo:
1
*****
Camera Sensor: E2V 1024 x 1024 (CCD 351)(B)(eXcelon), Serial #: Eng_12345
%%%%%
Camera Firmware:
Config                  	0x1087,363,4.0
Camera                  	0x48B2,487,2.53
Power                   	0x4887,492,1.0
%%%%%
Default ROI: 1024 (cols) x 1024 (rows)
Trying to commit exposure time to 0.00 ms... Exposure committed to 0.00 ms.
Valid ADC Speeds for this camera (in MHz):
	36.670, 30.000, 20.000, 10.000, 5.000

Attempting to set ADC Speed to 20.000 MHz... ADC Speed set to 20.000 MHz
Successfully changed ROI to 400 (cols) x 400 (rows)
	Commit successful! Current readout rate: 39.66 readouts/sec
ROI 1 shape:  (1, 400, 400)
*****
Sensor Temperature -70.00C (Locked). Set Point -70.00C.
*****
Acquisition of 0 frames started (preview mode)...

Key pressed during acquisition -- acquisition will stop.
Mean of most recently processed frame: 15603.096 cts
Acquisition stopped. 112 readouts obtained in 3.576s.
