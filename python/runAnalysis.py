#!/usr/bin/env python

import importlib

def runAnalysis(analysis,argv):
    '''Calls analysis function'''
    try:
        func=importlib.import_module('DevTools.Analyzer.%sAnalysis' % analysis).main
    except ImportError, AttributeError:
        return 0
    return func(argv)
