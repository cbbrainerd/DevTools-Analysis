# AnalysisBase.py

import logging
import os
import sys
import math
import time

sys.argv.append('-b')
import ROOT
sys.argv.pop()
from array import array

from CutTree import CutTree
from AnalysisTree import AnalysisTree

from PileupWeights import PileupWeights
from FakeRates import FakeRates
from LeptonScales import LeptonScales
from TriggerScales import TriggerScales
from TriggerPrescales import TriggerPrescales
from ZptGenWeight import ZptGenWeight
from ZZGenWeight import ZZGenWeight

from utilities import deltaR, deltaPhi
from DevTools.Utilities.utilities import getCMSSWVersion
from Candidates import *
from leptonId import passHppLoose, passHppMedium, passHppTight
from photonId import passPhoton, passPreselection, passPreselectionNoElectronVeto, passElectronVeto

try:
    from progressbar import ProgressBar, ETA, Percentage, Bar, SimpleProgress
    hasProgress = False
except:
    hasProgress = False

class AnalysisBase(object):
    '''
    Analysis Tree
    '''

    def __init__(self,**kwargs):
        inputFileNames = kwargs.pop('inputFileNames',[])
        inputTreeDirectory = kwargs.pop('inputTreeDirectory','miniTree')
        inputTreeName = kwargs.pop('inputTreeName','MiniTree')
        inputLumiName = kwargs.pop('inputTreeName','LumiTree')
        outputFileName = kwargs.pop('outputFileName','analysisTree.root')
        outputTreeName = kwargs.pop('outputTreeName','AnalysisTree')
        self.shift = kwargs.pop('shift','')
        self.outputTreeName = outputTreeName
        if hasProgress:
            self.pbar = kwargs.pop('progressbar',ProgressBar(widgets=['{0}: '.format(outputTreeName),' ',SimpleProgress(),' events ',Percentage(),' ',Bar(),' ',ETA()]))
        # preselection
        if not hasattr(self,'preselection'): self.preselection = '1'
        # input files
        self.fileNames = []
        if os.path.isfile('PSet.py'):                # grab input files from crab pset
            import PSet
            self.fileNames = list(PSet.process.source.fileNames)
        elif isinstance(inputFileNames, basestring): # inputFiles is a file name
            if os.path.isfile(inputFileNames):       # single file
                if inputFileNames[-4:] == 'root':    # file is a root file
                    self.fileNames += [inputFileNames]
                else:                                # file is list of files
                    with open(inputFileNames,'r') as f:
                        for line in f:
                            self.fileNames += [line.strip()]
        else:
            self.fileNames = inputFileNames          # already a python list or a cms.untracked.vstring()
        if not isinstance(outputFileName, basestring): # its a cms.string(), get value
            outputFileName = outputFileName.value()
        # test for hdfs
        #self.hasHDFS = os.path.exists('/hdfs/store/user')
        self.hasHDFS = False
        # input tchain
        self.treename = '{0}/{1}'.format(inputTreeDirectory,inputTreeName)
        luminame = '{0}/{1}'.format(inputTreeDirectory,inputLumiName)
        #tchainLumi = ROOT.TChain(luminame)
        self.totalEntries = 0
        self.numLumis = 0
        self.numEvents = 0
        self.summedWeights = 0
        logging.info('Getting Lumi information')
        #self.skims = {}
        for f,fName in enumerate(self.fileNames):
            if fName.startswith('/store'): fName = '{0}/{1}'.format('/hdfs' if self.hasHDFS else 'root://cmsxrootd.hep.wisc.edu/',fName)
            tfile = ROOT.TFile.Open(fName)
            tree = tfile.Get(self.treename)
            #skimName = 'skim{0}'.format(f)
            #tree.Draw('>>{0}'.format(skimName),self.preselection,'entrylist')
            #skimlist = ROOT.gDirectory.Get(skimName)
            #listEvents = skimlist.GetN()
            #self.skims[f] = skimlist
            #self.totalEntries += listEvents
            self.totalEntries += tree.GetEntries()
            if not hasattr(self,'version'):
                tree.GetEntry(1)
                if hasattr(tree,'provenance'):
                    ver = tree.provenance[0].split('_')
                    self.version = ''.join([ver[1],ver[2],'X'])
                else:
                    self.version = getCMSSWVersion()
            lumitree = tfile.Get(luminame)
            for entry in lumitree:
                self.numLumis += 1
                self.numEvents += lumitree.nevents
                self.summedWeights += lumitree.summedWeights
            tfile.Close('R')
            #tchainLumi.Add(fName)
        # get the lumi info
        #self.numLumis = tchainLumi.GetEntries()
        #self.numEvents = 0
        #self.summedWeights = 0
        #for entry in xrange(self.numLumis):
        #    tchainLumi.GetEntry(entry)
        #    self.numEvents += tchainLumi.nevents
        #    self.summedWeights += tchainLumi.summedWeights
        logging.info('Analysis is running with version {0}'.format(self.version))
        logging.info("Will process {0} lumi sections with {1} events ({2}).".format(self.numLumis,self.numEvents,self.summedWeights))
        self.flush()
        if not len(self.fileNames): raise Exception
        # other input files
        self.pileupWeights = PileupWeights(self.version)
        self.fakeRates = FakeRates(self.version)
        self.leptonScales = LeptonScales(self.version)
        self.triggerScales = TriggerScales(self.version)
        self.triggerPrescales = TriggerPrescales(self.version)
        self.zptGenWeight = ZptGenWeight(self.version)
        self.zzGenWeight = ZZGenWeight(self.version)
        # tfile
        self.outfile = ROOT.TFile(outputFileName,"recreate")
        # cut tree
        self.cutTree = CutTree()
        # analysis tree
        self.tree = AnalysisTree(outputTreeName)
        self.eventsStored = 0

        # some things we always need:

        dysamples = [
            'DY1JetsToLL_M-50_TuneCUETP8M1_13TeV-madgraphMLM-pythia8',
            'DY2JetsToLL_M-50_TuneCUETP8M1_13TeV-madgraphMLM-pythia8',
            'DY3JetsToLL_M-50_TuneCUETP8M1_13TeV-madgraphMLM-pythia8',
            'DY4JetsToLL_M-50_TuneCUETP8M1_13TeV-madgraphMLM-pythia8',
            'DYJetsToLL_M-10to50_TuneCUETP8M1_13TeV-madgraphMLM-pythia8',
            'DYJetsToLL_M-50_TuneCUETP8M1_13TeV-madgraphMLM-pythia8',
        ]

        qqzzsamples = [
            'ZZTo4L_13TeV_powheg_pythia8',
            'ZZTo4L_13TeV-amcatnloFXFX-pythia8',
        ]

        # pileup
        self.tree.add(lambda cands: self.pileupWeights.weight(self.event)[0], 'pileupWeight', 'F')
        self.tree.add(lambda cands: self.pileupWeights.weight(self.event)[1], 'pileupWeightUp', 'F')
        self.tree.add(lambda cands: self.pileupWeights.weight(self.event)[2], 'pileupWeightDown', 'F')
        self.tree.add(lambda cands: self.event.vertices_count(), 'numVertices', 'I')
        self.tree.add(lambda cands: self.event.rho(), 'rho', 'F')

        # gen
        self.tree.add(lambda cands: self.event.nTrueVertices(), 'numTrueVertices', 'I')
        self.tree.add(lambda cands: self.event.NUP(), 'NUP', 'I')
        self.tree.add(lambda cands: self.event.isData(), 'isData', 'I')
        self.tree.add(lambda cands: self.event.genWeight(), 'genWeight', 'F')
        if any([x in fName for x in dysamples]):
            self.tree.add(lambda cands: self.zptGenWeight.weight(self.gen), 'zPtWeight', 'F')
        if any([x in fName for x in qqzzsamples]):
            self.tree.add(lambda cands: self.zzGenWeight.weight(self.gen), 'qqZZkfactor', 'F')
        self.tree.add(lambda cands: self.event.numGenJets(), 'numGenJets', 'I')
        self.tree.add(lambda cands: self.event.genHT(), 'genHT', 'I')
        # scale shifts
        weightMap = {
            0: {'muR':1.0, 'muF':1.0},
            1: {'muR':1.0, 'muF':2.0},
            2: {'muR':1.0, 'muF':0.5},
            3: {'muR':2.0, 'muF':1.0},
            4: {'muR':2.0, 'muF':2.0},
            5: {'muR':2.0, 'muF':0.5},
            6: {'muR':0.5, 'muF':1.0},
            7: {'muR':0.5, 'muF':2.0},
            8: {'muR':0.5, 'muF':0.5},
        }
        self.tree.add(lambda cands: 0. if self.event.isData() else self.event.genWeights()[0] if len(self.event.genWeights())>0 else 0., 'genWeight_muR{muR:3.1f}_muF{muF:3.1f}'.format(**weightMap[0]), 'F')
        self.tree.add(lambda cands: 0. if self.event.isData() else self.event.genWeights()[1] if len(self.event.genWeights())>1 else 0., 'genWeight_muR{muR:3.1f}_muF{muF:3.1f}'.format(**weightMap[1]), 'F')
        self.tree.add(lambda cands: 0. if self.event.isData() else self.event.genWeights()[2] if len(self.event.genWeights())>2 else 0., 'genWeight_muR{muR:3.1f}_muF{muF:3.1f}'.format(**weightMap[2]), 'F')
        self.tree.add(lambda cands: 0. if self.event.isData() else self.event.genWeights()[3] if len(self.event.genWeights())>3 else 0., 'genWeight_muR{muR:3.1f}_muF{muF:3.1f}'.format(**weightMap[3]), 'F')
        self.tree.add(lambda cands: 0. if self.event.isData() else self.event.genWeights()[4] if len(self.event.genWeights())>4 else 0., 'genWeight_muR{muR:3.1f}_muF{muF:3.1f}'.format(**weightMap[4]), 'F')
        self.tree.add(lambda cands: 0. if self.event.isData() else self.event.genWeights()[5] if len(self.event.genWeights())>5 else 0., 'genWeight_muR{muR:3.1f}_muF{muF:3.1f}'.format(**weightMap[5]), 'F')
        self.tree.add(lambda cands: 0. if self.event.isData() else self.event.genWeights()[6] if len(self.event.genWeights())>6 else 0., 'genWeight_muR{muR:3.1f}_muF{muF:3.1f}'.format(**weightMap[6]), 'F')
        self.tree.add(lambda cands: 0. if self.event.isData() else self.event.genWeights()[7] if len(self.event.genWeights())>7 else 0., 'genWeight_muR{muR:3.1f}_muF{muF:3.1f}'.format(**weightMap[7]), 'F')
        self.tree.add(lambda cands: 0. if self.event.isData() else self.event.genWeights()[8] if len(self.event.genWeights())>8 else 0., 'genWeight_muR{muR:3.1f}_muF{muF:3.1f}'.format(**weightMap[8]), 'F')

    def __exit__(self, type, value, traceback):
        self.finish()

    def __del__(self):
        self.finish()

    def finish(self):
        print ''
        logging.info('Finishing')
        logging.info('Writing {0} events'.format(self.eventsStored))
        self.outfile.cd()
        cutflowHist = ROOT.TH1D('summedWeights','summedWeights',1,0,1)
        cutflowHist.SetBinContent(1,self.summedWeights)
        self.outfile.Write()
        self.outfile.Close()
        self.leptonScales.finish()

    def flush(self):
        sys.stdout.flush()
        sys.stderr.flush()

    #############################
    ### primary analysis loop ###
    #############################
    def analyze(self):
        '''
        The primary analyzer loop.
        '''
        logging.info('Beginning Analysis')
        start = time.time()
        new = start
        old = start
        if hasProgress:
            self.pbar.maxval = self.totalEntries
            self.pbar.start()
            total = 0
            for f, fName in enumerate(self.fileNames):
                if fName.startswith('/store'): fName = '{0}/{1}'.format('/hdfs' if self.hasHDFS else 'root://cmsxrootd.hep.wisc.edu/',fName)
                tfile = ROOT.TFile.Open(fName,'READ')
                tree = tfile.Get(self.treename)
                #skimName = 'skim{0}'.format(f)
                #tree.Draw('>>{0}'.format(skimName),self.preselection,'entrylist')
                #skimlist = ROOT.gDirectory.Get(skimName)
                #listEvents = skimlist.GetN()
                #for r in xrange(listEvents):
                for row in tree:
                    total += 1
                    #tree.GetEntry(skimlist.Next())
                    self.pbar.update(total)
                    self.setupEvent(tree)
                    self.perRowAction()
                tfile.Close('R')
            self.pbar.update(self.totalEntries)
        else:
            total = 0
            for f, fName in enumerate(self.fileNames):
                if fName.startswith('/store'): fName = '{0}/{1}'.format('/hdfs' if self.hasHDFS else 'root://cmsxrootd.hep.wisc.edu/',fName)
                logging.info('Processing file {0} of {1}: {2}'.format(f+1, len(self.fileNames), fName))
                tfile = ROOT.TFile.Open(fName,'READ')
                tree = tfile.Get(self.treename)
                #skimName = 'skim{0}'.format(f)
                #tree.Draw('>>{0}'.format(skimName),self.preselection,'entrylist')
                #skimlist = ROOT.gDirectory.Get(skimName)
                #listEvents = skimlist.GetN()
                #for r in xrange(listEvents):
                for row in tree:
                    total += 1
                    if total==2: start = time.time() # just ignore first event for timing
                    #tree.GetEntry(skimlist.Next())
                    if total % 1000 == 1:
                        cur = time.time()
                        elapsed = cur-start
                        remaining = float(elapsed)/total * float(self.totalEntries) - float(elapsed)
                        mins, secs = divmod(int(remaining),60)
                        hours, mins = divmod(mins,60)
                        logging.info('{0}: Processing event {1}/{2} - {3}:{4:02d}:{5:02d} remaining'.format(self.outputTreeName,total,self.totalEntries,hours,mins,secs))
                        self.flush()
                    self.setupEvent(tree)
                    self.perRowAction()
                tfile.Close('R')

    def setupEvent(self,tree):
        '''Setup the event objects'''
        # load objects
        self.event     = Event(tree)
        if self.event.isData(): self.shift = ''
        if not self.event.isData(): self.gen = [GenParticle(tree,entry=i) for i in range(tree.genParticles_count)]
        self.electrons = [Electron(tree,entry=i,shift=self.shift) for i in range(tree.electrons_count)]
        self.muons     = [Muon(tree,entry=i,shift=self.shift) for i in range(tree.muons_count)]
        self.taus      = [Tau(tree,entry=i,shift=self.shift) for i in range(tree.taus_count)]
        if hasattr(tree, 'photons_count'): self.photons   = [Photon(tree,entry=i,shift=self.shift) for i in range(tree.photons_count)]
        self.jets      = [Jet(tree,entry=i,shift=self.shift) for i in range(tree.jets_count)]
        self.pfmet     = Met(tree,shift=self.shift)

    def perRowAction(self):
        '''Per row action, can be overridden'''
        # select candidates
        cands = self.selectCandidates()
        cands['event'] = self.event

        # store event?
        goodToStore = self.cutTree.evaluate(cands)

        # do we store the tree?
        if not goodToStore: return

        self.tree.fill(cands)
        self.eventsStored += 1
        #self.outfile.Flush()

    def selectCandidates(self):
        '''
        Select candidates
            format should be:
            candidates = {
                "objectName" : ("collectionName", position),
                ...
            }
        '''
        logging.warning("You must override selectCandidates.")
        return {}

    #################
    ### utilities ###
    #################
    def findDecay(self,m_pdgid,d1_pdgid,d2_pdgid):
        '''Check if requested decay present in event'''
        for g in self.gen:
            if m_pdgid==g.pdgId():
                if (
                    (d1_pdgid==g.daughter_1()
                    and d2_pdgid==g.daughter_2())
                    or (d1_pdgid==g.daughter_2()
                    and d2_pdgid==g.daughter_1())
                   ):
                    return True
        return False

    def getCands(self,coll,func):
        return filter(func,coll)
#        cands = []
#        for cand in coll:
#            if func(cand): cands += [cand]
#        return cands

    def cleanCands(self,src,other,dr):
        cleaned = []
        for s in src:
            keep = True
            for o in other:
                if deltaR(s.eta(),s.phi(),o.eta(),o.phi())<dr:
                    keep = False
                    break
            if keep:
                cleaned += [s]
        return cleaned

    def getCollectionString(self,cand):
        if isinstance(cand,Electron): return 'e'
        elif isinstance(cand,Muon):   return 'm'
        elif isinstance(cand,Tau):    return 't'
        elif isinstance(cand,Photon): return 'g'
        elif isinstance(cand,Jet):    return 'j'
        else:                         return 'a'

    def checkTrigger(self,*datasets,**triggerNames):
        '''Check trigger using trigger map'''
        isData = self.event.isData()>0.5
        # reject triggers if they are in another dataset
        # looks for the dataset name in the filename
        # for MC it accepts any
        reject = True if isData else False
        for dataset in datasets:
            # if we match to the dataset, start accepting triggers
            if dataset in self.fileNames[0] and isData: reject = False
            for trigger in triggerNames[dataset]:
                var = '{0}Pass'.format(trigger)
                passTrigger = getattr(self.event,var)()
                if passTrigger>0.5:
                    # it passed the trigger
                    # in data: reject if it corresponds to a higher dataset
                    return False if reject else True
            # dont check the rest of data
            if dataset in self.fileNames[0] and isData: break
        return False

    def metFilter(self,cands):
        filterList = [
            'HBHENoiseFilter',
            'HBHENoiseIsoFilter',
            'globalTightHalo2016Filter',
            'EcalDeadCellTriggerPrimitiveFilter',
            'goodVertices',
            'eeBadScFilter',
            'noBadMuons',
            'BadChargedCandidateFilter',
        ]
        notFilterList = [
            'duplicateMuons',
            'badMuons',
        ]
        for f in filterList:
            if not getattr(self.event,f)(): return False
        for f in notFilterList:
            if getattr(self.event,f)(): return False
        return True


    ##################
    ### Common IDs ###
    ##################
    # override in derived class if desired
    # base selections for H++ analysis
    def passLoose(self,cand):
        return passHppLoose(cand)

    def passMedium(self,cand):
        return passHppMedium(cand)

    def passTight(self,cand):
        return passHppTight(cand)

    def passPhotonId(self,cand):
        return passPhoton(cand)

    def passElectronVeto(self,cand):
        return passElectronVeto(cand)

    def passPhotonPreselection(self,cand):
        return passPreselection(cand)

    def passAny(self,cand):
        return True

    def passPhotonPreselectionNoElectronVeto(self,cand):
        return passPreselectionNoElectronVeto(cand)

    def looseScale(self,cand):
        #key = 'CutbasedVeto' if abs(cand.eta())<1.479 else 'CutbasedLoose'
        if cand.collName=='muons': return self.leptonScales.getScale('MediumIDLooseIso',cand,doError=True)
        #elif cand.collName=='electrons': return self.leptonScales.getScale(key,cand,doError=True)
        elif cand.collName=='electrons': return self.leptonScales.getScale('CutbasedLoose',cand,doError=True)
        else: return [1.,1.,1.]

    def mediumScale(self,cand):
        if cand.collName=='muons': return self.leptonScales.getScale('MediumIDTightIso',cand,doError=True)
        elif cand.collName=='electrons': return self.leptonScales.getScale('CutbasedMedium',cand,doError=True)
        else: return [1.,1.,1.]

    def tightScale(self,cand):
        #if cand.collName=='muons': return self.leptonScales.getScale('MediumIDTightIso',cand,doError=True)
        if cand.collName=='muons': return self.leptonScales.getScale('TightIDTightIso',cand,doError=True)
        elif cand.collName=='electrons': return self.leptonScales.getScale('CutbasedTight',cand,doError=True)
        else: return [1.,1.,1.]

    def mediumFakeRate(self,cand):
        return self.fakeRates.getFakeRate(cand,'HppMedium','HppLoose',doError=True)

    def tightFakeRate(self,cand):
        return self.fakeRates.getFakeRate(cand,'HppTight','HppLoose',doError=True)

    def tightFromMediumFakeRate(self,cand):
        return self.fakeRates.getFakeRate(cand,'HppTight','HppMedium',doError=True)

    def getPassingCands(self,mode,*colls):
        if mode=='Loose': passMode = self.passLoose
        elif mode=='Medium': passMode = self.passMedium
        elif mode=='Tight': passMode = self.passTight
        elif mode=='Photon': passMode = self.passPhotonId
        elif mode=='ElectronVeto': passMode = self.passElectronVeto
        elif mode=='PhotonPreselection': passMode = self.passPhotonPreselection
        elif mode=='PhotonPreselectionNoElectronVeto': passMode = self.passPhotonPreselectionNoElectronVeto
        elif mode=='PassAny' : passMode = self.passAny
        else: return []
        cands = []
        for coll in colls:
            cands += self.getCands(coll,passMode)
        return cands

    def numJets(self,cleanJets,mode,pt):
        jetColl = self.getCands(
            cleanJets,
            lambda cand: getattr(cand,mode)()>0.5 and cand.pt()>pt
        )
        return len(jetColl)

    ##########################
    ### add object to tree ###
    ##########################
    def addTriggers(self):
        if self.version=='76X':
            # single lepton
            self.tree.add(lambda cands: self.event.IsoMu20Pass(), 'pass_IsoMu20', 'I')
            self.tree.add(lambda cands: self.event.IsoTkMu20Pass(), 'pass_IsoTkMu20', 'I')
            self.tree.add(lambda cands: self.event.Ele23_WPLoose_GsfPass(), 'pass_Ele23_WPLoose_Gsf', 'I')
            # double lepton
            self.tree.add(lambda cands: self.event.Mu17_TrkIsoVVL_Mu8_TrkIsoVVL_DZPass(), 'pass_Mu17_TrkIsoVVL_Mu8_TrkIsoVVL_DZ', 'I')
            self.tree.add(lambda cands: self.event.Mu17_TrkIsoVVL_TkMu8_TrkIsoVVL_DZPass(), 'pass_Mu17_TrkIsoVVL_TkMu8_TrkIsoVVL_DZ', 'I')
            self.tree.add(lambda cands: self.event.Ele17_Ele12_CaloIdL_TrackIdL_IsoVL_DZPass(), 'pass_Ele17_Ele12_CaloIdL_TrackIdL_IsoVL_DZ', 'I')
            self.tree.add(lambda cands: self.event.Mu8_TrkIsoVVL_Ele17_CaloIdL_TrackIdL_IsoVLPass(), 'pass_Mu8_TrkIsoVVL_Ele17_CaloIdL_TrackIdL_IsoVL', 'I')
            self.tree.add(lambda cands: self.event.Mu17_TrkIsoVVL_Ele12_CaloIdL_TrackIdL_IsoVLPass(), 'pass_Mu17_TrkIsoVVL_Ele12_CaloIdL_TrackIdL_IsoVL', 'I')
            self.tree.add(lambda cands: self.event.DoubleMediumIsoPFTau35_Trk1_eta2p1_RegPass(), 'pass_DoubleMediumIsoPFTau35_Trk1_eta2p1_Reg', 'I')
        else:
            # single lepton
            self.tree.add(lambda cands: self.event.IsoMu24Pass(), 'pass_IsoMu24', 'I')
            self.tree.add(lambda cands: self.event.IsoTkMu24Pass(), 'pass_IsoTkMu24', 'I')
            self.tree.add(lambda cands: self.event.Mu50Pass(), 'pass_Mu50', 'I')
            self.tree.add(lambda cands: self.event.TkMu50Pass(), 'pass_TkMu50', 'I')
            self.tree.add(lambda cands: self.event.Ele27_WPTight_GsfPass(), 'pass_Ele27_WPTight_Gsf', 'I')
            # double lepton
            self.tree.add(lambda cands: self.event.Mu17_TrkIsoVVL_Mu8_TrkIsoVVL_DZPass(), 'pass_Mu17_TrkIsoVVL_Mu8_TrkIsoVVL_DZ', 'I')
            self.tree.add(lambda cands: self.event.Mu17_TrkIsoVVL_TkMu8_TrkIsoVVL_DZPass(), 'pass_Mu17_TrkIsoVVL_TkMu8_TrkIsoVVL_DZ', 'I')
            self.tree.add(lambda cands: self.event.Ele23_Ele12_CaloIdL_TrackIdL_IsoVL_DZPass(), 'pass_Ele23_Ele12_CaloIdL_TrackIdL_IsoVL_DZ', 'I')
            self.tree.add(lambda cands: self.event.Mu8_TrkIsoVVL_Ele23_CaloIdL_TrackIdL_IsoVLPass(), 'pass_Mu8_TrkIsoVVL_Ele23_CaloIdL_TrackIdL_IsoVL', 'I')
            self.tree.add(lambda cands: self.event.Mu23_TrkIsoVVL_Ele8_CaloIdL_TrackIdL_IsoVLPass(), 'pass_Mu23_TrkIsoVVL_Ele8_CaloIdL_TrackIdL_IsoVL', 'I')
            self.tree.add(lambda cands: self.event.Mu8_TrkIsoVVL_Ele23_CaloIdL_TrackIdL_IsoVL_DZPass(), 'pass_Mu8_TrkIsoVVL_Ele23_CaloIdL_TrackIdL_IsoVL_DZ', 'I')
            self.tree.add(lambda cands: self.event.Mu23_TrkIsoVVL_Ele8_CaloIdL_TrackIdL_IsoVL_DZPass(), 'pass_Mu23_TrkIsoVVL_Ele8_CaloIdL_TrackIdL_IsoVL_DZ', 'I')
            self.tree.add(lambda cands: self.event.DoubleMediumCombinedIsoPFTau35_Trk1_eta2p1_RegPass(), 'pass_DoubleMediumCombinedIsoPFTau35_Trk1_eta2p1_Reg', 'I')
            # triple lepton
            self.tree.add(lambda cands: self.event.Ele16_Ele12_Ele8_CaloIdL_TrackIdLPass(), 'pass_Ele16_Ele12_Ele8_CaloIdL_TrackIdL', 'I')
            self.tree.add(lambda cands: self.event.Mu8_DiEle12_CaloIdL_TrackIdLPass(), 'pass_Mu8_DiEle12_CaloIdL_TrackIdL', 'I')
            self.tree.add(lambda cands: self.event.DiMu9_Ele9_CaloIdL_TrackIdLPass(), 'pass_DiMu9_Ele9_CaloIdL_TrackIdL', 'I')
            self.tree.add(lambda cands: self.event.TripleMu_12_10_5Pass(), 'pass_TripleMu_12_10_5', 'I')

    def addPhotonTriggers(self):
        self.tree.add(lambda cands: self.event.DoublePhoton60Pass(), 'pass_DoublePhoton60', 'I')
        self.tree.add(lambda cands: self.event.Diphoton30_18_R9Id_OR_IsoCaloId_AND_HE_R9Id_Mass90Pass(), 'pass_Diphoton30_18_R9Id_OR_IsoCaloId_AND_HE_R9Id_Mass90', 'I')
        self.tree.add(lambda cands: self.event.Photon175Pass(), 'pass_Photon175', 'I')
        

    def addCandVar(self,label,varLabel,var,rootType):
        '''Add a variable for a cand'''
        self.tree.add(lambda cands: getattr(cands[label],var)(), '{0}_{1}'.format(label,varLabel), rootType)

    def addFlavorDependentCandVar(self,label,varLabel,varMap,rootType):
        '''Add a variable for a cand based on flavor'''
        self.tree.add(lambda cands: getattr(cands[label],varMap[cands[label].collName])() if cands[label].collName in varMap else 0., '{0}_{1}'.format(label,varLabel), rootType)

    def addMet(self,label):
        '''Add Met variables'''
        self.addCandVar(label,'pt','et','F')
        self.addCandVar(label,'phi','phi','F')

    def addCandidate(self,label):
        '''Add variables relevant for all objects'''
        self.addCandVar(label,'pt','pt','F')
        self.addCandVar(label,'eta','eta','F')
        self.addCandVar(label,'phi','phi','F')
        self.addCandVar(label,'energy','energy','F')

    def addJet(self,label):
        '''Add variables relevant for jets'''
        self.addCandidate(label)

    def addLepton(self,label,doId=False,doScales=False,doFakes=False,doErrors=False):
        '''Add variables relevant for leptons'''
        self.addCandidate(label)
        self.addCandVar(label,'charge','charge','I')
        self.addCandVar(label,'dz','dz','F')
        self.addCandVar(label,'pdgId','pdgId','I')
        self.addFlavorDependentCandVar(label,'dxy',            {'electrons':'dB2D',           'muons':'dB2D',      'taus':'dxy',         '':''},'F')
        self.addFlavorDependentCandVar(label,'isolation',      {'electrons':'relPFIsoRhoR03', 'muons':'relPFIsoDeltaBetaR04',            '':''},'F')
        self.addFlavorDependentCandVar(label,'genMatch',       {'electrons':'genMatch',       'muons':'genMatch',  'taus':'genJetMatch', '':''},'I')
        self.tree.add(lambda cands: self.genDeltaR(cands[label]) if isinstance(cands[label],Electron) or isinstance(cands[label],Muon) else self.genJetDeltaR(cands[label]), '{0}_genDeltaR'.format(label), 'F')
        self.addFlavorDependentCandVar(label,'genStatus',      {'electrons':'genStatus',      'muons':'genStatus', 'taus':'genJetStatus','':''},'I')
        self.addFlavorDependentCandVar(label,'genPdgId',       {'electrons':'genPdgId',       'muons':'genPdgId',  'taus':'genJetPdgId', '':''},'I')
        self.addFlavorDependentCandVar(label,'genPt',          {'electrons':'genPt',          'muons':'genPt',     'taus':'genJetPt',    '':''},'F')
        self.addFlavorDependentCandVar(label,'genEta',         {'electrons':'genEta',         'muons':'genEta',    'taus':'genJetEta',   '':''},'F')
        self.addFlavorDependentCandVar(label,'genPhi',         {'electrons':'genPhi',         'muons':'genPhi',    'taus':'genJetPhi',   '':''},'F')
        self.addFlavorDependentCandVar(label,'genEnergy',      {'electrons':'genEnergy',      'muons':'genEnergy', 'taus':'genJetEnergy','':''},'F')
        self.addFlavorDependentCandVar(label,'genCharge',      {'electrons':'genCharge',      'muons':'genCharge', 'taus':'genJetCharge','':''},'I')
        self.addFlavorDependentCandVar(label,'genIsPrompt',    {'electrons':'genIsPrompt',    'muons':'genIsPrompt',                     '':''},'I')
        self.addFlavorDependentCandVar(label,'genIsFromTau',   {'electrons':'genIsFromTau',   'muons':'genIsFromTau',                    '':''},'I')
        self.addFlavorDependentCandVar(label,'genIsFromHadron',{'electrons':'genIsFromHadron','muons':'genIsFromHadron',                 '':''},'I')
        if doId:
            self.tree.add(lambda cands: self.passMedium(cands[label]),                     '{0}_passMedium'.format(label), 'I')
            self.tree.add(lambda cands: self.passTight(cands[label]),                      '{0}_passTight'.format(label), 'I')
        if doScales:
            self.tree.add(lambda cands: self.looseScale(cands[label])[0],                  '{0}_looseScale'.format(label), 'F')
            if doErrors: self.tree.add(lambda cands: self.looseScale(cands[label])[1],     '{0}_looseScaleUp'.format(label), 'F')
            if doErrors: self.tree.add(lambda cands: self.looseScale(cands[label])[2],     '{0}_looseScaleDown'.format(label), 'F')
            self.tree.add(lambda cands: self.mediumScale(cands[label])[0],                 '{0}_mediumScale'.format(label), 'F')
            if doErrors: self.tree.add(lambda cands: self.mediumScale(cands[label])[1],    '{0}_mediumScaleUp'.format(label), 'F')
            if doErrors: self.tree.add(lambda cands: self.mediumScale(cands[label])[2],    '{0}_mediumScaleDown'.format(label), 'F')
            self.tree.add(lambda cands: self.tightScale(cands[label])[0],                  '{0}_tightScale'.format(label), 'F')
            if doErrors: self.tree.add(lambda cands: self.tightScale(cands[label])[1],     '{0}_tightScaleUp'.format(label), 'F')
            if doErrors: self.tree.add(lambda cands: self.tightScale(cands[label])[2],     '{0}_tightScaleDown'.format(label), 'F')
        if doFakes:
            self.tree.add(lambda cands: self.mediumFakeRate(cands[label])[0],              '{0}_mediumFakeRate'.format(label), 'F')
            if doErrors: self.tree.add(lambda cands: self.mediumFakeRate(cands[label])[1], '{0}_mediumFakeRateUp'.format(label), 'F')
            if doErrors: self.tree.add(lambda cands: self.mediumFakeRate(cands[label])[2], '{0}_mediumFakeRateDown'.format(label), 'F')
            self.tree.add(lambda cands: self.tightFakeRate(cands[label])[0],               '{0}_tightFakeRate'.format(label), 'F')
            if doErrors: self.tree.add(lambda cands: self.tightFakeRate(cands[label])[1],  '{0}_tightFakeRateUp'.format(label), 'F')
            if doErrors: self.tree.add(lambda cands: self.tightFakeRate(cands[label])[2],  '{0}_tightFakeRateDown'.format(label), 'F')
            self.tree.add(lambda cands: self.tightFromMediumFakeRate(cands[label])[0],               '{0}_tightFromMediumFakeRate'.format(label), 'F')
            if doErrors: self.tree.add(lambda cands: self.tightFromMediumFakeRate(cands[label])[1],  '{0}_tightFromMediumFakeRateUp'.format(label), 'F')
            if doErrors: self.tree.add(lambda cands: self.tightFromMediumFakeRate(cands[label])[2],  '{0}_tightFromMediumFakeRateDown'.format(label), 'F')

    def addPhoton(self,label,doId=False,doScales=False,doFakes=False,doErrors=False):
        '''Add variables relevant for photons'''
        self.addCandidate(label)
        self.addCandVar(label,'mvaNonTrigValues','mvaNonTrigValues','F')
        self.addCandVar(label,'mvaNonTrigCategories','mvaNonTrigCategories','F')
        self.addCandVar(label,'r9','r9','F')
        self.addCandVar(label,'chargedIso','phoChargedIsolation','F')
        self.addCandVar(label,'neutralHadronIso','phoNeutralHadronIsolation','F')
        self.addCandVar(label,'photonIso','phoPhotonIsolation','F')
        if doId:
            self.tree.add(lambda cands: self.passPhotonId(cands[label]),           '{0}_passId'.format(label), 'I')
            self.tree.add(lambda cands: self.passElectronVeto(cands[label]),       '{0}_passElectronVeto'.format(label), 'I')
            self.tree.add(lambda cands: self.passPhotonPreselection(cands[label]), '{0}_passPreselection'.format(label), 'I')
            self.tree.add(lambda cands: self.passPhotonPreselectionNoElectronVeto(cands[label]), '{0}_passPreselectionNoElectronVeto'.format(label), 'I')

    def genDeltaR(self,cand):
        '''Get the gen level deltaR'''
        if cand.genMatch()==0: return 0.
        eta = cand.eta()
        genEta = cand.genEta()
        phi = cand.phi()
        genPhi = cand.genPhi()
        return deltaR(eta,phi,genEta,genPhi)

    def genJetDeltaR(self,cand):
        '''Get the gen level deltaR'''
        if cand.genJetMatch()==0: return 0.
        eta = cand.eta()
        genEta = cand.genJetEta()
        phi = cand.phi()
        genPhi = cand.genJetPhi()
        return deltaR(eta,phi,genEta,genPhi)

    def addDiCandidate(self,label):
        '''Add variables relevant for a two object candidate'''
        self.addCandVar(label,'mass','M','F')
        self.addCandVar(label,'pt','Pt','F')
        self.addCandVar(label,'eta','Eta','F')
        self.addCandVar(label,'phi','Phi','F')
        self.addCandVar(label,'deltaR','deltaR','F')
        self.addCandVar(label,'deltaEta','deltaEta','F')
        self.addCandVar(label,'deltaPhi','deltaPhi','F')
        self.addCandVar(label,'energy','Energy','F')

    def addDiJet(self,label):
        '''Add variables relevant for a dijet candidate'''
        self.addDiCandidate(label)

    def addDiLepton(self,label):
        '''Add variables relevant for a dilepton candidate'''
        self.addDiCandidate(label)

    def addLeptonMet(self,label):
        '''Add variables related to a lepton + met'''
        self.addCandVar(label,'mt','Mt','F')
        self.addCandVar(label,'pt','Pt','F')
        self.addCandVar(label,'eta','Eta','F')
        self.addCandVar(label,'phi','Phi','F')
        self.addCandVar(label,'deltaPhi','deltaPhi','F')

    def addComposite(self,label):
        '''Add variables related to multi object variables'''
        self.addCandVar(label,'mass','M','F')
        self.addCandVar(label,'pt','Pt','F')
        self.addCandVar(label,'eta','Eta','F')
        self.addCandVar(label,'phi','Phi','F')
        self.addCandVar(label,'energy','Energy','F')

    def addCompositeMet(self,label):
        '''Add variables related to multi object variables'''
        self.addCandVar(label,'mt','Mt','F')
        self.addCandVar(label,'pt','Pt','F')
        self.addCandVar(label,'eta','Eta','F')
        self.addCandVar(label,'phi','Phi','F')

