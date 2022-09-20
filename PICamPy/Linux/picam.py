#author: sabbi
#11/10/2021

import ctypes
import numpy as np
import os
import cv2
import threading
import time


os.environ["GENICAM_ROOT_V2_4"] = "/opt/pleora/ebus_sdk/x86_64/lib/genicam/"    #declaration needed for Linux SDK

lock = threading.Lock()

def calcParam(v,c,n):
    return (((c)<<24)+((v)<<16)+(n))

#check picam.h for parameter definitions -- maybe turn this into a dictionary so I don't need to use GetEnumString
paramFrames = ctypes.c_int(calcParam(6,2,40))    #PicamParameter_ReadoutCount
paramStride = ctypes.c_int(calcParam(1,1,45))    #PicamParameter_ReadoutStride
paramROIs = ctypes.c_int(calcParam(5, 4, 37))    #PicamParameter_Rois
paramReadRate=ctypes.c_int(calcParam(2,1,50))    #PicamParameter_ReadoutRateCalculation
paramExpose=ctypes.c_int(calcParam(2,2,23))        #PicamParameter_ExposureTime
paramRepetitiveGate=ctypes.c_int(calcParam(7,5,94))
paramActiveWidth=ctypes.c_int(calcParam(1,2,1))
paramActiveHeight=ctypes.c_int(calcParam(1,2,2))
paramVerticalShiftRate=ctypes.c_int(calcParam(2,3,13))
paramAdcSpeed=ctypes.c_int(calcParam(2,3,33))
paramAdcQuality=ctypes.c_int(calcParam(4,3,36))
paramSensorActiveWidth = ctypes.c_int(calcParam(1,1,59))
paramSensorActiveHeight = ctypes.c_int(calcParam(1,1,60))
paramSensorTemperatureReading = ctypes.c_int(calcParam(2,1,15))
paramSensorTemperatureSetPoint = ctypes.c_int(calcParam(2,2,14))
paramSensorTemperatureStatus = ctypes.c_int(calcParam(4,1,16))

#opencv related functions
def WindowSize(numRows,numCols):
    aspect = 1
    if numRows > 1080:
        aspect = int(numRows/1080)
    elif numCols > 1920:
        aspect = int(numCols/1920)
    winWidth = int(numCols/aspect)
    winHeight = int(numRows/aspect)
    if winWidth < 512:
        winWidth = 512
    if winHeight < 512:
        winHeight = 512
    return winWidth, winHeight

def SetupDisplay(numRows,numCols,windowName):        
    if numRows > 1:
        cv2.namedWindow(windowName,cv2.WINDOW_NORMAL)
        winWidth, winHeight = WindowSize(numRows, numCols)
        cv2.resizeWindow(windowName,winWidth,winHeight)
        cv2.moveWindow(windowName, 100,100)

def DisplayImage(imData, windowName):        #data needs to be passed in correct shape    
    normData = cv2.normalize(imData,None,alpha=0, beta=65535, norm_type=cv2.NORM_MINMAX)
    cv2.imshow(windowName, normData)
    
#this will run in its own thread
def AcquireHelper(camera):
    dat = availableData(0,0)
    aStatus=acqStatus(False,0,0)
    camera.picamLib.Picam_StartAcquisition(camera.dev)
    print('Acquisition Started, %0.2f readouts/sec...'%camera.readRate.value)
    #start a do-while
    camera.picamLib.Picam_WaitForAcquisitionUpdate(camera.dev,-1,ctypes.byref(dat),ctypes.byref(aStatus))
    camera.ProcessData(dat, camera.rStride.value)
    #while part
    while(aStatus.running):
        camera.picamLib.Picam_WaitForAcquisitionUpdate(camera.dev,-1,ctypes.byref(dat),ctypes.byref(aStatus))
        camera.runningStatus = aStatus.running
        if dat.readout_count > 0:                    
            camera.ProcessData(dat, camera.rStride.value)
        #add 50ms sleep in this thread to test if calling ProcessData fewer times leads to less jitter in display

#any key press to stop an acquisition - run as a daemon thread
#thread sits waiting for an input, if other threads finish, this exits
def Stop(camera):
    input()
    camera.picamLib.Picam_StopAcquisition(camera.dev)
    print('Key pressed during acquisition -- acquisition will stop.')

class camIDStruct(ctypes.Structure):
    _fields_=[
        ('model', ctypes.c_int),
        ('computer_interface', ctypes.c_int),
        ('sensor_name', ctypes.c_char * 64),
        ('serial_number', ctypes.c_char * 64)]

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
            ('memory_size',ctypes.c_longlong)]

class roiStruct(ctypes.Structure):
    _fields_=[
        ('x', ctypes.c_int),
        ('width', ctypes.c_int),
        ('x_binning', ctypes.c_int),
        ('y', ctypes.c_int),
        ('height', ctypes.c_int),
        ('y_binning', ctypes.c_int)]

class roisStruct(ctypes.Structure):
    _fields_=[
        ('roi_array', ctypes.c_void_p),
        ('roi_count', ctypes.c_int)]

class picamPulse(ctypes.Structure):
    _fields_=[
        ('delay', ctypes.c_double),
        ('width', ctypes.c_double)]
    
class collectionConstraint(ctypes.Structure):
    _fields_=[
        ('scope', ctypes.c_int),
        ('severity', ctypes.c_int),
        ('values_array', ctypes.c_void_p),
        ('values_count', ctypes.c_int)]

class validationResult(ctypes.Structure):
    _fields_=[
        ('is_valid', ctypes.c_bool),
        ('failed_parameter', ctypes.c_int),
        ('failed_error_constraint_scope', ctypes.c_int),
        ('failed_warning_constraint_scope', ctypes.c_int),
        ('error_constraining_parameter_array', ctypes.c_void_p),
        ('error_constraining_parameter_count', ctypes.c_int),
        ('warning_constraining_parameter_array', ctypes.c_void_p),
        ('warning_constraining_parameter_count', ctypes.c_int)]


class Camera():
    def __init__(self,*,libPath: str='/usr/local/lib/libpicam.so'):    #class will instantiate and initialize PICam
        self.cam = ctypes.c_void_p(0)
        self.dev = ctypes.c_void_p(0)
        self.camID = camIDStruct(0,0,b'',b'')
        self.numRows = ctypes.c_int(0)  #for first ROI
        self.numCols = ctypes.c_int(0)  #for first ROI
        self.readRate = ctypes.c_double(0)
        self.picamLib = ctypes.cdll.LoadLibrary(libPath)
        self.counter = 0
        self.totalData = np.array([])
        self.fullData = []  #will include ROIs
        self.newestFrame = np.array([])
        self.rStride = ctypes.c_int(0)
        self.display = False
        self.runningStatus = ctypes.c_bool(False)
        self.windowName = ''
        self.circBuff = circBuff = ctypes.ARRAY(ctypes.c_ubyte,0)()
        self.aBuf = acqBuf(0,0)
        self.roisPy=[]
        self.Initialize()

    def AcquisitionUpdated(self, device, available, status):    #PICam will launch callback in another thread
        #with lock:
        if status.contents.running:
            self.ProcessData(available.contents, self.rStride.value, saveAll = False)                    
        self.runningStatus = status.contents.running
        return 0
    
    #this ended up as a generic clearing function
    def ResetCount(self):
        self.counter = 0
        self.totalData = np.array([])

    def GetReadRate(self):
        self.picamLib.Picam_GetParameterFloatingPointValue(self.cam,paramReadRate,ctypes.byref(self.readRate))

    def Initialize(self):
        initCheck = ctypes.c_bool(0)
        self.picamLib.Picam_InitializeLibrary()
        self.picamLib.Picam_IsLibraryInitialized(ctypes.byref(initCheck))
        print('PICam Initialized: %r'%initCheck.value)
        if initCheck:
            #version check if PICam successfully initialized
            major = ctypes.c_int(0)
            minor = ctypes.c_int(0)
            distribution = ctypes.c_int(0)
            released = ctypes.c_int(0)
            self.picamLib.Picam_GetVersion(ctypes.byref(major),ctypes.byref(minor),ctypes.byref(distribution),ctypes.byref(released))
            print("\tVersion %d.%d.%d.%d"%(major.value, minor.value, distribution.value, released.value))

    def Uninitialize(self):
        self.picamLib.Picam_UninitializeLibrary()

    #calling this locks in the dimensions that will be displayed
    def GetFirstROI(self):        
        rois = ctypes.c_void_p(0)        
        self.picamLib.Picam_GetParameterRoisValue(self.cam, paramROIs, ctypes.byref(rois))
        roisCast = ctypes.cast(rois,ctypes.POINTER(roisStruct))[0]
        roiCast = ctypes.cast(roisCast.roi_array,ctypes.POINTER(roiStruct))[0]    #take first ROI
        self.numCols = int(roiCast.width/roiCast.x_binning)
        self.numRows = int(roiCast.height/roiCast.y_binning)
        self.picamLib.Picam_DestroyRois(rois)
        if self.numRows > 1:
            self.display = True       #change this back to True for opencv display
    
    #test function to generate n ROIs of full width and 10+ rows that start from the top of the camera.
    def SetROIs(self, n):
        if self.numRows >= ((n*10) + n):
            roiArray = ctypes.ARRAY(roiStruct, n)()
            lastPos = 0
            for i in range(0,n):
                roi = roiStruct(0, self.numCols, 1, lastPos, 10+i, 1)
                roiArray[i] = roi
                lastPos += 10+i
            rois = roisStruct(ctypes.addressof(roiArray[0]), n)
            #print(rois)
            self.picamLib.Picam_SetParameterRoisValue(self.cam, paramROIs, ctypes.byref(rois))
            self.GetFirstROI()   #call this to reset the numRows and numCols for display
            self.Commit()
            
    #testing Eran Reches' application of 8x3 ROIs -- print readout rates directly from function
    def SetEqualROIs(self, n):
        if self.numCols >= 2*(n*8):
            ##first set to fastest shift rate -- 2 = required constraint
            vertShift = ctypes.c_void_p(0)
            shiftSpeed = ctypes.c_double(0)
            self.picamLib.Picam_GetParameterCollectionConstraint(self.cam,paramVerticalShiftRate,2,ctypes.byref(vertShift))
            vertShift = ctypes.cast(vertShift,ctypes.POINTER(collectionConstraint))
            shiftSpeed.value = ctypes.cast(vertShift[0].values_array,ctypes.POINTER(ctypes.c_double))[0] #fastest
            print('Setting fastest shift rate...',end='')
            self.picamLib.Picam_SetParameterFloatingPointValue(self.cam,paramVerticalShiftRate,shiftSpeed)
            self.picamLib.Picam_GetParameterFloatingPointValue(self.cam,paramVerticalShiftRate,ctypes.byref(shiftSpeed))
            print('Shift speed set to %0.3f us'%(shiftSpeed.value))
            roiArray = ctypes.ARRAY(roiStruct, n)()
            lastPos = 0
            for i in range(0,n):
                roi = roiStruct(lastPos, 8, 1, 0, 3, 1)
                roiArray[i] = roi
                lastPos += 16
            rois = roisStruct(ctypes.addressof(roiArray), n)
            self.picamLib.Picam_SetParameterRoisValue(self.cam, paramROIs, ctypes.byref(rois))
            self.GetFirstROI()   #call this to reset the numRows and numCols for display
            self.Commit()

    #sets square (nxn) ROI in the center of the active sensor, assuming given dimension meets constraints
    def SetCenterROI(self, dim: np.int32):
        #get sensor active rows and cols
        defRows = ctypes.c_int(0)
        defCols = ctypes.c_int(0)
        self.picamLib.Picam_GetParameterIntegerValue(self.cam, paramSensorActiveWidth, ctypes.byref(defCols))
        self.picamLib.Picam_GetParameterIntegerValue(self.cam, paramSensorActiveHeight, ctypes.byref(defRows))
        #print(defRows.value, defCols.value)
        if dim <= defRows.value and dim <=defCols.value and dim >0:
            newDim = ctypes.c_int(dim)
            newX = ctypes.c_int(np.int32(np.floor(defCols.value/2 - dim/2)))
            newY = ctypes.c_int(np.int32(np.floor(defRows.value/2 - dim/2)))
            roiArray = ctypes.ARRAY(roiStruct, 1)()
            roiArray[0] = roiStruct(newX.value, dim, 1, newY.value, dim, 1)
            rois = roisStruct(ctypes.addressof(roiArray), 1)
            self.picamLib.Picam_SetParameterRoisValue(self.cam, paramROIs, ctypes.byref(rois))
            #now validate the ROI that was just set
            valObj = ctypes.c_void_p(0)
            self.picamLib.PicamAdvanced_ValidateParameter(self.cam, paramROIs, ctypes.byref(valObj))
            valObj = ctypes.cast(valObj,ctypes.POINTER(validationResult))
            #print(valObj[0].is_valid)
            if valObj[0].is_valid:
                print('Successfully changed ROI to ',end='')
            else:
                #get the default ROI
                roisDef = ctypes.c_void_p(0)
                self.picamLib.Picam_GetParameterRoisDefaultValue(self.cam, paramROIs, ctypes.byref(roisDef))
                self.picamLib.Picam_SetParameterRoisValue(self.cam, paramROIs, roisDef)
                self.picamLib.Picam_DestroyRois(roisDef)
                print('Could not change ROI. ROI has defaulted back to ')
            self.GetFirstROI()
            print('%d (cols) x %d (rows)'%(self.numCols, self.numRows))
            self.picamLib.Picam_DestroyValidationResult(valObj)
            #print(newX.value, newY.value)
            return
        #this is the exit if something fails along the way
        print('Could not attempt to set center ROI due to parameter and/or dimension mismatch.')
        return

    #find the fastest ADC speed the camera can handle and re-commit any necessary parameters based on constraints
    #assume that AdcQuality is the only thing that needs to be checked for match w/ capable and required.
    def SetFastestADCSpeed(self):
        speedConstObj = ctypes.c_void_p(0)
        speedReqObj = ctypes.c_void_p(0)
        adcSpeed = ctypes.c_double(0)
        adcSpeedReq = ctypes.c_double(0)
        self.picamLib.Picam_GetParameterCollectionConstraint(self.cam,paramAdcSpeed,1,ctypes.byref(speedConstObj))  #1: capable
        self.picamLib.Picam_GetParameterCollectionConstraint(self.cam,paramAdcSpeed,2,ctypes.byref(speedReqObj))  #2: required
        speedConstObj = ctypes.cast(speedConstObj,ctypes.POINTER(collectionConstraint))
        adcSpeed.value = ctypes.cast(speedConstObj[0].values_array,ctypes.POINTER(ctypes.c_double))[0] #fastest
        speedReqObj = ctypes.cast(speedReqObj,ctypes.POINTER(collectionConstraint))
        #print(speedReqObj[0].values_count)
        print('Setting to fastest ADC Speed...', end='')
        self.picamLib.Picam_SetParameterFloatingPointValue(self.cam,paramAdcSpeed,adcSpeed)
        self.picamLib.Picam_GetParameterFloatingPointValue(self.cam,paramAdcSpeed,ctypes.byref(adcSpeed))
        print(' ADC Speed set to %0.3f MHz'%(adcSpeed.value))
        match = False
        #check to see if the capable value matches any from required. If not, need to find required ADC Quality
        for i in range(0,speedReqObj[0].values_count):
            adcSpeedReq.value = ctypes.cast(speedReqObj[0].values_array,ctypes.POINTER(ctypes.c_double))[i]
            if adcSpeedReq.value == adcSpeed.value:
                match = True
                break
        if match == False:
            print('\tADC Quality needs to change.')
            qualCapObj = ctypes.c_void_p(0)
            errCt = ctypes.c_int(0)
            qual = ctypes.c_double(0)
            self.picamLib.Picam_GetParameterCollectionConstraint(self.cam,paramAdcQuality,1,ctypes.byref(qualCapObj))
            qualCapObj = ctypes.cast(qualCapObj,ctypes.POINTER(collectionConstraint))
            #loop through capable qualities until finding the one that can be validated
            matchQual = False
            for i in range(0,qualCapObj[0].values_count):
                qual.value = ctypes.cast(qualCapObj[0].values_array,ctypes.POINTER(ctypes.c_double))[i]
                self.picamLib.Picam_SetParameterIntegerValue(self.cam,paramAdcQuality,ctypes.c_int(np.int32(qual.value)))
                valObj = ctypes.c_void_p(0)
                self.picamLib.PicamAdvanced_ValidateParameter(self.cam, paramAdcSpeed, ctypes.byref(valObj))
                valObj = ctypes.cast(valObj,ctypes.POINTER(validationResult))
                if valObj[0].is_valid:
                    matchQual = True
                    enumStr = ctypes.c_char_p()
                    qualInt = ctypes.c_int(0)
                    self.picamLib.Picam_DestroyValidationResult(valObj)
                    self.picamLib.Picam_GetParameterIntegerValue(self.cam,paramAdcQuality,ctypes.byref(qualInt))
                    self.picamLib.Picam_GetEnumerationString(8, qualInt, ctypes.byref(enumStr)) #8: PicamEnumeratedType_AdcQuality
                    print('\tADC Quality changed to %s.'%(enumStr.value))
                    self.picamLib.Picam_DestroyString(enumStr)
                    break
                self.picamLib.Picam_DestroyValidationResult(valObj)
            if matchQual == False:
                print('\tCould not find correct parameter changes. Will commit fastest speed for current quality.')
            self.picamLib.Picam_DestroyCollectionConstraints(qualCapObj)
        self.CommitAndChange()
        self.picamLib.Picam_DestroyCollectionConstraints(speedConstObj)
        self.picamLib.Picam_DestroyCollectionConstraints(speedReqObj)
            
    def SetCustomSensor(self,height:np.int32,width:np.int32):
        print('Now setting custom sensor to %d Active Columns and %d Active Rows'%(width,height))
        self.picamLib.Picam_SetParameterIntegerValue(self.cam,paramActiveWidth,width)
        self.picamLib.Picam_SetParameterIntegerValue(self.cam,paramActiveHeight,height)
        self.CommitAndChange()

    def Commit(self,*,printMessage: bool=True):
        #paramArray = ctypes.pointer(ctypes.c_int(0))
        paramArray = ctypes.c_void_p(0)
        failedCount = ctypes.c_int(1)
        self.picamLib.Picam_CommitParameters(self.cam, ctypes.byref(paramArray), ctypes.byref(failedCount))
        if failedCount.value > 0:
            print('Failed to commit %d parameters. Cannot acquire.'%(failedCount.value))
            self.picamLib.Picam_DestroyParameters(paramArray)
            return False
        else:
            self.GetReadRate()
            if printMessage:
                print('\tCommit successful! Current readout rate: %0.2f readouts/sec'%(self.readRate.value))
            self.picamLib.Picam_DestroyParameters(paramArray)
            return True
    
    #attempts to change parameters that fail to commit based on constraints
    #example is when ADC speed changes and the current bit depth no longer applies
    #this implementation will only check for int, large int, and floating param times, and will assume collection constraint
    def CommitAndChange(self):
        paramArray = ctypes.c_void_p(0)
        failedCount = ctypes.c_int(1)
        self.picamLib.Picam_CommitParameters(self.cam, ctypes.byref(paramArray), ctypes.byref(failedCount))
        paramArray = ctypes.cast(paramArray,ctypes.POINTER(ctypes.c_int))
        #print(failedCount.value)
        if failedCount.value > 0:
            print('Changing the following parameters to allow a successful commit:')
        for i in range(0,failedCount.value):
            #print('\tFailed Param: %d'%(paramArray[i]))
            paramV = ctypes.c_int(0)
            enumStr = ctypes.c_char_p()
            self.picamLib.Picam_GetEnumerationString(6, paramArray[i], ctypes.byref(enumStr))   #6 = PicamEnumeratedType_Parameter
            self.picamLib.Picam_GetParameterValueType(self.cam,paramArray[i],ctypes.byref(paramV))
            #print(paramV.value)
            collConstObj = ctypes.c_void_p(0)
            paramValue = ctypes.c_double(0)
            self.picamLib.Picam_GetParameterCollectionConstraint(self.cam,paramArray[i],2,ctypes.byref(collConstObj))
            collConstObj = ctypes.cast(collConstObj,ctypes.POINTER(collectionConstraint))
            paramValue.value = ctypes.cast(collConstObj[0].values_array,ctypes.POINTER(ctypes.c_double))[0]   
            match paramV.value:
                case 1:
                    self.picamLib.Picam_SetParameterIntegerValue(self.cam,paramArray[i],ctypes.c_int(np.int32(paramValue.value)))
                case 2:
                    self.picamLib.Picam_SetParameterFloatingPointValue(self.cam,paramArray[i],paramValue)
                case 3:
                    self.picamLib.Picam_SetParameterIntegerValue(self.cam,paramArray[i],ctypes.c_int(np.int32(paramValue.value)))
                case 4:
                    self.picamLib.Picam_SetParameterIntegerValue(self.cam,paramArray[i],ctypes.c_int(np.int32(paramValue.value)))
                case 5:
                    self.picamLib.Picam_SetParameterLargeIntegerValue(self.cam,paramArray[i],ctypes.c_int(np.int64(paramValue.value)))                
            print('\t%s changed to %d'%(enumStr.value, paramValue.value))
            self.picamLib.Picam_DestroyCollectionConstraints(collConstObj)
            self.picamLib.Picam_DestroyString(enumStr)
        self.picamLib.Picam_DestroyParameters(paramArray)
        self.Commit(printMessage=False)


    def OpenFirstCamera(self,*,model: int=57): #if a connected camera is found, opens the first one, otherwise opens a demo        
        if self.picamLib.Picam_OpenFirstCamera(ctypes.byref(self.cam)) > 0: #try opening live cam
            self.picamLib.Picam_ConnectDemoCamera(model,b'SLTest',ctypes.byref(self.camID))
            if self.picamLib.Picam_OpenCamera(ctypes.byref(self.camID),ctypes.byref(self.cam)) > 0:
                print('No camera could be opened. Uninitializing.')
                self.Uninitialize()
            else:
                self.picamLib.Picam_GetCameraID(self.cam,ctypes.byref(self.camID))
        else:
            self.picamLib.Picam_GetCameraID(self.cam,ctypes.byref(self.camID))
        print('Camera Sensor: %s, Serial #: %s'%(self.camID.sensor_name.decode('utf-8'),self.camID.serial_number.decode('utf-8')))
        self.GetFirstROI()
        print('\tFirst ROI: %d (cols) x %d (rows)'%(self.numCols,self.numRows))
        self.windowName = 'Readout from %s'%(self.camID.sensor_name.decode('utf-8'))

    #for ICCD, treat input exposure as gate width (with default delay)
    def SetExposure(self, time):
        exist = ctypes.c_bool(False)
        expTime = ctypes.c_double(0)
        expTime.value = time
        self.picamLib.Picam_DoesParameterExist(self.cam, paramExpose, ctypes.byref(exist))
        if exist:
            self.picamLib.Picam_SetParameterFloatingPointValue(self.cam,paramExpose,expTime)
            print('Trying to commit exposure time to %0.2f ms... '%(expTime.value),end='')
            self.Commit(printMessage=False)
            self.picamLib.Picam_GetParameterFloatingPointValue(self.cam,paramExpose,ctypes.byref(expTime))
            print('Exposure committed to %0.2f ms.'%(expTime.value))
            return
        #if exposure time doesn't exist, see if gate exists
        self.picamLib.Picam_DoesParameterExist(self.cam, paramRepetitiveGate, ctypes.byref(exist))
        if exist:
            #use og pulse to get the delay and to keep track of the original setting
            ogPulse = ctypes.c_void_p(0)
            self.picamLib.Picam_GetParameterPulseValue(self.cam, paramRepetitiveGate, ctypes.byref(ogPulse))
            ogPulse = ctypes.cast(ogPulse,ctypes.POINTER(picamPulse))
            ogWidth = ogPulse[0].width
            ogDelay = ogPulse[0].delay
            #print('OG Pulse: %0.3f ns width, %0.3f ns delay'%(ogWidth, ogDelay))
            newPulse = picamPulse(ogDelay, time*1e6)
            self.picamLib.Picam_SetParameterPulseValue(self.cam, paramRepetitiveGate, ctypes.byref(newPulse))
            print('Trying to commit gate width to %0.2f ns... '%(time*1e6),end='')

            #validate the set parameter            
            valObj = ctypes.c_void_p(0)
            self.picamLib.PicamAdvanced_ValidateParameter(self.cam, paramRepetitiveGate, ctypes.byref(valObj))
            valObj = ctypes.cast(valObj,ctypes.POINTER(validationResult))
            #print(valObj[0].is_valid)
            if not valObj[0].is_valid:
                #if we can't validate, set the original pulse
                self.picamLib.Picam_SetParameterPulseValue(self.cam, paramRepetitiveGate, ogPulse)

            #now commit and check the pulse that was set to report to console
            self.Commit(printMessage=False)
            setPulse = ctypes.c_void_p(0)
            self.picamLib.Picam_GetParameterPulseValue(self.cam, paramRepetitiveGate, ctypes.byref(setPulse))
            setPulse = ctypes.cast(setPulse,ctypes.POINTER(picamPulse))
            setWidth = setPulse[0].width
            setDelay = setPulse[0].delay
            print('Committed Pulse: %0.3f ns width, %0.3f ns delay'%(setWidth, setDelay))            
            self.picamLib.Picam_DestroyPulses(ogPulse)
            self.picamLib.Picam_DestroyPulses(setPulse)
            self.picamLib.Picam_DestroyValidationResult(valObj)

    #this only works for 16-bit data, need to modify divisor to 4 for >16-bit. I will update to a more generic version at a later time.
    def ProcessData(self, data, readStride,*,saveAll: bool=True):
        with lock:
            #start = time.perf_counter_ns()
            #print(data.readout_count)
            #copy entire RO buffer to np array
            x=ctypes.cast(data.initial_readout,ctypes.POINTER(ctypes.c_uint16))#size of full readout
            xAlloc = ctypes.c_uint16*np.int32(readStride/2)*data.readout_count
            addr = ctypes.addressof(x.contents)
            numpyRO = np.copy(np.frombuffer(xAlloc.from_address(addr),dtype=np.uint16)) 
            #print('Buffer copy time: %0.2f ms'%((time.perf_counter_ns() - start)/1e6))           
            if data.readout_count > 0:                
                #this part processes only the final frame for display
                roiCols = np.shape(self.fullData[0])[2]
                roiRows = np.shape(self.fullData[0])[1]
                offsetA = np.int32((data.readout_count-1) * (readStride / 2)) + 0
                #print(offsetA)     
                readoutDat = numpyRO[offsetA:np.int32(roiCols*roiRows)+offsetA]            
                self.newestFrame = np.reshape(readoutDat, (roiRows, roiCols))
            #print('Total preview time %0.2f ms'%((time.perf_counter_ns() - start)/1e6))

        if saveAll and data.readout_count > 0:
            #this part goes readout by readout
            #get ROIs for more generic processing when there are multiple ROIs -- assumes no metada -> will need additional offset code for that                
            roiOffset = 0
            for k in range(0, len(self.fullData)):            
                roiCols = np.shape(self.fullData[k])[2]
                roiRows = np.shape(self.fullData[k])[1]
                #print(roiCols, roiRows)         
                readCounter = 0
                for i in range(0,data.readout_count):    #readout by readout
                    #start = time.perf_counter_ns()
                    offsetA = np.int32((i * readStride) / 2) + roiOffset
                    readoutDat = numpyRO[offsetA:np.int32(roiCols*roiRows)+offsetA]    
                    self.fullData[k][readCounter + self.counter,:,:] = np.reshape(readoutDat, (roiRows, roiCols))
                    #self.counter += 1
                    """ if i == data.readout_count-1 and k == 0:    #return most recent readout (normalized) to use for displaying, always ROI 1
                        self.newestFrame = readoutDat """
                    readCounter += 1
                    #print('Loop time: %0.2f ms'%((time.perf_counter_ns() - start)/1e6))
                roiOffset = roiOffset + np.int32(roiCols*roiRows)
        self.counter += data.readout_count
        #print('Total process time: %0.2f ms'%((time.perf_counter_ns() - start)/1e6))
    
    #helper to configure final data buffer before acquire -- this can be used to loop through ROIs later
    def SetupFullData(self, frames):
        rois = ctypes.c_void_p(0)        
        self.picamLib.Picam_GetParameterRoisValue(self.cam, paramROIs, ctypes.byref(rois))
        roisCast = ctypes.cast(rois,ctypes.POINTER(roisStruct))[0]
        self.fullData=[0]*roisCast.roi_count
        for i in range(0,roisCast.roi_count):
            roiCast = ctypes.cast(roisCast.roi_array,ctypes.POINTER(roiStruct))[i]
            roiCols = np.int32((roiCast.width / roiCast.x_binning))
            roiRows = np.int32((roiCast.height / roiCast.y_binning))                
            self.fullData[i] = np.zeros([frames, roiRows, roiCols])
            print('ROI %d shape: '%(i+1), np.shape(self.fullData[i]))
        self.picamLib.Picam_DestroyRois(rois)
    
    def ReadTemperatureStatus(self):
        tempStatus = {1: 'Unlocked', 2: 'Locked', 3: 'Faulted'}
        sensorTemp = ctypes.c_double(0)
        sensorLockStatus = ctypes.c_int(0)
        sensorSetPt = ctypes.c_double(0)
        self.picamLib.Picam_ReadParameterFloatingPointValue(self.cam, paramSensorTemperatureReading, ctypes.byref(sensorTemp))
        self.picamLib.Picam_GetParameterFloatingPointValue(self.cam, paramSensorTemperatureSetPoint, ctypes.byref(sensorSetPt))
        self.picamLib.Picam_ReadParameterIntegerValue(self.cam, paramSensorTemperatureStatus, ctypes.byref(sensorLockStatus))
        print('*****\nSensor Temperature %0.2fC (%s). Set Point %0.2fC.\n*****'%(sensorTemp.value, tempStatus[sensorLockStatus.value], sensorSetPt.value))

    #-s mode
    def Acquire(self,*,frames: int=1):    #will launch the AcquireHelper function in a new thread when user calls it
        frameCount = ctypes.c_int(0)
        frameCount.value = frames
        self.picamLib.Picam_SetParameterLargeIntegerValue(self.cam,paramFrames,frameCount)
        #0 is for infinite preview, don't allow for -s mode
        if self.Commit() and frameCount.value > 0:
            self.ResetCount()
            #set up total data objects
            #self.totalData = np.zeros((frameCount.value,self.numRows,self.numCols))
            self.SetupFullData(frames)
            if self.display:
                SetupDisplay(self.numRows, self.numCols, self.windowName)
            self.picamLib.Picam_GetParameterIntegerValue(self.cam, paramStride, ctypes.byref(self.rStride))

            #adding ring buffering so that large number of frames can still be collected if saving
            #same as in AcquireCB()
            self.picamLib.PicamAdvanced_GetCameraDevice(self.cam, ctypes.byref(self.dev))
            widthNominal = np.floor(512*1024*1024/self.rStride.value)
            if widthNominal < 100:                    #if 512MB not enough for 100 frames, allocate for 100 frames
                buffWidth = self.rStride.value*100
            else:
                buffWidth = np.int32(512*1024*1024)
            self.circBuff = ctypes.ARRAY(ctypes.c_ubyte,buffWidth)()
            self.aBuf.memory = ctypes.addressof(self.circBuff)
            self.aBuf.memory_size = ctypes.c_longlong(buffWidth)
            self.picamLib.PicamAdvanced_SetAcquisitionBuffer(self.dev, ctypes.byref(self.aBuf))

            #read camera temp right before acquisition
            self.ReadTemperatureStatus()

            acqThread = threading.Thread(target=AcquireHelper, args=(self,))
            acqThread.start()    #data processing will be in a different thread than the display

    #display will only show first ROI
    def DisplayCameraData(self):    #this will block and then unregister callback (if applicable) when done
        #do-while
        cv2.waitKey(100)
        runStatus = ctypes.c_bool(False)
        self.picamLib.Picam_IsAcquisitionRunning(self.cam, ctypes.byref(runStatus))
        self.runningStatus = runStatus
        while self.runningStatus:
            if self.display and len(self.newestFrame) > 0:                                  
                DisplayImage(self.newestFrame, self.windowName)
            cv2.waitKey(33)
        print('Acquisition stopped. %d readouts obtained.'%(self.counter))
        try:
            self.picamLib.PicamAdvanced_UnregisterForAcquisitionUpdated(self.dev, self.acqCallback)
        except:
            pass
        cv2.waitKey(10000)
        cv2.destroyAllWindows()

    #since we're not saving data here, this is not generalized for multi-ROI -- the first ROI will be displayed
    #-p mode
    def AcquireCB(self,*,frames: int=5):    #utilizes Advanced API to demonstrate callbacks, returns immediately
        self.picamLib.PicamAdvanced_GetCameraDevice(self.cam, ctypes.byref(self.dev))
        frameCount = ctypes.c_int(0)
        frameCount.value = frames
        self.picamLib.Picam_SetParameterLargeIntegerValue(self.dev,paramFrames,frameCount)    #setting with dev handle commits to physical device if successful
        if self.Commit() and frameCount.value >= 0:
            if self.display:
                SetupDisplay(self.numRows, self.numCols, self.windowName)
            self.ResetCount()
            self.picamLib.Picam_GetParameterIntegerValue(self.cam, paramStride, ctypes.byref(self.rStride))
            #even though FullData will not be used, need to set shape for ROI parsing in ProcessData
            self.SetupFullData(1)
                    
            #circ buffer so we can run for a long time without needing to allocate memory for all of it
            #the buffer array and the data structure should be global or class properties so they remain in scope when the
            #function returns        
            widthNominal = np.floor(512*1024*1024/self.rStride.value)
            if widthNominal < 100:                    #if 512MB not enough for 100 frames, allocate for 100 frames
                buffWidth = self.rStride.value*100
            else:
                buffWidth = np.int32(512*1024*1024)
            self.circBuff = ctypes.ARRAY(ctypes.c_ubyte,buffWidth)()
            self.aBuf.memory = ctypes.addressof(self.circBuff)
            self.aBuf.memory_size = ctypes.c_longlong(buffWidth)
            self.picamLib.PicamAdvanced_SetAcquisitionBuffer(self.dev, ctypes.byref(self.aBuf))
            
            CMPFUNC = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_void_p, ctypes.POINTER(availableData), ctypes.POINTER(acqStatus))
            #lines for internal callback        
            self.acqCallback = CMPFUNC(self.AcquisitionUpdated)
            self.picamLib.PicamAdvanced_RegisterForAcquisitionUpdated(self.dev, self.acqCallback)

            #read temperature before starting acqusition
            self.ReadTemperatureStatus()
            self.picamLib.Picam_StartAcquisition(self.dev)        
            print('Acquisition of %d frames asynchronously started'%(frameCount.value))
            stopThread = threading.Thread(target=Stop, daemon=True, args=(self,))
            stopThread.start()

    #niche function for user-specific test
    def TimeBetweenAcqs(self, iters:np.int32=3):
        #declare some needed variables and structs
        start=0
        dat = availableData(0,0)
        aStatus=acqStatus(False,0,0)
        #set to acquire large number of frames so that acquisition doesn't stop before Stop called.
        self.picamLib.Picam_SetParameterLargeIntegerValue(self.cam,paramFrames,50)
        self.Commit()
        runStatus = ctypes.c_int(0)
        for i in range(0,iters):
            self.picamLib.Picam_StartAcquisition(self.cam)
            if i>0:
                print('Time between stop and start: %0.2f ms'%((time.perf_counter_ns() - start)/1e6))
            time.sleep(3)
            self.picamLib.Picam_StopAcquisition(self.cam)
            #start timer once Stop has been called
            start = time.perf_counter_ns()            
            self.picamLib.Picam_WaitForAcquisitionUpdate(self.cam,-1,ctypes.byref(dat),ctypes.byref(aStatus))
            #next iteration will start once acquisition has stopped -- if needed, the aStatus from Wait 
            #can be used to verify that it has actually stopped.


    def ReturnData(self):
        return self.fullData

    def Close(self):
        self.ResetCount()
        self.picamLib.Picam_CloseCamera(self.cam)
        self.picamLib.Picam_DisconnectDemoCamera(ctypes.byref(self.camID))
        self.Uninitialize()
