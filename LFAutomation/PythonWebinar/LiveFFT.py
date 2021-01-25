# -*- coding: utf-8 -*-
"""
Created on Thu Oct  1 23:01:26 2020

@author: sabbi
"""

#will set up a demo ProHS in LF set to run continuously at ~1kHz.
#event will be hooked
#Upon live acquisition, live fft will update as data comes in, if there
#are enough samples (this example only does a single pixel)

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

# Import c compatible List and String
from System import String
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

import numpy as np
import ctypes
from matplotlib import pyplot as plt
import matplotlib.animation as anim
import scipy.fftpack

def convert_buffer(net_array, image_format):
    typeDic = {ImageDataFormat.MonochromeUnsigned16:ctypes.c_ushort*len(net_array),
               ImageDataFormat.MonochromeUnsigned32:ctypes.c_uint*len(net_array),
               ImageDataFormat.MonochromeFloating32:ctypes.c_float*len(net_array)}
    src_hndl = GCHandle.Alloc(net_array, GCHandleType.Pinned)
    try:
        src_ptr = src_hndl.AddrOfPinnedObject().ToInt64()
        buf_type = typeDic[image_format]                 
        cbuf = buf_type.from_address(src_ptr)
        resultArray = np.frombuffer(cbuf, dtype=cbuf._type_)

    # Free the handle 
    finally:        
        if src_hndl.IsAllocated: src_hndl.Free()        
    # Make a copy of the buffer
    return np.copy(resultArray)

def ManipulateImageData(dat, buff, w, h):
    im = convert_buffer(dat,buff.Format)
    im = np.reshape(im,(h,w),order='C')
    return im[np.int(np.floor(h/2)),np.int(np.floor(w/2))] #picking one pixel to analyze in the ROI, use center pixel

def unhookEvent():
    global i, intensityArray, x, y
    experiment.ImageDataSetReceived -= experimentDataReady
    intensityArray = np.empty(0)
    i=0
    x=np.empty(0)
    y=np.empty(0)
    
def animate(i):
    global line, ax
    ax.clear()
    ax.plot(x, y)
    #print('Animation iteration %d, x length %d'%(i,np.int(np.size(x))))

def performFFT(intensity):
    global x,y
    N = len(intensity)
    T = T=1.0/N
    yf = scipy.fftpack.fft(intensity)
    xf = np.linspace(0.0, 1.0/(2.0*T), np.int(N/2))
    yfft = 2.0/N * np.abs(yf[:N//2])
    print('FFT Computed. Position of highest frequency component: {0:d}'.format(np.argmax(yfft[1:N//2])+1))
    x = np.copy(xf)
    y = np.copy(yfft)
    
def onClick(event):
    global animRunning
    if animRunning:
        a.event_source.stop()
        animRunning = False
    else:
        a.event_source.start()
        animRunning = True


def experimentDataReady(sender, event_args):
    if (experiment.IsReadyToRun):
        global i, intensityArray, fig, ax, line, x, y
        frames = event_args.ImageDataSet.Frames
        regions = event_args.ImageDataSet.Regions        
        i+=frames   #in case an event returns multiple frames                 
        for k in range(0,frames):            
            buffer = event_args.ImageDataSet.GetFrame(0, k) #1st ROI and most recent frame in the event
            image_data = buffer.GetData()
            intensityArray = np.append(intensityArray,ManipulateImageData(image_data,buffer,regions[0].Width,regions[0].Height))
            if np.mod(len(intensityArray),128)==0:
                print('Frames so far: %d'%(i))
                performFFT(intensityArray)

plt.ion()
plt.close(fig='all')
auto = Automation(True, List[String]())
experiment = auto.LightFieldApplication.Experiment
experiment.Load("ProDemo")

i=0
intensityArray = np.empty(0)

fig = plt.figure()
ax = fig.add_subplot(111)
x=np.empty(0)
y=np.empty(0)
ax.plot(x,y, '-')
a = anim.FuncAnimation(fig, animate, frames=10000, repeat=False, interval=100)
animRunning = True
fig.canvas.mpl_connect('button_press_event', onClick)
plt.show()

experiment.ImageDataSetReceived += experimentDataReady

#unhookEvent()
#a.event_source.stop()