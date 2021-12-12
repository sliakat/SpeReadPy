#author: sabbi
#11/10/2021

import ctypes
import numpy as np
import os
import cv2
import threading

os.environ["GENICAM_ROOT_V2_4"] = "/opt/pleora/ebus_sdk/x86_64/lib/genicam/"	#declaration needed for Linux SDK

lock = threading.Lock()

def calcParam(v,c,n):
	return (((c)<<24)+((v)<<16)+(n))

#check picam.h for parameter definitions
paramFrames = ctypes.c_int(calcParam(6,2,40))
paramStride = ctypes.c_int(calcParam(1,1,45))
paramROIs = ctypes.c_int(calcParam(5, 4, 37))
paramReadRate=ctypes.c_int(calcParam(2,1,50))

#opencv related functions
def WindowSize(numRows,numCols):
	aspect = 1
	if numRows > 1080:
		aspect = int(numRows/1080)
	elif numCols > 1920:
		aspect = int(numCols/1920)
	winWidth = int(numCols/aspect)
	winHeight = int(numRows/aspect)
	return winWidth, winHeight

def SetupDisplay(numRows,numCols,windowName):        
	if numRows > 1:
		cv2.namedWindow(windowName,cv2.WINDOW_NORMAL)
		winWidth, winHeight = WindowSize(numRows, numCols)
		cv2.resizeWindow(windowName,winWidth,winHeight)

def DisplayImage(imData, windowName):		#data needs to be passed in correct shape
	normData = cv2.normalize(imData,None,alpha=0, beta=65535, norm_type=cv2.NORM_MINMAX)
	cv2.imshow(windowName, normData)
	cv2.waitKey(100)	#cap opencv refresh at 10fps for stability. May be able to keep up faster on higher powered machines.

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


class Camera(threading.Thread):
	def __init__(self,*,libPath: str='/usr/local/lib/libpicam.so'):	#class will instantiate and initialize PICam
		threading.Thread.__init__(self)
		self.cam = ctypes.c_void_p(0)
		self.camID = camIDStruct(0,0,b'',b'')
		self.numRows = ctypes.c_int(0)
		self.numCols = ctypes.c_int(0)
		self.readRate = ctypes.c_double(0)
		self.picamLib = ctypes.cdll.LoadLibrary(libPath)
		self.counter = 0
		self.totalData = np.array([])
		self.newestFrame = np.array([])
		self.rStride = ctypes.c_int(0)
		self.display = False
		self.runningStatus = ctypes.c_bool(False)
		self.windowName = ''
		self.Initialize()
		self.start()

	def AcquisitionUpdated(self, device, available, status):    
		with lock:
			if status.contents.running:				   
				self.newestFrame = self.ProcessData(available.contents, self.rStride.value, saveAll = False)				
		return 0
        
	def ResetCount(self):
		self.counter = 0
		self.totalData = np.array([])

	def Initialize(self):
		initCheck = ctypes.c_bool(0)
		self.picamLib.Picam_InitializeLibrary()
		self.picamLib.Picam_IsLibraryInitialized(ctypes.byref(initCheck))
		print('PICam Initialized: %r'%initCheck.value)

	def Uninitialize(self):
		self.picamLib.Picam_UninitializeLibrary()

	def GetFirstROI(self):
		rois = ctypes.c_void_p(0)		
		self.picamLib.Picam_GetParameterRoisValue(self.cam, paramROIs, ctypes.byref(rois))
		roisCast = ctypes.cast(rois,ctypes.POINTER(roisStruct))[0]
		roiCast = ctypes.cast(roisCast.roi_array,ctypes.POINTER(roiStruct))[0]	#take first ROI
		self.numCols = int(roiCast.width/roiCast.x_binning)
		self.numRows = int(roiCast.height/roiCast.y_binning)
		self.picamLib.Picam_DestroyRois(rois)
		if self.numRows > 1:
			self.display = True

	def Commit(self):
		paramArray = ctypes.pointer(ctypes.c_int(0))
		failedCount = ctypes.c_int(1)
		self.picamLib.Picam_CommitParameters(self.cam, ctypes.byref(paramArray), ctypes.byref(failedCount))
		if failedCount.value > 0:
			print('Failed to commit %d parameters. Cannot acquire.'%(failedCount.value))
			return False
		else:
			print('Commit successful!')
			return True

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

	def ProcessData(self, data, readStride,*,saveAll: bool=True):
		x=ctypes.cast(data.initial_readout,ctypes.POINTER(ctypes.c_uint16))
		for i in range(0,data.readout_count):	#readout by readout
			offset = int((i * readStride) / 2)
			readoutDat = np.asarray(x[offset:int(self.numCols*self.numRows + offset)],dtype=np.uint16)
			readoutDat = np.reshape(readoutDat, (self.numRows, self.numCols))
			if saveAll:
				self.totalData[(self.counter),:,:] = readoutDat
			#print(np.shape(self.totalData))
			self.counter += 1
			if i == data.readout_count-1:	#return most recent readout (normalized) to use for displaying
				return readoutDat

	def Acquire(self,*,frames: int=1):
		frameCount = ctypes.c_int(0)
		frameCount.value = frames
		self.picamLib.Picam_SetParameterLargeIntegerValue(self.cam,paramFrames,frameCount)
		if self.Commit():
			self.ResetCount()
			self.totalData = np.zeros((frameCount.value,self.numRows,self.numCols))
			self.picamLib.Picam_GetParameterFloatingPointValue(self.cam,paramReadRate,ctypes.byref(self.readRate))
			dat = availableData(0,0)
			aStatus=acqStatus(False,0,0)
			SetupDisplay(self.numRows, self.numCols, self.windowName)
			self.picamLib.Picam_GetParameterIntegerValue(self.cam, paramStride, ctypes.byref(self.rStride))
			self.picamLib.Picam_StartAcquisition(self.cam)
			print('Acquisition Started, %0.2f readouts/sec...'%self.readRate.value)
			#start a do-while
			self.picamLib.Picam_WaitForAcquisitionUpdate(self.cam,-1,ctypes.byref(dat),ctypes.byref(aStatus))
			imData = self.ProcessData(dat, self.rStride.value)
			if self.display:
				DisplayImage(imData, self.windowName)
			#while part
			while(aStatus.running):
				self.picamLib.Picam_WaitForAcquisitionUpdate(self.cam,-1,ctypes.byref(dat),ctypes.byref(aStatus))
				if dat.readout_count > 0:					
					imData = self.ProcessData(dat, self.rStride.value)
					if self.display:
						DisplayImage(imData, self.windowName)

			print('...Acquisiton Finished, %d readouts processed.'%(self.counter))
			if self.display:
				print('Viewer window will close in 20 secs. You can also press key after selecting viewer to exit.')
			cv2.waitKey(20000)
			cv2.destroyAllWindows()			
		return np.copy(np.reshape(self.totalData,(self.counter,self.numRows,self.numCols)))
    
	def AcquireCB(self,*,frames: int=5):	#utilizes Advanced API to demonstrate callbacks
		SetupDisplay(self.numRows, self.numCols, self.windowName)
		self.ResetCount()
		self.picamLib.Picam_GetParameterIntegerValue(self.cam, paramStride, ctypes.byref(self.rStride))
		dev = ctypes.c_void_p(0)
		self.picamLib.PicamAdvanced_GetCameraDevice(self.cam, ctypes.byref(dev))
		frameCount = ctypes.c_int(0)
		frameCount.value = frames
		self.picamLib.Picam_SetParameterLargeIntegerValue(dev,paramFrames,frameCount)	#setting with dev handle commits to physical device if successful
		self.totalData = np.zeros((frameCount.value,self.numRows,self.numCols))
		CMPFUNC = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_void_p, ctypes.POINTER(availableData), ctypes.POINTER(acqStatus))
		#lines for internal callback		
		acqCallback = CMPFUNC(self.AcquisitionUpdated)
		self.picamLib.PicamAdvanced_RegisterForAcquisitionUpdated(dev, acqCallback)
		self.picamLib.Picam_StartAcquisition(dev)
		#do-while
		cv2.waitKey(100)
		self.picamLib.Picam_IsAcquisitionRunning(self.cam, ctypes.byref(self.runningStatus))
		print('Acquisition of %d frames asynchronously started'%(frameCount.value))
		while self.runningStatus:
			self.picamLib.Picam_IsAcquisitionRunning(self.cam, ctypes.byref(self.runningStatus))
			if self.display and len(self.newestFrame) > 0:									
				DisplayImage(self.newestFrame, self.windowName)
		print('Acquisition stopped. %d readouts obtained from callback.'%(self.counter))
		self.picamLib.PicamAdvanced_UnregisterForAcquisitionUpdated(dev, acqCallback)
		cv2.waitKey(20000)
		#cv2.destroyAllWindows()

	def Close(self):
		self.picamLib.Picam_CloseCamera(self.cam)
		self.picamLib.Picam_DisconnectDemoCamera(ctypes.byref(self.camID))
		self.Uninitialize()
