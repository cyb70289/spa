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
import os
from bcc import BPF  # pylint: disable=import-error


class FunctionTool():
    def __init__(self, text, template, library=None, kernel=False, pid=None, process_name=None, logger=None):
        """Abstract class to create and attach probes to functions. A class
        inheriting this class should call super().init, _add_probes(), _create_bpf(),
        and attach_probes() in that order. It is fine to mix in calls to other
        functions between that ordering. Attach_probes will start data collection.

        Args:
        text (str): BPF text containing all defines and data structures to be shared across functions
        template (str): BPF function entry and return template. Functions must be named trace_enter_PROBE and
            trace_complete_PROBE, respectively
        library (str): Full path to a library containing the functions to probe
        kernel (bool): Whether to probe kernel functions. It is recommended
        not to probe both library and kernel functions at the same time.
        pid (int): Record statistics from this pid
        process_name (str): Record statistics from this process. If pid and
        process_name are both None, record every process except this python process.
        logger (logger): logger to log info to

        """
        self.text = text
        self.template = template
        self.metrics = []
        self.metrics_comp = []
        self.metrics_hash = []
        self.metrics_array = []
        self.library = library
        self.kernel = kernel
        self.num_probes = 0
        self.user_probe_names = {}
        self.kernel_probe_names = {}
        self.combined_probe_names = {}
        self.bpf = None
        if not logger:
            import logging
            logger = logging.getLogger('')
        self.logger = logger

        from sh import perf
        # delete all existing probes in case this app died incorrectly and left some open
        perf('probe', '-d', '*probe*', _ok_code=[0, 254])

        self.__setup_pid_filter(pid, process_name)

    def __setup_pid_filter(self, pid=None, process_name=None):
        from sh import pgrep
        pids = set()
        if pid:
            pids.add(int(pid))
        if process_name:
            # We absorb any errors from pgrep when it can't find a requested name
            pids.update([int(y) for x in process_name for y in pgrep(x, _ok_code=[0, 1])])

        if pids:
            code = 'switch(pid){\n' + \
                '\n'.join('      case {}: break;'.format(pid) for pid in pids) + \
                '\n    default: return 0;}'

            self.template = self.template.replace('FILTER', code)
        else:
            # Don't include functions this script calls
            pid = os.getpid()
            self.template = self.template.replace('FILTER',
                                                  """
                          if (pid == %d) {return 0;}
                    """ % pid)

    def _create_bpf(self, cflags=None):
        if cflags is None:
            cflags = []
        self.bpf = BPF(text=self.text, cflags=cflags)

    def _add_probes(self, symbol_re):
       # if self.library:
       #     from sh import readelf, awk, ErrorReturnCode_1
       #     # get ifuncs from elf until the bcc python API supports passing in an option to not read ifunc symbols
       #     try:
       #         elf = readelf('-Ws', '/usr/lib/debug{}'.format(self.library))
       #     except ErrorReturnCode_1:
       #         elf = readelf('-Ws', self.library)
       #     ifuncs_set = set(func.encode() for func in
       #                      awk(elf, 'BEGIN{IGNORECASE=1} /.*ifunc.*/{print $8}').splitlines())
       #     functions = BPF.get_user_functions_and_addresses(name=self.library, sym_re=symbol_re.encode())
       #     func_set = set()
       #     addr_dict = {}

       #     for func, addr in functions:  # in order defined by symtab
       #         if func in ifuncs_set or func in func_set:
       #             continue
       #         if addr not in addr_dict:
       #             addr_dict[addr] = func
       #             func_set.add(func)
       #         # Prefer function names that do not have GI and names that are shorter
       #         elif b'GI' not in func and (b'GI' in addr_dict.get(addr) or len(func) < len(addr_dict.get(addr))):
       #             addr_dict[addr] = func
       #             func_set.add(func)

       #     for func in addr_dict.values():
       #self.num_probes = 1
       self.text += self.template.replace('PROBE', str(self.num_probes))
       self.user_probe_names[self.num_probes] = symbol_re
       self.num_probes = 1
       #     self.logger.info('uprobe functions: %s', self.user_probe_names.values())

       # if self.kernel:
       #     functions = BPF.get_kprobe_functions(symbol_re.encode())
       #     addr_set = {}
       #     for func in functions:
       #         addr = BPF.ksymname(func)
       #         if addr in addr_set:
       #             continue  # Do not probe the same address
       #         addr_set[addr] = func
       #     for addr, func in sorted(addr_set.items(), reverse=True):
       #         # If a function __always__ calls another function, usually that
       #         # function is at a higher address. See memcpy vs memcpy_erms.
       #         # Reverse it so the higher address (inner) function gets probed
       #         # first, preventing calls from the outer function showing up.
       #         resolved_func = BPF.ksym(addr)  # Maps a function to a consistent name
       #         self.logger.info('%s = %s', func, resolved_func)
       #         self.text += self.template.replace('PROBE', str(self.num_probes))
         #       self.kernel_probe_names[self.num_probes] = resolved_func
            #self.logger.info('kprobe functions: %s', self.kernel_probe_names.values())
       self.text = self.text.replace('FUNCTIONS', str(self.num_probes))

    def attach_probes(self):
        for number, name in self.user_probe_names.items():
            try:
                self.bpf.attach_uretprobe(name=self.library, sym=name, fn_name="trace_complete_{}".format(number))
                self.bpf.attach_uprobe(name=self.library, sym=name, fn_name="trace_enter_{}".format(number))
            except Exception:  # pylint: disable=broad-except
                # A toplevel exception can be thrown if perf throws an error
                self.logger.info('%s failed to attach', name)

        #for number, name in self.kernel_probe_names.items():
         #   try:
          #      self.bpf.attach_kretprobe(event=name, fn_name="trace_complete_{}".format(number))
           #     self.bpf.attach_kprobe(event=name, fn_name="trace_enter_{}".format(number))
           # except Exception:  # pylint: disable=broad-except
            #    self.logger.info('%s failed to attach', name)

    def get_hist_results(self, table_name, unit):
        tmp = {}
        for k, v in self.bpf[table_name].items():
            pid = self.combined_probe_names[k.key]
            slot = k.slot
            count = v.value
            hist = tmp.get(pid, {unit: {}, 'count': 0})
            prev_count = hist[unit].get(slot, 0)
            hist[unit][slot] = prev_count + count
            hist['count'] += count
            tmp[pid] = hist
        return tmp

    def get_compare_hist_results(self, table_name, unit):
        tmp = {}
        for k, v in self.bpf[table_name].items():
            pid = self.combined_probe_names[k.key]
            slot1 = k.slot1
            slot2 = k.slot2
            count = v.value
            hist = tmp.get(pid, {unit: {}, 'count': 0})
            prev_count = hist[unit].get('{}-{}'.format(slot1, slot2), 0)
            hist[unit]['{}-{}'.format(slot1, slot2)] = prev_count + count
            hist['count'] += count
            tmp[pid] = hist
        return tmp

    def get_hash_results(self, table_name, unit):
        tmp = {}
        for k, v in self.bpf[table_name].items():
            pid = self.combined_probe_names[k.key]
            slot = k.slot
            count = v.value
            temp_dict = tmp.get(pid, {unit: {}})
            prev_count = temp_dict[unit].get(slot, 0)
            temp_dict[unit][slot] = prev_count + count
            tmp[pid] = temp_dict
        return tmp

    def get_array_results(self, table_name):
        tmp = {}
        for k, v in self.bpf[table_name].items():
            if v.value == 0:
                continue
            pid = self.combined_probe_names[k.value]
            count = v.value
            tmp[pid] = count
        return tmp

    def get_results(self):
        if self.library:
            library = self.library.split('/')[-1]
        for k, v in self.user_probe_names.items():
            if isinstance(v, list):
                v = [elem.decode() for elem in v]
            else:
                v = v
            self.combined_probe_names[k] = '[{}] {}'.format(library, v)
        for k, v in self.kernel_probe_names.items():
            if isinstance(v, list):
                v = [elem.decode() for elem in v]
            else:
                v = v.decode()
            self.combined_probe_names[k] = '[kernel] {}'.format(v)

        res = {}
        for metric in self.metrics:
            unit = 'hist-log2'
            if isinstance(metric, tuple):
                metric, unit = metric
            res[metric] = self.get_hist_results('{}_dist'.format(metric), unit)
        for metric in self.metrics_comp:
            unit = 'hist-log2'
            if isinstance(metric, tuple):
                metric, unit = metric
            res[metric] = self.get_compare_hist_results('{}_dist'.format(metric), unit)
        for metric in self.metrics_hash:
            unit = 'bin-log2'
            if isinstance(metric, tuple):
                metric, unit = metric
            res[metric] = self.get_hash_results('{}_hash'.format(metric), unit)
        for metric in self.metrics_array:
            res[metric] = self.get_array_results('{}_array'.format(metric))
        return res
