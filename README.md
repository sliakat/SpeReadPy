# SpeReadPy
Python spe file reader, works on v2.0 (WinSpec/32) and v3.0 (LightField) versions.

readSpe.py is the function that will load the relevant content from a given spe file.

showSpeTK.py is a script that uses matplotlib w/ TK backend to visualize images.
  -script contains main function, so can run as-is (provided you have the needed libraries and set graphics backend to Tk (%gui tk))
    -the readSpe.py function uploaded here is needed to parse the spe data
  -when running, tk file dialog pops up asking you to pick the file(s) you want to visualize
  -can scroll through multi-frame images using slider widget
  -boxes / spans can be selected for simple stats on images / line plots
  -currently works for region of interest #0

visualizeSpe.py is an example of how to load and visualize the data using pyplot

showSpe.py is a function that allows the operations done in the visualizeSpe.py script to be called from another script -- 1 line gets you a plot, xml, fig handle, and WL cal (if it exists in the spe).

readSpe takes a file path (including filename) as a string. It then outputs spe file content (data, xml footer, wavelength cal if [if applicable]) to a dataContainer class (defined in the readSpe.py file).

dataContainer.data will always exist, and it will be a list of numpy arrays. Each element of the list corresponds to a region of interest.
dataContainer.xmlFooter will exist in the case of an spe3.0 file.
dataContainer.wavelengths (wavelength calibration in x-axis) will exist if the data was taken with a calibrated detector + spectrometer combo in LightField.

Feel free to suggest changes / create own branch if desired.
More ideas / examples of visualization welcome!

**IMPORTANT: This repo will also contain helpful miscellaneous scripts and tutorials for automation of Teledyne Princeton Instruments systems with PICam and LightField Automation. Please browse through the subfolders and review the READMEs for those folders!**

