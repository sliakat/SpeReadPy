/******************************************************************************
*   This sample demonstrates moving a spectrograph center wavelength and related
*   callbacks and methods.
******************************************************************************/
#include <iostream>
#include "picam.h"

/******************************************************************************
* Show any error codes
******************************************************************************/
void ShowErrorCode(PicamError error)
{
    if (error != PicamError_None)
    {
        const pichar *pError;
        Picam_GetEnumerationString(PicamEnumeratedType_Error, error, &pError);

        std::cout << "Error: " << pError;
        std::cout << std::endl;

        Picam_DestroyString(pError);    
    }    
}
/******************************************************************************
*    Display the center wavelength allowable range 
******************************************************************************/
PicamError GetCenterWaveRange( PicamHandle spectrograph, 
                               piflt *minWave, 
                               piflt *maxWave,
                               piflt *increment)
{
    /* - note accessing a constraint returns an allocated copy */
    const PicamRangeConstraint* range;

    /* - get the range */
    PicamError error = 
        Picam_GetParameterRangeConstraint(spectrograph, 
                                          PicamParameter_CenterWavelengthSetPoint, 
                                          PicamConstraintCategory_Required, 
                                          &range );
    if (error == PicamError_None)
    {
        /* - describe the basic range */
        std::cout << "Center Wavelength Set Point Range: From " << range->minimum << " nm" 
                  << " to "  << range->maximum << " nm" 
                  << " increments of " << range->increment << " nm";

        std::cout << std::endl;

        /* Return the extents */
        *minWave = range->minimum;
        *maxWave = range->maximum;
        *increment = range->increment;

        /* - deallocate the constraint after printing */
        Picam_DestroyRangeConstraints( range );
    }    

    return error;
}
/******************************************************************************
* Move to a center wavelength and wait for the motion to complete
******************************************************************************/
void MoveToWavelength(PicamHandle spectrograph, 
                      piflt setPoint, 
                      pibln canWait)
{
    const PicamParameter *paramsFailed;	 /* Failed to commit    */
	piint failCount;		             /* Count of failed	    */

    Picam_SetParameterFloatingPointValue(spectrograph, 
                                         PicamParameter_CenterWavelengthSetPoint, 
                                         setPoint);

    /* Move begins on commit */
    Picam_CommitParameters(	spectrograph, &paramsFailed, &failCount);

    /* Show where we are going */
    std::cout << "Moving to Center Wavelength: " << setPoint;
    std::cout << std::endl;

    /* Wait for the move to complete (infinitely) */
    if (canWait)
    {
        std::cout << "Waiting..." << std::endl;
        Picam_WaitForStatusParameterValue(spectrograph, 
                                            PicamParameter_CenterWavelengthStatus,
                                            PicamCenterWavelengthStatus_Stationary,                               
                                            -1);

        /* Get the current center wave */
        piflt reading;        
        Picam_ReadParameterFloatingPointValue(spectrograph, 
                                             PicamParameter_CenterWavelengthReading, 
                                             &reading);
        /* Show we got there */
        std::cout << "Reading Center Wavelength: " << reading;
        std::cout << std::endl;
    }   
}
/******************************************************************************
* Make sure the center wavelength set value is on an increment
******************************************************************************/
piflt RoundToIncrement(piflt toRound, piflt increment, piflt minWave)
{
    /* Compute the number of increments */
    pi32u increments = (pi32u)(((toRound - minWave) / increment) + 0.5);
    
    /* Compute a perfect multiple of increments */
    return increments * increment + minWave;
}
/******************************************************************************
* Program entry point
******************************************************************************/
int main()
{
    /* Initialize the library */
    Picam_InitializeLibrary();

    /* Handle of the spectrograph */
    PicamHandle spectrograph;
    PicamCameraID id;
    const pichar* string;
    PicamError error;
    piflt minWave, maxWave, increment;

    /* Open the first camera, if you are running this sample the connected camera */
    /* should really be a Fergie */
    if( Picam_OpenFirstCamera( &spectrograph ) == PicamError_None )
        Picam_GetCameraID( spectrograph, &id );
    else
    {
        Picam_ConnectDemoCamera(PicamModel_Fergie256BFT, "0008675309", &id );
        Picam_OpenCamera( &id, &spectrograph );
        std::cout << "No Camera Detected, Creating Demo Spectrograph" << std::endl;
    }

    /* Display some information about the spectrograph */
    Picam_GetEnumerationString( PicamEnumeratedType_Model, id.model, &string );
    std::cout << string << "(SN:" << id.serial_number << ")" << std::endl;    
    Picam_DestroyString( string );

    /* Show the motion extents */
    error = GetCenterWaveRange(spectrograph, &minWave, &maxWave, &increment);

    /* Continue if no errors */
    if (error == PicamError_None)
    {           
        /* Can we wait for the status changes */
        pibln canWait;
        error = Picam_CanWaitForStatusParameter(spectrograph, 
                                                PicamParameter_CenterWavelengthStatus, 
                                                &canWait);
        if (error == PicamError_None)
        {                                
            /* Move to 25% full range*/
            piflt oneQuarterSetPoint = RoundToIncrement(minWave + ((maxWave - minWave) * 0.25), increment, minWave);
            MoveToWavelength(spectrograph, oneQuarterSetPoint, canWait);    
           
            /* Move to 75% full range */
            piflt threeQuarterSetPoint = RoundToIncrement(minWave + ((maxWave - minWave) * 0.75), increment, minWave);
            MoveToWavelength(spectrograph, threeQuarterSetPoint, canWait);
        }     
    }
 
    /* If we had any error show it */
    if (error != PicamError_None)
        ShowErrorCode(error);
    
    /* Clean up */
    Picam_CloseCamera( spectrograph );
    Picam_UninitializeLibrary();
}
