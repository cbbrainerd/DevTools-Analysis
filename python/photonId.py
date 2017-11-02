# common photon id

from Candidates import Photon

def passPhoton(photon,version='80X'):
    return photon.mvaNonTrigWP90()

def passPreselectionNoElectronVeto(photon,version='80X'):
    if photon.pt()<10: return False
    if abs(photon.eta())>2.5: return False
    # selections to match the online trigger requirements
    if photon.hadronicOverEM()>=0.08: return False
    if photon.isEB():
        if photon.r9()<=0.50: return False
        if photon.r9()<=0.85:
            if photon.sigmaIEtaIEta()>=0.015: return False
            if photon.phoPhotonIsolation()>=4.0: return False  # TODO: verify this is PF
            if photon.trackIso()>=6.0: return False
    else:
        if photon.r9()<=0.80: return False
        if photon.r9()<=0.90:
            if photon.sigmaIEtaIEta()>=0.035: return False
            if photon.phoPhotonIsolation()>=4.0: return False  # TODO: verify this is PF
            if photon.trackIso()>=6.0: return False
    return True

def passElectronVeto(photon,version='80X'):
    return photon.passElectronVeto()

def passPreselection(photon,version='80X'):
    # electron veto
    if not passElectronVeto(photon,version): return False
    return passPreselectionNoElectronVeto(photon,version)
