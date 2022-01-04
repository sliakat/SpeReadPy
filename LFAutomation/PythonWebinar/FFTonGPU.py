# -*- coding: utf-8 -*-
"""
Created on Tue Dec 28 11:21:46 2021

@author: sliakat
"""

#tested with CUDA 10.1

#Python / .NET imports
import clr
import sys
import os
import numpy as np
from System import String
from System.Collections.Generic import List
from System.Runtime.InteropServices import GCHandle, GCHandleType
import ctypes
import time
import threading
from matplotlib import pyplot as plt
from matplotlib.animation import FuncAnimation
import scipy.fft         #for cpu processing comparison

#gpu processing imports
import cupy as cp
import cupyx.scipy.fft as cufft
from cupy.fft.config import get_plan_cache
from cupyx.scipy.fftpack import get_fft_plan

# Add needed dll references
sys.path.append(os.environ['LIGHTFIELD_ROOT'])
sys.path.append(os.environ['LIGHTFIELD_ROOT']+"\\AddInViews")
clr.AddReference('PrincetonInstruments.LightFieldViewV5')
clr.AddReference('PrincetonInstruments.LightField.AutomationV5')
clr.AddReference('PrincetonInstruments.LightFieldAddInSupportServices')

# PI imports
from PrincetonInstruments.LightField.Automation import Automation
from PrincetonInstruments.LightField.AddIns import RegionOfInterest

lock = threading.Lock()     #lock for event callback

#gpu related functions
def clearFFTCache():
    cache = get_plan_cache()
    cache.clear()

def freeGPU():
    mem = cp.get_default_memory_pool()
    mem.free_all_blocks()
    
def gpuInit():  #bring a dummy 8k x 8k array of float into GPU memory
    with cp.cuda.Device(0):
        cp.cuda.set_allocator(cp.cuda.MemoryPool(cp.cuda.malloc_managed).malloc)        
        x_gpu = cp.ones((8192,8192))
        del x_gpu
        freeGPU()

#fft on cpu
def cpuFFT(data):    
    start = time.perf_counter_ns()
    cpu_fft = scipy.fft.fftshift(np.abs(scipy.fft.fft2(data)))  #do the fft on the cpu
    img.SetImage(cpu_fft)
    end = (time.perf_counter_ns()-start)/1e6
    print('CPU FFT completed in %0.3f ms'%(end))

#fft on gpu
def gpuFFT(data):
    start = time.perf_counter_ns()
    with cp.cuda.Device(0):
        x_gpu = cp.asarray(data)    #host --> device
        with scipy.fft.set_backend(cufft):
            plan = get_fft_plan(x_gpu)
            x_fft = cufft.fftshift(cp.abs(cufft.fft2(x_gpu,plan=plan)))  #do the fft on the gpu
        img.SetImage(cp.asnumpy(x_fft)) #asnumpy transfers back to host
        del x_gpu
        freeGPU()        
        #clearFFTCache()             
    end = (time.perf_counter_ns()-start)/1e6
    del x_fft
    print('GPU FFT completed in %0.3f ms'%(end))

def experimentDataReady(sender, event_args):
    global gpuProcess
    if event_args is not None:
        with lock:
            if event_args.ImageDataSet is not None:
                if (LF.ReadyCheck()):
                    frames = event_args.ImageDataSet.Frames
                    counter.increase(frames)   #in case an event returns multiple frames
                    recentFrame = LF.DataToNumpy(event_args.ImageDataSet, frames)[-1,:,:]   #[frame,row,col]
                    if gpuProcess:
                        gpuFFT(recentFrame)
                    else:
                        cpuFFT(recentFrame)
                    event_args.ImageDataSet.Dispose()
                    
def initView():
    ax = disp.Axis()
    ax.clear()
    im = img.ReturnImage()
    ax.imshow(im,origin='upper',cmap='gray')
    return [ax]
                    
def animate(i):     #matplotlib animate function
    ax = disp.Axis()
    ax.clear()
    im = img.ReturnImage()
    display_min = int(np.percentile(im.flatten(),5))
    display_max = int(np.percentile(im.flatten(),95))
    ax.imshow(im,origin='upper',vmin=display_min,vmax=display_max,cmap='gray')
    ax.set_xlabel('u axis')
    ax.set_ylabel('v axis')
    return [ax]
    
#for later matplotlib display if desired            
def ShowImage(img):
    fig = plt.figure('Single FFT')
    ax = fig.add_subplot(111)
    #image contrast adjustments - can modify later to use gpu as well
    display_min = int(np.percentile(img.flatten(),5))
    display_max = int(np.percentile(img.flatten(),95))
    ax.imshow(img,origin='upper',vmin=display_min,vmax=display_max,cmap='gray')
    ax.set(xlabel='Column')
    ax.set(ylabel='Row')
            
class Counter:
    def __init__(self):
        self.value = 0
        self.countLock = threading.Lock()
    def increase(self, val):
        with self.countLock:
            self.value += val
    def reset(self):
        with self.countLock:
            self.value = 0
    def retVal(self):
        return self.value
    
class LatestImage:      #container for most recent image data in the callback
    def __init__(self):
        self.img = np.array([])
        self.imageLock = threading.Lock()
    def SetImage(self,im):
        with self.imageLock:
            self.img = im
    def ReturnImage(self):
        return self.img

class DisplayContainer:
    def __init__(self,*,name: str='Image'):
        self.winName = name
        self.InitFig()        
    def InitFig(self):
        self.fig = plt.figure(self.winName)
        self.ax = self.fig.add_subplot(111)
    def Axis(self):
        return self.ax
    def Fig(self):
        return self.fig
    def Name(self):
        return self.winName

class AutoClass:        #object for LF automation
    def __init__(self):
        self.auto = []
        self.experiment = []
        self.dataFormat = {1:ctypes.c_ushort, 2:ctypes.c_uint, 3:ctypes.c_float}
        self.byteDiv = {1:2, 2:4, 3:4}
        self.rows = 0
        self.cols = 0
        
    def DataToNumpy(self, imageDataSet, numFrames):
        #find cols and rows from returned data using length of the perpecdicular slice
        numRows = imageDataSet.GetColumn(0,0,0).GetData().Length
        numCols = imageDataSet.GetRow(0,0,0).GetData().Length
        dataFmt = imageDataSet.GetFrame(0,0).Format        
        dataBuf = imageDataSet.GetDataBuffer()   #.NET Array (System.Byte[])
        src_hndl = GCHandle.Alloc(dataBuf, GCHandleType.Pinned)
        try:
            src_ptr = src_hndl.AddrOfPinnedObject().ToInt64()
            #generate array space that is the correct size
            buf_type = self.dataFormat[dataFmt]*int(len(dataBuf)/self.byteDiv[dataFmt])
            cbuf = buf_type.from_address(src_ptr)        
            resultArray = np.frombuffer(cbuf, dtype=cbuf._type_)        
        finally:        
            if src_hndl.IsAllocated: src_hndl.Free() 
        return np.reshape(resultArray, (numFrames,numRows,numCols))
    
    def GetCurrentROI(self):
        region = self.experiment.SelectedRegions
        self.rows = int(region[0].Height / region[0].YBinning)
        self.cols = int(region[0].Width / region[0].XBinning)
        return self.rows, self.cols
    
    def NewInstance(self,*,expName: str=''):      #loads an experiment and, if applicable, hooks event
        self.auto = Automation(True, List[String]())
        self.experiment = self.auto.LightFieldApplication.Experiment
        self.fileManager = self.auto.LightFieldApplication.FileManager
        if len(expName) > 0:
            self.experiment.Load(expName)
            if self.ReadyCheck():
                self.experiment.ImageDataSetReceived += experimentDataReady
                print('ImageDataSetReceived event hooked!')
            else:
                print('Cound not hook event!')
            
    def ReadyCheck(self):
        return self.experiment.IsReadyToRun
    
    def Stop(self):
        self.experiment.Stop()
    
    def CloseInstance(self):
        self.experiment.ImageDataSetReceived -= experimentDataReady
        print('Unhooked event, closing automation instance.')
        try:
            freeGPU()
            clearFFTCache()
            pass
        except:
            pass
        self.auto.Dispose()
        
if __name__=="__main__":
    gpuProcess = False
    img = LatestImage()
    if gpuProcess:
        gpuStarter = threading.Thread(target=gpuInit)
        gpuStarter.start()  #let this thread run while LightField initialization occurs in the following lines
    LF = AutoClass()
    counter = Counter()
    LF.NewInstance(expName='Kuro2048Demo')
    rows, cols = LF.GetCurrentROI()
    img.SetImage(np.ones((rows,cols)))
    disp = DisplayContainer(name='FFT Animation')
    
    try:
        gpuStarter.join()   #wait for GPU init to complete if it hasn't done so by this point
    except:
        pass
    a = FuncAnimation(disp.Fig(), animate, frames=100, repeat=False, interval=100, init_func=initView, blit=True)
    plt.show()
    
    ##press run in LF instance at some point now to kick off the processing / display##
    
    # ShowImage(img.ReturnImage())        #call this from console to see the latest transformed image
    # LF.CloseInstance()        #run this when finished to unhook event and dispose AddInProcess
