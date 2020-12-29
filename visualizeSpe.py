# -*- coding: utf-8 -*-
"""
Created on Mon Dec  7 15:32:25 2020

@author: sliakat
"""

from readSpe import readSpe
from matplotlib import pyplot as plt
import numpy as np
import tkinter as tk
from tkinter import filedialog

root = tk.Tk()
root.withdraw()

regionToDisplay=0 #this will display ROI #1

filePath = filedialog.askopenfilename()

totalData = readSpe(filePath)
waveCal=False
try:
    xmlFooter = totalData.xmlFooter
    wavelengths = totalData.wavelengths
    waveCal=True
except:
    print('No wavelength calibration in spe.')

dataList = totalData.data

#image contrast adjustments
sortedRegion=np.sort(np.reshape(dataList[regionToDisplay],(np.size(dataList[regionToDisplay]))))
display_min = sortedRegion[np.int(np.floor(0.05*np.size(dataList[regionToDisplay])-1))]
display_max = sortedRegion[np.int(np.ceil(0.95*np.size(dataList[regionToDisplay])-1))]
if display_min < 1:
    display_min = 1

# if display_max > 65535:
#     display_max = 65535

figCount=0


for k in range(0,np.size(dataList[regionToDisplay],0)): #show up to 5 figs, starting with whatever first input in range is 
    #data = dataList[regionToDisplay][:,:,k]
    data = dataList[regionToDisplay][k,:,:]
    fig = plt.figure('Frame %d'%(k+1))
    ax = fig.add_subplot(111)
    if np.size(data,0)==1:
        try:
            ax.plot(wavelengths,data[0])
            ax.set_xlabel('Wavelength (nm)')
        except:
            ax.plot(data[0])
        ax.set_ylabel('Intensity (counts)')
    else:
        if waveCal==True:
            #aspect=(np.size(data,0)/np.size(data,1))
            aspect = 0.25
            ax.imshow(data,vmin=display_min,vmax=display_max,cmap='gray',extent=[wavelengths[0],wavelengths[-1],np.size(data,0),0],aspect=aspect)
            ax.set(xlabel='Wavelength (nm)')
        else:
            ax.imshow(data,origin='upper',vmin=display_min,vmax=display_max,cmap='gray')
            ax.set(xlabel='Column')
        ax.set(ylabel='Row')
    figCount+=1        
    if figCount>4:
        break