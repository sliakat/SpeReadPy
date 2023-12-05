"""Spe reader package
-----

Spe file reader that works on v3.0 (LightField) versions.
Spe v2.x (WinSpec/32) files will work (only first ROI is parsed
for legacy files).

To use the spe reader, import the package, construct the SpeReference object
and call the methods -- it's that simple! The data will be returned as a list
of 3-D numpy arrays, with each element of the list corresponding to a
Region of Interest (ROI).

Metadata and other information can be found as properties of the
`SpeReference` object.

------------------------
Example usage to read spe file content from 'file.spe':
>>> from read_spe import SpeReference
>>> spe = SpeReference('file.spe')
>>> data = spe.GetData(rois=[2], frames=[0,2])
- this will get data (list of numpy array) for frames 1 and 3
in roi 3 for file

Notes
----
The astropy (`pip install astropy`) library is required for using the fits
writing module.
"""

from .read_spe import (ExperimentSetting, FrameTrackingNumber, GateTracking,
    ImageNdArray, SpeReference, TimeStamp)
from .fits import Fits
