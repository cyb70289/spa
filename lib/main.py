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
# This file instantiates all the coomponents for the profiler automation tool. 


import os
import warnings
import sys
import subprocess
import spa_pmu
import Analyzer
import data_manager
import argparse
import json
import platform
from defines import Verbosity, Style
from datetime import datetime
import analyze_ebpf as ae
import Analyzer_REC as AR
import logging 
import Analyzer_EBPF as AE
import spa_sar
import analyze_sar 

class spa:

    def __init__(self):

        self.log = logging.getLogger('')
        self.pmu_stat = None
        self.pmu_record = None
        self.ebpf_record = None
        self.sar_stat = None
        if not os.path.exists("Analysis_Results"):
            os.mkdir("Analysis_Results")


    def start_pmu_stat(self, options):
         
        pmu_obj = data_manager.PMU()
        output_file = ""
        if not os.path.exists("JSON_logs"):
            os.makedirs("JSON_logs/Regular_logs")
            os.mkdir("JSON_logs/TopDown_logs")
        
        if not os.path.exists("CSV_logs"):
            os.makedirs("CSV_logs/Topdown")
            os.mkdir("CSV_logs/Regular")
       
        if options['type'] == "TD" or options['type'] == "TDA":
            options['output_path'] = "JSON_logs/TopDown_logs"
            options['csv_path'] = "CSV_logs/Topdown"
        else:
            options['output_path'] = "JSON_logs/Regular_logs"
            options['csv_path'] = "CSV_logs/Regular"
        timestamp = datetime.timestamp(datetime.now())
        options['timestamp'] = timestamp

        if options['type'] != "Analyze" and options['type'] != "TDA":
            for _ in range(options['repeat']):
                pmu_obj = data_manager.PMU()
                
                output_file = "{}/pmu_result_{}".format(options['output_path'], timestamp)
                self.setup_metadata(pmu_obj, options)

                options['output_file'] = output_file
                pmu_obj.info['metadata']['timestamp'] = timestamp
                pmu_obj.info['metadata']['name'] = options['name']
                pmu_obj.info['metadata']['command'] = options['command']

                if 'interval' in options.keys():
                    pmu_obj.info['metadata']['interval'] = options['interval']
    
                pmu_obj.info['counter'] = options['counter_info']
    
                options['output_file'] = output_file 
                subprocess.call("rm pmu_result_latest", shell=True) 
                subprocess.call("ln -s {} pmu_result_latest".format(output_file), shell=True) 
                options['log'] = self.log 
                try:
                    stat_obj = spa_pmu.spa_pmu(self.log)
                    stat_obj.perform_perf_stat(pmu_obj, options)
                except KeyboardInterrupt:
                    self.dump_to_file(pmu_obj, output_file)
                
        if not options['type'] == "Run":
             pmu_obj.data = self.compare_data(options)
         
        
        self.pmu_stat = pmu_obj
    
    
    def setup_metadata(self, pmu_obj, options):
    
                pmu_obj.info['metadata']['system'] = platform.uname()[0]
                pmu_obj.info['metadata']['code'] = options['code']
                pmu_obj.info['metadata']['machine'] = platform.uname()[1]
                pmu_obj.info['metadata']['kernel'] = platform.uname()[2]
                pmu_obj.info['metadata']['release'] = platform.uname()[3]
                pmu_obj.info['metadata']['architecture'] = platform.uname()[4]
    
    
    def start_ebpf(self, options):
        
        ebpf_obj = data_manager.EBPF()
        timestamp = datetime.timestamp(datetime.now())
        ebpf_obj.info['metadata']['timestamp'] = timestamp
        ebpf_obj.info['metadata']['command'] = options['command']
        self.setup_metadata(ebpf_obj, options)

        if not options['verbosity'] == 'Low':
            self.set_logger(True)
        else:
            self.set_logger(False)

        if not options['type'] == 'Analyze':
            ae.analyze_ebpf(self.log, ebpf_obj, options)

        if not options['type'] == 'Run':
            obj = AE.Analyze(self.log, options)
            obj.gather_data() 
            ebpf_obj.data = obj

        self.ebpf_record = ebpf_obj


    def compare_data(self, options):
    
        analyzer = Analyzer.Analyzer(self.log, options)
        return analyzer


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


    def dump_to_file(self, pmu_obj, output_file):
        
        with open(output_file, 'w+') as out:
           json.dump(pmu_obj.info, out)
    
    
    def gather_pmu_json(self, pmu_file):
       
        pmu_list = None 
        with open(pmu_file) as f:
            pmu_list = json.load(f)
        return pmu_list
    
    
    def record_start(self, options):

        rec_obj = data_manager.REC()
        if not options['type'] == 'Analyze':
            
            
            rec_obj.info['metadata']['timestamp'] = options['timestamp']
            rec_obj.info['metadata']['command'] = options['command']
            self.setup_metadata(rec_obj, options)
            spa_obj = spa_pmu.spa_pmu(self.log)
            spa_obj.perform_perf_rec(rec_obj, options)
            
            if options['type'] == 'All':
                obj = AR.rec(self.log, options)
                obj.analyze_rec()
                rec_obj.data = obj
        else:
            
            obj = AR.rec(self.log, options)
            obj.analyze_rec()
            rec_obj.data = obj

        self.pmu_record = rec_obj


    def record(self, args):
    
        options = {}
        
        timestamp = datetime.timestamp(datetime.now())
        options['timestamp'] = timestamp 

        if not args.type == 'Analyze' and args.command == 'None':
            exit('Command Needs to be provided unless Analyzing')
        
        if not os.path.exists("PMU_rec_logs/record_{}".format(timestamp)):
            os.makedirs("PMU_rec_logs/record_{}/".format(timestamp))
        if not os.path.exists('PMU_rec_logs/records'):    
            os.makedirs("PMU_rec_logs/records".format(timestamp))
        
        options['cf'] = args.createflamegraph
        options['Flevel'] = args.Flevel
        options['callgraph'] = args.callgraph
        options['thorough'] = args.thorough
        
        if args.verbosity == 'High':
            options['verbosity'] = Verbosity.High
            self.set_logger(True)
        else:
            self.set_logger(False)
        
        if args.extra_args:
            options['extra_args'] = args.extra_args
        options['command'] = args.command
        
        if args.counters or args.input:
            options['event_list'] = self.create_event_list(args)[0]
        
        options['type'] = args.type 
        if args.type == 'Analyze':
            if not args.compare:
                self.log.warning("No Compare type provided! Using All as Default!")
            options['compare'] = args.compare
        
        options['filter'] = args.filter
        options['compare'] = args.compare
        
        if args.code:
            options['code'] = args.code
        else:
            timestamp = datetime.timestamp(datetime.now())
            options['code'] = timestamp
        self.record_start(options)


    def ebpf_create_event_list(self, args):

        event_list = []
        event_name = "EventName"
        if args.input:
            pmu_list = self.gather_pmu_json("{}".format(args.input))
            for i in pmu_list:
                event_list.append(i[event_name])
        else:
            event_list = (args.counters).split(',')
        return event_list


    def create_event_list(self, args):
   
        event_list = []
        counter_info = {}
        index = args.index
        event_name = "EventName"
        event_code = "EventCode"
        
        if args.type == "TD":
            pmu_list = self.gather_pmu_json("cpu_json/{}.json".format(args.platform))
            for i in pmu_list:
                alias = "EventName"

                if args.applyalias and 'Alias' in i.keys():
                   alias = "Alias"
                
                if index == event_code:
                    key = self.generate_raw_counter(args, i)
                else:
                    key = i[index]
                
                event_list.append(key)
                counter_info[key] = {'EventName':i[event_name], 'Alias':i[alias], 'EventCode':i[event_code],  'Value':[0], 'Timestamp':[]}
        else:
            if args.input:
                pmu_list = self.gather_pmu_json("{}".format(args.input))
                if not args.regex:
                    for i in pmu_list:
                        alias = "EventName"

                        if args.applyalias and 'Alias' in i.keys():
                            alias = "Alias"

                        if not args.regex:
                            event_list.append('r'.join(i[index]) if index == event_code else  i[index])
                            counter_info[i[event_name]] = {'EventName':i[event_name], 'Alias':i[alias], 'EventCode':i[event_code],  'Value':[0], 'Timestamp':[]}
                        else:
                            regex = re.compile(args.regex)
                            match = regex.match(i[event_name])
                            if match:
                                event_list.append(i[event_name])
                                counter_info[i[event_name]] = {'EventName':i[event_name], 'Alias':i[alias], 'EventCode':i[event_code],  'Value':[0], 'Timestamp':[]}
            else:
                event_list = (args.counters).split(',')
                for i in event_list:
                    counter_info[i] = {'EventName':i, 'Alias':i, 'EventCode':i, 'Value':[], 'Timestamp':[]}
        print(event_list)
        return [event_list, counter_info]
    
    
    def stat(self, args):
    
        options = {}



        if not args.type == 'Analyze' and args.command == 'None':
            self.log.error("Command not provided")
            exit('Command Needs to be provided unless Analyzing')
       
        options['verbosity'] = args.verbosity
        if args.verbosity == 'High':
            self.set_logger(True)
        else:
            self.set_logger(False)
            
        if args.type == 'Analyze' and args.compare == 'Runs':
            if args.base == 'Noname':
                sys.exit("Please provide the name of the run to be baselined with -B")
    
        
        if args.style == 'Iterate':
            options['style'] = Style.Iterate
        else:
            options['style'] = Style.Normal
         
        if args.compare == 'Custom':
            if not args.key:
                sys.exit("Key needs to be provided with the Custom Compare Analyze setting")
            else:
                options['key'] = args.key

        options['extra_args'] = args.extra_args
        options['compare'] = args.compare
        if not args.type == 'Analyze':
            info = self.create_event_list(args)
            options['event_list'] = info[0]
            options['counter_info'] = info[1]
        else:
            if args.compare == 'None':
                self.log.warning("No compare type provided using All as the default compare type")
                options["compare"] = 'Current'

        options['mx_degree'] = args.mx_degree

        if args.interval:
            options['interval'] = args.interval
        if args.code:
            options['code'] = args.code
        else:
            timestamp = datetime.timestamp(datetime.now())
            options['code'] = timestamp

        options['filter'] = args.filter
        options['command'] = args.command
        options['repeat'] = args.repeat
        options['name'] = args.name
        options['base'] = args.base
        options['type'] = args.type
        options['alias'] = args.applyalias
        options['arch'] = args.arch
        options['platform'] = args.platform
        
        self.start_pmu_stat(options)
    
    
    def ebpf(self, args):
    
        options = {}
    
        options['verbosity'] = args.verbosity
        options['regex'] = args.regex
        if args.counters:
            options['counters'] = args.counters
        options['event_list'] = []
        if args.input:
            if args.regex == 'All':
                args.regex = None
            event_list = self.ebpf_create_event_list(args)
            if args.sens:
                if args.sens == 'Max':
                    options['event_list'].append(','.join(i for i in event_list))
                elif args.sens == 'Custom':
                    while i < rangs(len(options['event_list'])):
                        event_tmp = event_list[0] 
                        for j in range(args.factor):
                             event_tmp = event_tmp + ',' + event_list[i+j]
                        options['event_list'].append(event_tmp)
                        i = i + args.factor

        else:
            options['event_list'].append(args.counters)

        if args.obfile:
            options['obfile'] = args.obfile
        else:
            options['obfile'] = args.path

        if args.list:
            options['list'] = args.list

        options['path'] = args.path
        options['command'] = args.command
        options['nooptimize'] = args.nooptimize
        options['type'] = args.type
        options['compare'] = args.compare
        if args.code:
            options['code'] = args.code
        else:
            timestamp = datetime.timestamp(datetime.now())
            options['code'] = timestamp
        self.start_ebpf(options)
   

    def sar(self, args):

        options = {}
        if args.verbosity == 'High':
            self.set_logger(True)
        else:
            self.set_logger(False)
        options['metrics'] = args.metrics
        options['interval'] = args.interval
        options['command'] = args.command
        options['net_type'] = args.net_type
        options['err_type'] = args.err_type
        options['type'] = args.type
        options['compare'] = args.compare
        if args.dev_list:
            options['dev_list'] = args.dev_list
        options['verbosity'] = args.verbosity
        timestamp = datetime.timestamp(datetime.now())
        options['timestamp'] = timestamp
        self.start_sar(options)


    def start_sar(self, options):

        if not os.path.exists("sar_logs"):
            os.makedirs('sar_logs/cpu_stat')
            os.makedirs('sar_logs/net_stat')
            os.makedirs('sar_logs/mem_stat')
            os.makedirs('sar_logs/dev_stat')
            os.makedirs('sar_logs/err_stat')
            os.makedirs('sar_logs/io_stat')

        self.create_sl()
        if not options['type'] == "Analysis":
            sar_obj = spa_sar.spa_sar(self.log, options)
        analysis_obj = analyze_sar.analyzer(self.log, options)
        self.sar_stat = analysis_obj


    def create_sl(self):

        if not os.path.exists("result_links"):
            os.mkdir('result_links')

    def generate_raw_counter(self, options, event):

        if options.arch == "ARM":
                return event["EventCode"].replace("0x", "r")
        if options.arch == "Intel":
                return "r{}{}".format(event["UMask"].replace("0x", ""), event["EventCode"].replace("0x", ""))
             
    
    def parse_input(self):
    
        parser = argparse.ArgumentParser()
        subparser = parser.add_subparsers(dest='cmd')
        subparser.required = True
    
        stat_parser = subparser.add_parser('stat', help='perfrom perf stat')
        stat_parser.set_defaults(func=self.stat)
        record_parser = subparser.add_parser('record', help='perform perf record')
        record_parser.set_defaults(func=self.record)
        ebpf_parser = subparser.add_parser('ebpf', help='perform ebpf analysis')
        ebpf_parser.set_defaults(func=self.ebpf)
        sar_parser = subparser.add_parser('sar', help='perform system analysis')
        sar_parser.set_defaults(func=self.sar)
        
        stat_parser.add_argument("-v", "--verbosity",  help="increase verbosity", choices=['Low', 'Medium', 'High'], default = 'Low', type=str)
        stat_parser.add_argument("-i", "--input", help="input pmu counters file [json]", required=False)
        stat_parser.add_argument("--index", help="Key in the input file to be used for perf [either code or name]", choices=['EventCode','EventName'],
                                 default="EventCode", required=False)
        stat_parser.add_argument("-c", "--counters", help="list of counters seperated by , ", type=str)
        stat_parser.add_argument("-p", "--platform", help="The current processor model for Top down analysis [Only valid when type='TD']", choices=["neoverse-n1"], default="neoverse-n1", type=str)
        stat_parser.add_argument("--arch", help="The current architecture", choices=["ARM, Intel"], default="ARM", type=str)
        stat_parser.add_argument("-s", "--style", help="Style of sampling [Default is Iterate]", choices=['Iterate', 'Normal'], default='Iterate', type=str)
        stat_parser.add_argument("-mx", "--mx_degree", help="Multiplexing limit for iterate style [default is 1]", default=1, type=int)
        stat_parser.add_argument("-r", "--regex", help="Regular Expression for matching events to profile", default="", type=str)
        stat_parser.add_argument("-C", "--compare", help="Compare gathered data", choices=['All', 'Runs', 'Profile', 'Custom', 'Current'], default="Current", type=str)
        stat_parser.add_argument("--key", help="Key to compare with in custom setting", default="Runs", type=str)
        stat_parser.add_argument("-n", "--repeat", help="Repeat profiling for n times", default = 1, type=int)
        stat_parser.add_argument("-N", "--name", help="Unique Run Name", default="Noname", type=str)
        stat_parser.add_argument("-B", "--base", help="Unique Run Name for baseline", default="Noname", type=str)
        stat_parser.add_argument("-t", "--type", help="Run Type", choices=['Analyze', 'All', 'Run', 'TD', 'TDA'], default="Run", type=str)
        stat_parser.add_argument("--applyalias", help="Make Alias key instead of EventName", action='store_true')
        stat_parser.add_argument("-I","--interval", help="Interval in miliseconds to sample", type=str)
        stat_parser.add_argument("--filter", 
                                 help="Add a filter to the data needed to analyze.Provide a query condition such as:\"{Machine != \\\"2p8168\\\"}\"",
                                 type=str)
        stat_parser.add_argument("--extra_args", help='perf stat extra arguments', type=str, default="") 
        stat_parser.add_argument("--command", help="Command to profile", type=str)
        
        record_parser.add_argument("-v", "--verbosity",  help="increase verbosity", choices=['Low', 'Medium', 'High'], default = 'Low', type=str)
        record_parser.add_argument("-i", "--input", help="input pmu counters file [json]", required=False)
        record_parser.add_argument("-c", "--counters", help="list of counters seperated by , ", type=str)
        record_parser.add_argument("-cf", "--createflamegraph", help='create flamegraphs', action='store_true') 
        record_parser.add_argument("-g", "--callgraph", help='generate call graphs', action='store_true') 
        record_parser.add_argument("--extra_args", help='perf record extra arguments', type=str) 
        record_parser.add_argument("--command", help="Command to profile", type=str)
        record_parser.add_argument("--Flevel", help="Sample Filter Level", type=int, default=10)
        record_parser.add_argument("--thorough", help="Sample Filter Level", type=bool, default=False)
        record_parser.add_argument("-C", "--compare", help="Compare gathered data", choices=['All', 'Runs', 'Profile', 'Custom', 'Current'], default="Current", type=str)
        record_parser.add_argument("--filter", 
                                   help="Add a filter to the data needed to analyze.Provide a query condition such as:\"{Machine != \\\"2p8168\\\"}\"", default='',
                                   type=str)
        record_parser.add_argument("-t", "--type", help="Run Type", choices=['Analyze', 'All', 'Run'], default="Run", type=str)
    
        ebpf_parser.add_argument("-R", "--regex", help="functions to profile [default is All]", type=str, default='All')
        ebpf_parser.add_argument("-L", "--list", help="functions to profile seperated by ,", type=str, default='')
        ebpf_parser.add_argument("-P", "--path", help="path to binary", type=str)
        ebpf_parser.add_argument("-O", "--obfile", help="path to object file", type=str)
        ebpf_parser.add_argument("-i", "--input", help="input pmu counters file [json]", required=False)
        ebpf_parser.add_argument("-t", "--type", help="Run or Analyze Data or do both", default='All', choices=['Run', 'All', 'Analyze'], type=str)
        ebpf_parser.add_argument("-c", "--counters", help="pmu counters to profile", type=str)
        ebpf_parser.add_argument("--sens", help="counters monitor sensitivity", type=str, default='Max', choices=['Max', 'Custom'])
        ebpf_parser.add_argument("--factor", help="Number of counters to sample simultaneously", type=int, default=1)
        ebpf_parser.add_argument("--nooptimize", help="do not apply auto-filtering of functions", action='store_true')
        ebpf_parser.add_argument("--command", help="Command to profile", type=str)
        ebpf_parser.add_argument("-C", "--compare", help="Compare gathered data", choices=['All', 'LBR', 'Profile', 'Custom', 'Current'], default="Current", type=str)
        ebpf_parser.add_argument("-v", "--verbosity",  help="increase verbosity", choices=['Low', 'Medium', 'High'], default = 'Low', type=str)
    
        sar_parser.add_argument("-m", "--metrics", help="Metrics to be captured (seperated by ,); Supported values: cpu,net,mem,dev,io,err", type=str, default="cpu" )
        sar_parser.add_argument("-I", "--interval", help="Intervals to capture metrics", default="1")
        sar_parser.add_argument("-t", "--type", help="Sar mode", choices=["Runs", "All", "Analysis"], default="All")
        sar_parser.add_argument("-C", "--compare", help="Compare gathered data", choices=['All', 'Current'], default="Current", type=str)
        sar_parser.add_argument("--command", help="Command to profile")
        sar_parser.add_argument("-v", "--verbosity",  help="increase verbosity", choices=['Low', 'Medium', 'High'], default = 'Low', type=str)
        sar_parser.add_argument("-n", "--net_type",  help="Network type to profile", choices=['DEV', 'UDP', 'IP', 'TCP', 'SOCK'], default = 'DEV', type=str)
        sar_parser.add_argument("-e", "--err_type",  help="Network error type to profile", choices=['EDEV', 'EIP', 'ETCP'], default = 'EDEV', type=str)
        sar_parser.add_argument("-dev", "--dev_list",  help="Block device to profile", type=str)

        args = parser.parse_args()
        args.func(args)


if __name__ == "__main__":
    
    obj = spa()
    obj.parse_input()
