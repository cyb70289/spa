#!bin/python3

import sys
import os
from defines import Verbosity, Style


class PMU:
    
    def __init__(self):
        self.info = {'metadata':{}, 'counter': {}}
        self.data = None
       # self.metadata = {}

class REC:

    def __init__(self):
        self.info = {'metadata':{}, 'info':{}}
        self.data = None


class EBPF:

    def __init__(self):
        self.info = {'metadata':{}, 'info':{}}
        self.data = None
