# SpeReadPy

This repo is a hub for automation/ programming content involving Teledyne SciCam products. It started as a Python spe file reader, hence the repository name, but has since branched out into much more.

This root directory contains a package -- `read_spe` -- for an spe file reader that works on v3.0 (LightField) versions. Spe v2.x (WinSpec/32) files will work (only first ROI is parsed for legacy files).

To use the spe reader, import the package, construct the SpeReference object and call the methods -- it's that simple! The data will be returned as a list of 3-D numpy arrays, with each element of the list corresponding to a Region of Interest (ROI).

Metadata and other information can be found as properties of the `SpeReference` object.

------------------------
Example usage to read spe file content from 'file.spe':
>>> from read_spe import SpeReference
>>> spe = SpeReference('file.spe')
>>> data = spe.GetData(rois=[2], frames=[0,2])
- this will get data (list of numpy array) for frames 1 and 3 in roi #3 for file

Additionally, see the definition of `print_metadata` in `show_spe_mpl.py` for an example of how metadata can be extracted from the `SpeReference` onject.

Implementation examples (all contain main block and can be run as-is):
------------------------
`show_spe_mpl.py` is a script that uses matplotlib with the slider widget to visualize multi-frame images.  
  -the `read_spe.py` package is needed to parse the spe data  
  -when running, tk file dialog pops up asking the user to pick the file(s) they want to visualize  
  -can scroll through multi-frame images using slider widget  
  -boxes / spans can be selected for simple stats on images / line plots  
  -figures created for each ROI in the chosen file(s)  
  -console prints some file information that is helpful for quick reference  
  -memory efficient when compared to original version - image data only loaded for in-demand block on respective figure.  

------------------------
`test_fits_write.py` demonstrates the use of the Fits class to generate a fits file from an `SpeReference`.

------------------------
`grouped_frames_csv_export.py` shows how to utilize numpy and pandas libraries to group spectral (single-row) frame data together into a single
(continuous) matrix and write to an Excel spreadsheet. This type of export is currently not possible through LightField - this example was inspired
by a customer inquiry!

Feel free to suggest changes / create own branch if desired.
More ideas / examples of visualization welcome!

**IMPORTANT: This repo will also contain helpful miscellaneous scripts and tutorials for automation of Teledyne Princeton Instruments systems with PICam and LightField Automation. Please browse through the subfolders and review the READMEs for those folders!**

