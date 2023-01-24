from readSpe import SpeReference
from SLPlots import PlotNumpy
import tkinter as tk
from tkinter import filedialog

root = tk.Tk()
file = filedialog.askopenfilename(title='Select Spe File',filetypes=[('spe files','*.spe'),('spe files','*.SPE')])
root.withdraw()

spe = SpeReference(file)
data = spe.GetData(rois=[], frames=[])
for item in data:
    PlotNumpy(item,file)
print(spe.GetWavelengths()[0])
