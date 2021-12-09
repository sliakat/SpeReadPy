// CameraTestCB.cpp : This file contains the 'main' function. Program execution begins and ends there.
// Similar purpose CameraTestDLL.cpp, but uses the AcquisitionUpdated callback from the Advanced API.
// if a valid long int is entered as a command line argument, the # of desired readouts will be set to that
// can be compiled without any static PICam libraries

#include <iostream>
#include <vector>
#include <windows.h>
#include <cstdlib>

//define structs
typedef enum PicamAcquisitionErrorsMask
{
    PicamAcquisitionErrorsMask_None = 0x00,
    PicamAcquisitionErrorsMask_CameraFaulted = 0x10,
    PicamAcquisitionErrorsMask_ConnectionLost = 0x02,
    PicamAcquisitionErrorsMask_ShutterOverheated = 0x08,
    PicamAcquisitionErrorsMask_DataLost = 0x01,
    PicamAcquisitionErrorsMask_DataNotArriving = 0x04
} PicamAcquisitionErrorsMask;

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

struct PicamAcquisitionStatus {
    bool running;
    PicamAcquisitionErrorsMask errors;
    double readout_rate;
};

//globals
long long numFrames = 5;    //default if no CLI for frame #
int readCount, readoutStride, frameSize = 0;
void* dev;

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
typedef int(__cdecl* MYPROCCB)(void*, const PicamAvailableData*, const PicamAcquisitionStatus*);
typedef int(__cdecl* MYPROC11)(void*, MYPROCCB);
typedef int(__cdecl* MYPROC12)(void*, int, int*);
typedef int(__cdecl* MYPROC13)(void*, void**);
typedef int(__cdecl* MYPROC14)(void*, bool*);
typedef int(__cdecl* MYPROC15)(void*, int, long long);

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
MYPROC9 CloseCamera, PICamStartAcq, PICamStopAcq;
MYPROC10 DisconnectDemoCamera;
MYPROC11 RegisterCB, UnregisterCB;
MYPROC12 GetIntParam;
MYPROC13 GetDevHandle;
MYPROC14 RunningStatus;
MYPROC15 SetLongIntParam;

void GetProcesses()
{
    Init = (MYPROC0)GetProcAddress(hinstLib, "Picam_InitializeLibrary");
    UnInit = (MYPROC0)GetProcAddress(hinstLib, "Picam_UninitializeLibrary");
    IsInit = (MYPROC2)GetProcAddress(hinstLib, "Picam_IsLibraryInitialized");
    CloseCamera = (MYPROC9)GetProcAddress(hinstLib, "PicamAdvanced_CloseCameraDevice");
    RunningStatus = (MYPROC14)GetProcAddress(hinstLib, "Picam_IsAcquisitionRunning");
    RegisterCB = (MYPROC11)GetProcAddress(hinstLib, "PicamAdvanced_RegisterForAcquisitionUpdated");
    UnregisterCB = (MYPROC11)GetProcAddress(hinstLib, "PicamAdvanced_UnregisterForAcquisitionUpdated");
    PICamStopAcq = (MYPROC9)GetProcAddress(hinstLib, "Picam_StopAcquisition");
    GetPICamVersion = (MYPROC1)GetProcAddress(hinstLib, "Picam_GetVersion");
    DisconnectDemoCamera = (MYPROC10)GetProcAddress(hinstLib, "Picam_DisconnectDemoCamera");
    OpenFirstCamera = (MYPROC3)GetProcAddress(hinstLib, "Picam_OpenFirstCamera");
    GetCameraID = (MYPROC4)GetProcAddress(hinstLib, "Picam_GetCameraID");
    ConnectDemoCamera = (MYPROC5)GetProcAddress(hinstLib, "Picam_ConnectDemoCamera");
    PICamOpen = (MYPROC7)GetProcAddress(hinstLib, "Picam_OpenCamera");
    GetDevHandle = (MYPROC13)GetProcAddress(hinstLib, "PicamAdvanced_GetCameraDevice");
    SetLongIntParam = (MYPROC15)GetProcAddress(hinstLib, "Picam_SetParameterLargeIntegerValue");
    PICamStartAcq = (MYPROC9)GetProcAddress(hinstLib, "Picam_StartAcquisition");
    GetEnumerationString = (MYPROC6)GetProcAddress(hinstLib, "Picam_GetEnumerationString");
    DestroyString = (MYPROC8)GetProcAddress(hinstLib, "Picam_DestroyString");
    GetIntParam = (MYPROC12)GetProcAddress(hinstLib, "Picam_GetParameterIntegerValue");
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

void GetStrides(void* cam)
{    
    GetIntParam(cam, 16842797, &readoutStride); //check Picam.h for parameter enums
    GetIntParam(cam, 16842794, &frameSize);
}

void EnumerationString(int type, int value, const char** string)
{    
    GetEnumerationString(type, value, string);
}

void DestroyEnumString(const char* string)
{    
    DestroyString(string);
}

int __stdcall AcquisitionUpdated(void* device, const PicamAvailableData* available, const PicamAcquisitionStatus* status)
{
    if (status->running)
    {
        long long readoutOffset;
        unsigned char* frame; unsigned short* frameptr = NULL;
        //go to last frame in case multiple readouts
        readoutOffset = readoutStride * (available->readout_count - 1);
        frame = static_cast<unsigned char*>(available->initial_readout) + readoutOffset;
        frameptr = reinterpret_cast<unsigned short*>(frame);
        std::vector<unsigned short> data16(frameptr, frameptr + frameSize / 2);     //re-using vector should deallocate the old one
        readCount += available->readout_count;
        if (available->readout_count > 0)
        {
            printf("\t%d readout(s) acquired. Mean Counts (most recent readout): %0.2f\n", (int)available->readout_count, GetMean(data16));
            printf("\t\tTotal readouts: %d, current rate: %0.2f readouts/sec\n", readCount, status->readout_rate);
        }
    }    
    else
    {
        const char* string;
        EnumerationString(25, status->errors, &string);
        printf("\tAcquisiton stopped. Error (if any): %s. Status: %s\n", string, status->running? "Running" : "Not Running");
        DestroyEnumString(string);
    }
    return 0;
}

void AcquireCB()
{
    GetStrides(dev);
    SetLongIntParam(dev, 33947688, numFrames);      //setting param with dev handle auto commits if successful
    PICamStartAcq(dev);
    printf("Asynchronously acquiring %d frame(s) with default settings...\n", (int)numFrames);
}

void OpenCamera(PicamCameraID* camID, void** camHandle, bool* demo)
{    
    const char* string;
    if (OpenFirstCamera(camHandle) == 0)
    {        
        GetCameraID(*(camHandle), camID);
        *(demo) = false;
    }
    else
    {
        printf("No live camera connected. Trying to open demo camera.\n");
        ConnectDemoCamera(1206, "VirtualCamera", camID);    //model 1206 = ProHS-1024BX3
        PICamOpen(camID, camHandle);
        *(demo) = true;
    }
    EnumerationString(2, camID->model, &string);
    printf("Camera Opened: %s (SN:%s) [%s]\n", string, camID->serial_number, camID->sensor_name);
    DestroyEnumString(string);    
    GetDevHandle(*(camHandle), &dev);
}

int main(int argc, char** argv)
{
    //check CL arg for valid long long frame #
    if (argc > 1)
    {
        errno = 0;
        char* endptr;
        long long x = strtol(argv[1], &endptr, 10);
        if (endptr == argv[1]) {
            std::cerr << "Invalid number: " << argv[1] << '\n';
        }
        else if (*endptr) {
            std::cerr << "Trailing characters after number: " << argv[1] << '\n';
        }
        else if (errno == ERANGE) {
            std::cerr << "Number out of range: " << argv[1] << '\n';
        }
        else
        {
            numFrames = x;
            printf("**Valid command line input; setting desired readouts to %d.**\n", (int)numFrames);
        }
    }    

    hinstLib = LoadLibrary(TEXT("Picam.dll"));
    BOOL fFreeResult = FALSE;
    bool initStatus, isDemo, running = FALSE;
    int major, minor, distribution, released = 0;
    void* cam;
    PicamCameraID camID;

    if (hinstLib != NULL)
    {
        GetProcesses();
        Init();
        IsInit(&initStatus);
        printf("Initialize Status: %s\n", initStatus ? "Initialized" : "UnInitialized");
        if (initStatus)
        {            
            GetPICamVersion(&major, &minor, &distribution, &released);
            printf("\t**PICam version: %d.%d.%d.%d\n", major, minor, distribution, released);
        }

        OpenCamera(&camID, &cam, &isDemo);

        readCount = 0;
        RegisterCB(dev, (MYPROCCB)AcquisitionUpdated);
        AcquireCB();

        do {
            RunningStatus(cam, &running);
        } while (running);

        UnregisterCB(dev, (MYPROCCB)AcquisitionUpdated);

        bool openStatus = true;
        do {
            if (CloseCamera(dev) == 0)
            {
                openStatus = false;
            }
        } while (openStatus);
        printf("...Camera Closed.\n");

        if (isDemo)
        {            
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
    else
    {
        printf("Could not load Picam.dll properly.\n");
    }
}
