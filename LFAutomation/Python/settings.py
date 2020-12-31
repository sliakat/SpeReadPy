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
from PrincetonInstruments.LightField.AddIns import DeviceType



def print_device_information():
    print ("Experiment Device Information:")
    # Print model and serial number of current device
    for device in experiment.ExperimentDevices:
        print(String.Format(
            '\t{0} {1}',
            device.Model,
            device.SerialNumber))

        
def print_current_capabilities(setting):
    # Get current ADC rates that correspond
    # with the current quality setting
    print (String.Format(
        "{0} {1} {2}", "Current",
        setting, "Capabilities:"))
    
    for item in experiment.GetCurrentCapabilities(setting):        
        print_speeds(item)

    
def print_maximum_capabilities(setting):    
    # Get Max Capabilities
    print(String.Format(
        "{0} {1} {2}", "Maximum",
        setting, "Capabilities:"))
    
    for item in experiment.GetMaximumCapabilities(setting):
        if (setting == CameraSettings.AdcSpeed):
            print_speeds(item)
        else:
            print(String.Format('\t{0} {1}', setting, item))


def set_value(setting, value):    
    # Check for existence before setting
    # gain, adc rate, or adc quality
    if experiment.Exists(setting):        
        print (String.Format(
            "{0}{1} to {2}", "Setting ",
            setting, value))
        
        experiment.SetValue(setting, value)
        

def print_setting(setting):
    # Check for existence before
    # getting gain, adc rate, or adc quality
    if experiment.Exists(setting):
        print(String.Format(
            '{0} {1} = {2}', "\tReading ",
            str(setting),
            experiment.GetValue(setting)))
    

def print_speeds(item):
    if item < 1:
        # Values less than 1 are kHz ADC rates
        rate = "kHz"
        item = item * 1000
    else:
        rate = "MHz"
           
    print(String.Format('\t{0}{1}', item, rate))
    

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
    # print experiment device information
    print_device_information()

    # print current ADC rate capabilities
    print_current_capabilities(CameraSettings.AdcSpeed)

    # print max capabilities for gain setting
    print_maximum_capabilities(CameraSettings.AdcAnalogGain)

    # print  max capabilities for speed setting
    print_maximum_capabilities(CameraSettings.AdcSpeed)

    # Change to Low Gain
    set_value(CameraSettings.AdcAnalogGain, 1)

    # Print setting
    print_setting(CameraSettings.AdcAnalogGain)

    # Change to High Gain
    set_value(CameraSettings.AdcAnalogGain, 3)

    # Print setting
    print_setting(CameraSettings.AdcAnalogGain)



# Result: will display various device capabilities
'''
Experiment Device Information:
	BLAZE: 400B Blaze03
Current Camera.Adc.Speed Capabilities:
	5MHz
	1MHz
	100kHz
Maximum Camera.Adc.AnalogGain Capabilities:
	Camera.Adc.AnalogGain 1
	Camera.Adc.AnalogGain 2
	Camera.Adc.AnalogGain 3
Maximum Camera.Adc.Speed Capabilities:
	16MHz
	10MHz
	6.25MHz
	5MHz
	1MHz
	100kHz
Setting Camera.Adc.AnalogGain to 1
	Reading  Camera.Adc.AnalogGain = 1
Setting Camera.Adc.AnalogGain to 3
'''

