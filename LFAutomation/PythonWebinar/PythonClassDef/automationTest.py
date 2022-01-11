# -*- coding: utf-8 -*-
"""
Created on Tue Jan 11 09:22:16 2022

@author: sliakat
"""

#Simple testing with LF.AutoClass
#will continue to expand with more functions

import LFAutomation
LF = LFAutomation.AutoClass()

LF.NewInstance(expName='ROITest')   #loads whatever experiment you pass in as expName
r = LF.GetCurrentROIs()
q = LF.Capture(numFrames = 100)     #list of numpy arrays: [region][frames,rows,cols]

#LF.CloseInstance()       #run when you want to dispose automation object