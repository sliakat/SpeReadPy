# -*- coding: utf-8 -*-
"""
Created on Wed Jan 27 13:23:30 2021

@author: sliakat
"""

#How to use, and notes:
#FIRST: CHANGE THE NAME FOR 'expToLoad' (line 106) TO A VALID EXPERIMENT FILE ON YOUR PC
#**If you don't change the name and use an experiment name that is not on your PC, it will crash**
#
#When you've changed the experiment accordingly, run script with all 3 functions in main commendted (so only the 'pass' line is active)
#This will open up an automation bridge to LightField that will be controllable via the Pyhton
#thread until the instance is disposed.
#
#Next, run ONLY the line in main calling 'Background'. This will create a BG file and save in
#the default save directory as 'Background.spe'.
#
#Next, run ONLY the line in main calling 'Reference'. This will create the reference file using LF
#BG subtraction w/ the file created by 'Background'.
#
#Finally, run ONLY the 'Transmitted' line to arm LightField with the desired formula. After this line is run, you can hit
#'Run' or 'Acquire in LF with all parameters armed.
#
#This script is meant to be an example of what is possible with the automation interface for this absorbance application.
#You can turn into a GUI by making buttons that call the 'Background', 'Reference', and 'Tramsitted' options.


import clr

# Import python sys module
import sys

# Import modules
import os

from System.Threading import AutoResetEvent

# Import c compatible types
from System import String, Int32, Int64, Double
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
from PrincetonInstruments.LightField import AddIns

def acquisitionFinished(sender, event_args):
    signal.Set()
    exp.ExperimentCompleted -= acquisitionFinished
    
def Acquire():
    exp.ExperimentCompleted += acquisitionFinished
    exp.Acquire()
    signal.WaitOne()

def SetFilenames(name):
    exp.SetValue(ExperimentSettings.FileNameGenerationBaseFileName, name)
    exp.SetValue(ExperimentSettings.FileNameGenerationAttachDate, False)
    exp.SetValue(ExperimentSettings.FileNameGenerationAttachTime, False)
    exp.SetValue(ExperimentSettings.FileNameGenerationAttachIncrement, False)
    
def SetFilenamesWithDate(name):
    exp.SetValue(ExperimentSettings.FileNameGenerationBaseFileName, name)
    exp.SetValue(ExperimentSettings.FileNameGenerationAttachDate, True)
    exp.SetValue(ExperimentSettings.FileNameGenerationAttachTime, True)
    exp.SetValue(ExperimentSettings.FileNameGenerationAttachIncrement, False)

def Background(expName):
    exp.SetValue(ExperimentSettings.OnlineCorrectionsBackgroundCorrectionEnabled,False) #unchecks BG correction box
    accums = exp.GetValue(ExperimentSettings.OnlineProcessingFrameCombinationFramesCombined)
    if accums < 5:
        exp.SetValue(ExperimentSettings.OnlineProcessingFrameCombinationFramesCombined,Int64(5))
    exp.SetValue(ExperimentSettings.OnlineProcessingFrameCombinationMethod, AddIns.FrameCombinationMethod.Average)
    exp.SetValue(ExperimentSettings.AcquisitionFramesToStore,Int64(1))                     #takes 1 frame for BG
    SetFilenames('Background')
    bgPath = exp.GetValue(ExperimentSettings.FileNameGenerationDirectory) + '\\Background.spe'
    Acquire()
    exp.Load(expName)       #reload original experiment to bring back previous settings after acquiring BG
    return bgPath
    
def Reference(expName,background,numAccums):
    exp.SetValue(ExperimentSettings.OnlineCorrectionsBackgroundCorrectionEnabled,True) #auto BG correction enabled
    exp.SetValue(ExperimentSettings.OnlineCorrectionsBackgroundCorrectionReferenceFile,background)
    exp.SetValue(ExperimentSettings.OnlineProcessingFrameCombinationFramesCombined,Int64(numAccums))
    exp.SetValue(ExperimentSettings.OnlineProcessingFrameCombinationMethod, AddIns.FrameCombinationMethod.Average)
    exp.SetValue(ExperimentSettings.AcquisitionFramesToStore,Int64(1))
    SetFilenames('Reference')
    refPath = exp.GetValue(ExperimentSettings.FileNameGenerationDirectory) + '\\Reference.spe'
    Acquire()
    exp.Load(expName)
    return refPath

def Transmitted(reference):
    exp.SetValue(ExperimentSettings.OnlineProcessingFormulasEnabled, True)
    formula = 'reference = \"' + reference + '\"\ntransmitted = input\n' + 'output = Log10(reference/transmitted)\n'
    exp.SetValue(ExperimentSettings.OnlineProcessingFormulasCustomFormula,formula)
    
expToLoad = 'ProDemo'

auto = Automation(True, List[String]())
exp = auto.LightFieldApplication.Experiment
exp.Load(expToLoad)
signal = AutoResetEvent(False)

if __name__ == '__main__':
    pass
    #bgPath = Background(expToLoad)
    #refPath = Reference(expToLoad,bgPath,10)                #change the 3rd parameter (integer) to input number of averaged accums
    #Transmitted(refPath)
    
    