'''
test script for generating fits files with static Fits method(s) in
readSpe.py
'''
from read_spe import(
    SpeReference,
    Fits
)
from astropy.io import fits
import tkinter as tk
from tkinter import filedialog

def MultiFileSelect(title: str='', filter: list[tuple]=[('Any file', '*.*')]) -> list[str]:
    '''
    optional input for a desired extension
    select multiple files from file selection dialog
    output list of paths to selected files
    '''
    root = tk.Tk()
    selected_filenames = filedialog.askopenfilenames(title=title,filetypes=filter)
    root.withdraw()
    return selected_filenames

if __name__ == "__main__":
    spe_files = MultiFileSelect(title='select spe file(s)', filter=[('LightField Data','*.spe')])
    for file in spe_files:
        spe = SpeReference(file)
        Fits.generate_fits_files(spe)
        #fits files should be created