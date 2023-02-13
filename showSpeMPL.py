# -*- coding: utf-8 -*-
"""
Created on Wed Feb  9 16:03:10 2022

@author: sliakat
"""

from readSpe import readSpe
import numpy as np
import tkinter as tk
from tkinter import filedialog
from tkinter import simpledialog
from matplotlib import pyplot as plt
from matplotlib.widgets import RectangleSelector, SpanSelector, Slider
import xml.etree.ElementTree as ET
import xml.dom.minidom as dom
import warnings
from scipy import interpolate
from matplotlib import cm
from matplotlib.colors import ListedColormap, LinearSegmentedColormap
import signal
import threading

#generic container class for the various objects used in this script
class Container:
    def __init__(self):
        self._content = list()
    def Add(self, val):
        self._content.append(val)
    def Get(self,index: int=-1):
        if index < 0:
            raise ValueError("index cannot be < 0")
        else:
            return self._content[index]
    def Reset(self):
        self._content = list()
        
class Region:
    def __init__(self):
        self.startX_ = 0
        self.startY_ = 0
        self.ogWidth_ = 0
        self.ogHeight_ = 0
        self.width_ = 0
        self.height_ = 0
        self.xBin_ = 0
        self.yBin_ = 0
    def Set(self,x,y,ogWidth,ogHeight,width,height,xBin,yBin):
        self.startX_ = x
        self.staryY_ = y
        self.ogWidth_ = ogWidth
        self.ogHeight_ = ogHeight
        self.width_ = width
        self.height_ = height
        self.xBin_ = xBin
        self.yBin_ = yBin

class PlotObject():
    def __init__(self):
        pass

#helper function to get pixel coords if wavelength cal is on x-axis
def findXPixels(wl,x1,x2):
    x1Pix = int(np.argmin(np.abs(wl - x1)))
    x2Pix = int(np.argmin(np.abs(wl - x2)))
    return x1Pix,x2Pix

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
    
#callback for scale
def update_frame(val,data,fig,ax,wave,name):    #pass in full data
    global pixelAxis, currFrame
    fig.canvas.draw_idle()
    currFrame = int(val)
    plotData(data[currFrame-1,:,:],ax,wave,name,currFrame,pixAxis=pixelAxis)
    
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
    global bits, bg, fontTitle, fontLabels  
    flatData = data.flatten()
    #image contrast adjustments
    if xBound1 > 0 and xBound2 > 10 and yBound1 > 0 and yBound2 > 10:
            display_min = int(np.percentile(data[yBound1:yBound2,xBound1:xBound2].flatten(),5))
            display_max = int(np.percentile(data[yBound1:yBound2,xBound1:xBound2].flatten(),95))
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
        if len(wave) > 10 and pixAxis==False:
            ax.plot(wave,data[0])
            ax.set_xlabel('Wavelength (nm)',fontsize=fontLabels)
            ax.set(xlim=(wave[0],wave[-1]))
        else:
            ax.plot(data[0])
            ax.set_xlabel('Pixels',fontsize=fontLabels)
            ax.set(xlim=(0,np.size(data[0])))
        ax.set_ylabel('Intensity (counts)',fontsize=fontLabels)
    else:
        # colorMap = 'gray'
        # if bg==False:
        #     colorMap = GenCustomCmap(flatData,bits)
        if len(wave) > 10 and pixAxis==False:
            waveRange = (wave[-1] - wave[0])
            # if waveRange < 50:
            #     aspect = waveRange/np.size(data,0)
            # else:
            #     aspect = 0.25
            aspect = (waveRange/np.size(data,0))/1.75
            ax.imshow(data,vmin=display_min,vmax=display_max,cmap='gray',extent=[wave[0],wave[-1],np.size(data,0),0],aspect=aspect)
            ax.set_xlabel('Wavelength (nm)',fontsize=fontLabels)
        else:
            ax.imshow(data,origin='upper',vmin=display_min,vmax=display_max,cmap='gray')
            ax.set_xlabel('Column',fontsize=fontLabels)
        ax.set_ylabel('Row',fontsize=fontLabels)
        if bg==False:
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
    ax.set_title(axName, fontsize=fontTitle)
    for label in (ax.get_xticklabels() + ax.get_yticklabels()):
        label.set_fontsize(fontLabels)
    plt.show()

def ParseXmlForRegion(xmlStr, region):
    startX = -1
    width = -1
    if len(xmlStr)>50:
        xmlRoot = ET.fromstring(xmlStr)
        #find DataHistories
        for child in xmlRoot:
            if 'Calibrations'.casefold() in child.tag.casefold():
                counter = 0
                for child1 in child:                    
                    if 'SensorMapping'.casefold() in child1.tag.casefold():
                        if counter == region:
                            startX = np.int32(child1.get('x'))
                            startY = np.int32(child1.get('y'))
                            ogWidth = np.int32(child1.get('width'))
                            ogHeight = np.int32(child1.get('height'))
                            xbin = np.int32(child1.get('xBinning'))
                            ybin = np.int32(child1.get('yBinning'))
                            width = np.int32(ogWidth / xbin)
                            height = np.int32(ogHeight / ybin)
                            rgn.Set(startX, startY, ogWidth, ogHeight, width, height, xbin, ybin)
                            break
                        else:
                            counter += 1
    return startX, width
       
#gets data out of spe file
def parseSpe(filename,*,suppress: bool=True):
    region = 0    
    totalData = readSpe(filename)
    wavelengths=[0]
    xmlFooter = 'xml footer does not exist for spe2.0 files' 
    try:
        xmlFooter = totalData.xmlFooter        
        wavelengths = totalData.wavelengths        
    except:
        if not suppress:
            print('No wavelength calibration in spe.')            
    dataList = totalData.data
    if len(dataList) > 1:
        region = simpledialog.askinteger('Pick Region', 'Pick ROI:\n0-%d'%(len(dataList)-1))
    if region >= len(dataList) or region < 0:
        print('Invalid ROI entered, showing ROI #1')
        region = 0
    data = dataList[region]
    startX, width = ParseXmlForRegion(xmlFooter,region)
    if len(wavelengths) > 2:        
        if startX > -1 and width > 0:
            wavelengths = wavelengths[startX:(startX+width)]
    print('%d ROIs in this spe file, showing ROI %d'%(len(dataList),region+1))
    return (data, xmlFooter, wavelengths)

#display helpers
def WriteStats(axis, string):
    global fontStats
    #clear previous text object
    for txt in axis.texts:
        txt.set_visible(False)
    axis.text(0,1.15,string, fontsize=fontStats, verticalalignment='top', color = 'r', transform=axis.transAxes)
    

def GetStats(data, x1, x2, y1, y2):
    regionDat = data[y1:y2,x1:x2]
    regMean = np.mean(regionDat.flatten())
    regDev = np.std(regionDat.flatten())
    regMin = np.min(regionDat.flatten())
    regMax = np.max(regionDat.flatten())
    return regMean,regDev,regMin,regMax
    
#callback for box selection
def box_select_callback(eclick, erelease, axis, wl, name):
    global pixelAxis, autoContrast, currFrame
    x1, y1 = int(np.floor(eclick.xdata)), int(np.floor(eclick.ydata))
    x2, y2 = int(np.floor(erelease.xdata)), int(np.floor(erelease.ydata))
    if not pixelAxis and len(wl) > 10:
        x1, x2 = findXPixels(wl, x1, x2)
    data = np.array(axis.get_images().pop()._A)
    centerRow = np.int32(np.floor(np.shape(data)[0]/2))
    mean, dev, regMin, regMax = GetStats(data,x1,x2,y1,y2)
    fwhm = FWHM(data[centerRow,x1:x2])
    statsString = 'Region Mean: %0.2f          Region Min: %0.2f\nRegion Std: %0.2f          Region Max: %0.2f\nMin/Mean Ratio: %0.3f          FWHM of horizontal slice: %0.3f pix'%(mean,regMin,dev,regMax,(regMin/mean),fwhm)    
    if autoContrast:
        plotData(data,axis,wl,name,currFrame,pixAxis=pixelAxis,xBound1=x1,xBound2=x2,yBound1=y1,yBound2=y2)
    else:
        plotData(data,axis,wl,name,currFrame,pixAxis=pixelAxis)
    # if x2 > 0 and y2 > 0:
    #     display_min = int(np.percentile(data[y1:y2,x1:x2].flatten(),5))
    #     display_max = int(np.percentile(data[y1:y2,x1:x2].flatten(),95))
    # axis.imshow(data,origin='upper',vmin=display_min,vmax=display_max,cmap='gray')
    
    WriteStats(axis, statsString)
    plt.show()
        
#callback for line selection
def StatsLinePlot(xmin, xmax, axis, wl):
    #data shape here will be (1, cols)
    #print(np.floor(xmin),np.floor(xmax))
    if not pixelAxis and len(wl) > 10:
        xmin, xmax = findXPixels(wl, xmin, xmax)    
    regionDat = axis.get_lines()[0].get_data()[1][int(np.floor(xmin)):int(np.floor(xmax))]
    mean = np.mean(regionDat)
    dev = np.std(regionDat)
    fwhm = FWHM(regionDat)
    statsString = 'Region Mean: %0.2f\n Region Std: %0.2f\nFWHM: %0.3f pix'%(mean,dev,fwhm)
    WriteStats(axis, statsString)
    plt.show()
    
#matplotlib widget for box selection
def RectSelect(axis, wl, name):
    return RectangleSelector(axis, lambda eclick, erelease: box_select_callback(eclick, erelease, axis, wl, name),
                                       drawtype='box', useblit=True,
                                       button=[1, 3],  # disable middle button
                                       minspanx=10, minspany=10,
                                       spancoords='pixels',
                                       interactive=True)

#matplotlib widget for line selection
def SpanSelect(axis,wl,name):
    return SpanSelector(axis, lambda xmin, xmax: StatsLinePlot(xmin, xmax, axis, wl), 'horizontal', span_stays=True)

def SliderGen(axis,maximum):
    fp = axis.get_position()        #get position of the figure
    axvert = plt.axes([fp.x0-0.08, fp.y0, 0.0225, 0.75])
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
        
def PrintSelectedXmlEntries(xmlStr):
    global bits, bg    
    if len(xmlStr)>50:
        xmlRoot = ET.fromstring(xmlStr)
        #find DataHistories
        for child in xmlRoot:
            if 'DataHistories'.casefold() in child.tag.casefold():
                for child1 in child:
                    if 'DataHistory'.casefold() in child1.tag.casefold():
                        for child2 in child1:
                            if 'Origin'.casefold() in child2.tag.casefold():
                                print('LF version used:\t%s'%(child2.get('softwareVersion')))
                                for child3 in child2:
                                    if 'Experiment'.casefold() in child3.tag.casefold():
                                        for child4 in child3:
                                            if 'System'.casefold() in child4.tag.casefold():
                                                for child2 in child4:
                                                    if 'Cameras'.casefold() in child2.tag.casefold():
                                                        for child3 in child2:
                                                            if 'Camera'.casefold() in child3.tag.casefold():
                                                                print('Camera model: %s\n\tSN: %s'%(child3.get('model'),child3.get('serialNumber')))
                                                    if 'Spectrometers'.casefold() in child2.tag.casefold():
                                                        for child3 in child2:
                                                            if 'Spectrometer'.casefold() in child3.tag.casefold():
                                                                print('Spectrograph model: %s\n\tSN: %s'%(child3.get('model'),child3.get('serialNumber')))                                            
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
                                                                                        print('Camera sensor:\t\t%s'%(child6.text))
                                                                                    if 'Pixel'.casefold() in child6.tag.casefold():
                                                                                        for child7 in child6:
                                                                                            if ('Width'.casefold() in child7.tag.casefold()) and ('GapWidth'.casefold() not in child7.tag.casefold()):
                                                                                                print('Pixel width:\t\t%sum'%(child7.text))
                                                                            if 'Temperature'.casefold() in child5.tag.casefold():
                                                                                for child6 in child5:
                                                                                    if 'Reading'.casefold() in child6.tag.casefold():
                                                                                        print('Temperature:\t\t%sC, Status: '%(child6.text),end='')
                                                                                    if ('Status'.casefold() in child6.tag.casefold()) and ('CoolingFanStatus'.casefold() not in child6.tag.casefold()) and ('VacuumStatus'.casefold() not in child6.tag.casefold()):
                                                                                        print('%s'%(child6.text))
                                                                                    if ('VacuumStatus'.casefold() in child6.tag.casefold()):
                                                                                        print('Vacuum Status:\t\t%s'%(child6.text))
                                                                            if 'Cleaning'.casefold() in child5.tag.casefold():
                                                                                for child6 in child5:
                                                                                    if 'CleanSerialRegister'.casefold() in child6.tag.casefold():
                                                                                        if child6.get('relevance') != 'False':
                                                                                            print('Clean Serial Reg:\t%s'%(child6.text))
                                                                                    if 'CleanUntilTrigger'.casefold() in child6.tag.casefold():
                                                                                        if child6.get('relevance') != 'False':
                                                                                            print('Clean Until Trig:\t%s'%(child6.text))
                                                                    if 'ShutterTiming'.casefold() in child4.tag.casefold():
                                                                        for child5 in child4:
                                                                            if 'ExposureTime'.casefold() in child5.tag.casefold():
                                                                                print('Exposure Time:\t\t%s ms'%(child5.text))
                                                                            if 'Mode'.casefold() in child5.tag.casefold():
                                                                                print('Shutter Mode:\t\t%s'%(child5.text))
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
                                                                            print('Gating:\t\t\t\t%s\nGate Width:\t\t\t%0.3f ns\nGate Delay:\t\t\t%0.3f ns'%(gateMode,startWidth,startDelay))
                                                                        if gateMode == 'Sequential' or gateMode == 'Dif':
                                                                            print('Gating:\t\t\t\t%s\nStart Width:\t\t%0.3f ns\nStart Delay:\t\t%0.3f ns\nEnd Width:\t\t\t%0.3f ns\nEnd Delay:\t\t\t%0.3f ns'
                                                                                  %(gateMode,startWidth,startDelay,endWidth,endDelay))
                                                                    if 'Intensifier'.casefold() in child4.tag.casefold():
                                                                        for child5 in child4:
                                                                            if 'Gain'.casefold() in child5.tag.casefold():
                                                                                if child5.get('relevance') != 'False':
                                                                                    print('Intensifier Gain:\t%sx'%(child5.text))
                                                                            if 'Status'.casefold() in child5.tag.casefold():
                                                                                print('Intensifier Status:\t%s'%(child5.text))
                                                                            if 'EMIccd'.casefold() in child5.tag.casefold():
                                                                                for child6 in child5:
                                                                                    if ('Gain'.casefold() in child6.tag.casefold()) and ('GainControlMode'.casefold() not in child6.tag.casefold()):
                                                                                        if child6.get('relevance') != 'False':
                                                                                            print('EMI Gain:\t\t\t%sx'%(child6.text))
                                                                                
                                                                    if 'ReadoutControl'.casefold() in child4.tag.casefold():
                                                                        for child5 in child4:
                                                                            if 'Mode'.casefold() in child5.tag.casefold():
                                                                                print('Readout Mode:\t\t%s'%(child5.text))
                                                                            if 'Time'.casefold() in child5.tag.casefold():
                                                                                print('Readout Time:\t\t%0.3f ms'%(np.float32(child5.text)))
                                                                            if 'StorageShiftRate'.casefold() in child5.tag.casefold():
                                                                                if child5.get('relevance') != 'False':
                                                                                    print('Storage Shift:\t\t%sus'%(child5.text))
                                                                            if 'VerticalShiftRate'.casefold() in child5.tag.casefold():
                                                                                if child5.get('relevance') != 'False':
                                                                                    print('Vertical Shift:\t\t%sus'%(child5.text))
                                                                            if 'PortsUsed'.casefold() in child5.tag.casefold():
                                                                                print('Ports Used:\t\t\t%s'%(child5.text))
                                                                            if 'Accumulations'.casefold() in child5.tag.casefold():
                                                                                print('Accumulations:\t\t%s'%(child5.text))
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
                                                                                    print('Trigger:\t\t\tInternal, %0.3f Hz'%(triggerFreq))
                                                                    if 'Adc'.casefold() in child4.tag.casefold():
                                                                        for child5 in child4:
                                                                            if 'Speed'.casefold() in child5.tag.casefold():
                                                                                if child5.get('relevance') != 'False':
                                                                                    print('ADC Speed:\t\t\t%s MHz'%(child5.text))
                                                                            if 'AnalogGain'.casefold() in child5.tag.casefold():
                                                                                if child5.get('relevance') != 'False':
                                                                                    print('Analog Gain:\t\t%s'%(child5.text))
                                                                            if 'EMGain'.casefold() in child5.tag.casefold():
                                                                                if child5.get('relevance') != 'False':
                                                                                    print('EM Gain:\t\t\t%sx'%(child5.text))
                                                                            if 'Quality'.casefold() in child5.tag.casefold():
                                                                                print('ADC Quality:\t\t%s'%(child5.text))
                                                                            if 'CorrectPixelBias'.casefold() in child5.tag.casefold():
                                                                                print('PBC On?:\t\t\t%s'%(child5.text))
                                                                            if 'BitDepth'.casefold() in child5.tag.casefold():
                                                                                bits = np.int32(child5.text)
                                                                    if 'Acquisition'.casefold() in child4.tag.casefold():
                                                                        for child5 in child4:
                                                                            if 'FrameRate'.casefold() in child5.tag.casefold():
                                                                                print('Frame Rate:\t\t\t%0.3f fps'%(np.float32(child5.text)))
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
                                                                                            print('Frame Combination:\t%s of %d frames.'%(method,framesCombined))
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
                                                                                                    bg = True
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
                                                                                    print('Correction(s):\t\t',end='')
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
                                                                                print('Grating:\t\t\t%s'%(child5.text),end='')
                                                                            if 'CenterWavelength'.casefold() in child5.tag.casefold():
                                                                                print(', CWL: %0.3f nm'%(np.float64(child5.text)))
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
                                                                                    print('Step and Glue:\t\t%0.3f nm to %0.3f nm'%(startWL,endWL))
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
                                                                            print('Calibration(s):\t\t',end='')
                                                                            for i in range(0,len(calibrationList)):
                                                                                print('%s'%(calibrationList[i]),end='')
                                                                                if i <len(calibrationList)-1:
                                                                                    print(', ',end='')        
    print('')
    print('Viewing Region:\t\t%d x %d, xBin %d, yBin %d\n\tFull ROI Info: [%d, %d, %d, %d, %d, %d]'%(rgn.ogWidth_,rgn.ogHeight_,rgn.xBin_,rgn.yBin_,
                                                                                                           rgn.startX_,rgn.startY_,rgn.width_,rgn.height_,rgn.xBin_,rgn.yBin_))

def PlotFunction(i, nameSplit, currFrame, pixelAxis):
    axTotal.Add(figTotal.Get(i).add_subplot(111))              
    MPSliderTotal.Add(SliderGen(axTotal.Get(i),framesMax))
    MPSliderTotal.Get(i).label.set_size(fontLabels)        
    plotData(dataTotal.Get(i)[0,:,:],axTotal.Get(i),wlTotal.Get(i),nameSplit,currFrame,pixAxis=pixelAxis)        
    #register slider to callback
    MPSliderConnect.Add(MPSliderTotal.Get(i).on_changed((lambda val: update_frame(val,dataTotal.Get(i),figTotal.Get(i),axTotal.Get(i),wlTotal.Get(i),nameSplit))))
    #rectangle / span selectors
    if np.size(dataTotal.Get(i),1)>1:
        RSTotal.Add(RectSelect(axTotal.Get(i),wlTotal.Get(i),nameSplit))
    else:
        SSTotal.Add(SpanSelect(axTotal.Get(i),wlTotal.Get(i),nameSplit))

def StopPrompt():
    print('Press Enter to end script')
    input()

if __name__=="__main__":  
    warnings.filterwarnings("ignore")
    #these objects append to keep data in scope in case they are needed w/ interactive console, labeling them *Total to distinguish    
    dataTotal = Container()
    xmlTotal = Container()
    xmlFormat = list()
    figTotal = Container()
    axTotal = Container()
    wlTotal = Container()
    RSTotal = Container()
    SSTotal = Container()
    MPSliderTotal = Container()
    MPSliderConnect = Container()
    rgn = Region()
    threads = []
    
    #globals
    pixelAxis = False
    autoContrast = True
    bg = False
    bits = 16
    currFrame = 1
    waitTime = 5   #wait n secs for user input at the end and then end program
    #font sizes (global)
    fontTitle = 36
    fontLabels = 24
    fontStats = 18
    
    #use tk for file dialog
    root = tk.Tk()
    filenames = filedialog.askopenfilenames(title='Select Spe Files',filetypes=[('spe files','*.spe'),('spe files','*.SPE')])
    root.withdraw()

    #makes figures spawn in individual threads
    plt.ion()
    
    for i in range(len(filenames)): #originally intended to open multiple files in one kernel, but slider doesn't seem to connect to multiple figs.
                                    #for comparison of multiple images, open each in separate kernel
        nameSplit = (filenames[i].rsplit('/',maxsplit=1)[1]).rsplit(r'.',maxsplit=1)[0]     #'/' for tk, '\\' for System.Windows.Forms   
        print('Information for %s:'%(nameSplit))     
        figTotal.Add(plt.figure(nameSplit))
        d,x,w = parseSpe(filenames[i])
        #append lists
        dataTotal.Add(d)
        framesMax = np.size(dataTotal.Get(i),axis=0)
        xmlTotal.Add(x)
        try:
            xmlFormat.append(dom.parseString(xmlTotal.Get(i)).toprettyxml())
        except:
            pass
        PrintSelectedXmlEntries(xmlTotal.Get(i))
        wlTotal.Add(w)
        PlotFunction(i, nameSplit, currFrame, pixelAxis)
    StopPrompt()
