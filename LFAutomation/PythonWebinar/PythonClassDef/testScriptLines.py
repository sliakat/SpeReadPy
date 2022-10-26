'''
author: sliakat
notepad for line by line tests
'''

from LFAutomation import AutoClassNiche as ac

if __name__=="__main__":
    lf = ac()
    lf.NewInstance(expName='PM1')
    lf.Capture()
    lf.Capture()
    lf.Capture()
    lf.CloseInstance()