//Basic example of asynchronous acquisiton with a virtual PI-MAX4.

//set number of frames to asynchronously acquire
#define NUM_FRAMES  100

#include <iostream>
#include <vector>
#include "picam.h"

//set virtual camera to run at ~25fps
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

//asynchronous acquisiton and type cqsting of returned frame data
void Acquire(PicamHandle cam)
{
    PicamAcquisitionStatus status; PicamAvailableData available; piint readoutStride; piint frameSize;
    pi64s lastReadoutOffset; pibyte* frame; pi16u* frameptr = NULL;
    PicamError err = PicamError_None;
    Picam_GetParameterIntegerValue(cam, PicamParameter_ReadoutStride, &readoutStride);
    Picam_GetParameterIntegerValue(cam, PicamParameter_FrameSize, &frameSize);
    std::vector<pi16u> imageData16(frameSize / 2, 0);
    //printf("Frame Size: %d\n", frameSize);
    Picam_StartAcquisition(cam);
    printf("**Acquisiton Started...\n");

    do
    {
        Picam_WaitForAcquisitionUpdate(cam, -1, &available, &status);
        if (available.readout_count > 0)
        {
            //move pointer to the most recent readout in the circular buffer
            lastReadoutOffset = readoutStride * (available.readout_count - 1);
            frame = static_cast<pibyte*>(available.initial_readout) + lastReadoutOffset;
            frameptr = reinterpret_cast<pi16u*>(frame);
            //copy image data from AvailableData into vector
            //if running with other threads that have PICam access, use mutex lock on initial_readout pointer
            std::vector<pi16u> imageData16(frameptr, frameptr + frameSize/2);
            printf("\tReadout Received. Image Mean: %0.2f counts.\n", GetMean(imageData16));
        }
    } while (status.running || err == PicamError_TimeOutOccurred);
    Picam_StopAcquisition(cam);
    printf("...Acquisiton Stopped**\n");
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
