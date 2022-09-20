#author: sabbi
#initially created 11/10/2021

import picam
import numpy as np
import argparse

def ParseArgs():
    global frameCount, asynch, exposure, roiSet, centerROIDim
    parser = argparse.ArgumentParser(description='Inputs for frame count, acquisition type, exposure time, and center ROI.\nExample usage: python3 -m picam-opencv 100 -s -exp 50 -roi 400')
    parser.add_argument('-p', action='store_true', help='preview mode (no data stored in np array)')
    parser.add_argument('-s', action='store_true', help='acquired data will be stored in np array')
    parser.add_argument('-exp', type=np.float64, nargs=1, help='exposure time (in ms)')
    parser.add_argument('-roi', type=np.int32, nargs=1, help='center ROI dimension (square - enter one integer only)')
    parser.add_argument('numFrames', type=int, nargs='?', default = 50, help='Number of frames to preview/ record')
    args = parser.parse_args()

    if args.numFrames >= 0:
        frameCount = args.numFrames
    if args.p:
        asynch = True
    if args.s:
        asynch = False
    if not (args.exp) == None:
        if (args.exp)[0] >= 0:
            exposure = (args.exp)[0]
    if not (args.roi) == None:
        if (args.roi)[0] > 0:
            roiSet = True
            centerROIDim = (args.roi)[0]

if __name__ == "__main__":
    #defaults for possible command line options
    frameCount = 10    #default number for frame count, can change with valid command line arg
    exposure = 100     #defaults to 100ms if not set in command line  
    asynch = True      #toggle to check the different acquisiton functions -- can toggle with command line arg
    roiSet = False     #toggle whether to set center n x n ROI
    centerROIDim = 100
    ParseArgs()         #parse any input args -- leave commented by default but use if you feel comfortable
    

    cam = picam.Camera()
    cam.OpenFirstCamera(model=1206)   #will open live camera if connected, otherwise opens virtual ProEM-HS demo cam
    cam.SetExposure(exposure)     #exposure time in ms
    cam.SetFastestADCSpeed()
    if roiSet:
        cam.SetCenterROI(centerROIDim)       #use to try out setting nxn square ROI in center of active region
    if asynch:
        cam.AcquireCB(frames=frameCount)       #asynchronously acquire with callback and preview n frames w/ opencv (does not save data)
    else:
        cam.Acquire(frames=frameCount)   #launch an acquisiton in a separate thread
    cam.DisplayCameraData()  #need to call display function to make multi-threading Acquire work, or else need to join the Acquire thread manually
    cam.Close()

    if not asynch:
        data = cam.ReturnData()
        for i in range(0,len(data)):
            print('Shape of returned data (ROI %d) is '%(i+1), np.shape(data[i]),'\n\tMean of ROI %d is: %0.3f cts'%((i+1),np.mean(data[i])))
            
