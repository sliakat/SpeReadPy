//Polling Acquisition Sample
//The sample will open the first camera attached
//and acquire 5 frames using a polling scheme.

#define NUM_FRAMES  5
#define TIMEOUT		-1//infinite

#include "stdio.h"
#include "picam.h"

void PrintData( pibyte* buf, pi64s numframes, piint framelength )
{
    pi16u  *midpt = NULL;
    pibyte *frameptr = NULL;

    for( piint loop = 0; loop < numframes; loop++ )
    {
        frameptr = buf + ( framelength * loop );
        midpt = (pi16u*)frameptr + ( ( ( framelength/sizeof(pi16u) )/ 2 ) );
        printf( "%5d,%5d,%5d\n", (int) *(midpt-1),(int) *(midpt), (int) *(midpt+1) );
    }
}

int main()
{
    Picam_InitializeLibrary();

    // - open the first camera if any or create a demo camera
	pibln bRunning;
	pibln committed;
    PicamHandle camera;
    PicamCameraID id;
    const pichar* string;
    PicamAvailableData data;
    PicamAcquisitionStatus status;
    piint readoutstride = 0;
	PicamError err;
	pi64s framecount = 0;

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
    Picam_SetParameterLargeIntegerValue( camera, PicamParameter_ReadoutCount, NUM_FRAMES );

	Picam_AreParametersCommitted( camera, &committed );
	if( !committed )
	{
		const PicamParameter* failed_parameter_array = NULL;
		piint           failed_parameter_count = 0;
		Picam_CommitParameters( camera, &failed_parameter_array, &failed_parameter_count );
		if( failed_parameter_count )
		{
			Picam_DestroyParameters( failed_parameter_array );
		}
	}
    printf( "Collecting %d frames\n\n",(int) NUM_FRAMES );
	printf( "Center Three Points:\n");
	err = Picam_StartAcquisition( camera );
	bRunning = ( err == PicamError_None );
	while( bRunning )
	{
		err = Picam_WaitForAcquisitionUpdate( camera, TIMEOUT, &data, &status );
		if( err == PicamError_None )
		{
			bRunning = status.running;
			framecount += data.readout_count;
			PrintData( (pibyte*)data.initial_readout, data.readout_count, readoutstride );
		}
		else if( err == PicamError_TimeOutOccurred )
		{
			printf( "Terminating prematurely!  Try increasing time out\n" );
			Picam_StopAcquisition( camera );
		}
	}
    Picam_CloseCamera( camera );
    Picam_UninitializeLibrary();
}
