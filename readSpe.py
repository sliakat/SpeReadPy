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
    Sequence,
    MutableSequence
)
from pathlib import PurePath
from typing import (
    TypeAlias,
    NewType
)
from enum import (
    Enum,
    auto
)
import os

setting_value_type: TypeAlias = np.uint64 | np.int64 | np.float64 | str
type_pixel_format: TypeAlias = str | int | None
meta_type: TypeAlias = np.int64 | np.float64
meta_type_dict = {'Int64': np.int64, 'Double': np.float64}

###
#typing
Frames = NewType('Frames', int)
Rows = NewType('Rows', int)
Cols = NewType('Cols', int)
Wavelengths = NewType('Wavelengths', float)
PixelDType: TypeAlias = np.dtype[np.uint16|np.uint32|np.float32]
WavelengthDType: TypeAlias = np.dtype[np.float64]
ImageShape: TypeAlias = tuple[Frames, Rows, Cols]
ImageNDArray: TypeAlias = np.ndarray[ImageShape, PixelDType]
LineShape: TypeAlias = tuple[Frames, Cols]
LineNDArray: TypeAlias = np.ndarray[LineShape, PixelDType]
SpeNDArray: TypeAlias = ImageNDArray | LineNDArray
WavelengthShape: TypeAlias = tuple[Wavelengths]
WavelengthNDArray: TypeAlias = np.ndarray[WavelengthShape, WavelengthDType]

class Unit(Enum):
    NONE = auto
    MS = auto
    US = auto
    NS = auto
    NM = auto
    MHz = auto
    DEGREES_CELSIUS = auto
    BITS = auto

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
        
#metadata objects
class Metadata():
    def __init__(self, event_name: str, datatype: str, bit_depth: np.uint64) -> None:
        self._meta_event = event_name
        self._datatype = meta_type_dict[datatype]
        self._bit_depth = bit_depth
    @property
    def meta_event(self) -> str:
        return self._meta_event
    @property
    def datatype(self) -> np.dtype:
        return self._datatype
    @property
    def bit_depth(self) -> np.uint64:
        return self._bit_depth
class TimeStamp(Metadata):
    _unit = Unit.MS
    def __init__(self, event_name: str, datatype: str, bit_depth: np.uint64, resolution: np.uint64, absolute_time: str) -> None:
        super().__init__(event_name, datatype, bit_depth)
        self._resolution = resolution
        self._absolute_time = absolute_time
    @property
    def resolution(self) -> np.uint64:
        return self._resolution
    @property
    def absolute_time(self) -> str:
        return self._absolute_time
    @property
    def unit(self) -> Unit:
        return self._unit
class FrameTrackingNumber(Metadata):
    def __init__(self, datatype: str, bit_depth: np.uint64) -> None:
        super().__init__('Frame Tracking Number', datatype, bit_depth)
class GateTrackimg(Metadata):
    _unit = Unit.NS
    def __init__(self, event_name: str, datatype: str, bit_depth: np.uint64, monotonic: bool) -> None:
        super().__init__(event_name, datatype, bit_depth)
        self._monotonic = monotonic
    @property
    def monotonic(self) -> bool:
        return self._monotonic
    @property
    def unit(self) -> Unit:
        return self._unit

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

class SpeReference():
    @staticmethod
    def split_file_path(filepath: str) -> tuple[str, str, str]:
        p = PurePath(filepath)
        return (str(p.parents[0]), p.stem, p.suffix)
    _dataTypes = {'MonochromeUnsigned16':np.uint16, 'MonochromeUnsigned32':np.uint32, 'MonochromeFloating32':np.float32}
    _dataTypes_old_spe = {0:np.float32, 1:np.int32, 2:np.int16, 3:np.uint16, 5:np.float64, 6:np.uint8, 8:np.uint32}

    ###to be populated by the self.initialize_spe
    _filepath: str
    _file_directory: str
    _file_name: str
    _file_extension: str
    _spe_version: float
    _roi_list: list[ROI]
    _readout_stride: int
    _frame_stride: int
    _num_frames: int
    _pixel_format_string: type_pixel_format
    _region_wavelengths: Sequence[WavelengthNDArray]
    _sensor_dims: ROI
    _meta_list: list[Metadata]
    _frame_metadata_values: list[list[meta_type]]
    _xml_footer: str
    def __init__(self, filePath: str):
        self._filepath = filePath
        (self._file_directory, self._file_name, self._file_extension) = SpeReference.split_file_path(self._filepath)
        self._roi_list = []
        self._region_wavelengths = []
        self._meta_list = []
        self._frame_metadata_values = []
        self.initialize_spe()

    def initialize_spe(self):
        with open(self._filepath, encoding="utf8") as f:
            f.seek(678)
            self.xmlLoc = np.fromfile(f,dtype=np.uint64,count=1)[0]
            f.seek(1992)
            self._spe_version = np.fromfile(f,dtype=np.float32,count=1)[0]

            #get ROIs and shapes
            if self._spe_version==3:
                f.seek(self.xmlLoc)
                self._xml_footer = f.read()
                xmlRoot = ET.fromstring(self._xml_footer)
                for child in xmlRoot:
                    if 'DataFormat'.casefold() in child.tag.casefold():
                        for child1 in child:                    
                            if 'DataBlock'.casefold() in child1.tag.casefold():
                                self._readout_stride=np.uint64(child1.get('stride'))
                                self._frame_stride = np.uint64(child1.get('size'))
                                self._num_frames=np.uint64(child1.get('count'))
                                self._pixel_format_string=child1.get('pixelFormat')
                                for child2 in child1:
                                    if 'DataBlock'.casefold() in child1.tag.casefold():
                                        regStride=np.int64(child2.get('stride'))
                                        regWidth=np.int64(child2.get('width'))
                                        regHeight=np.int64(child2.get('height'))
                                        self._roi_list.append(ROI(regWidth,regHeight,regStride))
                    if 'MetaFormat'.casefold() in child.tag.casefold():
                        for child1 in child:
                            if 'MetaBlock'.casefold() in child1.tag.casefold():
                                for child2 in child1:
                                    metaType: str = child2.tag.rsplit('}',maxsplit=1)[1]
                                    metaEvent: str = child2.get('event')
                                    metaDataType:str  = child2.get('type')
                                    metaBitDepth = np.uint64(child2.get('bitDepth'))                                    
                                    match metaType:
                                        case 'TimeStamp':
                                            metaResolution = np.uint64(child2.get('resolution'))
                                            metaAbsoluteTime:str = child2.get('absoluteTime')
                                            self._meta_list.append(TimeStamp(metaEvent, metaDataType, metaBitDepth, metaResolution, metaAbsoluteTime))
                                        case 'FrameTrackingNumber':
                                            self._meta_list.append(FrameTrackingNumber(metaDataType, metaBitDepth))
                                        case 'GateTracking':
                                            metaEvent: str = child2.get('component')
                                            metaMonotonic = bool(child2.get('monotonic'))
                                            self._meta_list.append(GateTrackimg(metaEvent, metaDataType, metaBitDepth, metaMonotonic))
                                        case _:
                                            raise RuntimeError('Metadata block was not recognized.')

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
                                        self._region_wavelengths = wavelengths
                                    else:
                                        self._region_wavelengths = np.fromstring(child2.text,sep=',')
                            if 'SensorInformation'.casefold() in child1.tag.casefold():
                                width = np.int32(child1.get('width'))
                                height = np.uint32(child1.get('height'))
                                self._sensor_dims= ROI(width, height, 0)
                            if 'SensorMapping'.casefold() in child1.tag.casefold():                                
                                if counter < len(self._roi_list):
                                    self._roi_list[counter].X = np.uint64(child1.get('x'))
                                    self._roi_list[counter].Y = np.uint64(child1.get('y'))
                                    ogWidth = np.uint64(child1.get('width'))
                                    ogHeight = np.uint64(child1.get('height'))
                                    self._roi_list[counter].xbin = np.uint64(child1.get('xBinning'))
                                    self._roi_list[counter].ybin = np.uint64(child1.get('yBinning'))
                                    self._roi_list[counter].width = np.uint64(ogWidth / self._roi_list[counter].xbin)
                                    self._roi_list[counter].height = np.uint64(ogHeight / self._roi_list[counter].ybin)
                                    counter += 1
                                else:
                                    break
                #now that xml parsing is done, extract all the metadata (if present)
                if len(self._meta_list) > 0:
                    self._frame_metadata_values = [0] * self._num_frames
                    for i in range(0, self._num_frames):
                        self._frame_metadata_values[i] = self.GetFrameMetaDataValue([i])

            elif self._spe_version >=2 and self._spe_version <3:
                self._xml_footer = ''
                f.seek(108)
                self._pixel_format_string=np.fromfile(f,dtype=np.int16,count=1)[0]
                f.seek(42)
                frameWidth=np.int32(np.fromfile(f,dtype=np.uint16,count=1)[0])
                f.seek(656)
                frameHeight=np.int32(np.fromfile(f,dtype=np.uint16,count=1)[0])
                f.seek(1446)
                self._num_frames=np.fromfile(f,dtype=np.int32,count=1)[0]
                stride = np.int32(frameHeight*frameWidth*np.dtype(self._dataTypes_old_spe[self._pixel_format_string]).itemsize)
                self._roi_list.append(ROI(frameWidth,frameHeight,stride))
            else:
                raise ValueError('Unrecognized spe file.')
                    

    def GetData(self,*,rois:Sequence[int], frames:Sequence[int]) -> Sequence[SpeNDArray]:
        dataList = list()
        #if no inputs, or empty list, set to all
        if len(rois) == 0:
            rois = range(0,len(self._roi_list))
        if len(frames) == 0:
            frames = range(0,self._num_frames)
        #check for improper values, raise exception if necessary
        try:
            for item in rois:
                if item < 0 or item >= len(self._roi_list):
                    raise ValueError('ROI value outside of allowed ranged (%d through %d)'%(0, len(self._roi_list)-1))
        except TypeError:
            raise TypeError('ROI input needs to be iterable')
        try:
            for item in frames:
                if item < 0 or item >= self._num_frames:
                    raise ValueError('Frame value outside of allowed ranged (%d through %d)'%(0, self._num_frames-1))
        except TypeError:
            raise TypeError('Frame input needs to be iterable')
        if self._spe_version >= 3:           
            regionOffset=0
            with open(self._filepath, encoding="utf8") as f:            
                bpp = np.dtype(self._dataTypes[self._pixel_format_string]).itemsize            
                for i in range(0,len(rois)):                
                    regionData = np.zeros([len(frames),self._roi_list[rois[i]].height, self._roi_list[rois[i]].width])
                    regionOffset = 0                
                    if rois[i]>0:
                        for ii in range(0,rois[i]):
                            regionOffset += np.uint64(self._roi_list[ii].stride/bpp)                    
                    for j in range(0,len(frames)):
                        f.seek(0)                    
                        frameOffset = np.uint64(frames[j]*self._readout_stride/bpp)
                        readCount =  np.uint64(self._roi_list[rois[i]].stride/bpp)
                        tmp = np.fromfile(f,dtype=self._dataTypes[self._pixel_format_string],count=readCount,offset=np.uint64(4100+(regionOffset*bpp)+(frameOffset*bpp)))
                        regionData[j,:] = np.reshape(tmp,[self._roi_list[rois[i]].height,self._roi_list[rois[i]].width])
                    dataList.append(regionData)
        elif self._spe_version >=2 and self._spe_version <3:
            if len(rois) != 1 and rois[0] !=0:
                raise ValueError('Only one ROI allowed for spe v2 parsing.')
            with open(self._filepath, encoding="utf8") as f:
                bpp = np.dtype(self._dataTypes_old_spe[self._pixel_format_string]).itemsize
                regionData = np.zeros([len(frames), self._roi_list[0].height, self._roi_list[0].width], dtype=self._dataTypes_old_spe[self._pixel_format_string])     
                for j in range(0,len(frames)):
                    f.seek(0)
                    frameOffset = (self._roi_list[0].stride) * frames[j]
                    tmp = np.fromfile(f,dtype=self._dataTypes_old_spe[self._pixel_format_string],count=np.uint64(self._roi_list[0].stride / bpp),offset=np.uint64(4100+frameOffset))
                    regionData[j] = np.reshape(tmp, [len(frames), self._roi_list[0].height, self._roi_list[0].width])
                dataList.append(regionData)        
        return dataList
    def GetWavelengths(self,*,rois:Sequence[int]) -> Sequence[WavelengthNDArray]:
        if self._spe_version < 3:
            print('Version %0.1f spe files do not have wavelength cal.'%(self._spe_version))
        if len(self._region_wavelengths) == 0:
            return []
        else:
            if len(rois) == 0:
                rois = range(0,len(self._roi_list))
            try:
                for item in rois:
                    if item < 0 or item >= len(self._roi_list):
                        raise ValueError('ROI value outside of allowed ranged (%d through %d)'%(0, len(self._roi_list)-1))
            except TypeError:
                raise TypeError('ROI input needs to be iterable')
            
            ##if len(self.wavelength) == self.sensorDims.width:
            wavelengthList = []
            for item in rois:
                if self._roi_list[item].width > 0:
                    wlIndex = np.arange(self._roi_list[item].X,self._roi_list[item].X+self._roi_list[item].width,self._roi_list[item].xbin,dtype=np.int32)
                    wavelengthList.append(self._region_wavelengths[wlIndex])
                else:
                    wavelengthList.append(self._region_wavelengths)
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
        xmlRoot = ET.fromstring(self._xml_footer)
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
        xmlRoot = ET.fromstring(self._xml_footer)
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

    def GetFrameMetaDataValue(self, frames: Sequence[int]) -> Sequence[Sequence[meta_type]]:
        output_metadata = [0] * len(frames)
        with open(self._filepath, encoding="utf8") as f:
            for i in range(0, len(frames)):                
                output_metadata[i] = [0] * len(self._meta_list)
                readout_offset = frames[i] * self._readout_stride
                metadata_offset = int(readout_offset + self._frame_stride)
                for j in range(0, len(self._meta_list)):
                    f.seek(0)                    
                    if j > 0:
                        metadata_offset += int((self._meta_list[j-1].bit_depth) / 8)
                    meta_length = np.dtype(self._meta_list[j].datatype).itemsize // int((self._meta_list[j-1].bit_depth) / 8)
                    output_metadata[i][j] = np.fromfile(f, dtype=self._meta_list[j].datatype, count=meta_length, offset=int(4100+metadata_offset))[0]
                    if type(self._meta_list[j]) == TimeStamp:
                        output_metadata[i][j] = (output_metadata[i][j] / self._meta_list[j].resolution) * 1000
        return output_metadata


class Fits():
    @staticmethod
    def GenerateFitsFile(spe_ref: SpeReference) -> None:
        '''
        work in progress;
        generate a fits file using astropy library;
        experiment settings to carry over from spe xml to fits header are being considered for addition
        one file per ROI
        frame metadata not included -- use GenerateFitsFiles for that
        '''
        for region in spe_ref._roi_list:
            if region.height < 1 or region.width < 1:
                raise ValueError('One or more region(s) of the spe file do not have valid data.')
        if spe_ref._spe_version >= 3:
            datatype: np.dtype = spe_ref._dataTypes[spe_ref._pixel_format_string]
        else:
            datatype: np.dtype = spe_ref._dataTypes_old_spe[spe_ref._pixel_format_string]
        from astropy.io import fits
        for i in range(0, len(spe_ref._roi_list)):
            output_filepath = '%s\\%s-ROI%03d.fits'%(spe_ref._file_directory, spe_ref._file_name, i+1)
            region_data = np.zeros([spe_ref._num_frames, spe_ref._roi_list[i].height, spe_ref._roi_list[i].width], dtype=datatype)
            for j in range(0, spe_ref._num_frames):
                region_data[j] = spe_ref.GetData(rois=[i], frames=[j])[0]
            hdu = fits.PrimaryHDU(region_data)
            hdr = hdu.header
            #append experiment settings list to header
            experiment_settings_list = spe_ref.GenerateSettingsList()
            experiment_settings_list.append(ExperimentSetting('X_BIN', np.int64(spe_ref._roi_list[i].xbin), np.int64, Unit.NONE))
            experiment_settings_list.append(ExperimentSetting('Y_BIN', np.int64(spe_ref._roi_list[i].ybin), np.int64, Unit.NONE))
            for setting in experiment_settings_list:
                hdr['HIERARCH %s'%(setting.setting_name)] = setting.setting_value
            hdu.writeto(output_filepath, overwrite=True)
    @staticmethod
    def GenerateFitsFiles(spe_ref:SpeReference) -> None:
        '''
        see docstring for GenerateFitsFile
        difference here is a new directory will be created and have 1 fits file per ROI per frame
        frame metadata for exposure started timestamp will be present in the header of each file (if exists in the spe)
        '''
        for region in spe_ref._roi_list:
            if region.height < 1 or region.width < 1:
                raise ValueError('One or more region(s) of the spe file do not have valid data.')
        if spe_ref._spe_version >= 3:
            datatype: np.dtype = spe_ref._dataTypes[spe_ref._pixel_format_string]
        else:
            datatype: np.dtype = spe_ref._dataTypes_old_spe[spe_ref._pixel_format_string]
        from astropy.io import fits
        new_folder_path = '%s\\%s-fits\\'%(spe_ref._file_directory, spe_ref._file_name)
        if not os.path.exists(new_folder_path):
            os.mkdir(new_folder_path)
        for i in range(0, len(spe_ref._roi_list)):
            for j in range(0, spe_ref._num_frames):
                output_filepath = '%s\\%s-ROI%03d-Frame%04d.fits'%(new_folder_path, spe_ref._file_name, i+1, j+1)
                file_data = spe_ref.GetData(rois=[i], frames=[j])[0]
                frame_metadata = spe_ref.GetFrameMetaDataValue([j])[0]
                hdu = fits.PrimaryHDU(file_data)
                hdr = hdu.header
                #add time stamps to header if they exist
                if len(spe_ref._meta_list) > 0:
                    count = 0
                    for meta in spe_ref._meta_list:
                        if type(meta) == TimeStamp:
                            if meta.meta_event == 'ExposureStarted':
                                hdr['HIERARCH ACQUISITION_ORIGIN'] = meta.absolute_time
                                hdr['HIERARCH FRAME_EXPOSURE_STARTED_OFFSET_MS'] = frame_metadata[count]
                        count += 1
                #append experiment settings list to header
                experiment_settings_list = spe_ref.GenerateSettingsList()
                experiment_settings_list.append(ExperimentSetting('X_BIN', np.int64(spe_ref._roi_list[i].xbin), np.int64, Unit.NONE))
                experiment_settings_list.append(ExperimentSetting('Y_BIN', np.int64(spe_ref._roi_list[i].ybin), np.int64, Unit.NONE))
                for setting in experiment_settings_list:
                    hdr['HIERARCH %s'%(setting.setting_name)] = setting.setting_value
                hdu.writeto(output_filepath, overwrite=True)
    