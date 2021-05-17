# -*- coding: utf-8 -*-
"""
Created on Mon May 17 16:32:10 2021

@author: sabbi
"""

#opens first PI Camera detected (if any) - if no camera, opens a ProEM 512x512
#takes full frame acquisition with either 100ms exposure (CCD, CMOS)
#or 1ms gate (ICCD) with fastest possible ADC speed (for default quality)
#uses multi-port if camera supports
#user sets desired number of frames with 'numFrames' and target MiB of memory allocation with 'targetMem'
#replaced matplotlib with pyqtgraph for faster visualization
#exit pyqtgraph window to terminate app

import ctypes
import numpy as np
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtGui
import threading
import sys

numFrames = 50
targetMem = 512 #target MiB of RAM to allocate for circular 

reshI = np.ones([1024,1024])
imv = pg.image(reshI)

count = 0   #running counter for how many cumulative frames have been captured
picam = ctypes.WinDLL("C:\Program Files\Common Files\Princeton Instruments\Picam\Runtime\Picam.dll")
lk = threading.Lock()

def animUpdate():
    global imv, reshI,lk
    imv.setImage(reshI.T,autoLevels=True)
    
def picamOperation():
    global reshI,lk
    
    def analyzeDat(dat,data,frameCt,stride,rate,count):
        #this function is where the read out data is processed into numpy array
        global reshI, lk
        lk.acquire()
        x=ctypes.cast(dat.initial_readout,ctypes.POINTER(ctypes.c_uint16))
        offset = ((dat.readout_count -1) * stride)/2
        data = x[int(offset):int((colVal.value*rowVal.value + offset))]    
        count += dat.readout_count
        reshI = np.copy(np.reshape(data,[rowVal.value,colVal.value]))
        lk.release()        
        return count
    
    def calcParam(v,c,n):
        return (((c)<<24)+((v)<<16)+(n))

    class availableData(ctypes.Structure):
        _fields_=[
            ('initial_readout', ctypes.c_void_p),
            ('readout_count', ctypes.c_longlong)]

    class acqStatus(ctypes.Structure):
        _fields_=[
            ('running', ctypes.c_bool),
            ('errors', ctypes.c_int),
            ('readout_rate',ctypes.c_double)]

    class acqBuf(ctypes.Structure):
        _fields_=[
            ('memory', ctypes.c_void_p),
            ('memory_size', ctypes.c_longlong)]

    class pulse(ctypes.Structure):
        _fields_=[
            ('delay', ctypes.c_double),
            ('width', ctypes.c_double)]

    class camIDs(ctypes.Structure):
        _fields_=[
            ('model', ctypes.c_int),
            ('computer_interface', ctypes.c_int),
            ('sensor_name', ctypes.c_char * 64),
            ('serial_number', ctypes.c_char * 64)]

    class collectionConstraint(ctypes.Structure):
        _fields_=[
            ('scope', ctypes.c_int),
            ('severity', ctypes.c_int),
            ('values_array', ctypes.c_void_p),
            ('values_count', ctypes.c_int)]
        
        
    cam = ctypes.c_void_p(0)
    dev = ctypes.c_void_p(0)
    errHand = ctypes.c_ubyte(0)
    rowVal = ctypes.c_int(10)
    colVal = ctypes.c_int(0)
    paramArray = ctypes.pointer(ctypes.c_int(0))
    failedcount = ctypes.c_int(1)
    errHand = ctypes.c_int(0)
    expTime = ctypes.c_double(0)
    expEntry = ctypes.c_double(0)
    frameCount = ctypes.c_int(0)
    readStride = ctypes.c_int(0)
    readRate = ctypes.c_double(0)
    gateWidth = ctypes.c_double(0)
    gateDelay = ctypes.c_double(0)
    adcSpeed = ctypes.c_double(0)
    display_min=1
    display_max=65535   
    
    dat=availableData(0,-1)
    aStatus=acqStatus(False,0,0)
    aBuf = acqBuf(0,0)
    gatePulse = pulse(0,0)
    camID = camIDs(0,0,b'',b'')
    adcRange = ctypes.c_void_p(0)
    qualRange = ctypes.c_void_p(0)
    
    
    err=picam.Picam_InitializeLibrary()
    if err == 5:
        err=picam.Picam_UninitializeLibrary()
        err=picam.Picam_InitializeLibrary() 
    errOpenCam=picam.Picam_OpenFirstCamera(ctypes.byref(cam))
    
    if errOpenCam > 0:
        #if no live camera connected, open a demo Pro512 
        picam.Picam_ConnectDemoCamera(1203,b'SlTestDemo',ctypes.byref(camID))
        errOpenCam = picam.Picam_OpenCamera(ctypes.byref(camID),ctypes.byref(cam));    
  
    if errOpenCam == 0:               
        #get info about camera frame size  
        errOpenCam_A = picam.PicamAdvanced_GetCameraDevice(cam,ctypes.byref(dev))
        paramStride = ctypes.c_int(calcParam(1,1,45)) #PicamParameter_ReadoutStride
        picam.Picam_GetParameterIntegerValue(cam, paramStride, ctypes.byref(readStride))
        paramRow=ctypes.c_int(calcParam(1,1,60)) #PicamParameter_SensorActiveHeight
        picam.Picam_GetParameterIntegerValue(cam,paramRow,ctypes.byref(rowVal))
        paramCol=ctypes.c_int(calcParam(1,1,59)) #PicamParameter_SensorActiveWidth
        picam.Picam_GetParameterIntegerValue(cam,paramCol,ctypes.byref(colVal))
        print('Columns: %4d, Rows: %4d.' % (colVal.value,rowVal.value))
        
        dataI = np.ones(colVal.value*rowVal.value,dtype=np.uint16)
        reshI = np.reshape(dataI,[rowVal.value,colVal.value])       
        iccdModels = list(range(300,302)) + list(range(700,721))
        picam.Picam_GetCameraID(dev,ctypes.byref(camID))
        print('Camera Sensor: %s, Camera Serial: %s'%(camID.sensor_name.decode('utf-8'),camID.serial_number.decode('utf-8')))
        if camID.model in iccdModels:
            #Gating (for ICCD)
            paramGateMode=ctypes.c_int(calcParam(4,3,93)) #PicamParameter_GatingMode
            errSet=picam.Picam_SetParameterIntegerValue(cam,paramGateMode,1) #repetitive
            if errSet!=0:
                print('Error setting gate mode, error code %d.'%(errSet))
            paramRepGate=ctypes.c_int(calcParam(7,5,94)) #
            gateWidth.value=1e6 #1ms
            gateDelay.value=26
            gatePulse.delay=gateDelay
            gatePulse.width=gateWidth
            errSet=picam.Picam_SetParameterPulseValue(cam,paramRepGate,ctypes.byref(gatePulse))
            if errSet!=0:
                print('Error setting gate parameters, error code %d.'%(errSet))
    
        else:    
            #Exposure (if not an ICCD)
            paramExp=ctypes.c_int(calcParam(2,2,23)) #PicamParameter_ExposureTime
            expEntry.value = 100 #in ms
            errSet=picam.Picam_SetParameterFloatingPointValue(cam,paramExp,expEntry)
            errGet=picam.Picam_GetParameterFloatingPointValue(cam,paramExp,ctypes.byref(expTime))
            if errSet!=0:
                print('Error setting exposure time, error code %d.'%(errSet))
        
        #Frames Count
        paramFrames=ctypes.c_int(calcParam(6,2,40))
        frameCount.value = numFrames
        errSet=picam.Picam_SetParameterLargeIntegerValue(cam,paramFrames,frameCount)
        if errSet!=0:
            print('Error setting Frames, error code %d.'%(errSet))
            
        #Multi-port (if applicable)
        paramPorts = ctypes.c_int(calcParam(1,3,28)) #PicamParameter_ReadoutPortCount
        errSet=picam.Picam_SetParameterIntegerValue(cam,paramPorts,4)
        if errSet!=0:
            if errSet==12:
                print('Multi-port not supported on this camera, running 1 port.')
            elif errSet==2:
                picam.Picam_SetParameterIntegerValue(cam,paramPorts,2)
            else:
                print('Error setting ports, error code %d.'%(errSet))
                
        #Speed and Gain
        paramADCSpeed=ctypes.c_int(calcParam(2,3,33)) #PicamParameter_AdcSpeed
        picam.Picam_GetParameterCollectionConstraint(cam,paramADCSpeed,1,ctypes.byref(adcRange))
        adcRange = ctypes.cast(adcRange,ctypes.POINTER(collectionConstraint))
        #adcSpeed.value = ctypes.cast(adcRange[0].values_array,ctypes.POINTER(ctypes.c_double))[(adcRange[0].values_count)-1] #slowest!
        adcSpeed.value = ctypes.cast(adcRange[0].values_array,ctypes.POINTER(ctypes.c_double))[0] #fastest
        errSet=picam.Picam_SetParameterFloatingPointValue(cam,paramADCSpeed,adcSpeed)
        errCom=picam.Picam_CommitParameters(cam,ctypes.byref(paramArray),ctypes.byref(failedcount))
        if errCom!=0:
            #try setting to High Speed (for Blaze cameras)
            paramADCQual=ctypes.c_int(calcParam(4,3,36)) #PicamParameter_AdcQuality
            picam.Picam_SetParameterIntegerValue(cam,paramADCQual,4)
            errSet=picam.Picam_SetParameterFloatingPointValue(cam,paramADCSpeed,adcSpeed)
            errCom=picam.Picam_CommitParameters(cam,ctypes.byref(paramArray),ctypes.byref(failedcount))
            if errCom!=0:
                #try setting to EM for 16x2 and 16x4 ProEM that default to Low Noise
                paramADCQual=ctypes.c_int(calcParam(4,3,36)) #PicamParameter_AdcQuality
                picam.Picam_SetParameterIntegerValue(cam,paramADCQual,3)
                errSet=picam.Picam_SetParameterFloatingPointValue(cam,paramADCSpeed,adcSpeed)
                errCom=picam.Picam_CommitParameters(cam,ctypes.byref(paramArray),ctypes.byref(failedcount))
                if errCom!=0:
                    #set back to lowest setting if highest doesn't work (for Kuro where bit depth needs to be changed -- I will add a bit depth change later)
                    adcSpeed.value = ctypes.cast(adcRange[0].values_array,ctypes.POINTER(ctypes.c_double))[(adcRange[0].values_count)-1] #slowest!
                    picam.Picam_SetParameterFloatingPointValue(cam,paramADCSpeed,adcSpeed)
                    print('Could not use fastest ADC Speed. Using slowest to test acquisiton.')
                
        paramADCGain=ctypes.c_int(calcParam(4,3,35)) #PicamParameter_AdcAnalogGain
        errSet=picam.Picam_SetParameterIntegerValue(cam,paramADCGain,3) #high gain
        
        #Circular Buffer Allocation        
        widthNominal = np.floor(targetMem*1024*1024/readStride.value)    #n*1024*1024 MB buff size; if not enough for 4 frames, make for 4 frames
        if widthNominal < 4:
            buffWidth = readStride.value*4
        else:
            buffWidth = int(widthNominal)*readStride.value
        circBuff = ctypes.ARRAY(ctypes.c_ubyte,buffWidth)()
        aBuf.memory=ctypes.addressof(circBuff)
        aBuf.memory_size=ctypes.c_longlong(buffWidth)
        errBuff = picam.PicamAdvanced_SetAcquisitionBuffer(dev,ctypes.byref(aBuf))
        picam.PicamAdvanced_GetAcquisitionBuffer(dev,ctypes.byref(aBuf))
        print("Acquisition Buffer Manually Set to: %d bytes (%0.2f MiB)" % (aBuf.memory_size,aBuf.memory_size/(1024*1024)))
        
        #Commit and get ready to acquire
        errCom=picam.Picam_CommitParameters(cam,ctypes.byref(paramArray),ctypes.byref(failedcount))
        if errCom==0:        
            paramReadRate=ctypes.c_int(calcParam(2,1,50)) #PicamParameter_ReadoutRateCalculation
            errGet=picam.Picam_GetParameterFloatingPointValue(cam,paramReadRate,ctypes.byref(readRate))
            
            #Acquisition
            errAcqStart=picam.Picam_StartAcquisition(cam)
            print("Acquiring, Readout Rate %6.2f fps..."%(readRate.value))   
            errAcqWait=picam.Picam_WaitForAcquisitionUpdate(cam,-1,ctypes.byref(dat),ctypes.byref(aStatus))
            if aStatus.errors!=0:
                print('\nAcquisition Error Code: %d. Stopping Acquisition.'%(aStatus.errors))
                picam.Picam_StopAcquisition(cam)
            count=dat.readout_count - 1    
            count = analyzeDat(dat,dataI,frameCount.value,readStride.value,readRate.value,count)
            while(aStatus.running or errAcqWait == 32):
                errAcqWait_inLoop=picam.Picam_WaitForAcquisitionUpdate(cam,-1,ctypes.byref(dat),ctypes.byref(aStatus))
                if aStatus.errors!=0:
                    print('\nAcquisition Error Code: %d. Stopping Acquisition.'%(aStatus.errors))
                    picam.Picam_StopAcquisition(cam)
                    break
                if count < (frameCount.value):
                    count = analyzeDat(dat,dataI,frameCount.value,readStride.value,readRate.value,count)
        else:
            print('Error when committing parameters. %d Failed Parameter(s). Not continuing to acquisition.'%(failedcount.value))
            
        errStop=picam.Picam_StopAcquisition(cam)
        print("...Acquisition Complete")
        
        picam.PicamAdvanced_CloseCameraDevice(dev)
        #picam.Picam_CloseCamera(cam) #don't need to close cam handle if dev handle is closed
    else:
        print("No camera detected. Uninitializing.")
            
    errUnInit=picam.Picam_UninitializeLibrary()
    try:
        del circBuff
    except:
        pass

if __name__ == '__main__':
    timer = pg.QtCore.QTimer()
    timer.timeout.connect(animUpdate)
    timer.start(33)     #cap display at ~30fps
    t1=threading.Thread(target=picamOperation)
    t1.start()
    if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
        QtGui.QApplication.setQuitOnLastWindowClosed(True)
        QtGui.QApplication.instance().exec_()
    t1.join()
 
