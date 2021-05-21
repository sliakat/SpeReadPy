//Multiple Camera Polling Acquisition Sample
//The sample will open the first camera attached
//and acquire 5 frames using a polling scheme.

#define NUM_FRAMES  5
#define NOTIMEOUT	-1 //infinite
#define MIN_CAMERAS 2

#include "stdio.h"
#include "stdlib.h"
#include "string.h"

#include "picam.h"

void PrintData( pibyte* buf, pi64s numframes, piint framelength, piint camnum )
{
    pi16u  *midpt = NULL;
    pibyte *frameptr = NULL;

    for( piint loop = 0; loop < numframes; loop++ )
    {
        frameptr = buf + ( framelength * loop );
        midpt = (pi16u*)frameptr + ( ( ( framelength/sizeof(pi16u) )/ 2 ) );
		printf( "Camera #%d %5d,%5d,%5d\n", (int)camnum,(int) *(midpt-1),(int) *(midpt),(int) *(midpt+1) );
    }
}

int main()
{
	pibln bLoop = true;
	pibln *bRunning = NULL;
    PicamAvailableData *data = NULL;
    PicamAcquisitionStatus *status = NULL;
    piint *readoutstride = NULL;
	pi64s *framecount = 0;
    const PicamCameraID *camID;
    PicamCameraID *demoID = NULL;
    piint numCamsAvailable = 0;
	piint numDemos = 0;
	PicamHandle *hCam = NULL;
	PicamError err = PicamError_None;
	//Only 3 cameras in demolist... more can be added.  Also add more sn's too
	piint demoList[] = { PicamModel_Quadro4096,PicamModel_Pixis1300F, PicamModel_ProEM512B  };
	const pichar *sn[] = { "1000000001", "1000000002", "1000000003" };

    // set millisecs timeout value 
    piint msecTimeout = 15000;   // NOTIMEOUT = no timeout

    Picam_InitializeLibrary();

	Picam_GetAvailableCameraIDs( &camID, &numCamsAvailable );
	Picam_DestroyCameraIDs( camID );

	if( numCamsAvailable < MIN_CAMERAS )
	{
		numDemos = MIN_CAMERAS - numCamsAvailable;
		demoID = (PicamCameraID*) malloc( sizeof( PicamCameraID ) * numDemos );
	}
	piint count = 0;
	while( numCamsAvailable < MIN_CAMERAS )
	{
        //need a minimum of MIN_CAMERAS(2) for multi-camera example
		Picam_ConnectDemoCamera( (PicamModel)demoList[count], sn[count], &demoID[count] );
		++numCamsAvailable;
		++count;
	}

	Picam_GetAvailableCameraIDs( &camID, &numCamsAvailable );
	hCam = (PicamHandle *) malloc( sizeof( PicamHandle ) * numCamsAvailable );
	readoutstride = ( piint * ) malloc( sizeof( piint ) * numCamsAvailable );
	data = (PicamAvailableData *) malloc( sizeof( PicamAvailableData ) * numCamsAvailable );
	status = (PicamAcquisitionStatus *) malloc( sizeof( PicamAcquisitionStatus ) * numCamsAvailable );
	bRunning = (pibln *) malloc( sizeof( pibln ) * numCamsAvailable );
    memset( bRunning, 0, sizeof( pibln ) * numCamsAvailable );
	framecount = (pi64s *) malloc( sizeof( pi64s ) * numCamsAvailable );
	memset( framecount, 0, sizeof( pi64s ) * numCamsAvailable );


	for( piint i = 0; i < numCamsAvailable; i++ )
	{
		if( Picam_OpenCamera( &camID[i], &hCam[i] ) )
		{
			printf( "Picam_OpenCamera() Failed.  Exiting\n" );
			Picam_UninitializeLibrary();
			if( demoID )
				free( demoID );
			free( hCam );
			free( readoutstride );
			free( data );
			free( status );
			free( bRunning );
			free( framecount );
			return 0;
		}
		else
		{
			const pichar* string = NULL;
			pibln committed = 0;
			Picam_GetEnumerationString( PicamEnumeratedType_Model, camID[i].model, &string );
            printf( "%2d: %s",(int) i+1, string );
			printf( " (SN:%s [%s])\n", camID[i].serial_number, camID[i].sensor_name );
			Picam_DestroyString( string );
			Picam_GetParameterIntegerValue( hCam[i], PicamParameter_ReadoutStride, &readoutstride[i] );
			Picam_SetParameterLargeIntegerValue( hCam[i], PicamParameter_ReadoutCount, NUM_FRAMES );

			Picam_AreParametersCommitted( hCam[i], &committed );
			if( !committed )
			{
				const PicamParameter* failed_parameter_array = NULL;
				piint failed_parameter_count = 0;
				Picam_CommitParameters( hCam[i], &failed_parameter_array, &failed_parameter_count );
				if( failed_parameter_count )
				{
					bLoop = false;//don't continue with acquisition
					Picam_DestroyParameters( failed_parameter_array );
				}
			}
		}
    }

    printf( "Collecting %d frames\n\n",(int) NUM_FRAMES );
	printf( "Center Three Points:\t\n");
	for( piint k = 0; k < numCamsAvailable; k++ )
    {
		Picam_StartAcquisition( hCam[k] );
        bRunning[k] = true;
    }
	while( bLoop )
	{
		for( piint i = 0; i < numCamsAvailable; i++ )
		{
			if( bRunning[i] )
			{
                // infinite timeout setting for acquire
                if (framecount[i] < NUM_FRAMES)
                    printf("\n    .. waiting for camera %d Frame #%d .. \n", (int)i + 1, (int)(framecount[i]+1));
                else
                    printf("\n    .. waiting for camera %d Stop notification .. \n",(int) i + 1);
				err = Picam_WaitForAcquisitionUpdate( hCam[i], msecTimeout, &data[i], &status[i] );

				if(  err == PicamError_None )
				{//got data
				    bRunning[i] = status[i].running;
                    if (!bRunning[i])
		                printf( "Camera #%d Has Stopped.\n",(int)i + 1 );

					framecount[i] += data[i].readout_count;
					PrintData( (pibyte*)data[i].initial_readout, data[i].readout_count, readoutstride[i], (i+1) );
				}
			}
			else
			{
				pibln bQuit = false;
				for( piint z = 0; z < numCamsAvailable; z++ )
				{
					if( bRunning[z] )
					{
						bQuit = false;
						break;
					}
					else
						bQuit = true;
				}
				if( bQuit )
					bLoop = false;
			}
		}
	}
    for( piint i = 0; i < numCamsAvailable; i++ )
	{
		Picam_CloseCamera( hCam[i] );
	}
	Picam_DestroyCameraIDs( camID );
	if( demoID )
		free( demoID );
	free( hCam );
	free( readoutstride );
	free( data );
	free( status );
	free( bRunning );
	free( framecount );

    Picam_UninitializeLibrary();
}
