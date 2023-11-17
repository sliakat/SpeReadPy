# -*- coding: utf-8 -*-
"""
Created on Sat Dec  5 23:46:02 2020

@author: sabbi

Class and methods that facilitate reading of data, metadata, and
experiment settings from spe files.

Full functionality with spe version 3.0+; for older versions
(i.e. spe2.x), data from single ROIs can be extracted.

Example usage of SpeReference class:
- import: `from read_spe import SpeReference`
- create reference to data with construction of class:
`img_reference = SpeReference(spe_file)`
- to pull data, call get_data:
`image = img_reference.get_data(frames=[idx], rois=[])[0][0]`
----- that will get frame #idx in the first region into a numpy array
- to get an experiment setting, call retrieve_experiment_settings:
`exposure_time = img_reference.retrieve_experiment_settings(
['EXPOSURE_TIME'])[0].setting_value`

"""

#pylint: disable=consider-using-f-string

import xml.etree.ElementTree as ET
import xml.dom.minidom as md
from collections.abc import Sequence
from pathlib import Path, PurePath
from typing import TypeAlias, NewType, Optional, cast
from enum import Enum, auto
import numpy as np

SettingValueType: TypeAlias = np.uint64 | np.int64 | np.float64 | str
PixelFormatKeyType: TypeAlias = str | int
MetaType: TypeAlias = np.int64 | np.float64
meta_type_dict = {'Int64': np.int64, 'Double': np.float64}

###
#typing
Frames = NewType('Frames', int)
Rows = NewType('Rows', int)
Cols = NewType('Cols', int)
Wavelengths = NewType('Wavelengths', float)
PixelDtype: TypeAlias = np.dtype[np.uint16|np.uint32|np.float32]
NumpyInteger: TypeAlias = np.uint16|np.uint32|np.uint64|np.int16|\
    np.int32|np.int64
WavelengthDtype: TypeAlias = np.dtype[np.float64]
ImageShape: TypeAlias = tuple[Frames, Rows, Cols]
ImageNdArray: TypeAlias = np.ndarray[ImageShape, PixelDtype]
LineShape: TypeAlias = tuple[Frames, Cols]
LineNdArray: TypeAlias = np.ndarray[LineShape, PixelDtype]
SpeNdArray: TypeAlias = ImageNdArray
WavelengthShape: TypeAlias = tuple[Wavelengths]
WavelengthNdArray: TypeAlias = np.ndarray[WavelengthShape, WavelengthDtype]

class _Unit(Enum):
    NONE = auto()
    MS = auto()
    US = auto()
    NS = auto()
    UM = auto()
    NM = auto()
    MHZ = auto()
    DEGREES_CELSIUS = auto()
    BITS = auto()

class _ROI():
    def __init__(self,width,height,stride):
        self._width=width
        self._height=height
        self._stride=stride
        self._x = 0
        self._y = 0
        self._xbin = 1
        self._ybin = 1
    @property
    def width(self) -> int:
        '''width of region'''
        return self._width
    @width.setter
    def width(self, val: int):
        self._width = val
    @property
    def height(self) -> int:
        '''height of region'''
        return self._height
    @height.setter
    def height(self, val: int):
        self._height = val
    @property
    def stride(self) -> int:
        '''readout stride of region (bytes)'''
        return self._stride
    @stride.setter
    def stride(self, val: int):
        self._stride = val
    @property
    def x(self) -> int:
        '''x position of upper-left pixel in region'''
        return self._x
    @x.setter
    def x(self, val: int):
        self._x = val
    @property
    def y(self) -> int:
        '''y position of upper-left pixel in region'''
        return self._y
    @y.setter
    def y(self, val: int):
        self._y = val
    @property
    def xbin(self) -> int:
        '''number of binned columns in region'''
        return self._xbin
    @xbin.setter
    def xbin(self, val: int):
        self._xbin = val
    @property
    def ybin(self) -> int:
        '''number of binned rows in region'''
        return self._ybin
    @ybin.setter
    def ybin(self, val: int):
        self._ybin = val
    def __eq__(self, compare_to: type['_ROI']) -> bool:
        if self.x == compare_to.x and\
        self.y == compare_to.y and\
        self.width == compare_to.width and\
        self.height == compare_to.height and\
        self.xbin == compare_to.xbin and\
        self.ybin == compare_to.ybin:
            return True
        else:
            return False

#metadata objects
class Metadata():
    '''Base class for metadata objects. Derived classes contain more specific
    members pertaining to the metadata content.
    '''
    def __init__(self, event_name: str, datatype: str,
                 bit_depth: np.uint64) -> None:
        self._meta_event = event_name
        self._datatype = meta_type_dict[datatype]
        self._bit_depth = bit_depth
    @property
    def meta_event(self) -> str:
        '''Metadata event name, pulled from spe xml footer.'''
        return self._meta_event
    @property
    def datatype(self) -> np.dtype:
        '''numpy dtype of the metadata value'''
        return self._datatype
    @property
    def bit_depth(self) -> np.uint64:
        '''bit depth of the metadata value'''
        return self._bit_depth

class TimeStamp(Metadata):
    '''Contains resolution, unit, and origin information for
    TimeStamp metadata
    '''
    _unit = _Unit.MS
    def __init__(self, event_name: str, datatype: str, bit_depth: np.uint64,
                resolution: np.uint64, absolute_time: str) -> None:
        super().__init__(event_name, datatype, bit_depth)
        self._resolution = resolution
        self._absolute_time = absolute_time
    @property
    def resolution(self) -> np.uint64:
        '''tick resolution'''
        return self._resolution
    @property
    def absolute_time(self) -> str:
        '''origin in ISO format'''
        return self._absolute_time
    @property
    def unit(self) -> _Unit:
        '''unit for values'''
        return self._unit

class FrameTrackingNumber(Metadata):
    '''Frame tracking number metadata'''
    def __init__(self, datatype: str, bit_depth: np.uint64) -> None:
        super().__init__('Frame Tracking Number', datatype, bit_depth)

class GateTracking(Metadata):
    '''Used for ICCDs and EMiCCDs'''
    _unit = _Unit.NS
    def __init__(self, event_name: str, datatype: str, bit_depth: np.uint64,
                 monotonic: bool) -> None:
        super().__init__(event_name, datatype, bit_depth)
        self._monotonic = monotonic
    @property
    def monotonic(self) -> bool:
        '''Is the gate being tracked monotonic?'''
        return self._monotonic
    @property
    def unit(self) -> _Unit:
        '''unit for values'''
        return self._unit

class ExperimentSetting():
    '''Contains experiment setting information parsed from the spe file's
    xml footer.

    --------------------------------------------------------------------------
    Inputs (for constructor):
    --------------------------------------------------------------------------
    - `setting_name`: string denoting the name of the setting.
    - `setting_value`: value of the named setting
    - `setting_type`: reference to setting's datatype
    - `unit`: uint64, int64, float64, or str
    '''
    def __init__(self, setting_name: str, setting_value: SettingValueType,
                 setting_type: type, setting_unit: _Unit) -> None:
        self._setting_name = setting_name
        self._setting_value = setting_value
        self._setting_type = setting_type
        self._setting_unit = setting_unit
    @property
    def setting_name(self) -> str:
        '''Name of experiment setting. '''
        return self._setting_name
    @property
    def setting_value(self) -> SettingValueType:
        '''Value of setting. Check units with `setting_unit`.'''
        return self._setting_value
    @property
    def setting_type(self) -> type:
        '''Data type of setting.'''
        return self._setting_type
    @property
    def setting_unit(self) -> _Unit:
        '''Unit of setting.'''
        return self._setting_unit

class SpeReference():
    '''Facilitates reading of data, metadata, and experiment settings
    from spe files.

    Full functionality with spe version 3.0+; for older versions
    (i.e. spe2.x), data from single ROIs can be extracted.

    --------------------------------------------------------------------------

    Example usage of SpeReference class:
    - import:
    
    `from readSpe import SpeReference`
    - create reference to data with construction of class:

    `img_reference = SpeReference(spe_file)`
    - to pull data, call get_data:

    `image = img_reference.get_data(frames=[idx], rois=[])[0][0]`
    ----- that will get frame #idx in the first region into a numpy array
    - to get an experiment setting, call retrieve_experiment_settings:

    `exposure_time_ms = img_reference.retrieve_experiment_settings(
    ['EXPOSURE_TIME'])[0].setting_value`
    ----------------------------------------------------------------------
    See Also:
    ----------------------------------------------------------------------
    - `read_spe.SpeReference.get_data`
    - `read_spe.SpeReference.get_wavelengths`
    - `read_spe.SpeReference.retrieve_experiment_settings`
    '''
    @staticmethod
    def _split_file_path(filepath: str) -> tuple[str, str, str]:
        '''Helper for splitting file path'''
        p = PurePath(filepath)
        return (str(p.parents[0]), p.stem, p.suffix)
    dataTypes = {'MonochromeUnsigned16':np.uint16,
                  'MonochromeUnsigned32':np.uint32,
                  'MonochromeFloating32':np.float32}
    dataTypes_old_spe = {0:np.float32, 1:np.int32, 2:np.int16, 3:np.uint16,
                          5:np.float64, 6:np.uint8, 8:np.uint32}
    ###to be populated by the self._initialize_spe
    _filepath: str
    _file_directory: str
    _file_name: str
    _file_extension: str
    _spe_version: float
    _roi_list: list[_ROI]
    _readout_stride: NumpyInteger
    _frame_stride: NumpyInteger
    _num_frames: NumpyInteger
    _pixel_format_key: PixelFormatKeyType
    _full_wavelength_coverage: WavelengthNdArray
    _sensor_dims: _ROI
    _meta_list: list[Metadata]
    _frame_metadata_values: Sequence[Sequence[MetaType]]
    _xml_footer: str
    def __init__(self, filepath: str):
        self._filepath = filepath
        (self._file_directory, self._file_name, self._file_extension)\
            = SpeReference._split_file_path(self._filepath)
        if self._file_extension.casefold() != '.spe':
            raise ValueError('Input filepath does not have a .spe extension.')
        self._roi_list = []
        self._full_wavelength_coverage = np.array([])
        self._meta_list = []
        self._frame_metadata_values = []
        self._initialize_spe()

    def _initialize_spe(self):
        '''Fills in members with info from spe file (if that info exists).
        Should always be called internally.
        '''
        with open(self._filepath, encoding="utf8") as f:
            f.seek(678)
            self.xml_loc = np.fromfile(f,dtype=np.uint64,count=1)[0]
            f.seek(1992)
            self._spe_version = np.fromfile(f,dtype=np.float32,count=1)[0]

            #get ROIs and shapes
            #pylint: disable=line-too-long
            if self._spe_version==3:
                f.seek(self.xml_loc)
                self._xml_footer = f.read()
                xml_root = ET.fromstring(self._xml_footer)
                for child in xml_root:
                    if 'DataFormat'.casefold() in child.tag.casefold():
                        for child1 in child:
                            if 'DataBlock'.casefold() in child1.tag.casefold():
                                self._readout_stride=np.uint64(child1.get('stride')) # type: ignore
                                self._frame_stride = np.uint64(child1.get('size')) # type: ignore
                                self._num_frames=np.uint64(child1.get('count')) # type: ignore
                                self._pixel_format_key=child1.get('pixelFormat')# type: ignore
                                for child2 in child1:
                                    if 'DataBlock'.casefold() in child1.tag.casefold():
                                        reg_stride=np.int64(child2.get('stride')) # type: ignore
                                        reg_width=np.int64(child2.get('width')) # type: ignore
                                        reg_height=np.int64(child2.get('height')) # type: ignore
                                        self._roi_list.append(_ROI(reg_width,reg_height,reg_stride))
                    if 'MetaFormat'.casefold() in child.tag.casefold():
                        for child1 in child:
                            if 'MetaBlock'.casefold() in child1.tag.casefold():
                                for child2 in child1:
                                    meta_type: str = child2.tag.rsplit('}',maxsplit=1)[1]
                                    meta_event: str = child2.get('event') # type: ignore
                                    meta_datatype:str  = child2.get('type') # type: ignore
                                    meta_bitdepth = np.uint64(child2.get('bitDepth')) # type: ignore
                                    match meta_type:
                                        case 'TimeStamp':
                                            meta_resolution = np.uint64(child2.get('resolution')) # type: ignore
                                            meta_absolute_time:str = child2.get('absoluteTime') # type: ignore
                                            self._meta_list.append(TimeStamp(meta_event, meta_datatype, meta_bitdepth, meta_resolution, meta_absolute_time))
                                        case 'FrameTrackingNumber':
                                            self._meta_list.append(FrameTrackingNumber(meta_datatype, meta_bitdepth))
                                        case 'GateTracking':
                                            meta_event: str = child2.get('component') # type: ignore
                                            meta_monotonic = bool(child2.get('monotonic'))
                                            self._meta_list.append(GateTracking(meta_event, meta_datatype, meta_bitdepth, meta_monotonic))
                                        case _:
                                            raise RuntimeError('Metadata block was not recognized.')

                    if 'Calibrations'.casefold() in child.tag.casefold():
                        counter = 0
                        for child1 in child:
                            if 'WavelengthMapping'.casefold() in child1.tag.casefold():
                                for child2 in child1:
                                    if 'WavelengthError'.casefold() in child2.tag.casefold():
                                        wavelengths = np.array([])
                                        assert child2.text
                                        wl_text = child2.text.rsplit()
                                        for elem in wl_text:
                                            wavelengths = np.append(wavelengths,np.fromstring(elem,sep=',')[0])
                                        self._full_wavelength_coverage = wavelengths
                                    else:
                                        self._full_wavelength_coverage = np.fromstring(child2.text,sep=',') # type: ignore
                            if 'SensorInformation'.casefold() in child1.tag.casefold():
                                width = np.int32(child1.get('width')) # type: ignore
                                height = np.uint32(child1.get('height')) # type: ignore
                                self._sensor_dims= _ROI(width, height, 0)
                            if 'SensorMapping'.casefold() in child1.tag.casefold():
                                if counter < len(self._roi_list):
                                    self._roi_list[counter].x = np.uint64(child1.get('x')) # type: ignore
                                    self._roi_list[counter].y = np.uint64(child1.get('y')) # type: ignore
                                    og_width = np.uint64(child1.get('width')) # type: ignore
                                    og_height = np.uint64(child1.get('height')) # type: ignore
                                    self._roi_list[counter].xbin = np.uint64(child1.get('xBinning')) # type: ignore
                                    self._roi_list[counter].ybin = np.uint64(child1.get('yBinning')) # type: ignore
                                    self._roi_list[counter].width = np.uint64(og_width / self._roi_list[counter].xbin) # type: ignore
                                    self._roi_list[counter].height = np.uint64(og_height / self._roi_list[counter].ybin) # type: ignore
                                    counter += 1
                                else:
                                    break
                #now that xml parsing is done, extract all the metadata (if present)
                if len(self._meta_list) > 0:
                    self._frame_metadata_values = self.get_frame_metadata_value(
                        frames=range(0, self._num_frames))

            elif self._spe_version >=2 and self._spe_version <3:
                self._xml_footer = ''
                f.seek(108)
                self._pixel_format_key=np.fromfile(f,dtype=np.int16,count=1)[0]
                f.seek(42)
                frame_width=np.int32(np.fromfile(f,dtype=np.uint16,count=1)[0])
                f.seek(656)
                frame_height=np.int32(np.fromfile(f,dtype=np.uint16,count=1)[0])
                f.seek(1446)
                self._num_frames=np.fromfile(f,dtype=np.int32,count=1)[0]
                stride = np.int32(frame_height*frame_width*np.dtype(self.dataTypes_old_spe[self._pixel_format_key]).itemsize)
                self._roi_list.append(_ROI(frame_width,frame_height,stride))
            else:
                raise ValueError('Unrecognized spe file.')

    def get_data(self,*,rois:Optional[Sequence[int]] = None,
                frames:Optional[Sequence[int]] = None) ->\
                Sequence[SpeNdArray]:
        '''Extracts requested data from the referenced spe file. Only grabs
        the frame(s) and ROI(s) requested in the input parameters.

        Example usage:

        `image = img_reference.get_data(frames=[idx], rois=[])`
        will return a list of numpy NDArrays that correspond to regions.
        These arrays will be of shape `[Frames, Rows, Cols]`.

        `image[0][0]` will then get frame referred to by `idx`, for the
        first ROI.

        ----------------------------------------------------------------------
        Inputs:
        ----------------------------------------------------------------------
        - `rois`: Optional named argument for a sequence of desired ROIs. If
        None, then all ROIs in the spe file are parsed.
        - `frames`: Optional named argument for a sequence of desired frames.
        If None, then all frames in the spe file are parsed.
        ----------------------------------------------------------------------
        Output:
        ----------------------------------------------------------------------
        - `Sequence[SpeNdArray]`: a list of numpy NDArrays. List elements
        (outer) correspond to ROIs, and the NDArrays contain data blocks with
        the shape [Frames, Rows, Cols]
        ----------------------------------------------------------------------
        Exceptions:
        ----------------------------------------------------------------------
        - `ValueError` raised if desired ROI(s) and / or frame(s) fall outside
        of the range contained in the spe file.
        - `TypeError` raised if inputs are not iterable.
        '''
        data_list = list()
        #if no inputs, or empty list, set to all
        if not rois:
            rois = range(0,len(self._roi_list))
        if not frames:
            frames = range(0,self._num_frames)
        #check for improper values, raise exception if necessary
        try:
            for item in rois:
                if item < 0 or item >= len(self._roi_list):
                    raise ValueError(
                    'ROI value outside of allowed ranged (%d through %d)'
                    %(0, len(self._roi_list)-1))
        except TypeError as exc:
            raise TypeError('ROI input needs to be iterable') from exc
        try:
            for item in frames:
                if item < 0 or item >= self._num_frames:
                    raise ValueError(
                    'Frame value outside of allowed ranged (%d through %d)'
                    %(0, self._num_frames-1))
        except TypeError as exc:
            raise TypeError('Frame input needs to be iterable') from exc
        if self._spe_version >= 3:
            region_offset=0
            with open(self._filepath, encoding="utf8") as f:
                bpp = np.dtype(self.dataTypes[
                    str(self._pixel_format_key)]).itemsize
                for _, roi in enumerate(rois):
                    region_data = np.zeros([len(frames),
                        self._roi_list[roi].height,
                        self._roi_list[roi].width])
                    region_offset = 0
                    if roi>0:
                        for ii in range(0,roi):
                            region_offset += np.uint64(
                                self._roi_list[ii].stride/bpp)
                    for idx_frame, frame in enumerate(frames):
                        f.seek(0)
                        frame_offset = np.uint64(
                            frame*self._readout_stride/bpp)
                        read_count =  np.uint64(
                            self._roi_list[roi].stride/bpp)
                        tmp = np.fromfile(f,dtype=self.dataTypes[str(
                            self._pixel_format_key)],count=read_count,
                            offset=np.uint64(
                            4100+(region_offset*bpp)+(frame_offset*bpp)))
                        region_data[idx_frame,:] = np.reshape(tmp,[
                            self._roi_list[roi].height,
                            self._roi_list[roi].width])
                    data_list.append(region_data)
        elif self._spe_version >=2 and self._spe_version <3:
            if len(rois) != 1 and rois[0] !=0:
                raise ValueError('Only one ROI allowed for spe v2 parsing.')
            with open(self._filepath, encoding="utf8") as f:
                bpp = np.dtype(self.dataTypes_old_spe[
                    self._pixel_format_key]).itemsize# type: ignore
                region_data = np.zeros(
                    [len(frames), self._roi_list[0].height,
                     self._roi_list[0].width], dtype=self.dataTypes_old_spe[
                        self._pixel_format_key])# type: ignore
                for idx_frame, frame in enumerate(frames):
                    f.seek(0)
                    frame_offset = (self._roi_list[0].stride) * frame
                    tmp = np.fromfile(f,dtype=self.dataTypes_old_spe[
                        self._pixel_format_key],count=np.uint64(
                        self._roi_list[0].stride / bpp),
                        offset=np.uint64(4100+frame_offset))# type: ignore
                    region_data[idx_frame] = np.reshape(tmp,
                        [len(frames), self._roi_list[0].height,
                         self._roi_list[0].width])
                data_list.append(region_data)
        return data_list

    def get_wavelengths(self,*, rois: Optional[Sequence[int]] = None) ->\
        Sequence[WavelengthNdArray]:
        '''Extracts wavelength calibration axis for the ROI(s) specified by
        the `rois` input. Returns empty list if wavelength calibration info
        does not exist.
        ----------------------------------------------------------------------
        Input:
        ----------------------------------------------------------------------
        - `rois`: Optional int sequence specifying the ROI(s) to extract
        wavelength calibration for. If empty, all ROI(s) in the spe file will
        be parsed for wavelength calibration information.
        ----------------------------------------------------------------------
        Output:
        ----------------------------------------------------------------------
        - `Sequence` of `WavelengthNdArray` type. Each item in the
        sequence corresponds to a given ROI, as selected by the user's input.
        The NDArray elements are of type `float64`. If no wavelengths exist,
        and empty list is returned.
        ----------------------------------------------------------------------
        Exceptions:
        ----------------------------------------------------------------------
        - `ValueError` raised when the user input ROI value is outside of the
        range of ROIs existing in the spe file.
        - `TypeError` raised if the input parameter is not iterable.
        '''
        if self._spe_version < 3:
            print('Version %0.1f spe files do not have wavelength cal.'%
                (self._spe_version))
        if not any(self._full_wavelength_coverage):
            return []
        if not rois:
            rois = range(0,len(self._roi_list))
        try:
            for item in rois:
                if item < 0 or item >= len(self._roi_list):
                    raise ValueError(
                        'ROI value outside of allowed range (%d through %d)'
                        %(0, len(self._roi_list)-1))
        except TypeError as exc:
            raise TypeError('ROI input needs to be iterable') from exc

        ##if len(self.wavelength) == self.sensorDims.width:
        wavelength_list = []
        for item in rois:
            if self._roi_list[item].width > 0:
                wl_idx = np.arange(self._roi_list[item].x,
                    self._roi_list[item].x+self._roi_list[item].width,
                    self._roi_list[item].xbin,dtype=np.int32)
                wavelength_list.append(self._full_wavelength_coverage[wl_idx])
            else:
                wavelength_list.append(self._full_wavelength_coverage)
        return wavelength_list
    def _get_camera_settings_do_not_use(self) -> dict:
        '''
        WILL NOT BE MAINTAINED -- SEE GenerateSettingsLists
        Return a dictionary of useful camera settings
        Work in progress
        Current keys: exposure, analog_gain, adc_speed,
        sensor_temperature, camera_sn
        '''
        settings_dictionary = {
            'exposure': None,
            'analog_gain': None,
            'adc_speed': None,
            'sensor_temperature': None,
            'camera_info': None,
            'sensor_info': None
        }
        #pylint: disable=line-too-long
        xml_root = ET.fromstring(self._xml_footer)
        for child in xml_root:
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
                                                                                settings_dictionary['exposure'] = np.float64(child5.text)# type: ignore
                                                                    if 'Adc'.casefold() in child4.tag.casefold():
                                                                        for child5 in child4:
                                                                            if 'Speed'.casefold() in child5.tag.casefold():
                                                                                if child5.get('relevance') != 'False':
                                                                                    settings_dictionary['adc_speed']=np.float64(child5.text)# type: ignore
                                                                            if 'AnalogGain'.casefold() in child5.tag.casefold():
                                                                                if child5.get('relevance') != 'False':
                                                                                    settings_dictionary['analog_gain']=child5.text# type: ignore
                                                                    if 'Sensor'.casefold() in child4.tag.casefold():
                                                                        for child5 in child4:
                                                                            if 'Temperature'.casefold() in child5.tag.casefold():
                                                                                for child6 in child5:
                                                                                    if 'Reading'.casefold() in child6.tag.casefold():
                                                                                        settings_dictionary['sensor_temperature']=np.float64(child6.text)# type: ignore
                                                                            if 'Information'.casefold() in child5.tag.casefold():
                                                                                for child6 in child5:
                                                                                    if 'SensorName'.casefold() in child6.tag.casefold():
                                                                                        settings_dictionary['sensor_info']=child6.text# type: ignore
                                            if 'System'.casefold() in child4.tag.casefold():
                                                for child2 in child4:
                                                    if 'Cameras'.casefold() in child2.tag.casefold():
                                                        for child3 in child2:
                                                            if 'Camera'.casefold() in child3.tag.casefold():
                                                                settings_dictionary['camera_info'] = '%s, SN: %s'%(child3.get('model'),child3.get('serialNumber'))# type: ignore
        return settings_dictionary
    def retrieve_all_experiment_settings(self) -> Sequence[ExperimentSetting]:
        '''Parses xml for key settings and output as a list of
        `ExperimentSetting`. Settings to include are a work in progress.
        
        Check docstring for `retrieve_experiment_settings`
        for a list of settings that are currently included.
        '''
        experiment_settings_list = []

        #xml parsing
        #pylint: disable=line-too-long
        xml_root = ET.fromstring(self._xml_footer)
        for child in xml_root:
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
                                                                                experiment_settings_list.append(ExperimentSetting('EXPOSURE_TIME',  np.float64(child5.text), np.float64, _Unit.MS))
                                                                    if 'Adc'.casefold() in child4.tag.casefold():
                                                                        for child5 in child4:
                                                                            if 'Speed'.casefold() in child5.tag.casefold():
                                                                                if child5.get('relevance') != 'False':
                                                                                    experiment_settings_list.append(ExperimentSetting('ADC_SPEED',  np.float64(child5.text), np.float64, _Unit.MHZ))
                                                                            if 'AnalogGain'.casefold() in child5.tag.casefold():
                                                                                if child5.get('relevance') != 'False':
                                                                                    experiment_settings_list.append(ExperimentSetting('ADC_ANALOG_GAIN', str(child5.text), str, _Unit.NONE))
                                                                            if 'BitDepth'.casefold() in child5.tag.casefold():
                                                                                experiment_settings_list.append(ExperimentSetting('BIT_DEPTH',  np.int64(child5.text), np.int64, _Unit.BITS))# type: ignore
                                                                    if 'ReadoutControl'.casefold() in child4.tag.casefold():
                                                                        for child5 in child4:
                                                                            if 'Time'.casefold() in child5.tag.casefold():
                                                                                experiment_settings_list.append(ExperimentSetting('READOUT_TIME',  np.float64(child5.text), np.float64, _Unit.MS))
                                                                            if 'VerticalShiftRate'.casefold() in child5.tag.casefold():
                                                                                if child5.get('relevance') != 'False':
                                                                                    experiment_settings_list.append(ExperimentSetting('VERTICAL_SHIFT_RATE',  np.float64(child5.text), np.float64, _Unit.US))
                                                                            if 'PortsUsed'.casefold() in child5.tag.casefold():
                                                                                experiment_settings_list.append(ExperimentSetting('PORTS_USED',  np.int64(child5.text), np.int64, _Unit.NONE))# type: ignore
                                                                    if 'Sensor'.casefold() in child4.tag.casefold():
                                                                        for child5 in child4:
                                                                            if 'Temperature'.casefold() in child5.tag.casefold():
                                                                                for child6 in child5:
                                                                                    if 'Reading'.casefold() in child6.tag.casefold():
                                                                                        experiment_settings_list.append(ExperimentSetting('SENSOR_TEMPERATURE',  np.float64(child6.text), np.float64, _Unit.DEGREES_CELSIUS))
                                                                            if 'Information'.casefold() in child5.tag.casefold():
                                                                                for child6 in child5:
                                                                                    if 'SensorName'.casefold() in child6.tag.casefold():
                                                                                        experiment_settings_list.append(ExperimentSetting('SENSOR_INFORMATION', str(child6.text), str, _Unit.NONE))
                                                                                    if 'Pixel'.casefold() in child6.tag.casefold():
                                                                                        for child7 in child6:
                                                                                            if 'Width' in child7.tag and not 'Gap' in child7.tag:
                                                                                                experiment_settings_list.append(ExperimentSetting('PIXEL_PITCH',
                                                                                                    np.float64(child7.text), np.float64, _Unit.UM))

                                            if 'System'.casefold() in child4.tag.casefold():
                                                for child2 in child4:
                                                    if 'Cameras'.casefold() in child2.tag.casefold():
                                                        for child3 in child2:
                                                            if 'Camera'.casefold() in child3.tag.casefold():
                                                                experiment_settings_list.append(ExperimentSetting('CAMERA_MODEL', str(child3.get('model')), str, _Unit.NONE))
                                                                experiment_settings_list.append(ExperimentSetting('SERIAL_NUMBER', str(child3.get('serialNumber')), str, _Unit.NONE))
        #
        return tuple(experiment_settings_list)

    def retrieve_experiment_settings(self, setting_names: Sequence[str]) ->\
        Sequence[ExperimentSetting]:
        '''Generates an experiment settings list via parsing of the spe's xml
        footer and iterates through parsed settings until the user input
        setting_names are found. Any found settings are appended to the output
        sequence.

        WORK IN PROGRESS -- more valid settings may be added.

        ----------------------------------------------------------------------
        Input:
        ----------------------------------------------------------------------
        * `setting_names`: sequence of strings for desired experiment setting
        ----------------------------------------------------------------------
        Output:
        ----------------------------------------------------------------------
        * sequence of ExperimentSetting objects, if any of the user input
        settings were found, empty sequence otherwise.
        ----------------------------------------------------------------------
        Valid setting_names:
        ----------------------------------------------------------------------
        - `ADC_SPEED`
        - `BIT_DEPTH`
        - `CAMERA_MODEL`
        - `EXPOSURE_TIME`
        - `PIXEL_PITCH`
        - `PORTS_USED`
        - `READOUT_TIME`
        - `SENSOR_INFORMATION`
        - `SENSOR_TEMPERATURE`
        - `SERIAL_NUMBER`
        - `VERTICAL_SHIFT_RATE`
        ----------------------------------------------------------------------
        '''
        experiment_settings_list = self.retrieve_all_experiment_settings()
        output_list: list[ExperimentSetting] = []
        for requested_name in setting_names:
            for exp_setting in experiment_settings_list:
                if exp_setting.setting_name.casefold() ==\
                    requested_name.casefold():
                    output_list.append(exp_setting)
        return output_list

    def get_frame_metadata_value(self, frames: Sequence[int]) ->\
        Sequence[Sequence[MetaType]]:
        '''Retrieves per-frame metadata values for the frames specified in
        the input. The values for any given frame are returned as a `Sequence`
        of `MetaType` values (either `int64` or `float64`). The `SpeReference`
        member `meta_list` should be consulted to understand the type of
        metadata the value is referencing.
        ----------------------------------------------------------------------
        Input:
        ----------------------------------------------------------------------
        - `frames`: Sequence of ints specifying the frames to retrieve
        metadata values for.
        ----------------------------------------------------------------------
        Output:
        ----------------------------------------------------------------------
        - `Sequence[Sequence[MetaType]]`: The outer sequence is indexed per
        frame (as specified in the input). The inner sequence contains values
        for each metadata type present in the spe file. These types can be
        found in the `meta_list` member of `SpeReference`.
        '''
        output_metadata: list = [0] * len(frames)
        with open(self._filepath, encoding="utf8") as f:
            for idx_frame, frame in enumerate(frames):
                output_metadata[idx_frame] = [0] * len(self._meta_list)
                readout_offset = frame * self._readout_stride
                metadata_offset = int(readout_offset + self._frame_stride)
                for idx_meta, meta in enumerate(self._meta_list):
                    f.seek(0)
                    if idx_meta > 0:
                        metadata_offset += int(
                            (self._meta_list[idx_meta-1].bit_depth) / 8)
                    meta_length = np.dtype(meta.datatype).itemsize // int((
                        self._meta_list[idx_meta-1].bit_depth) / 8)
                    output_metadata[idx_frame][idx_meta] = np.fromfile(
                        f, dtype=meta.datatype, count=meta_length,
                        offset=int(4100+metadata_offset))[0]
                    tmp = meta
                    if isinstance(tmp, TimeStamp):
                        output_metadata[idx_frame][idx_meta] = (
                            output_metadata[idx_frame][idx_meta] /
                            tmp.resolution) * 1000
        return output_metadata
    @property
    def filepath(self) -> str:
        '''Full file path'''
        return self._filepath
    @property
    def file_directory(self) -> str:
        '''Directory containing spe file'''
        return self._file_directory
    @property
    def file_extension(self) -> str:
        '''File extension'''
        return self._file_extension
    @property
    def file_name(self) -> str:
        '''File name (no extension)'''
        return self._file_name
    @property
    def spe_version(self) -> float:
        '''Spe file version'''
        return self._spe_version
    @property
    def roi_list(self) -> Sequence[_ROI]:
        '''tuple of ROIs in the data block'''
        return tuple(self._roi_list)
    @property
    def readout_stride(self) -> NumpyInteger:
        '''Readout stride of the data block, in bytes'''
        return self._readout_stride
    @property
    def frame_stride(self) -> NumpyInteger:
        '''Frame stride (containing ROIs and Metadata), in bytes'''
        return self._frame_stride
    @property
    def num_frames(self) -> NumpyInteger:
        '''Number of frames in the data block'''
        return self._num_frames
    @property
    def pixel_format_key(self) -> PixelFormatKeyType:
        '''key to access value in the appropriate pixel format dictionary'''
        return self._pixel_format_key
    @property
    def sensor_dims(self) -> _ROI:
        '''ROI object that has height and width corresponding to original
        sensor dimensions.
        '''
        return self._sensor_dims
    @property
    def meta_list(self) -> Sequence[Metadata]:
        '''Tuple of metadata types contained in each frame's data block.'''
        return tuple(self._meta_list)
    @property
    def frame_metadata_values(self) -> Sequence[Sequence[MetaType]]:
        '''Nested tuple containing all frame metadata values in the full
        data block. Outer loop indexes frame, and inner loop indexes metadata
        element.
        '''
        return tuple(map(tuple,self._frame_metadata_values))
    @property
    def xml_footer(self) -> str:
        '''xml footer of spe file as string, to be used for external
        parsing.
        '''
        return self._xml_footer
    @property
    def xml_footer_pretty_print(self) -> str:
        '''xml footer in pretty print form for easier visualization'''
        dom = md.parseString(self.xml_footer)
        return dom.toprettyxml()

class Fits():
    '''Container for static methods `generate_fits_file` and
    `generate_fits_files`.

    - `generate_fits_file` creates a fits file using the astropy library.
    One file (multi-frame) is generated per ROI. Select experiment
    information is passed in, but per-frame metadata is NOT. If per-frame
    metadata is needed, please use `generate_fits_files`.
    '''
    @staticmethod
    def generate_fits_file(spe_ref: SpeReference) -> None:
        '''**REQUIRES ASTROPY LIBRARY**
        
        Generate a fits file (per ROI) using astropy library.
        Select experiment settings from the spe file's xml footer
        are carried over to the fits header. For a list of these select
        settings, please reference the docstring for
        `read_spe.SpeReference.retrieve_experiment_settings`.

        One file is generated per ROI (these files can thus be multi-frame).
        As such, per-frame metadata not included -- please use
        GenerateFitsFiles if per-frame metadata needs to be exported.

        ----------------------------------------------------------------------
        Input:
        ----------------------------------------------------------------------
        - `spe_ref`: `SpeReference` object containing the information from the
        spe file that will be used to generate fits.
        ----------------------------------------------------------------------
        Exceptions:
        ----------------------------------------------------------------------
        - `ImportError`: The Python runtime will raise this if astropy cannot
        be imported.
        ----------------------------------------------------------------------
        See Also:
        ----------------------------------------------------------------------
        - `read_spe.Fits.generate_fits_files`
        - `read_spe.SpeReference.retrieve_experiment_settings`
        '''
        for region in spe_ref.roi_list:
            if region.height < 1 or region.width < 1:
                raise ValueError(
                    'One or more region(s) of the spe file do not have'
                    ' valid data.')
        if spe_ref.spe_version >= 3:
            datatype: np.dtype = spe_ref.dataTypes[
                spe_ref.pixel_format_key]# type: ignore
        else:
            datatype: np.dtype = spe_ref.dataTypes_old_spe[
                spe_ref.pixel_format_key]# type: ignore
        from astropy.io import fits
        for idx_roi, roi in enumerate(spe_ref.roi_list):
            output_filepath = '%s\\%s-ROI%03d.fits'%(
                spe_ref.file_directory, spe_ref.file_name, idx_roi+1)
            region_data = np.zeros(
                [spe_ref.num_frames, roi.height, roi.width], dtype=datatype)
            for j in range(0, spe_ref.num_frames):
                region_data[j] = spe_ref.get_data(rois=[idx_roi],
                    frames=[j])[0]
            hdu = fits.PrimaryHDU(region_data)
            hdr = hdu.header
            #append experiment settings list to header
            experiment_settings_seq =\
                spe_ref.retrieve_all_experiment_settings()
            bin_settings_seq = (ExperimentSetting('X_BIN',
                np.int64(roi.xbin), np.int64, _Unit.NONE),
                ExperimentSetting('Y_BIN', np.int64(roi.ybin),
                                  np.int64, _Unit.NONE))
            assert isinstance(experiment_settings_seq, tuple)
            for setting in experiment_settings_seq + bin_settings_seq:
                hdr['HIERARCH %s'%(setting.setting_name)] =\
                    setting.setting_value
            hdu.writeto(output_filepath, overwrite=True)

    @staticmethod
    def generate_fits_files(spe_ref:SpeReference) -> None:
        '''**REQUIRES ASTROPY LIBRARY**
        
        Generates fits file(s) per frame per ROI in a subdirectory created
        in the spe file's location. Select experiment settings from the spe
        file's xml footer are carried over to the fits header. For a list of
        these select settings, please reference the docstring for
        `read_spe.SpeReference.retrieve_experiment_settings`.

        Frame metadata for exposure started timestamp will be present in the
        header of each file (if exists in the spe file).

        ----------------------------------------------------------------------
        Input:
        ----------------------------------------------------------------------
        - `spe_ref`: `SpeReference` object containing the information from the
        spe file that will be used to generate fits.
        ----------------------------------------------------------------------
        Exceptions:
        ----------------------------------------------------------------------
        - `ImportError`: The Python runtime will raise this if astropy cannot
        be imported.
        ----------------------------------------------------------------------
        See Also:
        ----------------------------------------------------------------------
        - `read_spe.Fits.generate_fits_file`
        - `read_spe.SpeReference.retrieve_experiment_settings`
        '''
        for region in spe_ref.roi_list:
            if region.height < 1 or region.width < 1:
                raise ValueError('One or more region(s) of the'
                    ' spe file do not have valid data.')
        from astropy.io import fits
        new_folder_path = Path('%s\\%s-fits\\'%(spe_ref.file_directory,
            spe_ref.file_name))
        if not new_folder_path.exists():
            new_folder_path.mkdir()
        for idx_roi, roi in enumerate(spe_ref.roi_list):
            for j in range(0, spe_ref.num_frames):
                output_filepath = '%s\\%s-ROI%03d-Frame%04d.fits'%(
                    new_folder_path, spe_ref.file_name, idx_roi+1, j+1)
                file_data = spe_ref.get_data(rois=[idx_roi], frames=[j])[0]
                frame_metadata = spe_ref.get_frame_metadata_value([j])[0]
                hdu = fits.PrimaryHDU(file_data)
                hdr = hdu.header
                #add time stamps to header if they exist
                if spe_ref.meta_list:
                    count = 0
                    for meta in spe_ref.meta_list:
                        if isinstance(meta, TimeStamp):
                            if meta.meta_event == 'ExposureStarted':
                                hdr['HIERARCH ACQUISITION_ORIGIN']\
                                    = meta.absolute_time
                                hdr[
                                'HIERARCH FRAME_EXPOSURE_STARTED_OFFSET_MS']\
                                    = frame_metadata[count]
                        count += 1
                #append experiment settings list to header
                experiment_settings_seq\
                    = spe_ref.retrieve_all_experiment_settings()
                bin_settings_seq = (ExperimentSetting('X_BIN',
                np.int64(roi.xbin), np.int64, _Unit.NONE),
                ExperimentSetting('Y_BIN', np.int64(roi.ybin),
                                  np.int64, _Unit.NONE))
                assert isinstance(experiment_settings_seq, tuple)
                for setting in experiment_settings_seq + bin_settings_seq:
                    hdr['HIERARCH %s'%(setting.setting_name)]\
                        = setting.setting_value
                hdu.writeto(output_filepath, overwrite=True)
    