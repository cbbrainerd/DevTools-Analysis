#!/usr/bin/env python
import os
import sys
import glob
import argparse
from prettytable import PrettyTable
import logging

import ROOT

from DevTools.Analyzer.utilities import getNtupleDirectory
from DevTools.Plotter.utilities import getNtupleDirectory as getAnalysisNtupleDirectory
from DevTools.Plotter.utilities import getTreeName
from DevTools.Plotter.xsec import getXsec
from DevTools.Plotter.utilities import getLumi, isData
from DevTools.Utilities.utilities import getCMSSWVersion, get_hdfs_root_files, hdfs_ls_directory

log = logging.getLogger("submit_job")
logging.basicConfig(level=logging.INFO, stream=sys.stderr)


def parse_command_line(argv):
    parser = argparse.ArgumentParser(description='Dump samples available')

    parser.add_argument('--version',type=str,default=getCMSSWVersion(),help='Samples to dump')
    parser.add_argument('--analysis',type=str,default='',help='Analysis to use for detailed information')
    parser.add_argument('--selection',type=str,default='1',help='Selection to apply to tree')
    parser.add_argument('--verbose',action='store_true',help='Display detailed sample information')

    args = parser.parse_args(argv)

    return args


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]

    args = parse_command_line(argv)

    if args.verbose and args.analysis:
        table = PrettyTable(['Sample','xsec [pb]','entries','ratio neg.','lumi. [/pb]','eff. entries'])
    else:
        table = PrettyTable(['Sample','xsec [pb]'])
    table.align = 'r'
    table.align['Sample'] = 'l'

    ntupleDir = getAnalysisNtupleDirectory(args.analysis,True) if args.verbose and args.analysis else getNtupleDirectory(version=args.version)

    #Odd mix of local pathnames and xrootd access
#    for sample in sorted(hdfs_ls_directory(ntupleDir)):
    for sample in (glob.glob('/'.join([ntupleDir,'*']))):
        name = os.path.basename(sample)
        logging.info('Processing {0}'.format(name))
        data = isData(name)
        xsec = getXsec(name)
        if args.verbose and args.analysis:
            print sample
            fnames = get_hdfs_root_files(sample)
            # get total events, total weights
            tree = ROOT.TChain(getTreeName(args.analysis))
            summedWeights = 0.
            for f in fnames:
                tfile = ROOT.TFile.Open('/hdfs'+f)
                summedWeights += tfile.Get("summedWeights").GetBinContent(1)
                tfile.Close()
                tree.Add('/hdfs'+f)
            numEntries = tree.GetEntries(args.selection)
            weightedEntries = 0.
            negevents = 0.
            seltree = tree.CopyTree(args.selection)
            for row in seltree:
                if data:
                    weightedEntries += 1.
                else:
                    weightedEntries += row.genWeight
                    if row.genWeight<0.: negevents += 1
            if data:
                sampleLumi = getLumi()
            else:
                sampleLumi = float(summedWeights)/xsec if xsec else 0.
            negratio = float(negevents)/numEntries if numEntries else 0.
            effevents = weightedEntries*getLumi()/sampleLumi if sampleLumi else 0.
            table.add_row([name,'{0:.6f}'.format(float(xsec)),numEntries,'{0:.3}'.format(float(negratio)),'{0:.6f}'.format(float(sampleLumi)),'{0:.3f}'.format(float(effevents))])
        else:
            table.add_row([name,xsec])

    print table.get_string()


if __name__ == "__main__":
    status = main()
    sys.exit(status)
