# SingleMuonAnalysis.py
# for WZ analysis

from AnalysisBase import AnalysisBase
from utilities import ZMASS, deltaPhi, deltaR
from leptonId import passHppLoose, passHppTight

import itertools
import operator

import ROOT

class SingleMuonAnalysis(AnalysisBase):
    '''
    single m analysis
    '''

    def __init__(self,**kwargs):
        outputFileName = kwargs.pop('outputFileName','mTree.root')
        outputTreeName = kwargs.pop('outputTreeName','MTree')
        super(SingleMuonAnalysis, self).__init__(outputFileName=outputFileName,outputTreeName=outputTreeName,**kwargs)

        # setup cut tree
        self.cutTree.add(self.oneLoose,'singleLooseLeptons')
        self.cutTree.add(self.trigger,'trigger')

        # setup analysis tree

        # event counts
        self.tree.add(lambda rtrow,cands: self.numJets(rtrow,'isLoose',30), 'numJetsLoose30', 'I')
        self.tree.add(lambda rtrow,cands: self.numJets(rtrow,'isTight',30), 'numJetsTight30', 'I')
        self.tree.add(lambda rtrow,cands: self.numJets(rtrow,'passCSVv2T',30), 'numBjetsTight30', 'I')
        self.tree.add(lambda rtrow,cands: len(self.getCands(rtrow,'electrons',self.passLoose)), 'numLooseElectrons', 'I')
        self.tree.add(lambda rtrow,cands: len(self.getCands(rtrow,'electrons',self.passTight)), 'numTightElectrons', 'I')
        self.tree.add(lambda rtrow,cands: len(self.getCands(rtrow,'muons',self.passLoose)), 'numLooseMuons', 'I')
        self.tree.add(lambda rtrow,cands: len(self.getCands(rtrow,'muons',self.passTight)), 'numTightMuons', 'I')

        # trigger
        self.tree.add(lambda rtrow,cands: self.getTreeVariable(rtrow,'Mu8_TrkIsoVVLPass'), 'pass_Mu8_TrkIsoVVL', 'I')
        self.tree.add(lambda rtrow,cands: self.getTreeVariable(rtrow,'Mu17_TrkIsoVVLPass'), 'pass_Mu17_TrkIsoVVL', 'I')
        self.tree.add(lambda rtrow,cands: self.getTreeVariable(rtrow,'Mu24_TrkIsoVVLPass'), 'pass_Mu24_TrkIsoVVL', 'I')
        self.tree.add(lambda rtrow,cands: self.getTreeVariable(rtrow,'Mu34_TrkIsoVVLPass'), 'pass_Mu34_TrkIsoVVL', 'I')
        self.tree.add(lambda rtrow,cands: self.getTreeVariable(rtrow,'IsoMu20Pass'), 'pass_IsoMu20', 'I')
        self.tree.add(lambda rtrow,cands: self.getTreeVariable(rtrow,'IsoTkMu20Pass'), 'pass_IsoTkMu20', 'I')

        self.addJet('leadJet')

        # w lepton
        self.addLeptonMet('w','l1',('pfmet',0))
        self.addLepton('l1')
        self.tree.add(lambda rtrow,cands: self.passTight(rtrow,cands['l1']), 'l1_passTight', 'I')

        # met
        self.addMet('met',('pfmet',0))

    ############################
    ### select WZ candidates ###
    ############################
    def selectCandidates(self,rtrow):
        candidate = {
            'l1' : (),
            'leadJet' : (),
        }

        # get leptons
        colls = ['muons']
        pts = {}
        p4s = {}
        charges = {}
        leps = []
        leps = self.getPassingCands(rtrow,'Loose')
        if len(leps)<1: return candidate

        for cand in leps:
            pts[cand] = self.getObjectVariable(rtrow,cand,'pt')
            p4s[cand] = self.getObjectVariable(rtrow,cand,'p4')
            charges[cand] = self.getObjectVariable(rtrow,cand,'charge')

        # sort by pt
        l1 = sorted(pts.items(), key=operator.itemgetter(1), reverse=True)[0][0]

        candidate['l1'] = l1

        # add jet
        jets = self.getCands(rtrow, 'jets', lambda rtrow,cand: self.getObjectVariable(rtrow,cand,'isLoose')>0.5)
        if len(jets)>0:
            candidate['leadJet'] = jets[0]
        else:
            candidate['leadJet'] = ('jets',-1)

        return candidate

    #################
    ### lepton id ###
    #################
    def passLoose(self,rtrow,cand):
        return passHppLoose(self,rtrow,cand)

    def passTight(self,rtrow,cand):
        return passHppTight(self,rtrow,cand)

    def getPassingCands(self,rtrow,mode):
        if mode=='Loose':
            passMode = self.passLoose
        elif mode=='Tight':
            passMode = self.passTight
        else:
            return []
        cands = []
        for coll in ['muons']:
            cands += self.getCands(rtrow,coll,passMode)
        return cands

    def numJets(self,rtrow,mode,pt):
        return len(
            self.getCands(
                rtrow,
                'jets',
                lambda rtrow,cand: self.getObjectVariable(rtrow,cand,mode)>0.5 
                                   and self.getObjectVariable(rtrow,cand,'pt')>pt
            )
        )

    ###########################
    ### analysis selections ###
    ###########################
    def oneLoose(self,rtrow,cands):
        return len(self.getPassingCands(rtrow,'Loose'))>=1

    def trigger(self,rtrow,cands):
        triggerNames = {
            'DoubleMuon'       : [
                'Mu8_TrkIsoVVL',
                'Mu17_TrkIsoVVL',
                'Mu24_TrkIsoVVL',
                'Mu34_TrkIsoVVL',
            ],
            'SingleMuon' : [
                'IsoMu20',
                'IsoTkMu20',
            ],
        }
        # the order here defines the heirarchy
        # first dataset, any trigger passes
        # second dataset, if a trigger in the first dataset is found, reject event
        # so forth
        datasets = [
            'DoubleMuon', 
            'SingleMuon',
        ]
        # reject triggers if they are in another dataset
        # looks for the dataset name in the filename
        # for MC it accepts all
        reject = True if rtrow.isData>0.5 else False
        for dataset in datasets:
            # if we match to the dataset, start accepting triggers
            if dataset in self.fileNames[0]: reject = False
            for trigger in triggerNames[dataset]:
                var = '{0}Pass'.format(trigger)
                passTrigger = self.getTreeVariable(rtrow,var)
                if passTrigger>0.5:
                    # it passed the trigger
                    # in data: reject if it corresponds to a higher dataset
                    return False if reject else True
            # dont check the rest of data
            if dataset in self.fileNames[0]: break
        return False











