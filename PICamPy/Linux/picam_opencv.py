#author: sabbi
#11/10/2021

import picam
import numpy as np

cam = picam.Camera()
cam.OpenFirstCamera(model=60)   #will open live camera if connected, otherwise opens virtual demo cam
data = cam.Acquire(frames=50)   #when acquire finishes, pressing any key or waiting 20s will exit the opencv viewer
cam.Close()

print(np.shape(data)) #total acquired data will be available as numpy array for further analysys
