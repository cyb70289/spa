#!/usr/bin/python3

#    Copyright 2020 Arm Limited
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Author: Jumana Mundichipparakkal

from perfmon_cpu import PerfmonCpu
import pandas as pd
import numpy
import sys
sys.path.append('../')
import data_manager

class v1(PerfmonCpu):


    def derive_perfmon_metrics(self):
        '''
        Compute all derived metrics supported by the CPU.

        Return:
            (data_manager.PMU()): A new object containing all derived metric values.
        '''
        final_obj = data_manager.PMU()

        final_obj.info['metadata'] = self.pmu_obj.info['metadata']

        mpki_obj = self.metric_mpki(self.pmu_obj)
        metric_v1 = self.metric_v1(self.pmu_obj)
        stall_obj = self.metric_stall(self.pmu_obj)
        missrate_obj = self.metric_missrate(self.pmu_obj)
        instr_obj = self.metric_instruction_mix(self.pmu_obj)
        tlb_obj = self.metric_tlb_access_rate(self.pmu_obj)
        final_obj.info['counter'] = {**mpki_obj ,**stall_obj, **missrate_obj, **instr_obj, **tlb_obj, **metric_v1}
        return final_obj


    def metric_mpki(self, obj_in):
        
        obj_out = {}

        obj_out['IPC'] = self._check_div(
            obj_in, 'INST_RETIRED', 'CPU_CYCLES',  dscale=1)
        obj_out['L1I MPKI'] = self._check_div(
            obj_in, 'L1I_CACHE_REFILL', 'INST_RETIRED', dscale=1000)
        obj_out['L1I_TLB MPKI'] = self._check_div(
            obj_in, 'L1I_TLB_REFILL', 'INST_RETIRED', dscale=1000)
        obj_out['L1D_TLB MPKI'] = self._check_div(
            obj_in, 'L1D_TLB_REFILL', 'INST_RETIRED', dscale=1000)
        obj_out['L2D_TLB MPKI'] = self._check_div(
            obj_in, 'L2D_TLB_REFILL', 'INST_RETIRED', dscale=1000)
        obj_out['L1D MPKI'] = self._check_div(
            obj_in, 'L1D_CACHE_REFILL', 'INST_RETIRED', dscale=1000)
        obj_out['L2D MPKI'] = self._check_div(
            obj_in, 'L2D_CACHE_REFILL', 'INST_RETIRED', dscale=1000)
        obj_out['BRANCH MPKI'] = self._check_div(
           obj_in, 'BR_MIS_PRED_RETIRED', 'INST_RETIRED', dscale=1000)
        obj_out['DTLB_WALK MPKI'] = self._check_div(
            obj_in, 'DTLB_WALK', 'INST_RETIRED', dscale=1000)
        obj_out['ITLB_WALK MPKI'] = self._check_div(
            obj_in, 'ITLB_WALK', 'INST_RETIRED', dscale=1000)
        return obj_out


    def metric_stall(self, obj_in):
        '''
        Calculate derived metric counter values: Stalls

        Args:
            obj_in (data_manager.PMU): Input object to calculate Stalls on

        Return:
            obj_out (dict): A new dict containing Stalls derived metric values
        '''
        obj_out = {}

        # High level Stall Stack
        obj_out['FRONTEND_STALL'] = self._convert_to_percent(self._check_div(obj_in, 'STALL_FRONTEND', 'CPU_CYCLES'))
        obj_out['BACKEND_STALL'] = self._convert_to_percent(self._check_div(obj_in, 'STALL_BACKEND', 'CPU_CYCLES'))
        obj_out['PIPELINE_USEFUL_CYCLES'] = 100 - (obj_out['FRONTEND_STALL'] + obj_out['BACKEND_STALL'])
        return obj_out


    def metric_missrate(self, obj_in):
        '''
        Calculate derived metric counter values: Miss Rate

        Args:
            obj_in (data_manager.PMU): Input object to calculate Stalls on

        Return:
            obj_out (dict): A new dict containing Stalls derived metric values
        '''
        
        obj_out = {}
        obj_out['L1I Miss Rate'] = self._convert_to_percent(self._check_div(obj_in, 'L1I_CACHE_REFILL', 'L1I_CACHE'))
        obj_out['L1D Miss Rate'] = self._convert_to_percent(self._check_div(obj_in, 'L1D_CACHE_REFILL', 'L1D_CACHE'))
        obj_out['L2D Miss Rate'] = self._convert_to_percent(self._check_div(obj_in, 'L2D_CACHE_REFILL', 'L2D_CACHE'))
        #obj_out['L3D Miss Rate'] = self._check_div(obj_in, 'L3D_CACHE_REFILL', 'L3D_CACHE').apply(self._convert_to_percent)
        obj_out['BRANCH Misprediction Rate'] = self._convert_to_percent(self._check_div(obj_in, 'BR_MIS_PRED_RETIRED', 'BR_RETIRED'))
        obj_out['BRANCH Mis-speculation Rate'] = self._convert_to_percent(self._check_div(obj_in, 'BR_MIS_PRED', 'BR_PRED'))
        return obj_out
    
        #TLB
        # obj_out['BRANCH RETIRED MPKI'] = self._check_div(obj_in, 'BR_MIS_PRED_RETIRED', 'INST_RETIRED', dscale=1e3)

    def metric_tlb_access_rate(self, obj_in):
        '''
        Calculate derived metric counter values: TLB Miss Details

        Args:
            obj_in (data_manager.PMU): Input object to calculate Stalls on

        Return:
            obj_out (dict): A new dict containing Stalls derived metric values
        '''
        
        obj_out = {}
        obj_out['L2D_TLB_Miss_Data_%'] = self._convert_to_percent(self._check_div(obj_in, 'DTLB_WALK', 'MEM_ACCESS'))
        obj_out['L2D_TLB_Miss_Instruction_%'] = self._convert_to_percent(self._check_div(obj_in, 'ITLB_WALK', 'MEM_ACCESS'))
        return obj_out


    def metric_v1(self, obj_in):
        '''
        Extra PMU metric exclusive to V1

        Args:
            obj_in (data_manager.PMU): Input object to calculate Stalls on

        Return:
            obj_out (dict): A new dict containing Stalls derived metric values
        '''
        obj_out = {}
        tmp = {}
        
        tmp['RET/SPEC'] = self._check_div(obj_in, 'OP_RETIRED', 'OP_SPEC')
        tmp['STALL/CYCLES'] = self._check_div(obj_in, 'STALL_SLOT', 'CPU_CYCLES')
        tmp['STALLF/CYCLES'] = self._check_div(obj_in, 'STALL_SLOT_FRONTEND', 'CPU_CYCLES')
        tmp['STALLB/CYCLES'] = self._check_div(obj_in, 'STALL_SLOT_BACKEND', 'CPU_CYCLES')

        tmp['BR/CYC'] = numpy.divide(obj_in.info['counter']['BR_MIS_PRED']['Value'], obj_in.info['counter']['CPU_CYCLES']['Value'])*4
        tmp['invOP'] = 1 - tmp['RET/SPEC']
        tmp['invSL'] = 1 - (tmp['STALL/CYCLES']*(1/8))

        tmp['RETL1'] = tmp['RET/SPEC'] * tmp['invSL']*100
        tmp['BADSPECL1'] = tmp['invOP'] * tmp['invSL'] * tmp['BR/CYC'] * 100
        
        obj_out['Retiring'] = tmp['RETL1']
        obj_out['Bad Speculation'] = tmp['BADSPECL1']
        obj_out['Frontend Bound'] = 100 * (tmp['STALLF/CYCLES']*(1/8) - tmp['BR/CYC'])
        obj_out['Frontend Bound'] = 100 * (tmp['STALLB/CYCLES']*(1/8))

        return obj_out


    def metric_instruction_mix(self, obj_in):
        '''
        Calculate derived metric counter values: Instruction Mix

        Args:
            obj_in (data_manager.PMU): Input object to calculate Stalls on

        Return:
            obj_out (dict): A new dict containing Stalls derived metric values
        '''

        obj_out = {}
        obj_out['Load %'] = self._convert_to_percent(self._check_div(obj_in, 'LD_SPEC', 'INST_SPEC'))
        obj_out['Store %'] = self._convert_to_percent(self._check_div(obj_in, 'ST_SPEC', 'INST_SPEC'))
        obj_out['Branch'] = self._convert_to_percent(self._check_div(obj_in, 'BR_PRED', 'INST_SPEC'))
        obj_out['DP %'] = self._convert_to_percent(self._check_div(obj_in, 'DP_SPEC', 'INST_SPEC'))
        obj_out['VFP %'] = self._convert_to_percent(self._check_div(obj_in, 'VFP_SPEC', 'INST_SPEC'))
        obj_out['ASE %'] = self._convert_to_percent(self._check_div(obj_in, 'ASE_SPEC', 'INST_SPEC'))
        obj_out['Total Branches'] = [a+b+c for a,b,c in zip(obj_in.info['counter']['BR_INDIRECT_SPEC']['Value'],
                                     obj_in.info['counter']['BR_IMMED_SPEC']['Value'], obj_in.info['counter']['BR_RETURN_SPEC']['Value'])]
        obj_out['Crypto %'] = self._convert_to_percent(self._check_div(obj_in, 'CRYPTO_SPEC', 'INST_SPEC'))
        obj_out['Branch %'] = self._convert_to_percent(numpy.divide(obj_out['Total Branches'], obj_in.info['counter']['INST_SPEC']['Value']))
        return obj_out
    
    def metric_branch_mix(self, obj_in):
        '''
        Calculate derived metric counter values: Branch Mix

        Args:
            obj_in (data_manager.PMU): Input object to calculate Stalls on

        Return:
            obj_out (dict): A new dict containing Stalls derived metric values
        '''

        obj_out = {}
        obj_out['Return %'] = self._convert_to_percent(self._check_div(obj_in, 'BR_RETURN_SPEC', 'BR_PRED'))
        obj_out['Immed %'] = self._convert_to_percent(self._check_div(obj_in, 'BR_IMMED_SPEC', 'BR_PRED'))
        obj_out['Indirect %'] = self._convert_to_percent(self._check_div(obj_in, 'BR_INDIRECT_SPEC', 'BR_PRED'))
        return obj_out
