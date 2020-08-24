#!/usr/bin/python3

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
# Authors: Rob Golshan
#
# This file records PMU counters across function calls

from time import sleep, time
import json
import signal
import argparse
import logging
from virtif import set_logger  # pylint: disable=no-name-in-module
from function_ebpf import FunctionTool


class PerfToolBPF(FunctionTool):
    __BPF_TEXT = """
    #include <uapi/linux/ptrace.h>

    typedef struct data {
        PMU_FIELDS
    } data_t;

    typedef struct time_data{
         TIME_FIELDS
    } time_data_t;

    typedef struct data_key {
        u64 task;
        u64 cpu;
    } data_key_t;

    typedef struct hist_key {
        u64 key;
        u64 slot;
    } hist_key_t;

    PMU_ARRAYS

    BPF_HASH(data_hash, data_key_t, data_t);
    BPF_HASH(time_hash, data_key_t, time_data_t);
    """

    __TEMPLATE = """
    int trace_enter_PROBE(struct pt_regs *ctx) {
        u64 task = bpf_get_current_pid_tgid();
        u32 pid = task >> 32;
        FILTER
        data_key_t save_key = {
            .task = task,
            .cpu = bpf_get_smp_processor_id()
        };

        data_t data = {
            PMU_READ
        };

        time_data_t old_data_time = {
            TIME_READ
        };

        time_hash.update(&save_key, &old_data_time);
        data_hash.update(&save_key, &data);

        return 0;
    };

    int trace_complete_PROBE(struct pt_regs *ctx) {
        u64 task = bpf_get_current_pid_tgid();
        u32 pid = task >> 32;
        FILTER
        data_t new_data = {
            PMU_READ
        };

        time_data_t new_data_time = {
            TIME_READ
        };

        data_key_t save_key = {
            .task = task,
            .cpu = bpf_get_smp_processor_id()
        };

        time_data_t *old_data_time = time_hash.lookup(&save_key);
        data_t *data = data_hash.lookup(&save_key);
        
        if (data == 0) return 0;
        if (old_data_time == 0) return 0;

        hist_key_t key = {};
        key.key = PROBE;
        u64 pmu_diff;
        u64 latency;
        PMU_STORE

        data_hash.delete(&save_key);
        time_hash.delete(&save_key);

        return 0;
    };
    """

    def __init__(self, logger, perf_events, symbol_re, library=None, kernel=False, pid=None, process_name=None,
                 **kwargs):  # pylint: disable=unused-argument
        from os import cpu_count
        super().__init__(logger=logger, text=self.__BPF_TEXT, template=self.__TEMPLATE, library=library, kernel=kernel,
                         pid=pid, process_name=process_name)

        self.perf_events = perf_events.split(',')
        self.__add_pmus()
        self._add_probes(symbol_re)
        self._create_bpf(cflags=['-DNUM_CPUS={}'.format(cpu_count())])
        self.__open_pmus()
        self.attach_probes()

    def __open_pmus(self):
        import bcc  # pylint: disable=import-error
        for i, event in enumerate(self.perf_events):
            try:
                event = bcc.PerfHWConfig.__dict__[event.upper()]
                event_type = bcc.PerfType.HARDWARE
            except KeyError:
                # assume passing in raw counter
                if '0x' in event:
                    event = int(event, 16)
                else:
                    event = int(event)
                event_type = 4  # Raw event. Using a number until BCC supports specifying raw
            table = self.bpf['cnt{}'.format(i)]
            table.open_perf_event(event_type, event)

    def __add_pmus(self):
        self.metrics_array.extend(['totalpmu{}'.format(i) for i in range(len(self.perf_events))])
        self.metrics_array.extend(['latency{}'.format(i) for i in range(len(self.perf_events))])
        self.metrics.extend(['pmu{}'.format(i) for i in range(len(self.perf_events))])
        self.metrics.extend(['time{}'.format(i) for i in range(len(self.perf_events))])
        self.text = self.text.replace('PMU_FIELDS',
                                      ''.join('u64 pmu{};\n'.format(i) for i in range(len(self.perf_events))))
        self.text = self.text.replace('TIME_FIELDS',
                                      ''.join('u64 time{};\n'.format(i) for i in range(len(self.perf_events))))
        self.text = self.text.replace('PMU_ARRAYS',
                                      ''.join('''
            BPF_PERF_ARRAY(cnt{}, NUM_CPUS);\n
            BPF_HISTOGRAM(pmu{}_dist, hist_key_t, FUNCTIONS*64);\n
            BPF_HISTOGRAM(time{}_dist, hist_key_t, FUNCTIONS*64);\n
            BPF_ARRAY(totalpmu{}_array, u64, FUNCTIONS);\n
            BPF_ARRAY(latency{}_array, u64, FUNCTIONS);'''.format(i, i, i, i, i) for i in range(len(self.perf_events))))

        self.template = self.template.replace('PMU_READ',
                                              ''.join('.pmu{} = cnt{}.perf_read(CUR_CPU_IDENTIFIER),\n'.format(i, i) for i in range(len(self.perf_events))))
        self.template = self.template.replace('TIME_READ',
                                              ''.join('.time{} = bpf_ktime_get_ns(),\n'.format(i, i) for i in range(len(self.perf_events))))

        self.template = self.template.replace('PMU_STORE',
                                              ''.join('''
            pmu_diff = new_data.pmu{} - data->pmu{};
            if (pmu_diff)
                totalpmu{}_array.increment(key.key, pmu_diff);
            pmu_diff = pmu_diff? bpf_log2l(pmu_diff):0;
            key.slot = pmu_diff;
            pmu{}_dist.increment(key);
            time{}_dist.increment(key);
            latency = new_data_time.time{} - old_data_time->time{};
            if (latency)
                latency{}_array.increment(key.key, latency);
                    '''.format(i, i, i, i, i, i, i, i) for i in range(len(self.perf_events))))

    def get_results(self):
        import re
        result = {}
        for name, value in super().get_results().items():
            match = re.search(r'[pmu|latency](\d+)', name)
            if match:
                name = re.sub(match.group(1), self.perf_events[int(match.group(1))], name)
            result[name] = value
        return result


