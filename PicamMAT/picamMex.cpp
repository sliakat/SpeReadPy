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

//acq parameter map (param n in function 1):
// #3: exposure time (in ms)
// #4: shutter status (as int)
//     - use enum defs per Picam.h
//      - 1: Normal
//      - 2: Always Closed
//      - 3: Always Open
// #5: bin n center rows (0 for full frame roi set)

using namespace matlab::data;
using matlab::mex::ArgumentList;
using matlab::data::ArrayFactory;
using matlab::data::ArrayType;
using matlab::data::Array;
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
        piflt adc_speed;
        piint adc_ports_used;
        piint adc_analog_gain;
        piint adc_quality;
        piint sensor_original_cols;
        piint sensor_original_rows;
        const PicamRois* set_rois;
        
        CameraSettings()
        {
        }

        CameraSettings(PicamHandle camera)
        {
            _camera = camera;
            UpdateExposureTime();
            UpdateShutterMode();
            UpdateADCQuality();
            UpdateADCSpeed();
            UpdateAnalogGain();
            UpdatePorts();
            Picam_GetParameterIntegerValue(camera, PicamParameter_SensorActiveWidth, &sensor_original_cols);
            Picam_GetParameterIntegerValue(camera, PicamParameter_SensorActiveHeight, &sensor_original_rows);
            Picam_GetParameterRoisValue(camera, PicamParameter_Rois, &set_rois);
        }

        ~CameraSettings()
        {
            Picam_DestroyRois(set_rois);
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

        void UpdatePorts()
        {
            if (IsParameterValid(PicamParameter_ReadoutPortCount))
            {
                Picam_GetParameterIntegerValue(_camera, PicamParameter_ReadoutPortCount, &adc_ports_used);
            }
        }

        void UpdateADCSpeed()
        {
            if (IsParameterValid(PicamParameter_AdcSpeed))
            {
                Picam_GetParameterFloatingPointValue(_camera, PicamParameter_AdcSpeed, &adc_speed);
            }
        }

        void UpdateADCQuality()
        {
            if (IsParameterValid(PicamParameter_AdcQuality))
            {
                Picam_GetParameterIntegerValue(_camera, PicamParameter_AdcQuality, &adc_quality);
            }
        }

        void UpdateAnalogGain()
        {
            if (IsParameterValid(PicamParameter_AdcAnalogGain))
            {
                Picam_GetParameterIntegerValue(_camera, PicamParameter_AdcAnalogGain, &adc_analog_gain);
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
                else
                    Picam_DestroyPulses(newGate);
            }
            return false;
        }

        bool SetShutterMode(int mode)
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

        /*
        Attempts to set camera parameters to achieve the lowest read noise.
        This includes:
        - Set to 1-port, if applicable.
        - Checks for Low Noiae quality mode on the cameera. If the mode exists,
        changes to Low Noise quality and then sets ADC speed to the slowest speed
        in Low Noise.
        - true is returned if LowNoise Quality can be set, false otherwise
        */
        bool SetLowReadNoise()
        {
            if (IsParameterValid(PicamParameter_ReadoutPortCount))
            {
                Picam_SetParameterIntegerValue(_camera, PicamParameter_ReadoutPortCount, 1);
                if (CommitParameters())
                    UpdatePorts();
            }
            if (IsParameterValid(PicamParameter_AdcQuality))
            {
                // use capable constraints to get all possible ADC Qualities and identify if LowNoise exists
                if (SearchConstraints((piflt)PicamAdcQuality_LowNoise, PicamParameter_AdcQuality, PicamConstraintCategory_Capable))
                {
                    Picam_SetParameterIntegerValue(_camera, PicamParameter_AdcQuality, PicamAdcQuality_LowNoise);
                    CommitParameters();
                    UpdateADCQuality();
                    if (IsParameterValid(PicamParameter_AdcSpeed))
                    {
                        // now find the min of the the required constraints
                        const PicamCollectionConstraint* required;
                        piflt slowestSpeed;
                        Picam_GetParameterCollectionConstraint(_camera, PicamParameter_AdcSpeed,
                        PicamConstraintCategory_Required, &required);
                        slowestSpeed = MinFlt(required->values_array, required->values_count);
                        Picam_DestroyCollectionConstraints(required);
                        Picam_SetParameterFloatingPointValue(_camera, PicamParameter_AdcSpeed, slowestSpeed);
                        CommitParameters();
                        UpdateADCSpeed();
                        // now set high gain, if relevant
                        if (IsParameterValid(PicamParameter_AdcAnalogGain))
                        {
                            if (SearchConstraints((piflt)PicamAdcAnalogGain_High, PicamParameter_AdcAnalogGain, PicamConstraintCategory_Required))
                            {
                                Picam_SetParameterIntegerValue(_camera, PicamParameter_AdcAnalogGain, PicamAdcAnalogGain_High);
                                CommitParameters();
                                UpdateAnalogGain();
                            }
                        }
                        return true;
                    }
                }
            }
            return false;
        }

        /*
        Attempts to set a center row bin of n center rows per the user's input.
        An input of 0 or less will put the sensor in full frame mode, using the
        original sensor height and width determined during object construction.
        An input that is greater than the number of rows on the sensor will coerce
        to a full vertical bin.
        */
       bool SetCenterBinRows(int numRows)
       {
            PicamRoi roi;
            PicamRois rois;
            if (numRows <= 0)
            {
                // full sensor image
                roi.x = 0;
                roi.width = sensor_original_cols;
                roi.x_binning = 1;
                roi.y = 0;
                roi.height = sensor_original_rows;
                roi.y_binning = 1;
            }
            else if (numRows > sensor_original_rows)
            {
                // full vertical bin
                roi.x = 0;
                roi.width = sensor_original_cols;
                roi.x_binning = 1;
                roi.y = 0;
                roi.height = sensor_original_rows;
                roi.y_binning = sensor_original_rows;
            }
            else
            {
                // y index will be (sensor_original_rows - numRows) // 2
                int y = (int)((sensor_original_rows - numRows) / 2);
                roi.x = 0;
                roi.width = sensor_original_cols;
                roi.x_binning = 1;
                roi.y = y;
                roi.height = numRows;
                roi.y_binning = numRows;
            }
            rois.roi_array = &roi;
            rois.roi_count = 1;
            if (!Picam_SetParameterRoisValue(_camera, PicamParameter_Rois, &rois))
            {
                if (CommitParameters())
                {
                    Picam_GetParameterRoisValue(_camera, PicamParameter_Rois, &set_rois);
                    return true;
                }
            }
            return false;            
       }

       // check to see if the input parameter exists and is relevant
        bool IsParameterValid(PicamParameter param)
        {
            pibln exists;
            pibln isRelevant;
            Picam_DoesParameterExist(_camera, param, &exists);
            Picam_IsParameterRelevant(_camera, param, &isRelevant);
            return (exists && isRelevant);
        }

    private:
        PicamHandle _camera;  

        // try and commit parameters. Returns true on success.
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

        // helper function to get minumum value from a piflt array
        piflt MinFlt(const piflt* array, int arrayLength)
        {
            piflt minimum = array[0];
            for (int i=1; i<arrayLength; i++)
            {
                if (array[i] < minimum)
                    minimum = array[i];
            }
            return minimum;
        }

        // returns true if toFind is found inside the array, false if not
        bool FoundInArray(const piflt* array, int arrayLength, piflt toFind)
        {
            bool match = false;
            for (int i=0; i<arrayLength; i++)
            {
                if (toFind == array[i])
                {
                    match = true;
                    break;
                }
            }
            return match;
        }

        // helper function to loop through constraints to see if
        // the desired parameter can be set
        // returns true is toFind is found in the required/ capable constraints for
        // param, false otherwise
        bool SearchConstraints(piflt toFind, PicamParameter param, PicamConstraintCategory constraintType)
        {
            bool found = false;
            const PicamCollectionConstraint* constraint;
            Picam_GetParameterCollectionConstraint(_camera, param,
                constraintType, &constraint);
            for (int i=0; i<constraint->values_count; i++)
            {
                if (constraint->values_array[i] == toFind)
                {
                    found = true;
                    break;
                }
            }
            Picam_DestroyCollectionConstraints(constraint);
            return found;
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
            case 1:
                if (inputs.size() >=5)
                {
                    // param 5: center n row bin
                    int desiredCenterBin = factoryObject.createScalar<double>(inputs[4][0])[0];
                    if (!camSettings_.SetCenterBinRows(desiredCenterBin))
                    {
                        WriteString("Error when setting center bins.");
                    }
                }
                if (inputs.size() == 4)
                {
                    // param 4: shutter timing mode
                    int desiredShutter = factoryObject.createScalar<double>(inputs[3][0])[0];
                    if (!camSettings_.SetShutterMode(desiredShutter))
                    {
                        WriteString("Unable to set the shutter mode. Continuing with the original settings.");
                    }
                }
                if (inputs.size() == 3)
                {
                    // param 3: exposure time
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
            TypedArray<pi16u> rawData = factoryObject.createArray<pi16u>({(pi16u)cols_,(pi16u)rows_},imageData16_.data(),imageData16_.data()+imageData16_.size());
            std::vector<Array> args({rawData});
            std::shared_ptr<MATLABEngine> matlabPtr = getEngine();
            outputs[1] = matlabPtr->feval(u"transpose", args);
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
        WriteString("Initial ADC Parameters:");
        WriteADCParams();
    }
    void AcquireSingle()
    {        
        PicamAvailableData data;
        PicamAcquisitionErrorsMask errors;
        char temp[128];
        camSettings_.UpdateExposureTime();
        _snprintf_s(temp, 128, "Current Exposure time (ms if CCD, ns if gate width): %0.3f", camSettings_.exposure_time);
        WriteString(temp);
        Picam_GetParameterFloatingPointValue(*camera_, PicamParameter_ReadoutRateCalculation, &readRate_);
        _snprintf_s(temp, 128, "Read Rate: %0.3f fps", readRate_);
        WriteString(temp);
        camSettings_.SetLowReadNoise();
        WriteString("ADC Parameters Committed for Acquisition:");
        WriteADCParams();
        WriteString("ROI(s) Committed for Acquisition:");
        WriteROIs();
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

    // helper to condense ADC parameter writing into one call
    // quality, speed, gain, ports
    void WriteADCParams()
    {
        const char* temp_picam;
        char temp[128];
        if (camSettings_.IsParameterValid(PicamParameter_AdcQuality))
        {
            Picam_GetEnumerationString(PicamEnumeratedType_AdcQuality, camSettings_.adc_quality, &temp_picam);
            _snprintf_s(temp, 128, "\tQuality:\t%s", temp_picam);
            WriteString(temp);
        }
        if (camSettings_.IsParameterValid(PicamParameter_AdcSpeed))
        {
            _snprintf_s(temp, 128, "\tSpeed:\t\t%0.3fMHz", camSettings_.adc_speed);
            WriteString(temp);
        }
        if (camSettings_.IsParameterValid(PicamParameter_AdcAnalogGain))
        {
            Picam_GetEnumerationString(PicamEnumeratedType_AdcAnalogGain, camSettings_.adc_analog_gain, &temp_picam);
            _snprintf_s(temp, 128, "\tGain:\t\t%s", temp_picam);
            WriteString(temp);
        }
        if (camSettings_.IsParameterValid(PicamParameter_ReadoutPortCount))
        {
            _snprintf_s(temp, 128, "\tPorts:\t\t%d", camSettings_.adc_ports_used);
            WriteString(temp);
        }
        Picam_DestroyString(temp_picam);
    }

    // helper to write out the current ROI(s)
    void WriteROIs()
    {
        char temp[128];
        int roi_count = camSettings_.set_rois[0].roi_count;
        const PicamRoi* roi_objects = camSettings_.set_rois[0].roi_array;
        _snprintf_s(temp, 128, "%d ROI(s) set.", roi_count);
        WriteString(temp);
        for (int i=0; i < roi_count; i++)
        {
            _snprintf_s(temp, 128, "\tROI %d:", i+1);
            WriteString(temp);
            _snprintf_s(temp, 128, "\t\t(x, y):\t\t\t\t(%d, %d)",
                roi_objects[i].x, roi_objects[i].y);
            WriteString(temp);
            _snprintf_s(temp, 128, "\t\t(width, height):\t(%d, %d)",
                roi_objects[i].width, roi_objects[i].height);
            WriteString(temp);
            _snprintf_s(temp, 128, "\t\t(x_bin, y_bin):\t\t(%d, %d)",
                roi_objects[i].x_binning, roi_objects[i].y_binning);
            WriteString(temp);
        }
    }
};
