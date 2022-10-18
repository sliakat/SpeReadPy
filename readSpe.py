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
        
class MetaContainer:
    def __init__(self,metaType,stride,*,metaEvent:str='',metaResolution:np.int64=0):
        self.metaType=metaType
        self.stride=stride
        self.metaEvent=metaEvent
        self.metaResolution=metaResolution
        
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
            regionList=list()
            metaList = list()
            dataList=list()            
            #print(xmlRoot[0][0].attrib)
            calFlag=False
            for child in xmlRoot:
                if 'DataFormat'.casefold() in child.tag.casefold():
                    for child1 in child:                    
                        if 'DataBlock'.casefold() in child1.tag.casefold():
                            readoutStride=np.int64(child1.get('stride'))
                            numFrames=np.int64(child1.get('count'))
                            pixFormat=child1.get('pixelFormat')
                            for child2 in child1:
                                if 'DataBlock'.casefold() in child1.tag.casefold():
                                    regStride=np.int64(child2.get('stride'))
                                    regWidth=np.int64(child2.get('width'))
                                    regHeight=np.int64(child2.get('height'))
                                    regionList.append(ROI(regWidth,regHeight,regStride))
                if 'MetaFormat'.casefold() in child.tag.casefold():
                    for child1 in child:                    
                        if 'MetaBlock'.casefold() in child1.tag.casefold():
                            for child2 in child1:
                                metaType = child2.tag.rsplit('}',maxsplit=1)[1]
                                metaEvent = child2.get('event')
                                metaStride = np.int64(np.int64(child2.get('bitDepth'))/8)
                                metaResolution = child2.get('resolution')
                                if metaEvent != None and metaResolution !=None:
                                    metaList.append(MetaContainer(metaType,metaStride,metaEvent=metaEvent,metaResolution=np.int64(metaResolution)))
                                else:
                                    metaList.append(MetaContainer(metaType,metaStride))                                
                if 'Calibrations'.casefold() in child.tag.casefold():
                    for child1 in child:
                        if 'WavelengthMapping'.casefold() in child1.tag.casefold():
                            for child2 in child1:
                                if 'WavelengthError'.casefold() in child2.tag.casefold():
                                    wavelengths = np.array([])
                                    wlText = child2.text.rsplit()
                                    for elem in wlText:
                                        wavelengths = np.append(wavelengths,np.fromstring(elem,sep=',')[0])
                                else:
                                    wavelengths=np.fromstring(child2.text,sep=',')
                            calFlag=True                    
                    
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
                
            if calFlag==False:
                totalData=dataContainer(dataList,xmlFooter=xmlFooter)
            else:
                totalData=dataContainer(dataList,xmlFooter=xmlFooter,wavelengths=wavelengths)
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

class SpeReference():
    dataTypes = {'MonochromeUnsigned16':np.uint16, 'MonochromeUnsigned32':np.uint32, 'MonochromeFloating32':np.float32}
    def __init__(self, filePath: str):
        self.filePath = filePath
        self.speVersion = 0
        self.totalROIs = 0
        self.roiShapes = []
        self.wavelength = None

    def InitializeSpe(self, encoding="utf8"):
        with open(self.filePath) as f:
            f.seek(678)
            self.xmlLoc = np.fromfile(f,dtype=np.uint64,count=1)[0]
            f.seek(1992)
            self.speVersion = np.fromfile(f,dtype=np.float32,count=1)[0]

            #get ROIs and shapes
            if self.speVersion==3:
                f.seek(self.xmlLoc)
                xmlFooter = f.read()
                xmlRoot = ET.fromstring(xmlFooter)
                regionList=list()
                metaList = list()
                dataList=list()            
                calFlag=False
                for child in xmlRoot:
                    if 'DataFormat'.casefold() in child.tag.casefold():
                        for child1 in child:                    
                            if 'DataBlock'.casefold() in child1.tag.casefold():
                                readoutStride=np.int64(child1.get('stride'))
                                numFrames=np.int64(child1.get('count'))
                                pixFormat=child1.get('pixelFormat')
                                for child2 in child1:
                                    if 'DataBlock'.casefold() in child1.tag.casefold():
                                        regStride=np.int64(child2.get('stride'))
                                        regWidth=np.int64(child2.get('width'))
                                        regHeight=np.int64(child2.get('height'))
                                        regionList.append(ROI(regWidth,regHeight,regStride))
                    if 'MetaFormat'.casefold() in child.tag.casefold():
                        for child1 in child:                    
                            if 'MetaBlock'.casefold() in child1.tag.casefold():
                                for child2 in child1:
                                    metaType = child2.tag.rsplit('}',maxsplit=1)[1]
                                    metaEvent = child2.get('event')
                                    metaStride = np.int64(np.int64(child2.get('bitDepth'))/8)
                                    metaResolution = child2.get('resolution')
                                    if metaEvent != None and metaResolution !=None:
                                        metaList.append(MetaContainer(metaType,metaStride,metaEvent=metaEvent,metaResolution=np.int64(metaResolution)))
                                    else:
                                        metaList.append(MetaContainer(metaType,metaStride))                                
                    if 'Calibrations'.casefold() in child.tag.casefold():
                        for child1 in child:
                            if 'WavelengthMapping'.casefold() in child1.tag.casefold():
                                for child2 in child1:
                                    if 'WavelengthError'.casefold() in child2.tag.casefold():
                                        wavelengths = np.array([])
                                        wlText = child2.text.rsplit()
                                        for elem in wlText:
                                            wavelengths = np.append(wavelengths,np.fromstring(elem,sep=',')[0])
                                    else:
                                        wavelengths=np.fromstring(child2.text,sep=',')
                                calFlag=True                    
        
        