//Gating Sample
//Part 1 of the sample will open the first camera attached
//and if it is capable of gating, acquire 1 frame in repetitive gating mode.
//Part 2 of the sample will set gating mode to sequential and
//collect 4 frames.  The delay and width will grow by 25nS each frame.

#define NUM_FRAMES         1
#define SEQ_FRAMES         4
#define NO_TIMEOUT        -1
#define TRIG_FREQ        1.0//Hz
#define GATE_DELAY      25.0//nS -- Starting Gate Delay when in Sequential Gating mode
#define GATE_WIDTH      25.0//nS -- Starting Gate Width when in Sequential Gating mode
#define AUX_DELAY       50.0//nS
#define AUX_WIDTH       25.0//nS
#define SM2_DELAY        0.1//uS -- Syncmaster2 Delay
#define END_GATE_DELAY  100.0//nS -- Ending Gate Delay used with Sequential Gating
#define END_GATE_WIDTH  100.0//nS -- Ending Gate Width used with Sequential Gating
#define GAIN               20//   -- Intensifier Gain

#include "stdio.h"
#include "string.h"
#include "picam.h"

///////////////////////////////////////////////////////////////////////////////
// So some of the data points
///////////////////////////////////////////////////////////////////////////////
void PrintData( pibyte* buf, piint numframes, piint framelength )
{
    pi16u  *midpt = NULL;
    pibyte *frameptr = NULL;

    for( piint loop = 0; loop < numframes; loop++ )
    {
        frameptr = buf + ( framelength * loop );
        midpt = (pi16u*)frameptr + ( ( ( framelength/sizeof(pi16u) )/ 2 ) );
        printf( "%5d,%5d,%5d\t%d\n",(int) *(midpt-1),(int) *(midpt),(int) *(midpt+1),(int) loop+1 );
    }
}
///////////////////////////////////////////////////////////////////////////////
//
// Commit the current parameters and acquire in a loop for the specified number
// of frames for each acquisition.
//
///////////////////////////////////////////////////////////////////////////////
void CommitAndAcquire(PicamHandle camera,     // Camera Handle                      
                      piint acquisitions,     // Loop Picam_Acquire
                      piint framesPerAcquire, // How many frames are in each acquire                      
                      const pichar *message)   // Message 
{
    pibln committed;
    PicamAvailableData data;
    PicamAcquisitionErrorsMask errMask;
   
    //commit the changes
    Picam_AreParametersCommitted( camera, &committed );
    if( !committed )
    {
        const PicamParameter* failed_parameter_array = NULL;
        piint failed_parameter_count = 0;
        Picam_CommitParameters( camera, &failed_parameter_array, &failed_parameter_count );
        if( failed_parameter_count )
            Picam_DestroyParameters( failed_parameter_array );
        else
        {
            int readoutStride;
            Picam_GetParameterIntegerValue( camera, PicamParameter_ReadoutStride, &readoutStride );

            printf( "\n%s Collecting %d frame(s), looping %d times\n", message,(int) framesPerAcquire, (int)acquisitions );
            for( piint i = 0; i < acquisitions; i++ )
            {
                if( Picam_Acquire( camera, framesPerAcquire, NO_TIMEOUT, &data, &errMask ) )
                    printf( "Error: Camera only collected %d frames\n", (int)data.readout_count );
                else
                {    
                    PrintData( (pibyte*)data.initial_readout, framesPerAcquire, readoutStride );
                }
            }
        }
    }
}
///////////////////////////////////////////////////////////////////////////////
//
///////////////////////////////////////////////////////////////////////////////
void SetupCommonParameters( PicamHandle camera )
{
    Picam_SetParameterFloatingPointValue( camera, PicamParameter_TriggerFrequency, TRIG_FREQ );//internal trigger frequency
    Picam_SetParameterIntegerValue( camera, PicamParameter_IntensifierGain, GAIN );//intensifier gain
    Picam_SetParameterIntegerValue( camera, PicamParameter_TriggerSource, PicamTriggerSource_Internal );//use internal trigger
    Picam_SetParameterFloatingPointValue( camera, PicamParameter_SyncMaster2Delay, SM2_DELAY );//syncmaster2 delay time(uS)
    Picam_SetParameterIntegerValue( camera, PicamParameter_EnableSyncMaster, true );//turn on syncmaster
    Picam_SetParameterIntegerValue( camera, PicamParameter_EnableIntensifier, true );//turn on intensifier
}
///////////////////////////////////////////////////////////////////////////////
//
///////////////////////////////////////////////////////////////////////////////
void DoRepetitive( PicamHandle camera )
{
    PicamPulse genericPulser;

    Picam_SetParameterIntegerValue( camera, PicamParameter_GatingMode, PicamGatingMode_Repetitive );//set repetitve gating
    genericPulser.delay = GATE_DELAY;
    genericPulser.width = GATE_WIDTH;
    Picam_SetParameterPulseValue( camera, PicamParameter_RepetitiveGate, &genericPulser );//set GATE width&delay
    genericPulser.delay = AUX_DELAY;
    genericPulser.width = AUX_WIDTH;
    Picam_SetParameterPulseValue( camera, PicamParameter_AuxOutput, &genericPulser );//set AUX width&delay    

    // commit the changes and acquire the data
    CommitAndAcquire(camera, NUM_FRAMES, 1, "Repetitive Gating:");
}
///////////////////////////////////////////////////////////////////////////////
//
///////////////////////////////////////////////////////////////////////////////
void DoSequential( PicamHandle camera )
{
    PicamPulse genericPulser;

    Picam_SetParameterIntegerValue( camera, PicamParameter_GatingMode, PicamGatingMode_Sequential );//set sequential gating
    genericPulser.delay = 25000.0;
    genericPulser.width = 25000.0;
    Picam_SetParameterPulseValue( camera, PicamParameter_SequentialStartingGate, &genericPulser );//set Starting Gate width&delay
    genericPulser.delay = 100000.0;
    genericPulser.width = 100000.0;
    Picam_SetParameterPulseValue( camera, PicamParameter_SequentialEndingGate, &genericPulser );//set Ending Gate width&delay
    Picam_SetParameterLargeIntegerValue( camera, PicamParameter_SequentialGateStepCount, SEQ_FRAMES );//# of frames in sequence
    Picam_SetParameterLargeIntegerValue( camera, PicamParameter_SequentialGateStepIterations, 1 );

    //commit the changes and acquire the data
    CommitAndAcquire(camera, NUM_FRAMES, SEQ_FRAMES, "Sequential Gating:");
}
///////////////////////////////////////////////////////////////////////////////
//
//  Setup the camera for repetitive mode RF modulation
// all frames acquired will be the same.
//
///////////////////////////////////////////////////////////////////////////////
void DoRepetitiveRF( PicamHandle camera )
{    
    // Set Repetitive Gating Mode
    Picam_SetParameterIntegerValue( camera, PicamParameter_GatingMode, PicamGatingMode_Repetitive );

    // Set the RF Phase (90 degrees)
    Picam_SetParameterFloatingPointValue( camera, PicamParameter_RepetitiveModulationPhase, 90.0 );

    // Set the RF Modulation Duration (1 ms)
    Picam_SetParameterFloatingPointValue( camera, PicamParameter_ModulationDuration, 1.0 );

    // Set the RF Modulation Frequency (100 MHz)
    Picam_SetParameterFloatingPointValue( camera, PicamParameter_ModulationFrequency, 100.0 );     

    //commit the changes and acquire the data
    CommitAndAcquire(camera, NUM_FRAMES, 1, "Repetitive RF Modulation:");
}
///////////////////////////////////////////////////////////////////////////////
//
// Setup the camera for sequential mode RF modulation 
// Sweep from 90 to 270 degree phase, depending on the number of frames each
// image in the sequence will be shifted (270-90)/(n-1)
//
///////////////////////////////////////////////////////////////////////////////
void DoSequentialRF( PicamHandle camera )
{    
    // Set Sequential Gating Mode
    Picam_SetParameterIntegerValue( camera, PicamParameter_GatingMode, PicamGatingMode_Sequential );

    // Set the RF Starting Phase (90 degrees)
    Picam_SetParameterFloatingPointValue( camera, PicamParameter_SequentialStartingModulationPhase, 90.0 );

    // Set the RF Ending Phase (270 degrees)
    Picam_SetParameterFloatingPointValue( camera, PicamParameter_SequentialEndingModulationPhase, 270.0 );

    // Set the RF Modulation Duration (1 ms)
    Picam_SetParameterFloatingPointValue( camera, PicamParameter_ModulationDuration, 1.0 );

    // Set the RF Modulation Frequency (100 MHz)
    Picam_SetParameterFloatingPointValue( camera, PicamParameter_ModulationFrequency, 100.0 );      

    // Setup for 1 iteration of sequence of 4
    Picam_SetParameterLargeIntegerValue( camera, PicamParameter_SequentialGateStepCount, SEQ_FRAMES );//# of frames in sequence
    Picam_SetParameterLargeIntegerValue( camera, PicamParameter_SequentialGateStepIterations, 1 );

    //commit the changes and acquire the data
    CommitAndAcquire(camera, NUM_FRAMES, SEQ_FRAMES, "Sequential RF Modulation:");
}
///////////////////////////////////////////////////////////////////////////////
//
//  Setup the camera for sequential mode RF modulation
//
///////////////////////////////////////////////////////////////////////////////
void DoCustomSequenceRF( PicamHandle camera )
{      
    // Define some phase shifts for our custom sequence
    piflt phases[SEQ_FRAMES] = { 0, 180, 90, 270 };

    // Define some structures we need to fill in
    PicamModulations modulations;
    PicamModulation customModulations[SEQ_FRAMES];

    // fill in each index of the PicamModulation structure array
    for (piint i=0; i < SEQ_FRAMES; i++)
    {
        customModulations[i].duration                = 1.0;       // milliseconds
        customModulations[i].frequency               = 50.0;      // megahertz
        customModulations[i].output_signal_frequency = 50.0;      // megahertz
        customModulations[i].phase                   = phases[i]; // degrees
    }

    // Setup the container(PicamModulations) of the steps and array
    modulations.modulation_array = customModulations;
    modulations.modulation_count = SEQ_FRAMES;

    // Set Custom Gating Mode
    Picam_SetParameterIntegerValue( camera, PicamParameter_GatingMode, PicamGatingMode_Custom );

    // Set the custom mode array
    Picam_SetParameterModulationsValue( camera, PicamParameter_CustomModulationSequence, &modulations );

    //commit the changes and acquire the data
    CommitAndAcquire(camera, NUM_FRAMES, SEQ_FRAMES, "Custom RF Modulation:");
}
///////////////////////////////////////////////////////////////////////////////
// Enable the RF output signal and set the values for it
///////////////////////////////////////////////////////////////////////////////
void SetupRFOutput(PicamHandle camera, pibln enable, piflt frequency, piflt amplitude)
{
    //////////////////////////////RF OUTPUT SIGNAL////////////////////////////////////////////////
    // Output Enable
    Picam_SetParameterIntegerValue( camera, PicamParameter_EnableModulationOutputSignal, enable);

    // Set the RF Output Frequency (megahertz)
    Picam_SetParameterFloatingPointValue( camera, PicamParameter_ModulationOutputSignalFrequency, frequency );

    // Set the RF Output Amplitude (volts)
    Picam_SetParameterFloatingPointValue( camera, PicamParameter_ModulationOutputSignalAmplitude, amplitude );   
}
///////////////////////////////////////////////////////////////////////////////
// main
///////////////////////////////////////////////////////////////////////////////
int main()
{
    Picam_InitializeLibrary();

    // - open the first camera if any
    PicamHandle camera;
    PicamCameraID id;
    const pichar* string;
    pibln IsGatingAvailable = false;
    pibln IsRFModulationAvailable = false;

    if( Picam_OpenFirstCamera( &camera ) == PicamError_None )
        Picam_GetCameraID( camera, &id );
    else
    {
        printf( "No Camera Detected.  Exiting Program\n" );
        return 0;
    }
    Picam_GetEnumerationString( PicamEnumeratedType_Model, id.model, &string );
    printf( "%s", string );
    printf( " (SN:%s) [%s]\n", id.serial_number, id.sensor_name );
    Picam_DoesParameterExist( camera, PicamParameter_GatingMode, &IsGatingAvailable );
    if( !IsGatingAvailable )
    {
        Picam_DestroyString( string );
        Picam_CloseCamera( camera );
        Picam_UninitializeLibrary();
        printf( "Gating not supported by this camera\n" );
        return 0;
    }
    Picam_DestroyString( string );
      
    // Setup common camera parameters to all sample mode
    SetupCommonParameters( camera );

    // Repetitive Gating
    DoRepetitive( camera );

    // Sequential Gating
    DoSequential( camera );
        
    // Do more if it is an RF capable system
    Picam_DoesParameterExist(camera, PicamParameter_EnableModulation, &IsRFModulationAvailable);
    if (IsRFModulationAvailable)
    {        
        // Enable RF Modulation
        Picam_SetParameterIntegerValue( camera, PicamParameter_EnableModulation, true);

        // Enable RF output signal for all modes
        SetupRFOutput(camera, true, 50.0, 1.4);    

        // Do Repetitive Modulation
        DoRepetitiveRF( camera );
        
        // Do Sequential Modulation
        DoSequentialRF( camera );        

        // Do Custom Sequence Modulation
        DoCustomSequenceRF( camera );        
    }
        
    // Close the camera
    Picam_CloseCamera( camera );

    // Uninitialize the library
    Picam_UninitializeLibrary();
}
