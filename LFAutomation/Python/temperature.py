# Import the .NET class library
import clr

# Import python sys module
import sys

# Import os module
import os

# Import System.IO for saving and opening files
from System.IO import *

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
from PrincetonInstruments.LightField.AddIns import CameraSettings
from PrincetonInstruments.LightField.AddIns import SensorTemperatureStatus
from PrincetonInstruments.LightField.AddIns import DeviceType


def set_temperature(temperature):
    # Set temperature when LightField is ready to run and
    # when not acquiring data.     
    if (experiment.IsReadyToRun & experiment.IsRunning==False):
        experiment.SetValue(
            CameraSettings.SensorTemperatureSetPoint,
            temperature)        

def get_current_temperature():
    print(String.Format(
        "{0} {1}", "Current Temperature:",
        experiment.GetValue(CameraSettings.SensorTemperatureReading)))

def get_current_setpoint():
    print(String.Format(
        "{0} {1}", "Current Temperature Set Point:",
        experiment.GetValue(CameraSettings.SensorTemperatureSetPoint)))        

def get_status():    
    current = experiment.GetValue(CameraSettings.SensorTemperatureStatus)
    
    print(String.Format(
        "{0} {1}", "Current Status:",
        "UnLocked" if current == SensorTemperatureStatus.Unlocked 
        else "Locked"))
    
    return current

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

if (device_found()==True): 
    # Set temperature to -10 degrees C
    set_temperature(-10)

    # Report back the current set point
    get_current_setpoint()

    # Display current temperature
    get_current_temperature()

    # Get locked or unlocked status
    get_status()


# Result: Changes temperature set point to -10, 
#         reports current temperature and status
    

