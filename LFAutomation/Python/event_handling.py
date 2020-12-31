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
from PrincetonInstruments.LightField.AddIns import DeviceType



def experiment_isReadyToRunChanged(sender, event_args):
    if (experiment.IsReadyToRun):
        # No Errors in LightField
        print('\n\tLightField is Ready to Run\n')
    else:
        # For testing purposes set the exposure time
        # to a negative value (e.g. -9)
        print('\n\tLightField is Not Ready to Run\n')

def lightField_closing(sender, event_args):
    unhook_event()        
        
def unhook_event():
    # Unhook the eventhandler for IsReadyToRunChanged
    # Will be called upon exiting
    experiment.IsReadyToRunChanged -= experiment_isReadyToRunChanged    
    auto.LightFieldClosing -= lightField_closing    
    print("handlers unhooked")

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
    # Hook the eventhandler for IsReadyToRunChanged
    experiment.IsReadyToRunChanged += experiment_isReadyToRunChanged

    # Hook the eventhandler for LightField Closing
    auto.LightFieldClosing += lightField_closing  



#Result: user informed when LightField is ready to run
'''
	LightField is Not Ready to Run


	LightField is Ready to Run


	LightField is Not Ready to Run


	LightField is Ready to Run
'''
