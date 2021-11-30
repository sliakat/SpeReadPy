// CameraTestDynamicLink.cpp : This file contains the 'main' function. Program execution begins and ends there.
// runtime load of Picam.dll -- app designed to test camera connection and verify version of dll in runtime path
// will load ProHS1024BX3 demo if no live camera detected
// **acquisition part assumes 16-bit data

//benefit - can compile using only Windows libraries, no static PICam lib link needed

#include <iostream>
#include <vector>
#include <windows.h> 

#define NUM_FRAMES 5

//define structs
struct PicamCameraID {
    int model;
    int computer_interface;
    char sensor_name[64];
    char serial_number[64];
};

struct PicamAvailableData {
    void* initial_readout;
    long long readout_count;
};

typedef enum PicamAcquisitionErrorsMask
{
    PicamAcquisitionErrorsMask_None = 0x00,
    PicamAcquisitionErrorsMask_CameraFaulted = 0x10,
    PicamAcquisitionErrorsMask_ConnectionLost = 0x02,
    PicamAcquisitionErrorsMask_ShutterOverheated = 0x08,
    PicamAcquisitionErrorsMask_DataLost = 0x01,
    PicamAcquisitionErrorsMask_DataNotArriving = 0x04
} PicamAcquisitionErrorsMask;

//prototype dll calls
typedef int(__cdecl* MYPROC0)(void);
typedef int(__cdecl* MYPROC1)(int*, int*, int*, int*);
typedef int(__cdecl* MYPROC2)(bool*);
typedef int(__cdecl* MYPROC3)(void**);
typedef int(__cdecl* MYPROC4)(void*, PicamCameraID*);
typedef int(__cdecl* MYPROC5)(int, const char*, PicamCameraID*);
typedef int(__cdecl* MYPROC6)(int, int, const char**);
typedef int(__cdecl* MYPROC7)(const PicamCameraID*, void**);
typedef int(__cdecl* MYPROC8)(const char*);
typedef int(__cdecl* MYPROC9)(void*);
typedef int(__cdecl* MYPROC10)(const PicamCameraID*);
typedef int(__cdecl* MYPROC11)(void*, long long, int, PicamAvailableData*, PicamAcquisitionErrorsMask*);
typedef int(__cdecl* MYPROC12)(void*, int, int*);


//declare dll stuff
HINSTANCE hinstLib;
MYPROC0 Init, UnInit;
MYPROC1 GetPICamVersion;
MYPROC2 IsInit;
MYPROC3 OpenFirstCamera;
MYPROC4 GetCameraID;
MYPROC5 ConnectDemoCamera;
MYPROC6 GetEnumerationString;
MYPROC7 PICamOpen;
MYPROC8 DestroyString;
MYPROC9 CloseCamera;
MYPROC10 DisconnectDemoCamera;
MYPROC11 PICamAcquire;
MYPROC12 GetIntParam;

void EnumerationString(int type, int value, const char** string)
{
    GetEnumerationString = (MYPROC6)GetProcAddress(hinstLib, "Picam_GetEnumerationString");    
    GetEnumerationString(type, value, string);
}

void DestroyEnumString(const char* string)
{
    DestroyString = (MYPROC8)GetProcAddress(hinstLib, "Picam_DestroyString");
    DestroyString(string);
}

double GetMean(std::vector<unsigned short> imData)
{
    double runningCt = 0;
    for (int loop = 0; loop < (int)imData.size(); loop++)
    {
        runningCt += (double)imData.at(loop);
    }
    return runningCt / imData.size();
}

void AcquireOne(void* cam)
{
    PicamAcquisitionErrorsMask mask;
    PicamAvailableData available;
    PICamAcquire = (MYPROC11)GetProcAddress(hinstLib, "Picam_Acquire");
    printf("Acquiring %d frame(s) with default settings...\n", NUM_FRAMES);
    if (PICamAcquire(cam, NUM_FRAMES, -1, &available, &mask) == 0)   //synchronous acquire
    {
        if (mask == 0)
        {
            int readoutStride, frameSize = 0;
            GetIntParam = (MYPROC12)GetProcAddress(hinstLib, "Picam_GetParameterIntegerValue");
            GetIntParam(cam, 16842797, &readoutStride); //check Picam.h for parameter enums
            GetIntParam(cam, 16842794, &frameSize);
            double meanCts;
            long long readoutOffset;
            unsigned char* frame; unsigned short* frameptr = NULL;
            
            //go to last frame in case multiple readouts
            readoutOffset = readoutStride * (available.readout_count - 1);
            frame = static_cast<unsigned char*>(available.initial_readout) + readoutOffset;
            frameptr = reinterpret_cast<unsigned short*>(frame);
            std::vector<unsigned short> data16(frameptr, frameptr + frameSize / 2);
            printf("\t%d frame(s) acquired. Mean Counts (most recent readout): %0.2f\n", (int)available.readout_count, GetMean(data16));
            return;
        }
    }
    // this will not execute unless the acquisiton fails
    const char* string;
    EnumerationString(25, mask, &string);
    printf("\tAcquisiton failed, error: %s.\n", string);
    DestroyEnumString(string);
}

void OpenCamera(PicamCameraID *camID, void* *camHandle, bool *demo)
{
    OpenFirstCamera = (MYPROC3)GetProcAddress(hinstLib, "Picam_OpenFirstCamera");  
    const char* string;
    if (OpenFirstCamera(camHandle) == 0)
    {
        GetCameraID = (MYPROC4)GetProcAddress(hinstLib, "Picam_GetCameraID");
        GetCameraID(*(camHandle), camID);
        *(demo) = false;
    }
    else
    {
        printf("No live camera connected. Trying to open demo camera.\n");
        ConnectDemoCamera = (MYPROC5)GetProcAddress(hinstLib, "Picam_ConnectDemoCamera");
        PICamOpen = (MYPROC7)GetProcAddress(hinstLib, "Picam_OpenCamera");
        ConnectDemoCamera(1206, "VirtualCamera", camID);    //model 1206 = ProHS-1024BX3
        PICamOpen(camID, camHandle);
        *(demo) = true;
    }
    EnumerationString(2, camID->model, &string);
    printf("Camera Opened: %s (SN:%s) [%s]\n", string, camID->serial_number, camID->sensor_name);
    DestroyEnumString(string);
}

int main()
{
    hinstLib = LoadLibrary(TEXT("Picam.dll"));    
    BOOL fFreeResult = FALSE;    
    bool initStatus, isDemo = FALSE;
    int major, minor, distribution, released = 0;
    void* cam;
    PicamCameraID camID;

    if (hinstLib != NULL)
    {
        Init = (MYPROC0)GetProcAddress(hinstLib, "Picam_InitializeLibrary");        
        UnInit = (MYPROC0)GetProcAddress(hinstLib, "Picam_UninitializeLibrary");
        IsInit = (MYPROC2)GetProcAddress(hinstLib, "Picam_IsLibraryInitialized");
        CloseCamera = (MYPROC9)GetProcAddress(hinstLib, "Picam_CloseCamera");
        
        (Init)();
        (IsInit)(&initStatus);
        printf("Initialize Status: %s\n", initStatus ? "Initialized" : "UnInitialized");
        if (initStatus)
        {
            GetPICamVersion = (MYPROC1)GetProcAddress(hinstLib, "Picam_GetVersion");
            GetPICamVersion(&major, &minor, &distribution, &released);
            printf("\t**PICam version: %d.%d.%d.%d\n", major, minor, distribution, released);
        }

        OpenCamera(&camID, &cam, &isDemo);
        AcquireOne(cam);
        
        if (CloseCamera(cam) == 0)
        {
            printf("...Camera Closed.\n");
        }
        if (isDemo)
        {
            DisconnectDemoCamera = (MYPROC10)GetProcAddress(hinstLib, "Picam_DisconnectDemoCamera");
            DisconnectDemoCamera(&camID);
        }
        (UnInit)();
        (IsInit)(&initStatus);
        printf("Initialize Status: %s\n", initStatus ? "Initialized" : "UnInitialized");

        // Free the DLL module.
        fFreeResult = FreeLibrary(hinstLib);
        if (fFreeResult)
        {
            printf("\tLibrary module freed. Program complete!\n");
        }
    }
}
