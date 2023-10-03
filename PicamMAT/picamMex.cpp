#include "mex.hpp"
#include "mexAdapter.hpp"
#include "picam.h"
#include <stdio.h>

//Example cpp script using MATLAB's c++ API to integrate PICam
// with MATLAB to allow a user to repeatedly loop acquisitions
// and have access to the data in MATLAB.

//These will be defined as the main functions. Inputs will be integers:
//0: initialize and open
//1: acquire 1 frame and output data array to MATLAB
//2: close and uninitialize

//additional numeric inputs from parameter 3 onwards for
// some main functions.

//acq parameter map (param 3 in function 1):
// #3: exposure time (in ms)

using namespace matlab::data;
using matlab::mex::ArgumentList;
using matlab::data::ArrayFactory;
using matlab::data::ArrayType;
using matlab::engine::MATLABEngine;

//stores the camera parameter values that can be modified
class CameraSettings{
    public:
        enum ExposureTimeUnit{
            NONE,
            MS,
            NS    
        };
        piflt exposure_time;
        ExposureTimeUnit exposure_time_unit;      
        piint shutter_mode;
        
        CameraSettings()
        {
            exposure_time = -1;
            shutter_mode = PicamShutterTimingMode_Normal;
        }

        CameraSettings(PicamHandle camera)
        {
            _camera = camera;
            UpdateExposureTime();
            UpdateShutterMode();
        }

        //getters

        /*
        in this design, if exposure time doesn't exist, we check for gate width (ICCD)
        and treat that as an exposure time.
        if neither exposure time nor repetitive gate exist / are relevant,
        then defaults to -1 for exposure time and unit None
        */
        void UpdateExposureTime()
        {
            if (IsParameterValid(PicamParameter_ExposureTime))
            {
                Picam_GetParameterFloatingPointValue(_camera, PicamParameter_ExposureTime, &exposure_time);
                exposure_time_unit = ExposureTimeUnit::MS;
            }
            else if (IsParameterValid(PicamParameter_RepetitiveGate))
            {
                const PicamPulse* pulse;
                Picam_GetParameterPulseValue(_camera, PicamParameter_RepetitiveGate, &pulse);
                exposure_time = pulse->width;
                exposure_time_unit = ExposureTimeUnit::NS;
                Picam_DestroyPulses(pulse);
            }
            else
                exposure_time = -1;
                exposure_time_unit = ExposureTimeUnit::NONE;
        }

        void UpdateShutterMode()
        {
            if (IsParameterValid(PicamParameter_ShutterTimingMode))
            {
                Picam_GetParameterIntegerValue(_camera, PicamParameter_ShutterTimingMode, &shutter_mode);
            }
        }

        //setters
        bool SetExposureTime(piflt exposure_time)
        {
            if (IsParameterValid(PicamParameter_ExposureTime))
            {
                if (!Picam_SetParameterFloatingPointValue(_camera, PicamParameter_ExposureTime, exposure_time))
                {
                    if (CommitParameters())
                    {
                        UpdateExposureTime();
                        return true;
                    }
                }
            }
            if (IsParameterValid(PicamParameter_RepetitiveGate))
            {
                const PicamPulse* oldPulse;
                // need to get the old delay to put into new pulse
                Picam_GetParameterPulseValue(_camera, PicamParameter_RepetitiveGate, &oldPulse);
                piflt old_delay = oldPulse->delay;
                Picam_DestroyPulses(oldPulse);
                PicamPulse* newGate = new PicamPulse;
                newGate->delay = old_delay;
                newGate->width = exposure_time;
                if (!Picam_SetParameterPulseValue(_camera, PicamParameter_RepetitiveGate, newGate))
                {
                    Picam_DestroyPulses(newGate);
                    if (CommitParameters())
                    {
                        UpdateExposureTime();
                        return true;
                    }
                }
            }
            return false;
        }

        bool SetShutterMode(PicamShutterTimingMode mode)
        {
            if (IsParameterValid(PicamParameter_ShutterTimingMode))
            {
                Picam_SetParameterIntegerValue(_camera, PicamParameter_ShutterTimingMode, mode);
                if (CommitParameters())
                {
                    UpdateShutterMode();
                    return true;
                }
            }
            return false;
        }

    private:
        PicamHandle _camera;
        
        // check to see if the input parameter exists and is relevant
        bool IsParameterValid(PicamParameter param)
        {
            pibln exists;
            pibln isRelevant;
            Picam_DoesParameterExist(_camera, param, &exists);
            Picam_IsParameterRelevant(_camera, param, &isRelevant);
            return (exists && isRelevant);
        }

        //try and commit parameters. Returns true on success.
        // Success means there are no errors on the Commit call and
        // there are no failed parameters.
        bool CommitParameters()
        {
            const PicamParameter* failed_parameter_array;
            piint failed_parameter_count;
            if (!Picam_CommitParameters(_camera, &failed_parameter_array, &failed_parameter_count))
            {
                Picam_DestroyParameters(failed_parameter_array);
                if (failed_parameter_count == 0)
                {
                    return true;
                }
            }
            return false;
        }

};

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
        CheckArguments(outputs, inputs);
        const int inputInt = inputs[0][0];
        debug_ = false;
        //inputting anything as a second arg will turn on debug
        if (inputs.size() >= 2)
        {
            debug_ = true;              
        }        
        //WriteString("Read input");
        switch(inputInt){
            case 0: InitAndOpen();
                    break;
            case 1: if (inputs.size() >= 3)
                        {
                            double desiredExposure = factoryObject.createScalar<double>(inputs[2][0])[0];
                            if (!camSettings_.SetExposureTime(desiredExposure))
                            {
                                WriteString("Unable to set the exposure time. Continuing with the original settings.");
                            }
                        }
                    AcquireSingle();
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

    //basic sanity check on inputs
    void CheckArguments(ArgumentList outputs, ArgumentList inputs)
    {
        debug_ = true;
        std::shared_ptr<MATLABEngine> matlabPtr = getEngine();
        ArrayFactory factoryObject;

        //first check: there must be inputs
        if (inputs.size() < 1){
            matlabPtr->feval(u"error", 0,
            std::vector<Array>({ factoryObject.createScalar
            ("Mex function call has no inputs. See documentation in cpp file.") }));
        }
        //next, make sure the inputs are all scalar
        for (int i = 0; i < inputs.size(); i++)
        {            
            if (inputs[i].getNumberOfElements() != 1)
                {
                    matlabPtr->feval(u"error", 0,
                    std::vector<Array>({ factoryObject.createScalar
                    ("All inputs must be scalars.") }));
                }
        }
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
        _snprintf_s(temp, 128, "Read Rate: %0.3f fps", readRate_);
        WriteString(temp);
        camSettings_ = CameraSettings(*camera_);
        //shutter mode to Always Open; this is specific implementation for a user request, edit / remove
        // if not applicable
        if (!camSettings_.SetShutterMode(PicamShutterTimingMode_AlwaysOpen))
        {
            WriteString("Shutter could not be set to Always Open. Continuing with original settings.");
        }
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
        camSettings_.UpdateExposureTime();
        _snprintf_s(temp, 128, "Current Exposure time (ms if CCD, ns if gate width): %0.3f", camSettings_.exposure_time);
        WriteString(temp);
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
    CameraSettings camSettings_;
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
