from readSpe import SpeReference

file = 'C:\\Users\\sliakat\\OneDrive - Teledyne Technologies Inc\\MeetingsTrainings\\LunchAndLearn\\2022-Q2-Python\\02-OpenSpes\\TestMeta-MultiROI.spe'
spe = SpeReference(file)
print(spe.GetData(rois=[1]))
