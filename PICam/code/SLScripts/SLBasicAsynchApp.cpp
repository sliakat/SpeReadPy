//Basic example of asynchronous acquisiton with a virtual PI-MAX4.
//Incoming data stream is displayed using OpenCV.
//
//Scope: Demonstrate a simple way to observe, copy, and display incoming
//  frame data from an aynchronous acquisiton.
//External library requirement: **MUST have OpenCV installed and properly linked.**
//  This program was tested with OpenCV 4.5.2
//Limitations: A virtual PI-MAX4 1024i is hard-coded with some pre-determined parameters,
//  so that any user can just compile, run, and observe without need for any input.
//  These parameters may not apply to all cameras. Please keep in mind the scope of the
//  example is to demonstrate the asynchronous acquisiton. For more advanced usage, please
//  refer to the PICam samples provided with the SDK.


//set number of frames to asynchronously acquire
#define NUM_FRAMES  100

#include <iostream>
#include <vector>
#include "picam.h"

#include <opencv2/core.hpp>
#include <opencv2/imgcodecs.hpp>
#include <opencv2/highgui.hpp>

//set virtual camera to run at ~25fps (applicable for a virtual PI-MAX 1024i)
void ArmParameters(PicamHandle cam)
{
    piflt readRate; const PicamParameter* failed_parameter_array; piint failed_parameter_count = 0;
    //gate params
    PicamPulse genericPulser;
    genericPulser.delay = 250; genericPulser.width = 100; //250ns delay, 100ns width
    Picam_SetParameterPulseValue(cam, PicamParameter_RepetitiveGate, &genericPulser);
    //trigger
    Picam_SetParameterFloatingPointValue(cam, PicamParameter_TriggerFrequency, 100);//internal trigger frequency 100Hz
    //ADC
    Picam_SetParameterFloatingPointValue(cam, PicamParameter_AdcSpeed, 16); //16MHz
    Picam_SetParameterIntegerValue(cam, PicamParameter_ReadoutPortCount, 2); // 2-port readout
    //frame count
    Picam_SetParameterLargeIntegerValue(cam, PicamParameter_ReadoutCount, NUM_FRAMES);
    //commit and print readout rate
    Picam_CommitParameters(cam, &failed_parameter_array, &failed_parameter_count);
    if (failed_parameter_count == 0)
    {
        Picam_GetParameterFloatingPointValue(cam, PicamParameter_ReadoutRateCalculation, &readRate);
        printf("**Camera Readout Rate: %0.2f fps.**\n", readRate);
    }
    return;
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

//asynchronous acquisiton and type casting of returned frame data
void Acquire(PicamHandle cam)
{
    PicamAcquisitionStatus status; PicamAvailableData available; piint readoutStride; piint frameSize;
    pi64s lastReadoutOffset; pibyte* frame; pi16u* frameptr = NULL;
    PicamError err = PicamError_None;

    //get readout bytes and frame elements
    Picam_GetParameterIntegerValue(cam, PicamParameter_ReadoutStride, &readoutStride);
    Picam_GetParameterIntegerValue(cam, PicamParameter_FrameSize, &frameSize);
    std::vector<pi16u> imageData16(frameSize / 2, 0);

    //get height and width of opened camera (to set up image containers)
    piint rows, cols;
    Picam_GetParameterIntegerValue(cam, PicamParameter_SensorActiveHeight, &rows);
    Picam_GetParameterIntegerValue(cam, PicamParameter_SensorActiveWidth, &cols);
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
            //move pointer to the most recent readout in the circular buffer
            lastReadoutOffset = readoutStride * (available.readout_count - 1);
            frame = static_cast<pibyte*>(available.initial_readout) + lastReadoutOffset;
            frameptr = reinterpret_cast<pi16u*>(frame);
            //copy image data from AvailableData into vector
            //if running with other threads that have PICam access, use mutex lock on initial_readout pointer
            std::vector<pi16u> imageData16(frameptr, frameptr + frameSize / 2);
            printf("\tReadout Received. Image Mean: %0.2f counts.\n", GetMean(imageData16));
            std::memcpy(image.data, imageData16.data(), imageData16.size() * sizeof(pi16u));
            cv::normalize(image, adjImage, 0, 65535, cv::NORM_MINMAX);
            cv::imshow("Frame", adjImage);
            cv::waitKey(1);
        }
    } while (status.running || err == PicamError_TimeOutOccurred);
    Picam_StopAcquisition(cam);
    printf("...Acquisiton Stopped**\nPress any key after clicking display, or wait 20 secs to exit image display.\n");
    cv::waitKey(20000);         //leaves final frame up for 20 secs or key press
    return;
}

int main()
{
    Picam_InitializeLibrary();
    PicamHandle camera; PicamCameraID id; const pichar* string;

    //connect and open a virtual PI-MAX4
    Picam_ConnectDemoCamera(PicamModel_PIMax41024I, "VirtualCamera", &id);
    Picam_OpenCamera(&id, &camera);
    Picam_GetEnumerationString(PicamEnumeratedType_Model, id.model, &string);
    printf("Camera opened: %s  (SN:%s) [%s]\n", string, id.serial_number, id.sensor_name);
    Picam_DestroyString(string);

    ArmParameters(camera);
    Acquire(camera);

    Picam_CloseCamera(camera);
    Picam_DisconnectDemoCamera(&id);
    Picam_UninitializeLibrary();
}
