// AcquisitionState.cpp
// This sample utilizes the Picam Advanced API demonstrating the
// usage of the PicamAcquisitionStateUpdated Callback.  This sample 
// uses a single callback to handle all PicamAcquisitionStates, 
// however separate functions can be specified for each State.

#include <iostream>
#include <vector>

#include "picam_advanced.h"

//#defines
#define NUM_FRAMES      20
#define BUFFER_DEPTH    4
#define TIMEOUT         -1  //infinite

//prototypes for callback functions
PicamError PIL_CALL ReadoutStatusCB( PicamHandle, PicamAcquisitionState, 
                                     const PicamAcquisitionStateCounters*, 
                                     PicamAcquisitionStateErrorsMask errors );

//prototypes for helper functions
void PrintEnumString( PicamEnumeratedType, piint );
void PrintError( PicamError );

//global variables to cache AcquisitionState errors
pibln bErrorOccurred_ReadoutStarted = false;
pibln bErrorOccurred_ReadoutEnded = false;
pi64s ReadoutsStartedCount = 0;
pi64s ReadoutsEndedCount = 0;

pibool InitializeAndOpen( PicamHandle *hDevice )
{
    piint id_cnt = 0;
    const PicamCameraID* id = 0;
    PicamError e = PicamError_None;

    if( Picam_InitializeLibrary() != PicamError_None )
    {
        std::cout << "Cannot Initialize Picam Library" << std::endl;
        return false;
    }
    if( ( e = Picam_GetAvailableCameraIDs( &id, &id_cnt ) ) != PicamError_None )
    {
        PrintError( e );
        Picam_UninitializeLibrary();
        return false;
    }
    if( !id_cnt )
    {
        std::cout << "No Cameras Available" << std::endl;
        Picam_DestroyCameraIDs( id );
        Picam_UninitializeLibrary();
        return false;
    }
    if( ( e = PicamAdvanced_OpenCameraDevice( id, hDevice ) ) != PicamError_None )
    {
        PrintError( e );
        Picam_DestroyCameraIDs( id );
        Picam_UninitializeLibrary();
        return false;
    }

    Picam_DestroyCameraIDs( id );

    return true;
}
pibool ConfigureExperiment( PicamHandle hDevice, std::vector<pibyte> &dataBuf )
{
    PicamError e;
	PicamHandle hModel;
    PicamAcquisitionBuffer acqBuf;
    piint bufferDepth = BUFFER_DEPTH;
    piint frameSize = 0;
    pibln committed;
    const PicamParameter* failed_parameters;
    piint failed_parameters_count;
    const PicamCollectionConstraint  *constraint;
    piflt adcSpeed = 0.;

    if( ( e = Picam_GetParameterIntegerValue( hDevice, PicamParameter_ReadoutStride, &frameSize ) ) != PicamError_None )
    {
        PrintError( e );
        return false;
    }
    dataBuf.resize( frameSize * bufferDepth );
    PicamAdvanced_GetCameraModel( hDevice, &hModel );

    //determine slowest ADC speed for camera
    //Set ADC Quality to Low Noise
    if( ( e = Picam_SetParameterIntegerValue( hModel, PicamParameter_AdcQuality, PicamAdcQuality_LowNoise ) ) != PicamError_None )
        PrintError( e );
    //Query ADC Speed capabilities
    if( ( e = Picam_GetParameterCollectionConstraint( hModel, PicamParameter_AdcSpeed, PicamConstraintCategory_Capable,
                                                      &constraint ) ) != PicamError_None )
        PrintError( e );
    else
    {
        adcSpeed = constraint->values_array[0];
        //Choose slowest speed
        for( piint i = 1; i < constraint->values_count; i++ )
        {
            if( constraint->values_array[i] < constraint->values_array[i-1] )
                adcSpeed = constraint->values_array[i];
        }
    }
    Picam_DestroyCollectionConstraints(constraint);

    std::cout << "Setting Adc Speed to " << adcSpeed << " MHz." << std::endl;
    //Set ADC Speed
    if( ( e = Picam_SetParameterFloatingPointValue( hModel, PicamParameter_AdcSpeed, adcSpeed ) ) != PicamError_None )
        PrintError( e );//Adc speed not changed, but continuing anyway

    //Set Number of Readouts in Acquisition
    if( ( e = Picam_SetParameterLargeIntegerValue( hModel, PicamParameter_ReadoutCount, NUM_FRAMES ) ) != PicamError_None )
        PrintError( e );

    //commit changes to hardware
    if( ( e = Picam_AreParametersCommitted( hModel, &committed ) ) != PicamError_None )
        PrintError( e );
    if( ( e = Picam_CommitParameters( hModel, &failed_parameters, &failed_parameters_count ) ) != PicamError_None )
        PrintError( e );
    // - print any invalid parameters
    if( failed_parameters_count > 0 )
    {
        std::cout << "The following parameters are invalid:" << std::endl;
        for( piint i = 0; i < failed_parameters_count; ++i )
        {
            std::cout << "    ";
            PrintEnumString( PicamEnumeratedType_Parameter, failed_parameters[i] );
            std::cout << std::endl;
        }
    }
    // - free picam-allocated resources
    Picam_DestroyParameters( failed_parameters );

    acqBuf.memory = &dataBuf[0];
	acqBuf.memory_size = frameSize * bufferDepth;

	if( ( e = PicamAdvanced_SetAcquisitionBuffer( hDevice, &acqBuf ) ) != PicamError_None )
    {
        PrintError( e );
        return false;
    }

    return true;
}

void Acquire( PicamHandle d )
{
    Picam_StartAcquisition( d ); 

    PicamAcquisitionStatus status;
    PicamAvailableData available;
    PicamError err;
    piint dVal = 0;
    pichar D[]="|/-\\|/-\\";

    std::cout << "Acquiring " << NUM_FRAMES << " frames" << std::endl << std::endl << std::endl;
    do
    {
        err = Picam_WaitForAcquisitionUpdate( d, TIMEOUT, &available, &status );
        if( status.running )
        {
            dVal = ( dVal + available.readout_count ) % 8;
            std::cout << D[dVal] << '\r' << std::flush;
        }
    }
    while( status.running || err == PicamError_TimeOutOccurred );
}

void EnableReadoutStatusCallbacks( PicamHandle hDevice, pibln &bStarted, pibln &bEnded )
{
    pibln detectable;

    PicamAdvanced_CanRegisterForAcquisitionStateUpdated( hDevice, PicamAcquisitionState_ReadoutStarted, &detectable );
    if( !detectable )
        std::cout << "Camera doesn't support AcquisitionState_ReadoutStarted" << std::endl;
    else
    {
        if( PicamAdvanced_RegisterForAcquisitionStateUpdated( hDevice, PicamAcquisitionState_ReadoutStarted,
                                                        ReadoutStatusCB ) == PicamError_None )
            bStarted = true;
    }
    PicamAdvanced_CanRegisterForAcquisitionStateUpdated( hDevice, PicamAcquisitionState_ReadoutEnded, &detectable );
    if( !detectable )
        std::cout << "Camera doesn't support AcquisitionState_ReadoutEnded" << std::endl;
    else
    {
        if( PicamAdvanced_RegisterForAcquisitionStateUpdated( hDevice, PicamAcquisitionState_ReadoutEnded,
                                                        ReadoutStatusCB ) == PicamError_None )
            bEnded = true;
    }
}

void DisableReadoutStatusCallbacks( PicamHandle hDevice, pibln started, pibln ended )
{
    if( started )
        PicamAdvanced_UnregisterForAcquisitionStateUpdated( hDevice, PicamAcquisitionState_ReadoutStarted,
                                                            (PicamAcquisitionStateUpdatedCallback)ReadoutStatusCB );
    if( ended )
        PicamAdvanced_UnregisterForAcquisitionStateUpdated( hDevice, PicamAcquisitionState_ReadoutEnded,
                                                            (PicamAcquisitionStateUpdatedCallback)ReadoutStatusCB );
}
int main()
{
    std::vector<pibyte> userBuffer;
	PicamHandle hDevice;
    pibln readoutStartedEnabled = false;
    pibln readoutDoneEnabled = false;

    if( !InitializeAndOpen( &hDevice ) )
        return 0;

    if( !ConfigureExperiment( hDevice, userBuffer ) )
    {
        PicamAdvanced_CloseCameraDevice( hDevice );
        Picam_UninitializeLibrary();
        return 0;
    }

    EnableReadoutStatusCallbacks( hDevice, readoutStartedEnabled, readoutDoneEnabled );

    Acquire( hDevice );

    DisableReadoutStatusCallbacks( hDevice, readoutStartedEnabled, readoutDoneEnabled );

    std::cout << std::endl << "Acquisition Complete" << std::endl;
    if( readoutStartedEnabled )
        std::cout << "Number of AcquisitionState_ReadoutStarted: " << ReadoutsStartedCount << std::endl;
    if( readoutDoneEnabled )
        std::cout << "Number of AcquisitionState_ReadoutEnded: " << ReadoutsEndedCount << std::endl;

    PicamAdvanced_CloseCameraDevice( hDevice );

    Picam_UninitializeLibrary();

	return 0;
}

//callbacks
PicamError PIL_CALL ReadoutStatusCB( PicamHandle /*device*/, 
                    PicamAcquisitionState whatfor, 
                    const PicamAcquisitionStateCounters* counters,
                    PicamAcquisitionStateErrorsMask errors )
{
    switch( whatfor )
    {
        case PicamAcquisitionState_ReadoutStarted:
            ReadoutsStartedCount = counters->readout_started_count;
            if( errors & PicamAcquisitionStateErrorsMask_LostCount )
            {
                if( !bErrorOccurred_ReadoutStarted )//skip notification if not new
                {
                    bErrorOccurred_ReadoutStarted = true;
                    std::cout << "ReadoutStatusCallback::ReadoutStarted - Lost Counts @ " << counters->readout_started_count << std::endl;
                }
            }
            else
            {
                if( bErrorOccurred_ReadoutStarted )
                {
                    bErrorOccurred_ReadoutStarted = false;
                    std::cout << "ReadoutStartedCallback:ReadoutStarted - Error Condition Removed @ " << counters->readout_started_count << std::endl;
                }
            }
            break;
        case PicamAcquisitionState_ReadoutEnded:
            ReadoutsEndedCount = counters->readout_ended_count;
            if( errors & PicamAcquisitionStateErrorsMask_LostCount )
            {
                if( !bErrorOccurred_ReadoutEnded )//skip notification if not new
                {
                    bErrorOccurred_ReadoutEnded = true;
                    std::cout << "ReadoutStatusCallback::ReadoutEnded - Lost Counts @ " << counters->readout_started_count << std::endl;
                }
            }
            else
            {
                if( bErrorOccurred_ReadoutEnded )
                {
                    bErrorOccurred_ReadoutEnded = false;
                    std::cout << "ReadoutStartedCallback:ReadoutEnded - Error Condition Removed @ " << counters->readout_started_count << std::endl;
                }
            }
            break;
    }
    return PicamError_None;
}


// - prints any picam enum
void PrintEnumString( PicamEnumeratedType type, piint value )
{
    const pichar* string;
    Picam_GetEnumerationString( type, value, &string );
    std::cout << string;
    Picam_DestroyString( string );
}

void PrintError( PicamError e )
{
    const pichar *s;
    Picam_GetEnumerationString( PicamEnumeratedType_Error, e, &s );
    std::cout << s << std::endl;
    Picam_DestroyString( s );
}

