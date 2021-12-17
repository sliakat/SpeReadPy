#author: sabbi
#11/10/2021

import picam
import numpy as np

cam = picam.Camera()
cam.OpenFirstCamera(model=1206)   #will open live camera if connected, otherwise opens virtual demo cam
asynch = True
if asynch:
    cam.AcquireCB(frames=100)       #asynchronously acquire with callback and preview n frames w/ opencv
    cam.DisplayCameraData()
else:
    data = cam.Acquire(frames=50)   #when acquire finishes, pressing any key or waiting 20s will exit the opencv viewer

cam.Close()

try:
    print(np.mean(data[-1,:,:])) #total acquired data will be available as numpy array for further analysis
except:
    pass
