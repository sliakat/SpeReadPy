clear all;

Setup_LightField_Environment;
instance1=lfm(true);

exp=instance1.application.Experiment;

if device_loaded(exp)
    exp.Acquire();
    flagPrint=1;
    while exp.IsRunning
        if flagPrint
            fprintf('Acquiring...\n');
            flagPrint=0;
        end
    end
    fprintf('Acquisition finished.\n');
    directory = string(exp.GetValue(PrincetonInstruments.LightField.AddIns...
        .ExperimentSettings.FileNameGenerationDirectory));
    data = openSPE(instance1,directory);
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


function data = openSPE(obj,dirSPE)
    import System.IO.FileAccess;
    speFiles = dir(strcat(dirSPE,'\*.spe'));
    [~,ind] = sort([speFiles.datenum],'descend');
    PathSPE = strcat(dirSPE, '\', speFiles(ind(1)).name);
    imageset = obj.application.FileManager.OpenFile(PathSPE,FileAccess.Read);
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