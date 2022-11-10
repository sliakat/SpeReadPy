picam.py contains the class definition for Camera, which can be instantiated and then controlled via member functions. Functions are designed for demonstration and should not be considered an official API. Note that this is a work in progress and will be periodically updated.

picam-CLtest.py is a test script to show how the Camera class can be used to quickly open and acquire with a camera.

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

Windows test (with MPL):
- Windows 10 ENterprise (build 19045.2130)
- Python 3.10.6
- numpy 1.23.3
- matplotlib 3.6.0
- PICam 5.12.3.2209

**WE DO NOT OFFICIALLY SUPPORT ANY LINUX DISTRO OUTSIDE OF CENTOS7.
WHILE I GOT PICAM TO WORK ON UBUNTU, THERE WERE PACKAGE CHANGES
I HAD TO MAKE. IF YOU WANT TO RUN ON A NON-CENTOS7 DISTRO, YOU
WILL NEED TO FIGURE OUT WHAT CHANGES ARE NEEDED FOR YOUR DISTRO**
