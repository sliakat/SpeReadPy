'''
Test script for generating fits files with static Fits method(s) in
read_spe package.
'''

from typing import List, Sequence, Tuple
import tkinter as tk
from tkinter import filedialog
from read_spe import Fits, SpeReference

def multi_file_select(*, title: str='',
    filter_str: List[Tuple[str, str]]=[('Any file', '*.*')]) -> Sequence[str]:
    '''
    optional input for a desired extension
    select multiple files from file selection dialog
    output list of paths to selected files
    '''
    root = tk.Tk()
    selected_filenames = filedialog.askopenfilenames(
        title=title,filetypes=filter_str)
    root.withdraw()
    return selected_filenames

if __name__ == "__main__":
    spe_files = multi_file_select(
        title='Select Spe file(s)', filter_str=[('LightField Data','*.spe')])
    for file in spe_files:
        spe = SpeReference(file)
        Fits.generate_fits_files(spe)
        #fits files should be created
