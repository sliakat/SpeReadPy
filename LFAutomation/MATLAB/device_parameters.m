clear all

Setup_LightField_Environment;
instance1=lfm(true);

printDevParams(instance1);
instance1.close;

function printDevParams(obj)
devList=obj.application.Experiment.ExperimentDevices;
if 
device=devList.Item(0); %.NET object doesn't support MATLAB indexing
SN=string(device.SerialNumber);
model=string(device.Model);
fprintf('Camera model: %s \t Serial Number: %s \n', model, SN);
end
