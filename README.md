# SpeReadPy
Python spe file reader, works on v2.0 (WinSpec/32) and v3.0 (LightField) versions.

readSpe.py is the function that will load the relevant content from a given spe file.
- Added a class based reference to the spe file that allows for extraction of only needed data
- example usage:
- spe = SpeReference(file)
- data = spe.GetData(rois=[2], frames=[0,2])
- this will get data (list of numpy array) for frames 1 and 3 in roi #3 for file

showSpeMPL.py is a script that uses matplotlib with the slider widget to visualize multi-frame images.
  -script contains main function, so can run as-is
  -the readSpe.py function uploaded here is needed to parse the spe data
  -when running, tk file dialog pops up asking you to pick the file(s) you want to visualize
  -can scroll through multi-frame images using slider widget
  -boxes / spans can be selected for simple stats on images / line plots
  -need to specify the desired ROI in parseSpe; will work for multiple ROIs
  -console prints some file information that is helpful for quick reference

showSpeTK.py is a script that uses matplotlib w/ TK backend to visualize images.
  -need to set graphics backend to Tk (%gui tk)
  -sliders will work for multiple files (unlike in spowSpeMPL where the sliders can't seem to connect to multiple figs in the same kernel).
  -did not add spe xml parsing -- can just copy function from showSpeMPL.py if so desired

readSpe takes a file path (including filename) as a string. It then outputs spe file content (data, xml footer, wavelength cal if [if applicable]) to a dataContainer class (defined in the readSpe.py file).

dataContainer.data will always exist, and it will be a list of numpy arrays. Each element of the list corresponds to a region of interest.
dataContainer.xmlFooter will exist in the case of an spe3.0 file.
dataContainer.wavelengths (wavelength calibration in x-axis) will exist if the data was taken with a calibrated detector + spectrometer combo in LightField.

Feel free to suggest changes / create own branch if desired.
More ideas / examples of visualization welcome!

**IMPORTANT: This repo will also contain helpful miscellaneous scripts and tutorials for automation of Teledyne Princeton Instruments systems with PICam and LightField Automation. Please browse through the subfolders and review the READMEs for those folders!**

