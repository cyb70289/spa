
#!bin/python3


import os
import sys
import sh
import re
from time import time,sleep
from datetime import datetime
import json
import data_manager
import shutil


class analyze_sar:

    def __init__(self, log,  options):
        self.log = log
        self.options = options
        self.create_dataframe()

    def create_command(self):
        
        metrics = self.options['metrics'].split(',')
        for i in metrics:

