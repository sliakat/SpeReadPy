# -*- coding: utf-8 -*-
"""
Created on Tue Feb  8 10:13:16 2022

@author: sliakat
"""

#includes main function so one can just run this script and pick spe file(s) to view

from readSpe import readSpe
import numpy as np
import tkinter
from tkinter import filedialog
import matplotlib
from matplotlib.backends.backend_tkagg import (
    FigureCanvasTkAgg, NavigationToolbar2Tk)
from matplotlib.figure import Figure
from matplotlib.widgets import RectangleSelector
from matplotlib.widgets import SpanSelector

class frameInfo:
    def __init__(self):
        self._currFrame = 1
    @property
    def frame(self):
        return self._currFrame
    @frame.setter
    def frame(self, val):
        if (val < 1):
            raise ValueError("Frame cannot be set to <0")
        else:
            self._currFrame = val
    def Reset(self):
        self._currFrame = 1

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

#helper function to get pixel coords if wavelength cal is on x-axis
def findXPixels(wl,x1,x2):
    x1Pix = int(np.argmin(np.abs(wl - x1)))
    x2Pix = int(np.argmin(np.abs(wl - x2)))
    return x1Pix,x2Pix
    
#callback for scale
def update_frame(new_val,data,ax,wave,pixAxis,canvas):    #pass in full data
    global pixelAxis
    plotData(data[int(new_val)-1,:,:],ax,wave,canvas,pixAxis=pixelAxis)

def plotData(data,ax,wave,canvas,*,pixAxis: bool=False, xBound1: int=-1, xBound2: int=-1, yBound1: int=-1, yBound2: int=-1):     #pass in frame
    #image contrast adjustments
    if xBound1 > 0 and xBound2 > 10 and yBound1 > 0 and yBound2 > 10:
            display_min = int(np.percentile(data[yBound1:yBound2,xBound1:xBound2].flatten(),5))
            display_max = int(np.percentile(data[yBound1:yBound2,xBound1:xBound2].flatten(),95))
    else:
        display_min = int(np.percentile(data.flatten(),5))
        display_max = int(np.percentile(data.flatten(),95))
    if display_min < 1:
        display_min = 1
    if display_max <1:
        display_max = 1  
        
    ax.clear()
    #plotting
    if np.size(data,0)==1:
        if len(wave) > 10:
            ax.plot(wave,data[0])
            ax.set_xlabel('Wavelength (nm)')
            ax.set(xlim=(wave[0],wave[-1]))
        else:
            ax.plot(data[0])
            ax.set_xlabel('Pixels')
            ax.set(xlim=(0,np.size(data[0])))
        ax.set_ylabel('Intensity (counts)')
    else:
        if len(wave) > 10 and pixAxis==False:
            aspect = 0.25
            ax.imshow(data,vmin=display_min,vmax=display_max,cmap='gray',extent=[wave[0],wave[-1],np.size(data,0),0],aspect=aspect)   
            ax.set(xlabel='Wavelength (nm)')
        else:
            ax.imshow(data,origin='upper',vmin=display_min,vmax=display_max,cmap='gray')
            ax.set(xlabel='Column')
        ax.set(ylabel='Row')
    canvas.draw()
    canvas.get_tk_widget().pack(side=tkinter.TOP, fill=tkinter.BOTH, expand=1)  #need this line for plot to show    
   
#gets data out of spe file
def parseSpe(filename,*,region: int=0, suppress: bool=True):    
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
    data = dataList[region]    
    return (data, xmlFooter, wavelengths)

def tkSliderSetup(tkWindow, framesMax, data, ax, wl, canvas):
    global pixelAxis
    return tkinter.Scale(tkWindow, from_=1, to=(framesMax), orient=tkinter.HORIZONTAL,
                              command=(lambda new_val: update_frame(new_val,data,ax,wl,pixelAxis,canvas)), label="Frame #")

#display helpers
def WriteStats(axis, string):
    #clear previous text object
    for txt in axis.texts:
        txt.set_visible(False)
    axis.text(0,1.15,string, fontsize=10, verticalalignment='top', color = 'r', transform=axis.transAxes)
    

def GetStats(data, x1, x2, y1, y2):
    regionDat = data[y1:y2,x1:x2]
    regMean = np.mean(regionDat.flatten())
    regDev = np.std(regionDat.flatten())
    regMin = np.min(regionDat.flatten())
    regMax = np.max(regionDat.flatten())
    return regMean,regDev,regMin,regMax
    
#callback for box selection
def box_select_callback(eclick, erelease, axis, canvas, wl):
    global pixelAxis, autoContrast
    x1, y1 = int(np.floor(eclick.xdata)), int(np.floor(eclick.ydata))
    x2, y2 = int(np.floor(erelease.xdata)), int(np.floor(erelease.ydata))
    if not pixelAxis and len(wl) > 10:
        x1, x2 = findXPixels(wl, x1, x2)
    data = np.array(axis.get_images().pop()._A)
    mean, dev, regMin, regMax = GetStats(data,x1,x2,y1,y2)
    statsString = 'Region Mean: %0.2f         Region Min: %0.2f\n Region Std: %0.2f         Region Max: %0.2f'%(mean,regMin,dev,regMax)    
    if autoContrast:
        plotData(data,axis,wl,canvas,pixAxis=pixelAxis,xBound1=x1,xBound2=x2,yBound1=y1,yBound2=y2)
    else:
        plotData(data,axis,wl,canvas,pixAxis=pixelAxis)
    # if x2 > 0 and y2 > 0:
    #     display_min = int(np.percentile(data[y1:y2,x1:x2].flatten(),5))
    #     display_max = int(np.percentile(data[y1:y2,x1:x2].flatten(),95))
    # axis.imshow(data,origin='upper',vmin=display_min,vmax=display_max,cmap='gray')
    
    WriteStats(axis, statsString)
    canvas.draw()
    canvas.get_tk_widget().pack(side=tkinter.TOP, fill=tkinter.BOTH, expand=1)  #need this line for plot to show
    
#callback for line selection
def StatsLinePlot(xmin, xmax, axis, canvas, wl):
    #data shape here will be (1, cols)
    #print(np.floor(xmin),np.floor(xmax))
    if not pixelAxis and len(wl) > 10:
        xmin, xmax = findXPixels(wl, xmin, xmax)    
    regionDat = axis.get_lines()[0].get_data()[1][int(np.floor(xmin)):int(np.floor(xmax))]
    mean = np.mean(regionDat)
    dev = np.std(regionDat)
    statsString = 'Region Mean: %0.2f\n Region Std: %0.2f'%(mean,dev)
    WriteStats(axis, statsString)
    canvas.draw()
    canvas.get_tk_widget().pack(side=tkinter.TOP, fill=tkinter.BOTH, expand=1)  #need this line for plot to show

#matplotlib widget for box selection
def RectSelect(axis, canvas, wl):
    return RectangleSelector(axis, lambda eclick, erelease: box_select_callback(eclick, erelease, axis, canvas, wl),
                                       drawtype='box', useblit=True,
                                       button=[1, 3],  # disable middle button
                                       minspanx=10, minspany=10,
                                       spancoords='pixels',
                                       interactive=True)

#matplotlib widget for line selection
def SpanSelect(axis,canvas,wl):
    return SpanSelector(axis, lambda xmin, xmax: StatsLinePlot(xmin, xmax, axis, canvas, wl), 'horizontal', span_stays=True)

   
if __name__=="__main__":
    matplotlib.use('tkagg')     #matplotlib backend
    #these objects append to keep data in scope in case they are needed w/ interactive console, labeling them *Total to distinguish
    canvasTotal=Container()
    tkWindowsTotal = Container()
    tkSliderTotal = Container()
    tkToolbarTotal = Container()
    dataTotal = Container()
    xmlTotal = Container()
    axTotal = Container()
    wlTotal = Container()
    RSTotal = Container()
    SSTotal = Container()
    
    #globals
    pixelAxis = False
    autoContrast = False
       
    filenames = filedialog.askopenfilenames(title='Select Spe Files',filetypes=[('spe files','*.spe')])
    
    for i in range(len(filenames)):
        nameSplit = (filenames[i].rsplit('/',maxsplit=1)[1]).rsplit(r'.',maxsplit=1)[0]     #'/' for tk, '\\' for System.Windows.Forms
        tkWindowsTotal.Add(tkinter.Tk())
        tkWindowsTotal.Get(i).title(nameSplit)
        fig = Figure(figsize=(5, 4), dpi=200)
        d,x,w = parseSpe(filenames[i])
        #append lists
        dataTotal.Add(d)
        framesMax = np.size(dataTotal.Get(i),axis=0)
        xmlTotal.Add(x)
        wlTotal.Add(w)
        axTotal.Add(fig.add_subplot(111))
        canvasTotal.Add(FigureCanvasTkAgg(fig, master=tkWindowsTotal.Get(i)))
        
        #tk slider and toolbar-- need to do in main to retain scope     
        tkSliderTotal.Add(tkSliderSetup(tkWindowsTotal.Get(i), framesMax, dataTotal.Get(i), axTotal.Get(i), wlTotal.Get(i), canvasTotal.Get(i)))
        tkSliderTotal.Get(i).pack(side=tkinter.BOTTOM)
        tkToolbarTotal.Add(NavigationToolbar2Tk(canvasTotal.Get(i), tkWindowsTotal.Get(i)))
        tkToolbarTotal.Get(i).update()
        canvasTotal.Get(i).get_tk_widget().pack(side=tkinter.TOP, fill=tkinter.BOTH, expand=1)
        plotData(dataTotal.Get(i)[0,:,:],axTotal.Get(i),wlTotal.Get(i),canvasTotal.Get(i), pixAxis=pixelAxis)
        
        #rectangle / span selectors
        if np.size(dataTotal.Get(i),1)>1:
            RSTotal.Add(RectSelect(axTotal.Get(i),canvasTotal.Get(i),wlTotal.Get(i)))
        else:
            SSTotal.Add(SpanSelect(axTotal.Get(i),canvasTotal.Get(i),wlTotal.Get(i)))
        
    tkinter.mainloop()