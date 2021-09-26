# -*- coding: utf-8 -*-
"""
Created on Sat Dec  5 23:46:02 2020

@author: sabbi
"""

#input file name to the function, data will be output into dataContainer object,
#which will have xml fopoter and wavelength calibration if applicable
#dataContainer.data will be a list of numpy arrays per ROI

import numpy as np
import xml.etree.ElementTree as ET

class ROI:
    def __init__(self,width,height,stride):
        self.width=width
        self.height=height
        self.stride=stride
        
class dataContainer:
    def __init__(self,data,**kwargs):
        self.data=data
        self.__dict__.update(kwargs)



def readSpe(filePath):
    dataTypes = {'MonochromeUnsigned16':np.uint16, 'MonochromeUnsigned32':np.uint32, 'MonochromeFloating32':np.float32}
    
    with open(filePath) as f:
        f.seek(678)
        xmlLoc = np.fromfile(f,dtype=np.uint64,count=1)[0]
        f.seek(1992)
        speVer = np.fromfile(f,dtype=np.float32,count=1)[0]
    
    if speVer==3:
        with open(filePath, encoding="utf8") as f:
            f.seek(xmlLoc)
            xmlFooter = f.read()
            xmlRoot = ET.fromstring(xmlFooter)            
            #print(xmlRoot[0][0].attrib)
            readoutStride=np.int((xmlRoot[0][0].attrib)['stride'])
            numFrames=np.int((xmlRoot[0][0].attrib)['count'])
            pixFormat=(xmlRoot[0][0].attrib)['pixelFormat']
            #find number of regions
            #regions = list(xmlRoot[0][0])
            regionList=list()
            for child in xmlRoot[0][0]:
                regStride=np.int((child.attrib)['stride'])
                regWidth=np.int((child.attrib)['width'])
                regHeight=np.int((child.attrib)['height'])
                regionList.append(ROI(regWidth,regHeight,regStride))
            dataList=list()
            regionOffset=0
            
            #read entire datablock
            f.seek(0)
            bpp = np.dtype(dataTypes[pixFormat]).itemsize
            numPixels = np.int((xmlLoc-4100)/bpp)  
            totalBlock = np.fromfile(f,dtype=dataTypes[pixFormat],count=numPixels,offset=4100)
            for i in range(0,len(regionList)):
                offLen=list()                
                if i>0:
                    regionOffset += (regionList[i-1].stride)/bpp                    
                for j in range(0,numFrames):
                    offLen.append((np.int(regionOffset+(j*readoutStride/bpp)),regionList[i].width*regionList[i].height))     
                regionData = np.concatenate([totalBlock[offset:offset+length] for offset,length in offLen])
                dataList.append(np.reshape(regionData,(numFrames,regionList[i].height,regionList[i].width),order='C'))

            calFlag=False                
            for child in xmlRoot[1]:
                if 'Wavelength' in child.tag:
                    wavelengths=np.fromstring(child[0].text,sep=',')
                    calFlag=True
                    totalData=dataContainer(dataList,xmlFooter=xmlFooter,wavelengths=wavelengths)
            if calFlag==False:
                totalData=dataContainer(dataList,xmlFooter=xmlFooter)
            return totalData

        
    elif speVer<3:
        dataTypes2 = {0:np.float32, 1:np.int32, 2:np.int16, 3:np.uint16, 5:np.float64, 6:np.uint8, 8:np.uint32}
        with open(filePath, encoding="utf8") as f:
            f.seek(108)
            datatype=np.fromfile(f,dtype=np.int16,count=1)[0]
            f.seek(42)
            frameWidth=np.int(np.fromfile(f,dtype=np.uint16,count=1)[0])
            f.seek(656)
            frameHeight=np.int(np.fromfile(f,dtype=np.uint16,count=1)[0])
            f.seek(1446)
            numFrames=np.fromfile(f,dtype=np.int32,count=1)[0]
            numPixels = frameWidth*frameHeight*numFrames
            bpp = np.dtype(dataTypes2[datatype]).itemsize
            dataList=list()            
            f.seek(0)
            totalBlock = np.fromfile(f,dtype=dataTypes2[datatype],count=numPixels,offset=4100)
            offLen=list()
            for j in range(0,numFrames):
                offLen.append((np.int((j*frameWidth*frameHeight)),frameWidth*frameHeight))
            regionData = np.concatenate([totalBlock[offset:offset+length] for offset,length in offLen])
            dataList.append(np.reshape(regionData,(numFrames,frameHeight,frameWidth),order='C'))
            totalData=dataContainer(dataList)
            return totalData
            
