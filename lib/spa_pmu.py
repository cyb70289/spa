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
import pandas as pd
from statistics import mean, stdev
import numpy as np

sys.path.append("perfmon_cpu")
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
        
        #if 'interval' in options.keys():
        for k in pmu_obj.info['counter'].keys():
            v = pmu_obj.info['counter'][k]['Value']
            pmu_obj.info['counter'][k]['Value'] = v[1:] 

        if options['type'] == 'TD':
            
            output_file_metrics = "{}/topdown_metrics_{}.csv".format("{}/Metrics".format(options['csv_path']), options['timestamp']) 
            output_file_events = "{}/topdown_events_{}.csv".format("{}/RawEvents".format(options['csv_path']), options['timestamp']) 
            subprocess.call("rm result_links/csv_result_metrics_latest", shell=True) 
            subprocess.call("ln -s ../{} result_links/csv_result_metrics_latest".format(output_file_metrics), shell=True) 
            subprocess.call("rm result_links/csv_result_events_latest", shell=True) 
            subprocess.call("ln -s ../{} result_links/csv_result_events_latest".format(output_file_events), shell=True) 
            metric_obj = self.process_TD(pmu_obj, options)
            self.gather_data(pmu_obj, options, output_file_events)
            self.gather_data(metric_obj, options, output_file_metrics, 1)
        else:
            output_file = "{}/stat_{}.csv".format(options['csv_path'], options['timestamp']) 
            subprocess.call("rm result_links/csv_result_stat_latest", shell=True) 
            subprocess.call("ln -s ../{} result_links/csv_result_stat_latest".format(output_file), shell=True) 
            self.gather_data(pmu_obj, options, output_file)
    
    
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
            extra_args = options['extra_args'].split(' ')
            for arg in extra_args:
                com.append(arg)
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
        break_cond = False
        
        print("Creating Rec Obj")

        with open(filename, "r+" ) as f:
            for line in f:
                match = exp.match(line)
                if match:
                    key = match.group(7)
                    if key not in data.keys():
                        value = float(match.group(2)[:-1])
                        if value < options["Flevel"]:
                            break_cond = True
                            break
                        data[key] = match.group(2)[:-1]
        
        rec_obj.info['info'] = data
        filename = "PMU_rec_logs/records/record_{}".format(rec_obj.info['metadata']['timestamp'])
        
        with open(filename, "w+") as f:
            f.write(json.dumps(rec_obj.info))

        subprocess.call("rm rec_data_latest", shell=True)
        subprocess.call("ln -s {} rec_data_latest".format(filename), shell=True)

        print("Creating Flamegraphs")

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
            index = 0
            if not 'interval' in options.keys():
               # count_regex = re.compile("^( *)([0-9.]+)( *)(\S+)( *| +#.*)$")
                count_regex = re.compile("^( *)([0-9.]+)( +)([0-9A-Za-z.]+)( .*)")
                index = 2
                key = 4
            else: 
                count_regex = re.compile("^( *)([0-9.]+)( +)([0-9]+)( +)([0-9A-Za-z.]+)( *)")
                index = 4
                key = 6
    
            match = count_regex.search(i)
            if match and not match.group(key)=="seconds":
                value = int(match.group(index))
                if not value >= 0:
                    value = 0
                pmu_obj.info['counter'][match.group(key)]['Value'].append(value)

                if 'interval' in options.keys():
                    pmu_obj.info['counter'][match.group(key)]['Timestamp'].append(float(match.group(2)))
            else:
                if not match:
                    not_counted_regex = re.compile("^( *)([0-9.]+)( +)(<not counted>)( +)([0-9A-Za-z.]+)( *)")
                    match_nc = not_counted_regex.search(i)
                    if match_nc:
                        key = 6
                        if match_nc.group(key) in pmu_obj.info['counter'].keys():
                            del pmu_obj.info['counter'][match_nc.group(key)]
        
        
    def normal_style(self, pmu_obj, options):    
        
        com = self.com_create(options)
        events = ','.join(e[0:] for e in options['event_list'])
        com.append(events)
        for i in options['command'].split(' '):
            com.append(str(i))
        out  = self.perform_action(com, options)
        self.parse_output(pmu_obj, out, None, options)
    
    
    def iterative_style(self,  pmu_obj, options):    
       
        com = self.com_create(options)
        tmp = []
        event_set = ""
        i = 0
        for event in options['event_list']:
            if i < options['mx_degree']:
                tmp.append(event)
                i += 1
                if  (i != options['mx_degree']) and (event != options['event_list'][-1]):                  
                    continue

            if len(tmp) > 1:
                event_set = ','.join(e for e in tmp)
                com.append(event_set)
            else:
                com.append(event)
            
            for com_part in options['command'].split(' '):
                com.append(str(com_part))
            
            out = self.perform_action(com, options, event)
            self.parse_output(pmu_obj, out, event, options)
            
            event_set = ""
            tmp = []
            i = 0
            
            self.parse_output(pmu_obj, out, event, options)
            com = self.com_create(options)
    
    
    def com_create(self, options):
    
        com = ["perf", "stat"]
        if 'interval' in options.keys():
            com.append('-I')
            com.append(str(options['interval']))
        if options['extra_args']:
            extra_args = options['extra_args'].split(' ')
            for arg in extra_args:
                com.append(arg)
        com.append("-e")
        return com
    
    
    def perform_action(self, com, options, event=None):
    
        out = None
        self.log.info("Counter Being Profiled: {}".format(com))
        try:
            out = subprocess.Popen(com, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
        except Exception as e:
            self.log.warning("Error with profiling {}".format(e))
            #self.log.warning("Message = ".format(out))
        return out



    def gather_data(self, pmu_obj, options, output_file, flag=0):
    
        pmu_result_list = {}
        
        event_names = []
        values = []
        values_list = []
        timestamps = [] 
        names = [] 
        alias = []
        machine = []
        kernel = []
        system = []
        release = []
        event_codes = []
        code = []
        command = []
        architecture = []

        for i in pmu_obj.info['counter'].keys():
            if flag == 0:
                if not pmu_obj.info['counter'][i]['Value']:
                    continue
                event_names.append(pmu_obj.info['counter'][i]['EventName'])
                event_codes.append(pmu_obj.info['counter'][i]['EventCode'])
                values_list.append(pmu_obj.info['counter'][i]['Value'])
                if len(pmu_obj.info['counter'][i]['Value']) > 1:
                    values.append(mean(pmu_obj.info['counter'][i]['Value']))
                else:
                    values.append(pmu_obj.info['counter'][i]['Value'][0])
                alias.append(pmu_obj.info['counter'][i]['Alias'])
            else:
                event_names.append(i)
                event_codes.append("N/A")
                alias.append("N/A")
                values_list.append(pmu_obj.info['counter'][i])
                if len(pmu_obj.info['counter'][i]) > 1:
                    values.append(mean(pmu_obj.info['counter'][i]))
                else:
                    values.append(pmu_obj.info['counter'][i][0])
            timestamps.append(pmu_obj.info['metadata']['timestamp'])
            names.append(pmu_obj.info['metadata']['name'])
            code.append(pmu_obj.info['metadata']['code'])
            machine.append(pmu_obj.info['metadata']['machine'])
            kernel.append(pmu_obj.info['metadata']['kernel'])
            system.append(pmu_obj.info['metadata']['system'])
            release.append(pmu_obj.info['metadata']['release'])
            command.append(pmu_obj.info['metadata']['command'])
    
        info = {
                "Events":event_names,
                "EventCodes":event_codes,
                "Alias":alias,
                "Names":names,
                "Values_list":values_list,
                "Values":values,
                "Timestamps":timestamps,
                "Machine":machine,
                "Kernel":kernel,
                "System":system,
                "Release":release,
                "Command":command
                }

        dg = pd.DataFrame(info)
        dg.to_csv(index=False, path_or_buf=output_file, line_terminator="\n")


    def dump_to_file(self, pmu_obj, output_file):
        
        with open(output_file, 'w+') as out:
           json.dump(pmu_obj.info, out)


    def n1(self, pmu_obj, options):
    
        from pmu_n1 import n1
        
        n1_obj = n1(pmu_obj)
        return n1_obj


    def v1(self, pmu_obj, options):
    
        from pmu_v1 import v1
        
        v1_obj = v1(pmu_obj)
        return v1_obj


    def topdown(self, pmu_obj, options):
        
        pmap = {"neoverse-n1": self.n1(pmu_obj, options),
                "neoverse-v1": self.v1(pmu_obj, options)}[options['platform']]
        
        return pmap


    def process_TD(self, pmu_obj, options):

        pmu_obj_new = self.recreate_pmu_obj(pmu_obj, options)
        pmu_obj_new.info['metadata'] = pmu_obj.info['metadata'] 
        core_obj = self.topdown(pmu_obj_new, options)
        final_obj =  core_obj.derive_perfmon_metrics()
        return final_obj


    def recreate_pmu_obj(self, pmu_obj, options):

        min_size = 65536
        pmu_obj_new = data_manager.PMU()
        for event in pmu_obj.info['counter'].keys():
            size = len(pmu_obj.info['counter'][event]['Value'])
            if (size < min_size) and (size != 0):
                min_size = size

        for event in pmu_obj.info['counter'].keys():
            name = pmu_obj.info['counter'][event]['EventName']
            pmu_obj_new.info['counter'][name] = pmu_obj.info['counter'][event]
            pmu_obj_new.info['counter'][name]['Value'] = (pmu_obj.info['counter'][event]['Value'])[0:min_size]
        return pmu_obj_new




