#author: sabbi
#11/10/2021

import picam
import numpy as np
import time

cam = picam.Camera()    #default behavior is to look in Linux path. To use with Windows, enter libPath='<<path to Picam.dll>>'
cam.OpenFirstCamera(model=1206)   #will open live camera if connected, otherwise opens virtual demo cam
cam.SetExposure(50)     #exposure time in ms
asynch = True      #toggle to check the different acquisiton functions
if asynch:
    cam.AcquireCB(frames=200)       #asynchronously acquire with callback and preview n frames w/ opencv (does not save data)
else:
    cam.Acquire(frames=100)   #launch an acquisiton in a separate thread
cam.DisplayCameraData()
cam.Close()

if not asynch:
    data = cam.ReturnData()
    print('Shape of returned data is ', np.shape(data))
