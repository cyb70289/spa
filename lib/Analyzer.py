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

class Analyzer:

    def __init__(self, log, compare, apply_alias, name, cond, key=None):
        
        self.compare = compare
        self.apply_alias = apply_alias
        self.name = name
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
        self.code = []
        self.command = []
        self.architecture = []
        self.event_profile = {}
        self.dg = None
        self.cond = cond
        self.key = key
        self.log = log
        self.similarity = {}
        self.gather_data()


    def gather_data(self):
        self.log.info('Perf Stat Data Analysis Started')
    
        pd.options.mode.chained_assignment = None  # default='warn'
        pmu_result_list = {}
        
        pd.set_option('display.max_rows', None)
        pd.set_option('display.max_columns', None)
        pd.set_option('display.width', None)
        pd.set_option('display.max_colwidth', -1)

        if not self.compare == 'Current':
            for filename in os.listdir("PMU_logs"):
                pmu_result = data_manager.PMU()
                with open("PMU_logs/{}".format(filename), 'r') as pmu_file:
                    f = json.load(pmu_file)
                    pmu_result_list[filename] = f 
        else:
            with open("pmu_result_latest", "r") as stat_file:
                f = json.load(stat_file)
                pmu_result_list['pmu_result_latest'] = f
        count = 0
    
        for filename in pmu_result_list.keys():
            pmu = pmu_result_list[filename]
            for i in pmu['counter'].keys():
                self.event_names.append(i)
                self.runs.append("RUN_{}".format(count))
                self.values_list.append(pmu['counter'][i]['Value'])
                self.values.append(sum(pmu['counter'][i]['Value']))
                self.alias.append(pmu['counter'][i]['Alias'])
                self.timestamps.append(pmu['metadata']['timestamp'])
                self.names.append(pmu['metadata']['name'])
                self.code.append(pmu['metadata']['code'])
                self.machine.append(pmu['metadata']['machine'])
                self.kernel.append(pmu['metadata']['kernel'])
                self.system.append(pmu['metadata']['system'])
                self.release.append(pmu['metadata']['release'])
                self.command.append(pmu['metadata']['command'])
            count = count + 1
    
        info = {
                "Events":self.event_names,
                "Alias":self.alias,
                "Runs":self.runs,
                "Names":self.names,
                "Values":self.values,
                "Values_list":self.values_list,
                "Timestamps":self.timestamps,
                "Machine":self.machine,
                "Kernel":self.kernel,
                "System":self.system,
                "Release":self.release,
                "Command":self.command
                }

        dg = pd.DataFrame(info)
        if self.cond:
            dg = dg.query(self.cond)
       # dg.to_csv("dg_all.csv", index = False)

        self.dg = dg
        tag = 'Events'
        if self.apply_alias:
            tag = "Alias"
        runs = pd.unique(list(dg['Runs']))
        event_names = pd.unique(list(dg[tag]))
        
        if not len(runs) <= 1:

            if self.key:
                value = pd.unique(list(dg[self.key]))
            else:
                value = 'Events'

            event_names.sort()
            runs.sort()
            dg = dg.sort_values(by=[tag])
       #     print('\nKey used = {}'.format(tag))
            
                
            if self.compare == 'All': 
                self.compare_all(dg, tag, event_names)
                if len(dg['Values_list'][0]) > 1:
                    self.build_profile(dg, event_names, runs)
            if self.compare == 'Runs': 
                if len(runs) > 1:
                    self.compare_between_runs(dg, tag, event_names) 
            if self.compare ==  'Custom': 
                self.compare_custom(dg, value, self.key, tag, event_names)
            if self.compare == 'Profile': 
                self.build_profile(dg, event_names, runs)
        else:
            self.log.error('No Analysis can be done since only one Run has been performed')

    
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
        #print("\n\n--------------------------------------------------Showing Results------------------------------------------------------\n\n")
        #print(dg_final)
        #self.analyze(dg_list, "mean")
    
    
    def compare_between_runs(self, dg, tag, event_names):
        
        dg_list = []
        dg_final = None
        for i in event_names:
            tmp = dg.query('{} == "{}"'.format(tag, i))
            dg_list.append(tmp)
         
        for i in dg_list:
            base = 0
            tmp = i.query('Names == "{}"'.format(self.name))
            base_value = tmp['Values'].values 
            i['BAbsVariation%'] = abs((i['Values'] - base_value)/base_value) *100
            i['BVariation%'] = ((i['Values'] - base_value)/base_value) *100
        for i in dg_list:
            dg_final = pd.concat([dg_final, i])
        
        self.dg = dg_final
        #print("\n\n--------------------------------------------------Showing Results------------------------------------------------------\n\n")
        #print(dg_final)
        #self.analyze(dg_list, 1)
    
   
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
                values =  list(tmp_ev["Values_list"])[0]
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
