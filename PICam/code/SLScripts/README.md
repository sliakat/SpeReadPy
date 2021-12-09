The contents in this folder are simple c++ console apps showing how to use commonly needed PICam SDK commands.
The dynamically linked scripts can also serve as a quick means for testing PICam pathing and camera communication.

SLBasicAsynchApp.cpp -- uses WaitForAcquisitonUpdate to asynchronously acquire from the camera, and uses OpenCV to display the image stream from the camera. PICam and OpenCV need to be statically linked upon compile

CameraTestDynamicLink.cpp -- loads PICam.dll (if found) and does a simple synchronous acquisition (Acquire command) with default camera settings. This can be compiled without any static PICam libraries, making it a good candiate for quick camera tests.

CameraTestDynamicLinkCallback.cpp -- same concept as the previous, but performs asynchronous acquisition and returns live data via a callback. User also has the option to enter a long int as a command line argument to set the desired number of readouts. Another good candidate for quick camera tests.

