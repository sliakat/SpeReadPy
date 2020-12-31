# Import the .NET class library
import clr

# Import python sys module
import sys

# Import modules
import os, glob, string

from ctypes import *

# Import System.IO for saving and opening files
from System.IO import *

from System.Threading import AutoResetEvent

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
from PrincetonInstruments.LightField.AddIns import ExperimentSettings
from PrincetonInstruments.LightField.AddIns import DeviceType


def open_saved_image(directory):
    # Access previously saved image
    if( os.path.exists(directory)):        
        print("\nOpening .spe file...")        

        # Returns all .spe files
        files = glob.glob(directory +'/*.spe')

        # Returns recently acquired .spe file
        last_image_acquired = max(files, key=os.path.getctime)

        try:
            # Open file
            file_name = file_manager.OpenFile(
                last_image_acquired, FileAccess.Read)

            # Access image
            get_image_data(file_name)

            #Dispose of image
            file_name.Dispose()

        except IOError:
            print ("Error: can not find file or read data")
        
    else:
        print(".spe file not found...")
    
def get_image_data(file):        
    # Get the first frame
    imageData = file.GetFrame(0, 0);
    
    # Print Height and Width of first frame                
    print(String.Format(
        '\t{0} {1}X{2}',
        "Image Width and Height:",
        imageData.Width,imageData.Height))

    # Get image data
    buffer = imageData.GetData()

    # Print first 10 pixel intensities
    for pixel in range(0,10):
        print(String.Format('\t{0} {1}', 'Pixel Intensity:',
                            str(buffer[pixel])))  

def experiment_completed(sender, event_args):    
    print("Experiment Completed")    
    # Sets the state of the event to signaled,
    # allowing one or more waiting threads to proceed.
    acquireCompleted.Set()

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

# Get LightField Application object
application = auto.LightFieldApplication

# Get experiment object
experiment = application.Experiment

# Get file manager object
file_manager = application.FileManager

# Notifies a waiting thread that an event has occurred
acquireCompleted = AutoResetEvent(False)

# Check for device and inform user if one is needed
if (device_found()==True): 
    # Hook the experiment completed handler
    experiment.ExperimentCompleted += experiment_completed        

    try:
        # Acquire image in LightField
        experiment.Acquire()

        # Wait for acquisition to complete
        acquireCompleted.WaitOne()
        
    finally:
        # Cleanup handler
        experiment.ExperimentCompleted -= experiment_completed            

    # Get image directory
    _directory = experiment.GetValue(
        ExperimentSettings.FileNameGenerationDirectory)

    # Open previously saved image or inform the user
    # the file cannot be found
    open_saved_image(_directory)  



# Result: will acquire an image, open the spe file and
#         read back image width and height
#         also prints intensity of first 10 pixels
'''
Opening .spe file...
	Image Width and Height: 1024X1024
	Pixel Intensity: 682
	Pixel Intensity: 721
	Pixel Intensity: 642
	Pixel Intensity: 723
	Pixel Intensity: 704
	Pixel Intensity: 656
	Pixel Intensity: 686
	Pixel Intensity: 697
	Pixel Intensity: 712
	Pixel Intensity: 885
'''






