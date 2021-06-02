clear all

Setup_LightField_Environment;
instance1=lfm(true);
exp=instance1.application.Experiment;
remove_all_added_devices(exp); %if any device added by default, remove

exp.SaveAs('BlankExp'); %save blank experiment

print_saved_experiments(exp); %list all saved experiments

instance1.close;

function remove_all_added_devices(experiment)
    count = experiment.ExperimentDevices.Count;
    for i=1:count
        fprintf('\tRemoving Added Device...\n');
        experiment.Remove(experiment.ExperimentDevices.Item(i-1));
    end
end

function print_saved_experiments(experiment)
    fprintf('My Saved Experiments:\n');
    count = experiment.GetSavedExperiments().Count;
    for i=1:count
        fprintf('\t%s\n',string(experiment.GetSavedExperiments().Item(i-1)));
    end
end