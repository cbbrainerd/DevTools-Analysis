#!/usr/bin/env python
import argparse
import logging
import sys

from DevTools.Analyzer.utilities import getTestFiles
from DevTools.Analyzer.Hpp3lAnalysis import Hpp3lAnalysis

logger = logging.getLogger("Hpp3lAnalysis")
logging.basicConfig(level=logging.INFO, stream=sys.stderr, format='%(asctime)s.%(msecs)03d %(levelname)s %(name)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')


def parse_command_line(argv):
    parser = argparse.ArgumentParser(description='Run analyzer')

    parser.add_argument('--inputFiles', type=str, nargs='*', default=getTestFiles('MC'), help='Input files')
    parser.add_argument('--inputFileList', type=str, default='', help='Input file list')
    parser.add_argument('--outputFile', type=str, default='hpp3lTree.root', help='Output file')

    return parser.parse_args(argv)

def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]

    args = parse_command_line(argv)

    hpp3lAnalysis = Hpp3lAnalysis(
        outputFileName=args.outputFile,
        outputTreeName='Hpp3lTree',
        inputFileNames=args.inputFileList if args.inputFileList else args.inputFiles,
        inputTreeName='MiniTree',
        inputLumiName='LumiTree',
        inputTreeDirectory='miniTree',
    )
    
    try:
       hpp3lAnalysis.analyze()
       hpp3lAnalysis.finish()
    except KeyboardInterrupt:
       hpp3lAnalysis.finish()

    return 0

if __name__ == "__main__":
    status = main()
    sys.exit(status)
