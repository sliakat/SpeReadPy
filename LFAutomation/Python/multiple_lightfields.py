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
from PrincetonInstruments.LightField.AddIns import IDevice, DeviceType
from PrincetonInstruments.LightField.AddIns import ExperimentSettings

increment = 0

class LightFieldAutomation:
    
    def __init__(self):        
        # Create the LightField Application (true for visible)
        # The 2nd parameter forces LF to load with no experiment 
        auto = Automation(True, List[String]())
        
        # Get experiment object
        self.experiment = auto.LightFieldApplication.Experiment

    def get_experiment(self):
        return self.experiment


def open_single_instance():    
    print("\nOpening new instance of LightField...")
    
    # Open new instance of LightField
    experiment = LightFieldAutomation().get_experiment()
    
    # Add any available devices
    experiment = add_first_available_camera(experiment)
    
    # Set file name options to true to save unique files
    save_file_options(experiment)

    return experiment


def add_first_available_camera(experiment):
    # Add first available device when there
    # are none connected and return
    for device in experiment.ExperimentDevices:
        if (experiment.ExperimentDevices.Count == 1 and
            device.Type == DeviceType.Camera):
            return experiment

    for device in experiment.AvailableDevices:
        if (experiment.AvailableDevices.Count > 0 and
            device.Type == DeviceType.Camera):

            # Print information on device being added
            print("Found ", device.Model, "\n\tAdding Camera...")

            # Add device
            experiment.Add(device)
            
            return experiment
     
    # If connected device is not a camera inform the user
    print("Camera not found. Please add a camera and try again.")

    #Exit Python
    sys.exit()
    

def save_file_options(experiment):    

    global increment
    increment += 1
    
    # Option to Increment, set to false will not increment
    experiment.SetValue(
        ExperimentSettings.FileNameGenerationAttachIncrement,
        True)
    
    experiment.SetValue(
        ExperimentSettings.FileNameGenerationIncrementNumber,
        increment)
        
    # Option to add date
    experiment.SetValue(
        ExperimentSettings.FileNameGenerationAttachDate,
        True)

    # Option to add time
    experiment.SetValue(
        ExperimentSettings.FileNameGenerationAttachTime,
        True)
   


# Open single instance and add device
first_experiment = open_single_instance()

# Number of available devices
count = first_experiment.AvailableDevices.Count

# Acquire image in the new instance of LightField if ready
if (first_experiment.IsReadyToRun):
    print("Acquiring image from first LightField instance...")
    first_experiment.Acquire()

# Open second instance and add device if available
if (count > 0):
    second_experiment = open_single_instance()
else:
    print("\nSecond device required for this sample. ",
          "Add device and try again.")

if (count > 0 and second_experiment.IsReadyToRun):
    # Acquire image in the second instance of LightField
    # if ready and available
    print("Acquiring image from second LightField instance...") 
    second_experiment.Acquire()                                                           



# Result: capable of acquiring images from two instances of LightField
'''Opening new instance of LightField...
Found  PI-MAX3: 1024i 
	Adding Camera...

Opening new instance of LightField...
Found  BLAZE: 400B 
	Adding Camera...
	
Acquiring image from first LightField instance...
Acquiring image from second LightField instance...
'''
