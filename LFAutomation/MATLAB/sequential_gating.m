clear all

Setup_LightField_Environment;
instance1=lfm(true);
exp=instance1.application.Experiment;

if pm_loaded(exp)
    instance1.set(PrincetonInstruments.LightField.AddIns.CameraSettings...
        .ReadoutControlAccumulations, 3);
    fprintf('Current On-Chip Accumulations: %8g\n',string(instance1...
        .get(PrincetonInstruments.LightField.AddIns.CameraSettings...
        .ReadoutControlAccumulations)));
    set_sequential_gate(exp, 100, 50, 1000, 50); %pulse values in ns
    set(instance1,PrincetonInstruments.LightField.AddIns...
        .ExperimentSettings.AcquisitionFramesToStore, 10)
    data = acquire(instance1);
end

instance1.close;

function camLoaded=pm_loaded(obj)
    
    camLoaded=0;
    devList=obj.ExperimentDevices;
    objects=devList.Count;

    for i=1:objects
        device=devList.Item(i-1);
        type=string(device.Type);
        model=string(device.Model);
        if strcmp(type,'Camera') && contains(model,'PI-MAX')
            camLoaded=1;
            break;
        end
    end
    if ~camLoaded
        fprintf('Compatible camera not found. Please add PI-MAX type camera to LightField.');
    end
end

function set_sequential_gate(obj,start_width,start_delay...
    ,end_width,end_delay)
    if obj.Exists(PrincetonInstruments.LightField.AddIns.CameraSettings...
            .GatingMode)
        obj.SetValue(PrincetonInstruments.LightField.AddIns.CameraSettings...
            .GatingMode, PrincetonInstruments.LightField.AddIns...
            .GatingMode.Sequential);
        obj.SetValue(PrincetonInstruments.LightField.AddIns.CameraSettings...
            .GatingSequentialStartingGate, PrincetonInstruments.LightField...
        .AddIns.Pulse(start_width,start_delay));
        obj.SetValue(PrincetonInstruments.LightField.AddIns.CameraSettings...
        .GatingSequentialEndingGate, PrincetonInstruments.LightField...
        .AddIns.Pulse(end_width,end_delay));
    else
        fprintf('System not capable of Gating Mode');
    end
end