# -*- coding: utf-8 -*-
"""
Created on Tue Apr 19 23:38:08 2022

@author: sabbi
"""

#function to plot images in the form of numpy arrays -- use to build format-specific viewers

import numpy as np
from matplotlib import pyplot as plt
from matplotlib.widgets import RectangleSelector, Slider
import matplotlib

""" font = {'family' : 'normal',
        'weight' : 'bold',
        'size'   : 16}
matplotlib.rc('font', **font) """

#global variable
currFrame = 1
#font sizes (global)
fontTitle = 36
fontLabels = 24
fontStats = 18

#return this object to keep things in scope
class FigContainer():
    def __init__(self,fig,ax,RS,slider,sliderConnect):
        self.fig_ = fig
        self.ax_ = ax
        self.RS_ = RS
        self.slider_ = slider
        self.sliderConnect_ = sliderConnect
        
def GetStats(data, x1, x2, y1, y2):
    regionDat = data[y1:y2,x1:x2]
    regMean = np.mean(regionDat.flatten())
    regDev = np.std(regionDat.flatten())
    regMin = np.min(regionDat.flatten())
    regMax = np.max(regionDat.flatten())
    return regMean,regDev,regMin,regMax

def WriteStats(axis, string):
    global fontStats
    #clear previous text object
    for txt in axis.texts:
        txt.set_visible(False)
    axis.text(0,1.13,string, fontsize=fontStats, verticalalignment='top', color = 'r', transform=axis.transAxes)
    plt.draw()
    plt.pause(.001)

#here, im is passed in as 2D numpy        
def displayImage(im, axis, name, frame: int=1,*, xBound1: int=-1, xBound2: int=-1, yBound1: int=-1, yBound2: int=-1):
    global currFrame, fontTitle, fontLabels
    if xBound1 > 0 and xBound2 > 10 and yBound1 > 0 and yBound2 > 10:
            display_min = int(np.percentile(im[yBound1:yBound2,xBound1:xBound2].flatten(),5))
            display_max = int(np.percentile(im[yBound1:yBound2,xBound1:xBound2].flatten(),95))
    else:
        display_min = int(np.percentile(im.flatten(),5))
        display_max = int(np.percentile(im.flatten(),95))
    if display_min < 1:
        display_min = 1
    if display_max <1:
        display_max = 1
    axis.clear()
    axis.imshow(im,vmin=display_min,vmax=display_max,cmap='gray')
    axis.set_xlabel('Column',fontsize=fontLabels)
    axis.set_ylabel('Row',fontsize=fontLabels)
    axis.set_title('%s, Frame %d'%(name,currFrame), fontsize=fontTitle)
    #plt.pause(.001)
    plt.show(block=True)
    
#callback for slider
def update_frame(val,data,ax,name):    #pass in full data
    global currFrame
    currFrame = int(val)
    displayImage(data[currFrame-1,:,:],ax,name)
        
def SliderGen(axis,maximum):
    fp = axis.get_position()        #get position of the figure
    axvert = plt.axes([fp.x0-0.08, fp.y0, 0.0225, 0.75])
    return Slider(ax=axvert,label='%d Total Frames'%(maximum), valmin=1, valmax=maximum, valinit=1, orientation="vertical", valstep=1)

def box_select_callback(eclick, erelease, axis, name):
        x1, y1 = int(np.floor(eclick.xdata)), int(np.floor(eclick.ydata))
        x2, y2 = int(np.floor(erelease.xdata)), int(np.floor(erelease.ydata))
        data = np.array(axis.get_images().pop()._A)
        mean, dev, regMin, regMax = GetStats(data,x1,x2,y1,y2)
        statsString = 'Region Mean: %0.2f         Region Min: %0.2f\n Region Std: %0.2f         Region Max: %0.2f'%(mean,regMin,dev,regMax)
        displayImage(data,axis,name,xBound1=x1,xBound2=x2,yBound1=y1,yBound2=y2)        
        WriteStats(axis, statsString)        
        plt.draw()
        plt.pause(.001)

def RectSelect(axis, name):
    return RectangleSelector(axis, lambda eclick, erelease: box_select_callback(eclick, erelease, axis, name),
                                       drawtype='box', useblit=True,
                                       button=[1, 3],  # disable middle button
                                       minspanx=10, minspany=10,
                                       spancoords='pixels',
                                       interactive=True)

#this is the function that gets called from the outside
def PlotNumpy(data, filename):
    if len(np.shape(data)) == 2:
        data = np.reshape(data,[1,np.shape(data)[0],np.shape(data)[1]])
    if len(np.shape(data)) > 3:
        print('Data must be a 2D or 3D numpy array.')
        return
    framesMax = np.shape(data)[0]
    
    fig = plt.figure('Image: %s'%(filename))
    ax = fig.add_subplot(1,1,1)
    slider=SliderGen(ax, framesMax)
    sliderConnect=slider.on_changed(lambda val: update_frame(val,data,ax,filename))
    RS=RectSelect(ax,filename)
    displayImage(data[0], ax, filename)
    return FigContainer(fig,ax,RS,slider,sliderConnect)
        