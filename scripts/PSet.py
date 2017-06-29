import FWCore.ParameterSet.Config as cms
process=cms.Process("Analysis")
process.source=cms.Source("PoolSource",fileNames=cms.untracked.vstring('/store/user/dntaylor/2017-06-06_DevTools_80X_photon_v1/SinglePhoton//2017-06-06_DevTools_80X_photon_v1/170606_205318/0000/miniTree_61.root'))
