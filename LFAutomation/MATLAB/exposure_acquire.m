clear all

Setup_LightField_Environment;
instance1=lfm(true);

exp=instance1.application.Experiment;
framesToCapture = 10;

if device_loaded(exp)
    set_value(exp,PrincetonInstruments.LightField.AddIns.CameraSettings...
        .ShutterTimingExposureTime,20.0);
    imageset=exp.Capture(framesToCapture); %synch acquire n frames without saving
    data=extractData(imageset);
end

%instance1.close; %close instance via this command (or you can just x the
%window when you are done)


function set_value(obj,setting,value)
    if obj.Exists(setting)
        if obj.IsValid(setting,value)
            obj.SetValue(setting,value);
        else 
            disp('value not valid')
        end
    else
        disp('operation not found/defined');
    end
end

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

function data = extractData(imageset)
    if imageset.Regions.Length == 1
        if imageset.Frames == 1
            frame = imageset.GetFrame(0,0);
            data = reshape(frame.GetData().double,frame.Width,frame.Height)';
            return;
        else
            data = [];
            for i = 0:imageset.Frames-1
                frame = imageset.GetFrame(0,i);
                data = cat(3,data,reshape(frame.GetData().double,frame.Width,frame.Height,1)');
            end
            return;
        end
    else
        data = cell(imageset.Regions.Length,1);
        for j = 0:imageset.Regions.Length-1
            if imageset.Frames == 1
                frame = imageset.GetFrame(j,0);
                buffer = reshape(frame.GetData().double,frame.Width,frame.Height)';
            else
                buffer = [];
                for i = 0:imageset.Frames-1
                    frame = imageset.GetFrame(j,i);
                    buffer = cat(3,buffer,reshape(frame.GetData().double,frame.Width,frame.Height,1)');
                end
            end
            data{j+1} = buffer;
        end
    end

end