# -*- coding: utf-8 -*-
"""
Created on Thu Nov  4 09:44:09 2021

@author: sliakat
"""

##work in progress

import clr
import sys
import os
import numpy as np
from System import String
from System.Collections.Generic import List
from System.Runtime.InteropServices import GCHandle, GCHandleType
from System.Threading import AutoResetEvent
import ctypes
import time
clr.AddReference('System.Windows.Forms')
import gc

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
from PrincetonInstruments.LightField.AddIns import Pulse 

class AutoClass:
    #static class properties go here
    dataFormat = {1:ctypes.c_ushort, 2:ctypes.c_uint, 3:ctypes.c_float}
    byteDiv = {1:2, 2:4, 3:4}
    
    def __init__(self):
        #per-instance properties
        #none of these are being updated outside the class, so did not implement getter/setter
        self.auto = None
        self.experiment = None
        self.fileManager = None
        self.acquiredFiles = list()
        self.acquireCompleted = AutoResetEvent(False)
        self.counter = 0
        self.ROIs = np.array([],dtype=np.uint32)
        self.numROIs = 0
    
    def ResetCounter(self):
        self.counter = 0
        
    def acquire_complete(self, sender, event_args):
        self.acquireCompleted.Set()
        
    def NewInstance(self,*,expName: str=''):      #design is to contain LFA class objects within the wrapper class, not give outside access
        self.auto = Automation(True, List[String]())
        self.experiment = self.auto.LightFieldApplication.Experiment
        self.fileManager = self.auto.LightFieldApplication.FileManager
        if len(expName) > 0:
            self.experiment.Load(expName)
        self.experiment.ExperimentCompleted += self.acquire_complete
        
    def GetCurrentROIs(self):
        self.ROIs = np.array([],dtype=np.uint32)
        region = self.experiment.SelectedRegions
        self.numROIs = region.Length
        for i in range(0,region.Length):
            self.ROIs = np.append(self.ROIs,[int(region[i].Height / region[i].YBinning), int(region[i].Width / region[i].XBinning)])  #rows, cols
        return self.ROIs
    
    def DataToNumpy(self, imageDataSet):        
        self.GetCurrentROIs()
        outData = list()    #output data will be in a list of numpy arrays -- each list element for a region
        dataFmt = imageDataSet.GetFrame(0,0).Format  
        frames = imageDataSet.Frames
        #get stride of each region
        regions = np.zeros(self.numROIs,dtype=np.uint32)
        for i in range(0,self.numROIs):
            regions[i] = self.ROIs[i*2] * self.ROIs[i*2+1]
        #start = time.perf_counter()
        dataBuf = imageDataSet.GetDataBuffer()   #.NET vector (System.Byte[])
        #print('GetDataBuffer function took: %0.3f s'%(time.perf_counter()-start))        
        #convert entre .NET vector to numpy
        src_hndl = GCHandle.Alloc(dataBuf, GCHandleType.Pinned)
        try:
            src_ptr = src_hndl.AddrOfPinnedObject().ToInt64()
            #generate array space that is the correct size
            buf_type = self.dataFormat[dataFmt]*int(len(dataBuf)/self.byteDiv[dataFmt])
            cbuf = buf_type.from_address(src_ptr)        
            resultArray = np.frombuffer(cbuf, dtype=cbuf._type_)        
        finally:        
            if src_hndl.IsAllocated: src_hndl.Free() 
        
        #append by region
        resultArray = np.reshape(resultArray,(frames,sum(regions)))
        for j in range(0,self.numROIs):
            if j == 0:
                outData.append(np.reshape(resultArray[:,0:sum(regions[0:1])],(frames,self.ROIs[j*2],self.ROIs[j*2+1])))
            else:
                outData.append(np.reshape(resultArray[:,sum(regions[0:j]):sum(regions[0:j+1])],(frames,self.ROIs[j*2],self.ROIs[j*2+1])))          
        #explicit cleanup before return
        imageDataSet.Dispose()
        del(dataBuf)
        del(resultArray)        
        return outData
        
    def CreateSpeFile(self, name, rows, cols, numFrames, imgFormat):   #name should include full path, incl dir
        roi = [RegionOfInterest(0,0,cols,rows,1,1)]
        return self.fileManager.CreateFile(name,roi,numFrames,imgFormat)

    def SpeCharacteristics(self, name):
        imgSetTemp = self.fileManager.OpenFile(name, 1)  #read: 1, write: 2, readwrite: 3
        imageRows = imgSetTemp.GetColumn(0,0,0).GetData().Length
        imageCols = imgSetTemp.GetRow(0,0,0).GetData().Length
        imageFormat = imgSetTemp.GetFrame(0,0).Format
        self.fileManager.CloseFile(imgSetTemp)
        return imageRows, imageCols, imageFormat        
            
    def Capture(self,*,numFrames: int=1,reset: bool=False):   #for debugging automation errors
        if self.experiment.IsReadyToRun:
            if reset:
                self.ResetCounter()
            self.counter +=1
            dataSet = self.experiment.Capture(numFrames)
            if dataSet is None:
                print('Capture returned NULL dataset.')
                return False
            else:
                return self.DataToNumpy(dataSet)
                #return dataSet
        else:
            return np.arr([])  

    def ReportCounter(self):
        return self.counter        
            
    def CloseInstance(self):
        try:
            self.experiment.ExperimentCompleted -= self.acquire_complete
        except:
            pass
        self.auto.Dispose()
        
class AutoClassNiche(AutoClass):    #these are for niche functions or used for debugging
    def __init__(self):
        super().__init__()
    
    #niche capture for debugging, overrides superclass
    def Capture(self,*,numFrames: int=1,startTime: float=0):   #for debugging automation errors
        if self.experiment.IsReadyToRun:
            self.counter +=1
            dataSet = self.experiment.Capture(numFrames)
            if dataSet is None:
                print('Capture returned NULL dataset.')
                return False
            else:
                dataArr = self.DataToNumpy(dataSet)
                if self.counter%100 == 0:
                    print('%d Captures parsed, Total time elapsed: %0.3f hrs'%(self.counter,(time.perf_counter()-startTime)/(60*60)))
                try:
                    dataSet.Dispose()
                except:
                    pass              #may have been disposed in DataToNumpy                
                del(dataArr)
                #gc.collect()
                return True              
        else:
            return True
        
    def FilenameGen(self, width, delay):
        self.experiment.SetValue(ExperimentSettings.FileNameGenerationBaseFileName, 'CustomSequence.GW%0.3fns.Delay%0.3fus'%(width,(delay/1000)))
        self.experiment.SetValue(ExperimentSettings.FileNameGenerationAttachDate, True)
        self.experiment.SetValue(ExperimentSettings.FileNameGenerationAttachTime, True)
        
    #this is a niche function, ignore for typical use
    def RunSequence(self,*,numSteps: int=2, startDelay: float=1, endDelay: float=100):   #delays in us
        self.ResetCounter()
        self.experiment.SetValue(ExperimentSettings.AcquisitionFramesToStore, 1)
        self.experiment.SetValue(CameraSettings.AcquisitionGateTrackingEnabled, True)        
        delaySteps = np.linspace(startDelay*1000, endDelay*1000, numSteps)  #LFA Pulse accepts ns, so convert
        gateWidth = self.experiment.GetValue(CameraSettings.GatingRepetitiveGate).Width
        #print('Gate Width: %0.3f ns'%(gateWidth))
        #print(delaySteps)
        for step in delaySteps:
            self.experiment.SetValue(CameraSettings.GatingRepetitiveGate, Pulse(gateWidth, step))
            self.FilenameGen(gateWidth, step)
            self.experiment.Acquire()
            self.acquireCompleted.WaitOne()
            self.acquiredFiles.append(str(self.fileManager.GetRecentlyAcquiredFileNames()[0]))
        #print(self.acquiredFiles)
        
        #prep the new spe file
        saveDir = self.acquiredFiles[0].rsplit('\\',maxsplit=1)[0]
        newFileName = saveDir + '\\' + 'CustomSequenceFrames.' + time.strftime("%Y-%d-%m at %H.%M.%S", time.localtime()) + '.spe'
        imageRows, imageCols, imageFormat = self.SpeCharacteristics(self.acquiredFiles[0])
        combinedData = self.CreateSpeFile(newFileName,imageRows,imageCols,len(self.acquiredFiles),imageFormat)
        #print(imageRows, imageCols)
                  
        #2 loops by design -- first acquire the data, then put it together afterwards
        for name in self.acquiredFiles:
            imgSetTemp = self.fileManager.OpenFile(name, 1)     ##this line was wrong before, changed to name which should be correct
            combinedData.GetFrame(0,self.counter).SetData(imgSetTemp.GetFrame(0,0).GetData())
            self.fileManager.CloseFile(imgSetTemp)
            super(AutoClassNiche,self).counter += 1        
        self.fileManager.CloseFile(combinedData)
        