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
    set_repetitive_gate(exp, 50, 100); %pulse values in ns
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

function set_repetitive_gate(obj,width,delay)
    if obj.Exists(PrincetonInstruments.LightField.AddIns.CameraSettings...
            .GatingMode)
        obj.SetValue(PrincetonInstruments.LightField.AddIns.CameraSettings...
            .GatingMode, PrincetonInstruments.LightField.AddIns...
            .GatingMode.Repetitive);
        obj.SetValue(PrincetonInstruments.LightField.AddIns.CameraSettings...
            .GatingRepetitiveGate, PrincetonInstruments.LightField.AddIns...
            .Pulse(width,delay));
    else
        fprintf('System not capable of Gating Mode');
    end
end