clear all

Setup_LightField_Environment;
data=struct;


instance1 = open_single_instance();
exp1=instance1.application.Experiment;
if exp1.IsReadyToRun
    fprintf('Acquiring image from first LightField instance...\n');
    data(1).data=acquire(instance1);
else
    fprintf('No camera found in instance 1.\n')
end

instance2 = open_single_instance();
exp2=instance2.application.Experiment;
if exp2.IsReadyToRun
    fprintf('Acquiring image from second LightField instance...\n');
    data(2).data=acquire(instance2);
else
    fprintf('No camera found in instance 2.\n')
end


instance1.close;
instance2.close;

function obj = open_single_instance()
    obj=lfm(true);
end