"""Module to assist with writing of fits files containing data
and select header information from a given `SpeReference` object.

**REQUIRES ASTROPY: pip install astropy**
-----
"""

from pathlib import Path
import numpy as np
from .read_spe import (ExperimentSetting, SpeReference, TimeStamp, _Unit)

class Fits():
    """Container for static methods `generate_fits_file` and
    `generate_fits_files`.

    - `generate_fits_file` creates a fits file using the astropy library.
    One file (multi-frame) is generated per ROI. Select experiment
    information is passed in, but per-frame metadata is NOT. If per-frame
    metadata is needed, please use `generate_fits_files`.
    """
    @staticmethod
    def generate_fits_file(spe_ref: SpeReference) -> None:
        """**REQUIRES ASTROPY LIBRARY**
        
        Generate a fits file (per ROI) using astropy library.
        Select experiment settings from the spe file's xml footer
        are carried over to the fits header. For a list of these select
        settings, please reference the docstring for
        `read_spe.SpeReference.retrieve_experiment_settings`.

        One file is generated per ROI (these files can thus be multi-frame).
        As such, per-frame metadata not included -- please use
        GenerateFitsFiles if per-frame metadata needs to be exported.

        ----------------------------------------------------------------------
        Input:
        ----------------------------------------------------------------------
        - `spe_ref`: `SpeReference` object containing the information from the
        spe file that will be used to generate fits.
        ----------------------------------------------------------------------
        Exceptions:
        ----------------------------------------------------------------------
        - `ImportError`: The Python runtime will raise this if astropy cannot
        be imported.
        ----------------------------------------------------------------------
        See Also:
        ----------------------------------------------------------------------
        - `read_spe.Fits.generate_fits_files`
        - `read_spe.SpeReference.retrieve_experiment_settings`
        """
        for region in spe_ref.roi_list:
            if region.height < 1 or region.width < 1:
                raise ValueError(
                    'One or more region(s) of the spe file do not have'
                    ' valid data.')
        if spe_ref.spe_version >= 3:
            datatype: np.dtype = spe_ref.dataTypes[
                spe_ref.pixel_format_key]# type: ignore
        else:
            datatype: np.dtype = spe_ref.dataTypes_old_spe[
                spe_ref.pixel_format_key]# type: ignore
        from astropy.io import fits
        for idx_roi, roi in enumerate(spe_ref.roi_list):
            output_filepath = '%s\\%s-ROI%03d.fits'%(
                spe_ref.file_directory, spe_ref.file_name, idx_roi+1)
            region_data = np.zeros(
                [spe_ref.num_frames, roi.height, roi.width], dtype=datatype)
            for j in range(0, spe_ref.num_frames):
                region_data[j] = spe_ref.get_data(rois=[idx_roi],
                    frames=[j])[0]
            hdu = fits.PrimaryHDU(region_data)
            hdr = hdu.header
            #append experiment settings list to header
            experiment_settings_seq =\
                spe_ref.retrieve_all_experiment_settings()
            bin_settings_seq = (ExperimentSetting('X_BIN',
                np.int64(roi.xbin), np.int64, _Unit.NONE),
                ExperimentSetting('Y_BIN', np.int64(roi.ybin),
                                  np.int64, _Unit.NONE))
            assert isinstance(experiment_settings_seq, tuple)
            for setting in experiment_settings_seq + bin_settings_seq:
                hdr['HIERARCH %s'%(setting.setting_name)] =\
                    setting.setting_value
            hdu.writeto(output_filepath, overwrite=True)

    @staticmethod
    def generate_fits_files(spe_ref:SpeReference) -> None:
        """**REQUIRES ASTROPY LIBRARY**
        
        Generates fits file(s) per frame per ROI in a subdirectory created
        in the spe file's location. Select experiment settings from the spe
        file's xml footer are carried over to the fits header. For a list of
        these select settings, please reference the docstring for
        `read_spe.SpeReference.retrieve_experiment_settings`.

        Frame metadata for exposure started timestamp will be present in the
        header of each file (if exists in the spe file).

        ----------------------------------------------------------------------
        Input:
        ----------------------------------------------------------------------
        - `spe_ref`: `SpeReference` object containing the information from the
        spe file that will be used to generate fits.
        ----------------------------------------------------------------------
        Exceptions:
        ----------------------------------------------------------------------
        - `ImportError`: The Python runtime will raise this if astropy cannot
        be imported.
        ----------------------------------------------------------------------
        See Also:
        ----------------------------------------------------------------------
        - `read_spe.Fits.generate_fits_file`
        - `read_spe.SpeReference.retrieve_experiment_settings`
        """
        for region in spe_ref.roi_list:
            if region.height < 1 or region.width < 1:
                raise ValueError('One or more region(s) of the'
                    ' spe file do not have valid data.')
        from astropy.io import fits
        new_folder_path = Path('%s\\%s-fits\\'%(spe_ref.file_directory,
            spe_ref.file_name))
        if not new_folder_path.exists():
            new_folder_path.mkdir()
        for idx_roi, roi in enumerate(spe_ref.roi_list):
            for j in range(0, spe_ref.num_frames):
                output_filepath = '%s\\%s-ROI%03d-Frame%04d.fits'%(
                    new_folder_path, spe_ref.file_name, idx_roi+1, j+1)
                file_data = spe_ref.get_data(rois=[idx_roi], frames=[j])[0]
                frame_metadata = spe_ref.get_frame_metadata_value([j])[0]
                hdu = fits.PrimaryHDU(file_data)
                hdr = hdu.header
                #add time stamps to header if they exist
                if spe_ref.meta_list:
                    count = 0
                    for meta in spe_ref.meta_list:
                        if isinstance(meta, TimeStamp):
                            if meta.meta_event == 'ExposureStarted':
                                hdr['HIERARCH ACQUISITION_ORIGIN']\
                                    = meta.absolute_time
                                hdr[
                                'HIERARCH FRAME_EXPOSURE_STARTED_OFFSET_MS']\
                                    = frame_metadata[count]
                        count += 1
                #append experiment settings list to header
                experiment_settings_seq\
                    = spe_ref.retrieve_all_experiment_settings()
                bin_settings_seq = (ExperimentSetting('X_BIN',
                np.int64(roi.xbin), np.int64, _Unit.NONE),
                ExperimentSetting('Y_BIN', np.int64(roi.ybin),
                                  np.int64, _Unit.NONE))
                assert isinstance(experiment_settings_seq, tuple)
                for setting in experiment_settings_seq + bin_settings_seq:
                    hdr['HIERARCH %s'%(setting.setting_name)]\
                        = setting.setting_value
                hdu.writeto(output_filepath, overwrite=True)
