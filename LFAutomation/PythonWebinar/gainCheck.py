# -*- coding: utf-8 -*-
"""
Created on Wed Oct 27 15:34:22 2021

@author: sliakat
"""

#quick gain check, assumes you set gated diode so that camera will not saturate on highest gain setting.
#exposure time 100ms for illumination -- set diode accordingly!
#run the cycle settings function after camera has cooled
#this version won't work on PI-MAX (gating) or Kuro (bit depth mismatch for diff speeds).

import clr
import sys
import os
import numpy as np
from System import String
from System.Collections.Generic import List
from System.Runtime.InteropServices import GCHandle, GCHandleType
import ctypes
import time

# Add needed dll references
sys.path.append(os.environ['LIGHTFIELD_ROOT'])
sys.path.append(os.environ['LIGHTFIELD_ROOT']+"\\AddInViews")
clr.AddReference('PrincetonInstruments.LightFieldViewV5')
clr.AddReference('PrincetonInstruments.LightField.AutomationV5')
clr.AddReference('PrincetonInstruments.LightFieldAddInSupportServices')

# PI imports
from PrincetonInstruments.LightField.Automation import Automation
from PrincetonInstruments.LightField.AddIns import CameraSettings
from PrincetonInstruments.LightField.AddIns import ExperimentSettings
from PrincetonInstruments.LightField.AddIns import RegionOfInterest

quality = {1:'LowNoise', 2:'HighCap', 3:'EM', 4:'HighSpd'}
gain = {1:'Low', 2:'Med', 3:'High'}
dataFormat = {1:ctypes.c_ushort, 2:ctypes.c_uint, 3:ctypes.c_float}

def SetROI():
    #if >= 100 rows, set to 100x100 ROI, else set to 100x1
    sensorCols = experiment.GetValue(CameraSettings.SensorInformationActiveAreaWidth)
    sensorRows = experiment.GetValue(CameraSettings.SensorInformationActiveAreaHeight)
    if sensorRows <100:
        experiment.SetCustomRegions([RegionOfInterest(int(sensorCols/2-50),0,100,1,1,1)])
    else:
        startX = int(sensorCols/2-50)   
        startY = int(sensorRows/2-50)
        #mod 4 check for symmetric ROIs in NIRVana (forced 4-port RO)
        if startX%4!=0:
            startX -= 2
        if startY%4!=0:
            startY -= 2        
        experiment.SetCustomRegions([RegionOfInterest(startX,startY,100,100,1,1)])

def LoadCamera(*,serial: str):
    #first clear out any camera that might be loaded already
    for eDev in experiment.ExperimentDevices:
        experiment.Remove(eDev)
    found = False
    for dev in experiment.AvailableDevices:
        if serial in dev.SerialNumber:
            experiment.Add(dev)
            SetROI()
            found = True
            break
    if not found:
        print('Desired camera not found or available.')
        
def DataToNumpy(imageDataSet, numFrames):
    dataArray = np.zeros(0)
    #find cols and rows from returned data using length of the perpecdicular slice
    numRows = imageDataSet.GetColumn(0,0,0).GetData().Length
    numCols = imageDataSet.GetRow(0,0,0).GetData().Length
    dataFmt = imageDataSet.GetFrame(0,0).Format
    for i in range(0,numFrames):    
        dataBuf = imageDataSet.GetFrame(0,i).GetData()     #.NET array
        src_hndl = GCHandle.Alloc(dataBuf, GCHandleType.Pinned)
        try:
            src_ptr = src_hndl.AddrOfPinnedObject().ToInt64()
            buf_type = dataFormat[dataFmt]*len(dataBuf)
            cbuf = buf_type.from_address(src_ptr)
            resultArray = np.frombuffer(cbuf, dtype=cbuf._type_)
        finally:        
            if src_hndl.IsAllocated: src_hndl.Free() 
        dataArray = np.append(dataArray,resultArray)        
    return np.reshape(dataArray, (numFrames,numRows,numCols))
    
def WriteFile(string):
    filename = 'C:\\Users\\sliakat\\Documents\\Python Gain Log\\GainLog.SN%s.txt'%SNDesired
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    with open(filename,'w') as f:
        current_time = time.strftime("%Y-%d-%m (yyyy-dd-mm) at %H:%M:%S", time.localtime()) + '\n'
        string = current_time + string
        f.write(string)

def GetAnalogGain():
    #discard first frame
    experiment.SetValue(ExperimentSettings.AcquisitionFramesToInitiallyDiscard, 1)
    #bias w/ 0-expose (avg of 5 dark frames)
    experiment.SetValue(ExperimentSettings.OnlineProcessingFrameCombinationFramesCombined, 5)
    experiment.SetValue(ExperimentSettings.OnlineProcessingFrameCombinationMethod, 2) #1 = sum, 2 = avg
    experiment.SetValue(CameraSettings.ShutterTimingExposureTime, experiment.GetCurrentRange(CameraSettings.ShutterTimingExposureTime).Minimum) #min exposure for camera
    bias = DataToNumpy(experiment.Capture(1), 1)
    
    #3 exposed frames, frame 1 to get mean illumination, frames 2-3 to get variance
    experiment.SetValue(ExperimentSettings.OnlineProcessingFrameCombinationFramesCombined, 1)
    experiment.SetValue(CameraSettings.ShutterTimingExposureTime, 100)
    illuminated = DataToNumpy(experiment.Capture(3), 3)
    
    #calculation
    meanSignal = np.mean(illuminated[0,:,:] - bias[0,:,:])
    variance = np.var((illuminated[1,:,:].flatten() - illuminated[2,:,:].flatten()))/2
    analogGain = meanSignal / variance
    return analogGain
    
def CycleSettings(string):    
    global finalStr
    for s in experiment.GetCurrentCapabilities(CameraSettings.AdcSpeed):      
        experiment.SetValue(CameraSettings.AdcSpeed, s)
        if experiment.IsRelevant(CameraSettings.AdcAnalogGain):            
            for g in experiment.GetCurrentCapabilities(CameraSettings.AdcAnalogGain):
                experiment.SetValue(CameraSettings.AdcAnalogGain, g)            
                settingStr = '%sSpeed: %0.3f MHz,\tGain: %s\t\t'%(string, s, gain[g])
                gainStr = '%s%0.3f e-/ct'%(settingStr,GetAnalogGain())
                print(gainStr)
                finalStr += (gainStr + '\n')             
        else:
            settingStr = '%sSpeed: %0.3f MHz,\tGain: N/A\t\t'%(string, s)
            gainStr = '%s%0.3f e-/ct'%(settingStr,GetAnalogGain())
            print(gainStr)
            finalStr += (gainStr + '\n')

def InitializeCycle():
    global finalStr
    #force one port
    if experiment.Exists(CameraSettings.ReadoutControlPortsUsed):
        if not experiment.IsReadOnly(CameraSettings.ReadoutControlPortsUsed):
            experiment.SetValue(CameraSettings.ReadoutControlPortsUsed, 1)
    if experiment.Exists(CameraSettings.AdcQuality):
        for q in experiment.GetMaximumCapabilities(CameraSettings.AdcQuality):
            outputStr = ''
            experiment.SetValue(CameraSettings.AdcQuality, q)
            outputStr += 'Quality: %s,\t'%(quality[q])
            CycleSettings(outputStr)
    else:
        CycleSettings('')
    WriteFile(finalStr)
    
                            

auto = Automation(True, List[String]())
experiment = auto.LightFieldApplication.Experiment
experiment.Load('Blank')
finalStr=''

SNDesired = '05579519'

#LoadCamera(serial=SNDesired)

#InitializeCycle()
