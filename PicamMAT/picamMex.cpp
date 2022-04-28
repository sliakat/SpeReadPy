#include "mex.hpp"
#include "mexAdapter.hpp"
#include "picam.h"

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
    }
    void operator()(ArgumentList outputs, ArgumentList inputs){
        int* errPtr;
        ArrayFactory factoryObject;
        const int inputInt = inputs[0][0];
        switch(inputInt){
            case 0: InitAndOpen(errPtr);
                    break;
            case 1: AcquireSingle(errPtr);
                    break;
            case 2: CloseAndExit(errPtr);
                    break;
            default: CloseAndExit(errPtr);
                    break;
        }
        TypedArray<int> outputErr = factoryObject.createScalar<int>(*(errPtr));
        outputs[0] = outputErr;
        
        int regionLength = rows_*cols_;
        if (regionLength > 0)
        {
            //TypedArray<pi16u> outputData = factoryObject.createArray<pi16u>({1, imageData16_.size()},imageData16_.data(),imageData16_.data()+imageData16_.size());
            TypedArray<pi16u> outputData = factoryObject.createArray<pi16u>({(pi16u)rows_,(pi16u)cols_},imageData16_.data(),imageData16_.data()+imageData16_.size());
            outputs[1] = outputData;
        }        
    }
    void InitAndOpen(int* errPtr)
    {
        Picam_InitializeLibrary();
        int err = Picam_OpenFirstCamera(&camera_);
        Picam_GetCameraID(camera_,&id_);
        Picam_GetParameterFloatingPointValue(camera_, PicamParameter_ReadoutRateCalculation, &readRate_);
        *(errPtr) = err;
    }
    void AcquireSingle(int *errPtr)
    {        
        PicamAvailableData data;
        PicamAcquisitionErrorsMask errors;
        //give acquire a timeout of 2x readout rate, or 3 secs, whichever is larger
        //having a timeout error returned can give the user a means to "reset" in the main app
        double expectedFrameTime = (1 / readRate_);
        timeout_ = (int)(2 * expectedFrameTime * 1000);
        if (timeout_ < 3000)
        {
            timeout_ = 3000;
        }
        int err = Picam_Acquire(camera_, 1, timeout_, &data, &errors);
        *(errPtr) = err;
        if (err == 0)
        {
            GetXandY();
            Picam_GetParameterIntegerValue(camera_, PicamParameter_ReadoutStride, &readoutStride_);
            piint readCount = data.readout_count;
            //assume 16-bit data
            pi16u* framePtr = nullptr;
            framePtr = reinterpret_cast<pi16u*>(data.initial_readout);
            std::vector<pi16u> imageData16(framePtr, framePtr + (readCount * (readoutStride_ / 2)));
			imageData16_ = imageData16;
        }
    }
    
    //this is the cleanup
    void CloseAndExit(int* errPtr)
    {
        //stop any running acquisition --> close camera --> uninitialize PICam
        pibln cameraRunning = false;
        PicamAvailableData data;
        PicamAcquisitionStatus status;
        Picam_IsAcquisitionRunning(camera_, &cameraRunning);
        if (cameraRunning)
		{
			Picam_StopAcquisition(camera_);
			while (cameraRunning)
			{
				Picam_WaitForAcquisitionUpdate(camera_,timeout_,&data,&status);
                		cameraRunning = status.running;
			}
		}
        int err = Picam_CloseCamera(camera_);
        Picam_UninitializeLibrary();
        *(errPtr) = err;
    }
    //destructor to close the camera and uninitialize PICam if something happens to the MATLAB connection.
    ~MexFunction(){
        int* errPtr;
        CloseAndExit(errPtr);
    }
    void GetXandY()
    {
        //here we assume there is only 1 ROI (as we did not assign any ROI parameters in this example
        //see Rois sample for more examples on ROI
        const PicamRois* rois; piint width, height, xbin, ybin;
        Picam_GetParameterRoisValue(camera_, PicamParameter_Rois, &rois);

        width = rois[0].roi_array[0].width;
        height = rois[0].roi_array[0].height;
        xbin = rois[0].roi_array[0].x_binning;
        ybin = rois[0].roi_array[0].y_binning;

        //determine rows and columns by dividing ROI length by binning in respective direction
        cols_ = (piint)(width / xbin);
        rows_ = (piint)(height / ybin);
    }
private:
    PicamHandle camera_;
    PicamCameraID id_;
    double readRate_;
    int readoutStride_;
    std::vector<pi16u> imageData16_;
    int rows_;
    int cols_;
    int timeout_;
};
