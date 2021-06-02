clear all

%n x 6 matrix, n = number of desired ROIs
%column order (Lightfield Parameters): [X Y W H B B]
regionMat=[0 0 420 504 1 1; 478 418 512 516 1 1];

Setup_LightField_Environment;
instance1=lfm(true);

exp=instance1.application.Experiment;

if device_loaded(exp)
    setROIs(instance1,regionMat);   %Custom ROIs set to whatever was in matrix

    instance1.set_frames(1);    
    data=instance1.acquire;     
    instance1.experiment.SetFullSensorRegion(); %now set to Full Frame
    dataFull=instance1.acquire;     

    %plot acquired data
    figure(1);
    subplot(1,3,1), imshow(data{1,1},[]), title('ROI 1')
    subplot(1,3,2), imshow(data{2,1},[]), title('ROI 2')
    subplot(1,3,3), imshow(dataFull,[]), title('Full Frame')

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


function setROIs(obj,regionMat)      
regions=size(regionMat,1);
regionArray = NET.createArray('PrincetonInstruments.LightField.AddIns.RegionOfInterest',regions);
for i=1:regions
    x=regionMat(i,1); y=regionMat(i,2); width=regionMat(i,3);
    height=regionMat(i,4); xb=regionMat(i,5); yb=regionMat(i,6);
    regionArray(i) = PrincetonInstruments.LightField.AddIns.RegionOfInterest(x,y,width,height,xb,yb);
end

obj.experiment.SetCustomRegions(regionArray);

end
