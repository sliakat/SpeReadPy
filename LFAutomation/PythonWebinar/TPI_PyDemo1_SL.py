# -*- coding: utf-8 -*-
"""
Created on Fri Mar 27 14:49:15 2020

@author: sliakat
"""

#declarations
import clr

# Import python sys module
import sys

# Import modules
import os, glob, string

# Import System.IO for saving and opening files
from System.IO import *

from System.Threading import AutoResetEvent

# Import c compatible List and String
from System import String
from System.Collections.Generic import List

# Add needed dll references
sys.path.append(os.environ['LIGHTFIELD_ROOT'])
sys.path.append(os.environ['LIGHTFIELD_ROOT']+"\\AddInViews")
clr.AddReference('PrincetonInstruments.LightFieldViewV5')
clr.AddReference('PrincetonInstruments.LightField.AutomationV5')
clr.AddReference('PrincetonInstruments.LightFieldAddInSupportServices')

# PI imports
from PrincetonInstruments.LightField.Automation import Automation
from PrincetonInstruments.LightField.AddIns import ExperimentSettings
from PrincetonInstruments.LightField.AddIns import SpectrometerSettings
from PrincetonInstruments.LightField.AddIns import CameraSettings
#/declarations

def experiment_completed(sender, event_args):
    print("...Acquisition Complete!")        
    acquireCompleted.Set()
    
def InitializeFilenameParams():
    experiment.SetValue(ExperimentSettings.FileNameGenerationAttachIncrement,True)
    experiment.SetValue(ExperimentSettings.FileNameGenerationIncrementNumber,1)
    experiment.SetValue(ExperimentSettings.FileNameGenerationIncrementMinimumDigits,2)
    experiment.SetValue(ExperimentSettings.FileNameGenerationAttachDate,False)
    experiment.SetValue(ExperimentSettings.FileNameGenerationAttachTime,False)
    
   
def AcquireAndLock(name):
    print("Acquiring...",end="")
    name += 'Exp{0:06.2f}ms.CWL{1:07.2f}nm'.format(\
                        experiment.GetValue(CameraSettings.ShutterTimingExposureTime)\
                        ,experiment.GetValue(SpectrometerSettings.GratingCenterWavelength))
    experiment.SetValue(ExperimentSettings.FileNameGenerationBaseFileName,name)
    experiment.Acquire()
    acquireCompleted.WaitOne()

auto = Automation(True, List[String]())
experiment = auto.LightFieldApplication.Experiment
acquireCompleted = AutoResetEvent(False)

experiment.Load("TPIPyDemo1")
experiment.ExperimentCompleted += experiment_completed
experiment.SetValue(SpectrometerSettings.GratingSelected,'[500nm,1200][1][0]')
InitializeFilenameParams()

exposures = [50,100]
specPositions = [560, 435, 546]
baseFilename = "TPI.PyDemoI."

for i in range(0,len(specPositions)):
    for j in range(0,len(exposures)):
        experiment.SetValue(SpectrometerSettings.GratingCenterWavelength, specPositions[i])
        experiment.SetValue(CameraSettings.ShutterTimingExposureTime, exposures[j])
        AcquireAndLock(baseFilename)

#auto.Dispose()
