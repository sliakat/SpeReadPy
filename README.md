# SpeReadPy
Python spe file reader, works on v3.0 (LightField) versions. Spe v2.0 (WinSpec/32) compatibility may be added in at some point.

readSpe.py contains code that will load the relevant content from a given spe file.
- Added a class based reference to the spe file that allows for extraction of only needed data
- example usage:
- spe = SpeReference(file)
- data = spe.GetData(rois=[2], frames=[0,2])
- this will get data (list of numpy array) for frames 1 and 3 in roi #3 for file

showSpeMPL.py is a script that uses matplotlib with the slider widget to visualize multi-frame images.
  -script contains main block, so can run as-is
  -the readSpe.py file uploaded here is needed to parse the spe data
  -when running, tk file dialog pops up asking you to pick the file(s) you want to visualize
  -can scroll through multi-frame images using slider widget
  -boxes / spans can be selected for simple stats on images / line plots
  -figures created for each ROI in the chosen file(s)
  -console prints some file information that is helpful for quick reference
  -memory efficient when compared to original version - image data only loaded for in-demand block on respective figure.

Example output of showSpeMPL.py:

**Information for TestCal-MultiROI.spe**
LF version used:        6.15.2.2201
Spectrograph model: ISO-160
        SN: 16010192
Camera model: PIXIS: 400B eXcelon
        SN: 05579519
Camera sensor:          E2V 1340 x 400 (CCD 36)(B)(eXcelon)
Pixel width:            20um
Temperature:            -70C, Status: Locked
Clean Serial Reg:       True
Exposure Time:          50 ms
Shutter Mode:           Normal
Readout Mode:           FullFrame
Readout Time:           226.606 ms
Vertical Shift:         15.2us
ADC Speed:                      2 MHz
Analog Gain:            High
ADC Quality:            LowNoise
Frame Rate:                     3.514 fps
Grating:                        [800nm,150][2][0], CWL: 960.956 nm
Calibration(s):         Wavelength (Broadband)
2 region(s):
        ROI 01: 224 x 200, xbin 1, ybin 1
        ROI 02: 617 x 106, xbin 1, ybin 1


Feel free to suggest changes / create own branch if desired.
More ideas / examples of visualization welcome!

**IMPORTANT: This repo will also contain helpful miscellaneous scripts and tutorials for automation of Teledyne Princeton Instruments systems with PICam and LightField Automation. Please browse through the subfolders and review the READMEs for those folders!**

