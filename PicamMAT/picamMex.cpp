#include "mex.hpp"
#include "mexAdapter.hpp"
#include "picam.h"
#include <stdio.h>

//inputs will be integers:
//0: initialize and open
//1: acquire 1 frame and output data array to MATLAB
//2: close and uninitialize

using namespace matlab::data;
using matlab::mex::ArgumentList;
using matlab::data::ArrayFactory;

class MexFunction : public matlab::mex::Function{
public:
    MexFunction()
    {
        rows_ = 0;
        cols_ = 0;
        id_ = new PicamCameraID;
        camera_ = new PicamHandle;
        error_ = 0;
        counter_ = 0;
    }
    void operator()(ArgumentList outputs, ArgumentList inputs){
        ArrayFactory factoryObject;
        const int inputInt = inputs[0][0];
        debug_ = false;
        //inputting anything as a second arg will turn on debug
        if (inputs.size() == 2)
        {
            debug_ = true;              
        }        
        //WriteString("Read input");
        switch(inputInt){
            case 0: InitAndOpen();
                    break;
            case 1: AcquireSingle();
                    break;
            case 2: CloseAndExit();
                    break;
            default: CloseAndExit();
                    break;
        }
        TypedArray<int> outputErr = factoryObject.createScalar<int>(error_);
        outputs[0] = outputErr;
    	WriteString("Outputs[0] succeeded.");
        
        int regionLength = rows_*cols_;
        if (regionLength > 0)
        {
            char temp[128];
            _snprintf_s(temp, 128, "Inside Region Loop, length: %d", regionLength);
            WriteString(temp);
            //TypedArray<pi16u> outputData = factoryObject.createArray<pi16u>({1, imageData16_.size()},imageData16_.data(),imageData16_.data()+imageData16_.size());
            TypedArray<pi16u> outputData = factoryObject.createArray<pi16u>({(pi16u)rows_,(pi16u)cols_},imageData16_.data(),imageData16_.data()+imageData16_.size());
            outputs[1] = outputData;
            counter_++;
            if (inputInt < 2)
            {
            _snprintf_s(temp, 128, "Acquisition iteration %d succeeded, Outputs[1] generated.", counter_);
            WriteString(temp);
            }
        }
        else
        {
            if (inputInt > 0)
            {
                char temp[128];
                _snprintf_s(temp, 128, "Region Length %d, failed check. Outputting 0.", regionLength);
                WriteString(temp);
                TypedArray<int> failedOutput = factoryObject.createScalar<int>(0);
                outputs[1] = failedOutput;
            }
            
        }
        WriteString("*************************************\n");
    }
    void InitAndOpen()
    {
        WriteString("*************************************\nNEW ACQUISITION RUN\n*************************************");
        Picam_InitializeLibrary();
        WriteString("Initialized.");
        error_ = Picam_OpenFirstCamera(camera_);
        WriteString("Opened.");
        Picam_GetCameraID(*camera_,id_);
        WriteString("Got ID.");
        Picam_GetParameterFloatingPointValue(*camera_, PicamParameter_ReadoutRateCalculation, &readRate_);
        char temp[128];
        _snprintf_s(temp, 128, "Read Rate: %0.3f", readRate_);
        WriteString(temp);
    }
    void AcquireSingle()
    {        
        PicamAvailableData data;
        PicamAcquisitionErrorsMask errors;
        char temp[128];
        //give acquire a timeout of 2x readout rate, or 3 secs, whichever is larger
        //having a timeout error returned can give the user a means to "reset" in the main app
        double expectedFrameTime = (1 / readRate_);
        timeout_ = (int)(2 * expectedFrameTime * 1000);
        if (timeout_ < 3000)
        {
            timeout_ = 3000;
        }
        WriteString("Before Acquire.");
        error_ = Picam_Acquire(*camera_, 1, timeout_, &data, &errors);
        WriteString("After Acquire.");        
        _snprintf_s(temp, 128, "\tPicamError %d\n\tErrorsMask %d\n", error_, errors);
        WriteString(temp);
        if ((error_ == 0) && (errors == 0))
        {
            GetXandY();
            WriteString("Got X and Y.");
            Picam_GetParameterIntegerValue(*camera_, PicamParameter_ReadoutStride, &readoutStride_);
            piint readCount = data.readout_count;        
            //assume 16-bit data
            pi16u* framePtr = nullptr;
            framePtr = reinterpret_cast<pi16u*>(data.initial_readout);
            WriteString("Successfully cast.");
            std::vector<pi16u> imageData16(framePtr, framePtr + (readCount * (readoutStride_ / 2)));
            WriteString("Created vector.");
			imageData16_ = imageData16;            
        }
    }
    
    //this is the cleanup
    void CloseAndExit()
    {
        //stop any running acquisition --> close camera --> uninitialize PICam
        pibln cameraRunning = false;
        PicamAvailableData data;
        PicamAcquisitionStatus status;
        Picam_IsAcquisitionRunning(*camera_, &cameraRunning);
        if (cameraRunning)
		{
			Picam_StopAcquisition(*camera_);
			while (cameraRunning)
			{
				Picam_WaitForAcquisitionUpdate(*camera_,timeout_,&data,&status);
                cameraRunning = status.running;
			}
		}
        error_ = Picam_CloseCamera(*camera_);
        WriteString("Closed Camera.");
        Picam_UninitializeLibrary();
        WriteString("Uninitialized library.");        
    }
    //destructor to clean up and reset state for next operation
    ~MexFunction(){
        WriteString("Inside Destructor.");
        CloseAndExit();
        delete id_;
        delete camera_;
        WriteString("Deleted handles.");
    }
    void GetXandY()
    {
        //here we assume there is only 1 ROI (as we did not assign any ROI parameters in this example
        //see Rois sample for more examples on ROI
        const PicamRois* rois; piint width, height, xbin, ybin;
        Picam_GetParameterRoisValue(*camera_, PicamParameter_Rois, &rois);

        width = rois[0].roi_array[0].width;
        height = rois[0].roi_array[0].height;
        xbin = rois[0].roi_array[0].x_binning;
        ybin = rois[0].roi_array[0].y_binning;

        //determine rows and columns by dividing ROI length by binning in respective direction
        cols_ = (piint)(width / xbin);
        rows_ = (piint)(height / ybin);
    }
private:
    PicamHandle* camera_;
    PicamCameraID* id_;
    double readRate_;
    int readoutStride_;
    std::vector<pi16u> imageData16_;
    int rows_;
    int cols_;
    int timeout_;
    FILE* pFile_;
    char string_[128];
    bool debug_;
    int error_;
    int counter_;
    
    //writes only if debug_ is set to True
    void WriteString(char* src)
    {
        if (debug_)
        {
            _snprintf_s(string_, 128, "%s\n", src);
            pFile_ = fopen("mexOutputStrings.txt","a");
            fprintf(pFile_, "%s", string_);
            fclose(pFile_);
        }       
    }
};
