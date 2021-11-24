#author: sabbi
#11/10/2021

import ctypes
import numpy as np
import threading
import sys
import os
import cv2

os.environ["GENICAM_ROOT_V2_4"] = "/opt/pleora/ebus_sdk/x86_64/lib/genicam/"

def calcParam(v,c,n):
	return (((c)<<24)+((v)<<16)+(n))

#check picam.h for parameter definitions
paramFrames = ctypes.c_int(calcParam(6,2,40))
paramStride = ctypes.c_int(calcParam(1,1,45))
paramROIs = ctypes.c_int(calcParam(5, 4, 37))
paramReadRate=ctypes.c_int(calcParam(2,1,50))

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


class Camera:
	def __init__(self,*,libPath: str='/usr/local/lib/libpicam.so'):	#class will instantiate and initialize PICam
		self.cam = ctypes.c_void_p(0)
		self.camID = camIDStruct(0,0,b'',b'')
		self.numRows = ctypes.c_int(0)
		self.numCols = ctypes.c_int(0)
		self.readRate = ctypes.c_double(0)
		self.picamLib = ctypes.cdll.LoadLibrary(libPath)
		self.counter = 0
		self.totalData = np.zeros(0)
		self.Initialize()

	def ResetCount(self):
		self.counter = 0
		self.totalData = np.zeros(0)

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
		print('Camera Sensor: %s, Serial #: %s'%(self.camID.sensor_name.decode('utf-8'),self.camID.serial_number.decode('utf-8')))
		self.GetFirstROI()
		print('\tFirst ROI: %d (cols) x %d (rows)'%(self.numCols,self.numRows))

	def ProcessData(self,data, readStride, dispBool):
		x=ctypes.cast(data.initial_readout,ctypes.POINTER(ctypes.c_uint16))
		for i in range(0,data.readout_count):	#readout by readout
			offset = int((i * readStride) / 2)
			readoutDat = np.asarray(x[offset:int(self.numCols*self.numRows + offset)],dtype=np.uint16)
			self.counter += 1
			self.totalData = np.append(self.totalData,readoutDat)
			if i == data.readout_count-1:
				if dispBool:	#display only every 5 for more stability
					#pass
					normImg = cv2.normalize(np.reshape(readoutDat,(self.numRows,self.numCols)),None,alpha=0, beta=65535, norm_type=cv2.NORM_MINMAX)
					cv2.imshow("Frame", normImg)
					cv2.waitKey(50)

	def Acquire(self,*,frames: int=1):
		display = False
		frameCount = ctypes.c_int(0)
		frameCount.value = frames
		self.picamLib.Picam_SetParameterLargeIntegerValue(self.cam,paramFrames,frameCount)
		if self.Commit():
			self.ResetCount()
			self.picamLib.Picam_GetParameterFloatingPointValue(self.cam,paramReadRate,ctypes.byref(self.readRate))
			dat = availableData(0,0)
			aStatus=acqStatus(False,0,0)
			rStride = ctypes.c_int(0)
			self.picamLib.Picam_GetParameterIntegerValue(self.cam, paramStride, ctypes.byref(rStride))
			if self.numRows > 1:
				display = True				
			else:
				print('**Note: will not live display line plot.**')
			self.picamLib.Picam_StartAcquisition(self.cam)
			print('Acquisition Started, %0.2f readouts/sec...'%self.readRate.value)
			#start a do-while
			self.picamLib.Picam_WaitForAcquisitionUpdate(self.cam,-1,ctypes.byref(dat),ctypes.byref(aStatus))
			self.ProcessData(dat, rStride.value, display)
			#while part
			while(aStatus.running):
				self.picamLib.Picam_WaitForAcquisitionUpdate(self.cam,-1,ctypes.byref(dat),ctypes.byref(aStatus))
				if dat.readout_count > 0:					
					self.ProcessData(dat, rStride.value, display)
			print('...%d readouts processed.'%(self.counter))
			cv2.waitKey(20000)				
		return np.copy(np.reshape(self.totalData,(self.counter,self.numRows,self.numCols)))

	def Close(self):
		self.picamLib.Picam_CloseCamera(self.cam)
		self.picamLib.Picam_DisconnectDemoCamera(ctypes.byref(self.camID))
		self.Uninitialize()
