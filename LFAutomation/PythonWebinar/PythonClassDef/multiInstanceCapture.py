# -*- coding: utf-8 -*-
"""
Created on Tue Jan 11 09:22:16 2022

@author: sliakat
"""

#Simple testing with LF.AutoClass for specific things I need

from LFAutomation import AutoClassNiche as ac
import threading
import time

class AutomationObjectManager():
    def __init__(self, instanceNames: list):
        self.objectList = []
        self.threadList = []
        self.Stop = False
        for name in instanceNames:
            self.objectList.append(ac())
            self.objectList[-1].NewInstance(expName=name)
    def __len__(self):
        return len(self.objectList)
    def __getitem__(self, idx):
        return self.objectList[idx]

    #capture 1 frame repeatedly, repeat until stopped or Capture returns false.
    def ImageLoop(self, idx):
        startTime = time.perf_counter()
        #do-while loop
        dataList = self.objectList[idx].Capture(numFrames=1, startTime=startTime)
        while len(dataList) > 0:
            if self.Stop == True:
                break
            dataList = self.objectList[idx].Capture(numFrames=1, startTime=startTime)
    #create separate threads for all the acquiring instances
    def ImageLoopAll(self):
        for i in range(0, len(self)):
            self.threadList.append(threading.Thread(target=self.ImageLoop, args=(i,)))
        for item in self.threadList:
            item.start()
    def StopAll(self):
        self.Stop = True
        for item in self.threadList:
            item.join()
        self.Stop = False
    def DisposeAll(self):
        self.StopAll()
        for item in self.objectList:
            item.CloseInstance()

def InputToStop():
    input('Enter any key to stop\n')
    instances.DisposeAll()

if __name__=="__main__":
    instances = AutomationObjectManager(['PM1', 'PM2', 'PM3', 'PM4'])
    instances.ImageLoopAll()
    stopThread = threading.Thread(target=InputToStop, daemon=False)    
    stopThread.start()
    stopThread.join()