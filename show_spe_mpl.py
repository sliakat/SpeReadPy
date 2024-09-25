# -*- coding: utf-8 -*-
"""
Created on Wed Feb  9 16:03:10 2022

@author: sliakat
"""

from typing import Any, Optional
from collections.abc import Sequence
from functools import partial
from threading import Lock
import tkinter as tk
from tkinter import filedialog
import xml.etree.ElementTree as ET
import warnings
import numpy as np
from matplotlib import pyplot as plt
from matplotlib.widgets import (Button, RectangleSelector, SpanSelector,
    Slider, TextBox)
from scipy import interpolate
from matplotlib import cm
from matplotlib.axes import Axes
from matplotlib.colors import ListedColormap
from matplotlib.transforms import Bbox
from read_spe import (SpeReference, TimeStamp, FrameTrackingNumber,
    GateTracking, ImageNdArray)

## globals
#font sizes
font_title = 36
font_labels = 24
font_stats = 18

spe_state_objects: list['SpeState'] = []

##user inputs
# if True, then x-axis is displayed
# as pixel even if calibration exists
PIXEL_AXIS = False 
AUTOCONTRAST = True
BG_APPLIED = False

class Region():
    '''Contains information for a data region to allow for processing.
    Information includes height, width, and origin x/y position.
    '''
    def __init__(self, x: int=-1, y: int=-1, og_width: int=0,
                 og_height: int=0, width: int=0, height:int=0,
                 x_bin: int=0, y_bin: int=0) -> None:
        self._x = x
        self._y = y
        self._og_width = og_width
        self._og_height = og_height
        self._width = width
        self._height = height
        self._x_bin = x_bin
        self._y_bin = y_bin
    @property
    def x(self) -> int:
        '''x position (upper-left, 0-indexed)'''
        return self._x
    @x.setter
    def x(self, val):
        self._x = val
    @property
    def y(self) -> int:
        '''y position (upper-left, 0-indexed)'''
        return self._y
    @y.setter
    def y(self, val):
        self._y = val
    @property
    def og_width(self) -> int:
        '''width of the region before binning is considered'''
        return self._og_width
    @og_width.setter
    def og_width(self, val):
        self._og_width = val
    @property
    def og_height(self) -> int:
        '''height of the region before binning is considered'''
        return self._og_height
    @og_height.setter
    def og_height(self, val):
        self._og_height = val
    @property
    def width(self) -> int:
        '''width of the region after binning is considered'''
        return self._width
    @width.setter
    def width(self, val):
        self._width = val
    @property
    def height(self) -> int:
        '''height of the region after binning is considered'''
        return self._height
    @height.setter
    def height(self, val):
        self._height = val
    @property
    def x_bin(self) -> int:
        '''binned columns'''
        return self._x_bin
    @x_bin.setter
    def x_bin(self, val):
        self._x_bin = val
    @property
    def y_bin(self) -> int:
        'binned rows'
        return self._y_bin
    @y_bin.setter
    def y_bin(self, val):
        self._y_bin = val

class Rectangle():
    '''Coordinate information for a rectangle, to be used to process user-
    selected boxes on the image plots.
    '''
    def __init__(self, x_left: int=-1, x_right: int=-1, y_top: int=-1, y_bottom: int=-1) -> None:
        self._x_left = x_left
        self._x_right = x_right
        self._y_top = y_top
        self._y_bottom = y_bottom
    @property
    def x_left(self) -> int:
        return self._x_left
    @x_left.setter
    def x_left(self, val: int):
        self._x_left = val
    @property
    def x_right(self) -> int:
        return self._x_right
    @x_right.setter
    def x_right(self, val: int):
        self._x_right = val
    @property
    def y_top(self) -> int:
        return self._y_top
    @y_top.setter
    def y_top(self, val: int):
        self._y_top = val
    @property
    def y_bottom(self) -> int:
        return self._y_bottom
    @y_bottom.setter
    def y_bottom(self, val: int):
        self._y_bottom = val
    
class SpeState():
    def __init__(self,spe_file_path:str) -> None:
        self._spe_file = SpeReference(spe_file_path)
        self._num_regions = len(self.spe_file._roi_list)
        self.region_list: Sequence[RegionImageState] = []
        for i in range(0, self.num_regions):
            self.region_list.append(RegionImageState(i))
            self.region_list[-1].region.x = self.spe_file._roi_list[i].x
            self.region_list[-1].region.y = self.spe_file._roi_list[i].y
            self.region_list[-1].region.width = self.spe_file._roi_list[i].width
            self.region_list[-1].region.height = self.spe_file._roi_list[i].height
            self.region_list[-1].region.x_bin = self.spe_file._roi_list[i].xbin
            self.region_list[-1].region.y_bin = self.spe_file._roi_list[i].ybin
    @property
    def spe_file(self)->SpeReference:
        return(self._spe_file)
    @property
    def num_regions(self)->int:
        return(self._num_regions)

class RegionImageState():
    """Stores states of objects needed to visualize the data in the
    current Region.
    """
    _current_frame: int
    _fig: Optional[Any] = None
    _ax: Optional[Axes] = None
    _ax_row_slices: list[Axes] = []
    _rectangle_select: Optional[RectangleSelector] = None
    _lock = Lock()
    _span_select: Optional[SpanSelector] = None
    _slider: Optional[Slider] = None
    _slider_connect: Optional[int] = None
    _button: Optional[Button] = None
    _textbox: Optional[TextBox] = None
    _textbox_entry = 0
    _pixel_axis: bool = False
    _autocontrast: bool = True
    _selection_rectangle: Rectangle
    _region: Region
    _region_wavelengths: Optional[Sequence[float]] = None
    def __init__(self, roi_index: int) -> None:
        self._roi_index = roi_index
        self._current_frame = 1
        self._selection_rectangle = Rectangle()
        self._region = Region()
    @property
    def roi_index(self)->int:
        return(self._roi_index)
    @property
    def current_frame(self)->int:
        return(self._current_frame)
    @current_frame.setter
    def current_frame(self, val: int):
        self._current_frame = val
    @property
    def fig(self) -> Any:
        return(self._fig)
    @fig.setter
    def fig(self, val):
        self._fig = val
    @property
    def ax(self) -> Any:
        return(self._ax)
    @ax.setter
    def ax(self, val):
        self._ax = val
    @property
    def rectangle_select(self) -> RectangleSelector | None:
        return(self._rectangle_select)
    @rectangle_select.setter
    def rectangle_select(self, val):
        self._rectangle_select = val
    @property
    def span_select(self) -> SpanSelector | None:
        return (self._span_select)
    @span_select.setter
    def span_select(self, val):
        self._span_select = val
    @property
    def slider(self) -> Any:
        return(self._slider)
    def generate_mpl_widgets(self, spe_state: SpeState):
        '''connect to matplotlibs callback from object state'''
        #slider
        if spe_state.spe_file.num_frames > 1:
            self._slider = SliderGen(self.ax, spe_state.spe_file.num_frames)
            self.slider.label.set_size(font_labels)
            self.slider_connect = self.slider.on_changed((
                lambda val: update_frame(val, spe_state, self)))
        if self.region.height > 1:
            #rectangle selection
            self.rectangle_select = RectSelect(spe_state, self)
            self._textbox_entry = int(self.region.height//2 - 1)
            self._textbox = generate_text_box(int(self.region.height//2 - 1))
            self._textbox.on_submit(self.on_text_submit)
            self._button = generate_button('Plot row slice')
            self._button.on_clicked(partial(self.on_button_click,
                spe_state=spe_state))
        elif self.region.height == 1:
            self.span_select = SpanSelect(spe_state, self)
        else:
            raise RuntimeError('Region height needs to be >= 1 row.')
    def on_text_submit(self, text: str) -> None:
        """Callback for text box submission. Validates for an integer
        > 0 and < height of data block. If the submission is valid,
        """
        # validate
        try:
            selected_row = int(text)
        except ValueError:
            warnings.warn('An integer needs to be entered into the text box.'
                f' Setting back to {self._textbox_entry}.')
            self._textbox.set_val(str(self._textbox_entry))
            return
        if selected_row < 0 or selected_row >= self.region.height:
            warnings.warn('A incorrect value was entered. The value needs to'
                f' be > 0 and < {self.region.height}.')
            self._textbox.set_val(str(self._textbox_entry))
            return
        with self._lock:
            self._textbox_entry = selected_row
    def on_button_click(self, click, spe_state: SpeState) -> None:
        """Callback for button click. Generates a line plot in a new
        figure (modeless) for the row specified in the text box.

        -----
        Notes:
        -----
        The text box callback will have performed the necessary
        validation on the row input, so there doesn't need to be
        any here.
        """
        data = spe_state.spe_file.get_data(frames=[self.current_frame-1],
            rois=[self.roi_index])[0][:, self._textbox_entry, :]
        self._ax_row_slices.append(plt.figure(
            f'Row {self._textbox_entry} slice for '
            f'{spe_state.spe_file.file_name}, ROI {self.roi_index+1}'
            ).add_subplot(111))
        plotData(data, self._ax_row_slices[-1], self.region_wavelengths,
            '%s, ROI %02d'%(
            spe_state.spe_file.file_name, self.roi_index+1),
            self.current_frame, pixAxis=self.pixel_axis,
            xBound1=-1, xBound2=-1, yBound1=-1, yBound2=-1)
    @property
    def slider_connect(self) -> Any:
        return(self._slider_connect)
    @slider_connect.setter
    def slider_connect(self, val):
        self._slider_connect = val
    @property
    def pixel_axis(self) -> bool:
        return self._pixel_axis
    @pixel_axis.setter
    def pixel_axis(self, val: bool):
        self._pixel_axis = val
    @property
    def autocontrast(self) -> bool:
        return self._autocontrast
    @autocontrast.setter
    def autocontrast(self, val):
        self._autocontrast = val
    @property
    def selection_rectangle(self) -> Rectangle:
        return self._selection_rectangle
    def update_selection_rectangle(self, x_left: int, x_right: int, y_top: int, y_bottom: int):
        self._selection_rectangle.x_left = x_left
        self._selection_rectangle.x_right = x_right
        self._selection_rectangle.y_top = y_top
        self._selection_rectangle.y_bottom = y_bottom
    @property
    def region_wavelengths(self) -> np.ndarray | None:
        return self._region_wavelengths
    @region_wavelengths.setter
    def region_wavelengths(self, val):
        self._region_wavelengths = val
        if self.region_wavelengths:
            self._region_wavelengths = self._region_wavelengths[0]
    @property
    def region(self) -> Region:
        return self._region
    @region.setter
    def region(self, x: int, y: int, og_width: int, og_height: int, width: int, height: int, x_bin: int, y_bin: int):
        self._region.x = x
        self._region.y = y
        self._region.og_width = og_width
        self._region.og_height = og_height
        self._region.width = width
        self._region.height = height
        self._region.x_bin = x_bin
        self._region.y_bin = y_bin
    

def generate_text_box(def_entry: int) -> TextBox:
    """Generates a text box used to enter a row number (from a 2-D image)
    to plot as a 1-D line. Used with an accompanying button.

    -----
    Input:
    -----
    img_axis
        `Axes` representing the painted image. The text box
        (and accompanying) button will be oriented underneath
        this `Axes`.
    """
    ax_text_box: Axes = plt.axes((0.45, 0.01, .02, .025))
    return TextBox(ax_text_box, '', initial = str(def_entry),
        textalignment='center')

def generate_button(label: str) -> Button:
    """Generates a button that will plot the a slice for the row number
    shown by the accompanying text box.

    -----
    Input:
    -----
    label:
        The displayed label for the button.    
    """
    ax_button: Axes = plt.axes((0.48, 0.01, .05, .025))
    return Button(ax_button, label)

def find_x_pixels(wl: int, x1: int, x2: int):
    """helper function to get pixel coords if wavelength cal
    is on x-axis
    """
    x1_pix = int(np.argmin(np.abs(wl - x1)))
    x2_pix = int(np.argmin(np.abs(wl - x2)))
    return x1_pix, x2_pix

#not using this in plot routine because mpl norms and then cmaps, but it is still a useful helper function for other applications
def GenCustomCmap(data, bits: int=16):  #take gray cmap, make yellow if 0, red if saturated
    gray = cm.get_cmap('gray',2**bits)
    newColors = gray(np.linspace(0,1,bits))
    red = np.array([1,0,0,1])
    yellow = np.array([1,1,0,1])
    if np.min(data) <= 0:
        newColors[0,:] = yellow
    if np.max(data) == 2**bits-1:
        newColors[-1,:] = red
    newMap = ListedColormap(newColors)
    return newMap
    
#callback for slider
def update_frame(val, spe_state: SpeState, region: RegionImageState):
    region.fig.canvas.draw_idle()
    region.current_frame = int(val)
    data = spe_state.spe_file.get_data(frames=[region.current_frame - 1], rois=[region.roi_index])[0][0]
    if region.autocontrast:
        plotData(data,region.ax, region.region_wavelengths, '%s, ROI %02d'%(spe_state.spe_file._file_name, region.roi_index+1),int(val),pixAxis=region.pixel_axis,xBound1=region.selection_rectangle.x_left,xBound2=region.selection_rectangle.x_right,yBound1=region.selection_rectangle.y_top,yBound2=region.selection_rectangle.y_bottom)
    else:
        plotData(data,region.ax, region.region_wavelengths, '%s, ROI %02d'%(spe_state.spe_file._file_name, region.roi_index+1),int(val),pixAxis=region.pixel_axis,xBound1=-1,xBound2=-1,yBound1=-1,yBound2=-1)
    print_metadata(spe_state.spe_file, region.current_frame)
    
def print_metadata(spe_file: SpeReference, frame_number: int) -> None:
    '''Prints metadata event name and value on request.'''
    if len(spe_file.meta_list) > 0:
        print('Metadata for %s, frame %d:'%(spe_file.file_name, frame_number))
        count = 0
        for meta in spe_file.meta_list:
            meta_value = spe_file.frame_metadata_values[frame_number-1][count]
            if isinstance(meta, TimeStamp):
                 print(f'{meta.meta_event}'.ljust(30)
                    + f'{meta_value:0,.3f} ms')
            if isinstance(meta, FrameTrackingNumber):
                print(f'{meta.meta_event}'.ljust(30)
                    + f'{meta_value:04d}')
            if isinstance(meta, GateTracking):
                print(f'{meta.meta_event}'.ljust(30)
                    + f'{meta_value:0,.3f} ns')
            count += 1
#helper to get FWHM of a line section
def FWHM(data):  #pass in a line (1D array)
    bias = np.percentile(data,10)  #take the 10th percentile of data as a bias
    halfMax = (np.max(data)-bias)/2 + bias #this is the target to search for
    #interpolate the data
    interpFactor = 100  #FWHM precision to hundredths
    dataPts = len(data)
    x = np.arange(0,dataPts)
    f = interpolate.interp1d(x, data)
    xnew = np.arange(0,dataPts-1,1/interpFactor)
    ynew = f(xnew)
    #search for FWHM
    maxLoc = np.argmax(ynew)
    if maxLoc > 0:
        subtracted = np.abs(ynew-halfMax)
        leftSide = subtracted[0:maxLoc]
        rightSide = subtracted[maxLoc:len(subtracted)]
        leftPoint = np.argmin(leftSide)
        rightPoint = np.argmin(rightSide) + maxLoc
        #print(leftPoint,maxLoc,rightPoint)
        return (rightPoint-leftPoint)/interpFactor
    else:
        return 0
    

def plotData(data,ax,wave,name,frame: int=1,*,pixAxis: bool=False, xBound1: int=-1, xBound2: int=-1, yBound1: int=-1, yBound2: int=-1):     #pass in frame
    global bits, BG_APPLIED, font_title, font_labels  
    flatData = data.ravel()
    #image contrast adjustments
    if (xBound2 - xBound1 > 2) and (yBound2 -yBound1 > 2):
            display_min = int(np.percentile(data[yBound1:yBound2,xBound1:xBound2].ravel(),5))
            display_max = int(np.percentile(data[yBound1:yBound2,xBound1:xBound2].ravel(),95))
    else:
        display_min = int(np.percentile(flatData,5))
        display_max = int(np.percentile(flatData,95))
    if display_min < 1:
        display_min = 1
    if display_max <1:
        display_max = 1 

    ax.clear()
    #plotting
    if np.size(data,0)==1:
        ax.grid()
        if len(wave) > 0 and pixAxis is False:
            ax.plot(wave,data[0])
            ax.set_xlabel('Wavelength (nm)',fontsize=font_labels)
            ax.set(xlim=(wave[0],wave[-1]))
        else:
            ax.plot(data[0])
            ax.set_xlabel('Pixels',fontsize=font_labels)
            ax.set(xlim=(0,np.size(data[0])))
        ax.set_ylabel('Intensity (counts)',fontsize=font_labels)
    else:
        # colorMap = 'gray'
        # if bg==False:
        #     colorMap = GenCustomCmap(flatData,bits)
        # aspect factor (to match original 1 w/ pixel axis):
        # new X / old X
        if len(wave) > 0 and pixAxis is False and np.min(wave) != np.max(wave):
            ax.imshow(data,vmin=display_min,vmax=display_max,cmap='gray',extent=[wave[0],wave[-1],np.size(data,0),0],
                aspect=(wave[-1]-wave[0]) / data.shape[1])
            ax.set_xlabel('Wavelength (nm)',fontsize=font_labels)
        else:
            ax.imshow(data,origin='upper',vmin=display_min,vmax=display_max,cmap='gray', aspect=1)
            ax.set_xlabel('Column',fontsize=font_labels)
        ax.set_ylabel('Row',fontsize=font_labels)
        if BG_APPLIED==False:
            if np.min(data) <= 0:
                zeros = np.argwhere(data==0)
                if len(wave) > 10 and pixAxis==False:
                    ax.scatter(wave[zeros[:,1]],wave[zeros[:,0]],color='yellow',s=10)
                else:
                    ax.scatter(zeros[:,1],zeros[:,0],color='yellow',s=10)
            if np.max(data) == 2**bits-1:
                sat = np.argwhere(data==2**bits-1)
                if len(wave) > 10 and pixAxis==False:
                    ax.scatter(wave[sat[:,1]],sat[:,0],color='red',s=10)
                else:
                    ax.scatter(sat[:,1],sat[:,0],color='red',s=10)
    axName = '%s, Frame %d'%(name,frame)
    ax.set_title(axName, fontsize=font_title)
    for label in (ax.get_xticklabels() + ax.get_yticklabels()):
        label.set_fontsize(font_labels)
    plt.show()

#display helpers
def WriteStats(axis, string):
    global font_stats
    #clear previous text object
    for txt in axis.texts:
        txt.remove()
    plt.draw()
    axis.text(0,1.15,string, fontsize=font_stats, verticalalignment='top', color = 'r', transform=axis.transAxes)
    

def GetStats(data, x1, x2, y1, y2):
    regionDat = data[y1:y2,x1:x2]
    regMean = np.mean(regionDat.flatten())
    regDev = np.std(regionDat.flatten())
    regMin = np.min(regionDat.flatten())
    regMax = np.max(regionDat.flatten())
    return regMean,regDev,regMin,regMax
    
#callback for box selection
def box_select_callback(eclick, erelease, spe_state: SpeState, region: RegionImageState):
    x1, y1 = int(np.floor(eclick.xdata)), int(np.floor(eclick.ydata))
    x2, y2 = int(np.floor(erelease.xdata)), int(np.floor(erelease.ydata))
    if not region.pixel_axis and any(region.region_wavelengths):
        x1, x2 = find_x_pixels(region.region_wavelengths, x1, x2)
    if x2-x1 >= 3 and y2-y1 >= 3:
        data = np.array(region.ax.get_images().pop()._A)
        centerRow = np.int32(np.floor(np.shape(data)[0]/2))
        mean, dev, regMin, regMax = GetStats(data,x1,x2,y1,y2)
        fwhm = FWHM(data[centerRow,x1:x2])
        statsString = 'Region Mean: %0.2f          Region Min: %0.2f\nRegion Std: %0.2f          Region Max: %0.2f\nMin/Mean Ratio: %0.3f          FWHM of horizontal slice: %0.3f pix'%(mean,regMin,dev,regMax,(regMin/mean),fwhm)    
        region.update_selection_rectangle(x1, x2, y1, y2)
        if region.autocontrast:
            plotData(data,region.ax,region.region_wavelengths,'%s, ROI %02d'%(spe_state.spe_file._file_name, region.roi_index+1),region.current_frame,pixAxis=region.pixel_axis,xBound1=x1,xBound2=x2,yBound1=y1,yBound2=y2)
        else:
            plotData(data,region.ax,region.region_wavelengths,'%s, ROI %02d'%(spe_state.spe_file._file_name, region.roi_index+1),region.current_frame,pixAxis=region.pixel_axis,xBound1=-1,xBound2=-1,yBound1=-1,yBound2=-1)
        WriteStats(region.ax, statsString)
    else:
        for txt in region.ax.texts:
            txt.remove()
            plt.draw()
    plt.show()
        
#callback for line selection
def StatsLinePlot(xmin, xmax, spe_state: SpeState, region: RegionImageState):
    #data shape here will be (1, cols)
    #print(np.floor(xmin),np.floor(xmax))
    if not region.pixel_axis and len(region.region_wavelengths) > 0:
        xmin, xmax = find_x_pixels(region.region_wavelengths, xmin, xmax)    
    regionDat = region.ax.get_lines()[0].get_data()[1][int(np.floor(xmin)):int(np.floor(xmax))]
    mean = np.mean(regionDat)
    dev = np.std(regionDat)
    fwhm = FWHM(regionDat)
    statsString = 'Region Mean: %0.2f\n Region Std: %0.2f\nFWHM: %0.3f pix'%(mean,dev,fwhm)
    WriteStats(region.ax, statsString)
    plt.show()
    
#matplotlib widget for box selection
def RectSelect(spe_state: SpeState, region: RegionImageState):
    return RectangleSelector(region.ax, lambda eclick, erelease: box_select_callback(eclick, erelease, spe_state, region),
                                       useblit=True,
                                       button=[1], minspanx=10, minspany=10,
                                       spancoords='pixels', interactive=True)

#matplotlib widget for line selection
def SpanSelect(spe_state: SpeState, region: RegionImageState):
    return SpanSelector(region.ax, lambda xmin, xmax: StatsLinePlot(xmin, xmax, spe_state, region), 'horizontal', interactive=True)

def SliderGen(axis,maximum):
    fp = axis.get_position()        #get position of the figure
    axvert = plt.axes((fp.x0-0.08, fp.y0, 0.0225, 0.75))
    return Slider(ax=axvert,label='%d Total Frames'%(maximum), valmin=1, valmax=maximum, valinit=1, orientation="vertical", valstep=1)

#parse xml for experiment info
def FindXmlElems(xmlStr, stringList):
    if len(xmlStr)>50:
        for elem in ET.fromstring(xmlStr).iter():
            for key in elem.attrib.keys():
                if 'serialNumber'.casefold() in key.casefold():
                    tagSplit = elem.tag.rsplit('}',maxsplit=1)[1]
                    print('%s:\t\t%s'%(tagSplit, elem.attrib))
                    break
            for item in stringList:
                if item.casefold() in elem.tag.casefold():
                    tagSplit = elem.tag.rsplit('}',maxsplit=1)[1]
                    print('%s:\t\t%s\t\t%s'%(tagSplit, elem.attrib, elem.text))
        print('\n\n')
        
def print_selected_xml_entries(xmlStr):
    global bits, BG_APPLIED    
    if len(xmlStr)>50:
        xmlRoot = ET.fromstring(xmlStr)
        #find DataHistories
        for child in xmlRoot:
            if 'DataHistories'.casefold() in child.tag.casefold():
                for child1 in child:
                    if 'DataHistory'.casefold() in child1.tag.casefold():
                        for child2 in child1:
                            if 'Origin'.casefold() in child2.tag.casefold():
                                print('LF version used:'.ljust(30)
                                    + f'{child2.get('softwareVersion')}')
                                for child3 in child2:
                                    if 'Experiment'.casefold() in child3.tag.casefold():
                                        for child4 in child3:
                                            if 'System'.casefold() in child4.tag.casefold():
                                                for child2 in child4:
                                                    if 'Cameras'.casefold() in child2.tag.casefold():
                                                        for child3 in child2:
                                                            if 'Camera'.casefold() in child3.tag.casefold():
                                                                print('Camera model:'.ljust(30)
                                                                    + f'{child3.get('model')}\n'
                                                                    + 'Camera Serial Number:'.ljust(30)
                                                                    + f'{child3.get('serialNumber')}')
                                                    if 'Spectrometers'.casefold() in child2.tag.casefold():
                                                        for child3 in child2:
                                                            if 'Spectrometer'.casefold() in child3.tag.casefold():
                                                                print('Spectrograph model:'.ljust(30)
                                                                    + f'{child3.get('model')}\n'
                                                                    + 'Spectrograph Serial Number:'.ljust(30)
                                                                    + f'{child3.get('serialNumber')}')                                            
                                            if 'Devices'.casefold() in child4.tag.casefold():
                                                for child2 in child4:
                                                    if 'Cameras'.casefold() in child2.tag.casefold():
                                                        for child3 in child2:
                                                            if 'Camera'.casefold() in child3.tag.casefold():
                                                                for child4 in child3:
                                                                    if 'Sensor'.casefold() in child4.tag.casefold():
                                                                        for child5 in child4:
                                                                            if 'Information'.casefold() in child5.tag.casefold():
                                                                                for child6 in child5:
                                                                                    if 'SensorName'.casefold() in child6.tag.casefold():
                                                                                        print('Camera sensor:'.ljust(30)
                                                                                          + f'{child6.text}')
                                                                                    if 'Pixel'.casefold() in child6.tag.casefold():
                                                                                        for child7 in child6:
                                                                                            if ('Width'.casefold() in child7.tag.casefold()) and ('GapWidth'.casefold() not in child7.tag.casefold()):
                                                                                                print('Pixel width:'.ljust(30)
                                                                                                + f'{child7.text}um')
                                                                            if 'Temperature'.casefold() in child5.tag.casefold():
                                                                                for child6 in child5:
                                                                                    if 'Reading'.casefold() in child6.tag.casefold():
                                                                                        print('Temperature:'.ljust(30)
                                                                                          + f'{child6.text}C, ', end='')
                                                                                    if ('Status'.casefold() in child6.tag.casefold()) and ('CoolingFanStatus'.casefold() not in child6.tag.casefold()) and ('VacuumStatus'.casefold() not in child6.tag.casefold()):
                                                                                        print('%s'%(child6.text))
                                                                                    if ('VacuumStatus'.casefold() in child6.tag.casefold()):
                                                                                        print('Vacuum Status:'.ljust(30)
                                                                                          + f'{child6.text}')
                                                                            if 'Cleaning'.casefold() in child5.tag.casefold():
                                                                                for child6 in child5:
                                                                                    if 'CleanSerialRegister'.casefold() in child6.tag.casefold():
                                                                                        if child6.get('relevance') != 'False':
                                                                                            print('Clean Serial Reg:'.ljust(30)
                                                                                          + f'{child6.text}')
                                                                                    if 'CleanUntilTrigger'.casefold() in child6.tag.casefold():
                                                                                        if child6.get('relevance') != 'False':
                                                                                            print('Clean Until Trig:'.ljust(30)
                                                                                          + f'{child6.text}')
                                                                    if 'ShutterTiming'.casefold() in child4.tag.casefold():
                                                                        for child5 in child4:
                                                                            if 'ExposureTime'.casefold() in child5.tag.casefold():
                                                                                print('Exposure Time:'.ljust(30)
                                                                                          + f'{float(child5.text):0,.3f}ms')
                                                                            if 'Mode'.casefold() in child5.tag.casefold():
                                                                                print('Shutter Mode:'.ljust(30)
                                                                                          + f'{child5.text}')
                                                                    if 'Gating'.casefold() in child4.tag.casefold():
                                                                        gateMode = ''
                                                                        startDelay = 0
                                                                        endDelay = 0
                                                                        startWidth = 0
                                                                        endWidth = 0
                                                                        for child5 in child4:
                                                                            if 'Mode'.casefold() in child5.tag.casefold():
                                                                                gateMode = child5.text
                                                                            if 'RepetitiveGate'.casefold() in child5.tag.casefold():
                                                                                if child5.get('relevance') != 'False':
                                                                                    for child6 in child5:
                                                                                        if 'Pulse'.casefold() in child6.tag.casefold():
                                                                                            startWidth = np.float64(child6.get('width'))
                                                                                            startDelay = np.float64(child6.get('delay'))
                                                                            if 'Sequential'.casefold() in child5.tag.casefold():                                                                                
                                                                                for child6 in child5:
                                                                                    if 'StartingGate'.casefold() in child6.tag.casefold():
                                                                                        if child6.get('relevance') != 'False':
                                                                                            for child7 in child6:
                                                                                                if 'Pulse'.casefold() in child7.tag.casefold():
                                                                                                    startWidth = np.float64(child7.get('width'))
                                                                                                    startDelay = np.float64(child7.get('delay'))
                                                                                    if 'EndingGate'.casefold() in child6.tag.casefold():
                                                                                        if child6.get('relevance') != 'False':
                                                                                            for child7 in child6:
                                                                                                if 'Pulse'.casefold() in child7.tag.casefold():
                                                                                                    endWidth = np.float64(child7.get('width'))
                                                                                                    endDelay = np.float64(child7.get('delay'))  
                                                                            if 'Dif'.casefold() in child5.tag.casefold():                                                                                
                                                                                for child6 in child5:
                                                                                    if 'StartingGate'.casefold() in child6.tag.casefold():
                                                                                        if child6.get('relevance') != 'False':
                                                                                            for child7 in child6:
                                                                                                if 'Pulse'.casefold() in child7.tag.casefold():
                                                                                                    startWidth = np.float64(child7.get('width'))
                                                                                                    startDelay = np.float64(child7.get('delay'))
                                                                                    if 'EndingGate'.casefold() in child6.tag.casefold():
                                                                                        if child6.get('relevance') != 'False':
                                                                                            for child7 in child6:
                                                                                                if 'Pulse'.casefold() in child7.tag.casefold():
                                                                                                    endWidth = np.float64(child7.get('width'))
                                                                                                    endDelay = np.float64(child7.get('delay'))
                                                                                                    gateMode = 'Dif'
                                                                        if gateMode == 'Repetitive':
                                                                            print('Gating:'.ljust(30)+ gateMode.ljust(30)
                                                                                  + '\nStart Width:'.ljust(30) + f'{startWidth:0,.3f}ns'.ljust(30)
                                                                                  + '\nGate Delay:'.ljust(30) + f'{startDelay:0,.3f}ns'.ljust(30))
                                                                        if gateMode == 'Sequential' or gateMode == 'Dif':
                                                                            print('Gating:'.ljust(30)+ gateMode.ljust(30)
                                                                            + '\nStart Width:'.ljust(30) + f'{startWidth:0,.3f}ns'.ljust(30)
                                                                            + '\nStart Delay:'.ljust(30) + f'{startDelay:0,.3f}ns'.ljust(30)
                                                                            + '\nEnd Width:'.ljust(30) + f'{endWidth:0,.3f}ns'.ljust(30)
                                                                            + '\nEnd Delay:'.ljust(30) + f'{endDelay:0,.3f}ns'.ljust(30))
                                                                    if 'Intensifier'.casefold() in child4.tag.casefold():
                                                                        for child5 in child4:
                                                                            if 'Gain'.casefold() in child5.tag.casefold():
                                                                                if child5.get('relevance') != 'False':
                                                                                    print('Intensifier Gain:'.ljust(30)
                                                                                          + f'{child5.text}x')
                                                                            if 'Status'.casefold() in child5.tag.casefold():
                                                                                print('Intensifier Status:'.ljust(30)
                                                                                          + f'{child5.text}')
                                                                            if 'EMIccd'.casefold() in child5.tag.casefold():
                                                                                for child6 in child5:
                                                                                    if ('Gain'.casefold() in child6.tag.casefold()) and ('GainControlMode'.casefold() not in child6.tag.casefold()):
                                                                                        if child6.get('relevance') != 'False':
                                                                                            print('EMI Gain:'.ljust(30)
                                                                                          + f'{child6.text}x')
                                                                                
                                                                    if 'ReadoutControl'.casefold() in child4.tag.casefold():
                                                                        for child5 in child4:
                                                                            if 'Mode'.casefold() in child5.tag.casefold():
                                                                                print('Readout Mode:'.ljust(30)
                                                                                          + f'{child5.text}')
                                                                            if 'Time'.casefold() in child5.tag.casefold():
                                                                                print('Readout Time:'.ljust(30)
                                                                                          + f'{float(child5.text):0,.3f}ms')
                                                                            if 'StorageShiftRate'.casefold() in child5.tag.casefold():
                                                                                if child5.get('relevance') != 'False':
                                                                                    print('Storage Shift:'.ljust(30)
                                                                                          + f'{float(child5.text):0,.3f}us')
                                                                            if 'VerticalShiftRate'.casefold() in child5.tag.casefold():
                                                                                if child5.get('relevance') != 'False':
                                                                                    print('Vertical Shift:'.ljust(30)
                                                                                          + f'{float(child5.text):0,.3f}us')
                                                                            if 'PortsUsed'.casefold() in child5.tag.casefold():
                                                                                print('Ports Used:'.ljust(30)
                                                                                          + f'{child5.text}')
                                                                            if 'Accumulations'.casefold() in child5.tag.casefold():
                                                                                print('Accumulations:'.ljust(30)
                                                                                          + f'{float(child5.text):0,.3f}')
                                                                    if 'HardwareIO'.casefold() in child4.tag.casefold():
                                                                        for child5 in child4:                                                    
                                                                            if 'Trigger'.casefold() in child5.tag.casefold():
                                                                                triggerMode = ''
                                                                                triggerFreq = 0
                                                                                for child6 in child5:
                                                                                    if 'Frequency'.casefold() in child6.tag.casefold():
                                                                                        triggerFreq = np.float64(child6.text)
                                                                                    if 'Source'.casefold() in child6.tag.casefold():
                                                                                        triggerMode = child6.text
                                                                                if triggerMode == "Internal":
                                                                                    print('Trigger:'.ljust(30)
                                                                                          + f'Internal, {triggerFreq:0,.3f} Hz')
                                                                    if 'Adc'.casefold() in child4.tag.casefold():
                                                                        for child5 in child4:
                                                                            if 'Speed'.casefold() in child5.tag.casefold():
                                                                                if child5.get('relevance') != 'False':
                                                                                    print('ADC Speed:'.ljust(30)
                                                                                          + f'{child5.text} MHz')
                                                                            if 'AnalogGain'.casefold() in child5.tag.casefold():
                                                                                if child5.get('relevance') != 'False':
                                                                                    print('Analog Gain:'.ljust(30)
                                                                                          + f'{child5.text}')
                                                                            if 'EMGain'.casefold() in child5.tag.casefold():
                                                                                if child5.get('relevance') != 'False':
                                                                                    print('EM Gain:'.ljust(30)
                                                                                          + f'{float(child5.text):0,.0f}x')
                                                                            if 'Quality'.casefold() in child5.tag.casefold():
                                                                                print('ADC Quality:'.ljust(30)
                                                                                          + f'{child5.text}')
                                                                            if 'CorrectPixelBias'.casefold() in child5.tag.casefold():
                                                                                print('PBC On?:'.ljust(30)
                                                                                          + f'{child5.text}')
                                                                            if 'BitDepth'.casefold() in child5.tag.casefold():
                                                                                bits = np.int32(child5.text)
                                                                    if 'Acquisition'.casefold() in child4.tag.casefold():
                                                                        for child5 in child4:
                                                                            if 'FrameRate'.casefold() in child5.tag.casefold():
                                                                                print('Frame Rate:'.ljust(30)
                                                                                          + f'{float(child5.text):0,.3f} fps')
                                                                    if 'Experiment'.casefold() in child4.tag.casefold():
                                                                        for child5 in child4:
                                                                            if 'OnlineProcessing'.casefold() in child5.tag.casefold():
                                                                                for child6 in child5:
                                                                                    if 'FrameCombination'.casefold() in child6.tag.casefold():
                                                                                        isCombined = True
                                                                                        method = ''
                                                                                        framesCombined = 1
                                                                                        for child7 in child6:
                                                                                            if 'Method'.casefold() in child7.tag.casefold():
                                                                                                if child7.get('relevance') == 'False': #if relevance is there, that means it's false
                                                                                                    isCombined = False
                                                                                                method = child7.text
                                                                                            if 'FramesCombined'.casefold() in child7.tag.casefold():
                                                                                                framesCombined = np.int64(child7.text)
                                                                                        if isCombined:
                                                                                            print('Frame Combination:'.ljust(30)
                                                                                                + f'{method} of {framesCombined:0d} frames.')
                                                                            if 'OnlineCorrections'.casefold() in child5.tag.casefold():
                                                                                correctionList = []
                                                                                for child6 in child5:
                                                                                    if 'OrientationCorrection'.casefold() in child6.tag.casefold():
                                                                                        for child7 in child6:
                                                                                            if 'Enabled'.casefold() in child7.tag.casefold():
                                                                                                if child7.text == 'True':
                                                                                                    correctionList.append('Orientation')
                                                                                    if 'BlemishCorrection'.casefold() in child6.tag.casefold():
                                                                                        for child7 in child6:
                                                                                            if 'Enabled'.casefold() in child7.tag.casefold():
                                                                                                if child7.text == 'True':
                                                                                                    correctionList.append('Blemish')
                                                                                    if 'BackgroundCorrection'.casefold() in child6.tag.casefold():
                                                                                        for child7 in child6:
                                                                                            if 'Enabled'.casefold() in child7.tag.casefold():
                                                                                                if child7.text == 'True':
                                                                                                    correctionList.append('Background')
                                                                                                    BG_APPLIED = True
                                                                                    if 'FlatfieldCorrection'.casefold() in child6.tag.casefold():
                                                                                        for child7 in child6:
                                                                                            if 'Enabled'.casefold() in child7.tag.casefold():
                                                                                                if child7.text == 'True':
                                                                                                    correctionList.append('Flatfield')
                                                                                    if 'CosmicRayCorrection'.casefold() in child6.tag.casefold():
                                                                                        for child7 in child6:
                                                                                            if 'Enabled'.casefold() in child7.tag.casefold():
                                                                                                if child7.text == 'True':
                                                                                                    correctionList.append('Cosmic')
                                                                                if len(correctionList) > 0:
                                                                                    print('Correction(s):'.ljust(30),end='')
                                                                                    for i in range(0,len(correctionList)):
                                                                                        print('%s'%(correctionList[i]),end='')
                                                                                        if i <len(correctionList)-1:
                                                                                            print(', ',end='')
                                                                                    print('')
                                                    if 'Spectrometers'.casefold() in child2.tag.casefold():                                
                                                        for child3 in child2:
                                                            if 'Spectrometer'.casefold() in child3.tag.casefold():
                                                                for child4 in child3:
                                                                    if 'Grating'.casefold() in child4.tag.casefold():
                                                                        for child5 in child4:
                                                                            if 'Selected'.casefold() in child5.tag.casefold():
                                                                                print('Grating:'.ljust(30)
                                                                                    + f'{child5.text}', end='')
                                                                            if 'CenterWavelength'.casefold() in child5.tag.casefold():
                                                                                print(f', CWL: {float(child5.text):0,.3f} nm')
                                                                    if 'Experiment'.casefold() in child4.tag.casefold():
                                                                        calibrationList = []
                                                                        for child5 in child4:
                                                                            if 'StepAndGlue'.casefold() in child5.tag.casefold():
                                                                                startWL = 0
                                                                                endWL = 0
                                                                                enabled = ''
                                                                                for child6 in child5:
                                                                                    if 'Enabled'.casefold() in child6.tag.casefold():
                                                                                        enabled = child6.text
                                                                                    if 'StartingWavelength'.casefold() in child6.tag.casefold():
                                                                                        startWL = np.float64(child6.text)
                                                                                    if 'EndingWavelength'.casefold() in child6.tag.casefold():
                                                                                        endWL = np.float64(child6.text)
                                                                                if enabled == 'True':
                                                                                    print('Step and Glue:'.ljust(30)
                                                                                        + f'{startWL:0,.3f} nm to {endWL:0,.3f} nm')
                                                                            if 'IntensityCalibration'.casefold() in child5.tag.casefold():
                                                                                for child6 in child5:
                                                                                    if 'Enabled'.casefold() in child6.tag.casefold():
                                                                                        if child6.text == 'True':
                                                                                            calibrationList.append('Intensity')
                                                                            if 'WavelengthCalibration'.casefold() in child5.tag.casefold():
                                                                                for child6 in child5:
                                                                                    if 'Mode'.casefold() in child6.tag.casefold():
                                                                                        calType = child6.get('type')
                                                                                        if calType == 'NullableCalibrationMode':
                                                                                            break
                                                                                        else:
                                                                                            calString = 'Wavelength (%s)'%(child6.text)
                                                                                            calibrationList.append(calString)
                                                                        if len(calibrationList) > 0:
                                                                            print('Calibration(s):'.ljust(30),end='')
                                                                            for i in range(0,len(calibrationList)):
                                                                                print('%s'%(calibrationList[i]),end='')
                                                                                if i <len(calibrationList)-1:
                                                                                    print(', ',end='')
    print('')

def stop_prompt():
    print('Press Enter to end script')
    input()

if __name__=="__main__":
    #use tk for file dialog
    root = tk.Tk()
    filenames = filedialog.askopenfilenames(
        title='Select Spe Files',filetypes=[
        ('spe files','*.spe'),('spe files','*.SPE')])
    root.withdraw()

    #makes figures spawn in individual threads
    plt.ion()

    for idx_filename, filename in enumerate(filenames):
        spe_state_objects.append(SpeState(filename))        
        current_spe = spe_state_objects[idx_filename].spe_file
        print('**Information for %s%s**'
              %(current_spe.file_name, current_spe.file_extension))
        xml_total = current_spe._xml_footer
        bits = None
        try:
            xml_format = current_spe.xml_footer_pretty_print
            print_selected_xml_entries(xml_total)
            print('%d region(s):'%(len(current_spe.roi_list)))
        except:
            if current_spe.spe_version < 3:
                print('spe file version %0.1f does not have an xml footer.'
                    ' Only first ROI is displayed for this spe file version.'
                    %(current_spe.spe_version))
            else:
                print('xml could not be formatted and/ or parsed')
        if bits == None:
            bits = 16 #assume 16 bit data for legacy spe files or
            # files that don't have it in the xml content.
            # this may or may not be true -- please alert if issue discovered.
        for idx_rgn, rgn in enumerate(
            spe_state_objects[idx_filename].region_list):
            print('\tROI %02d: %d x %d, xbin %d, ybin %d'
                %(idx_rgn+1, rgn.region.width, rgn.region.height,
                  rgn.region.x_bin, rgn.region.y_bin))
            rgn.fig = plt.figure('%s, ROI %02d'%
                (current_spe.file_name, idx_rgn+1))
            rgn.region_wavelengths = current_spe.get_wavelengths(
                rois=[idx_rgn])
            rgn.ax = rgn.fig.add_subplot(111)
            rgn.generate_mpl_widgets(spe_state_objects[idx_filename])
            rgn.pixel_axis = PIXEL_AXIS
            rgn.autocontrast = AUTOCONTRAST
            plotData(current_spe.get_data(frames=[0], rois=[idx_rgn])[0][0],
                rgn.ax, rgn.region_wavelengths, '%s, ROI %02d'%
                (current_spe.file_name, idx_rgn+1), pixAxis=PIXEL_AXIS)
            print_metadata(current_spe, rgn.current_frame)
        print('\n')
    if filenames:
        stop_prompt()
