clear all

fileName='myData';

Setup_LightField_Environment;
instance1=lfm(true);

if ~device_found(instance1)
    fprintf('Camera not found. Please add a camera and try again.\n');
else
    setFileParams(instance1,fileName);

    instance1.application.Experiment.Acquire()
    fprintf('Image saved to %s\n',string(instance1.application.Experiment...
    .GetValue(PrincetonInstruments.LightField.AddIns.ExperimentSettings...
    .FileNameGenerationDirectory)));
end



instance1.close;

function camDetected=device_found(obj)

    devList=obj.application.Experiment.AvailableDevices;
    objects=devList.Count;
    camDetected=0;

    for i=1:objects
        device=devList.Item(i-1);
        type=string(device.Type);
        if strcmp(type,'Camera')
            obj.application.Experiment.Add...
                (obj.application.Experiment.AvailableDevices.Item(i-1));
            fprintf('Loading Camera...\n')
            fprintf('Camera Loaded in Experiment\n');
            camDetected=1;
        end
    end
    
    %if nothing found in available devices, see if it was already added
    if camDetected==0
        devList=obj.application.Experiment.ExperimentDevices;
        objects=devList.Count;
        
        for i=1:objects
            device=devList.Item(i-1);
            type=string(device.Type);
            if strcmp(type,'Camera')
                fprintf('Camera Loaded in Experiment\n');
                camDetected=1;
            end
        end
    end


end

function setFileParams(obj,filename)
    import System.IO.Path;
    obj.set(PrincetonInstruments.LightField.AddIns.ExperimentSettings...
        .FileNameGenerationBaseFileName, Path.GetFileName(filename));
    obj.set(PrincetonInstruments.LightField.AddIns.ExperimentSettings...
        .FileNameGenerationAttachIncrement,'False');
    obj.set(PrincetonInstruments.LightField.AddIns.ExperimentSettings...
        .FileNameGenerationAttachDate,'True');
    obj.set(PrincetonInstruments.LightField.AddIns.ExperimentSettings...
        .FileNameGenerationAttachTime,'True');
    %file name will include base + date + time

end