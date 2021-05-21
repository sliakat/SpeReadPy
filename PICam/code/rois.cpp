#include "picam.h" /* Teledyne Princeton Instruments API Header */
#include "stdio.h"

#define SAMPLE_REGIONS		4	/* Multiple Region Count */
#define ACQUIRE_TIMEOUT	15000	/* Fifteen second timeout */

/* Single Region Example Code */
void DoSingleROI(PicamHandle camera);

/* Multiple Region Example Code */
void DoMultipleROIs(PicamHandle camera);

/* Show error code helper routine */
void DisplayError(PicamError errCode);

/* Compute average pixel value helper routine */
piflt ComputeAverage(void *p, piint depth, piint x, piint y, piint pixelOffset);

/******************************************************************************
*	Teledyne Princeton Instruments Region of Interest (ROI) example.
*
*	This example main is broken up into two core parts 
*			a.) Single Region 
*			b.) Multiple region
*
******************************************************************************/
int main()
{
	PicamError  errCode = PicamError_None;	/* Error Code		*/
	PicamHandle camera  = NULL;				/* Camera Handle	*/

	/* Initialize the library */
	errCode = Picam_InitializeLibrary();

	/* Check error code */
	if (errCode == PicamError_None)
	{
		/* Open the first camera */
		errCode = Picam_OpenFirstCamera( &camera );

		/* If the camera open succeeded */
		if (errCode == PicamError_None)
		{
			/* Setup and acquire with a single region of interest */
			DoSingleROI(camera);

			/* Setup and acquire with multiple regions of interest */
			DoMultipleROIs(camera);

			/* We are done with the camera so close it */
			Picam_CloseCamera(camera);
		}
		/* Show error string if a problem occurred */
		else 
			DisplayError(errCode);		
	}
	/* Show error string if a problem occurred */
	else 
		DisplayError(errCode);

	/* Uninitialize the library */
	Picam_UninitializeLibrary();
}

/******************************************************************************
*	Teledyne Princeton Instruments Region of Interest (ROI) example.
*
*	Sets up the camera and acquires from a single region of interest.
*
*		------------------------	This example gets the maximum extent and
*		------------------------	sets up a window in the center that is 
*		------xxxxxxxxxxxx------	 1/2 of the maximum height and width.
*		------xxxxxxxxxxxx------
*		------xxxxxxxxxxxx------
*		------xxxxxxxxxxxx------
*		------------------------
*		------------------------
*
******************************************************************************/
void DoSingleROI(PicamHandle camera)
{
	PicamError					err;			 /* Error Code			*/
	PicamAvailableData			dataFrame;		 /* Data Struct			*/
	PicamAcquisitionErrorsMask	acqErrors;		 /* Errors				*/
	const PicamRois				*region;		 /* Region of interest  */
	const PicamParameter		*paramsFailed;	 /* Failed to commit    */
	piint						failCount;		 /* Count of failed	    */
	const PicamRoisConstraint  *constraint;		 /* Constraints			*/
	
	/* Variables to compute central region in image */
	piint halfHeight, halfWidth, totalWidth, totalHeight;

	/* Get dimensional constraints */
	err = Picam_GetParameterRoisConstraint(	camera, 
											PicamParameter_Rois, 
											PicamConstraintCategory_Required, 
											&constraint);	
	/* Error check */
	if (err == PicamError_None)
	{		
		/* Get width and height from constraints */
		totalWidth = (piint)constraint->width_constraint.maximum;
		totalHeight= (piint)constraint->height_constraint.maximum;

		/* Clean up constraints after using constraints */
		Picam_DestroyRoisConstraints(constraint);

		halfWidth	= totalWidth  / 2;
		halfHeight	= totalHeight / 2;	

		/* Get the orinal ROI */
		err = Picam_GetParameterRoisValue(	camera, 
											PicamParameter_Rois, 
											&region);
		/* Error check */
		if (err == PicamError_None)
		{
			/* Modify the region */
			if (region->roi_count == 1) 
			{
				/* The absolute size of the ROI */
				region->roi_array[0].height		= halfHeight;
				region->roi_array[0].width		= halfWidth;

				/* The offset into the chip of the ROI (1/4th) */
				region->roi_array[0].x			= halfWidth  / 2;
				region->roi_array[0].y			= halfHeight / 2;

				/* The vertical and horizontal binning */
				region->roi_array[0].x_binning	= 1;
				region->roi_array[0].y_binning	= 1;
			}
			/* Set the region of interest */
			err = Picam_SetParameterRoisValue(	camera, 
												PicamParameter_Rois, 
												region);
			/* Error check */
			if (err == PicamError_None)
			{
				/* Commit ROI to hardware */
				err = Picam_CommitParameters(	camera, 
												&paramsFailed, 
												&failCount);
                Picam_DestroyParameters(paramsFailed);

				/* Error check */
				if (err == PicamError_None)
				{
					/* Acquire 1 frame of data with a timeout */
					if (Picam_Acquire(camera, 1, ACQUIRE_TIMEOUT, &dataFrame, &acqErrors) == PicamError_None) 
					{
						/* Get the bit depth */
						piint depth;
						Picam_GetParameterIntegerValue(	camera, 
														PicamParameter_PixelBitDepth,  
														&depth);
						/* Compute the average over the region */
						double dAverage = ComputeAverage(	dataFrame.initial_readout, 
															depth, 
															halfWidth, 
															halfHeight,
															0);						
						/* Print Average */
						printf("Single: Average for ROI => %.2f \n", (double) dAverage);						
					}
				}				
			}	
			/* Free the regions */
			Picam_DestroyRois(region);
		}
	} 	
}

/******************************************************************************
*	Teledyne Princeton Instruments Region of Interest (ROI) example.
*
*	Sets up the camera and acquires from four regions of interest.
*
*		------------------------	This example code will generate four ROIs
*		--1111---------111------	with various sizes and binning.
*		--1111---------111------	
*		---------------111------
*		------------------------
*		--222222--------2222----
*		--222222--------2222----
*		------------------------
*
******************************************************************************/
void DoMultipleROIs(PicamHandle camera)
{
	PicamError					err;			 /* Error Code			*/
	PicamAvailableData			dataFrame;		 /* Data Struct			*/
	PicamAcquisitionErrorsMask	acqErrors;		 /* Errors				*/	
	const PicamParameter		*paramsFailed;	 /* Failed to commit    */
	piint						failCount;		 /* Count of failed	    */

	PicamRois					region;			 /* Region of interest  */
	PicamRoi					sampleRegions[SAMPLE_REGIONS];

	const PicamRoisConstraint  *constraint;		 /* Constraints			*/

	/* Simple structure used to compute N regions	*/
	/* based on overall imager percentages			*/
	struct RegionPercents 
	{
		piflt percentX_start;	/* Offset X position as a percent */
		piflt percentY_start;	/* Offset Y position as a percent */
		piflt percentX_end;		/* Ending X position as a percent */
		piflt percentY_end;		/* Ending Y position as a percent */
		piint xBin;				/* X Binning of this region		  */
		piint yBin;				/* Y Binning of this region		  */
	};
	
	/* 4 regions defined as percentages of imaging area */
	RegionPercents computed[] = {{ 0.10, 0.10, 0.25, 0.25, 1, 1 }, 
								 { 0.65, 0.05, 0.84, 0.35, 1, 1 }, 
								 { 0.15, 0.50, 0.37, 0.90, 1, 2 }, 
								 { 0.55, 0.50, 0.95, 0.90, 1, 2 }};

	/* setup the region object count and pointer */	
	region.roi_count = SAMPLE_REGIONS;
	region.roi_array = sampleRegions;

	/* Variables to compute central region in image */
	piint totalWidth, totalHeight;

	/* If we require symmetrical regions return since we are not setup */
	/* for that with our regions */
	err = Picam_GetParameterRoisConstraint(	camera, 
											PicamParameter_Rois, 
											PicamConstraintCategory_Required, 
											&constraint);	

	/* Error check for width and height */
	if (err == PicamError_None)
	{						
		/* If we require symmetrical regions return since we are not setup */
		/* for that with our regions, they are asymmetrical */
		if ((constraint->rules & PicamRoisConstraintRulesMask_HorizontalSymmetry) ||
			(constraint->rules & PicamRoisConstraintRulesMask_VerticalSymmetry))
		{
			/* cleanup and return */
			Picam_DestroyRoisConstraints(constraint);
			return;
		}

		/* Get width and height from constraints */
		totalWidth  = (piint)constraint->width_constraint.maximum;
		totalHeight = (piint)constraint->height_constraint.maximum;

		/* Clean up constraints after using them */
		Picam_DestroyRoisConstraints(constraint);

		/* Compute the 4 regions based on percentages of the sensor size */
		for (int i=0; i<SAMPLE_REGIONS; i++) {

			/* Sizes (convert from percents to pixels) */
			sampleRegions[i].height = (piint)((computed[i].percentY_end - computed[i].percentY_start) * (piflt)totalHeight);
			sampleRegions[i].width  = (piint)((computed[i].percentX_end - computed[i].percentX_start) * (piflt)totalWidth);

			/* Offsets (convert from percents to pixels) */
			sampleRegions[i].y = (piint)(computed[i].percentY_start * (piflt)totalHeight);
			sampleRegions[i].x = (piint)(computed[i].percentX_start * (piflt)totalWidth);

			/* Binning */
			sampleRegions[i].y_binning = computed[i].yBin;
			sampleRegions[i].x_binning = computed[i].xBin;
		}

		/* Set the region of interest */
		err = Picam_SetParameterRoisValue(camera, PicamParameter_Rois, &region);

		/* Error check */
		if (err == PicamError_None)
		{
			/* Commit ROI to hardware */
			err = Picam_CommitParameters(camera, &paramsFailed, &failCount);
            Picam_DestroyParameters(paramsFailed);

			/* Error check */
			if (err == PicamError_None)
			{
				/* Get the bit depth */
				piint depth;
				Picam_GetParameterIntegerValue(	camera, 
												PicamParameter_PixelBitDepth,  
												&depth);
				/* Acquire 1 frame of data with a timeout */
				if (Picam_Acquire(camera, 1, ACQUIRE_TIMEOUT, &dataFrame, &acqErrors) == PicamError_None)
				{
					piint offset_pixels = 0;
					for (int i=0; i<SAMPLE_REGIONS; i++)
					{
						/* Compute the average over the region */
						double dAverage = ComputeAverage(	dataFrame.initial_readout, 
															depth, 
															sampleRegions[i].width / sampleRegions[i].x_binning, 
															sampleRegions[i].height/ sampleRegions[i].y_binning,
															offset_pixels);

						/* move the offset into the buffer to look at for next roi */
						offset_pixels += (sampleRegions[i].width / sampleRegions[i].x_binning) * (sampleRegions[i].height / sampleRegions[i].y_binning);

						/* Print Average */
						printf("Multiple: Average for ROI %i => %.2f \n",(int) i+1, (double)dAverage);
					}							
				}
			}			
		}					
	} 		
}

/******************************************************************************
*	Teledyne Princeton Instruments Region of Interest (ROI) example.
*	
*	DisplayError helper routine, prints out the message for the associated 
*	error code.
*
******************************************************************************/
void DisplayError(PicamError errCode)
{
	/* Get the error string, the called function allocates the memory */
	const pichar *errString;
	Picam_GetEnumerationString(	PicamEnumeratedType_Error, 
								(piint)errCode, 
								&errString);
	/* Print the error */
	printf("%s\n", errString);

	/* Since the called function allocated the memory it must free it */
	Picam_DestroyString(errString);
}

/******************************************************************************
*
*	Simple helper function to make an average computation from within a buffer
*	Note: The pixelOffset should be the sum of pixels in the regions you are
*	skipping over.
*
******************************************************************************/
piflt ComputeAverage(void *buffer, 
					 piint depth, 
					 piint x, 
					 piint y,
					 piint pixelOffset)
{	
	piint totalPixels = x*y;
	piflt average	  = 0.0;

	switch (depth)
	{				
		case 16: 
			{			
				/* Sum Pixels */
				unsigned short *pUShort = (unsigned short *)buffer + pixelOffset;
				for (int i=0; i<x*y; i++)				
					average += *pUShort++;

				/* Divide by N */
				average /= totalPixels;
			}
			break;
	}
	return average;
}
