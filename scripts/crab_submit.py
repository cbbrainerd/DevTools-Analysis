#!/bin/bash

#The following code checks if the environment has been set up, and if it has not, sets it up then executes the python file

#Note that python ignores this because it is a multiline string constant
''':'
if [ -z "$CMSSW_BASE" ]; then
    . /cvmfs/cms.cern.ch/cmsset_default.sh; eval `scramv1 runtime -sh`; . /cvmfs/cms.cern.ch/crab3/crab.sh;
elif ! /usr/bin/which crab &> /dev/null; then 
    . /cvmfs/cms.cern.ch/crab3/crab.sh
fi
exec python "$0" "$@"
exit 1
'''

import subprocess
import pickle
import re

import sys
import os

import datetime

DEBUG=False

now=datetime.datetime.utcnow().strftime("%Y-%m-%d_%H:%M:%S")

print 'Jobs started at time %s' % (now)

analysis='WGFakeRate' #Obviously won't stay hard-coded, but I'm lazy for now. Will probably allow for a loop here in the future
subtitle=None

from DevTools.Utilities.utilities import get_hdfs_root_files

from DevTools.Analyzer.runAnalysis import analysisFunctionDict as tmp

try:
    tmp[analysis]
except KeyError:
    print '%s is not a valid analysis.' % analysis
    print tmp.keys()
    raise

try:
    from CRABClient.UserUtilities import config
    from CRABClient.UserUtilities import getUsernameFromSiteDB as uname
except ImportError:
    print 'You need to source the CRAB setup scripts first.'
    print '(Run the command `. /cvmfs/cms.cern.ch/crab3/crab.sh`)'
#    os.execlp('bash','bash','-c','. /cvmfs/cms.cern.ch/crab3/crab.sh ; python %s' % ' '.join(sys.argv))
    raise SystemExit

def getConfig(analysis,dataset,listOfFiles,debug=False):
    crabConfig=config()
    crabConfig.General.requestName='_'.join([analysis,dataset])
    crabConfig.General.workArea='/uscms_data/d3/%s/crab_projects/%s%s/%s' % (uname(),analysis,'_%s' % subtitle if subtitle else '',now)
    crabConfig.JobType.scriptExe='crab_wrapper.py'
    crabConfig.JobType.scriptArgs=['analysis=%s'%analysis,'outputFile=%s_%s.root'%(analysis,dataset)]
    crabConfig.JobType.pluginName='Analysis'
    crabConfig.JobType.outputFiles=['%s_%s.root' % (analysis,dataset)]
    crabConfig.JobType.pluginName='Analysis'
    crabConfig.JobType.psetName='PSet.py'
    crabConfig.Site.storageSite='T3_US_FNALLPC'
    crabConfig.Data.userInputFiles=listOfFiles
    crabConfig.Data.unitsPerJob=10
    crabConfig.Site.whitelist=["T2_US_Wisconsin"]
    crabConfig.Data.splitting='FileBased'
    crabConfig.Data.outputPrimaryDataset=dataset
    crabConfig.JobType.sendPythonFolder = True
    crabConfig.General.transferOutputs = True
    crabConfig.General.transferLogs = True
    return crabConfig

datasetPath='/hdfs/store/user/dntaylor/2017-06-06_DevTools_80X_photon_v1'

def getDatasets(argv):
        for x in range(1,len(argv)-1):
            if(argv[x]=='--datasets'):
                argv.pop(x)
                dataset=argv.pop(x)
                if os.path.isfile(dataset):
                    with open(dataset,'r') as f:
                        datasetList=[line.strip() for line in f]
                else:
                    datasetList=dataset.split(',')
                return datasetList
        print 'Need to give datasets to run over!'
        raise SystemExit

listOfDatasets=getDatasets(sys.argv)

from CRABAPI.RawCommand import crabCommand

for jobNumber,dataset in enumerate(listOfDatasets):
    try:
        print 'Starting job %d of %d on dataset %s' % (jobNumber+1,len(listOfDatasets),dataset)
        fileList=get_hdfs_root_files('%s/%s' % (datasetPath,dataset))
        crabConfig=getConfig(analysis=analysis,dataset=dataset,listOfFiles=fileList)
        crabCommand('submit',config=crabConfig) if not DEBUG else crabCommand('submit','--dryrun',config=crabConfig)
        if DEBUG:
            break
    except Exception as e:
        print 'Job %d on dataset %s failed' % (jobNumber,dataset)
        print e

outputDir='/uscms_data/d3/%s/crab_projects/%s%s/%s' % (uname(),analysis,'_%s' % subtitle if subtitle else '',now)
try:
    thisDir=os.environ['CMSSW_BASE']+'/src'
except KeyError:
    thisDir=os.getcwd()

os.execlp("bash","bash","~/bin/crabHandleCronWrapper.sh","SETUP",thisDir,outputDir)
