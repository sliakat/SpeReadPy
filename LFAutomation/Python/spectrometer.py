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
from PrincetonInstruments.LightField.AddIns import SpectrometerSettings
from PrincetonInstruments.LightField.AddIns import DeviceType


def set_center_wavelength(center_wave_length): 
    # Set the spectrometer center wavelength   
    experiment.SetValue(
        SpectrometerSettings.GratingCenterWavelength,
        center_wave_length)    


def get_spectrometer_info():   
    print(String.Format("{0} {1}","Center Wave Length:" ,
                  str(experiment.GetValue(
                      SpectrometerSettings.GratingCenterWavelength))))     
       
    print(String.Format("{0} {1}","Grating:" ,
                  str(experiment.GetValue(
                      SpectrometerSettings.Grating))))

        
# Create the LightField Application (true for visible)
# The 2nd parameter forces LF to load with no experiment 
auto = Automation(True, List[String]())

# Get experiment object
experiment = auto.LightFieldApplication.Experiment

# Find connected device
for device in experiment.ExperimentDevices:

    if (device.IsConnected==True):
    
        if (experiment.Exists(SpectrometerSettings.GratingCenterWavelength)):
            
            # Set the spectrometer center wavelength
            set_center_wavelength(5)

            # Get spectrometer settings information
            get_spectrometer_info()
        else:
            # Inform the user, spectrometer is needed
            print("Spectrometer not found. Please add a spectrometer and try again.")
                




    

