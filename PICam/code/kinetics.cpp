//---------------------------------------------------------------------------
//	Kinetics.cpp  Sample Code to demonstrate Kinetics Capture using PI API
//   This source defaults to produce a set of free-running kinetics acquisitions
//   See notes below to produce code for manually triggered acquisition
//---------------------------------------------------------------------------

#include "picam.h" // Teledyne Princeton Instruments API Header 
#include "stdio.h"

// Name, location of Raw Data output file
const char* TargetFileName="fileoutput.dat";


//!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
// to have source produce code for manually triggered acquisition,
//   #define one of these:  (BUT NOT BOTH)

// manually trigger each kinetics window frame acquisition
//#define DO_KINETICS_WITH_SHIFT_PER_TRIGGER

// manually trigger each kinetics window frame expose 
//#define DO_KINETICS_WITH_EXPOSE_DURING_TRIGGER_PULSE

// manually trigger each Readout acquisition
//#define DO_KINETICS_WITH_READOUT_PER_TRIGGER
//!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

// Kinetics Example Code 
void DoKineticsCapture(PicamHandle camera);

// Show error code helper routine 
void DisplayError(PicamError errCode);

// sample function to show how to write captured pixel data to binary file  
//     returns true for success,  false if failed
// DOES NOT HANDLE MetaData
pibool myWriteDataToFile(void *buffer, piint pixelBitDepth, pi64s numreadouts,
                 piint pixelsWide, piint pixelsHigh, const char* TargetFileName);

//---------------------------------------------------------------------------
//	Teledyne Princeton Instruments Kinetics Capture example.
//
//	Main is a generic stub, calling specially written functions
//
//---------------------------------------------------------------------------
int main()
{
    PicamError  errCode = PicamError_None;	// Error Code		
    PicamHandle camera  = NULL;				// Camera Handle	

    // ensure that only ONE Trigger condition was #defined:
    piint DefineTest = 0;
    #ifdef DO_KINETICS_WITH_SHIFT_PER_TRIGGER
    DefineTest++;
    #endif
    #ifdef DO_KINETICS_WITH_EXPOSE_DURING_TRIGGER_PULSE
    DefineTest++;
    #endif
    #ifdef  DO_KINETICS_WITH_READOUT_PER_TRIGGER
    DefineTest++;
    #endif
    if (DefineTest>1)
    {
        printf("\n\n ! ! ERROR-  %d TRIGGER conditions #defined, can have only one ! ! \n",(int)DefineTest);
        return 1;
    }


    // Initialize the library 
    errCode = Picam_InitializeLibrary();

    // Check error code 
    if (errCode == PicamError_None)
    {
        // Open the first camera 
        errCode = Picam_OpenFirstCamera( &camera );

        // If the camera open succeeded 
        if (errCode == PicamError_None)
        {
            // Setup and acquire for a Kinetics Capture 
            DoKineticsCapture(camera);


            // We are done with the camera so close it 
            Picam_CloseCamera(camera);
        }
        // Show error string if a problem occurred 
        else 
            DisplayError(errCode);		
    }
    // Show error string if a problem occurred 
    else 
        DisplayError(errCode);

    // Uninitialize the library 
    Picam_UninitializeLibrary();

    printf("\n\n ! ! ! Finished- Press Any Key To Exit ! ! ! !\n");
    //!!	_getch();
    return 0;
}

//---------------------------------------------------------------------------
//	DisplayError helper routine, prints out the message for the associated 
//	error code.
//
//---------------------------------------------------------------------------
void DisplayError(PicamError errCode)
{
    // Get the error string, the called function allocates the memory 
    const pichar *errString;
    Picam_GetEnumerationString(	PicamEnumeratedType_Error, 
        (piint)errCode, 
        &errString);
    // Print the error 
    printf("%s\n", errString);

    // Since the called function allocated the memory it must free it 
    Picam_DestroyString(errString);
}

//---------------------------------------------------------------------------
// myWriteDataToFile( )   returns true for success,  false if failed
// sample function to show how to write captured pixel data to binary file  
//	WARNING:  This is JUST a sample how to handle image data after capture
//    This will NOT Work as written if metadata is present
//---------------------------------------------------------------------------
pibool myWriteDataToFile(void *buffer, piint pixelBitDepth, pi64s numreadouts,
                 piint pixelsWide, piint pixelsHigh, const char* TargetFileName)
{	
    pibool returnOK = false;
    piint imagePixels = pixelsWide * pixelsHigh;
    piint bytesInReadout = 0;

    // simple dump of raw data into binary file
    FILE* fs = fopen(TargetFileName, "wb");
    if (!fs)
    {
        printf("\n ! ! Could not open datafile %s for output\n", TargetFileName);
        return returnOK;
    }

    // Conversion of numpixels in readout to numbytes
    // currently we recognize only 16 bit image pixel size
    switch (pixelBitDepth)
    {
    case 16:
        bytesInReadout = 2 * imagePixels;
        break;
    default:
        bytesInReadout = 0;
        break;
    }

    // write out numreadouts  *  readoutSize worth of data to file
    // each readout data blob is contiguously stored
    // ! ! THIS LOGIC WILL NOT CORRECTLY OUTPUT READOUT WITH METADATA ! ! ! 
    if (fwrite(buffer, bytesInReadout, (size_t)numreadouts, fs) == (size_t)numreadouts)
        returnOK = true;  
    fclose(fs);

    if (returnOK)
        printf("\n ! ! Successfully wrote %d bytes to %s \n", 
                     (int)(bytesInReadout * numreadouts), TargetFileName);
    else
        printf("\n ! ! Could not write data to %s \n", TargetFileName);

    return returnOK;
}
//---------------------------------------------------------------------------
//	Teledyne Princeton Instruments Kinetics example.
//
//	Sets up the camera and acquires a kinetics image set.
//
//---------------------------------------------------------------------------
void DoKineticsCapture(PicamHandle camera)
{
    PicamError					err;			 // Error Code			
    PicamAvailableData			acquisitionData;		 // Data Struct			 
    PicamAcquisitionErrorsMask	acqErrors;		 // Errors				
    const PicamParameter		*paramsFailed;	 // Failed to commit    
    piint						failCount;		 // Count of failed	    
    const PicamRoisConstraint   *ptrConstraint;	 // Constraints			

	PicamRois				    roiSetup;		 // region of interest  setup
	PicamRoi					theKineticsROI;

    piint framesPerReadout = 0;

    // Variables to compute data blob sizes 
    piint readoutHeight    = 0;      // Height of Readout (in pixels)
    piint readoutWidth     = 0;      // Width  of Readout (in pixels)
    piint singleFrameHeight= 0;      // Height of single Kinetics frame (in pixels)


    // Inputs into this experiment:
    //    Acquire 3 readout of data with a 10000 ms timeout 
    //    Using kinetics mode, with window height of 128 pixels

    PicamReadoutControlMode ReadoutMode = PicamReadoutControlMode_Kinetics;
    piint acquireTimoutMillisecs = 10000;	// Ten second timeout for normal kinetics
                                            // is disabled by logic if trigger mode

    piint kineticsWindowHeight = 10;
    piint exposureTimeMillisecs = 20;  
    pi64s numReadoutsRequested = 3;


    PicamTriggerResponse TriggerResponse = PicamTriggerResponse_NoResponse;
    pibool usingTrigger = false;
    PicamTriggerDetermination TriggerDetermination = PicamTriggerDetermination_PositivePolarity;

    printf("..STARTING KINETICS EXPERIMENT..\n\n");

#ifdef DO_KINETICS_WITH_EXPOSE_DURING_TRIGGER_PULSE
    TriggerResponse =  PicamTriggerResponse_ExposeDuringTriggerPulse; 
    TriggerDetermination = PicamTriggerDetermination_PositivePolarity;
    acquireTimoutMillisecs = -1; // Disable timeout on acquisition
    usingTrigger = true;
    printf("   with Expose During Trigger Pulse Hardware mode\n\n");
#endif

#ifdef DO_KINETICS_WITH_SHIFT_PER_TRIGGER
    TriggerResponse = PicamTriggerResponse_ShiftPerTrigger;
    TriggerDetermination = PicamTriggerDetermination_PositivePolarity;
    usingTrigger = true;
    acquireTimoutMillisecs = -1; // Disable timeout on acquisition
    printf("   with Shift Per Trigger Hardware mode\n\n");
#endif

#ifdef DO_KINETICS_WITH_READOUT_PER_TRIGGER
    TriggerResponse = PicamTriggerResponse_ReadoutPerTrigger;
    TriggerDetermination = PicamTriggerDetermination_NegativePolarity;
    usingTrigger = true;
    acquireTimoutMillisecs = -1; // Disable timeout on acquisition
    printf("   with Readout Per Trigger Hardware mode\n\n");
#endif

    err = Picam_SetParameterIntegerValue(camera,
                    PicamParameter_ReadoutControlMode, ReadoutMode); 
    if (err != PicamError_None)
    {
        printf("ERROR SetParameter PicamParameter_ReadoutControlMode");
        return;
    }

    err = Picam_SetParameterFloatingPointValue(
        camera,PicamParameter_ExposureTime, exposureTimeMillisecs );
    if (err != PicamError_None)
    {
        printf("ERROR SetParameter PicamParameter_ExposureTime");
        return;
    }

    err = Picam_SetParameterIntegerValue(   camera,
                PicamParameter_KineticsWindowHeight, kineticsWindowHeight);
    if (err != PicamError_None)
    {
        printf("ERROR SetParameter PicamParameter_KineticsWindowHeight");
        return;
    }

    // If using a triggered kinetics acquisition, set type of trigger response
    if (usingTrigger)
    {
        // trigger each  image  or each frame/shift
        err = Picam_SetParameterIntegerValue( camera,
            PicamParameter_TriggerResponse, TriggerResponse);

        if (err != PicamError_None)
        {
            printf("ERROR SetParameter PicamParameter_TriggerResponse");
            return;
        }

        //  Positive or negative edge of trigger pulse
        err = Picam_SetParameterIntegerValue(   camera,
            PicamParameter_TriggerDetermination, TriggerDetermination);

        if (err != PicamError_None)
        {
            printf("ERROR SetParameter PicamParameter_TriggerDetermination");
            return;
        }
    } // if (usingTrigger)


     // Get dimensional constraints (ptrConstraint must be deallocated)
    err = Picam_GetParameterRoisConstraint(	camera, PicamParameter_Rois, 
        PicamConstraintCategory_Required, &ptrConstraint);	
    if (err != PicamError_None)
    {
        printf("ERROR GetParameter PicamParameter_Rois");
        return;
    }

    // Get width and height of accessible region from current constraints 
    readoutWidth      = (piint)ptrConstraint->width_constraint.maximum;
    singleFrameHeight = (piint)ptrConstraint->height_constraint.maximum;

    // Deallocate constraints after using access 
    Picam_DestroyRoisConstraints(ptrConstraint);

    // Get number of frames that are returned in a single readout,
    //    given this kinetics window size
    err = Picam_GetParameterIntegerValue( camera, 
            PicamParameter_FramesPerReadout, &framesPerReadout);
    if (err != PicamError_None)
    {
        printf("ERROR GetParameter PicamParameter_FramesPerReadout");
        return;
    }

    // calculate height of full readout 
    readoutHeight = singleFrameHeight * framesPerReadout;

    // setup the roiSetup object count and pointer 
	roiSetup.roi_count = 1;
    roiSetup.roi_array = &theKineticsROI;

    // The ROI structure should hold the size of a single kinetics capture ROI 
    theKineticsROI.height		= singleFrameHeight;
    theKineticsROI.width		= readoutWidth;

    // The ROI structure should hold the location of this ROI (upper left corner of window)
    theKineticsROI.x			= 0;
    theKineticsROI.y			= 0;

    // The vertical and horizontal binning 
    theKineticsROI.x_binning	= 1;
    theKineticsROI.y_binning	= 1;

    // Set the roiSetup of interest 
    err = Picam_SetParameterRoisValue(	camera, PicamParameter_Rois, &roiSetup);

    // Commit to hardware 
    err = Picam_CommitParameters( camera, &paramsFailed, &failCount);

    if (err == PicamError_None) 
    {
        printf("\nStart Picam_Acquire():\n  %d frames of Kinetics data (%d pix high), in %d readouts\n", 
            (int)(framesPerReadout * numReadoutsRequested),(int) kineticsWindowHeight,(int)numReadoutsRequested);

        // Prompt if Triggered mode is requested
#ifdef DO_KINETICS_WITH_SHIFT_PER_TRIGGER
    printf("\n   Press Trigger for each Kinetics Window frame requested....\n");
#endif

#ifdef DO_KINETICS_WITH_EXPOSE_PER_TRIGGERPAIR
    printf("\n   Press Trigger for each Kinetics Window frame expose requested....\n");
#endif

#ifdef DO_KINETICS_WITH_READOUT_PER_TRIGGER
    printf("\n   Press Trigger to begin Kinetics capture for each readout requested....\n");
#endif
        if (acquireTimoutMillisecs != -1)
            printf("     .... %d msec Timeout ....\n",(int)acquireTimoutMillisecs);


        if (Picam_Acquire(camera, numReadoutsRequested, acquireTimoutMillisecs, 
                &acquisitionData, &acqErrors) == PicamError_None) 
        {
            printf("..Picam_Acquire() successfully returned\n");

            // Get the pixel BitDepth 
            piint pixelBitDepth;
            Picam_GetParameterIntegerValue(	camera, PicamParameter_PixelBitDepth, &pixelBitDepth);

            // sample function to show how to write out this data to file
            //   returns boolean true if success, else false
            myWriteDataToFile(acquisitionData.initial_readout, 
                    pixelBitDepth, numReadoutsRequested,
                    readoutHeight,   readoutWidth, TargetFileName);
 
        }
        else // Error returned from Picam_Acquire( 
        {
            printf("\n! ! Error returned from Picam_Acquire() = %d ! !\n",(int)err);
            DisplayError(err);
        }

    } // after Picam_CommitParameters( )
    else // Error returned from Picam_CommitParameters( 
    {
        printf("\n ! ! Error returned from Picam_CommitParameters() = %d: %d failures:\n",(int)err, (int)failCount);
        DisplayError(err);
        const PicamParameter *ptrErr = paramsFailed;

        for (int n=0; n < failCount; n++)
        {
            printf("  %2d:  %d\n",(int)n+1,(int) *ptrErr);
            ptrErr++;
        }

        // free failed parameter array allocated by picam
        Picam_DestroyParameters(paramsFailed);
     } //if (err == PicamError_None)	 

} //DoKineticsCapture( ) 

