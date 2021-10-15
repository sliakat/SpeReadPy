# -*- coding: utf-8 -*-
"""
Created on Fri Oct 15 09:57:11 2021

@author: sliakat
"""

#kwargs: region (which region to display), frames (#frames),
#
#Return tuple will be in the form: (data, xml, fig, waveCal)
#   if waveCal doesn't exist, will return 0

from readSpe import readSpe
from matplotlib import pyplot as plt
import numpy as np

def showSpe(filename,*,region: int=0,frames: int=1):
    #mainly cpp from visualizeSpe test script
    totalData = readSpe(filename)
    waveCal=False
    try:
        xmlFooter = totalData.xmlFooter
        wavelengths = totalData.wavelengths
        waveCal=True
    except:
        print('No wavelength calibration in spe.')
    
    dataList = totalData.data
        
    displayRange = range(0,frames)   #frames
    
    for k in displayRange:
        data = dataList[region][k,:,:]
        fig = plt.figure(filename + ' : Frame %d'%(k+1))
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
                aspect = 0.25
                ax.imshow(data,vmin=display_min,vmax=display_max,cmap='gray',extent=[wavelengths[0],wavelengths[-1],np.size(data,0),0],aspect=aspect)
                
            else:
                ax.imshow(data,origin='upper',vmin=display_min,vmax=display_max,cmap='gray')
                ax.set(xlabel='Column')
            ax.set(ylabel='Row')
            if k+1 >= np.size(dataList[region],0):
                break
            
    #returns
    if waveCal:
        return (dataList[region], xmlFooter, fig, wavelengths)
    else:
        return (dataList[region], xmlFooter, fig, [0])
