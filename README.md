# SpeReadPy
Python spe file reader, works on v2.0 (WinSpec/32) and v3.0 (LightField) versions.

readSpe.py is the function that will load the relevant content from a given spe file.
visualizeSpe.py is an example of how to load and visualize the data using pyplot

readSpe takes a file path (including filename) as a string. It then outputs spe file content (data, xml footer, wavelength cal if [if applicable]) to a dataContainer class (defined in the readSpe.py file).

dataContainer.data will always exist, and it will be a list of numpy arrays. Each element of the list corresponds to a region of interest.
dataContainer.xmlFooter will exist in the case of an spe3.0 file.
dataContainer.wavelengths (wavelength calibration in x-axis) will exist if the data was taken with a calibrated detector + spectrometer combo in LightField.

Feel free to suggest changes / create own branch if desired.
More ideas / examples of visualization welcome!

This repo will also contain helpful miscellaneous scripts and tutorials for automation of Teledyne Princeton Instruments systems with PICam and LightField Automation.
