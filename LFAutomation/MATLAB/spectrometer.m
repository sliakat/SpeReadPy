clear all

Setup_LightField_Environment;
instance1=lfm(true);

exp=instance1.application.Experiment;

if spec_loaded(exp)
    set_center_wavelength(exp,500);
    get_spectrometer_info(exp);
end

instance1.close;


function set_center_wavelength(obj,cwl)
    obj.SetValue(PrincetonInstruments.LightField.AddIns...
        .SpectrometerSettings.GratingCenterWavelength, cwl);
end

function get_spectrometer_info(obj)
    fprintf('Center Wavelength: %s\n', string(obj.GetValue(...
        PrincetonInstruments.LightField.AddIns.SpectrometerSettings...
        .GratingCenterWavelength)));
    fprintf('Center Wavelength: %s\n', string(obj.GetValue(...
        PrincetonInstruments.LightField.AddIns.SpectrometerSettings...
        .GratingSelected)));
end

function specLoaded=spec_loaded(obj)
    
    specLoaded=0;
    devList=obj.ExperimentDevices;
    objects=devList.Count;

    for i=1:objects
        device=devList.Item(i-1);
        type=string(device.Type);
        if strcmp(type,'Spectrometer')
            specLoaded=1;
            break;
        end
    end
    if ~specLoaded
        fprintf('Spectrometer not found. Please add a spectrometer and try again.\n');
    end
end