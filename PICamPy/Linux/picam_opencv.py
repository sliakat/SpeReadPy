#author: sabbi
#initially created 11/10/2021

import picam
import numpy as np
import argparse

def ParseArgs():
    global frameCount, asynch
    parser = argparse.ArgumentParser(description='Inputs for frame count and acquisition type.')
    parser.add_argument('-p', action='store_true', help='preview mode (no data stored in np array)')
    parser.add_argument('-s', action='store_true', help='acquired data will be stored in np array')
    parser.add_argument('numFrames', type=int, nargs='?', default = 50, help='Number of frames to preview/ record')
    args = parser.parse_args()

    if args.numFrames > 0:
        frameCount = args.numFrames
    if args.p:
        asynch = True
    if args.s:
        asynch = False

if __name__ == "__main__":
    #defaults for possible command line options
    frameCount = 10    #default number for frame count, can change with valid command line arg    
    asynch = False      #toggle to check the different acquisiton functions -- can toggle with command line arg
    #ParseArgs()         #parse any input args -- leave commented by default but use if you feel comfortable
    

    cam = picam.Camera(libPath='C:\\Program Files\\Common Files\\Princeton Instruments\\Picam\\Runtime\\Picam.dll')
    cam.OpenFirstCamera(model=1206)   #will open live camera if connected, otherwise opens virtual ProEM-HS demo cam
    cam.SetExposure(100)     #exposure time in ms
    cam.SetROIs(10)
    if asynch:
        cam.AcquireCB(frames=frameCount)       #asynchronously acquire with callback and preview n frames w/ opencv (does not save data)
    else:
        cam.Acquire(frames=frameCount)   #launch an acquisiton in a separate thread -- temporarily removed threading
    cam.DisplayCameraData()  #need to call display function to make multi-threading Acquire work, or else need to join the Acquire thread manually
    cam.Close()

    if not asynch:
        data = cam.ReturnData()
        for i in range(0,len(data)):
            print('Shape of returned data (ROI %d) is '%(i+1), np.shape(data[i]),'\n\tMean of ROI %d is: %0.3f cts'%((i+1),np.mean(data[i])))
