# -*- coding: utf-8 -*-
"""
Created on Mon Mar 30 10:16:26 2020

@author: sliakat
"""

#declarations
import clr

# Import python sys module
import sys

# Import modules
import os, glob, string

# Import System.IO for saving and opening files
from System.IO import *
from System.Runtime.InteropServices import Marshal
from System.Runtime.InteropServices import GCHandle, GCHandleType

from System.Threading import AutoResetEvent

# Import c compatible types
from System import String, Int32, Int64, Double
from System.Collections.Generic import List

# Add needed dll references
sys.path.append(os.environ['LIGHTFIELD_ROOT'])
sys.path.append(os.environ['LIGHTFIELD_ROOT']+"\\AddInViews")
clr.AddReference('PrincetonInstruments.LightFieldViewV5')
clr.AddReference('PrincetonInstruments.LightField.AutomationV5')
clr.AddReference('PrincetonInstruments.LightFieldAddInSupportServices')

# PI imports
from PrincetonInstruments.LightField.Automation import Automation
from PrincetonInstruments.LightField.AddIns import ExperimentSettings
from PrincetonInstruments.LightField.AddIns import CameraSettings
from PrincetonInstruments.LightField.AddIns import ImageDataFormat

# Other Python libraries
import numpy as np
import serial
import ctypes
from skimage.measure import moments
import time
#/declarations

def clearSer(obj):
    obj.reset_input_buffer()
    obj.reset_output_buffer()
    
   
def convert_buffer(net_array, image_format):
    src_hndl = GCHandle.Alloc(net_array, GCHandleType.Pinned)
    try:
        src_ptr = src_hndl.AddrOfPinnedObject().ToInt64()

        # Possible data types returned from acquisition
        if (image_format==ImageDataFormat.MonochromeUnsigned16):
            buf_type = ctypes.c_ushort*len(net_array)
        elif (image_format==ImageDataFormat.MonochromeUnsigned32):
            buf_type = ctypes.c_uint*len(net_array)
        elif (image_format==ImageDataFormat.MonochromeFloating32):
            buf_type = ctypes.c_float*len(net_array)
                    
        cbuf = buf_type.from_address(src_ptr)
        resultArray = np.frombuffer(cbuf, dtype=cbuf._type_)

    # Free the handle 
    finally:        
        if src_hndl.IsAllocated: src_hndl.Free()        
    # Make a copy of the buffer
    return np.copy(resultArray)

def ManipulateImageData(dat, buff):
    im = convert_buffer(dat,buff.Format)
    im = np.reshape(im,(height,width))
    return im
    
def experimentDataReady(sender, event_args):
    if (experiment.IsReadyToRun):
        global i
        frames = event_args.ImageDataSet.Frames
        i+=frames   #in case an event returns multiple frames
        buffer = event_args.ImageDataSet.GetFrame(0, frames-1) #1st ROI and most recent frame in the event
        image_data = buffer.GetData()
        data_array = ManipulateImageData(image_data,buffer)
        M = moments(data_array)
        centroid = (M[1, 0] / M[0, 0], M[0, 1] / M[0, 0])
        print('Centroids for frame {0:d}: {1:6.2f}, {2:6.2f}'.format(i,(centroid[0]),centroid[1]))
        event_args.ImageDataSet.Dispose()

def experiment_completed(sender, event_args):
    print("...Acquisition Complete!")        
    acquireCompleted.Set()
    experiment.ImageDataSetReceived -= experimentDataReady
    
def InitializeFilenameParams():
    experiment.SetValue(ExperimentSettings.FileNameGenerationAttachIncrement,True)
    experiment.SetValue(ExperimentSettings.FileNameGenerationIncrementNumber,Int32(1))
    experiment.SetValue(ExperimentSettings.FileNameGenerationIncrementMinimumDigits,Int32(2))
    experiment.SetValue(ExperimentSettings.FileNameGenerationAttachDate,False)
    experiment.SetValue(ExperimentSettings.FileNameGenerationAttachTime,True)
    
def WaitForSerial(specObj):
    flagStop = 0
    commStr = ''
    commStr = specObj.read(1).decode()
    while flagStop == 0:
        commStr += specObj.read(1).decode()
        if 'ok' in commStr:
            flagStop = 1
    clearSer(specObj)
    
   
def AcquireMoveAndLock(name,specObj):
    experiment.ImageDataSetReceived += experimentDataReady
    print("Acquiring...")
    name += 'Exp{0:06.2f}ms.528nmTo546nm'.format(\
                        experiment.GetValue(CameraSettings.ShutterTimingExposureTime))
                        
    experiment.SetValue(ExperimentSettings.FileNameGenerationBaseFileName,name)    
    experiment.Acquire()
    specObj.write('546 goto'.encode()+b'\x0d')
    WaitForSerial(specObj)
    time.sleep(2)
    specObj.write('570 goto'.encode()+b'\x0d')
    WaitForSerial(specObj)            
    acquireCompleted.WaitOne()

auto = Automation(True, List[String]())
experiment = auto.LightFieldApplication.Experiment
acquireCompleted = AutoResetEvent(False)

experiment.Load("TPIPyDemo2")
experiment.ExperimentCompleted += experiment_completed
InitializeFilenameParams()
i=0

ser=serial.Serial('COM13',baudrate=9600,parity=serial.PARITY_NONE,bytesize=serial.EIGHTBITS,stopbits=serial.STOPBITS_ONE)
ser.timeout = 10
clearSer(ser)

#set grating 2, move to position, wait for commands to finish
ser.write('0 goto'.encode()+ b'\x0d')
WaitForSerial(ser)
ser.write('1 grating'.encode()+ b'\x0d')
WaitForSerial(ser)
ser.write('522 goto'.encode()+ b'\x0d')
WaitForSerial(ser)
#after these steps, the spectrometer grating will be in position to being the demo.

experiment.SetValue(CameraSettings.ShutterTimingExposureTime, Double(100))
experiment.SetValue(ExperimentSettings.AcquisitionFramesToStore, Int64(20))
width = experiment.GetValue(CameraSettings.SensorInformationActiveAreaWidth)
height = experiment.GetValue(CameraSettings.SensorInformationActiveAreaHeight)

baseFilename = "TPI.PyDemoII."
AcquireMoveAndLock(baseFilename,ser)


auto.Dispose()
ser.close()
