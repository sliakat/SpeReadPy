//Basic Acquisition Sample
//The sample will open the first camera attached
//and acquire 5 frames.  Part 2 of the sample will collect
//1 frame of data each time the function is called, looping
//through 5 times.

#define NUM_FRAMES  5
#define NO_TIMEOUT  -1

#include "stdio.h"
#include "picam.h"

void PrintData( pibyte* buf, piint numframes, piint framelength )
{
    pi16u  *midpt = NULL;
    pibyte *frameptr = NULL;

    for( piint loop = 0; loop < numframes; loop++ )
    {
        frameptr = buf + ( framelength * loop );
        midpt = (pi16u*)frameptr + ( ( ( framelength/sizeof(pi16u) )/ 2 ) );
        printf( "%5d,%5d,%5d\t%d\n", (int) *(midpt-1), (int) *(midpt),  (int) *(midpt+1), (int) loop+1 );
    }
}
int main()
{
    Picam_InitializeLibrary();

    // - open the first camera if any or create a demo camera
    PicamHandle camera;
    PicamCameraID id;
    const pichar* string;
    PicamAvailableData data;
    PicamAcquisitionErrorsMask errors;
    piint readoutstride = 0;
    if( Picam_OpenFirstCamera( &camera ) == PicamError_None )
        Picam_GetCameraID( camera, &id );
    else
    {
        Picam_ConnectDemoCamera(
            PicamModel_Pixis100F,
            "0008675309",
            &id );
        Picam_OpenCamera( &id, &camera );
        printf( "No Camera Detected, Creating Demo Camera\n" );
    }
    Picam_GetEnumerationString( PicamEnumeratedType_Model, id.model, &string );
    printf( "%s", string );
    printf( " (SN:%s) [%s]\n", id.serial_number, id.sensor_name );
    Picam_DestroyString( string );

    Picam_GetParameterIntegerValue( camera, PicamParameter_ReadoutStride, &readoutstride );
    printf( "Waiting for %d frames to be collected\n\n", (int) NUM_FRAMES );
    if( Picam_Acquire( camera, NUM_FRAMES, NO_TIMEOUT, &data, &errors ) )
        printf( "Error: Camera only collected %d frames\n", (int) data.readout_count );
    else
    {    
        printf( "Center Three Points:\tFrame # \n");
        PrintData( (pibyte*)data.initial_readout, NUM_FRAMES, readoutstride );
    }

    //collect NUM_FRAMES one at a time
    printf( "\n\n" );
    printf( "Collecting 1 frame, looping %d times\n\n", (int) NUM_FRAMES );
    for( piint i = 0; i < NUM_FRAMES; i++ )
    {
        if( Picam_Acquire( camera, 1, NO_TIMEOUT, &data, &errors ) )
            printf( "Error: Camera only collected %d frames\n", (int)data.readout_count );
        else
        {
            PrintData( (pibyte*)data.initial_readout, 1, readoutstride );
        }
    }
    Picam_CloseCamera( camera );
    Picam_UninitializeLibrary();
}
