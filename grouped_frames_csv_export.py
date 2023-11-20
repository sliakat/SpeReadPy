"""Test module for exporting multi-frame spectral data into a
single grid. A spe file is input and a .xlsx Excel worksheet is
output to the present working directory.

If the spe data contains a wavelength calibration,
it will be extracted from the `SpeReference` object and used as
column headers in the exported spreadsheet.

The frame data in the spe file must be spectral -- i.e. 1 row only.

Uses numpy, openpyxl, and pandas external libraries.
"""

import numpy as np
from pandas import DataFrame as df
from read_spe import SpeReference

if __name__ == '__main__':
    #TODO: Replace 'Sample1.spe' with a path to your spe file.
    spe_ref = SpeReference('Sample1.spe')
    # validate we have 1-D data
    data_height = int(spe_ref.roi_list[0].height
        / spe_ref.roi_list[0].ybin)
    if data_height != 1:
        raise ValueError('Must have 1-D frame data in spe file.')
    # initialize new array of shape [Frames, Cols]
    data_width = int(spe_ref.roi_list[0].width
        / spe_ref.roi_list[0].xbin)
    new_np_array = np.zeros([spe_ref.num_frames, data_width])
    # loop through frames
    for i in range(0, spe_ref.num_frames):
        # get spe data of ith frame, 1st ROI, 1st row
        # (there should only be one row)
        new_np_array[i,:] = spe_ref.get_data(frames=[i])[0][0]
    # construct a pandas dataframe and write it to excel
    if not spe_ref.get_wavelengths():
        df(new_np_array).to_excel(f'{spe_ref.file_name}.xlsx')
    else:
        # if wavelength calibration exists in the spe file,
        # use those as the column headers
        df(new_np_array, columns=spe_ref.get_wavelengths()[0]
            ).to_excel(f'{spe_ref.file_name}.xlsx')
