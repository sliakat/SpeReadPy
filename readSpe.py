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
        self.X = 0
        self.Y = 0
        self.xbin = 1
        self.ybin = 1
        
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
        self.roiList = []
        self.readoutStride = 0
        self.numFrames = 0
        self.pixelFormat = None
        self.wavelength = None
        self.metaList = []
        self.InitializeSpe()

    def InitializeSpe(self):
        with open(self.filePath, encoding="utf8") as f:
            f.seek(678)
            self.xmlLoc = np.fromfile(f,dtype=np.uint64,count=1)[0]
            f.seek(1992)
            self.speVersion = np.fromfile(f,dtype=np.float32,count=1)[0]

            #get ROIs and shapes
            if self.speVersion==3:
                f.seek(self.xmlLoc)
                xmlFooter = f.read()
                xmlRoot = ET.fromstring(xmlFooter)
                for child in xmlRoot:
                    if 'DataFormat'.casefold() in child.tag.casefold():
                        for child1 in child:                    
                            if 'DataBlock'.casefold() in child1.tag.casefold():
                                self.readoutStride=np.int64(child1.get('stride'))
                                self.numFrames=np.int64(child1.get('count'))
                                self.pixelFormat=child1.get('pixelFormat')
                                for child2 in child1:
                                    if 'DataBlock'.casefold() in child1.tag.casefold():
                                        regStride=np.int64(child2.get('stride'))
                                        regWidth=np.int64(child2.get('width'))
                                        regHeight=np.int64(child2.get('height'))
                                        self.roiList.append(ROI(regWidth,regHeight,regStride))
                    if 'MetaFormat'.casefold() in child.tag.casefold():
                        for child1 in child:                    
                            if 'MetaBlock'.casefold() in child1.tag.casefold():
                                for child2 in child1:
                                    metaType = child2.tag.rsplit('}',maxsplit=1)[1]
                                    metaEvent = child2.get('event')
                                    metaStride = np.int64(np.int64(child2.get('bitDepth'))/8)
                                    metaResolution = child2.get('resolution')
                                    if metaEvent != None and metaResolution !=None:
                                        self.metaList.append(MetaContainer(metaType,metaStride,metaEvent=metaEvent,metaResolution=np.int64(metaResolution)))
                                    else:
                                        self.metaList.append(MetaContainer(metaType,metaStride))                                
                    if 'Calibrations'.casefold() in child.tag.casefold():
                        counter = 0
                        for child1 in child:
                            if 'WavelengthMapping'.casefold() in child1.tag.casefold():
                                for child2 in child1:
                                    if 'WavelengthError'.casefold() in child2.tag.casefold():
                                        wavelengths = np.array([])
                                        wlText = child2.text.rsplit()
                                        for elem in wlText:
                                            wavelengths = np.append(wavelengths,np.fromstring(elem,sep=',')[0])
                                        self.wavelength = wavelengths
                                    else:
                                        self.wavelength = np.fromstring(child2.text,sep=',')       
                            if 'SensorMapping'.casefold() in child1.tag.casefold():                                
                                if counter < len(self.roiList):
                                    self.roiList[counter].X = np.int32(child1.get('x'))
                                    self.roiList[counter].Y = np.int32(child1.get('y'))
                                    ogWidth = np.int32(child1.get('width'))
                                    ogHeight = np.int32(child1.get('height'))
                                    self.roiList[counter].xbin = np.int32(child1.get('xBinning'))
                                    self.roiList[counter].ybin = np.int32(child1.get('yBinning'))
                                    self.roiList[counter].width = np.int32(ogWidth / self.roiList[counter].xbin)
                                    self.roiList[counter].height = np.int32(ogHeight / self.roiList[counter].ybin)
                                    counter += 1
                                else:
                                    break
    
    def GetData(self,*,rois:list=[], frames:list=[]):
        #if no inputs, or empty list, set to all
        if len(rois) == 0:
            rois = np.arange(0,len(self.roiList))
        if len(frames) == 0:
            frames = np.arange(0,self.numFrames)
        #check for improper values, raise exception if necessary
        try:
            for item in rois:
                if item < 0 or item >= len(self.roiList):
                    raise ValueError('ROI value outside of allowed ranged (%d through %d)'%(0, len(self.roiList)-1))
        except TypeError:
            raise TypeError('ROI input needs to be iterable')
        try:
            for item in frames:
                if item < 0 or item >= self.numFrames:
                    raise ValueError('Frame value outside of allowed ranged (%d through %d)'%(0, self.numFrames-1))
        except TypeError:
            raise TypeError('Frame input needs to be iterable')

        #now with that out of the way... get the data
        regionOffset=0
        dataList=list()
        with open(self.filePath, encoding="utf8") as f:            
            bpp = np.dtype(self.dataTypes[self.pixelFormat]).itemsize            
            for i in range(0,len(rois)):                
                regionData = np.zeros([len(frames),self.roiList[rois[i]].height, self.roiList[rois[i]].width])
                regionOffset = 0                
                if rois[i]>0:
                    for ii in range(0,rois[i]):
                        regionOffset += np.int32(self.roiList[ii].stride/bpp)                    
                for j in range(0,len(frames)):
                    f.seek(0)                    
                    frameOffset = np.int32(frames[j]*self.readoutStride/bpp)
                    readCount =  np.int64(self.roiList[rois[i]].stride/bpp)
                    tmp = np.fromfile(f,dtype=self.dataTypes[self.pixelFormat],count=readCount,offset=np.int64(4100+(regionOffset*bpp)+(frameOffset*bpp)))
                    regionData[j,:] = np.reshape(tmp,[self.roiList[rois[i]].height,self.roiList[rois[i]].width])
                dataList.append(regionData)
        return dataList

    def GetWavelengths(self,*,rois:list=[]):
        if len(self.wavelength) == 0:
            return []
        else:
            if len(rois) == 0:
                rois = np.arange(0,len(self.roiList))
            try:
                for item in rois:
                    if item < 0 or item >= len(self.roiList):
                        raise ValueError('ROI value outside of allowed ranged (%d through %d)'%(0, len(self.roiList)-1))
            except TypeError:
                raise TypeError('ROI input needs to be iterable')

            wavelengthList = []
            for item in rois:
                if self.roiList[item].width > 0:
                    wlIndex = np.arange(self.roiList[item].X,self.roiList[item].X+self.roiList[item].width,self.roiList[item].xbin,dtype=np.int32)
                    wavelengthList.append(self.wavelength[wlIndex])
                else:
                    wavelengthList.append(self.wavelength)
            return wavelengthList
