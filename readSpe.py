# -*- coding: utf-8 -*-
"""
Created on Sat Dec  5 23:46:02 2020

@author: sabbi

usage of SpeReference class:
- import: from readSpe import SpeReference
- create reference to data with construction of class: img_reference = SpeReference(spe_file)
- when data is needed, call GetData: image = self.img_reference.GetData(frames=[idx], rois=[])[0][0]
----- that will get frame #idx in the first region into a numpy array
"""

import numpy as np
import xml.etree.ElementTree as ET
from collections.abc import (
    Sequence
)
from pathlib import PurePath
from typing import TypeAlias
from enum import (
    Enum,
    auto
)

setting_value_type: TypeAlias = np.uint64 | np.int64 | np.float64 | str
pixel_format: TypeAlias = str | int | None

class ROI():
    def __init__(self,width,height,stride):
        self._width=width
        self._height=height
        self._stride=stride
        self._X = 0
        self._Y = 0
        self._xbin = 1
        self._ybin = 1
    @property
    def width(self) -> int:
        return self._width
    @width.setter
    def width(self, val: int):
        self._width = val
    @property
    def height(self) -> int:
        return self._height
    @height.setter
    def height(self, val: int):
        self._height = val
    @property
    def stride(self) -> int:
        return self._stride
    @stride.setter
    def stride(self, val: int):
        self._stride = val
    @property
    def X(self) -> int:
        return self._X
    @X.setter
    def X(self, val: int):
        self._X = val
    @property
    def Y(self) -> int:
        return self._Y
    @Y.setter
    def Y(self, val: int):
        self._Y = val
    @property
    def xbin(self) -> int:
        return self._xbin
    @xbin.setter
    def xbin(self, val: int):
        self._xbin = val
    @property
    def ybin(self) -> int:
        return self._ybin
    @ybin.setter
    def ybin(self, val: int):
        self._ybin = val
    
    
    
        
class MetaContainer():
    def __init__(self,metaType,stride,*,metaEvent:str='',metaResolution:np.int64=0):
        self.metaType=metaType
        self.stride=stride
        self.metaEvent=metaEvent
        self.metaResolution=metaResolution

class Unit(Enum):
    NONE = auto
    MS = auto
    US = auto
    NM = auto
    MHz = auto
    DEGREES_CELSIUS = auto
    BITS = auto

class ExperimentSetting():
    def __init__(self, setting_name: str, setting_value: setting_value_type, setting_type: type, setting_unit: Unit) -> None:
        self._setting_name = setting_name
        self._setting_value = setting_value
        self._setting_type = setting_type
        self._setting_unit = setting_unit
    @property
    def setting_name(self) -> str:
        return self._setting_name
    @property
    def setting_value(self) -> setting_value_type:
        return self._setting_value
    @property
    def setting_type(self) -> type:
        return self._setting_type  
    @property
    def setting_unit(self) -> Unit:
        return self._setting_unit

#right now works with spe3 only
class SpeReference():
    @staticmethod
    def split_file_path(filepath: str) -> tuple[str, str, str]:
        p = PurePath(filepath)
        return (str(p.parents[0]), p.stem, p.suffix)
    dataTypes = {'MonochromeUnsigned16':np.uint16, 'MonochromeUnsigned32':np.uint32, 'MonochromeFloating32':np.float32}
    dataTypes_old_spe = {0:np.float32, 1:np.int32, 2:np.int16, 3:np.uint16, 5:np.float64, 6:np.uint8, 8:np.uint32}
    def __init__(self, filePath: str):
        self.filePath = filePath
        (self.file_directory, self.file_name, self.file_extension) = SpeReference.split_file_path(self.filePath)
        self.speVersion = 0
        self.roiList: list[ROI] = []
        self.readoutStride = 0
        self.numFrames = 0
        self.pixelFormat: pixel_format = None
        self.wavelength = []
        self.sensorDims = None
        self.metaList = []
        self.xmlFooter = ''
        self.InitializeSpe()

    def InitializeSpe(self):
        with open(self.filePath, encoding="utf8") as f:
            f.seek(678)
            self.xmlLoc = np.fromfile(f,dtype=np.uint64,count=1)[0]
            f.seek(1992)
            self.speVersion = np.fromfile(f,dtype=np.float32,count=1)[0]

            #get ROIs and shapes
            if self.speVersion==3:
                f.seek(self.xmlLoc)
                self.xmlFooter = f.read()
                xmlRoot = ET.fromstring(self.xmlFooter)
                for child in xmlRoot:
                    if 'DataFormat'.casefold() in child.tag.casefold():
                        for child1 in child:                    
                            if 'DataBlock'.casefold() in child1.tag.casefold():
                                self.readoutStride=np.uint64(child1.get('stride'))
                                self.numFrames=np.uint64(child1.get('count'))
                                self.pixelFormat=child1.get('pixelFormat')
                                for child2 in child1:
                                    if 'DataBlock'.casefold() in child1.tag.casefold():
                                        regStride=np.int64(child2.get('stride'))
                                        regWidth=np.int64(child2.get('width'))
                                        regHeight=np.int64(child2.get('height'))
                                        self.roiList.append(ROI(regWidth,regHeight,regStride))
                    if 'MetaFormat'.casefold() in child.tag.casefold():
                        for child1 in child:                    
                            if 'MetaBlock'.casefold() in child1.tag.casefold():
                                for child2 in child1:
                                    metaType = child2.tag.rsplit('}',maxsplit=1)[1]
                                    metaEvent = child2.get('event')
                                    metaStride = np.int64(np.int64(child2.get('bitDepth'))/8)
                                    metaResolution = child2.get('resolution')
                                    if metaEvent != None and metaResolution !=None:
                                        self.metaList.append(MetaContainer(metaType,metaStride,metaEvent=metaEvent,metaResolution=np.int64(metaResolution)))
                                    else:
                                        self.metaList.append(MetaContainer(metaType,metaStride))                                
                    if 'Calibrations'.casefold() in child.tag.casefold():
                        counter = 0
                        for child1 in child:
                            if 'WavelengthMapping'.casefold() in child1.tag.casefold():
                                for child2 in child1:
                                    if 'WavelengthError'.casefold() in child2.tag.casefold():
                                        wavelengths = np.array([])
                                        wlText = child2.text.rsplit()
                                        for elem in wlText:
                                            wavelengths = np.append(wavelengths,np.fromstring(elem,sep=',')[0])
                                        self.wavelength = wavelengths
                                    else:
                                        self.wavelength = np.fromstring(child2.text,sep=',')
                            if 'SensorInformation'.casefold() in child1.tag.casefold():
                                width = np.uint32(child1.get('width'))
                                height = np.uint32(child1.get('height'))
                                self.sensorDims= ROI(width, height, 0)
                            if 'SensorMapping'.casefold() in child1.tag.casefold():                                
                                if counter < len(self.roiList):
                                    self.roiList[counter].X = np.uint64(child1.get('x'))
                                    self.roiList[counter].Y = np.uint64(child1.get('y'))
                                    ogWidth = np.uint64(child1.get('width'))
                                    ogHeight = np.uint64(child1.get('height'))
                                    self.roiList[counter].xbin = np.uint64(child1.get('xBinning'))
                                    self.roiList[counter].ybin = np.uint64(child1.get('yBinning'))
                                    self.roiList[counter].width = np.uint64(ogWidth / self.roiList[counter].xbin)
                                    self.roiList[counter].height = np.uint64(ogHeight / self.roiList[counter].ybin)
                                    counter += 1
                                else:
                                    break   
            elif self.speVersion >=2 and self.speVersion <3:
                f.seek(108)
                self.pixelFormat=np.fromfile(f,dtype=np.int16,count=1)[0]
                f.seek(42)
                frameWidth=np.int32(np.fromfile(f,dtype=np.uint16,count=1)[0])
                f.seek(656)
                frameHeight=np.int32(np.fromfile(f,dtype=np.uint16,count=1)[0])
                f.seek(1446)
                self.numFrames=np.fromfile(f,dtype=np.int32,count=1)[0]
                stride = np.int32(frameHeight*frameWidth*np.dtype(self.dataTypes_old_spe[self.pixelFormat]).itemsize)
                self.roiList.append(ROI(frameWidth,frameHeight,stride))
            else:
                raise ValueError('Unrecognized spe file.')
                    

    def GetData(self,*,rois:Sequence[int], frames:Sequence[int]):
        dataList = list()
        #if no inputs, or empty list, set to all
        if len(rois) == 0:
            rois = np.arange(0,len(self.roiList))
        if len(frames) == 0:
            frames = np.arange(0,self.numFrames)
        #check for improper values, raise exception if necessary
        try:
            for item in rois:
                if item < 0 or item >= len(self.roiList):
                    raise ValueError('ROI value outside of allowed ranged (%d through %d)'%(0, len(self.roiList)-1))
        except TypeError:
            raise TypeError('ROI input needs to be iterable')
        try:
            for item in frames:
                if item < 0 or item >= self.numFrames:
                    raise ValueError('Frame value outside of allowed ranged (%d through %d)'%(0, self.numFrames-1))
        except TypeError:
            raise TypeError('Frame input needs to be iterable')
        if self.speVersion >= 3:           
            regionOffset=0
            with open(self.filePath, encoding="utf8") as f:            
                bpp = np.dtype(self.dataTypes[self.pixelFormat]).itemsize            
                for i in range(0,len(rois)):                
                    regionData = np.zeros([len(frames),self.roiList[rois[i]].height, self.roiList[rois[i]].width])
                    regionOffset = 0                
                    if rois[i]>0:
                        for ii in range(0,rois[i]):
                            regionOffset += np.uint64(self.roiList[ii].stride/bpp)                    
                    for j in range(0,len(frames)):
                        f.seek(0)                    
                        frameOffset = np.uint64(frames[j]*self.readoutStride/bpp)
                        readCount =  np.uint64(self.roiList[rois[i]].stride/bpp)
                        tmp = np.fromfile(f,dtype=self.dataTypes[self.pixelFormat],count=readCount,offset=np.uint64(4100+(regionOffset*bpp)+(frameOffset*bpp)))
                        regionData[j,:] = np.reshape(tmp,[self.roiList[rois[i]].height,self.roiList[rois[i]].width])
                    dataList.append(regionData)
        elif self.speVersion >=2 and self.speVersion <3:
            if len(rois) != 1 and rois[0] !=0:
                raise ValueError('Only one ROI allowed for spe v2 parsing.')
            with open(self.filePath, encoding="utf8") as f:
                bpp = np.dtype(self.dataTypes_old_spe[self.pixelFormat]).itemsize
                regionData = np.zeros([len(frames), self.roiList[0].height, self.roiList[0].width], dtype=self.dataTypes_old_spe[self.pixelFormat])     
                for j in range(0,len(frames)):
                    f.seek(0)
                    frameOffset = (self.roiList[0].stride) * frames[j]
                    tmp = np.fromfile(f,dtype=self.dataTypes_old_spe[self.pixelFormat],count=np.uint64(self.roiList[0].stride / bpp),offset=np.uint64(4100+frameOffset))
                    regionData[j] = np.reshape(tmp, [len(frames), self.roiList[0].height, self.roiList[0].width])
                dataList.append(regionData)        
        return dataList
    def GetWavelengths(self,*,rois:Sequence[int]):
        if self.speVersion < 3:
            print('Version %0.1f spe files do not have wavelength cal.'%(self.speVersion))
        if len(self.wavelength) == 0:
            return []
        else:
            if len(rois) == 0:
                rois = np.arange(0,len(self.roiList))
            try:
                for item in rois:
                    if item < 0 or item >= len(self.roiList):
                        raise ValueError('ROI value outside of allowed ranged (%d through %d)'%(0, len(self.roiList)-1))
            except TypeError:
                raise TypeError('ROI input needs to be iterable')
            
            ##if len(self.wavelength) == self.sensorDims.width:
            wavelengthList = []
            for item in rois:
                if self.roiList[item].width > 0:
                    wlIndex = np.arange(self.roiList[item].X,self.roiList[item].X+self.roiList[item].width,self.roiList[item].xbin,dtype=np.int32)
                    wavelengthList.append(self.wavelength[wlIndex])
                else:
                    wavelengthList.append(self.wavelength)
            return wavelengthList
            ##else:
                ##raise ValueError('Wavelength calibration was not performed with full ROI.')
    def GetCameraSettings(self) -> dict:
        '''
        Return a dictionary of useful camera settings
        Work in progress
        Current keys: exposure, analog_gain, adc_speed, sensor_temperature, camera_sn
        '''
        settings_dictionary = {
            'exposure': None,
            'analog_gain': None,
            'adc_speed': None,
            'sensor_temperature': None,
            'camera_info': None,
            'sensor_info': None
        }
        xmlRoot = ET.fromstring(self.xmlFooter)
        for child in xmlRoot:
            if 'DataHistories'.casefold() in child.tag.casefold():
                for child1 in child:
                    if 'DataHistory'.casefold() in child1.tag.casefold():
                        for child2 in child1:
                            if 'Origin'.casefold() in child2.tag.casefold():
                                for child3 in child2:
                                    if 'Experiment'.casefold() in child3.tag.casefold():
                                        for child4 in child3:                                            
                                            if 'Devices'.casefold() in child4.tag.casefold():
                                                for child2 in child4:
                                                    if 'Cameras'.casefold() in child2.tag.casefold():
                                                        for child3 in child2:
                                                            if 'Camera'.casefold() in child3.tag.casefold():
                                                                for child4 in child3:
                                                                    if 'ShutterTiming'.casefold() in child4.tag.casefold():
                                                                        for child5 in child4:
                                                                            if 'ExposureTime'.casefold() in child5.tag.casefold():
                                                                                settings_dictionary['exposure'] = np.float64(child5.text)
                                                                    if 'Adc'.casefold() in child4.tag.casefold():
                                                                        for child5 in child4:
                                                                            if 'Speed'.casefold() in child5.tag.casefold():
                                                                                if child5.get('relevance') != 'False':
                                                                                    settings_dictionary['adc_speed']=np.float64(child5.text)
                                                                            if 'AnalogGain'.casefold() in child5.tag.casefold():
                                                                                if child5.get('relevance') != 'False':
                                                                                    settings_dictionary['analog_gain']=child5.text
                                                                    if 'Sensor'.casefold() in child4.tag.casefold():
                                                                        for child5 in child4:
                                                                            if 'Temperature'.casefold() in child5.tag.casefold():
                                                                                for child6 in child5:
                                                                                    if 'Reading'.casefold() in child6.tag.casefold():
                                                                                        settings_dictionary['sensor_temperature']=np.float64(child6.text)
                                                                            if 'Information'.casefold() in child5.tag.casefold():
                                                                                for child6 in child5:
                                                                                    if 'SensorName'.casefold() in child6.tag.casefold():
                                                                                        settings_dictionary['sensor_info']=child6.text
                                            if 'System'.casefold() in child4.tag.casefold():
                                                for child2 in child4:
                                                    if 'Cameras'.casefold() in child2.tag.casefold():
                                                        for child3 in child2:
                                                            if 'Camera'.casefold() in child3.tag.casefold():
                                                                settings_dictionary['camera_info'] = '%s, SN: %s'%(child3.get('model'),child3.get('serialNumber'))
        return settings_dictionary
    def GenerateSettingsList(self) -> list[ExperimentSetting]:
        '''
        parse xml for key settings and output as a list of ExperimentSetting.
        settings to include are TBD
        list will include:
        - sensor name
        - camera model
        - camera serial number
        - exposure time
        - ADC Speed
        - ADC Analog gain
        - bit depth
        - readout time
        - shift rate
        - sensor temperature
        - number of ports used
        - x bin (region dependent, parse directly from region list when needed)
        - y bin (see above for x bin)
        '''
        experiment_settings_list = []

        #xml parsing
        xmlRoot = ET.fromstring(self.xmlFooter)
        for child in xmlRoot:
            if 'DataHistories'.casefold() in child.tag.casefold():
                for child1 in child:
                    if 'DataHistory'.casefold() in child1.tag.casefold():
                        for child2 in child1:
                            if 'Origin'.casefold() in child2.tag.casefold():
                                for child3 in child2:
                                    if 'Experiment'.casefold() in child3.tag.casefold():
                                        for child4 in child3:                                            
                                            if 'Devices'.casefold() in child4.tag.casefold():
                                                for child2 in child4:
                                                    if 'Cameras'.casefold() in child2.tag.casefold():
                                                        for child3 in child2:
                                                            if 'Camera'.casefold() in child3.tag.casefold():
                                                                for child4 in child3:
                                                                    if 'ShutterTiming'.casefold() in child4.tag.casefold():
                                                                        for child5 in child4:
                                                                            if 'ExposureTime'.casefold() in child5.tag.casefold():
                                                                                experiment_settings_list.append(ExperimentSetting('EXPOSURE_TIME',  np.float64(child5.text), np.float64, Unit.MS))
                                                                    if 'Adc'.casefold() in child4.tag.casefold():
                                                                        for child5 in child4:
                                                                            if 'Speed'.casefold() in child5.tag.casefold():
                                                                                if child5.get('relevance') != 'False':
                                                                                    experiment_settings_list.append(ExperimentSetting('ADC_SPEED',  np.float64(child5.text), np.float64, Unit.MHz))
                                                                            if 'AnalogGain'.casefold() in child5.tag.casefold():
                                                                                if child5.get('relevance') != 'False':
                                                                                    experiment_settings_list.append(ExperimentSetting('ADC_ANALOG_GAIN', str(child5.text), str, Unit.NONE))
                                                                            if 'BitDepth'.casefold() in child5.tag.casefold():
                                                                                experiment_settings_list.append(ExperimentSetting('BIT_DEPTH',  np.int64(child5.text), np.int64, Unit.BITS))
                                                                    if 'ReadoutControl'.casefold() in child4.tag.casefold():
                                                                        for child5 in child4:
                                                                            if 'Time'.casefold() in child5.tag.casefold():
                                                                                experiment_settings_list.append(ExperimentSetting('READOUT_TIME',  np.float64(child5.text), np.float64, Unit.MS))
                                                                            if 'VerticalShiftRate'.casefold() in child5.tag.casefold():
                                                                                if child5.get('relevance') != 'False':
                                                                                    experiment_settings_list.append(ExperimentSetting('VERTICAL_SHIFT_RATE',  np.float64(child5.text), np.float64, Unit.US))
                                                                            if 'PortsUsed'.casefold() in child5.tag.casefold():
                                                                                experiment_settings_list.append(ExperimentSetting('PORTS_USED',  np.int64(child5.text), np.int64, Unit.NONE))
                                                                    if 'Sensor'.casefold() in child4.tag.casefold():
                                                                        for child5 in child4:
                                                                            if 'Temperature'.casefold() in child5.tag.casefold():
                                                                                for child6 in child5:
                                                                                    if 'Reading'.casefold() in child6.tag.casefold():
                                                                                        experiment_settings_list.append(ExperimentSetting('SENSOR_TEMPERATURE',  np.float64(child6.text), np.float64, Unit.DEGREES_CELSIUS))
                                                                            if 'Information'.casefold() in child5.tag.casefold():
                                                                                for child6 in child5:
                                                                                    if 'SensorName'.casefold() in child6.tag.casefold():
                                                                                        experiment_settings_list.append(ExperimentSetting('SENSOR_INFORMATION', str(child6.text), str, Unit.NONE))
                                            if 'System'.casefold() in child4.tag.casefold():
                                                for child2 in child4:
                                                    if 'Cameras'.casefold() in child2.tag.casefold():
                                                        for child3 in child2:
                                                            if 'Camera'.casefold() in child3.tag.casefold():
                                                                experiment_settings_list.append(ExperimentSetting('CAMERA_MODEL', str(child3.get('model')), str, Unit.NONE))
                                                                experiment_settings_list.append(ExperimentSetting('SERIAL_NUMBER', str(child3.get('serialNumber')), str, Unit.NONE))
        #
        return experiment_settings_list
    def GenerateFitsFile(self) -> None:
        '''
        work in progress;
        generate a fits file using astropy library;
        experiment settings to carry over from spe xml to fits header are being considered for addition
        one file per ROI
        '''
        for region in self.roiList:
            if region.height < 1 or region.width < 1:
                raise ValueError('One or more region(s) of the spe file do not have valid data.')
        if self.speVersion >= 3:
            datatype: np.dtype = self.dataTypes[self.pixelFormat]
        else:
            datatype: np.dtype = self.dataTypes_old_spe[self.pixelFormat]
        from astropy.io import fits
        for i in range(0, len(self.roiList)):
            output_filepath = '%s\\%s-ROI%03d.fits'%(self.file_directory, self.file_name, i+1)
            region_data = np.zeros([self.numFrames, self.roiList[i].height, self.roiList[i].width], dtype=datatype)
            for j in range(0, self.numFrames):
                region_data[j] = self.GetData(rois=[i], frames=[j])[0]
            hdu = fits.PrimaryHDU(region_data)
            hdr = hdu.header
            #append experiment settings list to header
            experiment_settings_list = self.GenerateSettingsList()
            experiment_settings_list.append(ExperimentSetting('X_BIN', np.int64(self.roiList[i].xbin), np.int64, Unit.NONE))
            experiment_settings_list.append(ExperimentSetting('Y_BIN', np.int64(self.roiList[i].ybin), np.int64, Unit.NONE))
            for setting in experiment_settings_list:
                hdr['HIERARCH %s'%(setting.setting_name)] = setting.setting_value
            hdu.writeto(output_filepath, overwrite=True)