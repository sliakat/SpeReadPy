#author: sabbi
#11/10/2021

import ctypes
import numpy as np
import os
import cv2
import threading
import queue
import time


os.environ["GENICAM_ROOT_V2_4"] = "/opt/pleora/ebus_sdk/x86_64/lib/genicam/"    #declaration needed for Linux SDK

lock = threading.Lock()
q = queue.Queue()

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
paramAdcBitDepth=ctypes.c_int(calcParam(1,3,34))
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

def DisplayImage(imData, windowName, bits):        #data needs to be passed in correct shape
    vmax = pow(2,16)-1
    if bits >16:
        #needed because opencv can't display uint32
        #vmax = pow(2,bits)-1
        divFactor = pow(2,bits-16)
        imData = (imData/divFactor).astype(np.uint16)
    normData = cv2.normalize(imData,None,alpha=0, beta=vmax, norm_type=cv2.NORM_MINMAX)    
    cv2.imshow(windowName, normData)
    
#this will run in its own thread
def AcquireHelper(camera):
    dat = availableData(0,0)
    aStatus=acqStatus(False,0,0)
    camera.picamLib.Picam_StartAcquisition(camera.dev)
    camera.acqTimer = time.perf_counter_ns()
    print('Acquisition Started, %0.2f readouts/sec...'%camera.readRate.value)
    #start a do-while
    camera.picamLib.Picam_WaitForAcquisitionUpdate(camera.dev,-1,ctypes.byref(dat),ctypes.byref(aStatus))
    if camera.bits <=16:
        camera.ProcessData(dat, camera.rStride.value)
    elif camera.bits > 16 and camera.bits <=32:
        camera.ProcessData32(dat, camera.rStride.value)
    #while part
    while(aStatus.running):
        camera.picamLib.Picam_WaitForAcquisitionUpdate(camera.dev,-1,ctypes.byref(dat),ctypes.byref(aStatus))
        camera.runningStatus = aStatus.running
        if dat.readout_count > 0:
            if camera.bits <=16:                    
                camera.ProcessData(dat, camera.rStride.value)
            elif camera.bits > 16 and camera.bits <32:
                camera.ProcessData32(dat, camera.rStride.value)
        #add 50ms sleep in this thread to test if calling ProcessData fewer times leads to less jitter in display

#any key press to stop an acquisition - run as a daemon thread
#thread sits waiting for an input, if other threads finish, this exits
def Stop(camera):
    input()
    camera.picamLib.Picam_StopAcquisition(camera.dev)
    print('Key pressed during acquisition -- acquisition will stop.')
    print('Mean of most recently processed frame: %0.3f cts'%(np.mean(camera.newestFrame)))

#daemon for writing data - idea is to speed up process as much as possible, and writing can lag at the end, if needed.
def Write(camera):
    time.sleep(.001)
    while True:
        queueItem = q.get()
        roiNum = queueItem[0]
        frame = queueItem[1]
        roiRows = queueItem[2]
        roiCols = queueItem[3]
        readoutDat = queueItem[4]
        if camera.saveDisk:
            camera.fileHandle.write(readoutDat.tobytes())
        else:            
            #to my surprise, doing this is actually faster on large data than using np.put w/ linear index
            camera.fullData[roiNum][frame] = np.reshape(readoutDat, (roiRows, roiCols))
        q.task_done()


class camIDStruct(ctypes.Structure):
    _fields_=[
        ('model', ctypes.c_int),
        ('computer_interface', ctypes.c_int),
        ('sensor_name', ctypes.c_char * 64),
        ('serial_number', ctypes.c_char * 64)]

class firmwareDetail(ctypes.Structure):
    _fields_=[
        ('name', ctypes.c_char * 64),
        ('detail', ctypes.c_char * 256)]

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
        self.bits = 0   #bit depth of the camera referenced by self.cam
        self.display = False
        self.runningStatus = ctypes.c_bool(False)
        self.windowName = ''
        self.circBuff = ctypes.ARRAY(ctypes.c_ubyte,0)()
        self.aBuf = acqBuf(0,0)
        self.roisPy=[]
        self.saveDisk = False
        self.eventTimer = 0
        self.acqTimer = 0
        self.Initialize()

    def AcquisitionUpdated(self, device, available, status):    #PICam will launch callback in another thread
        #with lock:
        if status.contents.running:
            if self.counter > 0:
                eventTime = (time.perf_counter_ns() - self.eventTimer) /1e6
                if status.contents.readout_rate > 0:
                    expectedTime = (1/status.contents.readout_rate) * 1e3
                #print('Event latency: %0.3f ms'%(np.abs(eventTime-expectedTime)))
            self.eventTimer = time.perf_counter_ns()
            if self.bits <=16:
                self.ProcessData(available.contents, self.rStride.value, saveData = False)
            elif self.bits > 16 and self.bits <=32:
                self.ProcessData32(available.contents, self.rStride.value, saveData = False)
        self.runningStatus = status.contents.running
        return 0
    
    #this ended up as a generic clearing function
    def ResetCount(self):
        self.counter = 0
        self.totalData = np.array([])
        self.acqTimer = 0

    def GetReadRate(self):
        self.picamLib.Picam_GetParameterFloatingPointValue(self.cam,paramReadRate,ctypes.byref(self.readRate))

    def EnumString(self, type:int, value:int):
        enumStr = ctypes.c_char_p()
        self.picamLib.Picam_GetEnumerationString(type, value, ctypes.byref(enumStr))
        outStr = enumStr.value.decode('utf-8')
        self.picamLib.Picam_DestroyString(enumStr)
        return outStr

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
    def SetFastestADCSpeed(self):
        #need to check for existence b/c COSMOS does not have AdcSpeed param
        exist = ctypes.c_bool(False)
        self.picamLib.Picam_DoesParameterExist(self.cam, paramAdcSpeed, ctypes.byref(exist))
        if exist.value:
            speedConstObj = ctypes.c_void_p(0)
            adcSpeed = ctypes.c_double(0)
            self.picamLib.Picam_GetParameterCollectionConstraint(self.cam,paramAdcSpeed,1,ctypes.byref(speedConstObj))  #1: capable
            speedConstObj = ctypes.cast(speedConstObj,ctypes.POINTER(collectionConstraint))
            adcSpeed.value = ctypes.cast(speedConstObj[0].values_array,ctypes.POINTER(ctypes.c_double))[0] #fastest
            print('Setting to fastest ADC Speed...')
            self.picamLib.Picam_DestroyCollectionConstraints(speedConstObj)
            self.SetADCSpeed(adcSpeed.value)            

    #sets ADC speed per the user input. Looks for match of input to capable values to within 15kHz.
    #traverses through ADC Quality to find the right match, if speed does not match required constraint.
    def SetADCSpeed(self,speed:np.float64):
        exist = ctypes.c_bool(False)
        self.picamLib.Picam_DoesParameterExist(self.cam, paramAdcSpeed, ctypes.byref(exist))
        if exist.value:
            speedMatch = False
            speedCapObj = ctypes.c_void_p(0)            
            adcSpeedChosen = ctypes.c_double(0)   
            adcSpeedLoop = ctypes.c_double(0)         
            self.picamLib.Picam_GetParameterCollectionConstraint(self.cam,paramAdcSpeed,1,ctypes.byref(speedCapObj))  #1: capable
            speedCapObj = ctypes.cast(speedCapObj,ctypes.POINTER(collectionConstraint))
            print('Valid ADC Speeds for this camera (in MHz):\n\t',end='')
            #loop through the capable speed values to see if any match with the input (to within 15kHz)
            for i in range(0,speedCapObj[0].values_count):                
                adcSpeedLoop.value = ctypes.cast(speedCapObj[0].values_array,ctypes.POINTER(ctypes.c_double))[i]
                print('%0.3f'%(adcSpeedLoop.value), end='')
                #formatting stuff
                if i >= 0 and i < speedCapObj[0].values_count - 1:
                    print(', ', end='')
                diff = np.abs(adcSpeedLoop.value-speed)
                #print(diff)
                if diff <=0.015:
                    speedMatch = True
                    adcSpeedChosen.value = adcSpeedLoop.value
                    #print('Chosen ADC Speed: %0.3f MHz'%(adcSpeedChosen.value))                    
            print('\n')                
            #if we get a match, set the speed, then check if quality change is needed to commit          
            if speedMatch == True:
                #set the ADC speed
                adcSpeedSet = ctypes.c_double(0)
                print('Attempting to set ADC Speed to %0.3f MHz... '%(adcSpeedChosen.value),end='')
                self.picamLib.Picam_SetParameterFloatingPointValue(self.cam,paramAdcSpeed,adcSpeedChosen)
                self.picamLib.Picam_GetParameterFloatingPointValue(self.cam,paramAdcSpeed,ctypes.byref(adcSpeedSet))
                print('ADC Speed set to %0.3f MHz'%(adcSpeedSet.value))

                #now check for necessary quality changes (if quality exists)
                reqMatch = False
                speedReqObj = ctypes.c_void_p(0)
                self.picamLib.Picam_GetParameterCollectionConstraint(self.cam,paramAdcSpeed,2,ctypes.byref(speedReqObj))  #2: required
                speedReqObj = ctypes.cast(speedReqObj,ctypes.POINTER(collectionConstraint))
                adcSpeedReq = ctypes.c_double(0)
                for i in range(0,speedReqObj[0].values_count):
                    adcSpeedReq.value = ctypes.cast(speedReqObj[0].values_array,ctypes.POINTER(ctypes.c_double))[i]
                    if adcSpeedReq.value == adcSpeedChosen.value:
                        reqMatch = True
                        break
                if not reqMatch:
                    self.picamLib.Picam_DoesParameterExist(self.cam, paramAdcQuality, ctypes.byref(exist))
                    if exist.value:
                        print('\tADC Quality needs to change.')
                        qualMatch = False
                        qualCapObj = ctypes.c_void_p(0)
                        errCt = ctypes.c_int(0)
                        qual = ctypes.c_double(0)
                        self.picamLib.Picam_GetParameterCollectionConstraint(self.cam,paramAdcQuality,1,ctypes.byref(qualCapObj))
                        qualCapObj = ctypes.cast(qualCapObj,ctypes.POINTER(collectionConstraint))
                        for i in range(0,qualCapObj[0].values_count):
                            qual.value = ctypes.cast(qualCapObj[0].values_array,ctypes.POINTER(ctypes.c_double))[i]
                            self.picamLib.Picam_SetParameterIntegerValue(self.cam,paramAdcQuality,ctypes.c_int(np.int32(qual.value)))
                            valObj = ctypes.c_void_p(0)
                            #need to validate on speed becuase quality is hierarchically superior and will always pass
                            self.picamLib.PicamAdvanced_ValidateParameter(self.cam, paramAdcSpeed, ctypes.byref(valObj))
                            valObj = ctypes.cast(valObj,ctypes.POINTER(validationResult))
                            if valObj[0].is_valid:
                                qualMatch = True
                                enumStr = ctypes.c_char_p()
                                qualInt = ctypes.c_int(0)
                                self.picamLib.Picam_DestroyValidationResult(valObj)
                                self.picamLib.Picam_GetParameterIntegerValue(self.cam,paramAdcQuality,ctypes.byref(qualInt))
                                self.picamLib.Picam_GetEnumerationString(8, qualInt, ctypes.byref(enumStr)) #8: PicamEnumeratedType_AdcQuality
                                print('\tADC Quality changed to %s.'%(enumStr.value.decode('utf-8')))
                                self.picamLib.Picam_DestroyString(enumStr)
                                break
                            self.picamLib.Picam_DestroyValidationResult(valObj)
                        if not qualMatch:
                            print('\tCould not find correct parameter changes. Will commit fastest speed for current constraints.')
                        self.picamLib.Picam_DestroyCollectionConstraints(qualCapObj)
                self.picamLib.Picam_DestroyCollectionConstraints(speedReqObj)
                self.CommitAndChange()
            else:
                print('Camera does not contain an ADC Speed that matches the input.')
            self.picamLib.Picam_DestroyCollectionConstraints(speedCapObj)
        else:
            print('ADC Speed parameter does not exist for this camera.')

    #sets custom sensor only -- need to handle ROI manually -- no validation added yet        
    def SetCustomSensor(self,height:np.int32,width:np.int32):
        print('Now setting custom sensor to %d Active Columns and %d Active Rows'%(width,height))
        self.picamLib.Picam_SetParameterIntegerValue(self.cam,paramActiveWidth,width)
        self.picamLib.Picam_SetParameterIntegerValue(self.cam,paramActiveHeight,height)
        self.CommitAndChange()

    #sets 
    def SetCustomSensorAndROI(self, height: np.int32, width: np.int32):
        setHeight = ctypes.c_int(0)
        setWidth = ctypes.c_int(0)
        #try to set to desired width / height
        print('Attempting to change custom sensor to %d (cols) x %d (rows)... '%(width, height), end='')
        self.picamLib.Picam_SetParameterIntegerValue(self.cam,paramActiveWidth,width)
        self.picamLib.Picam_SetParameterIntegerValue(self.cam,paramActiveHeight,height)
        #now check what GetParameter returns
        self.picamLib.Picam_GetParameterIntegerValue(self.cam,paramActiveWidth,ctypes.byref(setWidth))
        self.picamLib.Picam_GetParameterIntegerValue(self.cam,paramActiveHeight,ctypes.byref(setHeight))
        print('Set to %d (cols) x %d (rows)'%(setWidth.value, setHeight.value))        
        #setROI if the desired and actual match
        if height==setHeight.value and width==setWidth.value:
            roiArray = ctypes.ARRAY(roiStruct, 1)()
            roiArray[0] = roiStruct(0, setWidth.value, 1, 0, setHeight.value, 1)
            rois = roisStruct(ctypes.addressof(roiArray), 1)
            self.picamLib.Picam_SetParameterRoisValue(self.cam, paramROIs, ctypes.byref(rois))
            self.GetFirstROI()  #for display
        self.CommitAndChange()


    def Commit(self,*,printMessage: bool=True):
        #paramArray = ctypes.pointer(ctypes.c_int(0))
        paramArray = ctypes.c_void_p(0)
        failedCount = ctypes.c_int(1)
        self.picamLib.Picam_CommitParameters(self.cam, ctypes.byref(paramArray), ctypes.byref(failedCount))

        #update cam object's bit depth value on each commit
        bitsInt = ctypes.c_int(0)
        self.picamLib.Picam_GetParameterIntegerValue(self.cam, paramAdcBitDepth, ctypes.byref(bitsInt))
        self.bits = bitsInt.value
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
            print('\t%s changed to %d'%(enumStr.value.decode('utf-8'), paramValue.value))
            self.picamLib.Picam_DestroyCollectionConstraints(collConstObj)
            self.picamLib.Picam_DestroyString(enumStr)
        self.picamLib.Picam_DestroyParameters(paramArray)
        self.Commit(printMessage=False)

    #use after self.camID has been populated with a valid camera id (i.e. through OpenCamera())
    def PrintCameraFirmware(self):
        fwArray = ctypes.c_void_p(0)
        fwCount = ctypes.c_int(0)
        self.picamLib.Picam_GetFirmwareDetails(ctypes.byref(self.camID), ctypes.byref(fwArray), ctypes.byref(fwCount))
        if fwCount.value > 0:
            fwArray = ctypes.cast(fwArray,ctypes.POINTER(firmwareDetail))
            print('%%%%%\nCamera Firmware:')
            for i in range(0,fwCount.value):
                print('%s\t%s'%(fwArray[i].name.decode('utf-8').ljust(24), fwArray[i].detail.decode('utf-8')))
            print('%%%%%')
        self.picamLib.Picam_DestroyFirmwareDetails(fwArray)


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

    #lists available cameras, then asks user for input
    #option to open demo camera with 0
    def OpenCamera(self):
        idArray = ctypes.c_void_p(0)
        idCount = ctypes.c_int(0)
        returnVal = False
        self.picamLib.Picam_GetAvailableCameraIDs(ctypes.byref(idArray), ctypes.byref(idCount))
        idArray = ctypes.cast(idArray,ctypes.POINTER(camIDStruct))
        print('*****\n%d Teledyne SciCam camera(s) detected:'%(idCount.value))
        for i in range(0,idCount.value):
            currID = idArray[i]
            print('[%d]: %s, Serial #: %s'%((i+1),currID.sensor_name.decode('utf-8'),currID.serial_number.decode('utf-8')))
        selectionStr = input('*****\nEnter the integer for the camera you want to open, or 0 for demo:\n')
        try:
            selection = np.int32(selectionStr)
        except ValueError:
            print('Valid integer could not be parsed.')
            selection = -1
        finally:
            if selection <= -1 or selection > idCount.value:
                print('Cannot open camera - invalid input.')
                returnVal = False
            elif selection >0 and selection <= idCount.value:
                openErr = self.picamLib.Picam_OpenCamera(ctypes.byref(idArray[selection-1]),ctypes.byref(self.cam))
                if openErr == 0:
                    #make sure the destination struct is initialized first
                    ctypes.memmove(ctypes.addressof(self.camID), ctypes.addressof(idArray[selection-1]), ctypes.sizeof(idArray[selection-1]))
                    returnVal = True
                else:
                    errStr = self.EnumString(1, openErr)
                    print('Cannot open camera: %s'%(errStr))
                    returnVal = False
            elif selection == 0:
                selectionStr = input('Enter the camera model ID for desired demo (e.g. 1206 for ProEM-HS 1024):\n')
                try:
                    selectionDemo = np.int32(selectionStr)
                except ValueError:
                    print('Valid integer could not be parsed. Not opening any camera.')
                    selectionDemo = -1
                    returnVal = False
                if selectionDemo > 0:
                    self.picamLib.Picam_ConnectDemoCamera(ctypes.c_int(selectionDemo),b'SLTest',ctypes.byref(self.camID))
                    openErr = self.picamLib.Picam_OpenCamera(ctypes.byref(self.camID),ctypes.byref(self.cam))
                    if openErr == 0:
                        returnVal = True
                    else:
                        errStr = self.EnumString(1, openErr)
                        print('Cannot open camera: %s'%(errStr))
                        returnVal = False
            else:
                print('Unknown Error.')
                returnVal = False
        self.picamLib.Picam_DestroyCameraIDs(idArray)
        #print(self.camID)
        if returnVal:
            print('*****\nCamera Sensor: %s, Serial #: %s'%(self.camID.sensor_name.decode('utf-8'),self.camID.serial_number.decode('utf-8')))
            self.PrintCameraFirmware()
            self.GetFirstROI()
            print('Default ROI: %d (cols) x %d (rows)'%(self.numCols,self.numRows))
            self.windowName = 'Readout from %s'%(self.camID.sensor_name.decode('utf-8'))
        return returnVal        

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

    #function to process 16-bit data
    def ProcessData(self, data, readStride,*,saveData: bool=True):
        with lock:
            start = time.perf_counter_ns()
            #copy entire RO buffer to np array
            x=ctypes.cast(data.initial_readout,ctypes.POINTER(ctypes.c_uint16))#size of full readout
            xAlloc = ctypes.c_uint16*np.int64(readStride/2)*data.readout_count
            addr = ctypes.addressof(x.contents)
            numpyRO = np.copy(np.frombuffer(xAlloc.from_address(addr),dtype=np.uint16)) 
            #print('Buffer copy time: %0.2f ms'%((time.perf_counter_ns() - start)/1e6))           
            if data.readout_count > 0:                
                #this part processes only the final frame for display
                roiCols = np.shape(self.fullData[0])[2]
                roiRows = np.shape(self.fullData[0])[1]
                offsetA = np.int64((data.readout_count-1) * (readStride / 2)) + 0     
                readoutDat = numpyRO[offsetA:np.int64(roiCols*roiRows)+offsetA]            
                self.newestFrame = np.reshape(readoutDat, (roiRows, roiCols))
            #print('Total preview time %0.2f ms'%((time.perf_counter_ns() - start)/1e6))

        if saveData and data.readout_count > 0:
            #this part goes readout by readout
            #get ROIs for more generic processing when there are multiple ROIs -- assumes no metada -> will need additional offset code for that                
            roiOffset = 0
            for k in range(0, len(self.fullData)):            
                roiCols = np.shape(self.fullData[k])[2]
                roiRows = np.shape(self.fullData[k])[1]         
                readCounter = 0
                for i in range(0,data.readout_count):    #readout by readout
                    #start = time.perf_counter_ns()
                    offsetA = np.int64((i * readStride) / 2) + roiOffset
                    readoutDat = numpyRO[offsetA:np.int64(roiCols*roiRows)+offsetA]
                    #the Write() worker daemon will fill in the fullData array from the queue
                    #the processing function is free to continue

                    q.put([k, readCounter + self.counter, roiRows, roiCols, readoutDat])
                    #startA = time.perf_counter_ns()
                    readCounter += 1
                    #print('Loop time: %0.2f ms'%((time.perf_counter_ns() - start)/1e6))
                roiOffset = roiOffset + np.int64(roiCols*roiRows)
        self.counter += data.readout_count
        #print('Total process time: %0.2f ms'%((time.perf_counter_ns() - start)/1e6))

    #function to process 32-bit data (>16 bits: <=32 bits)
    def ProcessData32(self, data, readStride,*,saveData: bool=True):
        with lock:
            start = time.perf_counter_ns()
            #print(data.readout_count)
            #copy entire RO buffer to np array
            x=ctypes.cast(data.initial_readout,ctypes.POINTER(ctypes.c_uint32))#size of full readout
            xAlloc = ctypes.c_uint32*np.int64(readStride/4)*data.readout_count
            addr = ctypes.addressof(x.contents)
            numpyRO = np.copy(np.frombuffer(xAlloc.from_address(addr),dtype=np.uint32)) 
            #print('Buffer copy time: %0.2f ms'%((time.perf_counter_ns() - start)/1e6))           
            if data.readout_count > 0:                
                #this part processes only the final frame for display
                roiCols = np.shape(self.fullData[0])[2]
                roiRows = np.shape(self.fullData[0])[1]
                offsetA = np.int64((data.readout_count-1) * (readStride / 4)) + 0     
                readoutDat = numpyRO[offsetA:np.int32(roiCols*roiRows)+offsetA]            
                self.newestFrame = np.reshape(readoutDat, (roiRows, roiCols))
            #print('Total preview time %0.2f ms'%((time.perf_counter_ns() - start)/1e6))

        if saveData and data.readout_count > 0:
            #this part goes readout by readout
            #get ROIs for more generic processing when there are multiple ROIs -- assumes no metada -> will need additional offset code for that                
            roiOffset = 0
            for k in range(0, len(self.fullData)):            
                roiCols = np.shape(self.fullData[k])[2]
                roiRows = np.shape(self.fullData[k])[1]         
                readCounter = 0
                for i in range(0,data.readout_count):    #readout by readout
                    #start = time.perf_counter_ns()
                    offsetA = np.int64((i * readStride) / 4) + roiOffset
                    readoutDat = numpyRO[offsetA:np.int64(roiCols*roiRows)+offsetA]
                    #the Write() worker daemon will fill in the fullData array from the queue
                    #the processing function is free to continue
                    q.put([k, readCounter + self.counter, roiRows, roiCols, readoutDat])
                    readCounter += 1
                    #print('Loop time: %0.2f ms'%((time.perf_counter_ns() - start)/1e6))
                roiOffset = roiOffset + np.int32(roiCols*roiRows)
        self.counter += data.readout_count
        #print('Total process time (%d bit data): %0.2f ms'%(self.bits, (time.perf_counter_ns() - start)/1e6))
    
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

    #-s mode, default saves to numpy array in memory, -d mode optionally write to disk (and not keep in memory)
    def Acquire(self,*,frames: int=1, bufNomWidth: int=50, saveDisk: bool=False, launchDisp: bool=False):    #will launch the AcquireHelper function in a new thread when user calls it
        self.saveDisk = saveDisk
        frameCount = ctypes.c_int(0)
        frameCount.value = frames
        self.picamLib.Picam_SetParameterLargeIntegerValue(self.cam,paramFrames,frameCount)
        #0 is for infinite preview, don't allow for -s mode
        if self.Commit() and frameCount.value > 0:
            self.ResetCount()
            #set up total data objects
            #self.totalData = np.zeros((frameCount.value,self.numRows,self.numCols))
            if self.saveDisk:
                #if saving to disk, just set up 1 dummy array for ROI info while parsing.
                self.SetupFullData(1)
                timeStr = time.strftime('%Y%d%m-%H%M%S',time.gmtime())
                #filename will have info for ROI 1 -- if multiple ROIs the dims will not apply
                self.filename = 'data' + timeStr + '-%dx%d-%d-%dbit.raw'%(np.shape(self.fullData[0])[2],np.shape(self.fullData[0])[1],frames,self.bits)
                self.fileHandle = open(self.filename, 'wb')
            else:
                self.SetupFullData(frames)
            if self.display:
                SetupDisplay(self.numRows, self.numCols, self.windowName)
            self.picamLib.Picam_GetParameterIntegerValue(self.cam, paramStride, ctypes.byref(self.rStride))

            #adding ring buffering so that large number of frames can still be collected if saving
            #same as in AcquireCB()
            self.picamLib.PicamAdvanced_GetCameraDevice(self.cam, ctypes.byref(self.dev))
            widthNominal = np.floor(512*1024*1024/self.rStride.value)
            if widthNominal < bufNomWidth:                    #user can input bufWidth (useful when testing large data formats)
                buffWidth = self.rStride.value*bufNomWidth
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
            writeThread = threading.Thread(target=Write, daemon=True, args=(self,))
            writeThread.start()
            #use launchDisp when running interactively -- in this case the calling thread will not return until acquisition stops.
            if launchDisp:
                self.DisplayCameraData()

    #display will only show first ROI
    def DisplayCameraData(self):    #this will block and then unregister callback (if applicable) when done
        #do-while
        cv2.waitKey(100)
        runStatus = ctypes.c_bool(False)
        self.picamLib.Picam_IsAcquisitionRunning(self.cam, ctypes.byref(runStatus))
        self.runningStatus = runStatus
        while self.runningStatus:
            if self.display and len(self.newestFrame) > 0:                                  
                DisplayImage(self.newestFrame, self.windowName, self.bits)
            cv2.waitKey(42) #~24fps, if it can keep up
        print('Acquisition stopped. %d readouts obtained in %0.3fs.'%(self.counter, (time.perf_counter_ns()-self.acqTimer)/1e9))
        try:
            self.picamLib.PicamAdvanced_UnregisterForAcquisitionUpdated(self.dev, self.acqCallback)
        except:
            pass
        cv2.waitKey(10000)
        cv2.destroyAllWindows()

    #since we're not saving data here, this is not generalized for multi-ROI -- the first ROI will be displayed
    #-p mode
    def AcquireCB(self,*,frames: int=5, bufNomWidth: int=50, launchDisp: bool=False):    #utilizes Advanced API to demonstrate callbacks, returns immediately
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
            if widthNominal < bufNomWidth:                    #user can input bufWidth (useful when testing large data formats)
                buffWidth = self.rStride.value*bufNomWidth
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
            self.acqTimer = time.perf_counter_ns()
            self.picamLib.Picam_StartAcquisition(self.dev)        
            print('Acquisition of %d frames started (preview mode)...'%(frameCount.value))
            stopThread = threading.Thread(target=Stop, daemon=True, args=(self,))
            stopThread.start()
            #use launchDisp when running interactively -- in this case the calling thread will not return until acquisition stops.
            if launchDisp:
                self.DisplayCameraData()

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
        start = time.perf_counter_ns()
        q.join()        
        if self.saveDisk:
            self.fileHandle.close()
            print('Disk writing lag: %0.2f ms'%((time.perf_counter_ns() - start)/1e6))
            return 'Data saved to %s'%(self.filename)
        else:
            return self.fullData

    def Close(self):
        self.ResetCount()
        self.picamLib.Picam_CloseCamera(self.cam)
        self.picamLib.Picam_DisconnectDemoCamera(ctypes.byref(self.camID))
        self.Uninitialize()
