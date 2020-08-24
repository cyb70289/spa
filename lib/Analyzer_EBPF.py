#!usr/bin/python3

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
# This file handles analysis of data captured through EBPF tracing. 

import json
import data_manager
import pandas as pd
import os
import re
from statistics import mean, stdev

class Analyze:

    def __init__(self, log, options):

        self.options = options
        self.log = log
        self.function_name = []
        self.event_name = []
        self.latency = []
        self.run = []
        self.value = []
        self.count = []
        self.machine = []
        self.kernel = []
        self.release = []
        self.system = []
        self.code = []
        self.command = []
        self.timestamp = [] 
        self.dg = None
        self.dg_latency = None
     
    def gather_data(self):

        self.log.info("Ebpf Data Analysis is starting")
        pd.options.mode.chained_assignment = None  # default='warn'
        ebpf_result_list = {}
        pd.set_option('display.max_rows', None)
        pd.set_option('display.max_columns', None)
        pd.set_option('display.width', None)
        pd.set_option('display.max_colwidth', -1)
         
        if not self.options['compare'] == 'Current':
            for filename in os.listdir("ebpf_stats"):
                ebpf_result = data_manager.EBPF()
                with open("ebpf_stats/{}".format(filename), 'r') as ebpf_file:
                    f = json.load(ebpf_file)
                    ebpf_result_list[filename] = f 
        else:
            with open("ebpf_latest", "r") as ebpf_file:
                f = json.load(ebpf_file)
                ebpf_result_list['ebpf_latest'] = f
        
        
        count = 0
    
        for filename in ebpf_result_list.keys():
            ebpf = ebpf_result_list[filename]
            for k,v in ebpf['info'].items():
                for k1,v1 in v['Value']['counter']['value'].items():
                    self.run.append("RUN_{}".format(count))
                    self.function_name.append(k)
                    self.count.append(v['Value']['count'])
                    self.event_name.append(k1)
                    self.latency.append(v['Value']['counter']['latency'][k1])
                    self.value.append(v1)
                    self.timestamp.append(ebpf['metadata']['timestamp'])
                    self.machine.append(ebpf['metadata']['machine'])
                    self.kernel.append(ebpf['metadata']['kernel'])
                    self.system.append(ebpf['metadata']['system'])
                    self.release.append(ebpf['metadata']['release'])
                    self.code.append(ebpf['metadata']['code'])
                    self.command.append(ebpf['metadata']['command'])
            count = count +1
        
        print(len(self.latency), len(self.event_name), len(self.value)) 
        info = {
                "Event":self.event_name,
                "Run":self.run,
                "Function":self.function_name,
                "Value":self.value,
                "Count":self.count,
                "Latency":self.latency,
                "Count":self.count,
                "Timestamp":self.timestamp,
                "Machine":self.machine,
                "Kernel":self.kernel,
                "System":self.system,
                "Release":self.release,
                "Code":self.code,
                "Command":self.command
                }
        self.dg = pd.DataFrame(info)
        if self.options['compare'] == 'LBR':
            if len(self.run) > 1:
                self.latency_comparison_between_runs()
            else:
                self.log.error("Only one run has been performed")
        elif not self.options['compare'] == 'Current':
            self.compare_latency()
            self.compare_events()


    def compare_latency(self):
    
        values_list = {}
        tmp  = self.dg['Latency']
        self.dg['LMean'] = mean(tmp)
        self.dg['LStdev'] = stdev(tmp)
        self.dg['LDev'] = self.dg['Latency'] - self.dg['LMean']
        self.dg['ALV%'] = abs(self.dg['Latency'] - self.dg['LMean'])/self.dg['LMean'] * 100
        #print("\n\n--------------------------------------------------Showing Results------------------------------------------------------\n\n")
        #print(self.dg[['Function', 'Event', 'Latency', 'LMean', 'LDev', 'ALV%']])
 

    def compare_events(self):

        dg_list = []
        dg_final = None
        for i in pd.unique(self.dg['Event']):
           tmp = self.dg.query('Event == "{}"'.format(i))
           dg_list.append(tmp)
    
        values_list = {}
        for i in dg_list:
            tmp  = i['Value']
            i['CMean'] = mean(tmp)
            i['CStdev'] = stdev(tmp)
            i['CDev'] = i['Value'] - i['CMean']
            i['ACV%'] = abs(i['Value'] - i['CMean'])/i['CMean'] * 100
        dg_final = None
        for i in dg_list:
            dg_final = pd.concat([dg_final, i])
        self.dg = dg_final
        #print("\n\n--------------------------------------------------Showing Results------------------------------------------------------\n\n")
        #print(self.dg[['Event', 'Function', 'Latency', 'CMean', 'CDev', 'ACV%']])



    def latency_comparison_between_runs(self):

        dg_array = []
        dg_final = None

        for r1 in pd.unique(self.run):
            for name in pd.unique(self.function_name):
                for event in pd.unique(self.event_name):
                    tmp_data = {}
                    tmp_r1 = self.dg.query('Run == "{}" and Function == "{}" and Event == "{}"'.format(r1, name, event))
                    for r2 in self.run:
                        tmp_r2 = self.dg.query('Run == "{}" and Function == "{}" and Event == "{}"'.format(r2, name, event))
                        variance = abs(float(tmp_r1['Latency']) - float(tmp_r2['Latency'])) / float(tmp_r1['Latency'])
                        tmp_data['L"{}"WRT"{}"'.format(r2, r1)] = variance

                    tmp_r1['Latency_Comparison'] = [tmp_data]
                    dg_array.append(tmp_r1)
        
        dg_final = pd.concat(dg_array)

        self.dg_latency = dg_final
        print(dg_final[['Run', 'Function', 'Latency', 'Event', 'Latency_Comparison']])
