////////////////////////////////////////////////////////////////////////////////
// Configure Sample
// - demonstrates camera setup including:
//   - changing common camera parameters
//   - reading temperature directly from hardware
//   - changing exposure time during acquisition
// - uses the first camera found if any or creates a demo camera
////////////////////////////////////////////////////////////////////////////////

#include <string>
#include <iostream>
#include "picam.h"

// - prints any picam enum
void PrintEnumString( PicamEnumeratedType type, piint value )
{
    const pichar* string;
    Picam_GetEnumerationString( type, value, &string );
    std::cout << string;
    Picam_DestroyString( string );
}

// - prints the camera identity
void PrintCameraID( const PicamCameraID& id )
{
    // - print the model
    PrintEnumString( PicamEnumeratedType_Model, id.model );

    // - print the serial number and sensor
    std::cout << " (SN:" << id.serial_number << ")"
              << " ["    << id.sensor_name   << "]" << std::endl;
}

// - prints error code
void PrintError( PicamError error )
{
    if( error == PicamError_None )
        std::cout << "Succeeded" << std::endl;
    else
    {
        std::cout << "Failed (";
        PrintEnumString( PicamEnumeratedType_Error, error );
        std::cout << ")" << std::endl;
    }
}

// - calculates and prints mean intensity
void CalculateMean( PicamHandle camera, const PicamAvailableData& available )
{
    PicamPixelFormat format;
    Picam_GetParameterIntegerValue(
        camera,
        PicamParameter_PixelFormat,
        reinterpret_cast<piint*>( &format ) );

    piint bit_depth;
    Picam_GetParameterIntegerValue(
        camera,
        PicamParameter_PixelBitDepth,
        &bit_depth );

    if( format == PicamPixelFormat_Monochrome16Bit && bit_depth == 16 )
    {
        piint readout_stride;
        Picam_GetParameterIntegerValue(
            camera,
            PicamParameter_ReadoutStride,
            &readout_stride );

        piint frame_size;
        Picam_GetParameterIntegerValue(
            camera,
            PicamParameter_FrameSize,
            &frame_size );

        const piint pixel_count = frame_size / sizeof( pi16u );
        for( piint r = 0; r < available.readout_count; ++r )
        {
            const pi16u* pixel = reinterpret_cast<const pi16u*>(
                static_cast<const pibyte*>( available.initial_readout ) +
                r*readout_stride );

            piflt mean = 0.0;
            for( piint p = 0; p < pixel_count; ++p )
                mean += *pixel++;
            mean /= pixel_count;

            std::cout << "    Mean Intensity: " << mean << std::endl;
        }
    }
}

// - changes some common camera parameters and applies them to hardware
void Configure( PicamHandle camera )
{
    PicamError error;

    // - set low gain
    std::cout << "Set low analog gain: ";
    error =
        Picam_SetParameterIntegerValue(
            camera,
            PicamParameter_AdcAnalogGain,
            PicamAdcAnalogGain_Low );
    PrintError( error );

    // - set exposure time (in millseconds)
    std::cout << "Set 500 ms exposure time: ";
    error = 
        Picam_SetParameterFloatingPointValue(
            camera,
            PicamParameter_ExposureTime,
            500.0 );
    PrintError( error );

    // - show that the modified parameters need to be applied to hardware
    pibln committed;
    Picam_AreParametersCommitted( camera, &committed );
    if( committed )
        std::cout << "Parameters have not changed" << std::endl;
    else
        std::cout << "Parameters have been modified" << std::endl;

    // - apply the changes to hardware
    std::cout << "Commit to hardware: ";
    const PicamParameter* failed_parameters;
    piint failed_parameters_count;
    error =
        Picam_CommitParameters(
            camera,
            &failed_parameters,
            &failed_parameters_count );
    PrintError( error );

    // - print any invalid parameters
    if( failed_parameters_count > 0 )
    {
        std::cout << "The following parameters are invalid:" << std::endl;
        for( piint i = 0; i < failed_parameters_count; ++i )
        {
            std::cout << "    ";
            PrintEnumString(
                PicamEnumeratedType_Parameter,
                failed_parameters[i] );
            std::cout << std::endl;
        }
    }

    // - free picam-allocated resources
    Picam_DestroyParameters( failed_parameters );
}

// - acquires some data and displays the mean intensity
void Acquire( PicamHandle camera )
{
    std::cout << "Acquire data: ";

    // - acquire some data
    const pi64s readout_count = 1;
    const piint readout_time_out = -1;  // infinite
    PicamAvailableData available;
    PicamAcquisitionErrorsMask errors;
    PicamError error =
        Picam_Acquire(
            camera,
            readout_count,
            readout_time_out,
            &available,
            &errors );
    PrintError( error );

    // - print results
    if( error == PicamError_None && errors == PicamAcquisitionErrorsMask_None )
        CalculateMean( camera, available );
    else
    {
        if( error != PicamError_None )
        {
            std::cout << "    Acquisition failed (";
            PrintEnumString( PicamEnumeratedType_Error, error );
            std::cout << ")" << std::endl;
        }

        if( errors != PicamAcquisitionErrorsMask_None )
        {
            std::cout << "    The following acquisition errors occurred: ";
            PrintEnumString(
                PicamEnumeratedType_AcquisitionErrorsMask,
                errors );
            std::cout << std::endl;
        }
    }
}

// - reads the temperature and temperature status directly from hardware
//   and waits for temperature to lock if requested
void ReadTemperature( PicamHandle camera, pibool lock )
{
    PicamError error;

    // - read temperature
    std::cout << "Read sensor temperature: ";
    piflt temperature;
    error =
        Picam_ReadParameterFloatingPointValue(
            camera,
            PicamParameter_SensorTemperatureReading,
            &temperature );
    PrintError( error );
    if( error == PicamError_None )
    {
        std::cout << "    " << "Temperature is "
                  << temperature << " degrees C" << std::endl;
    }

    // - read temperature status
    std::cout << "Read sensor temperature status: ";
    PicamSensorTemperatureStatus status;
    error =
        Picam_ReadParameterIntegerValue(
            camera,
            PicamParameter_SensorTemperatureStatus,
            reinterpret_cast<piint*>( &status ) );
    PrintError( error );
    if( error == PicamError_None )
    {
        std::cout << "    " << "Status is ";
        PrintEnumString( PicamEnumeratedType_SensorTemperatureStatus, status );
        std::cout << std::endl;
    }

    // - wait indefinitely for temperature to lock if requested
    if( lock )
    {
        std::cout << "Waiting for temperature lock: ";
        error =
            Picam_WaitForStatusParameterValue(
                camera,
                PicamParameter_SensorTemperatureStatus,
                PicamSensorTemperatureStatus_Locked,
                -1 );
        PrintError( error );
    }
}

// - acquires data while changing exposure time
void AcquireAndExpose( PicamHandle camera )
{
    PicamError error;

    // - set to acquire 10 readouts
    std::cout << "Set 10 readouts: ";
    const pi64s readout_count = 10;
    error =
        Picam_SetParameterLargeIntegerValue(
            camera,
            PicamParameter_ReadoutCount,
            readout_count );
    PrintError( error );

    // - commit
    std::cout << "Commit to hardware: ";
    const PicamParameter* failed_parameters;
    piint failed_parameters_count;
    error =
        Picam_CommitParameters(
            camera,
            &failed_parameters,
            &failed_parameters_count );
    Picam_DestroyParameters( failed_parameters );
    PrintError( error );

    // - acquire asynchronously
    std::cout << "Acquire:" << std::endl;
    std::cout << "    Start: ";
    error = Picam_StartAcquisition( camera );
    PrintError( error );

    // - acquisition loop
    const piint readout_time_out = -1;  // infinite
    PicamAvailableData available;
    PicamAcquisitionStatus status;
    pibool running = true;
    pi64s readouts_acquired = 0;
    pibool changed_exposure = false;
    while( (error == PicamError_None || error == PicamError_TimeOutOccurred) &&
           running )
    {
        // - wait for data, completion or failure
        error =
            Picam_WaitForAcquisitionUpdate(
                camera,
                readout_time_out,
                &available,
                &status );

        // - display each result
        if( error == PicamError_None &&
            status.errors == PicamAcquisitionErrorsMask_None )
        {
            running = status.running != 0;
            readouts_acquired += available.readout_count;
            if( available.readout_count )
                CalculateMean( camera, available );

            // - change exposure time in the midst
            if( !changed_exposure && readouts_acquired >= readout_count/2 )
            {
                changed_exposure = true;
                piflt exposure;
                Picam_GetParameterFloatingPointValue(
                    camera,
                    PicamParameter_ExposureTime,
                    &exposure );
                exposure /= 2.0;
                std::cout << "    Halve exposure time: ";
                PicamError online_error =
                    Picam_SetParameterFloatingPointValueOnline(
                        camera,
                        PicamParameter_ExposureTime,
                        exposure );
                PrintError( online_error );
            }
        }
        else
        {
            if( error != PicamError_None )
            {
                std::cout << "    Acquisition failed (";
                PrintEnumString( PicamEnumeratedType_Error, error );
                std::cout << ")" << std::endl;
            }

            if( status.errors != PicamAcquisitionErrorsMask_None )
            {
                std::cout << "    The following acquisition errors occurred: ";
                PrintEnumString(
                    PicamEnumeratedType_AcquisitionErrorsMask,
                    status.errors );
                std::cout << std::endl;
            }
        }
    }
}

int main( int argc, char* argv[] )
{
    // - set formatting options
    std::cout << std::boolalpha;

    // - allow the optional argument 'lock' to wait for temperature lock
    pibool lock = false;
    if( argc == 2 )
    {
        std::string arg( argv[1] );
        if( arg == "lock" )
            lock = true;
        else
        {
            std::cout << "Invalid argument to lock temperature.";
            return -1;
        }
    }

    Picam_InitializeLibrary();

    // - open the first camera if any or create a demo camera
    PicamHandle camera;
    PicamCameraID id;
    if( Picam_OpenFirstCamera( &camera ) == PicamError_None )
        Picam_GetCameraID( camera, &id );
    else
    {
        Picam_ConnectDemoCamera(
            PicamModel_Pixis100B,
            "12345",
            &id );
        Picam_OpenCamera( &id, &camera );
    }

    PrintCameraID( id );
    std::cout << std::endl;

    std::cout << "Configuration" << std::endl
              << "=============" << std::endl;
    Configure( camera );
    Acquire( camera );
    std::cout << std::endl;

    std::cout << "Temperature" << std::endl
              << "===========" << std::endl;
    ReadTemperature( camera, lock );
    std::cout << std::endl;

    std::cout << "Online Exposure" << std::endl
              << "===============" << std::endl;
    AcquireAndExpose( camera );
    std::cout << std::endl;

    Picam_CloseCamera( camera );

    Picam_UninitializeLibrary();
}
