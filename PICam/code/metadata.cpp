//Acquisition with Metadata Sample
//The sample will open the first camera attached
//and acquire 5 frames.  Timestamps and Frame Tracking will be 
//included in the metadata.
//Metadata Format
//<PIXEL DATA>TS_ExposureStart|TS_ExposureEnd|Frame_Tracking_Number

#define NUM_FRAMES  5
#define NO_TIMEOUT  -1

#include "stdio.h"
#include "picam.h"

int main()
{
    Picam_InitializeLibrary();

    // - open the first camera if any or create a demo camera
    PicamHandle camera;
	pibln bUseFrameTrack;
	pibln committed;
    PicamCameraID id;
    const pichar* string;
    PicamAvailableData data;
    PicamAcquisitionErrorsMask errors;
    piint readoutstride = 0;
	piint framesize = 0;
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

	//enable metadata
	piint ts_mask = PicamTimeStampsMask_ExposureStarted | PicamTimeStampsMask_ExposureEnded;
	bUseFrameTrack = true;

	Picam_SetParameterIntegerValue( camera, PicamParameter_TimeStamps,  ts_mask );
	Picam_SetParameterIntegerValue( camera, PicamParameter_TrackFrames, bUseFrameTrack );
    Picam_SetParameterFloatingPointValue( camera, PicamParameter_ExposureTime, 1000 );//1second exposure

	//commit settings
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
			pi64s tsRes;
			piint tsBitDepth;//bit depth for Time Stamp(s)
			piint frameBitDepth;//bit depth for Frame Tracking

			Picam_GetParameterIntegerValue( camera, PicamParameter_ReadoutStride, &readoutstride );
			Picam_GetParameterIntegerValue( camera, PicamParameter_FrameSize, &framesize );
			Picam_GetParameterLargeIntegerValue( camera, PicamParameter_TimeStampResolution, &tsRes );
			Picam_GetParameterIntegerValue( camera, PicamParameter_TimeStampBitDepth, &tsBitDepth );
			Picam_GetParameterIntegerValue( camera, PicamParameter_FrameTrackingBitDepth, &frameBitDepth );
			printf( "Waiting for %d frames to be collected\n\n", (int)NUM_FRAMES );
			if( !Picam_Acquire( camera, NUM_FRAMES, NO_TIMEOUT, &data, &errors ) )
			{
				pibyte *frame = NULL;
				pi64s metadataOffset;
				printf( "%-24s%-*.*s%-*.*s%-*.*s\n", 
					"Center Three Points:",
					(ts_mask & PicamTimeStampsMask_ExposureStarted)?15:0,
					(ts_mask & PicamTimeStampsMask_ExposureStarted)?15:0,
					(ts_mask & PicamTimeStampsMask_ExposureStarted)?"TS_EXP_Start":"",
					(ts_mask & PicamTimeStampsMask_ExposureEnded)?15:0,
					(ts_mask & PicamTimeStampsMask_ExposureEnded)?15:0,
					(ts_mask & PicamTimeStampsMask_ExposureEnded)?"TS_EXP_END":"",
					(bUseFrameTrack)?15:0,
					(bUseFrameTrack)?15:0,
					(bUseFrameTrack)?"Frame #":"" );
				for( piint loop = 0; loop < NUM_FRAMES; loop++ )
				{
					frame = ((pibyte*) data.initial_readout + ( readoutstride * loop ) );
					metadataOffset = (pi64s)frame + framesize;
					pi16u *midpt = (pi16u*)frame + ( ( ( framesize/sizeof(pi16u) )/ 2 ) );
					printf( "%-7d,%-8d,%-7d",(int) *(midpt-1),(int) *(midpt),(int) *(midpt+1) );
					if( ts_mask )
					{
						switch( tsBitDepth )
						{
							case 64:
							{
								pi64s *tmpPtr = NULL;
								if( ts_mask & PicamTimeStampsMask_ExposureStarted )
								{
									tmpPtr = (pi64s*)metadataOffset;
									printf( "%-15.8f", (double)*tmpPtr/(double)tsRes);
									metadataOffset += ( tsBitDepth/(sizeof(pichar)*8) );
								}
								if( ts_mask & PicamTimeStampsMask_ExposureEnded )
								{
									tmpPtr = (pi64s*)metadataOffset;
									printf( "%-15.8f", (double)*tmpPtr/(double)tsRes);
									metadataOffset += ( tsBitDepth/(sizeof(pichar)*8) );
								}
								break;
							}
						}
					}
					if( bUseFrameTrack )
					{
						switch( frameBitDepth )
						{
							case 64:
							{
								pi64s *tmpPtr = (pi64s*)metadataOffset;
								printf( "%d\t", (int) *tmpPtr );
								break;
							}
						}
					}
					printf( "\n" );
				}
			}
		}
	}
    Picam_CloseCamera( camera );
    Picam_UninitializeLibrary();
}
