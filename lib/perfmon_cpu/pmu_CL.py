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

from .perfmon_cpu import PerfmonCpu
import pandas as pd
import numpy


class CL(PerfmonCpu):

    def _set_metrics(self):
        """
        Registers a list of all derived metrics available for the cpu.

        Registers plot details for the derived metrics of the cpu.
        """

        
        #self.metric_list = ['branch_mix', 'mpki', 'stall', 'branch', 'missrate', 'instruction_mix', 'tlb_access_rate']
        self.metric_list = [ 'mpki']
        
        # branch details
        # self.metric_plot_data['branch_mix'] = (['Immediate', 'Return', 'Indirect', 'Rest'],
                                                    #'stacked-bar',
                                                    #'Branch Mix')

        # mpki details
        self.metric_plot_data['mpki'] = (['L1I MPKI', 'ITLB MPKI', 'DTLB MPKI', 'L1D MPKI', 'L2D MPKI', 'L3 MPKI'],
                                          'single-bar',
                                          'Misses Per Kilo Instructions')
        
         # instruction_mix details
        #self.metric_plot_data['instruction_mix'] = (['Load', 'Store', 'Integer', 'SIMD', 'FloatingPoint', 'Branch', 'Crypto'],
         #                                           'stacked-bar',
          #                                          'Instruction Mix')
      

        # stalls highlevel, stack is worst case scenario as front and and back end
        # stalls can occur concurrently
        #self.metric_plot_data['stall'] = (['STALL', 'L1D_STALL', 'L2_STALL', 'L3_STALL'],
                                          #'stacked-bar',
                                          #'Stall Distribution')
       
            
        # missrate details
        #self.metric_plot_data['missrate'] = (['L1D Miss Rate', 'L2D Miss Rate'],
                                           # 'single-bar',
                                           # '')  # Empty because each element name will be the title

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
        # missrate_df = self.metric_missrate(self.raw_df)
        # instr_df = self.metric_instruction_mix(self.raw_df)
        # tlb_df = self.metric_tlb_access_rate(self.raw_df)
        self.raw_df = pd.concat([self.raw_df, mpki_df, stall_df], axis=1)

    def metric_mpki(self, df_in):
        '''
        Calculate derived metric counter values: Misses Per Kilo Instructions - MPKI

        Args:
            df_in (pandas.DataFrame): Input df to calculate MPKI on

        Return:
            (pandas.DataFrame): A new df containing MPKI derived metric values
        '''
        df_out = pd.DataFrame(index=df_in.index)

        df_out['L1I MPKI'] = self._convert_to_percent(self._check_div(
            df_in, 'L1-icache-load-misses', 'inst_retired.any', dscale=1000))
        df_out['ITLB MPKI'] = self._convert_to_percent(self._check_div(
            df_in, 'L1-dcache-load-misses', 'inst_retired.any', dscale=1000))
        df_out['DTLB MPKI'] = self._convert_to_percent(self._check_div(
            df_in, 'L1-dcache-load-misses', 'inst_retired.any', dscale=1000))
        df_out['L1D MPKI'] = self._convert_to_percent(self._check_div(
            df_in, 'L1-dcache-load-misses', 'inst_retired.any', dscale=1000))
        df_out['L2D MPKI'] = self._convert_to_percent(self._check_div(
            df_in, 'MEM_LOAD_RETIRED.L2_MISS', 'inst_retired.any', dscale=1000))
        df_out['L3D MPKI'] = self._convert_to_percent(self._check_div(
            df_in, 'MEM_LOAD_RETIRED.L3_MISS', 'inst_retired.any', dscale=1000))
        
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
        df_out['STALL'] = self._convert_to_percent(self._check_div(df_in, 'CYCLE_ACTIVITY.STALLS_TOTAL', 'cycles'))
        df_out['L1D_STALL'] = self._convert_to_percent(self._check_div(df_in, 'CYCLE_ACTIVITY.STALLS_L1D_MISS', 'cycles'))
        df_out['L2_STALL'] = self._convert_to_percent(self._check_div(df_in, 'CYCLE_ACTIVITY.STALLS_L2_MISS', 'cycles'))
        df_out['L3_STALL'] = self._convert_to_percent(self._check_div(df_in, 'CYCLE_ACTIVITY.STALLS_L3_MISS', 'cycles'))
        return df_out

