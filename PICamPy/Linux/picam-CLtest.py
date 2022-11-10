#author: sabbi
#initially created 11/10/2021

import picam
import numpy as np
from matplotlib import pyplot as plt
import argparse

def ParseArgs():
    global frameCount, preview, exposure, roiSet, centerROIDim, saveDisk, speed, binRows
    parser = argparse.ArgumentParser(description='Inputs for frame count, acquisition type, exposure time, and center ROI.\nExample usage: python3 -m picam-opencv 100 -s -exp 50 -roi 400')
    parser.add_argument('-p', action='store_true', help='preview mode (no data stored)')
    parser.add_argument('-s', action='store_true', help='acquired data will be stored in np array on memory')
    parser.add_argument('-d', action='store_true', help='acquired data will be stored in a *.raw file')
    parser.add_argument('-exp', type=np.float64, nargs=1, help='exposure time (in ms)')
    parser.add_argument('-roi', type=np.int32, nargs=1, help='center ROI dimension (square - enter one integer only)')
    parser.add_argument('-speed', type=np.float64, nargs=1, help='Desired ADC speed to run camera (in MHz). User input must match camera capable collection value to within 15kHz. Set to 0 to auto-select fastest speed for camera.')
    parser.add_argument('-sbin', type=np.int32, nargs=1, help='SpecBIN-Desired number of center rows to bin (with full sensor width). Will cancel -roi')
    parser.add_argument('numFrames', type=int, nargs='?', default = 50, help='Number of frames to preview/ record')
    args = parser.parse_args()

    if args.numFrames >= 0:
        frameCount = args.numFrames
    if args.p:
        preview = True
    if args.s:
        preview = False
    #if both -s and -d present, should go to -d behavior
    if args.d:
        preview = False
        saveDisk = True
    if not (args.exp) == None:
        if (args.exp)[0] >= 0:
            exposure = (args.exp)[0]
    if not (args.roi) == None:
        if (args.roi)[0] > 0:
            roiSet = True
            centerROIDim = (args.roi)[0]
    if not (args.speed) == None:
        if (args.speed)[0] >= 0:
            speed = (args.speed)[0]
    if not (args.sbin) == None:
        if (args.sbin)[0] > 0:
            roiSet = False
            binRows = (args.sbin)[0]

if __name__ == "__main__":
    #defaults for possible command line options
    frameCount = 10    #default number for frame count, can change with valid command line arg
    exposure = 100     #defaults to 100ms if not set in command line  
    preview = True      #toggle to check the different acquisiton functions -- can toggle with command line arg
    roiSet = False     #toggle whether to set center n x n ROI
    centerROIDim = 100
    saveDisk = False
    speed = 0          #set through command line or enter valid value here -- 0 will call SetFastest
    binRows = 0
    ParseArgs()         #parse any input args
    
    #For Linux / Windows lines, comment out the one you are not using
    #Linux
    cam = picam.Camera(dispType=1)
    #Windows
    #cam = picam.Camera(libPath = 'C:\\Program Files\\Common Files\\Princeton Instruments\\Picam\\Runtime\\Picam.dll',dispType=1)
    if cam.OpenCamera():
        cam.SetExposure(exposure)     #exposure time in ms
        if speed == 0:
            cam.SetFastestADCSpeed()
        else:
            cam.SetADCSpeed(speed)

        if roiSet:
            cam.SetCenterROI(centerROIDim)       #use to try out setting nxn square ROI in center of active region
        elif binRows > 0:
            cam.SetCenterBinROI(binRows)        #bin n nows in center (use full sensor width)
        
        if preview:
            cam.AcquireCB(frames=frameCount, bufNomWidth=20)       #asynchronously acquire with callback and preview n frames w/ opencv (does not save data)
        else:
            cam.Acquire(frames=frameCount, bufNomWidth=20, saveDisk=saveDisk)   #launch an acquisiton in a separate thread
        cam.DisplayCameraData()  #need to call display function to make multi-threading Acquire work, or else need to join the Acquire thread manually
    cam.Close()

    if not preview:
        output = cam.ReturnData()
        if not saveDisk:
            for i in range(0,len(output)):
                print('Shape of returned data (ROI %d) is '%(i+1), np.shape(output[i]),'\n\tMean of ROI %d is: %0.3f cts'%((i+1),np.mean(output[i])))
        else:
            #if data is saved to disk, there will not be any data kept in memory
            print(output)