clear all

Setup_LightField_Environment;
instance1=lfm(true);

exp=instance1.application.Experiment;

if device_loaded(exp)
    exp=instance1.application.Experiment;
    if set_value(exp,PrincetonInstruments.LightField.AddIns.CameraSettings...
            .AdcQuality, PrincetonInstruments.LightField.AddIns...
            .AdcQuality.ElectronMultiplied)
        set_first_capability(exp,PrincetonInstruments.LightField.AddIns...
            .CameraSettings.AdcSpeed);
        
        set_value(exp,PrincetonInstruments.LightField.AddIns...
            .CameraSettings.AdcEMGain,10.0);
        
        data = acquire(instance1);
    end
else
    fprintf('Camera not found. Please add a camera and try again.\n');
end


instance1.close;

function camLoaded=device_loaded(obj)
    
    camLoaded=0;
    devList=obj.ExperimentDevices;
    objects=devList.Count;

    for i=1:objects
        device=devList.Item(i-1);
        type=string(device.Type);
        if strcmp(type,'Camera')
            fprintf('Camera Loaded in Experiment\n');
            camLoaded=1;
            break;
        end
    end
end


function setFlag = set_value(obj,setting,value)
    setFlag=0;
    if obj.Exists(setting)
        if obj.IsValid(setting,value)
            obj.SetValue(setting,value);
            setFlag=1;
        else 
            disp('value not valid\n')
        end
    else
        disp('operation not found/defined\n');
    end
end

function set_first_capability(obj,setting)
    firstValue = obj.GetCurrentCapabilities(setting).Item(0);
    set_value(obj,setting,firstValue);
end
