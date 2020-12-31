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
    

def add_available_devices():
    # Add first available device and return
    for device in experiment.AvailableDevices:
        print("\n\tAdding Device...")
        experiment.Add(device)
        return device

# create a C# compatible List of type String object
list1 = List[String]()

# add the command line option for an empty experiment
list1.Add("/empty")

# Create the LightField Application (true for visible)
auto = Automation(True, List[String](list1))

# Get experiment object
experiment = auto.LightFieldApplication.Experiment


# Check for device and inform user if one is needed
if (experiment.AvailableDevices.Count == 0):
    print("Device not found. Please add a device and try again.")
else:
    device = add_available_devices()
    
    print("\n\tRemoving Device...")
    
    # Removes the current device
    experiment.Remove(device)


# Result: LightField will add and remove a device.
'''
	Adding Device...

	Removing Device...
'''
