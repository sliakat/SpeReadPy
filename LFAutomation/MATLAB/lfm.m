classdef (ConstructOnLoad = true) lfm
    properties (Access = public)
        automation;
        addinbase;
        application;
        experiment;
    end
    methods
        function out = lfm(visible)
            empStr=NET.createGeneric('System.Collections.Generic.List',{'System.String'},0);
            out.addinbase = PrincetonInstruments.LightField.AddIns.AddInBase();
            out.automation = PrincetonInstruments.LightField.Automation.Automation(visible,empStr);
            out.application = out.automation.LightFieldApplication;
            out.experiment = out.application.Experiment;
            
        end
    	function close(obj)
			obj.automation.Dispose();
        end
        function set(obj,setting,value)
            if obj.experiment.Exists(setting)
                if obj.experiment.IsValid(setting,value)
                    obj.experiment.SetValue(setting,value);
                else 
                    disp('value not valid')
                end
            else
                disp('operation not found/defined');
            end
        end
        function return_value = get(obj,setting)
            if obj.experiment.Exists(setting)
                return_value = obj.experiment.GetValue(setting);
            end
        end
        function load_experiment(obj,value)
            obj.experiment.Load(value);
        end
        function set_exposure(obj,value)
            obj.set(PrincetonInstruments.LightField.AddIns.CameraSettings.ShutterTimingExposureTime,value);
        end
        function set_frames(obj,value)
            obj.set(PrincetonInstruments.LightField.AddIns.ExperimentSettings.FrameSettingsFramesToStore,value);
        end
        function [data, wavelength] = acquire(obj)
            import System.IO.FileAccess;
            obj.experiment.Acquire();
            accessed_wavelength = 0;
            
            while obj.experiment.IsRunning % During acquisition...
                % Case where wavelength is empty
                if accessed_wavelength == 0 && isempty(obj.experiment.SystemColumnCalibration)
                    fprintf('Wavelength information not available\n');
                    wavelength = [];
                    accessed_wavelength = 1;
                elseif accessed_wavelength == 0
                    wavelen_len = obj.experiment.SystemColumnCalibration.Length;
                    assert(wavelen_len >= 1);
                    wavelength = zeros(wavelen_len, 1);
                    for i = 0:wavelen_len-1 % load wavelength info directly from LightField instance
                        wavelength(i+1) = obj.experiment.SystemColumnCalibration.Get(i);
                    end
                    accessed_wavelength = 1;
                end
            end
            
            lastfile = obj.application.FileManager.GetRecentlyAcquiredFileNames.GetItem(0);
			imageset = obj.application.FileManager.OpenFile(lastfile,FileAccess.Read);
            
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
    end
end

