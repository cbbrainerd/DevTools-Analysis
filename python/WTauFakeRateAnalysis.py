#!/usr/bin/env python
import argparse
import logging
import sys

from DevTools.Analyzer.utilities import getTestFiles
from AnalysisBase import AnalysisBase
from leptonId import passWZLoose, passWZMedium, passWZTight, passHppLoose, passHppMedium, passHppTight
from utilities import ZMASS, deltaPhi, deltaR

from Candidates import *

import sys
import itertools
import operator

sys.argv.append('-b')
import ROOT
sys.argv.pop()

logger = logging.getLogger("WTauFakeRateAnalysis")
logging.basicConfig(level=logging.INFO, stream=sys.stderr, format='%(asctime)s.%(msecs)03d %(levelname)s %(name)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

class WTauFakeRateAnalysis(AnalysisBase):
    '''
    Select a muon + tau for fake rate in a W control region
    '''

    def __init__(self,**kwargs):
        outputFileName = kwargs.pop('outputFileName','WTauFakeRateTree.root')
        outputTreeName = kwargs.pop('outputTreeName','WTauFakeRateTree')
        super(WTauFakeRateAnalysis, self).__init__(outputFileName=outputFileName,outputTreeName=outputTreeName,**kwargs)

        # setup cut tree
        self.cutTree.add(self.trigger,'trigger')

        # setup analysis tree

        # chan string
        self.tree.add(self.getChannelString, 'channel', ['C',3])

        # trigger
        if self.version=='76X':
            self.tree.add(lambda cands: self.event.IsoMu20Pass(), 'pass_IsoMu20', 'I')
            self.tree.add(lambda cands: self.event.IsoTkMu20Pass(), 'pass_IsoTkMu20', 'I')
        else:
            self.tree.add(lambda cands: self.event.IsoMu22Pass(), 'pass_IsoMu22', 'I')
            self.tree.add(lambda cands: self.event.IsoTkMu22Pass(), 'pass_IsoTkMu22', 'I')
        self.tree.add(self.triggerEfficiency, 'triggerEfficiency', 'F')

        # lepton
        # mu tag
        self.addLeptonMet('wm')
        self.addLepton('m')
        self.tree.add(lambda cands: self.tightScale(cands['m']), 'm_tightScale', 'F')

        # tau probe
        self.addLeptonMet('wt')
        self.addLepton('t')
        self.tree.add(lambda cands: self.passMedium(cands['t']), 't_passMedium', 'I')
        self.tree.add(lambda cands: self.passTight(cands['t']), 't_passTight', 'I')
        self.tree.add(lambda cands: self.looseScale(cands['t']), 't_looseScale', 'F')
        self.tree.add(lambda cands: self.mediumScale(cands['t']), 't_mediumScale', 'F')
        self.tree.add(lambda cands: self.tightScale(cands['t']), 't_tightScale', 'F')

        # dilepton combination
        self.addDiLepton('z')

        # met
        self.addMet('met')

    #############################
    ### select fake candidate ###
    #############################
    def selectCandidates(self):
        candidate = {
            'm' : None,
            't' : None,
            'z' : None,
            'wm': None,
            'wt': None,
            'met': self.pfmet,
        }

        # get leptons
        leps = self.getPassingCands('Loose')
        muons = self.getCands(self.muons,self.passTight)
        loosemuons = self.getCands(self.muons,self.passLoose)
        taus = self.getCands(self.taus,self.passLoose)
        if len(muons)!=1: return candidate # need 1 tight muon
        if len(loosemuons)>1: return candidate # dont allow another loose muon
        if len(taus)<1: return candidate # need at least 1 tau 

        # get invariant masses
        bestT = ()
        bestPt = 0
        for zpair in itertools.permutations(leps,2):
            if zpair[0].collName!='muons': continue
            if zpair[1].collName!='taus': continue
            if zpair[0].pt()<25: continue
            if zpair[1].pt()<20: continue
            z = DiCandidate(*zpair)
            if z.deltaR()<0.5: continue
            pt = zpair[1].pt()
            if pt>bestPt:
                bestT = zpair
                bestPt = pt

        if not bestT: return candidate # need a z candidate

        z = bestT
        candidate['m'] = z[0]
        candidate['t'] = z[1]
        candidate['z'] = DiCandidate(z[0],z[1])
        candidate['wm'] = MetCompositeCandidate(self.pfmet,z[0])
        candidate['wt'] = MetCompositeCandidate(self.pfmet,z[1])


        return candidate


    ##################
    ### lepton IDs ###
    ##################
    def passLoose(self,cand):
        return passHppLoose(cand)

    def passMedium(self,cand):
        return passHppMedium(cand)

    def passTight(self,cand):
        return passHppTight(cand)

    def looseScale(self,cand):
        if isinstance(cand,Muon):       return self.leptonScales.getScale('MediumIDLooseIso',cand)
        elif isinstance(cand,Electron): return self.leptonScales.getScale('CutbasedVeto',cand)
        else:                           return 1.

    def mediumScale(self,cand):
        if isinstance(cand,Muon):       return self.leptonScales.getScale('MediumIDTightIso',cand)
        elif isinstance(cand,Electron): return self.leptonScales.getScale('CutbasedMedium',cand)
        else:                           return 1.

    def tightScale(self,cand):
        if isinstance(cand,Muon):       return self.leptonScales.getScale('MediumIDTightIso',cand)
        elif isinstance(cand,Electron): return self.leptonScales.getScale('CutbasedTight',cand)
        else:                           return 1.

    def getPassingCands(self,mode):
        if mode=='Loose':
            passMode = self.passLoose
        elif mode=='Medium':
            passMode = self.passMedium
        elif mode=='Tight':
            passMode = self.passTight
        else:
            return []
        cands = []
        for coll in [self.muons,self.taus]:
            cands += self.getCands(coll,passMode)
        return cands


    ######################
    ### channel string ###
    ######################
    def getChannelString(self,cands):
        '''Get the channel string'''
        chanString = 'mt'
        return chanString

    ###########################
    ### analysis selections ###
    ###########################
    def trigger(self,cands):
        # accept MC, check trigger for data
        if self.event.isData()<0.5: return True
        if self.version=='76X':
            triggerNames = {
                'SingleMuon'     : [
                    'IsoMu20',
                    'IsoTkMu20',
                ],
            }
        else:
            triggerNames = {
                'SingleMuon'     : [
                    'IsoMu22',
                    'IsoTkMu22',
                ],
            }
        # the order here defines the heirarchy
        # first dataset, any trigger passes
        # second dataset, if a trigger in the first dataset is found, reject event
        # so forth
        datasets = [
            'SingleMuon',
        ]
        # reject triggers if they are in another dataset
        # looks for the dataset name in the filename
        # for MC it accepts all
        reject = True if self.event.isData()>0.5 else False
        for dataset in datasets:
            # if we match to the dataset, start accepting triggers
            if dataset in self.fileNames[0]: reject = False
            for trigger in triggerNames[dataset]:
                var = '{0}Pass'.format(trigger)
                passTrigger = getattr(self.event,var)()
                if passTrigger>0.5:
                    # it passed the trigger
                    # in data: reject if it corresponds to a higher dataset
                    return False if reject else True
            # dont check the rest of data
            if dataset in self.fileNames[0]: break
        return False

    def triggerEfficiency(self,cands):
        candList = [cands['m']]
        triggerList = ['IsoMu20_OR_IsoTkMu20'] if self.version=='76X' else ['IsoMu22ORIsoTkMu22']
        return self.triggerScales.getDataEfficiency(triggerList,candList)

def parse_command_line(argv):
    parser = argparse.ArgumentParser(description='Run analyzer')

    parser.add_argument('--inputFiles', type=str, nargs='*', default=getTestFiles('w'), help='Input files')
    parser.add_argument('--inputFileList', type=str, default='', help='Input file list')
    parser.add_argument('--outputFile', type=str, default='wTauFakeRateTree.root', help='Output file')
    parser.add_argument('--shift', type=str, default='', choices=['','ElectronEnUp','ElectronEnDown','MuonEnUp','MuonEnDown','TauEnUp','TauEnDown','JetEnUp','JetEnDown','JetResUp','JetResDown','UnclusteredEnUp','UnclusteredEnDown'], help='Energy shift')

    return parser.parse_args(argv)

def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]

    args = parse_command_line(argv)

    dyAnalysis = WTauFakeRateAnalysis(
        outputFileName=args.outputFile,
        outputTreeName='WTauFakeRateTree',
        inputFileNames=args.inputFileList if args.inputFileList else args.inputFiles,
        inputTreeName='MiniTree',
        inputLumiName='LumiTree',
        inputTreeDirectory='miniTree',
        shift = args.shift,
    )

    try:
       dyAnalysis.analyze()
       dyAnalysis.finish()
    except KeyboardInterrupt:
       dyAnalysis.finish()

    return 0

if __name__ == "__main__":
    status = main()
    sys.exit(status)

