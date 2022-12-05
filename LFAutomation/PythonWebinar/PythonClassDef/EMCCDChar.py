from LFAutomation import AutoClassNiche as ac

if __name__=="__main__":
    lf = ac()
    lf.NewInstance(expName='Evolve10Char')
    lf.EMCCDCharCurve(5, 200, '100x.csv')
    lf.CloseInstance()