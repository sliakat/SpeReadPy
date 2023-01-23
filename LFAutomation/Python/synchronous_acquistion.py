# Import the .NET class library
import clr, ctypes

# Import python sys module
import sys, os

# numpy import
import numpy as np

# Import c compatible List and String
from System import *
from System.Collections.Generic import List
from System.Runtime.InteropServices import Marshal
from System.Runtime.InteropServices import GCHandle, GCHandleType


# Add needed dll references
sys.path.append(os.environ['LIGHTFIELD_ROOT'])
sys.path.append(os.environ['LIGHTFIELD_ROOT']+"\\AddInViews")
clr.AddReference('PrincetonInstruments.LightFieldViewV5')
clr.AddReference('PrincetonInstruments.LightField.AutomationV5')
clr.AddReference('PrincetonInstruments.LightFieldAddInSupportServices')

# PI imports
from PrincetonInstruments.LightField.Automation import *
from PrincetonInstruments.LightField.AddIns import *


# Create the LightField Application (true for visible)
# The 2nd parameter forces LF to load with no experiment 
_auto = Automation(True, List[String]())

# Get LightField Application object
_application = _auto.LightFieldApplication

# Get experiment object
_experiment = _application.Experiment



def validate_camera():
    camera = None
    
    # Find connected device

    for device in _experiment.ExperimentDevices:
        if (device.Type == DeviceType.Camera and _experiment.IsReadyToRun):
            camera = device

    if (camera == None):
        print("This sample requires a camera.")
        return False

    if (not _experiment.IsReadyToRun):
        print("The system is not ready for acquisition, is there an error?")
    
    return True


# Creates a numpy array from our acquired buffer 
def convert_buffer(net_array, image_format):
    src_hndl = GCHandle.Alloc(net_array, GCHandleType.Pinned)
    try:
        src_ptr = src_hndl.AddrOfPinnedObject().ToInt64()

        # Possible data types returned from acquisition
        if (image_format==ImageDataFormat.MonochromeUnsigned16):
            buf_type = ctypes.c_ushort*len(net_array)
        elif (image_format==ImageDataFormat.MonochromeUnsigned32):
            buf_type = ctypes.c_uint*len(net_array)
        elif (image_format==ImageDataFormat.MonochromeFloating32):
            buf_type = ctypes.c_float*len(net_array)
                    
        cbuf = buf_type.from_address(src_ptr)
        resultArray = np.frombuffer(cbuf, dtype=cbuf._type_)

    # Free the handle 
    finally:        
        if src_hndl.IsAllocated: src_hndl.Free()
        
    # Make a copy of the buffer
    return np.copy(resultArray)


# Print Pixel Data from Acquired Image    
def print_data(image_data, image_frame, iteration, acquisitions):
    
    # Calculate center
    center_pixel = int(((image_frame.Height / 2 - 1) * image_frame.Width) + image_frame.Width / 2)

    # Last Pixel
    last_pixel = int((image_frame.Width * image_frame.Height) - 1)

    print("\n- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - ")

    # First Pixel
    pixel1 = "\nFirst Pixel Intensity: %s" % str(image_data.GetValue(0))

    # Center Pixel, zero based
    pixel2 = "\nCenter Pixel Intensity: %s" % str(image_data.GetValue(center_pixel))

    # Last Pixel
    pixel3 = "\nLast Pixel Intensity: %s" % str(image_data.GetValue(last_pixel))

    # Create formatted message
    formattedString = "\nAcquisition {0} of {1} \n{2} \n{3} \n{4}".format(iteration,
                                                                          acquisitions,
                                                                          pixel1,
                                                                          pixel2,
                                                                          pixel3)
    # Print message
    print(formattedString)

    
# Print Statistics from Numpy
def numpy_statistics(image_data, image_frame):

    # Create a numpy compatible list out of image_data
    array = convert_buffer(image_data, image_frame.Format)

    # Calculated mean
    print("\nMean: %s" % str(round(np.mean(array)))) 
    
    # Calculated median
    print("\nMedian: %s" % str(round(np.median(array)))) 
        
    # Calculated max
    print("\nMax Value: %s" % str(round(np.max(array))))  
        
    # Calculated min
    print("\nMin Value: %s" % str(np.min(array)))
    

_experiment.Load('PM1')

# Validate camera state
if (validate_camera()):
            
    # Full Frame
    _experiment.SetFullSensorRegion()

    images = 3
    frames = 1

    # Set number of frames
    _experiment.SetValue(ExperimentSettings.AcquisitionFramesToStore, Int32(frames))
    
    for i in range(images):
        # Capture 1 Frame
        dataset = _experiment.Capture(Int32(frames))

        # Stop processing if we do not have all frames
        if (dataset.Frames != frames):
            print(dataset.Frames, frames, type(dataset.Frames))
            # Clean up the image data set                    
            dataset.Dispose()

            raise Exception("Frames are not equal.")

        # Get the data from the current frame
        image_data = dataset.GetFrame(0, frames - 1).GetData()

        # Cache the frame
        image_frame = dataset.GetFrame(0, frames - 1)

        print_data(image_data, image_frame, str(i+1), str(images))
        
        numpy_statistics(image_data, image_frame)


''' example result below

- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - 

Acquisition 1 of 3 

First Pixel Intensity: 4918 

Center Pixel Intensity: 4994 

Last Pixel Intensity: 4605

Mean: 4820.0

Median: 4819.0

Max Value: 5455

Min Value: 2625

- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - 

Acquisition 2 of 3 

First Pixel Intensity: 4981 

Center Pixel Intensity: 4932 

Last Pixel Intensity: 4695

Mean: 4819.0

Median: 4818.0

Max Value: 5416

Min Value: 2614

- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - 

Acquisition 3 of 3 

First Pixel Intensity: 4880 

Center Pixel Intensity: 4930 

Last Pixel Intensity: 4675

Mean: 4819.0

Median: 4818.0

Max Value: 5433

Min Value: 2639

'''                   
