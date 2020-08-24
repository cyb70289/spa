#!/usr/bin/env python3
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
# This file handles carrying out ebpf tracing and collection of data. 

import os
import sys
import sh
import re
import multiprocessing
import subprocess
import signal
import threading
from time import time,sleep
import perf_ebpf as pe
from datetime import datetime
import json
import data_manager
import shutil


class analyze_ebpf:


    def __init__(self, log, ebpf_obj, options):
        self.log = log
        self.ebpf_obj = ebpf_obj
        self.keys = []
        self.analyze(options)


    def analyze(self, options):
    
        path_result = "Ebpf_logs/stat_{}".format(datetime.timestamp(datetime.now()))
        self.log.info("EBPF Tracing is starting")

        if not os.path.exists("Ebpf_logs"):
            os.mkdir("Ebpf_logs")
        
        if os.path.exists(path_result):
            os.remove(path_result)
        
        if options['regex'] == 'All':
            self.default_analysis(options, path_result)
        elif not options['list']:
            self.conf_analysis(options, path_result)
        else:
            self.list_analysis(options, path_result)

        self.gather_data(path_result)
        subprocess.call("rm ebpf_latest", shell=True) 
        subprocess.call("ln -s {} ebpf_latest".format(path_result), shell=True) 
        
 
    
    def list_analysis(self, options, path_result):
    
        path = options['path']
        counters = None
        if 'event_list' in options.keys():
            counters = options['event_list']
        e = multiprocessing.Event()
        for i in options['event_list']:
            for j in options['list']:
                self.create_process(e, j, path, path_result, i, options)


    def conf_analysis(self, options, path_result):
    
        path = options['path']
        counters = None
        if 'event_list' in options.keys():
            counters = options['event_list']
        e = multiprocessing.Event()
        for i in options['event_list']:
            self.create_process(e, options['regex'], path, path_result, i, options)


    def default_analysis(self, options, path_result):
        
        path = options['path']
        counters = None
        
        if 'event_list' in options.keys():
            counters = options['event_list']
        
        arr = []
        
        command = sh.Command("readelf")
        output = command(["-Ws", "{}".format(options['obfile'])], _err_to_out = True)
        e = multiprocessing.Event()
        exp = re.compile('.*FUNC.* ([a-z_]+)')
        functions = []

        if not os.path.exists('cache.txt') or options['nooptimize'] == True:
            options['filter'] = (os.path.exists('cache.txt') == False)
            for line in output:
                match = exp.match(line)
                if match:
                    if  match.group(1):
                        self.log.info("profiling {}".format(match.group(1)))
                        for i in options['event_list']:
                            self.create_process(e, match.group(1), path, path_result, i, options)
        else:
            with open('cache.txt','r') as i:
                line = i.readline()
                while line:
                        self.log.info(line)
                        for j in options['event_list']:
                            options['filter'] = False
                            self.create_process(e, line.rstrip(), path, path_result, j, options)
                        line = i.readline()


    def create_process(self, e, function, path, path_result, counters, options):

        t1 = None
        t2 = None
        
        try:
            
            t1 = multiprocessing.Process(target=self.task, args=(options['command'],e, ))
            t2 = multiprocessing.Process(target=self.profile, 
                                         args=("{}:{}".format(path, function), 
                                         e,
                                         options['filter'],
                                         path_result,
                                         t1.pid,
                                         counters,  ))
            t2.start()
            t1.start()
            t2.join()
            t1.join()
        
        except Exception as e:
           
           exit(e)
    


    def task(self, run_c, e):
    
        sleep(1)
        process = subprocess.Popen(run_c, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        self.log.info('Starting the Run\n')
        output = process.communicate()[0]
        self.log.info('Run Finished\n')
        e.set()
    
    
    def profile(self, func, e, pred, path, pid, counters=None):
        
        command = sh.Command("python3")
        cmd = []
        opt = func.split(':')
        options = {}
        options['library'] = opt[0]
        options['symbol_re'] = opt[1]
        options['perf_events'] = counters
        options['pid'] = pid
        
    
        self.log.info("Starting the Profiler")
        tool = None

        try:
            tool = pe.PerfToolBPF(logger=self.log,**options)
        except Exception as error:
            self.log.error(error)
           
        start_time = time()
        
        self.log.info("Tracing --- hit ctrl-c to end.")
        
        def sigterm_handler(*_):
            pass
        
        try:
            e.wait()
            e.clear()
        finally:
            sigterm_old = signal.signal(signal.SIGINT, sigterm_handler)
            res = {}
            elapsedtime = time() - start_time
        
            res.update(tool.get_results())
             
            signal.signal(signal.SIGINT, sigterm_old)
            self.log.info('Detaching ...')
            self.ebpf_obj.info['info'][opt[1]] = {}
            self.ebpf_obj.info['info'][opt[1]]['Value'] = {'elapsed-time': elapsedtime, 'counter': {'latency':{} , 'value':{}}}
            for k,v in res.items():
                for k1,v1 in v.items():
                    match = re.search(r'latency.*', k)
                    if type(v1) == dict:
                        for k2,v2 in v1.items():
                            if k2 == 'count':
                                self.ebpf_obj.info['info'][opt[1]]['Value'][k2] = v2
                    elif match:
                        self.ebpf_obj.info['info'][opt[1]]['Value']['counter']['latency'].update({k[7:]: v1})
                    else:
                        self.ebpf_obj.info['info'][opt[1]]['Value']['counter']['value'].update({k[8:]: v1})
            self.dump_to_file(path, opt[1])

            if pred:
                for key in res.keys():
                    match = re.match('^total(\w+)', key)
                    if match:
                            for k, v  in res[key].items():
                                if v > 0:
                                    with open('cache.txt','a') as cache:
                                        cache.write('{}\n'.format(k.split(' ')[1]))
                                        exit()


    def dump_to_file(self, path, func):
           
        if not os.path.exists(path):
            os.mkdir(path)
        path_final = path+'/'+func
        
        with open(path_final, 'w+') as f:
           json.dump(self.ebpf_obj.info, f)


    def gather_data(self, path):

        ebpf_obj = data_manager.EBPF()

        for filename in os.listdir(path):
            with open(path+'/'+filename, 'r') as ebpf_file:
                f = json.load(ebpf_file)
                if not ebpf_obj.info['metadata']:
                    ebpf_obj.info['metadata'] = f['metadata']
                for key, value in f['info'].items():
                    ebpf_obj.info['info'][key] = value
        #print(ebpf_obj.info)
        shutil.rmtree(path)

        with open(path, 'w') as f:
            json.dump(ebpf_obj.info, f)





