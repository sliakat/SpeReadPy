# -*- coding: utf-8 -*-
"""
Created on Tue Mar 23 13:06:53 2021

@author: sliakat
"""

#demonstration to stop an experiment if it has hung during acquisiton
#experiment has Pixis camera firing off 10Hz external trigger for 100 frames
#total experiment time should be 10secs if successful
#wait timeout set to 12s
#while the experiment is running, shut off the trigger, acquisiton should hang
#waiting for the next trigger.
#The timeout in the AutoResetEvent should trigger the stop command after 12s elapse

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
    print('...Acquisition Complete!')        
    acquireCompleted.Set()

auto = Automation(True, List[String]())
experiment = auto.LightFieldApplication.Experiment
acquireCompleted = AutoResetEvent(False)

experiment.Load('PixTrig')
experiment.ExperimentCompleted += experiment_completed
experiment.Acquire()
flag = acquireCompleted.WaitOne(12000)
if flag==False:
    experiment.Stop()
    print('Experiment stopped.')
    
#auto.Dispose()