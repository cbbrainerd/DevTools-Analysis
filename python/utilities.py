# common utilities for analyzers
import os
import sys
import glob

import ROOT

from DevTools.Utilities.utilities import ZMASS, getCMSSWVersion

def deltaPhi(phi0,phi1):
    result = phi0-phi1
    while result>ROOT.TMath.Pi():
        result -= 2*ROOT.TMath.Pi()
    while result<=-ROOT.TMath.Pi():
        result += 2*ROOT.TMath.Pi()
    return result

def deltaR(eta0,phi0,eta1,phi1):
    deta = eta0-eta1
    dphi = deltaPhi(phi0,phi1)
    return ROOT.TMath.Sqrt(deta**2+dphi**2)

latestNtuples = {
    '76X' : '2016-09-28_DevTools_76X_v1',
    #'80X' : '2016-07-20_DevTools_80X_v1', # ICHEP 2016
    '80X' : '2017-02-28_DevTools_80X_v1', # Moriond 2017
    '80XPhoton' : '2017-06-06_DevTools_80X_photon_v1', # Moriond 2017
}

def getNtupleDirectory(version=None):
    baseDir = '/hdfs/store/user/dntaylor'
    if not version: version = getCMSSWVersion()
    if version in latestNtuples:
        return os.path.join(baseDir,latestNtuples[version])

def getTestFiles(sample,n=1,version=None):
    if not version: version = getCMSSWVersion()

    sampleMap = {
        'wz'    : 'WZTo3LNu_TuneCUETP8M1_13TeV-powheg-pythia8',
        'zz'    : 'ZZTo4L_13TeV_powheg_pythia8',
        'data'  : 'DoubleMuon',
        'hpp'   : 'HPlusPlusHMinusMinusHTo4L_M-500_13TeV-pythia8' if version=='76X' else 'HPlusPlusHMinusMinusHTo4L_M-500_TuneCUETP8M1_13TeV_pythia8',
        'hpp4l' : 'HPlusPlusHMinusMinusHTo4L_M-500_13TeV-pythia8' if version=='76X' else 'HPlusPlusHMinusMinusHTo4L_M-500_TuneCUETP8M1_13TeV_pythia8',
        'hppr4l': 'HPlusPlusHMinusMinusHRTo4L_M-500_13TeV-pythia8' if version=='76X' else 'HPlusPlusHMinusMinusHRTo4L_M-500_TuneCUETP8M1_13TeV_pythia8',
        'hpp3l' : 'HPlusPlusHMinusHTo3L_M-500_TuneCUETP8M1_13TeV_calchep-pythia8' if version=='76X' else 'HPlusPlusHMinusHTo3L_M-500_13TeV-calchep-pythia8',
        #'dy'    : 'DYJetsToLL_M-50_TuneCUETP8M1_13TeV-amcatnloFXFX-pythia8',
        'dy'    : 'DYJetsToLL_M-50_TuneCUETP8M1_13TeV-madgraphMLM-pythia8',
        'w'     : 'WJetsToLNu_TuneCUETP8M1_13TeV-amcatnloFXFX-pythia8',
        'SingleMuon'    : 'SingleMuon',
        'SingleElectron': 'SingleElectron',
        'DoubleMuon'    : 'DoubleMuon',
        'DoubleEG'      : 'DoubleEG',
        'MuonEG'        : 'MuonEG',
        'Tau'           : 'Tau',
    }

    if sample not in sampleMap: return []
    
    files = [f.replace('/hdfs','') for f in glob.glob('{0}/{1}/*/*/*/*.root'.format(getNtupleDirectory(version=version),sampleMap[sample]))]

    if sample=='wz': return files[1:min(n+1,len(files)-1)] # temporary hack to get a better WZ sample (Summer16 MC)
    return files[:min(n,len(files))]

def get_hdfs_root_files(topDir,lastDir=''):
    '''Utility for getting all root files in a directory (and subdirectories)'''
    lsDir = strip_hdfs('{0}/{1}'.format(topDir,lastDir)) if lastDir else strip_hdfs(topDir)
    nextLevel = hdfs_ls_directory(lsDir)
    out = []
    for nl in nextLevel:
        if nl=='failed': # dont include
            continue
        elif nl[-4:]=='root': # its a root file
            out += ['{0}/{1}'.format(lsDir,nl)]
        else: # keep going down
            out += get_hdfs_root_files(lsDir,nl)
    return out
