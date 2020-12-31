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
from PrincetonInstruments.LightField.AddIns import RegionOfInterest
from PrincetonInstruments.LightField.AddIns import DeviceType

    
def set_custom_ROI():
    # Get device full dimensions
    dimensions = get_device_dimensions()
        
    regions = []
    
    # Add two ROI to regions
    regions.append(
        RegionOfInterest
        (dimensions.X, dimensions.Y,
         dimensions.Width, dimensions.Height/4,
         dimensions.XBinning, dimensions.YBinning))
    
    regions.append(
        RegionOfInterest
        (dimensions.X, dimensions.Height/2,
         dimensions.Width, dimensions.Height/4,
         dimensions.XBinning, dimensions.YBinning))

    # Set both ROI
    experiment.SetCustomRegions(regions)

    # Display the dimensions for each ROI
    for roi in regions:
        print_region(roi)    

def get_device_dimensions():
    return experiment.FullSensorRegion

def print_region(region):
    print("Custom Region Setting:")
    print(String.Format("{0} {1}", "\tX:", region.X))
    print(String.Format("{0} {1}", "\tY:", region.Y))
    print(String.Format("{0} {1}", "\tWidth:", region.Width))
    print(String.Format("{0} {1}", "\tHeight:", region.Height))
    print(String.Format("{0} {1}", "\tXBinning:", region.XBinning))
    print(String.Format("{0} {1}", "\tYBinning:", region.YBinning))

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
    # Set a custom region of interest
    set_custom_ROI()

    # Acquire image
    experiment.Acquire()



# Result: Two regions of interest are set in LightField.
#         They will be used to acquire an image.
#         ROI dimensions printed.
'''
Custom Region Setting:
	X: 0
	Y: 0
	Width: 1024
	Height: 64
	XBinning: 1
	YBinning: 1
Custom Region Setting:
	X: 0
	Y: 128
	Width: 1024
	Height: 64
	XBinning: 1
	YBinning: 1
'''


