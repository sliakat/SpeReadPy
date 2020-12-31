# Import the .NET class library
import clr

# Import python sys module
import sys

# Import os module
import os

# Import System.IO for saving and opening files
from System.IO import *

# Import C compatible List and String
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
from PrincetonInstruments.LightField.AddIns import CameraSettings
from PrincetonInstruments.LightField.AddIns import AdcQuality
from PrincetonInstruments.LightField.AddIns import DeviceType   



def set_value(setting, value):    
    # Check for existence before setting
    # gain, adc rate, or adc quality
    if experiment.Exists(setting):
        
        experiment.SetValue(setting, value)

        #return true if setting such as EM exists
        return True
    else:
        return False

def set_first_capability(setting):
    # Set the first capability at this quality and return
    for value in experiment.GetCurrentCapabilities(setting):
        set_value(setting, value)
        return

def device_found():
    # Find connected device
    for device in experiment.ExperimentDevices:
        if (device.Type == DeviceType.Camera):
            return True
     
    # If connected device is not a camera inform the user
    print("Camera not found. Please add a camera and try again.")
    return False 
    

        
# Create the LightField Application (true for visible)
# The 2nd parameter forces LF to load with no experiment 
auto = Automation(True, List[String]())

# Get experiment object
experiment = auto.LightFieldApplication.Experiment

# Check for device and inform user if one is needed
if (device_found()==True):
    # Check for EM port capability
    if (set_value(CameraSettings.AdcQuality, AdcQuality.ElectronMultiplied)):

        # Set the first adc rate capability at this quality
        set_first_capability(CameraSettings.AdcSpeed)
        
        # Set Intensifier EM Gain
        set_value(CameraSettings.AdcEMGain, 10.0)

        # Acquire image
        experiment.Acquire()
    else:
        print("Device not supported, EMCCD mode needed")


# Result: Sets the EM Adc quality and the first adc rate available.
#         Also sets EM gain to 10 and acquires image.
