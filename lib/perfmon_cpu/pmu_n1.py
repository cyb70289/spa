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


class n1(PerfmonCpu):

    def _set_metrics(self):
        """
        Registers a list of all derived metrics available for the cpu.

        Registers plot details for the derived metrics of the cpu.
        """

        
        #self.metric_list = ['branch_mix', 'mpki', 'stall', 'branch', 'missrate', 'instruction_mix', 'tlb_access_rate']
        self.metric_list = [ 'mpki', 'stall', 'missrate', 'instruction_mix']
        
        # branch details
        # self.metric_plot_data['branch_mix'] = (['Immediate', 'Return', 'Indirect', 'Rest'],
                                                    #'stacked-bar',
                                                    #'Branch Mix')

        # mpki details
        self.metric_plot_data['mpki'] = (['L1I MPKI', 'L1D MPKI', 'L2D MPKI', 'BRANCH MPKI', 'DTLB_WALK MPKI', 
                                          'ITLB_WALK MPKI'],
                                          'single-bar',
                                          'Misses Per Kilo Instructions')
        
         # instruction_mix details
        self.metric_plot_data['instruction_mix'] = (['Load', 'Store', 'Integer', 'SIMD', 'FloatingPoint', 'Branch', 'Crypto'],
                                                    'stacked-bar',
                                                    'Instruction Mix')
      

        # stalls highlevel, stack is worst case scenario as front and and back end
        # stalls can occur concurrently
        self.metric_plot_data['stall'] = (['FRONT_END_STALL', 'BACKEND_STALL', 'PIPELINE_USEFUL_CYCLES'],
                                          'stacked-bar',
                                          'Stall Distribution')
        # missrate details
        self.metric_plot_data['missrate'] = (['L1I Miss Rate', 'L1D Miss Rate', 'L2D Miss Rate', 'BRANCH Mispred Rate', 'DTLB Walk Rate', 'ITLB Walk Rate'],
                                             'single-bar',
                                             '')  # Empty because each element name will be the title

        # TLB Performance details
        #self.metric_plot_data['tlb_access_rate'] = (['DTLB_WALK_%', 'ITLB_WALK_%'],
        #                               'stacked-bar',
        #                              'L2 TLB Miss Distribution'
        #                            )

       

    def derive_perfmon_metrics(self):
        '''
        Compute all derived metrics supported by the CPU.

        Return:
            (pandas.DataFrame): A new df containing all derived metric values appended
                                to input raw counter dataframe.
        '''
        mpki_df = self.metric_mpki(self.raw_df)
        stall_df = self.metric_stall(self.raw_df)
        missrate_df = self.metric_missrate(self.raw_df)
        instr_df = self.metric_instruction_mix(self.raw_df)
        # tlb_df = self.metric_tlb_access_rate(self.raw_df)
        self.raw_df = pd.concat([self.raw_df, mpki_df, stall_df, missrate_df, instr_df], axis=1)
        return self.raw_df


    def metric_mpki(self, df_in):
        '''
        Calculate derived metric counter values: Misses Per Kilo Instructions - MPKI

        Args:
            df_in (pandas.DataFrame): Input df to calculate MPKI on

        Return:
            (pandas.DataFrame): A new df containing MPKI derived metric values
        '''
        df_out = pd.DataFrame(index=df_in.index)

        df_out['IPC'] = self._check_div(
            df_in, 'INST_RETIRED', 'CPU_CYCLES',  dscale=1000)
        df_out['L1I MPKI'] = self._check_div(
            df_in, 'L1I_CACHE_REFILL', 'INST_RETIRED', dscale=1000)
        df_out['L1I_TLB MPKI'] = self._check_div(
            df_in, 'L1I_TLB_REFILL', 'INST_RETIRED', dscale=1000)
        df_out['L1D_TLB MPKI'] = self._check_div(
            df_in, 'L1D_TLB_REFILL', 'INST_RETIRED', dscale=1000)
        df_out['L2D_TLB MPKI'] = self._check_div(
            df_in, 'L2D_TLB_REFILL', 'INST_RETIRED', dscale=1000)
        df_out['L1D MPKI'] = self._check_div(
            df_in, 'L1D_CACHE_REFILL', 'INST_RETIRED', dscale=1000)
        df_out['L2D MPKI'] = self._check_div(
            df_in, 'L2D_CACHE_REFILL', 'INST_RETIRED', dscale=1000)
        df_out['BRANCH MPKI'] = self._check_div(
           df_in, 'BR_MIS_PRED_RETIRED', 'INST_RETIRED', dscale=1000)
        df_out['DTLB_WALK MPKI'] = self._check_div(
            df_in, 'DTLB_WALK', 'INST_RETIRED', dscale=1000)
        df_out['ITLB_WALK MPKI'] = self._check_div(
            df_in, 'ITLB_WALK', 'INST_RETIRED', dscale=1000)
        return df_out

    def metric_stall(self, df_in):
        '''
        Calculate derived metric counter values: Stalls

        Args:
            df_in (pandas.DataFrame): Input df to calculate Stalls on

        Return:
            (pandas.DataFrame): A new df containing Stalls derived metric values
        '''
        df_out = pd.DataFrame(index=df_in.index)

        # High level Stall Stack
        df_out['FRONTEND_STALL'] = self._convert_to_percent(self._check_div(df_in, 'STALL_FRONTEND', 'CPU_CYCLES'))
        df_out['BACKEND_STALL'] = self._convert_to_percent(self._check_div(df_in, 'STALL_BACKEND', 'CPU_CYCLES'))
        df_out['PIPELINE_USEFUL_CYCLES'] = 100 - (df_out['FRONTEND_STALL'] + df_out['BACKEND_STALL'])
        return df_out


    def metric_missrate(self, df_in):
        '''
        Calculate derived metric counter values: Miss Rate

        Args:
            df_in (pandas.DataFrame): Input df to calculate Miss Rate on

        Return:
            (pandas.DataFrame): A new df containing Miss Rate derived metric values
        '''
        df_out = pd.DataFrame(index=df_in.index)
        df_out['L1I Miss Rate'] = self._convert_to_percent(self._check_div(df_in, 'L1I_CACHE_REFILL', 'L1I_CACHE'))
        df_out['L1D Miss Rate'] = self._convert_to_percent(self._check_div(df_in, 'L1D_CACHE_REFILL', 'L1D_CACHE'))
        df_out['L2D Miss Rate'] = self._convert_to_percent(self._check_div(df_in, 'L2D_CACHE_REFILL', 'L2D_CACHE'))
        # df_out['L3D Miss Rate'] = self._check_div(df_in, 'L3D_CACHE_REFILL', 'L3D_CACHE').apply(self._convert_to_percent)
        df_out['BRANCH Misprediction Rate'] = self._convert_to_percent(self._check_div(df_in, 'BR_MIS_PRED_RETIRED', 'BR_RETIRED'))
        df_out['BRANCH Mis-speculation Rate'] = self._convert_to_percent(self._check_div(df_in, 'BR_MIS_PRED', 'BR_PRED'))
        return df_out
    
        #TLB
        # df_out['BRANCH RETIRED MPKI'] = self._check_div(df_in, 'BR_MIS_PRED_RETIRED', 'INST_RETIRED', dscale=1e3)

    def metric_tlb_access_rate(self, df_in):
        '''
        Calculate derived metric counter values: TLB Miss Details

        Args:
            df_in (pandas.DataFrame): Input df to calculate TLB Miss Details on

        Return:
            (pandas.DataFrame): A new df containing TLB Miss Details derived metric values
        '''
        df_out = pd.DataFrame(index=df_in.index)
        df_out['L2D_TLB_Miss_Data_%'] = self._convert_to_percent(self._check_div(df_in, 'DTLB_WALK', 'MEM_ACCESS'))
        df_out['L2D_TLB_Miss_Instruction_%'] = self._convert_to_percent(self._check_div(df_in, 'ITLB_WALK', 'MEM_ACCESS'))
        return df_out

    def metric_instruction_mix(self, df_in):
        '''
        Calculate derived metric counter values: Instruction Mix

        Args:
            df_in (pandas.DataFrame): Input df to calculate Instruction Mix on

        Return:
            (pandas.DataFrame): A new df containing Instruction Mix derived metric values
        '''

        df_out = pd.DataFrame(index=df_in.index)
        df_out['Load %'] = self._convert_to_percent(self._check_div(df_in, 'LD_SPEC', 'INST_SPEC'))
        df_out['Store %'] = self._convert_to_percent(self._check_div(df_in, 'ST_SPEC', 'INST_SPEC'))
        df_out['Branch'] = self._convert_to_percent(self._check_div(df_in, 'BR_PRED', 'INST_SPEC'))
        df_out['DP %'] = self._convert_to_percent(self._check_div(df_in, 'DP_SPEC', 'INST_SPEC'))
        df_out['VFP %'] = self._convert_to_percent(self._check_div(df_in, 'VFP_SPEC', 'INST_SPEC'))
        df_out['ASE %'] = self._convert_to_percent(self._check_div(df_in, 'ASE_SPEC', 'INST_SPEC'))
        df_out['Total Branches'] = df_in[ 'BR_INDIRECT_SPEC'] + df_in['BR_IMMED_SPEC'] + df_in['BR_RETURN_SPEC']
        df_out['Crypto %'] = self._convert_to_percent(self._check_div(df_in, 'CRYPTO_SPEC', 'INST_SPEC'))
        #df_out['Branch %'] = self._convert_to_percent(self._check_div(df_in, 'Total Branches', 'INST_SPEC'))
        return df_out
    
    def metric_branch_mix(self, df_in):
        '''
        Calculate derived metric counter values: Branch Mix

        Args:
            df_in (pandas.DataFrame): Input df to calculate Branch Mix on

        Return:
            (pandas.DataFrame): A new df containing Branch Mix derived metric values
        '''

        df_out = pd.DataFrame(index=df_in.index)
        df_out['Return %'] = self._convert_to_percent(self._check_div(df_in, 'BR_RETURN_SPEC', 'BR_PRED'))
        df_out['Immed %'] = self._convert_to_percent(self._check_div(df_in, 'BR_IMMED_SPEC', 'BR_PRED'))
        df_out['Indirect %'] = self._convert_to_percent(self._check_div(df_in, 'BR_INDIRECT_SPEC', 'BR_PRED'))
        return df_out
