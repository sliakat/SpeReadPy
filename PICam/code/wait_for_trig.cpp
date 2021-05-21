//External Trigger Acquisition Sample
//The sample will open the first camera attached
//and acquire a single frame after being triggered

#define TIMEOUT		-1 //infinite

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
        printf( "%5d,%5d,%5d\t%d\n",(int) *(midpt-1),(int) *(midpt),(int) *(midpt+1),(int) loop+1 );
    }
}

int main()
{
    Picam_InitializeLibrary();

    // - open the first camera if any
    PicamHandle camera;
	pibln committed;
    PicamCameraID id;
    const pichar* string;
    PicamAvailableData data;
	PicamAcquisitionErrorsMask errMask;
    piint readoutstride = 0;

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
    Picam_DestroyString( string );

    Picam_GetParameterIntegerValue( camera, PicamParameter_ReadoutStride, &readoutstride );

	Picam_SetParameterIntegerValue( camera, PicamParameter_TriggerResponse, PicamTriggerResponse_ReadoutPerTrigger );
	Picam_SetParameterIntegerValue( camera, PicamParameter_TriggerDetermination, PicamTriggerDetermination_NegativePolarity );
	//commit the changes
	Picam_AreParametersCommitted( camera, &committed );
	if( !committed )
	{
		const PicamParameter* failed_parameter_array = NULL;
		piint           failed_parameter_count = 0;
		Picam_CommitParameters( camera, &failed_parameter_array, &failed_parameter_count );
		if( failed_parameter_count )
			Picam_DestroyParameters( failed_parameter_array );
		else
		{
			printf( "Waiting for external trigger\n" );
			if (!Picam_Acquire( camera, 1, TIMEOUT, &data, &errMask ))
            {
			    printf( "Received external trigger\n\n" );
			    printf( "Center Three Points:\tFrame # \n");
			    PrintData( (pibyte*)data.initial_readout, 1, readoutstride );
            }
		}
	}
	Picam_CloseCamera( camera );
    Picam_UninitializeLibrary();
}
