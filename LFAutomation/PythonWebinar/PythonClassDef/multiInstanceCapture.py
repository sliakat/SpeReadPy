# -*- coding: utf-8 -*-
"""
Created on Tue Jan 11 09:22:16 2022

@author: sliakat
"""

#Simple testing with LF.AutoClass for specific things I need

from LFAutomation import AutoClassNiche as ac
import LFAutomation
import threading
#import multiprocessing as mp
import time

def StreamWithEvent(autoObj):
    startTime = time.perf_counter()
    autoObj.experiment.ImageDataSetReceived += lambda sender, event_args: LFAutomation.experimentDataReady(sender, event_args, autoObj, startTime)
    autoObj.ResetCounter()
    autoObj.experiment.Preview()

class AutomationObjectManager():
    def __init__(self, instanceNames: list):
        self.objectList = []
        self.threadList = []
        self.objectRecentFrame = []
        self.Stop = False
        for name in instanceNames:
            self.objectList.append(ac())
            self.objectList[-1].NewInstance(expName=name)
    def __len__(self):
        return len(self.objectList)
    def __getitem__(self, idx):
        return self.objectList[idx]

    #capture 1 frame repeatedly, repeat until stopped or Capture returns false.
    #inefficient approch, use for debugging / performance analysis only
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

    #generate threads for all objects and go
    #can't use mp because Automation object can't be pickled
    def StreamAllWithEvent(self):
        for i in range(0, len(self)):
            self.threadList.append(threading.Thread(target=StreamWithEvent, args=(self[i],)))
        time.sleep(1)
        for item in self.threadList:
            item.start()
            #stagger object starts by a second
            time.sleep(1)
        #now the cameras will be running infinitely (until stopped by the Stop thread) and returning data on the event. 
        # you can poke at each experiment's recentData property and get the last updated frame for that experiment.

    def StopAll(self,*,eventAcq: bool=False):
        self.Stop = True
        if eventAcq:
            for item in self.objectList:
                item.experiment.Stop()
                try:
                    item.experiment.ImageDataSetReceived -= lambda sender, event_args: LFAutomation.experimentDataReady(sender, event_args, item, 0)
                except ValueError:
                    pass
        for item in self.threadList:
            item.join()
        self.Stop = False
    def DisposeAll(self,*,eventAcq: bool=False):
        self.StopAll(eventAcq=eventAcq)
        for item in self.objectList:
            item.CloseInstance()

def InputToStop(eventAcq:bool):
    input('Enter any key to stop\n')
    instances.DisposeAll(eventAcq=eventAcq)

if __name__=="__main__":
    #replace my experiment names with experiments you are trying to run
    instances = AutomationObjectManager(['PM1', 'PM2', 'PM3', 'PM4'])
    stopThread = threading.Thread(target=InputToStop, daemon=False, args=(True,))    
    stopThread.start()
    instances.StreamAllWithEvent()
    stopThread.join()
