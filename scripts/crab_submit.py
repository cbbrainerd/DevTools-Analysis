#!/usr/bin/env python

import subprocess
import pickle
import re

import sys

import datetime

now=datetime.datetime.utcnow().strftime("%Y-%m-%d_%H:%M:%S")

analysis='ThreePhoton' #Obviously won't stay hard-coded, but I'm lazy for now. Will probably allow for a loop here in the future

from DevTools.Utilities.utilities import get_hdfs_root_files

try:
    from CRABClient.UserUtilities import config
    from CRABClient.UserUtilities import getUsernameFromSiteDB as uname
except ImportError:
    print 'You need to source the CRAB setup scripts first.'
    print '(Run the command `. /cvmfs/cms.cern.ch/crab3/crab3.sh`)'
    raise SystemExit

def getConfig(analysis,dataset,listOfFiles,debug=False):
    crabConfig=config()
    crabConfig.General.requestName='_'.join([analysis,now,dataset])
    crabConfig.General.workArea='/uscms_data/d3/%s/crab_projects/%s/%s/%s' % (uname(),analysis,dataset,crabConfig.General.requestName)
    crabConfig.JobType.scriptExe='crab_wrapper.py'
    crabConfig.JobType.scriptArgs=['analysis=%s'%analysis,'outputFile=%s_%s.root' % (analysis,dataset)]
    crabConfig.JobType.pluginName='Analysis'
    crabConfig.JobType.outputFiles=['%s_%s.root' % (analysis,dataset)]
    crabConfig.JobType.pluginName='Analysis'
    crabConfig.JobType.psetName='PSet.py'
    crabConfig.Site.storageSite='T3_US_FNALLPC'
    crabConfig.Data.userInputFiles=listOfFiles
    crabConfig.Data.unitsPerJob=1
    crabConfig.Data.totalUnits=1 if debug else None
    crabConfig.Data.splitting='FileBased'
    crabConfig.Data.outputPrimaryDataset=dataset
    return crabConfig

datasetPath='/hdfs/store/user/dntaylor/2017-06-06_DevTools_80X_photon_v1'

def getDatasets(argv):
        for x in range(1,len(argv)-1):
            if(argv[x]=='--datasets'):
                argv.pop(x)
                return argv.pop(x).split(',')
        print 'Need to give datasets to run over!'
        raise SystemExit

listOfDatasets=getDatasets(sys.argv)

from CRABAPI.RawCommand import crabCommand

for jobNumber,dataset in enumerate(listOfDatasets):
    try:
        print 'Starting job %d of %d on dataset %s' % (jobNumber+1,len(listOfDatasets),dataset)
        fileList=get_hdfs_root_files('%s/%s' % (datasetPath,dataset))
        config=getConfig(analysis=analysis,dataset=dataset,listOfFiles=fileList)
        crabCommand('submit','--dryrun',config=config)
    except Exception as e:
        print 'Job %d on dataset %s failed' % (jobNumber,dataset)
        print e
