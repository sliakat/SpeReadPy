clear all

Setup_LightField_Environment;
instance1=lfm(true);
exp=instance1.application.Experiment;

if device_loaded(exp)
    print_device_information(exp);
    print_current_capabilities(exp, string(PrincetonInstruments...
        .LightField.AddIns.CameraSettings.AdcSpeed));
    print_maximum_capabilities(exp, string(PrincetonInstruments...
        .LightField.AddIns.CameraSettings.AdcAnalogGain));
    print_maximum_capabilities(exp, string(PrincetonInstruments...
        .LightField.AddIns.CameraSettings.AdcSpeed));
    set_value(exp, PrincetonInstruments.LightField.AddIns.CameraSettings...
        .AdcAnalogGain, 1);
    print_setting(exp, PrincetonInstruments.LightField.AddIns...
        .CameraSettings.AdcAnalogGain);
    set_value(exp, PrincetonInstruments.LightField.AddIns.CameraSettings...
        .AdcAnalogGain, 3);
    print_setting(exp, PrincetonInstruments.LightField.AddIns...
    .CameraSettings.AdcAnalogGain);
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
            camLoaded=1;
            break;
        end
    end
    if ~camLoaded
        fprintf('Camera not found. Please add a camera and try again.\n');
    end
end

function print_device_information(obj)
    fprintf('Experiment Device Information\n');
    devList=obj.ExperimentDevices;
    objects=devList.Count;

    for i=1:objects
        device=devList.Item(i-1);
        SN=string(device.SerialNumber);
        model=string(device.Model);
        fprintf('\t%s \t%s\n',model,SN);
    end
end

function print_current_capabilities(obj, setting)
    fprintf('Current %s Capabilities:\n',setting);
    capabilities = obj.GetCurrentCapabilities(setting);
    caps = capabilities.Count;
    for i=1:caps
        print_speeds(str2double(string((capabilities.Item(i-1)))));
    end
end

function print_speeds(item)
    if item < 1
        rate = 'kHz';
        item = item * 1000;
    else
        rate = 'MHz';
    end
    fprintf('\t%d %s\n', item, rate);    
end

function print_maximum_capabilities(obj, setting)
    fprintf('Maximum %s Capabilities:\n', setting);
    capabilities = obj.GetMaximumCapabilities(setting);
    caps = capabilities.Count;
    for i=1:caps
        if contains(setting, 'Camera.Adc.Speed')
            print_speeds(str2double(string((capabilities.Item(i-1)))));
        else
            fprintf('\t%s %s\n', setting, string(capabilities.Item(i-1)))
        end
    end
end

function set_value(obj, setting, value)
    if obj.Exists(setting)
        fprintf('Setting %s to %s\n', string(setting), string(value));
        obj.SetValue(setting, value);
    end
end

function print_setting(obj, setting)
    if obj.Exists(setting)
        fprintf('\tReading %s = %s\n', string(setting),...
            string(obj.GetValue(setting)));
    end
end