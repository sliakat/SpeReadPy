# SpeReadPy
Python spe file reader, works on v3.0 (LightField) versions. Spe v2.x (WinSpec/32) files will work (only first ROI is parsed for legacy files.)

------------------------
read_spe.py contains code that will load the relevant content from a given spe file.  
- Added a class based reference to the spe file that allows for extraction of only needed data
- example usage:  
`spe = SpeReference(file)`  
`data = spe.GetData(rois=[2], frames=[0,2])`  
- this will get data (list of numpy array) for frames 1 and 3 in roi #3 for file

------------------------
show_spe_mpl.py is a script that uses matplotlib with the slider widget to visualize multi-frame images.  
  -script contains main block, so can run as-is  
  -the `read_spe.py` file uploaded here is needed to parse the spe data  
  -when running, tk file dialog pops up asking you to pick the file(s) you want to visualize  
  -can scroll through multi-frame images using slider widget  
  -boxes / spans can be selected for simple stats on images / line plots  
  -figures created for each ROI in the chosen file(s)  
  -console prints some file information that is helpful for quick reference  
  -memory efficient when compared to original version - image data only loaded for in-demand block on respective figure.  

------------------------

Feel free to suggest changes / create own branch if desired.
More ideas / examples of visualization welcome!

**IMPORTANT: This repo will also contain helpful miscellaneous scripts and tutorials for automation of Teledyne Princeton Instruments systems with PICam and LightField Automation. Please browse through the subfolders and review the READMEs for those folders!**

