#author: sabbi
#11/10/2021

import ctypes
import numpy as np
import os
#import cv2
import threading
import queue
import time
from PyQt5.QtWidgets import QVBoxLayout, QWidget, QMainWindow
from PyQt5.QtCore import QSize
from matplotlib import pyplot as plt
import matplotlib
from matplotlib.backends.backend_qtagg import FigureCanvas
from matplotlib.figure import Figure

os.environ["GENICAM_ROOT_V2_4"] = "/opt/pleora/ebus_sdk/x86_64/lib/genicam/"    #declaration needed for Linux SDK

lock = threading.Lock()
q = queue.Queue()
qTimes = queue.Queue()
qMeta = queue.Queue()

displayType = {0:'opencv', 1:'matplotlib'}

def calcParam(v,c,n):
    return (((c)<<24)+((v)<<16)+(n))

#check picam.h for parameter definitions -- maybe turn this into a dictionary so I don't need to use GetEnumString
paramFrames = ctypes.c_int(calcParam(6,2,40))    #PicamParameter_ReadoutCount
paramStride = ctypes.c_int(calcParam(1,1,45))    #PicamParameter_ReadoutStride
paramFrameSize = ctypes.c_int(calcParam(1,1,42))
paramFrameStride = ctypes.c_int(calcParam(1,1,43))
paramFramesPerRead = ctypes.c_int(calcParam(1,1,44))
paramROIs = ctypes.c_int(calcParam(5, 4, 37))    #PicamParameter_Rois
paramReadRate=ctypes.c_int(calcParam(2,1,50))    #PicamParameter_ReadoutRateCalculation
paramExpose=ctypes.c_int(calcParam(2,2,23))        #PicamParameter_ExposureTime
paramRepetitiveGate=ctypes.c_int(calcParam(7,5,94))
paramReadoutControlMode=ctypes.c_int(calcParam(4,3,26))
paramActiveWidth=ctypes.c_int(calcParam(1,2,1))
paramActiveHeight=ctypes.c_int(calcParam(1,2,2))
paramTopMargin=ctypes.c_int(calcParam(1,2,4))
paramBottomMargin=ctypes.c_int(calcParam(1,2,6))
paramLeftMargin=ctypes.c_int(calcParam(1,2,3))
paramRightMargin=ctypes.c_int(calcParam(1,2,5))
paramMaskHeight=ctypes.c_int(calcParam(1,2,7))
paramMaskTopMargin=ctypes.c_int(calcParam(1,2,8))
paramMaskBottomMargin=ctypes.c_int(calcParam(1,2,73))
paramCorrectPixelBias=ctypes.c_int(calcParam(3,3,106))
paramVerticalShiftRate=ctypes.c_int(calcParam(2,3,13))
paramCleanUntilTrigger=ctypes.c_int(calcParam(3,3,22))
paramCleanSerialRegister=ctypes.c_int(calcParam(3,3,19))
paramCleanBeforeExposure=ctypes.c_int(calcParam(3,3,78))
paramAdcSpeed=ctypes.c_int(calcParam(2,3,33))
paramAdcQuality=ctypes.c_int(calcParam(4,3,36))
paramAdcGain=ctypes.c_int(calcParam(4,3,35))
paramAdcBitDepth=ctypes.c_int(calcParam(1,3,34))
paramReadoutPortCount=ctypes.c_int(calcParam(1,3,28))
paramSensorActiveWidth = ctypes.c_int(calcParam(1,1,59))
paramSensorActiveHeight = ctypes.c_int(calcParam(1,1,60))
paramShutterClosingDelay=ctypes.c_int(calcParam(2,2,25))
paramShutterOpeningDelay=ctypes.c_int(calcParam(2,2,46))
paramSensorTemperatureReading = ctypes.c_int(calcParam(2,1,15))
paramSensorTemperatureSetPoint = ctypes.c_int(calcParam(2,2,14))
paramSensorTemperatureStatus = ctypes.c_int(calcParam(4,1,16))

#metadata related
paramTimeStamps = ctypes.c_int(calcParam(4,3,68))
paramTimeStampResolution = ctypes.c_int(calcParam(6,3,69))
paramTimeStampBitDepth = ctypes.c_int(calcParam(1,3,70))
paramTrackFrames = ctypes.c_int(calcParam(3,3,71))
paramFrameTrackingBitDepth = ctypes.c_int(calcParam(1,3,72))

#display related objects/ functions
class ImageWindowMPL(QMainWindow):
    def __init__(self, numRows, numCols, windowName):
        super().__init__()
        self.numRows = numRows
        self.numCols = numCols
        self.winWidth, self.winHeight = WindowSize(numRows, numCols)
        self.widget = QWidget()
        self.windowTitle = windowName
        self.setFixedSize(QSize(np.int32(self.winWidth),np.int32(self.winHeight)))
        self.setWindowTitle(self.windowTitle)
        self.setCentralWidget(self.widget)

    def InitializeLayout(self):
        self.layout = QVBoxLayout()
        self.widget.setLayout(self.layout)
        self.canvas = FigureCanvas(Figure(figsize=(self.winWidth/75,self.winHeight/75)))
        self.fig = self.canvas.figure
        self.layout.addWidget(self.canvas)
        self.ax = self.fig.subplots()
        dummyData = np.zeros([self.numRows,self.numCols])
        if np.size(dummyData,0)==1:
            self.ax.grid()
            (self.artist,) = self.ax.plot(dummyData[0])
            self.ax.set_xlabel('Pixel')
            self.ax.set(xlim=(0,np.size(dummyData[0])))
            self.ax.set_ylabel('Intensity (counts)')
        else:
            self.artist = self.ax.imshow(dummyData,origin='upper',cmap='gray')
            self.ax.set_xlabel('Column')
            self.ax.set_ylabel('Row')
        self.ax.set_title(self.windowTitle)
        self.bg = self.fig.canvas.copy_from_bbox(self.fig.bbox)
        self.ax.draw_artist(self.artist)
        self.fig.canvas.blit(self.fig.bbox)
        self.widget.show()
    
    def UpdateData(self, imData):
        self.fig.canvas.restore_region(self.bg)
        if np.size(imData,0)==1:            
            upper = np.max(imData[0])*1.25
            self.ax.set(ylim=(0,upper))            
            self.artist.set_ydata(imData[0])            
        else:
            self.artist.set_data(imData)
            self.artist.autoscale() 
            #ax.imshow(imData,origin='upper',vmin=display_min,vmax=display_max,cmap='gray',animated=True)  
        
        self.ax.draw_artist(self.artist)
        self.fig.canvas.blit(self.fig.bbox)
        self.fig.canvas.flush_events()

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

def SetupDisplayMPL(numRows,numCols,windowName):
    winWidth, winHeight = WindowSize(numRows, numCols)
    fig = plt.figure(windowName, figsize=(winWidth/75,winHeight/75))
    ax = fig.add_subplot(1,1,1)
    dummyData = np.zeros([numRows,numCols])
    if np.size(dummyData,0)==1:
        ax.grid()
        (artist,) = ax.plot(dummyData[0])
        ax.set_xlabel('Pixel')
        ax.set(xlim=(0,np.size(dummyData[0])))
        ax.set_ylabel('Intensity (counts)')
    else:
        artist = ax.imshow(dummyData,origin='upper',cmap='gray')
        ax.set_xlabel('Column')
        ax.set_ylabel('Row')
    ax.set_title(windowName)
    #manager = fig.canvas.manager
    plt.show(block=False)
    #plt.pause(.01)

    bg = fig.canvas.copy_from_bbox(fig.bbox)
    ax.draw_artist(artist)
    fig.canvas.blit(fig.bbox)
    return ax, fig, artist, bg

def SetupDisplayPyQt(numRows, numCols,windowName):
    winWidth, winHeight = WindowSize(numRows, numCols)
    window = pg.GraphicsLayoutWidget(size=(winWidth, winHeight), title=windowName)
    vb = pg.ViewBox()
    dummyData = np.zeros([numRows,numCols])    
    if np.size(dummyData,0)==1:
        p1 = pg.PlotDataItem(y=dummyData[0])              
    else:
        p1 = pg.ImageItem(image=dummyData)
    vb.addItem(p1)
    window.addItem(vb, 0, 0)
    window.show()
    print(len(dummyData[0]))
    test = pg.plot(np.random.normal(size=1024))
    return window, vb, p1

def DisplayImage(imData, windowName, bits):        #data needs to be passed in correct shape
    vmax = pow(2,16)-1
    if bits >16:
        #needed because opencv can't display uint32
        #vmax = pow(2,bits)-1
        divFactor = pow(2,bits-16)
        imData = (imData/divFactor).astype(np.uint16)
    normData = cv2.normalize(imData,None,alpha=0, beta=vmax, norm_type=cv2.NORM_MINMAX)    
    cv2.imshow(windowName, normData)

def DisplayImageMPL(imData, windowName, bits, ax, fig, artist, bg):
    start = time.perf_counter_ns()
    fig.canvas.restore_region(bg)
    #print('Time for percentile: %0.3fms'%((time.perf_counter_ns()-start)/1e6))
    #ax.clear()

    if np.size(imData,0)==1:
        artist.set_ydata(imData[0])
        upper = np.max(imData[0])*1.25
        ax.set(ylim=(0,upper))
        #plt.pause(.001) #setting axes limits so this is needed
        plt.draw()
    else:
        artist.set_data(imData)
        artist.autoscale() 
        #ax.imshow(imData,origin='upper',vmin=display_min,vmax=display_max,cmap='gray',animated=True)  
    
    ax.draw_artist(artist)
    fig.canvas.blit(fig.bbox)
    fig.canvas.flush_events()
    #print('Time for imshow: %0.3fms'%((time.perf_counter_ns()-start)/1e6))
    
def DisplayImagePG(imData, bits, displayItem):
    pass
    
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
        with lock:
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
    if not camera.dispType == 3:
        input()
        print('Key pressed during acquisition -- acquisition will stop.')
    camera.picamLib.Picam_StopAcquisition(camera.dev)  
    if len(camera.newestFrame > 0):
        print('Mean of most recently processed frame: %0.3f cts'%(np.mean(camera.newestFrame)))

def QueueTimes(camera):
    while True:
        queueItem = qTimes.get()
        time = queueItem[0]
        camera.processTimesArray = np.append(camera.processTimesArray,time)
        qTimes.task_done()


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

def WriteMeta(camera):
    time.sleep(.001)
    while True:
        #will be a ctypes array of bytes
        queueItem = qMeta.get()
        #self.metaDict = {'TimeStampStart':[False,0,0], 'TimeStampStop':[False,0,0], 'FrameNo':[False,0], 'GateDelay':[False,0,0], 'ModPhase':[False,0]}
        #default seems to be 8 byte depth -- use long int and double
        offset = 0
        #print(ctypes.byref(queueItem), ctypes.byref(queueItem, ctypes.sizeof(ctypes.c_ubyte)*20))
        for key in camera.metaDict:
            if camera.metaDict[key][0] == True:
                if key == 'FrameNo':
                    value = ctypes.c_ulonglong(0)
                else:
                    value = ctypes.c_longlong(0)
                ctypes.memmove(ctypes.byref(value), ctypes.byref(queueItem, ctypes.sizeof(ctypes.c_ubyte)*offset), ctypes.sizeof(value))
                offset += np.int64(np.floor((camera.metaDict[key][1] + 7)/8))
                if key == 'FrameNo':
                    printVal = '%d'%(value.value)
                else:
                    printVal = '%0.3fms'%(value.value * 1000 / camera.metaDict[key][2])
                print(key, '\t%s'%(printVal))
        qMeta.task_done()

class Event():
    def __init__(self):
        self.eventHandlers = []
    def __iadd__(self, handler):
        self.eventHandlers.append(handler)
        return self
    def __isub__(self, handler):
        self.eventHandlers.remove(handler)
        return self
    def __call__(self, *args, **keywargs):
        for eventhandler in self.eventHandlers:
            eventhandler(*args, **keywargs)

class MetaData():
    def __init__(self):
        self.timeStarted = None
        self.timeStopped = None
        self.frameNo = None
        self.gateDelay = None
        self.modPhase = None

class ctypesStruct(ctypes.Structure):
    def __eq__(self, compareTo):
        for field in self._fields_:
            if getattr(self, field[0]) != getattr(compareTo, field[0]):
                return False
        return True
    def __ne__(self, compareTo):
        for field in self._fields_:
            if getattr(self, field[0]) != getattr(compareTo, field[0]):
                return True
        return False

class camIDStruct(ctypesStruct):
    _fields_=[
        ('model', ctypes.c_int),
        ('computer_interface', ctypes.c_int),
        ('sensor_name', ctypes.c_char * 64),
        ('serial_number', ctypes.c_char * 64)]



class firmwareDetail(ctypesStruct):
    _fields_=[
        ('name', ctypes.c_char * 64),
        ('detail', ctypes.c_char * 256)]

class availableData(ctypesStruct):
    _fields_=[
        ('initial_readout', ctypes.c_void_p),
        ('readout_count', ctypes.c_longlong)]

class acqStatus(ctypesStruct):
        _fields_=[
            ('running', ctypes.c_bool),
            ('errors', ctypes.c_int),
            ('readout_rate',ctypes.c_double)]

class acqBuf(ctypesStruct):
        _fields_=[
            ('memory', ctypes.c_void_p),
            ('memory_size',ctypes.c_longlong)]

class roiStruct(ctypesStruct):
    _fields_=[
        ('x', ctypes.c_int),
        ('width', ctypes.c_int),
        ('x_binning', ctypes.c_int),
        ('y', ctypes.c_int),
        ('height', ctypes.c_int),
        ('y_binning', ctypes.c_int)]

class roisStruct(ctypesStruct):
    _fields_=[
        ('roi_array', ctypes.c_void_p),
        ('roi_count', ctypes.c_int)]

class picamPulse(ctypesStruct):
    _fields_=[
        ('delay', ctypes.c_double),
        ('width', ctypes.c_double)]
    
class collectionConstraint(ctypesStruct):
    _fields_=[
        ('scope', ctypes.c_int),
        ('severity', ctypes.c_int),
        ('values_array', ctypes.c_void_p),
        ('values_count', ctypes.c_int)]

class validationResult(ctypesStruct):
    _fields_=[
        ('is_valid', ctypes.c_bool),
        ('failed_parameter', ctypes.c_int),
        ('failed_error_constraint_scope', ctypes.c_int),
        ('failed_warning_constraint_scope', ctypes.c_int),
        ('error_constraining_parameter_array', ctypes.c_void_p),
        ('error_constraining_parameter_count', ctypes.c_int),
        ('warning_constraining_parameter_array', ctypes.c_void_p),
        ('warning_constraining_parameter_count', ctypes.c_int)]


#base class, functions for command line operations
class Camera():
    errorsMask = {0x00:'None', 0x10:'Camera Faulted', 0x02:'Connection Lost', 0x08:'Shutter Overheated', 0x01:'Data Lost', 0x04:'Data Not Arriving'}
    def __init__(self,*,libPath: str='/usr/local/lib/libpicam.so', dispType: int=0):    #class will instantiate and initialize PICam
        self.dispType = dispType
        self.picamLib = ctypes.cdll.LoadLibrary(libPath)
        self.ResetCount()
        self.initString = self.Initialize()

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
                self.ProcessData(available.contents, self.rStride.value, saveData = self.saveDisk)
            elif self.bits > 16 and self.bits <=32:
                self.ProcessData32(available.contents, self.rStride.value, saveData = self.saveDisk)
        with lock:
            self.runningStatus = status.contents.running
        if status.contents.errors != 0x00:
            print('!!\tAcquisition Callback Error: %s\t!!'%(self.errorsMask[status.contents.errors]))
        return 0
    
    #this ended up as a generic clearing function
    def ResetCount(self):
        self.cam = ctypes.c_void_p(0)
        self.dev = ctypes.c_void_p(0)
        self.camID = camIDStruct(0,0,b'',b'')
        self.numRows = ctypes.c_int(0)  #for first ROI
        self.numCols = ctypes.c_int(0)  #for first ROI
        self.readRate = ctypes.c_double(0)        
        self.counter = 0
        self.totalData = np.array([])
        self.fullData = []  #will include ROIs
        self.newestFrame = np.array([])
        self.rStride = ctypes.c_int(0)
        self.frameSize = ctypes.c_int(0)
        self.frameStride = ctypes.c_int(0)
        self.framesPerRead = ctypes.c_int(0)

        self.bits = 0   #bit depth of the camera referenced by self.cam
        self.display = False
        self.runningStatus = ctypes.c_bool(False)
        self.windowName = ''
        self.circBuff = ctypes.ARRAY(ctypes.c_ubyte,0)()
        self.aBuf = acqBuf(0,0)
        self.roisPy=[]
        self.metaData = []
        #[enabled, bit depth, res]
        self.metaDict = {'TimeStampStart':[False,0,0], 'TimeStampStop':[False,0,0], 'FrameNo':[False,0], 'GateDelay':[False,0,0], 'ModPhase':[False,0]}        
        self.saveDisk = False
        self.eventTimer = 0
        self.acqTimer = 0
        self.figWindow = None
        self.processTimesArray = np.array([])
        self.openStatus = -1

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
        outStr = ''
        outStr += 'PICam Initialized: %r'%initCheck.value
        if initCheck:
            #version check if PICam successfully initialized
            major = ctypes.c_int(0)
            minor = ctypes.c_int(0)
            distribution = ctypes.c_int(0)
            released = ctypes.c_int(0)
            self.picamLib.Picam_GetVersion(ctypes.byref(major),ctypes.byref(minor),ctypes.byref(distribution),ctypes.byref(released))
            outStr += '\n\tVersion %d.%d.%d.%d'%(major.value, minor.value, distribution.value, released.value)
            #display behavior: if dispType entered 0 (default), qt w/ opencv is used. mpl is only used if there is 1 row 
            #if dispType is entered 1, the mpl will be used for both images and line plots. backend must be set accordingly
            if self.dispType == 1:
                matplotlib.use('TkAgg')
        if not self.dispType == 3:
            print(outStr)
        return outStr

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
        self.display = True
        #if there is one row in the first ROI, use matplotlib for line plot -- backend needs to be set properly
        if not self.dispType == 3:
            if self.numRows == 1:
                self.dispType = 1
                matplotlib.use('TkAgg')
        if self.numRows <= 1 and self.dispType == 0:
            self.display = False       #opencv can't handle line plots, so don't plot single row data if using opencv
    
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
            self.SetFastestShiftRate()
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

    def SetFastestShiftRate(self):
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
        self.Commit()

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
    
    #set dual port (for fast line reads) -- if param exists/ valid
    def SetDualPort(self):
        exist = self.CheckExistenceAndRelevance(paramReadoutPortCount)
        if exist == 0:
            ports = ctypes.c_int(0)
            self.picamLib.Picam_SetParameterIntegerValue(self.cam, paramReadoutPortCount, ctypes.c_int(2))
            self.Commit(printMessage=False)
            self.picamLib.Picam_GetParameterIntegerValue(self.cam, paramReadoutPortCount, ctypes.byref(ports))
            print('Attempting to change to dual port... set to %d port readout.'%(ports.value))
            

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

    #fills in strides
    def GetSizeParameters(self):
        self.picamLib.Picam_GetParameterIntegerValue(self.cam, paramFrameSize, ctypes.byref(self.frameSize))
        self.picamLib.Picam_GetParameterIntegerValue(self.cam, paramFrameStride, ctypes.byref(self.frameStride))
        self.picamLib.Picam_GetParameterIntegerValue(self.cam, paramFramesPerRead, ctypes.byref(self.framesPerRead))
        self.picamLib.Picam_GetParameterIntegerValue(self.cam, paramStride, ctypes.byref(self.rStride))

    def Commit(self,*,printMessage: bool=True):
        #paramArray = ctypes.pointer(ctypes.c_int(0))
        paramArray = ctypes.c_void_p(0)
        failedCount = ctypes.c_int(1)
        self.picamLib.Picam_CommitParameters(self.cam, ctypes.byref(paramArray), ctypes.byref(failedCount))

        #update cam object's bit depth value on each commit
        bitsInt = ctypes.c_int(0)
        self.picamLib.Picam_GetParameterIntegerValue(self.cam, paramAdcBitDepth, ctypes.byref(bitsInt))
        self.bits = bitsInt.value
        if self.bits > 0 and self.bits <=16:
            self.bpp = 2
        elif self.bits <=32:
            self.bpp = 4
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
            print('Changing the following %d parameters to allow a successful commit:'%(failedCount.value))
        for i in range(0,failedCount.value):
            #print('\tFailed Param: %d'%(paramArray[i]))
            paramV = ctypes.c_int(0)
            enumStr = ctypes.c_char_p()
            self.picamLib.Picam_GetEnumerationString(6, paramArray[i], ctypes.byref(enumStr))   #6 = PicamEnumeratedType_Parameter
            self.picamLib.Picam_GetParameterValueType(self.cam,paramArray[i],ctypes.byref(paramV))
            #print('%s'%(enumStr.value.decode('utf-8')))
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
        self.GetSizeParameters()        


    def CheckExistenceAndRelevance(self, param: int):
        outputDict = {0: 'Exists and Valid', 1: 'Does not Exist', 2: 'Exists, not Relevant'}
        exist = ctypes.c_bool(False)
        self.picamLib.Picam_DoesParameterExist(self.cam, param, ctypes.byref(exist))
        if exist:
            relevant = ctypes.c_bool(False)
            self.picamLib.Picam_IsParameterRelevant(self.cam, param, ctypes.byref(relevant))
            if relevant:
                return 0
            else:
                return 2
        else:
            return 1

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

    #connect demo cam (don't open) for testing purposes
    def ConnectDemoCam(self,*,model: int=1206):
        connectErr = self.picamLib.Picam_ConnectDemoCamera(model,b'TestCam',ctypes.byref(self.camID))
        if connectErr != 0:            
            print('Demo Connection Error: %s'%(self.EnumString(1, connectErr)))

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

    ###################################
    ########GUI Funcs
    ###exposure functions (may still be useful for base object)
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
    def GetExposure(self):
        exist = ctypes.c_bool(False)
        self.picamLib.Picam_DoesParameterExist(self.cam, paramExpose, ctypes.byref(exist))
        if exist:
            expTime = ctypes.c_double(0)
            self.picamLib.Picam_GetParameterFloatingPointValue(self.cam,paramExpose,ctypes.byref(expTime))
            return expTime.value
        self.picamLib.Picam_DoesParameterExist(self.cam, paramRepetitiveGate, ctypes.byref(exist))
        if exist:
            ogPulse = ctypes.c_void_p(0)
            self.picamLib.Picam_GetParameterPulseValue(self.cam, paramRepetitiveGate, ctypes.byref(ogPulse))
            ogPulse = ctypes.cast(ogPulse,ctypes.POINTER(picamPulse))
            ogWidth = ogPulse[0].width
            ogDelay = ogPulse[0].delay
            return ogWidth/1e6
        else:
            return 0

    #ROI Functions for GUI dropdown
    #full ROI relies on sensorinformation
    def SetFullROI(self):
        defRows = ctypes.c_int(0)
        defCols = ctypes.c_int(0)
        self.picamLib.Picam_GetParameterIntegerValue(self.cam, paramSensorActiveWidth, ctypes.byref(defCols))
        self.picamLib.Picam_GetParameterIntegerValue(self.cam, paramSensorActiveHeight, ctypes.byref(defRows))
        roiArray = ctypes.ARRAY(roiStruct, 1)()
        roiArray[0] = roiStruct(0, defCols.value, 1, 0, defRows.value, 1)
        rois = roisStruct(ctypes.addressof(roiArray), 1)
        self.picamLib.Picam_SetParameterRoisValue(self.cam, paramROIs, ctypes.byref(rois))
        self.GetFirstROI()
        print('Full Frame ROI set: %d (cols) x %d (rows)'%(self.numCols, self.numRows))
        self.Commit()

    #sets square (nxn) ROI in the center of the active sensor, assuming given dimension meets constraints
    def SetCenterROI(self, dim: np.int32):
        retVal = False
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
                self.Commit()
                retVal = True
            else:
                '''
                #get the default ROI
                roisDef = ctypes.c_void_p(0)
                self.picamLib.Picam_GetParameterRoisDefaultValue(self.cam, paramROIs, ctypes.byref(roisDef))
                self.picamLib.Picam_SetParameterRoisValue(self.cam, paramROIs, roisDef)
                self.picamLib.Picam_DestroyRois(roisDef)
                '''
                print('Could not change ROI. ROI has defaulted back to ')
                self.SetFullROI()
                retVal = False
            self.GetFirstROI()
            print('%d (cols) x %d (rows)'%(self.numCols, self.numRows))
            self.picamLib.Picam_DestroyValidationResult(valObj)
            #print(newX.value, newY.value)
            return retVal
        #this is the exit if something fails along the way
        print('Could not attempt to set center ROI due to parameter and/or dimension mismatch.')
        return False

    #full width, bin n center rows
    def SetCenterBinROI(self, rows: np.int32=1):
        retVal = False
        defRows = ctypes.c_int(0)
        defCols = ctypes.c_int(0)
        self.picamLib.Picam_GetParameterIntegerValue(self.cam, paramSensorActiveWidth, ctypes.byref(defCols))
        self.picamLib.Picam_GetParameterIntegerValue(self.cam, paramSensorActiveHeight, ctypes.byref(defRows))
        #print(defRows.value, defCols.value)
        if rows <= defRows.value and rows >0:
            newDim = ctypes.c_int(rows)
            newX = ctypes.c_int(0)
            newY = ctypes.c_int(np.int32(np.floor(defRows.value/2 - rows/2)))
            newHeight = ctypes.c_int(rows)
            newYBin = ctypes.c_int(rows)
            roiArray = ctypes.ARRAY(roiStruct, 1)()
            roiArray[0] = roiStruct(newX.value, defCols.value, 1, newY.value, newHeight.value, newYBin.value)
            rois = roisStruct(ctypes.addressof(roiArray), 1)
            self.picamLib.Picam_SetParameterRoisValue(self.cam, paramROIs, ctypes.byref(rois))
            #now validate the ROI that was just set
            valObj = ctypes.c_void_p(0)
            self.picamLib.PicamAdvanced_ValidateParameter(self.cam, paramROIs, ctypes.byref(valObj))
            valObj = ctypes.cast(valObj,ctypes.POINTER(validationResult))
            #print(valObj[0].is_valid)
            if valObj[0].is_valid:
                print('Successfully changed ROI to ',end='')
                self.Commit()
                retVal = True
            else:
                '''
                #get the default ROI
                roisDef = ctypes.c_void_p(0)
                self.picamLib.Picam_GetParameterRoisDefaultValue(self.cam, paramROIs, ctypes.byref(roisDef))
                self.picamLib.Picam_SetParameterRoisValue(self.cam, paramROIs, roisDef)
                self.picamLib.Picam_DestroyRois(roisDef)
                '''
                print('Could not change ROI. ROI has defaulted back to ')
                self.SetFullROI()
                retVal = False
            self.GetFirstROI()
            print('%d (cols) x %d (rows)'%(self.numCols, self.numRows))
            self.picamLib.Picam_DestroyValidationResult(valObj)
            #print(newX.value, newY.value)
            return retVal
        #this is the exit if something fails along the way
        print('Could not attempt to set center ROI due to parameter and/or dimension mismatch.')
        return False

    #Quality List for GUI dropdown
    def CapableQualities(self):
        qualCapObj = ctypes.c_void_p(0)
        qual = ctypes.c_double(0)
        qualList = []
        exist = ctypes.c_bool(False)
        self.picamLib.Picam_DoesParameterExist(self.cam, paramAdcQuality, ctypes.byref(exist))
        if exist:
            self.picamLib.Picam_GetParameterCollectionConstraint(self.cam,paramAdcQuality,1,ctypes.byref(qualCapObj))
            qualCapObj = ctypes.cast(qualCapObj,ctypes.POINTER(collectionConstraint))
            for i in range(0,qualCapObj[0].values_count):
                qual.value = ctypes.cast(qualCapObj[0].values_array,ctypes.POINTER(ctypes.c_double))[i]
                qualList.append(np.int32(qual.value))
        return qualList
    def GetQuality(self):
        exist = ctypes.c_bool(False)
        self.picamLib.Picam_DoesParameterExist(self.cam, paramAdcQuality, ctypes.byref(exist))
        if exist:
            qual = ctypes.c_int(0)
            self.picamLib.Picam_GetParameterIntegerValue(self.cam,paramAdcQuality,ctypes.byref(qual))
            return qual.value
        else:
            return None
    def SetQuality(self, qual: int):
        exist = ctypes.c_bool(False)
        self.picamLib.Picam_DoesParameterExist(self.cam, paramAdcQuality, ctypes.byref(exist))
        if exist:
            self.picamLib.Picam_SetParameterIntegerValue(self.cam,paramAdcQuality,ctypes.c_int(qual))
            self.Commit()
    
    #Speed List for GUI dropdown
    def RequiredSpeeds(self):
        speedReqObj = ctypes.c_void_p(0)
        speed = ctypes.c_double(0)
        speedList = []
        exist = ctypes.c_bool(False)
        self.picamLib.Picam_DoesParameterExist(self.cam, paramAdcSpeed, ctypes.byref(exist))
        if exist:
            self.picamLib.Picam_GetParameterCollectionConstraint(self.cam,paramAdcSpeed,2,ctypes.byref(speedReqObj))
            speedReqObj = ctypes.cast(speedReqObj,ctypes.POINTER(collectionConstraint))
            for i in range(0,speedReqObj[0].values_count):
                speed.value = ctypes.cast(speedReqObj[0].values_array,ctypes.POINTER(ctypes.c_double))[i]
                speedList.append(np.float64(speed.value))
        return speedList
    def GetSpeed(self):
        exist = ctypes.c_bool(False)
        self.picamLib.Picam_DoesParameterExist(self.cam, paramAdcSpeed, ctypes.byref(exist))
        if exist:
            speed = ctypes.c_double(0)
            self.picamLib.Picam_GetParameterFloatingPointValue(self.cam,paramAdcSpeed,ctypes.byref(speed))
            return speed.value
        else:
            return None
    def SetSpeed(self, speed: np.float64):
        exist = ctypes.c_bool(False)
        self.picamLib.Picam_DoesParameterExist(self.cam, paramAdcSpeed, ctypes.byref(exist))
        if exist:
            try:
                self.picamLib.Picam_SetParameterFloatingPointValue(self.cam,paramAdcSpeed,ctypes.c_double(speed))
            except TypeError:
                return
            finally:
                self.Commit()

    #Gain List for GUI Dropdown
    def RequiredGains(self):
        gainReqObj = ctypes.c_void_p(0)
        gain = ctypes.c_double(0)
        gainList = []
        exist = self.CheckExistenceAndRelevance(paramAdcGain)
        if exist == 0:
            self.picamLib.Picam_GetParameterCollectionConstraint(self.cam,paramAdcGain,2,ctypes.byref(gainReqObj))
            gainReqObj = ctypes.cast(gainReqObj,ctypes.POINTER(collectionConstraint))
            for i in range(0,gainReqObj[0].values_count):
                gain.value = ctypes.cast(gainReqObj[0].values_array,ctypes.POINTER(ctypes.c_double))[i]
                gainList.append(np.int32(gain.value))
        return gainList
    def GetGain(self):
        exist = self.CheckExistenceAndRelevance(paramAdcGain)
        if exist == 0:
            gain = ctypes.c_int(0)
            self.picamLib.Picam_GetParameterIntegerValue(self.cam, paramAdcGain, ctypes.byref(gain))
            return gain.value
        else:
            return None
    def SetGain(self, gain: np.int32):
        exist = self.CheckExistenceAndRelevance(paramAdcGain)
        if exist == 0:
            try:
                self.picamLib.Picam_SetParameterIntegerValue(self.cam,paramAdcSpeed,ctypes.c_int(gain))
            except TypeError:
                return
            finally:
                self.Commit()
    
    #Frames to Save (from GUI, can be used generally)
    #returns what was actually set
    def SetFramesToSave(self, frames: np.int32=1):
        self.picamLib.Picam_SetParameterLargeIntegerValue(self.cam,paramFrames,ctypes.c_int(frames))
        actualFrames = ctypes.c_int(0)
        self.picamLib.Picam_GetParameterLargeIntegerValue(self.cam,paramFrames,ctypes.byref(actualFrames))
        return actualFrames.value

    #function to process 16-bit data
    def ProcessData(self, data, readStride,*,saveData: bool=True):
        with lock:
            start = time.perf_counter_ns()
            x=ctypes.cast(data.initial_readout,ctypes.POINTER(ctypes.c_byte))#size of full readout           
            if data.readout_count > 0:                
                #this part processes only the final frame for display
                if self.counter % 1 == 0:
                    roiCols = np.shape(self.fullData[0])[2]
                    roiRows = np.shape(self.fullData[0])[1]
                    offsetA = np.int64(((data.readout_count-1) * (readStride)) + ((self.framesPerRead.value-1)*self.frameStride.value))
                    #offsetAddr = ctypes.cast(x[offsetA])
                    copySize = int(roiCols*roiRows*self.bpp)
                    copyArray = np.zeros([np.int64(roiRows*roiCols)], dtype=np.uint16)
                    copyAddr = copyArray.__array_interface__['data'][0]
                    #print(type(copyAddr), type(int(ctypes.addressof(x.contents)+offsetA)), type(ctypes.addressof(x.contents)), type(copySize))
                    ctypes.memmove(copyAddr, int(ctypes.addressof(x.contents)+offsetA), copySize)
                    #print(copyArray[0])
                    self.newestFrame = copyArray
            #print('Total preview time %0.2f ms'%((time.perf_counter_ns() - start)/1e6))            

            if saveData and data.readout_count > 0:
                #this part goes readout by readout
                #get ROIs for more generic processing when there are multiple ROIs -- assumes no metada -> will need additional offset code for that                
                roiOffset = 0
                for k in range(0, len(self.fullData)):            
                    roiCols = np.shape(self.fullData[k])[2]
                    roiRows = np.shape(self.fullData[k])[1]         
                    readCounter = 0
                    for i in range(0,np.uint64((data.readout_count * self.framesPerRead.value))):    #readout by readout
                        #start = time.perf_counter_ns()
                        #offsetA = np.int64((i * readStride) / 2) + roiOffset
                        offsetA = np.int64((i * self.frameStride.value)) + roiOffset
                        copySize = int(roiCols*roiRows*self.bpp)
                        copyArray = np.zeros([np.int64(roiRows*roiCols)], dtype=np.uint16)
                        copyAddr = copyArray.__array_interface__['data'][0]
                        #print(type(copyAddr), type(int(ctypes.addressof(x.contents)+offsetA)), type(ctypes.addressof(x.contents)), type(copySize))
                        ctypes.memmove(copyAddr, int(ctypes.addressof(x.contents)+offsetA), copySize)                        
                        #the Write() worker daemon will fill in the fullData array from the queue
                        #the processing function is free to continue
                        q.put([k, readCounter + self.counter, roiRows, roiCols, copyArray])
                        #handle metadata if present -- send to WriteMeta() daemon
                        metaBytes = int(self.frameStride.value-self.frameSize.value)
                        if metaBytes > 0:
                            offsetMeta = offsetA + copySize
                            metaCopyArray = ctypes.ARRAY(ctypes.c_ubyte, metaBytes)()
                            ctypes.memmove(ctypes.addressof(metaCopyArray), int(ctypes.addressof(x.contents)+offsetMeta), metaBytes)
                            qMeta.put(metaCopyArray)
                        readCounter += 1
                        #print('Loop time: %0.2f ms'%((time.perf_counter_ns() - start)/1e6))
                    roiOffset = roiOffset + np.int64(roiCols*roiRows*self.bpp)
            self.counter += data.readout_count
        #print('Total process time: %0.2f ms'%((time.perf_counter_ns() - start)/1e6))
        if data.readout_count > 0:
            qTimes.put([((time.perf_counter_ns() - start)/1e6)/data.readout_count])

    #function to process 32-bit data (>16 bits: <=32 bits)
    def ProcessData32(self, data, readStride,*,saveData: bool=True):
        with lock:
            start = time.perf_counter_ns()
            x=ctypes.cast(data.initial_readout,ctypes.POINTER(ctypes.c_byte))#size of full readout           
            if data.readout_count > 0:                
                #this part processes only the final frame for display
                if self.counter % 1 == 0:
                    roiCols = np.shape(self.fullData[0])[2]
                    roiRows = np.shape(self.fullData[0])[1]
                    offsetA = np.int64(((data.readout_count-1) * (readStride)) + ((self.framesPerRead.value-1)*self.frameStride.value))
                    #offsetAddr = ctypes.cast(x[offsetA])
                    copySize = int(roiCols*roiRows*self.bpp)
                    copyArray = np.zeros([np.int64(roiRows*roiCols)], dtype=np.uint32)
                    copyAddr = copyArray.__array_interface__['data'][0]
                    #print(type(copyAddr), type(int(ctypes.addressof(x.contents)+offsetA)), type(ctypes.addressof(x.contents)), type(copySize))
                    ctypes.memmove(copyAddr, int(ctypes.addressof(x.contents)+offsetA), copySize)
                    #print(copyArray[0])
                    self.newestFrame = copyArray
            #print('Total preview time %0.2f ms'%((time.perf_counter_ns() - start)/1e6))            

            if saveData and data.readout_count > 0:
                #this part goes readout by readout
                #get ROIs for more generic processing when there are multiple ROIs -- assumes no metada -> will need additional offset code for that                
                roiOffset = 0
                for k in range(0, len(self.fullData)):            
                    roiCols = np.shape(self.fullData[k])[2]
                    roiRows = np.shape(self.fullData[k])[1]         
                    readCounter = 0
                    for i in range(0,np.uint64((data.readout_count * self.framesPerRead.value))):    #readout by readout
                        #start = time.perf_counter_ns()
                        #offsetA = np.int64((i * readStride) / 2) + roiOffset
                        offsetA = np.int64((i * self.frameStride.value)) + roiOffset
                        copySize = int(roiCols*roiRows*self.bpp)
                        copyArray = np.zeros([np.int64(roiRows*roiCols)], dtype=np.uint32)
                        copyAddr = copyArray.__array_interface__['data'][0]
                        #print(type(copyAddr), type(int(ctypes.addressof(x.contents)+offsetA)), type(ctypes.addressof(x.contents)), type(copySize))
                        ctypes.memmove(copyAddr, int(ctypes.addressof(x.contents)+offsetA), copySize)                        
                        #the Write() worker daemon will fill in the fullData array from the queue
                        #the processing function is free to continue
                        q.put([k, readCounter + self.counter, roiRows, roiCols, copyArray])
                        #handle metadata if present -- send to WriteMeta() daemon
                        metaBytes = int(self.frameStride.value-self.frameSize.value)
                        if metaBytes > 0:
                            offsetMeta = offsetA + copySize
                            metaCopyArray = ctypes.ARRAY(ctypes.c_ubyte, metaBytes)()
                            ctypes.memmove(ctypes.addressof(metaCopyArray), int(ctypes.addressof(x.contents)+offsetMeta), metaBytes)
                            qMeta.put(metaCopyArray)
                        readCounter += 1
                        #print('Loop time: %0.2f ms'%((time.perf_counter_ns() - start)/1e6))
                    roiOffset = roiOffset + np.int64(roiCols*roiRows*self.bpp)
            self.counter += data.readout_count
        #print('Total process time: %0.2f ms'%((time.perf_counter_ns() - start)/1e6))
        if data.readout_count > 0:
            qTimes.put([((time.perf_counter_ns() - start)/1e6)/data.readout_count])
    
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
        self.newestFrame = np.zeros([roiRows, roiCols])

    #hard code the metadata you want, then parse through all options to set dictionary
    def SetupMetaData(self):
        timeStampsMask = {0:'None', 1:'Start', 2:'Stop', 3:'Both'}
        gateTrackMask = {0: 'None', 1:'Delay', 2:'Width', 3:'Both'}
        #set frame tracking
        self.picamLib.Picam_SetParameterIntegerValue(self.cam, paramTrackFrames, ctypes.c_bool(True))        
        #set time stamp
        self.picamLib.Picam_SetParameterIntegerValue(self.cam, paramTimeStamps, ctypes.c_int(3))    
        self.Commit(printMessage=False)
        self.GetSizeParameters()
        #now go through all of them and fill in the member dictionary flags -- for now, ignore gate tracking and modulation tracking.
        stamp = ctypes.c_int(0)
        tracking = ctypes.c_bool(False)
        bDepth = ctypes.c_int(0)
        #time stamp
        self.picamLib.Picam_GetParameterIntegerValue(self.cam, paramTimeStamps, ctypes.byref(stamp))
        if stamp.value > 0:
            res = ctypes.c_longlong(0)
            self.picamLib.Picam_GetParameterIntegerValue(self.cam, paramTimeStampBitDepth, ctypes.byref(bDepth))
            self.picamLib.Picam_GetParameterLargeIntegerValue(self.cam, paramTimeStampResolution, ctypes.byref(res))
            #self.metaDict = {'TimeStampStart':[False,0,0], 'TimeStampStop':[False,0,0], 'FrameNo':[False,0], 'GateDelay':[False,0,0], 'ModPhase':[False,0]} 
            if stamp.value==3:
                self.metaDict['TimeStampStart'] = [True, bDepth.value, res.value]
                self.metaDict['TimeStampStop'] = [True, bDepth.value, res.value]
            elif stamp.value == 1:
                self.metaDict['TimeStampStart'] = [True, bDepth.value, res.value]
            elif stamp.value == 2:
                self.metaDict['TimeStampStop'] = [True, bDepth.value, res.value]
        #frame tracking
        self.picamLib.Picam_GetParameterIntegerValue(self.cam, paramTrackFrames, ctypes.byref(tracking))
        if tracking.value:
            #get bit depth
            self.picamLib.Picam_GetParameterIntegerValue(self.cam, paramFrameTrackingBitDepth, ctypes.byref(bDepth))
            self.metaDict['FrameNo'] = [True, bDepth.value]            
    
    def ReadTemperatureStatus(self,*,printString: bool=True):
        tempStatus = {1: 'Unlocked', 2: 'Locked', 3: 'Faulted'}
        sensorTemp = ctypes.c_double(0)
        sensorLockStatus = ctypes.c_int(0)
        sensorSetPt = ctypes.c_double(0)
        #with lock:
        readErr = self.picamLib.Picam_ReadParameterFloatingPointValue(self.cam, paramSensorTemperatureReading, ctypes.byref(sensorTemp))
        if readErr == 0:
            self.picamLib.Picam_GetParameterFloatingPointValue(self.cam, paramSensorTemperatureSetPoint, ctypes.byref(sensorSetPt))
            self.picamLib.Picam_ReadParameterIntegerValue(self.cam, paramSensorTemperatureStatus, ctypes.byref(sensorLockStatus))
            try:
                outStr = '%0.2fC (%s). Set Point %0.2fC'%(sensorTemp.value, tempStatus[sensorLockStatus.value], sensorSetPt.value)
            #handle case where camera gets shut off and an event handler is still trying to read this
            except KeyError:
                outStr = ''
            finally:
                if printString:
                    print('*****\nSensor Temperature %0.2fC (%s). Set Point %0.2fC.\n*****'%(sensorTemp.value, tempStatus[sensorLockStatus.value], sensorSetPt.value))
                return outStr
        else:
            return ''

    #-s mode, default saves to numpy array in memory, -d mode optionally write to disk (and not keep in memory)
    def Acquire(self,*,frames: int=1, bufNomWidth: int=50, saveDisk: bool=False, launchDisp: bool=False, queueTimes: bool=False):    #will launch the AcquireHelper function in a new thread when user calls it
        self.saveDisk = saveDisk
        frameCount = ctypes.c_int(0)
        frameCount.value = frames
        self.picamLib.Picam_SetParameterLargeIntegerValue(self.cam,paramFrames,frameCount)
        #0 is for infinite preview, don't allow for -s mode
        if self.Commit() and frameCount.value > 0:
            self.counter = 0
            #set up total data objects
            #self.totalData = np.zeros((frameCount.value,self.numRows,self.numCols))
            if self.saveDisk:
                #if saving to disk, just set up 1 dummy array for ROI info while parsing.
                self.SetupFullData(1)
                self.SetupMetaData()
                timeStr = time.strftime('%Y%d%m-%H%M%S',time.gmtime())
                #filename will have info for ROI 1 -- if multiple ROIs the dims will not apply
                self.filename = 'data' + timeStr + '-%dx%d-%d-%dbit.raw'%(np.shape(self.fullData[0])[2],np.shape(self.fullData[0])[1],frames,self.bits)
                self.fileHandle = open(self.filename, 'wb')
            else:
                self.SetupFullData(frames)
            if self.display:
                match self.dispType:
                    case 0:                        
                        SetupDisplay(self.numRows, self.numCols, self.windowName)
                    case 1:
                        self.ax, self.fig, self.artist, self.bg = SetupDisplayMPL(self.numRows, self.numCols, self.windowName)
                    case 3:
                        try:
                            self.figWindow.close()
                            del self.figWindow
                        except AttributeError:
                            pass
                        finally:
                            self.figWindow = ImageWindowMPL(self.numRows, self.numCols, self.windowName)
                            self.figWindow.InitializeLayout()
                            self.figWindow.show()
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
            metaThread = threading.Thread(target=WriteMeta, daemon=True, args=(self,))
            metaThread.start()
            #use launchDisp when running interactively -- in this case the calling thread will not return until acquisition stops.
            if launchDisp:
                self.DisplayCameraData()
            #this is a niche function I am using to export processing times into a queue.
            if queueTimes:
                timesThread = threading.Thread(target=QueueTimes, daemon=True, args=(self,))
                timesThread.start()

    #display will only show first ROI
    def DisplayCameraData(self):    #this will block and then unregister callback (if applicable) when done
        #do-while
        if self.dispType == 0:
            cv2.waitKey(100)
        else:
            time.sleep(0.1)
        runStatus = ctypes.c_bool(False)
        self.picamLib.Picam_IsAcquisitionRunning(self.cam, ctypes.byref(runStatus))
        self.runningStatus = runStatus
        while self.runningStatus:
            if self.display and len(self.newestFrame) > 0:
                with lock:
                    self.newestFrame = np.reshape(self.newestFrame, (self.numRows, self.numCols))
                match self.dispType:
                    case 0:
                        start = time.perf_counter_ns()
                        DisplayImage(self.newestFrame, self.windowName, self.bits)
                        end = time.perf_counter_ns() 
                        dispTime = (end-start)/1e6
                        #print('Display time: %0.3fms'%(dispTime))
                        if dispTime < 42:
                            cv2.waitKey(np.int32(42-dispTime)) #~24fps, if it can keep up
                    case 1:
                        start = time.perf_counter_ns()                        
                        DisplayImageMPL(self.newestFrame, self.windowName, self.bits, self.ax, self.fig, self.artist, self.bg)  
                        end = time.perf_counter_ns() 
                        dispTime = (end-start)/1e6
                        #print('Display time: %0.3fms'%(dispTime)) 
                        if dispTime < 42:
                            time.sleep((42-dispTime)/1000) #~24fps, if it can keep up
                    case 3:
                        start = time.perf_counter_ns()
                        self.figWindow.UpdateData(self.newestFrame)  
                        end = time.perf_counter_ns() 
                        dispTime = (end-start)/1e6
                        #print('Display time: %0.3fms'%(dispTime)) 
                        if dispTime < 42:
                            time.sleep((42-dispTime)/1000) #~24fps, if it can keep up
            #self.picamLib.Picam_IsAcquisitionRunning(self.cam, ctypes.byref(runStatus))
            #self.runningStatus = runStatus
        endTime = (time.perf_counter_ns()-self.acqTimer)/1e9
        print('Acquisition stopped. %d readouts obtained in %0.3fs (%0.3frps)'%(self.counter, endTime, self.counter/endTime))
        try:
            self.picamLib.PicamAdvanced_UnregisterForAcquisitionUpdated(self.dev, self.acqCallback)
        except:
            pass
        match self.dispType:
            case 0:
                cv2.waitKey(10000)
                cv2.destroyAllWindows()
            case 1:
                self.newestFrame = np.reshape(self.newestFrame, (self.numRows, self.numCols))
                DisplayImageMPL(self.newestFrame, self.windowName, self.bits, self.ax, self.fig, self.artist, self.bg)
                plt.show()      #blocks until display is closed.
            case 3:
                self.ReturnData()

    #since we're not saving data here, this is not generalized for multi-ROI -- the first ROI will be displayed
    #-p mode
    def AcquireCB(self,*,frames: int=5, bufNomWidth: int=50, launchDisp: bool=False, queueTimes: bool=False):    #utilizes Advanced API to demonstrate callbacks, returns immediately
        self.picamLib.PicamAdvanced_GetCameraDevice(self.cam, ctypes.byref(self.dev))
        frameCount = ctypes.c_int(0)
        frameCount.value = frames
        self.picamLib.Picam_SetParameterLargeIntegerValue(self.dev,paramFrames,frameCount)    #setting with dev handle commits to physical device if successful
        if self.Commit() and frameCount.value >= 0:
            self.CommitAndChange()
            if self.display:
                match self.dispType:
                    case 0:                        
                        SetupDisplay(self.numRows, self.numCols, self.windowName)
                    case 1:
                        self.ax, self.fig, self.artist, self.bg = SetupDisplayMPL(self.numRows, self.numCols, self.windowName)
                    case 3:
                        try:
                            self.figWindow.close()
                            del self.figWindow
                        except AttributeError:
                            pass
                        finally:
                            #self.displayItem = SetupDisplayPG(self.numRows, self.numCols, self.windowName)
                            #self.ax, self.fig, self.artist, self.bg = SetupDisplayMPL(self.numRows, self.numCols, self.windowName)
                            self.figWindow = ImageWindowMPL(self.numRows, self.numCols, self.windowName)
                            self.figWindow.InitializeLayout()
                            self.figWindow.show()
                            #pass
            self.counter = 0
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
            if not self.dispType == 3:
                stopThread = threading.Thread(target=Stop, daemon=True, args=(self,))
                stopThread.start()
            #use launchDisp when running interactively -- in this case the calling thread will not return until acquisition stops.
            if launchDisp:
                self.DisplayCameraData()
            #this is a niche function I am using to export processing times into a queue.
            if queueTimes:
                timesThread = threading.Thread(target=QueueTimes, daemon=True, args=(self,))
                timesThread.start()

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

    def TimeForFirstAcq(self, iters:np.int32=10):
        dat = availableData(0,0)
        aStatus=acqStatus(False,0,0)
        self.picamLib.Picam_SetParameterLargeIntegerValue(self.cam,paramFrames,1)
        self.Commit()       #my commit function puts readout rate into self.readRate
        for i in range(0,iters):
            start = time.perf_counter_ns()  #start timer right before 
            self.picamLib.Picam_StartAcquisition(self.cam)            
            self.picamLib.Picam_WaitForAcquisitionUpdate(self.cam,-1,ctypes.byref(dat),ctypes.byref(aStatus))
            while(aStatus.running):
                self.picamLib.Picam_WaitForAcquisitionUpdate(self.cam,-1,ctypes.byref(dat),ctypes.byref(aStatus))
            end = time.perf_counter_ns()    #end time after status is no longer running.
            totalElapsed = (end - start) /1e6   #elapsed time in ms
            acqDelay = totalElapsed - (1000/self.readRate.value)  #acquisition lag is the total elapsed time - expected readout time
            print('First acquisition delay: %0.3fms'%(acqDelay))
            time.sleep(5)   #sleep for 5 seconds before starting another acq -- put camera in clean mode

    def ReturnData(self):
        start = time.perf_counter_ns()
        q.join()
        if self.dispType == 3:
            if len(self.newestFrame) > 0:
                imFrame = np.reshape(self.newestFrame, (self.numRows, self.numCols))
                #make a subclass that fires an event to update the frame after this
                #self.figWindow.UpdateData(self.newestFrame)
                self.newestFrame = np.array([])       
        if self.saveDisk:
            self.fileHandle.close()
            #print('Disk writing lag: %0.2f ms'%((time.perf_counter_ns() - start)/1e6))
            qMeta.join()
            return 'Data saved to %s'%(self.filename)
        else:
            return self.fullData

    def ReturnTimeArray(self):
        qTimes.join()
        return self.processTimesArray

    def Close(self):
        dat = availableData(0,0)
        aStatus=acqStatus(False,0,0)        
        if self.runningStatus:
            self.picamLib.Picam_StopAcquisition(self.cam)
            while self.runningStatus:
                self.picamLib.Picam_WaitForAcquisitionUpdate(self.cam,-1,ctypes.byref(dat),ctypes.byref(aStatus))
                self.runningStatus = aStatus
        self.picamLib.Picam_CloseCamera(self.cam)
        self.picamLib.Picam_DisconnectDemoCamera(ctypes.byref(self.camID))
        #self.ResetCount()
        self.Uninitialize()
        print('PICam Uninitialized.')