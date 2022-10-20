# -*- coding: utf-8 -*-
"""
Created on Tue Jan 11 09:22:16 2022

@author: sliakat
"""

#Simple testing with LF.AutoClass for specific things I need

from LFAutomation import AutoClassNiche as ac

inputDir = 'C:\\Users\\sabbi\\Documents\\Python\\Datasets\\SPECatDog\\spefiles-val\\'

LF = ac()

LF.NewInstance()   #loads whatever experiment you pass in as expName
LF.CombineSpes(inputDir, 'ValidationDataCombined.spe')

#LF.CloseInstance()       #run when you want to dispose automation object