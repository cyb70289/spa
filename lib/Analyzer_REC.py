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
# This file handles analysis of data captured by the perf record tool. 

import re
import os
import json
import subprocess
import pandas as pd
import data_manager


class rec:

    def __init__(self, log, options):

        self.log = log
        self.dg = None
        self.options = options


    def analyze_rec(self):

        self.log.info("Perf RECORD Data Analysis is starting")    
        pd.set_option('display.max_rows', None)
        pd.set_option('display.max_columns', None)
        pd.set_option('display.width', None)
        pd.set_option('display.max_colwidth', -1)
        rec_result_list = {}
      
        if not self.options['compare'] == 'Current':
            for filename in os.listdir("PMU_rec_logs/records"):
                rec_result = data_manager.REC()
                with open("PMU_rec_logs/records/{}".format(filename), 'r') as rec_file:
                    f = json.load(rec_file)
                    rec_result_list[filename] = f
        else:
            with open("rec_data_latest", "r") as rec_file:
                f = json.load(rec_file)
                rec_result_list['rec_data_latest'] = f
    
        runs = []
        values = []
        count = 0
        timestamps = [] 
        names = [] 
        alias = []
        machine = []
        kernel = []
        system = []
        release = []
        code = []
        command = []
        
        move_forward = False
        for filename in rec_result_list.keys():
            rec = rec_result_list[filename]
            for i in rec['info'].keys():
                if float(rec['info'][i]) < self.options['Flevel']:
                    move_forward = True
                    break
                runs.append("RUN_{}".format(count))
                values.append(float(rec['info'][i]))
                timestamps.append(rec['metadata']['timestamp'])
                names.append(i)
                machine.append(rec['metadata']['machine'])
                code.append(rec['metadata']['code'])
                kernel.append(rec['metadata']['kernel'])
                system.append(rec['metadata']['system'])
                release.append(rec['metadata']['release'])
                command.append(rec['metadata']['command'])
            if move_forward:
                break
            count = count + 1
    
    
        info = {
                "Name":names,
                "Value":values,
                "Run":runs,
                "Timestamp":timestamps,
                "Machine":machine,
                "Code":code,
                "Kernel":kernel,
                "System":system,
                "Release":release,
                "Command":command
                }
        
        dg = pd.DataFrame(info)
        if self.options['filter']:
            dg = dg.query("{}".format(self.options['filter']))
        self.dg = dg
        dg_filter = self.filter_data(dg)
        if count > 1:
            self.compare_all(dg_filter)
    
    
    def filter_data(self, dg):
    
        dg_filter = dg.query('Value > 10')
        return dg_filter


    def compare_all(self, dg):
        
        dg = dg.sort_values(by=['Run'])
        diff_all = []
        var_all = []
        dg_list = []
        runs = pd.unique(dg['Run'])
        dg_aggr = []
        
        for run in runs:
            tmp = dg.query('Run == "{}"'.format(run))
            dg_list.append(tmp)
       

        for i in dg_list:
            names = pd.unique(i['Name'])
            run = i['Run'].values[0]
            for name in names:
                tmp = i.query('Name == "{}"'.format(name))
                diff_local = {}
                var_local = {}
                for run_2 in runs:
                    if not run_2 == run:
                        tmp_2 = dg.query('Run == "{}"'.format(run_2))
                        diff = 0.0
                        if name in tmp_2['Name'].values:
                            tmp_2 = tmp_2.query('Name == "{}" '.format(name))
                            diff = tmp['Value'].values[0] - tmp_2['Value'].values[0]
                        else:
                            diff = tmp['Value'].values[0]
                        diff_local["{}_{}".format(run, run_2)] = diff
                        var_local["{}_{}".format(run, run_2)] = abs(diff * 100)/ tmp['Value'].values[0]

                tmp['Diff'] = [diff_local]
                tmp['Var%'] = [var_local]
                dg_aggr.append(tmp)

        dg_final = pd.concat(dg_aggr)
        self.dg = dg_final
        #print(dg_final)








