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
# This file manages the analysis of data collected by perf stat tool. 

import os
import sys
import data_manager
import re
import pandas as pd
from statistics import mean, stdev
import json
import matplotlib.pyplot as plt
import numpy as np

class analyzer:

    def __init__(self, log, options):
        
        self.options = options
        self.log = log
        self.key_list = {'cpu': ['%user', '%nice', '%system', '%iowait', '%steal', '%idle'],
                         'net_DEV': 'rxpck/s   txpck/s    rxkB/s    txkB/s   rxcmp/s   txcmp/s  rxmcst/s   %ifutil'.split(),
                         'net_TCP': 'active/s passive/s    iseg/s    oseg/s'.split(),
                         'net_UDP': 'idgm/s    odgm/s  noport/s idgmerr/s'.split(),
                         'net_SOCK': 'totsck    tcpsck    udpsck    rawsck   ip-frag    tcp-tw'.split(),
                         'mem': 'kbmemfree   kbavail kbmemused  %memused kbbuffers  kbcached  kbcommit   %commit  kbactive   kbinact   kbdirty'.split(),
                         'err_EDEV': 'rxerr/s   txerr/s    coll/s  rxdrop/s  txdrop/s  txcarr/s  rxfram/s  rxfifo/s  txfifo/s'.split(),
                         'err_ETCP': 'atmptf/s  estres/s retrans/s isegerr/s   orsts/s'.split(),
                         'io': 'tps      rtps      wtps      dtps   bread/s   bwrtn/s   bdscd/s'.split(),
                         'dev': 'tps     rkB/s     wkB/s     dkB/s   areq-sz    aqu-sz     await     %util'.split()}
        self.analyze_data()


    def analyze_data(self):
        
        self.log.info('Sysstat Data Analysis Started')
    
        pd.options.mode.chained_assignment = None  # default='warn'
        
        pd.set_option('display.max_rows', None)
        pd.set_option('display.max_columns', None)
        pd.set_option('display.width', None)
        pd.set_option('display.max_colwidth', -1)
        dg = None
        
        count = 0
        metrics = self.options['metrics'].split(',')
        for i in metrics:
            if not self.options['compare'] == 'Current':
                for filename in os.listdir("sar_logs/{}_stat".format(i)):

                    tmp = pd.read_csv("sar_logs/{}_stat/{}".format(i, filename))
                    runs = np.repeat("RUN_{}".format(count), len(tmp))
                    tmp["Runs"] = runs
                    tmp_dg = pd.DataFrame(tmp)
                    if count == 0:
                        dg = tmp_dg
                    else:
                        dg = pd.concat([dg, tmp_dg])
                    count = count + 1
                        
            else:
                    dg = pd.read_csv("result_links/{}_latest".format(i))
                    runs = np.repeat("RUN_{}".format(count), len(dg))
                    dg["Runs"] = runs 
       
            self.dg = dg
            runs = pd.unique(list(dg['Runs']))
            self.dg_analyzed = dg 
            self.aggr_data(i)
            if len(runs) > 1:
                
                if self.options['compare'] == 'All': 
                    self.compare_all(i)
               # if self.options['compare'] == 'Runs': 
                #    self.compare_between_runs(dg, tag, event_names) 
               # if self.options['compare'] ==  'Custom': 
                #    self.compare_custom(dg, value, self.options['key'], tag, event_names)
                #if self.options['compare'] == 'Profile': 
                 #   self.build_profile(dg, event_names, runs)
            self.dg_analyzed.to_csv("Analysis_Results/stat_analysis_{}".format(self.options["timestamp"]))

    
    def create_key(self, metric):

        metric_final = metric
        if metric == 'net':
            metric_final = "{}_{}".format(metric, self.options['net_type'])
        if metric == 'err':
            metric_final = "{}_{}".format(metric, self.options['err_type'])
    
        return metric_final


    def compare_all(self, metric):
    
        dg_final = self.dg_aggr
        metric_final = self.create_key(metric)
        for key in self.key_list[metric_final]:
            key = "{}_M".format(key)
            tmp  = dg_final[key]
            dg_final['{}_Mean'.format(key)] = mean(tmp)
            dg_final['{}_Stdev'.format(key)] = stdev(tmp)
            dg_final['{}_Dev'.format(key)] = dg_final[key] - dg_final['{}_Mean'.format(key)]
            dg_final['{}_AbsVariation%'.format(key)] = abs(dg_final[key] - dg_final['{}_Mean'.format(key)])/dg_final['{}_Mean'.format(key)] * 100
        self.dg_analyzed = dg_final
        print(dg_final)
    

    def aggr_data(self, metric):

        dg_list = []
        dg_final = None
        metric_final = self.create_key(metric)
         
        runs = pd.unique(list(self.dg['Runs']))
        for i in runs:
            tmp = self.dg.query('Runs == "{}"'.format(i))
            dg_list.append(tmp)

        for i in dg_list:
            for key in self.key_list[metric_final]:
                tmp  = i[key]
                i['{}_M'.format(key)] = (mean(tmp))
            i.drop(self.key_list[metric_final], inplace=True, axis=1)
            i.drop_duplicates(inplace=True)
        for i in dg_list:
            dg_final = pd.concat([dg_final, i])
        self.dg_aggr = dg_final
        print(dg_final)

