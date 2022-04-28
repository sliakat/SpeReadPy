%test the built mex function
%the test runs on the first PI camera that is connected to the PC
%picamMex(0) initializes PICam and opens the camera
%picamMex(1) calls an Acquire of 1 and brings the raw data array into
%MATLAB (row,col) dimensions
%picamMex(2) closes the camera and uninitializes PICam

numLoops = 20;  %start with a small number to make sure the program is working the way you expect

errOpen = picamMex(0);
if errOpen==0
    for i = 1:numLoops
        [errAcq,outData] = picamMex(1);
        fprintf('Loop number %d, Acquisition error %d\n',i,errAcq);
        %add code here to perform operations before the next acquire
    end
end
errClose = picamMex(2);