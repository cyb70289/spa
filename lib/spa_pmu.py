#!bin/python3

# The confidential and proprietary information contained in this file may
# only be used by a person authorised under and to the extent permitted
# by a subsisting licensing agreement from ARM Limited.
#
#            (C) COPYRIGHT 2018 ARM Limited.
#                    ALL RIGHTS RESERVED
#
# This entire notice must be reproduced on all copies of this file
# and copies of this file may only be made by a person if such person is
# permitted to do so under the terms of a subsisting license agreement
# from ARM Limited.
#
# Authors: Tushar Singh Chouhan
# This file manages the perf data collection. 


import os
import sys
import re
import subprocess
import json
import data_manager 
import shutil 
from defines import Verbosity, Style

class spa_pmu:

    
    def __init__(self, log):
    
        self.log = log

    def display_counters(self, pmu_list):
        
        print(pmu_list)
    
    
    def perform_perf_stat(self, pmu_obj, options):
        
        self.log.info("Perf monitoring is starting") 
        
        if options['style'] == Style.Normal:
            self.normal_style(pmu_obj, options)
        else:
            self.iterative_style(pmu_obj, options)
    
    
    def perform_perf_rec(self, rec_obj, options):
        
        record_path = 'PMU_rec_logs/record_{}'.format(options['timestamp'])
        com = ["perf", "record"]
        if not options['cf']:
            if options['callgraph']:
                com.append('--call-graph')
                com.append('dwarf')
        else:
            com.append('--call-graph')
            com.append('dwarf')
        if 'extra_args' in options.keys():
            com.append(options['extra_args'])
        com.append(options['command'])
        com = ' '.join(i for i in com)
        self.log.info(com)
        subprocess.call(com,shell=True)
        
        with open("{}/rec".format(record_path), "w+") as op:
            subprocess.call("perf report | cat", stdout=op, shell=True)
        
        
        filename = "{}/rec".format(record_path)
        regex = "( *)([0-9.]+%) *([0-9.]+)% *(\S+) *(\S+) +([\[\].a-z]+) +(\S+)(.*)"
        exp = re.compile(regex)
        data = {}
        with open(filename, "r+" ) as f:
            for line in f:
                match = exp.match(line)
                if match:
                    key = match.group(7)
                    if key not in data.keys():
                        value = float(match.group(2)[:-1])
                        if value < options["Flevel"]:
                            break
                        data[key] = match.group(2)[:-1]
        
        rec_obj.info['info'] = data
        filename = "PMU_rec_logs/records/record_{}".format(rec_obj.info['metadata']['timestamp'])
        
        with open(filename, "w+") as f:
            f.write(json.dumps(rec_obj.info))
        subprocess.call("rm rec_data_latest", shell=True)
        subprocess.call("ln -s {} rec_data_latest".format(filename), shell=True)
        
        if options['cf']:
            shutil.move('perf.data', record_path)
            os.chdir(record_path)
            self.flamegraph(record_path)
            os.chdir('../../')
    
    
    def flamegraph(self, record_path):
      
        
        try:
            self.log.info("Creating Flamegraph")
            with open("out.perf", "w+") as op:
                subprocess.check_call(["perf", "script", "-i", "perf.data"], stdout=op, shell=False)

            with open("out.folded", "w+") as op:
                subprocess.check_call(["/opt/FlameGraph/stackcollapse-perf.pl", "out.perf"], stdout=op, shell=False)
        
            with open("out.svg", "w+") as op:
                subprocess.check_call(["/opt/FlameGraph/flamegraph.pl", "out.folded"], stdout=op, shell=False)
       
        except Exception as e:
            self.log.error(e)
    
    
    def parse_output(self, pmu_obj, out, event_list, options):
    
        data = {} 
        count = 0
        while True:
            i = out.stdout.readline()
            if not i:
                break
            self.log.info(i)
            count_regex = ""
            if not options['style'] == Style.Iterate:
                index = 0
                if not 'interval' in options.keys():
                    count_regex = re.compile("^( *)([0-9.]+)( *)(\S+)( *| +#.*)$")
                    index = 2
                    key = 4
                else: 
                    count_regex = re.compile("( *)([0-9.]+)( +)([0-9]+)( +)(\S+)( *)")
                    index = 4
                    key = 6
    
                match = count_regex.search(i)
                if match:
                    pmu_obj.info['counter'][match.group(key)]['Value'].append(int(match.group(index)))
                    if 'interval' in options.keys():
                        pmu_obj.info['counter'][match.group(key)]['Timestamp'].append(float(match.group(2)))
            else:
               if not 'interval' in options.keys():
                   count_regex = re.compile("( *)([0-9.]+)( *)({})( .*)".format(event_list))
                   index = 2
                   key = 4
               else: 
                   count_regex = re.compile("( *)([0-9.]+)( *)([0-9]+)( *)({})( *)".format(event_list))
                   index = 4
                   key = 6
    
               match = count_regex.match(i)
               if match:
                   pmu_obj.info['counter'][match.group(key)]['Value'].append(int(match.group(index)))
                   if 'interval' in options.keys():
                       pmu_obj.info['counter'][match.group(key)]['Timestamp'].append(float(match.group(2)))
        
        if 'interval' in options.keys():
            for k in pmu_obj.info['counter'].keys():
                v = pmu_obj.info['counter'][k]['Value']
                pmu_obj.info['counter'][k]['Value'] = v[:-1]

    
        
    def normal_style(self, pmu_obj, options):    
        
        com = self.com_create(options)
        events = ','.join(e[0:] for e in options['event_list'])
        com.append(events)
        for i in options['command'].split(' '):
            com.append(str(i))
        out  = self.perform_action(com, options)
        self.parse_output(pmu_obj, out, None, options)
    
    
    def iterative_style(self,  pmu_obj, options):    
        
        for event in options['event_list']:
            com = self.com_create(options)
            com.append(event)
            for i in options['command'].split(' '):
                com.append(str(i))
            out = self.perform_action(com, options, event)
            self.parse_output(pmu_obj, out, event, options)
    
    
    def com_create(self, options):
    
        com = ["perf", "stat"]
        if 'interval' in options.keys():
            com.append('-I')
            com.append(str(options['interval']))
        com.append("-e")
        return com
    
    
    def perform_action(self, com, options, event=None):
    
        out = None
        self.log.info("Counter Being Profiles: {}".format(com[3]))
        try:
            out = subprocess.Popen(com, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
        except Exception as e:
            self.log.warning("Error with profiling {}".format(e))
            #self.log.warning("Message = ".format(out))
        return out
