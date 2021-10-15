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

plt.close(fig='all')
root = tk.Tk()
root.withdraw()

regionToDisplay=0 #this will display ROI #1

filePath = filedialog.askopenfilenames()    #can select multiple files
for i in range(0,len(filePath)):
    totalData = readSpe(filePath[i])
    waveCal=False
    try:
        xmlFooter = totalData.xmlFooter
        wavelengths = totalData.wavelengths
        waveCal=True
    except:
        print('No wavelength calibration in spe.')
    
    dataList = totalData.data
      
    figCount=0
    displayRange = range(0,1)
    
    for k in displayRange: #whatever range of figs dictated by displayRange
        data = dataList[regionToDisplay][k,:,:]
        fig = plt.figure('%s, Frame %d'%(filePath[i],k+1))
        ax = fig.add_subplot(111)
        #image contrast adjustments
        display_min = int(np.percentile(data.flatten(),5))
        display_max = int(np.percentile(data.flatten(),95))    
        if display_min < 1:
            display_min = 1
            
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
                aspect = 0.05
                ax.imshow(data,vmin=display_min,vmax=display_max,cmap='gray',extent=[wavelengths[0],wavelengths[-1],np.size(data,0),0],aspect=aspect)
                ax.set(xlabel='Wavelength (nm)')
            else:
                ax.imshow(data,origin='upper',vmin=display_min,vmax=display_max,cmap='gray')
                ax.set(xlabel='Column')
            ax.set(ylabel='Row')
            if k+1 >= np.size(dataList[regionToDisplay],0):
                break
