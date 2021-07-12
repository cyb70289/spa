#!bin/python3


import os
import sys
import sh
import re
import multiprocessing
import subprocess
import signal
import threading
from time import time,sleep
from datetime import datetime
import json
import data_manager
import shutil


class spa_sar:

    def __init__(self, log,  options):
        
        self.log = log
        self.options = options
        self.create_command()

    def create_command(self):
        
        metrics = self.options['metrics'].split(',')
        
        for i in metrics:
            if i == "cpu":
                print("cpu")
                cmd_op = self.create_cpu_command()
                output_path = "sar_logs/cpu_util"
            if i == "net":
                cmd_op = self.create_network_command()
                print(cmd_op)
                output_path = "sar_logs/net_stat"
            if i == "mem":
                cmd_op = self.create_memory_command()
                output_path = "sar_logs/mem_stat"
            if i == "dev":
                cmd_op = self.create_device_command()
                output_path = "sar_logs/dev_stat"
            if i == "err":
                cmd_op = self.create_err_command()
                output_path = "sar_logs/err_stat"
            if i == "io":
                cmd_op = self.create_err_command()
                output_path = "sar_logs/io_stat"
        
            e = multiprocessing.Event()

            try:
                t1 = multiprocessing.Process(target=self.run_profiler, args=(cmd_op, output_path, e,))
                t2 = multiprocessing.Process(target=self.run_command, args=(e,))
                t1.start()
                t2.start()
                e.wait()
                t1.terminate()
                e.clear()
                t1.join()
                t2.join()

            except Exception as exp:
                self.log.error(exp)
                exit(exp)
            self.create_csv(output_path)
            os.remove("output")


    def create_cpu_command(self):

        cmd_op = []
        cmd_op.append('-u')
        cmd_op.append(self.options['interval'])

        return cmd_op

    
     
    def create_network_command(self):
    
        cmd_op = []
        cmd_op.append('-n')
        cmd_op.append(self.options['net_type'])
        cmd_op.append(self.options['interval'])
        return cmd_op
   

    def create_device_command(self):   #sar -d for all the block devices
        
        cmd_op = []
        cmd_op.append('-d')
        cmd_op.append(self.options['interval'])
        if "dev_list" in self.options.keys():
            cmd_op.append('--dev')
            cmd_op.append(self.options[dev_list])

        return cmd_op
    

    def create_memory_command(self):   #sar -d for all the block devices
        
        cmd_op = []
        cmd_op.append('-r')
        cmd_op.append(self.options['interval'])
        return cmd_op



    def create_io_command(self):   #sar -b for all the I/O statistics
        
        cmd_op = []
        cmd_op.append('-b')
        cmd_op.append(self.options['interval'])
        return cmd_op
    

    def create_err_command(self):

        cmd_op = []
        cmd_op.append('-n')
        cmd_op.append(self.options['err_type'])
        cmd_op.append(self.options['interval'])
        return cmd_op


    def run_command(self, e):

        sleep(1)
        process = subprocess.Popen(self.options['command'], shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        self.log.info('Starting the Run\n')
        output = process.communicate()[0]
        self.log.info('Run Finished\n')
        e.set()


    def run_profiler(self, cmd_op, output_path, e):
        
        com = sh.Command('sar')
        
        try:
            com(cmd_op, _bg=False, _out='output',  _err_to_out=True)
        except Exception as err:
            self.log.error(err)
        

    def create_csv(self, output_path):

        out = ""
        with open("{}/sar_{}.csv".format(output_path, self.options['timestamp']), "w") as f:
            with open("output", "r") as fread:
                skip = 0
                i = 0
                for line in fread:
                    if i < 2:
                        i = i + 1
                        continue
                    out = line
                    if out == "\n" or skip == 1:
                        if skip == 1:
                            skip = 0
                            continue
                        skip = 1
                        continue
                    out = re.sub('\033\\[([0-9]+)(;[0-9]+)*m', '', str(out)) 
                    out = re.sub(" +", ",", out)
                    self.log.info(out)
                    f.write(out)
    
