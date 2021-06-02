clear all

Setup_LightField_Environment;
instance1=lfm(true);

exp=instance1.application.Experiment;

if exp.AvailableDevices.Count == 0 && exp.ExperimentDevices.Count == 0
    fprintf('Device not found. Please add a device and try again.\n');
else
    devAdded=add_available_devices(exp,exp.AvailableDevices.Count);
    remove_added_devices(exp,devAdded);
end

instance1.close();

function devices = add_available_devices(experiment,count)
    for i=1:count
        fprintf('\tAdding Device...\n');
        experiment.Add(experiment.AvailableDevices.Item(i-1));
    end
    devices=experiment.ExperimentDevices.Count;
end

function remove_added_devices(experiment,count)
    for i=1:count
        fprintf('\tRemoving Device...\n');
        experiment.Remove(experiment.ExperimentDevices.Item(i-1));
    end
end
