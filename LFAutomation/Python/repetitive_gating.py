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
from PrincetonInstruments.LightField.AddIns import GatingMode
from PrincetonInstruments.LightField.AddIns import Pulse 
from PrincetonInstruments.LightField.AddIns import DeviceType   



def set_repetitive_gate(width, delay):
    # Check Gating Mode existence
    if (experiment.Exists(CameraSettings.GatingMode)):

        # Set repetitive gating mode
        experiment.SetValue(CameraSettings.GatingMode, GatingMode.Repetitive)  
        
        pulses = []

        # Add PI Pulse type with parameters to pulser list
        pulses.append(Pulse(width,delay))

        # Set repetitive gate
        experiment.SetValue(
            CameraSettings.GatingRepetitiveGate,
            pulses[0])
    else:
        print("System not capable of Gating Mode")
        

def set_on_chip_accumulations(accumulations):
    # Set On-chip accumulations
    experiment.SetValue(
    CameraSettings.ReadoutControlAccumulations, accumulations)
    

def get_on_chip_accumulations():
    print(String.Format("{0} {1}", "Current On-Chip Accumulations:",
                        experiment.GetValue(
                            CameraSettings.ReadoutControlAccumulations)))
    
def device_found():
    # Find connected device
    for device in experiment.ExperimentDevices:
        if (device.Type == DeviceType.Camera and
            "PI-MAX" in device.Model):
            return True
     
    # If connected device is not a camera inform the user
    print("Camera not found. Please add PI-MAX type camera to LightField.")
    return False  


        
# Create the LightField Application (true for visible)
# The 2nd parameter forces LF to load with no experiment 
auto = Automation(True, List[String]())

# Get experiment object
experiment = auto.LightFieldApplication.Experiment

# If PI-MAX3 or 4 found continue
if (device_found()==True):
    # Set on-chip accumulations
    set_on_chip_accumulations(3)

    # Print on-chip accumulations
    get_on_chip_accumulations()

    # Set repetitive gate width and delay
    set_repetitive_gate(50, 100)

    # Acquire image
    experiment.Acquire()


#Result: This sample will set/get a value for on chip accumulations.
#        Set repetitive gate pulse width and delay.
#        Acquire an image.


    
