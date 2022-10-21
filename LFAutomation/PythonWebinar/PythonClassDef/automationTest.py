# -*- coding: utf-8 -*-
"""
Created on Tue Jan 11 09:22:16 2022

@author: sliakat
"""

#Simple testing with LF.AutoClass for specific things I need

from LFAutomation import AutoClassNiche as ac

inputDir = 'C:\\Users\\sliakat\\OneDrive - Teledyne Technologies Inc\\SLSandbox\\Python\\GeneralDatasets\\SNRExample\\'

LF = ac()

LF.NewInstance()   #loads whatever experiment you pass in as expName
LF.CombineSpes(inputDir, 'SNRTestDataCombined.spe', frames=[0,1])

#LF.CloseInstance()       #run when you want to dispose automation object