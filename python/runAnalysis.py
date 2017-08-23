#!/usr/bin/env python

# import run script
from DevTools.Analyzer.WZAnalysis import main as runWZ
from DevTools.Analyzer.ZZAnalysis import main as runZZ
from DevTools.Analyzer.DYAnalysis import main as runDY
from DevTools.Analyzer.ZFakeRateAnalysis import main as runZFakeRate
from DevTools.Analyzer.ChargeAnalysis import main as runCharge
from DevTools.Analyzer.TauChargeAnalysis import main as runTauCharge
from DevTools.Analyzer.Hpp3lAnalysis import main as runHpp3l
from DevTools.Analyzer.Hpp4lAnalysis import main as runHpp4l
from DevTools.Analyzer.DijetFakeRateAnalysis import main as runDijetFakeRate
from DevTools.Analyzer.WTauFakeRateAnalysis import main as runWTauFakeRate
from DevTools.Analyzer.WGFakeRateAnalysis import main as runWGFakeRate
from DevTools.Analyzer.WFakeRateAnalysis import main as runWFakeRate
from DevTools.Analyzer.ElectronAnalysis import main as runElectron
from DevTools.Analyzer.MuonAnalysis import main as runMuon
from DevTools.Analyzer.TauAnalysis import main as runTau
from DevTools.Analyzer.TriggerCountAnalysis import main as runTriggerCount
from DevTools.Analyzer.ThreeLeptonAnalysis import main as runThreeLepton
from DevTools.Analyzer.FourPhotonAnalysis import main as runFourPhoton
from DevTools.Analyzer.ThreePhotonAnalysis import main as runThreePhoton
from DevTools.Analyzer.TwoPhotonAnalysis import main as runTwoPhoton
from DevTools.Analyzer.EGAnalysis import main as runEG
from DevTools.Analyzer.DYGGAnalysis import main as runDYGG
from DevTools.Analyzer.MMGAnalysis import main as runMMG

analysisFunctionDict={
    'WZ':runWZ,
    'ZZ':runZZ,
    'DY':runDY,
    'ZFakeRate':runZFakeRate,
    'Charge':runCharge,
    'TauCharge':runTauCharge,
    'Hpp3l':runHpp3l,
    'Hpp4l':runHpp4l,
    'DijetFakeRate':runDijetFakeRate,
    'WTauFakeRate':runWTauFakeRate,
    'WFakeRate':runWFakeRate,
    'Electron':runElectron,
    'Muon':runMuon,
    'Tau':runTau,
    'TriggerCount':runTriggerCount,
    'ThreeLepton':runThreeLepton,
    'FourPhoton':runFourPhoton,
    'ThreePhoton':runThreePhoton,
    'TwoPhoton':runTwoPhoton,
    'EG':runEG,
    'DYGG':runDYGG,
    'MMG':runMMG,
    'WGFakeRate':runWGFakeRate
}

def runAnalysis(analysis,argv):
    '''Return analysis function'''
    try:
        func=analysisFunctionDict[analysis]
    except KeyError:
        return 0

    return func(argv)

