//Basic example of asynchronous acquisiton with the first detected camera.
//Incoming data stream is displayed using OpenCV.
//
//Scope: Demonstrate a simple way to observe, copy, and display incoming
//  frame data from an aynchronous acquisiton.
//External library requirement: **MUST have OpenCV installed and properly linked.**
//  This program was tested with OpenCV 4.5.2
//Limitations: Please keep in mind the scope of the example is to demonstrate the asynchronous acquisiton. 
//  For more advanced usage, please refer to the PICam samples provided with the SDK.


//set number of frames to asynchronously acquire
#define NUM_FRAMES  100

#include <iostream>
#include <vector>
#include "picam.h"

#include <opencv2/core.hpp>
#include <opencv2/imgcodecs.hpp>
#include <opencv2/highgui.hpp>

//set camera parameters
bool ArmParameters(PicamHandle cam)
{
    piflt readRate; const PicamParameter* failed_parameter_array; piint failed_parameter_count = 0;
    const PicamCollectionConstraint* required;

    //get possible ADC speeds (for default quality, if applicable) and set to fastest
    Picam_GetParameterCollectionConstraint(cam, PicamParameter_AdcSpeed, PicamConstraintCategory_Required, &required);
    Picam_SetParameterFloatingPointValue(cam, PicamParameter_AdcSpeed, required->values_array[0]);
    //Picam_SetParameterFloatingPointValue(cam, PicamParameter_AdcSpeed, required->values_array[(required->values_count) - 1]); //this line will select the slowest
    Picam_SetParameterFloatingPointValue(cam, PicamParameter_ExposureTime, 0.02); // set to 20us exposure (if camera has exposure time parameter)
    //frame count
    Picam_SetParameterLargeIntegerValue(cam, PicamParameter_ReadoutCount, NUM_FRAMES);
    //commit and print readout rate
    Picam_CommitParameters(cam, &failed_parameter_array, &failed_parameter_count);
    Picam_DestroyCollectionConstraints(required);
    if (failed_parameter_count == 0)
    {
        Picam_GetParameterFloatingPointValue(cam, PicamParameter_ReadoutRateCalculation, &readRate);
        printf("**Camera Readout Rate: %0.2f fps.**\n", readRate);
        return true;
    }
    else
    {
        const pichar* string = "";
        printf("!!*Problem committing parameters. Cannot Acquire.*!!\n");
        for (int i = 0; i < failed_parameter_count; i++)
        {
            Picam_GetEnumerationString(PicamEnumeratedType_Parameter, failed_parameter_array[i], &string);
            printf("\tFailed parameter %d: %s.\n", (i+1), string);
        }
        Picam_DestroyString(string);
        return false;
    }

}

//get height and width of frame from looking at the committed ROI
void getXandY(PicamHandle cam, piint *x, piint *y)
{
    //here we assume there is only 1 ROI (as we did not assign any ROI parameters in this example
    //see Rois sample for more examples on ROI
    const PicamRois* rois; piint width, height, xbin, ybin;
    Picam_GetParameterRoisValue(cam, PicamParameter_Rois, &rois);
    
    width = rois[0].roi_array[0].width;
    height = rois[0].roi_array[0].height;
    xbin = rois[0].roi_array[0].x_binning;
    ybin = rois[0].roi_array[0].y_binning;

    //determine rows and columns by dividing ROI length by binning in respective direction
    *x = (piint)(width / xbin);
    *y = (piint)(height / ybin);
}

//calculate mean of image data
piflt GetMean(std::vector<pi16u> imData)
{
    piflt runningCt = 0;
    for (piint loop = 0; loop < (piint)imData.size(); loop++)
    {
        runningCt += (piflt)imData.at(loop);
    }
    return runningCt / imData.size();
}

//asynchronous acquisiton and type cqsting of returned frame data
void Acquire(PicamHandle cam)
{
    PicamAcquisitionStatus status; PicamAvailableData available; piint readoutStride; piint frameSize;
    pi64s readoutOffset; pibyte* frame; pi16u* frameptr = NULL;
    PicamError err = PicamError_None;

    //get readout bytes and frame elements
    Picam_GetParameterIntegerValue(cam, PicamParameter_ReadoutStride, &readoutStride);
    Picam_GetParameterIntegerValue(cam, PicamParameter_FrameSize, &frameSize);
    std::vector<pi16u> imageData16(frameSize / 2, 0);

    //get height and width of opened camera (to set up image containers)
    piint rows, cols;
    getXandY(cam, &cols, &rows);
    //openCV image object with the size of camera (rows, cols)
    cv::Mat image = cv::Mat(rows, cols, CV_16UC1);
    cv::Mat adjImage; //destination for contrast-adjusted image

    Picam_StartAcquisition(cam);
    printf("**Acquisiton Started...\n");

    do
    {
        Picam_WaitForAcquisitionUpdate(cam, -1, &available, &status);
        //image processing and display happens in the following loop
        if (available.readout_count > 0)
        {
            //traverse through readouts returned by the wait call
            for (int i = 0; i < available.readout_count; i++)
            {
                readoutOffset = readoutStride * i;
                //initial_readout points to first frame returned by most recent Wait
                frame = static_cast<pibyte*>(available.initial_readout) + readoutOffset;
                frameptr = reinterpret_cast<pi16u*>(frame); //assumes 16-bit image. Will NOT work with 18-bit readout cameras (32-bit data object)
                //copy image data from AvailableData into vector
                //if running with other threads that have PICam access, use mutex lock on initial_readout pointer
                std::vector<pi16u> imageData16(frameptr, frameptr + frameSize / 2);
                printf("\tReadout Received. Image Mean: %0.2f counts.\n", GetMean(imageData16));
                if (i == (available.readout_count) - 1) //display the last readout returned by the most recent Wait
                {
                    std::memcpy(image.data, imageData16.data(), imageData16.size() * sizeof(pi16u));
                    cv::normalize(image, adjImage, 0, 65535, cv::NORM_MINMAX);
                    cv::imshow("Frame", adjImage);
                    cv::waitKey(1);
                }
            }
        }
    } while (status.running || err == PicamError_TimeOutOccurred);
    Picam_StopAcquisition(cam);
    printf("...Acquisiton Stopped**\nPress any key after clicking display, or wait 20 secs to exit image display.\n");
    cv::waitKey(20000);         //leaves final frame up for 20 secs or key press
    return;
}

//open the first connected camera. If no connected cameras, open a virtual ProEM
void OpenCamera(PicamCameraID *camID, PicamHandle *camHandle)
{
    const pichar* string;
    if (Picam_OpenFirstCamera(camHandle) == PicamError_None)
    {
        Picam_GetCameraID(*(camHandle), camID);
    }
    else
    {
        Picam_ConnectDemoCamera(PicamModel_ProEMHS1024BExcelon, "VirtualCamera", camID);
        Picam_OpenCamera(camID, camHandle);
    }
    Picam_GetEnumerationString(PicamEnumeratedType_Model, camID->model, &string);
    printf("Camera opened: %s  (SN:%s) [%s]\n", string, camID->serial_number, camID->sensor_name);
    Picam_DestroyString(string);
    return;
}

int main()
{
    //workflow for PICam experiment: initialize --> open camera --> set parameters --> acquire --> close camera --> uninitialize
    Picam_InitializeLibrary();
    PicamHandle camera; PicamCameraID id;

    OpenCamera(&id, &camera);

    if (ArmParameters(camera))
    {
        //for real experiments you would want to make sure camera is cooled before acquiring
        Acquire(camera);
    }

    Picam_CloseCamera(camera);
    Picam_DisconnectDemoCamera(&id);
    Picam_UninitializeLibrary();
}
