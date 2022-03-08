#!bin/python3

import yaml
import main as pa
import logging
from datetime import datetime
from bcc import BPF
import pandas as pd
import Analyzer as AE
from statistics import mean
import json
import sys
import re

sys.path.append("perfmon_cpu")

class stat:

    def __init__(self, options):

        self.type = options['type']
        self.input = options['input']
        self.command = options['command']
        self.counters = options['counters']
        self.filter = options['filter']
        self.applyalias = options['applyalias']
        self.interval = options['interval']
        self.mx_degree = options['mx_degree']
        self.verbosity = options['verbosity']
        self.style = options['style']
        self.compare = options['compare']
        self.name = options['name']
        self.base = options['base']
        self.regex = options['regex']
        self.repeat = options['repeat']
        self.key = options['key']
        self.code = options['code']
        self.platform = options['platform']
        self.arch = options['arch']
        self.index = options['index']
        self.extra_args = options['extra_args']


class record:

    def __init__(self, options):

        self.type = options['type']
        self.command = options['command']
        self.filter = options['filter']
        self.verbosity = options['verbosity']
        self.compare = options['compare']
        self.extra_args = options['extra_args']
        self.createflamegraph = options['createflamegraph']
        self.callgraph = options['callgraph']
        self.counters = options['counters']
        self.input = options['input']
        self.code = options['code']
        self.Flevel = options['Flevel']
        self.thorough = options['thorough']


class ebpf:

    def __init__(self, options):

        self.type = options['type']
        self.regex = options['regex']
        self.path = options['path']
        self.obfile = options['obfile']
        self.counters = options['counters']
        self.command = options['command']
        self.nooptimize = options['nooptimize']
        self.verbosity = options['verbosity']
        self.input = options['input']
        self.sens = options['sens']
        self.factor = options['factor']
        self.code = options['code']
        self.list = options['list']
        self.compare = options['compare']


class sar:

    def __init__(self, options):

        self.type = options['type']
        self.metrics = options['metrics']
        self.interval = options['interval']
        self.verbosity = options['verbosity']
        self.command = options['command']
        self.obfile = options['compare']
        self.counters = options['verbosity']
        self.net_type = options['net_type']
        self.err_type = options['err_type']
        self.dev_list = options['dev_list']
        self.compare = options['compare']



def parse_config():

    config = None
    with open("config.yaml") as f:
        config_main = yaml.load(f)
    
    spa_obj = pa.spa()
    
    virtif = config_main['virtif']
    jobs = {'stat': 0, 'record': 0, 'ebpf': 0, 'sar':0}

    with open(virtif['run_config']) as f:
         config = yaml.load(f)
    with open("run_configurations/defaults.yaml") as f:
         config_def = yaml.load(f)

    def_stat = config_def['stat']
    def_ebpf = config_def['ebpf']
    def_rec = config_def['record']
    def_sar = config_def['sar']

    

    if 'stat' in config.keys():
    
        options = setup_tools("stat", def_stat, config, virtif)
        stat_obj = stat(options)
        spa_obj.stat(stat_obj)
        if not options['type'] == 'Run':
                analyze_stat(spa_obj, options)
        jobs['stat'] += 1
    
    if 'record' in config.keys():  
    
        options = setup_tools("record", def_rec, config, virtif)
        record_obj = record(options)
        spa_obj.record(record_obj)
        if not options['type'] == 'Run':
            analyze_rec(spa_obj, options)
        jobs['record'] += 1

    if 'ebpf' in config.keys():  
    
        options = setup_tools("ebpf", def_ebpf, config, virtif)
        ebpf_obj = ebpf(options)
        spa_obj.ebpf(ebpf_obj)
        jobs['ebpf'] += 1
        if not options['type'] == 'Run':
            analyze_ebpf(spa_obj, options)
    
    if 'sar' in config.keys():  

        options = setup_tools("sar", def_sar, config, virtif)
        sar_obj = sar(options)
        spa_obj.sar(sar_obj)
        jobs['sar'] += 1

        if not options['type'] == 'Run':
            analyze_sar(spa_obj, options)

    if virtif['Slevel'] > 0:
        if jobs['record'] > 0 and jobs['ebpf'] > 0:
            merge_rec_ebpf_data(spa_obj)


def setup_tools(tool, def_stat, config, virtif):
        
    timestamp = datetime.timestamp(datetime.now())
    options_stat = config[tool]
    options_stat['code'] = timestamp
    options_stat['command'] = virtif['command']
    arg_replacer(options_stat)
    for key in options_stat.keys():
        def_stat[key] = options_stat[key]
    return def_stat 
        


def arg_replacer(options):
    for i, arg in enumerate(sys.argv):
        if i > 0:
            match = re.search(r'(\S+)\s*=(.*)', arg)
            if match:
                key = match.group(1)
                value = match.group(2)
                if not key == "mx_degree":
                    options[match.group(1)] = match.group(2).strip()
                else:
                    options[key] = int(value)


def analyze_ebpf(spa_obj, options):

    ebpf_data = spa_obj.ebpf_record.data.dg
        
    ebpf_data.to_csv("../output/ebpf_data.csv", index = False)
    print(ebpf_data[['Run', 'Function', 'Latency', 'Event', 'Count', 'Value']])


def analyze_sar(spa_obj, options):

#    sar_data = spa_obj.sar_stat.dg_analyzed
        
    #sar_data.to_csv("../output/ebpf_data.csv", index = False)
    print(sar)


def analyze_rec(spa_obj, options):

    record_data = spa_obj.pmu_record.data.dg
    record_data = record_data.query('Value > {}'.format(options['Flevel']))
    dump_output(record_data, "record_data")
    print(record_data[['Run', 'Name', 'Value']])


def merge_rec_ebpf_data(spa_obj):

    record_data = spa_obj.pmu_record.data.dg
    ebpf_data = spa_obj.ebpf_record.data.dg
    match_name = []
    ebpf_function = pd.unique(ebpf_data['Function'])
    for name in list(record_data['Name']):
        if name in ebpf_function:
            match_name.append(name)
    arr = []
    
    for name in match_name:
        tmp = record_data.query('Name == "{}"'.format(name))
        tmp_ebpf = ebpf_data.query('Function == "{}"'.format(name))
        latency = list(tmp_ebpf['Latency'])[0]
        count = list(tmp_ebpf['Count'])[0]
        tmp['Ebpf_latency'] = latency
        tmp['Ebpf_count'] = count
        arr.append(tmp)
    try:
        rec_ebpf_data = pd.concat(arr)
        rec_ebpf_data = rec_ebpf_data.sort_values(by=['Value']) 
        dump_output(rec_ebpf_data, "record_ebpf_data")

        print(rec_ebpf_data[['Name', 'Value', 'Ebpf_latency', 'Ebpf_count']])
    except ValueError:
        print('Cannot find values to match')
        pass


def analyze_stat(spa_obj, options):

   stat_data = spa_obj.pmu_stat.data.dg
   tmp = stat_data.sort_values(by = ['Events', 'Runs'])
   dump_output(tmp, "stat_data")
   size = len(pd.unique(tmp['Runs']))
   if options['compare'] == 'Profile' and size > 1:

       print('-----------------------------Similarity Index of Runs--------------------------')
       sim = spa_obj.pmu_stat.data.similarity
       for key in sim.keys():
           if mean(sim[key]) > int(options['Flevel']):
               print('{} = {}'.format(key, mean(sim[key])))
   
   elif options['compare'] == 'All' and size > 1:
        print(tmp[['Events', 'Alias', 'Runs', 'Names', 'Values', 'Mean', 'AbsVariation%', 'Dev', 'Command']])
   elif options['compare'] == 'Runs' and size > 1:
        print(tmp[['Events', 'Alias', 'Runs', 'Names', 'Values', 'BAbsVariation%', 'BVariation%']])
   elif options['compare'] == 'Custom' and size > 1:
        print(tmp[['Events', 'Alias', 'Runs', 'Names', 'Values', 'RelVar%']])
   elif size == 1:
        print(stat_data[['Runs', 'Names', 'Events', 'Alias', 'Values', 'Values_list']])
   else:
        print('NO DATA FOUND')
        exit()



def ebpf_analyzer(symbol_re, options):

   functions = BPF.get_user_functions_and_addresses(name=options['path'], sym_re=symbol_re)
   if len(functions) > 0:
       return True    

def dump_output(data, filename):
    data.to_csv("../output/"+filename+".csv", index=False)

def set_logger(self, is_verbose):

   logging.basicConfig(level=logging.INFO,
                       format='%(asctime)s %(levelname)-7s %(message)s',
                       datefmt='%m-%d %H:%M:%S',
                       filename='profiler.log',
                       filemode='a')
   if is_verbose:
       console = logging.StreamHandler()
       console.setLevel(logging.INFO if is_verbose else logging.WARNING)
       formatter = logging.Formatter('%(asctime)s %(levelname)-7s %(message)s')
       console.setFormatter(formatter)
       logging.getLogger('').addHandler(console)


if __name__ == '__main__':
    parse_config()
