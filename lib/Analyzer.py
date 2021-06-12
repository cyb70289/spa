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

class Analyzer:

    def __init__(self, log, options):
        
        self.options = options
        self.event_names = []
        self.runs = []
        self.values = []
        self.values_list = []
        self.timestamps = [] 
        self.names = [] 
        self.alias = []
        self.machine = []
        self.kernel = []
        self.system = []
        self.release = []
        self.event_codes = []
        self.code = []
        self.command = []
        self.architecture = []
        self.event_profile = {}
        self.dg = None
        self.log = log
        self.similarity = {}
        self.analyze_data()


    def analyze_data(self):
        self.log.info('Perf Stat Data Analysis Started')
    
        pd.options.mode.chained_assignment = None  # default='warn'
        pmu_result_list = {}
        
        pd.set_option('display.max_rows', None)
        pd.set_option('display.max_columns', None)
        pd.set_option('display.width', None)
        pd.set_option('display.max_colwidth', -1)
        dg = None
        
        count = 0
        if not self.options['compare'] == 'Current':
            for filename in os.listdir(self.options['csv_path']):
                tmp = pd.read_csv("{}/{}".format(self.options['csv_path'], filename))

                runs = np.repeat("RUN_{}".format(count), len(tmp))
                tmp["Runs"] = runs
                tmp_dg = pd.DataFrame(tmp)
                if count == 0:
                    dg = tmp_dg
                else:
                    dg = pd.concat([dg, tmp_dg])
                count = count + 1
                    
        else:
                dg = pd.read_csv("csv_result_latest")
                runs = np.repeat("RUN_{}".format(count), len(dg))
                dg["Runs"] = runs 
        
        if self.options['filter']:
            dg = dg.query(self.options['filter'])

        self.dg = dg
        tag = 'Events'
        if self.options['alias']:
            tag = "Alias"
        runs = pd.unique(list(dg['Runs']))
        event_names = pd.unique(list(dg[tag]))
        
        if not len(runs) <= 1:

            if self.options['compare'] ==  'Custom': 
                value = pd.unique(list(dg[self.options['key']]))
            else:
                value = 'Events'

            event_names.sort()
            runs.sort()
            dg = dg.sort_values(by=[tag])

                
            if self.options['compare'] == 'All': 
                self.compare_all(dg, tag, event_names)
            if self.options['compare'] == 'Runs': 
                if len(runs) > 1:
                    print("here")
                    self.compare_between_runs(dg, tag, event_names) 
            if self.options['compare'] ==  'Custom': 
                self.compare_custom(dg, value, self.options['key'], tag, event_names)
            if self.options['compare'] == 'Profile': 
                self.build_profile(dg, event_names, runs)
        else:
            self.log.error('No Analysis can be done since only one Run has been performed')
        self.dg.to_csv("Analysis_Results/{}".format(self.options["timestamp"]))



    def compare_all(self, dg, tag, event_names):
    
        dg_list = []
        dg_final = None
        for i in event_names:
            tmp = dg.query('{} == "{}"'.format(tag, i))
            dg_list.append(tmp)
    
        values_list = {}
        for i in dg_list:
            tmp  = i['Values']
            i['Mean'] = mean(tmp)
            i['Stdev'] = stdev(tmp)
            i['Dev'] = i['Values'] - i['Mean']
            i['AbsVariation%'] = abs(i['Values'] - i['Mean'])/i['Mean'] * 100
        dg_final = None
        for i in dg_list:
            dg_final = pd.concat([dg_final, i])
        self.dg = dg_final
    
    
    def compare_between_runs(self, dg, tag, event_names):
        
        dg_list = []
        dg_final = None
        for i in event_names:
            tmp = dg.query('{} == "{}"'.format(tag, i))
            dg_list.append(tmp)
         
        for i in dg_list:
            base = 0
            tmp = i.query('Names == "{}"'.format(self.options['base']))
            base_value = tmp['Values'].values 
            i['BAbsVariation%'] = abs((i['Values'] - base_value)/base_value) *100
            i['BVariation%'] = ((i['Values'] - base_value)/base_value) *100
        for i in dg_list:
            dg_final = pd.concat([dg_final, i])
        
        self.dg = dg_final
    
   
    def compare_custom(self, dg, value, key, tag, event_names): #key must not be event or alias

        dg_list = []
        dg_aggr = []
        dg = dg.sort_values(by=[key, tag])
        for i in value:
            tmp = dg.query('{} == "{}"'.format(key, i))
            dg_list.append(tmp)
        all_data = [] 
        for i in dg_list:
            for e in event_names:
                tmp_i = i.query('{} == "{}"'.format(tag, e))
                relvar = {}
                for j in dg_list:
                    tmp_j = j.query('{} == "{}"'.format(tag, e))
                    variance = 0.0
                    if int(tmp_i['Values']) > 0:
                        variance = float(abs(int(tmp_j['Values']) - int(tmp_i['Values'])) / int(tmp_i['Values']))
                    key_t = "{}WRT{}".format(tmp_j[key].values[0], tmp_i[key].values[0])
                    relvar[key_t] = variance
                tmp_i['RelVar%'] = [relvar]
                dg_aggr.append(tmp_i)
        self.dg = pd.concat(dg_aggr)
        #print(self.dg[[key, tag, 'Values', 'RelVar']])


    def analyze(self, dg_list, Flevel):
        
        dg_final = None
        for i in dg_list:
            tmp = i[i['AbsVariation%'] >= Flevel]
            dg_final = pd.concat([dg_final, tmp])
    
        return dg_final


    def build_profile(self, dg, event_names, runs):

        import numpy as np
        profile = []
        for i in runs:
            tmp = dg.query('Runs == "{}"'.format(i))
            for j in event_names:
                tmp_ev = tmp.query('Events == "{}"'.format(j))
                values = list(tmp_ev["Values_list"])[0]
                values = values.replace('[', '')
                values = values.replace(']', '')
                values = values.replace(' ', '').split(',')
                values = map(int, values)
                values = list(values)
                index = np.arange(len(values))
                line, slope, inter = self.create_bf_line(index, values)
                tmp_profile = {'line':line, 'slope':slope, 'inter':inter}
                profile.append(tmp_profile)
        
        self.dg = self.dg.sort_values(by=['Runs', 'Events'])
        self.dg['Profile'] = profile
        self.compare_profiles(runs, event_names)
            
           
    def create_bf_line(self, xs, ys):

        m = (((mean(xs)*mean(ys)) - mean(xs*ys)) /
             ((mean(xs)*mean(xs)) - mean(xs*xs)))
             
        b = mean(ys) - m*mean(xs)
                 
        regression = []
        for i in xs:
            regression.append(i*m + b)

        return regression, m, b


    def compare_profiles(self, runs, event_names):

        similarity_all = []
        dg_aggr = []
        for r1 in runs:
            for e in event_names:
                similarity = {}
                tmp_r1 = self.dg.query('Runs == "{}" and Events == "{}"'.format(r1, e))
                pro_r1 = tmp_r1['Profile'].values[0]
                for r2 in runs:
                    tmp_r2 = self.dg.query('Runs == "{}" and Events == "{}"'.format(r2, e))
                    pro_r2 = tmp_r2['Profile'].values[0]
                    variance = abs(int(pro_r1['slope']) - int(pro_r2['slope'])) / abs(int(pro_r2['slope']))
                    if variance > 1:
                        variance = 1
                    key = 'Sim{}WRT{}'.format(r1,r2)
                    similarity[key] = (1 - variance) * 100
                #similarity_all.append(similarity)
                tmp_r1['Similarity'] = [similarity]
                dg_aggr.append(tmp_r1)
        #self.dg['Similarity'] = similarity_all
        self.dg = pd.concat(dg_aggr)

        #print(self.dg[['Runs', 'Events', 'Similarity']])
        self.run_similarity(runs)


    def run_similarity(self, runs):

        sim = {}
        for r1 in runs:
            tmp_r = self.dg.query('Runs == "{}"'.format(r1))
            sim_dg = tmp_r['Similarity']
            for sim_single in sim_dg:
                for key in sim_single.keys():
                    if key in sim.keys():
                        sim[key].append((sim_single[key]))
                    else:
                        sim[key] = []
                        sim[key].append((sim_single[key]))
        self.similarity = sim
